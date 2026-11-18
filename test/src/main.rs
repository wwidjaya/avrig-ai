use anyhow::{Context, Result, anyhow};
use base64::Engine;
use base64::engine::general_purpose::URL_SAFE_NO_PAD;
use chrono::{DateTime, Duration, Utc};
use rand::RngCore;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::HashMap;
use std::fs;
use std::path::Path;
use std::sync::mpsc;
use tiny_http::{Response, Server};
use url::Url;

const DEFAULT_AUTH_URL: &str = "https://auth.openai.com/api/accounts/authorize";
const DEFAULT_TOKEN_URL: &str = "https://auth.openai.com/api/accounts/oauth/token";
const DEFAULT_REDIRECT_URI: &str = "http://127.0.0.1:8080/callback";
const RESOURCE_URL: &str = "https://api.openai.com/v1";
const DYNAMIC_CLIENT_ID: &str = "dynamic_agent_client";
const SCOPES: &str =
    "openid profile email offline_access resource.invoke chatgpt.tokens.use.direct";
const STORAGE_FILE: &str = "test/data/chatgpt.json";
const PENDING_PKCE_FILE: &str = "test/data/pending_pkce.json";

#[derive(Debug, Serialize, Deserialize, Clone)]
struct StoredCredentials {
    access_token: String,
    refresh_token: Option<String>,
    client_id: String,
    expires_at: DateTime<Utc>,
}

#[derive(Debug, Serialize, Deserialize)]
struct PendingPkce {
    code_verifier: String,
    state: String,
    redirect_uri: String,
    created_at: DateTime<Utc>,
}

#[derive(Debug, Deserialize)]
struct TokenResponse {
    access_token: String,
    expires_in: i64,
    refresh_token: Option<String>,
    client_id: Option<String>,
}

#[derive(Debug, Serialize)]
struct InputMessage {
    role: String,
    content: String,
}

#[derive(Debug, Serialize)]
struct ResponsesRequest {
    model: String,
    input: Vec<InputMessage>,
    store: bool,
    stream: bool,
}

#[derive(Debug, Deserialize)]
struct ResponsesContent {
    #[serde(default)]
    text: Option<String>,
}

#[derive(Debug, Deserialize)]
struct ResponsesOutputItem {
    #[serde(default)]
    content: Option<Vec<ResponsesContent>>,
    #[serde(default)]
    text: Option<String>,
}

#[derive(Debug, Deserialize)]
struct ResponsesResponse {
    #[serde(default)]
    output_text: Option<String>,
    #[serde(default)]
    output: Option<Vec<ResponsesOutputItem>>,
}

fn generate_random_base64url(bytes: usize) -> String {
    let mut buffer = vec![0u8; bytes];
    rand::thread_rng().fill_bytes(&mut buffer);
    URL_SAFE_NO_PAD.encode(buffer)
}

fn generate_pkce() -> (String, String) {
    let verifier = generate_random_base64url(32);
    let mut hasher = Sha256::new();
    hasher.update(verifier.as_bytes());
    let hash = hasher.finalize();
    let challenge = URL_SAFE_NO_PAD.encode(hash);
    (verifier, challenge)
}

fn load_credentials() -> Option<StoredCredentials> {
    if let Ok(data) = fs::read_to_string(STORAGE_FILE) {
        if let Ok(creds) = serde_json::from_str::<StoredCredentials>(&data) {
            return Some(creds);
        }
    }
    None
}

fn save_credentials(creds: &StoredCredentials) -> Result<()> {
    if let Some(parent) = Path::new(STORAGE_FILE).parent() {
        fs::create_dir_all(parent)?;
    }
    let data = serde_json::to_string_pretty(creds)?;
    fs::write(STORAGE_FILE, data)?;
    println!("Saved ChatGPT OAuth credentials to {}", STORAGE_FILE);
    Ok(())
}

