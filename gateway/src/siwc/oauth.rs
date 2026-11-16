use super::types::{RESOURCE_URL, SCOPES, StoredCredentials, TokenResponse};
use anyhow::{Context, Result, anyhow};
use base64::Engine;
use base64::engine::general_purpose::URL_SAFE_NO_PAD;
use chrono::{Duration, Utc};
use rand::RngCore;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::HashMap;
use std::fs;
use std::path::Path;
use std::process::Command;
use std::sync::mpsc;
use tiny_http::{Response, Server};
use tracing::info;
use url::Url;

#[allow(dead_code)]
#[derive(Serialize, Deserialize)]
struct PendingPkce {
    code_verifier: String,
    state: String,
    client_id: String,
}

pub fn load_credentials(path: &Path) -> Result<StoredCredentials> {
    if !path.exists() {
        return Err(anyhow!("Credential file {:?} does not exist", path));
    }
    let content = fs::read_to_string(path)
        .with_context(|| format!("Failed to read credentials file: {:?}", path))?;
    let creds: StoredCredentials = serde_json::from_str(&content)
        .with_context(|| format!("Failed to parse credentials file: {:?}", path))?;
    Ok(creds)
}

pub fn save_credentials(path: &Path, creds: &StoredCredentials) -> Result<()> {
    if let Some(parent) = path.parent() {
        if !parent.as_os_str().is_empty() {
            fs::create_dir_all(parent)?;
        }
    }
    let content = serde_json::to_string_pretty(creds)?;
    fs::write(path, content)?;
    Ok(())
}

pub async fn refresh_access_token(
    http_client: &reqwest::Client,
    token_url: &str,
    creds: &StoredCredentials,
) -> Result<StoredCredentials> {
    let refresh_tok = creds
        .refresh_token
        .as_deref()
        .ok_or_else(|| anyhow!("No refresh_token found in stored credentials"))?;

    let mut params = HashMap::new();
    params.insert("grant_type", "refresh_token");
    params.insert("refresh_token", refresh_tok);
    params.insert("client_id", &creds.client_id);
    params.insert("resource", RESOURCE_URL);

    let resp = http_client
        .post(token_url)
        .form(&params)
        .send()
        .await
        .context("Failed to contact token endpoint for refresh")?;

    let status = resp.status();
    let body = resp.text().await?;

    if !status.is_success() {
        return Err(anyhow!("Token refresh failed ({}): {}", status, body));
    }

    let token_resp: TokenResponse = serde_json::from_str(&body)
        .with_context(|| format!("Failed to parse token response: {}", body))?;

    let new_creds = StoredCredentials {
        access_token: token_resp.access_token,
        refresh_token: token_resp
            .refresh_token
            .or_else(|| creds.refresh_token.clone()),
        client_id: token_resp
            .client_id
            .unwrap_or_else(|| creds.client_id.clone()),
        expires_at: Utc::now() + Duration::seconds(token_resp.expires_in),
    };

    Ok(new_creds)
}

pub async fn exchange_code_for_token(
    http_client: &reqwest::Client,
    token_url: &str,
    redirect_uri: &str,
    client_id: &str,
    code: &str,
    code_verifier: &str,
) -> Result<StoredCredentials> {
    let mut params = HashMap::new();
    params.insert("grant_type", "authorization_code");
    params.insert("code", code);
    params.insert("redirect_uri", redirect_uri);
    params.insert("client_id", client_id);
    params.insert("code_verifier", code_verifier);
    params.insert("resource", RESOURCE_URL);

    let resp = http_client
        .post(token_url)
        .form(&params)
        .send()
        .await
        .context("Failed to contact token endpoint for code exchange")?;

    let status = resp.status();
    let body = resp.text().await?;

    if !status.is_success() {
        return Err(anyhow!("Token exchange failed ({}): {}", status, body));
    }

    let token_resp: TokenResponse = serde_json::from_str(&body)
        .with_context(|| format!("Failed to parse token response: {}", body))?;

    Ok(StoredCredentials {
        access_token: token_resp.access_token,
        refresh_token: token_resp.refresh_token,
        client_id: token_resp
            .client_id
            .unwrap_or_else(|| client_id.to_string()),
        expires_at: Utc::now() + Duration::seconds(token_resp.expires_in),
    })
}

pub fn generate_pkce() -> (String, String) {
    let mut bytes = [0u8; 32];
    rand::thread_rng().fill_bytes(&mut bytes);
    let verifier = URL_SAFE_NO_PAD.encode(bytes);

    let mut hasher = Sha256::new();
    hasher.update(verifier.as_bytes());
    let challenge = URL_SAFE_NO_PAD.encode(hasher.finalize());

    (verifier, challenge)
}

pub fn generate_random_state() -> String {
    let mut bytes = [0u8; 24];
    rand::thread_rng().fill_bytes(&mut bytes);
    URL_SAFE_NO_PAD.encode(bytes)
}

pub async fn login(
    creds_path: &Path,
    auth_url: &str,
    token_url: &str,
    redirect_uri: &str,
    client_id: &str,
) -> Result<StoredCredentials> {
    let (code_verifier, code_challenge) = generate_pkce();
    let state = generate_random_state();

    let mut auth = Url::parse(auth_url)?;
    auth.query_pairs_mut()
        .append_pair("client_id", client_id)
        .append_pair("response_type", "code")
        .append_pair("redirect_uri", redirect_uri)
        .append_pair("scope", SCOPES)
        .append_pair("state", &state)
        .append_pair("code_challenge", &code_challenge)
        .append_pair("code_challenge_method", "S256")
        .append_pair("resource", RESOURCE_URL)
        .append_pair("prompt", "login");

    let parsed_redirect = Url::parse(redirect_uri)?;
    let listen_host = parsed_redirect.host_str().unwrap_or("127.0.0.1");
    let listen_port = parsed_redirect.port().unwrap_or(8080);
    let listen_addr = format!("{}:{}", listen_host, listen_port);

    let server = Server::http(&listen_addr)
        .map_err(|e| anyhow!("Failed to bind local HTTP server on {}: {}", listen_addr, e))?;

    println!("\n=== Sign in with ChatGPT (SIWC) Authorization Required ===");
    println!("Please open the following link in your browser to sign in:\n");
    println!("{}\n", auth.as_str());

    // Try opening browser automatically
    #[cfg(target_os = "windows")]
    {
        let _ = Command::new("rundll32")
            .args(["url.dll,FileProtocolHandler", auth.as_str()])
            .spawn();
    }
    #[cfg(target_os = "macos")]
    {
        let _ = Command::new("open").arg(auth.as_str()).spawn();
    }
    #[cfg(not(any(target_os = "windows", target_os = "macos")))]
    {
        let _ = Command::new("xdg-open").arg(auth.as_str()).spawn();
    }

    let (tx, rx) = mpsc::channel();
    let thread_state = state.clone();
    let expected_path = parsed_redirect.path().to_string();

    std::thread::spawn(move || {
        let deadline = std::time::Instant::now() + std::time::Duration::from_secs(300);
        while std::time::Instant::now() < deadline {
            if let Ok(Some(request)) = server.recv_timeout(std::time::Duration::from_millis(500)) {
                let req_url = format!("http://localhost{}", request.url());
                let parsed = match Url::parse(&req_url) {
                    Ok(u) => u,
                    Err(_) => continue,
                };

                if parsed.path() == expected_path {
                    let mut code = None;
                    let mut returned_state = None;
                    for (k, v) in parsed.query_pairs() {
                        if k == "code" {
                            code = Some(v.to_string());
                        } else if k == "state" {
                            returned_state = Some(v.to_string());
                        }
                    }

                    if let (Some(code), Some(returned_state)) = (code, returned_state) {
                        if returned_state != thread_state {
                            let _ = request.respond(Response::from_string("OAuth state mismatch. Please try again."));
                            continue;
                        }
                        let response = Response::from_string(
                            "Authentication successful! You can now close this tab and return to OpenCode.",
                        );
                        let _ = request.respond(response);
                        let _ = tx.send(code);
                        break;
                    }
                } else {
                    let _ = request.respond(Response::from_string("Not Found").with_status_code(404));
                }
            }
        }
    });

    let code = rx
        .recv_timeout(std::time::Duration::from_secs(310))
        .map_err(|_| anyhow!("Timed out waiting for OAuth callback authorization code"))?;

    let http_client = reqwest::Client::new();
    let creds = exchange_code_for_token(
        &http_client,
        token_url,
        redirect_uri,
        client_id,
        &code,
        &code_verifier,
    )
    .await?;

    save_credentials(creds_path, &creds)?;
    info!("Saved ChatGPT OAuth credentials to {:?}", creds_path);
    Ok(creds)
}