fn save_pending_pkce(pending: &PendingPkce) -> Result<()> {
    if let Some(parent) = Path::new(PENDING_PKCE_FILE).parent() {
        fs::create_dir_all(parent)?;
    }
    let data = serde_json::to_string_pretty(pending)?;
    fs::write(PENDING_PKCE_FILE, data)?;
    Ok(())
}

fn load_pending_pkce() -> Option<PendingPkce> {
    if let Ok(data) = fs::read_to_string(PENDING_PKCE_FILE) {
        if let Ok(pending) = serde_json::from_str::<PendingPkce>(&data) {
            return Some(pending);
        }
    }
    None
}

async fn refresh_access_token(
    http_client: &reqwest::Client,
    creds: &StoredCredentials,
    token_url: &str,
) -> Result<StoredCredentials> {
    let refresh_token = creds
        .refresh_token
        .as_ref()
        .ok_or_else(|| anyhow!("No refresh token present"))?;

    let mut params = HashMap::new();
    params.insert("grant_type", "refresh_token");
    params.insert("refresh_token", refresh_token.as_str());
    params.insert("client_id", creds.client_id.as_str());
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

    save_credentials(&new_creds)?;
    Ok(new_creds)
}

async fn exchange_code_for_token(
    http_client: &reqwest::Client,
    token_url: &str,
    code: &str,
    code_verifier: &str,
    client_id: &str,
    redirect_uri: &str,
) -> Result<StoredCredentials> {
    let mut params = HashMap::new();
    params.insert("grant_type", "authorization_code");
    params.insert("code", code);
    params.insert("redirect_uri", redirect_uri);
    params.insert("client_id", client_id);
    params.insert("resource", RESOURCE_URL);
    params.insert("code_verifier", code_verifier);

    let resp = http_client
        .post(token_url)
        .form(&params)
        .send()
        .await
        .context("Failed to exchange code at token endpoint")?;

    let status = resp.status();
    let body = resp.text().await?;

    if !status.is_success() {
        return Err(anyhow!("Token exchange failed ({}): {}", status, body));
    }

    let token_resp: TokenResponse = serde_json::from_str(&body)
        .with_context(|| format!("Failed to parse token response: {}", body))?;

    let effective_client_id = token_resp
        .client_id
        .unwrap_or_else(|| client_id.to_string());

    let creds = StoredCredentials {
        access_token: token_resp.access_token,
        refresh_token: token_resp.refresh_token,
        client_id: effective_client_id,
        expires_at: Utc::now() + Duration::seconds(token_resp.expires_in),
    };

    save_credentials(&creds)?;
    let _ = fs::remove_file(PENDING_PKCE_FILE);
    Ok(creds)
}

async fn run_oauth_flow(
    http_client: &reqwest::Client,
    auth_url: &str,
    token_url: &str,
    redirect_uri: &str,
    initial_client_id: &str,
) -> Result<StoredCredentials> {
    let state = generate_random_base64url(16);
    let (code_verifier, code_challenge) = generate_pkce();

    // Persist pending PKCE verifier so manual exchange works if browser was opened separately
    let pending = PendingPkce {
        code_verifier: code_verifier.clone(),
        state: state.clone(),
        redirect_uri: redirect_uri.to_string(),
        created_at: Utc::now(),
    };
    let _ = save_pending_pkce(&pending);

    let mut auth_endpoint = Url::parse(auth_url)?;
    auth_endpoint
        .query_pairs_mut()
        .append_pair("client_id", initial_client_id)
        .append_pair("response_type", "code")
        .append_pair("redirect_uri", redirect_uri)
        .append_pair("scope", SCOPES)
        .append_pair("state", &state)
        .append_pair("code_challenge", &code_challenge)
        .append_pair("code_challenge_method", "S256")
        .append_pair("resource", RESOURCE_URL)
        .append_pair("agent_name_hint", "Avrig Agent")
        .append_pair(
            "ext_agent_host_id",
            "urn:uuid:68ae5192-8214-4d32-b036-592917978280",
        );

    let parsed_redirect = Url::parse(redirect_uri)?;
    let host = parsed_redirect.host_str().unwrap_or("127.0.0.1");
    let port = parsed_redirect.port().unwrap_or(8080);
    let bind_addr = format!("{}:{}", host, port);

    println!("\n1. Please open the following URL in your browser to authorize with ChatGPT:");
    println!("{}\n", auth_endpoint);
    println!("Listening for callback on http://{} ...", bind_addr);
    println!("(Or run: cargo run -p chatgpt_oauth_test -- \"<callback_url>\" if pasted manually)");

    let server = Server::http(&bind_addr).map_err(|e| anyhow!("Failed to bind server: {}", e))?;
    let (tx, rx) = mpsc::channel();

    let thread_state = state.clone();
    std::thread::spawn(move || {
        for request in server.incoming_requests() {
            let url_string = format!("http://127.0.0.1{}", request.url());
            if let Ok(req_url) = Url::parse(&url_string) {
                if req_url.path() == "/callback" {
                    let mut code = None;
                    let mut returned_state = None;
                    let mut cb_client_id = None;

                    for (k, v) in req_url.query_pairs() {
                        if k == "code" {
                            code = Some(v.into_owned());
                        } else if k == "state" {
                            returned_state = Some(v.into_owned());
                        } else if k == "client_id" {
                            cb_client_id = Some(v.into_owned());
                        }
                    }

                    if let (Some(code), Some(returned_state)) = (code, returned_state) {
                        if returned_state != thread_state {
                            println!(
                                "Warning: browser sent state '{}' from an older tab, waiting for current state '{}'...",
                                returned_state, thread_state
                            );
                            let _ = request.respond(Response::from_string("Older request detected. Please open the latest authorization link in the terminal."));
                            continue;
                        }
                        let response = Response::from_string(
                            "Authentication successful! You can now close this tab and return to the terminal.",
                        );
                        let _ = request.respond(response);
                        let _ = tx.send((code, returned_state, cb_client_id));
                        break;
                    }
                } else {
                    let _ = request.respond(Response::from_string("Waiting for OAuth callback..."));
                }
            } else {
                let _ = request.respond(Response::from_string("Invalid request URL"));
            }
        }
    });

    let (code, _returned_state, cb_client_id) = rx
        .recv()
        .map_err(|_| anyhow!("Failed to receive authorization code from callback"))?;

    println!("Received authorization code! Exchanging for access token...");

    let client_id_to_exchange = cb_client_id
        .clone()
        .unwrap_or_else(|| initial_client_id.to_string());

    exchange_code_for_token(
        http_client,
        token_url,
        &code,
        &code_verifier,
        &client_id_to_exchange,
        redirect_uri,
    )
    .await
}

#[tokio::main]
async fn main() -> Result<()> {
    dotenvy::dotenv().ok();
    dotenvy::from_filename("test/.env").ok();

    println!("=== Sign in with ChatGPT (SIWC) OAuth Client ===");

    let auth_url =
        std::env::var("OPENAI_AUTH_URL").unwrap_or_else(|_| DEFAULT_AUTH_URL.to_string());
    let token_url =
        std::env::var("OPENAI_TOKEN_URL").unwrap_or_else(|_| DEFAULT_TOKEN_URL.to_string());
    let redirect_uri =
        std::env::var("OPENAI_REDIRECT_URL").unwrap_or_else(|_| DEFAULT_REDIRECT_URI.to_string());
    let client_id_env =
        std::env::var("OPENAI_OAUTH_CLIENT_ID").unwrap_or_else(|_| DYNAMIC_CLIENT_ID.to_string());

    let http_client = reqwest::Client::new();

    // Check if user passed the callback URL directly via CLI argument
    let args: Vec<String> = std::env::args().collect();
    let creds = if args.len() > 1 && (args[1].contains("code=") || args[1].contains("/callback")) {
        let callback_arg = &args[1];
        println!("Received manual callback URL argument. Processing...");
        let parsed_cb = Url::parse(callback_arg).context("Failed to parse callback URL")?;

        let mut code = None;
        let mut state = None;
        let mut client_id = None;

        for (k, v) in parsed_cb.query_pairs() {
            if k == "code" {
                code = Some(v.into_owned());
            } else if k == "state" {
                state = Some(v.into_owned());
            } else if k == "client_id" {
                client_id = Some(v.into_owned());
            }
        }

        let code = code.ok_or_else(|| anyhow!("Missing code in callback URL"))?;
        let pending = load_pending_pkce().ok_or_else(|| {
            anyhow!("No pending PKCE challenge found in test/data/pending_pkce.json. Please start flow again.")
        })?;

        if let Some(st) = state {
            if st != pending.state {
                println!(
                    "Warning: callback state mismatch (pending: {}, callback: {})",
                    pending.state, st
                );
            }
        }

        let effective_cid = client_id.unwrap_or(client_id_env);
        exchange_code_for_token(
            &http_client,
            &token_url,
            &code,
            &pending.code_verifier,
            &effective_cid,
            &pending.redirect_uri,
        )
        .await?
    } else {
        // 1. Check if we already have valid stored credentials
        match load_credentials() {
            Some(stored) => {
                println!(
                    "Found cached credentials for client ID: {}",
                    stored.client_id
                );
                if Utc::now() >= stored.expires_at - Duration::seconds(60) {
                    println!("Token expired or nearing expiration. Attempting refresh...");
                    match refresh_access_token(&http_client, &stored, &token_url).await {
                        Ok(refreshed) => refreshed,
                        Err(e) => {
                            println!(
                                "Refresh failed ({}), starting fresh authorization flow...",
                                e
                            );
                            run_oauth_flow(
                                &http_client,
                                &auth_url,
                                &token_url,
                                &redirect_uri,
                                &stored.client_id,
                            )
                            .await?
                        }
                    }
                } else {
                    println!("Access token is valid until: {}", stored.expires_at);
                    stored
                }
            }
            None => {
                println!(
                    "No cached credentials found. Starting Sign in with ChatGPT authorization..."
                );
                run_oauth_flow(
                    &http_client,
                    &auth_url,
                    &token_url,
                    &redirect_uri,
                    &client_id_env,
                )
                .await?
            }
        }
    };

    let model_name = std::env::var("OPENAI_MODEL").unwrap_or_else(|_| "gpt-5.6-luna".to_string());
    println!(
        "\nAccess token ready! Calling OpenAI Responses API (/v1/responses) with model: {}...",
        model_name
    );

    let responses_req = ResponsesRequest {
        model: model_name,
        input: vec![InputMessage {
            role: "user".to_string(),
            content: "Hello! Please reply with 'Hello from ChatGPT SIWC!' to confirm connection."
                .to_string(),
        }],
        store: false,
        stream: true,
    };

    let api_response = http_client
        .post("https://api.openai.com/v1/responses")
        .bearer_auth(&creds.access_token)
        .json(&responses_req)
        .send()
        .await?;

    let status = api_response.status();
    println!("API Response Status: {}", status);

    let body_text = api_response.text().await?;
    if status.is_success() {
        // Collect streamed delta or output text lines
        let mut final_text = String::new();
        for line in body_text.lines() {
            if let Some(json_str) = line.strip_prefix("data: ") {
                if let Ok(val) = serde_json::from_str::<serde_json::Value>(json_str) {
                    if let Some(delta) = val.get("delta").and_then(|d| d.as_str()) {
                        final_text.push_str(delta);
                    } else if let Some(text) = val.get("text").and_then(|t| t.as_str()) {
                        if final_text.is_empty() {
                            final_text = text.to_string();
                        }
                    }
                }
            }
        }

        if !final_text.is_empty() {
            println!("\nChatGPT Response:\n{}", final_text);
        } else {
            println!("Response Stream:\n{}", body_text);
        }
    } else {
        println!("Error Response Body:\n{}", body_text);
    }

    Ok(())
}
