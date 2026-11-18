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

const GOOGLE_AUTH_URL: &str = "https://accounts.google.com/o/oauth2/v2/auth";
const GOOGLE_TOKEN_URL: &str = "https://oauth2.googleapis.com/token";
const DEFAULT_REDIRECT_URI: &str = "http://127.0.0.1:8085/callback";
const STORAGE_FILE: &str = "test/data/google_gemini.json";

// Standard Google Gemini Generative Language scopes
const GOOGLE_SCOPES: &str = "https://www.googleapis.com/auth/generative-language https://www.googleapis.com/auth/cloud-platform";

#[derive(Debug, Serialize, Deserialize, Clone)]
struct StoredCredentials {
    access_token: String,
    refresh_token: Option<String>,
    client_id: String,
    client_secret: Option<String>,
    expires_at: DateTime<Utc>,
}

#[derive(Debug, Deserialize)]
struct TokenResponse {
    access_token: String,
    expires_in: i64,
    refresh_token: Option<String>,
}

#[derive(Debug, Serialize)]
struct ContentPart {
    text: String,
}

#[derive(Debug, Serialize)]
struct Content {
    parts: Vec<ContentPart>,
}

#[derive(Debug, Serialize)]
struct GenerateContentRequest {
    contents: Vec<Content>,
}

#[derive(Debug, Deserialize)]
struct CandidateContent {
    parts: Option<Vec<CandidatePart>>,
}

#[derive(Debug, Deserialize)]
struct CandidatePart {
    text: Option<String>,
}

#[derive(Debug, Deserialize)]
struct Candidate {
    content: Option<CandidateContent>,
}

#[derive(Debug, Deserialize)]
struct GenerateContentResponse {
    candidates: Option<Vec<Candidate>>,
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
    println!("Saved Google Gemini OAuth credentials to {}", STORAGE_FILE);
    Ok(())
}

async fn refresh_access_token(
    http_client: &reqwest::Client,
    creds: &StoredCredentials,
) -> Result<StoredCredentials> {
    let refresh_token = creds
        .refresh_token
        .as_ref()
        .ok_or_else(|| anyhow!("No refresh token present in credentials file"))?;

    let mut params = HashMap::new();
    params.insert("grant_type", "refresh_token");
    params.insert("refresh_token", refresh_token.as_str());
    params.insert("client_id", creds.client_id.as_str());

    if let Some(secret) = &creds.client_secret {
        params.insert("client_secret", secret.as_str());
    }

    let resp = http_client
        .post(GOOGLE_TOKEN_URL)
        .form(&params)
        .send()
        .await
        .context("Failed to contact Google token endpoint for refresh")?;

    let status = resp.status();
    let body = resp.text().await?;

    if !status.is_success() {
        return Err(anyhow!(
            "Google token refresh failed ({}): {}",
            status,
            body
        ));
    }

    let token_resp: TokenResponse = serde_json::from_str(&body)
        .with_context(|| format!("Failed to parse Google token response: {}", body))?;

    let new_creds = StoredCredentials {
        access_token: token_resp.access_token,
        refresh_token: token_resp
            .refresh_token
            .or_else(|| creds.refresh_token.clone()),
        client_id: creds.client_id.clone(),
        client_secret: creds.client_secret.clone(),
        expires_at: Utc::now() + Duration::seconds(token_resp.expires_in),
    };

    save_credentials(&new_creds)?;
    Ok(new_creds)
}

async fn run_google_oauth_flow(
    http_client: &reqwest::Client,
    client_id: &str,
    client_secret: Option<&str>,
    redirect_uri: &str,
) -> Result<StoredCredentials> {
    let state = generate_random_base64url(16);
    let (code_verifier, code_challenge) = generate_pkce();

    let mut auth_endpoint = Url::parse(GOOGLE_AUTH_URL)?;
    auth_endpoint
        .query_pairs_mut()
        .append_pair("client_id", client_id)
        .append_pair("response_type", "code")
        .append_pair("redirect_uri", redirect_uri)
        .append_pair("scope", GOOGLE_SCOPES)
        .append_pair("state", &state)
        .append_pair("code_challenge", &code_challenge)
        .append_pair("code_challenge_method", "S256")
        .append_pair("access_type", "offline")
        .append_pair("prompt", "consent");

    let parsed_redirect = Url::parse(redirect_uri)?;
    let host = parsed_redirect.host_str().unwrap_or("127.0.0.1");
    let port = parsed_redirect.port().unwrap_or(8085);
    let bind_addr = format!("{}:{}", host, port);

    println!("\n1. Please open the following URL in your browser to authorize with Google:");
    println!("{}\n", auth_endpoint);
    println!("Listening for callback on http://{} ...", bind_addr);

    let server = Server::http(&bind_addr)
        .map_err(|e| anyhow!("Failed to bind server on {}: {}", bind_addr, e))?;
    let (tx, rx) = mpsc::channel();

    let thread_state = state.clone();
    std::thread::spawn(move || {
        for request in server.incoming_requests() {
            let url_string = format!("http://127.0.0.1{}", request.url());
            if let Ok(req_url) = Url::parse(&url_string) {
                if req_url.path() == "/callback" {
                    let mut code = None;
                    let mut returned_state = None;

                    for (k, v) in req_url.query_pairs() {
                        if k == "code" {
                            code = Some(v.into_owned());
                        } else if k == "state" {
                            returned_state = Some(v.into_owned());
                        }
                    }

                    if let (Some(code), Some(returned_state)) = (code, returned_state) {
                        if returned_state != thread_state {
                            let _ = request.respond(Response::from_string("State mismatch"));
                            continue;
                        }
                        let response = Response::from_string(
                            "Google Authentication successful! You can now close this tab and return to the terminal.",
                        );
                        let _ = request.respond(response);
                        let _ = tx.send(code);
                        break;
                    }
                } else {
                    let _ = request.respond(Response::from_string(
                        "Waiting for Google OAuth callback...",
                    ));
                }
            }
        }
    });

    let code = rx
        .recv()
        .map_err(|_| anyhow!("Failed to receive authorization code from callback"))?;

    println!("Received Google authorization code! Exchanging for access token...");

    let mut params = HashMap::new();
    params.insert("grant_type", "authorization_code");
    params.insert("code", code.as_str());
    params.insert("redirect_uri", redirect_uri);
    params.insert("client_id", client_id);
    params.insert("code_verifier", code_verifier.as_str());

    if let Some(secret) = client_secret {
        params.insert("client_secret", secret);
    }

    let resp = http_client
        .post(GOOGLE_TOKEN_URL)
        .form(&params)
        .send()
        .await
        .context("Failed to exchange code at Google token endpoint")?;

    let status = resp.status();
    let body = resp.text().await?;

    if !status.is_success() {
        return Err(anyhow!(
            "Google token exchange failed ({}): {}",
            status,
            body
        ));
    }

    let token_resp: TokenResponse = serde_json::from_str(&body)
        .with_context(|| format!("Failed to parse Google token response: {}", body))?;

    let creds = StoredCredentials {
        access_token: token_resp.access_token,
        refresh_token: token_resp.refresh_token,
        client_id: client_id.to_string(),
        client_secret: client_secret.map(|s| s.to_string()),
        expires_at: Utc::now() + Duration::seconds(token_resp.expires_in),
    };

    save_credentials(&creds)?;
    Ok(creds)
}

#[tokio::main]
async fn main() -> Result<()> {
    dotenvy::dotenv().ok();
    dotenvy::from_filename("test/.env").ok();

    println!("=== Google OAuth Gemini Client ===");

    let client_id = std::env::var("GOOGLE_OAUTH_CLIENT_ID")
        .context("Missing GOOGLE_OAUTH_CLIENT_ID environment variable (create OAuth Desktop client in Google Cloud Console)")?;
    let client_secret = std::env::var("GOOGLE_OAUTH_CLIENT_SECRET").ok();
    let redirect_uri =
        std::env::var("GOOGLE_REDIRECT_URI").unwrap_or_else(|_| DEFAULT_REDIRECT_URI.to_string());

    let http_client = reqwest::Client::new();

    // 1. Check if we already have valid stored credentials
    let creds = match load_credentials() {
        Some(stored) => {
            println!(
                "Found cached Google credentials for client ID: {}",
                stored.client_id
            );
            if Utc::now() >= stored.expires_at - Duration::seconds(60) {
                println!("Token expired or nearing expiration. Attempting refresh...");
                match refresh_access_token(&http_client, &stored).await {
                    Ok(refreshed) => refreshed,
                    Err(e) => {
                        println!(
                            "Refresh failed ({}), starting fresh Google authorization flow...",
                            e
                        );
                        run_google_oauth_flow(
                            &http_client,
                            &client_id,
                            client_secret.as_deref(),
                            &redirect_uri,
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
            println!("No cached credentials found. Starting Google OAuth authorization...");
            run_google_oauth_flow(
                &http_client,
                &client_id,
                client_secret.as_deref(),
                &redirect_uri,
            )
            .await?
        }
    };

    println!("\nAccess token ready! Calling Gemini API (gemini-2.5-flash:generateContent)...");

    let model =
        std::env::var("GOOGLE_GEMINI_MODEL").unwrap_or_else(|_| "gemini-2.5-flash".to_string());
    let url = format!(
        "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent",
        model
    );

    let gen_req = GenerateContentRequest {
        contents: vec![Content {
            parts: vec![ContentPart {
                text: "Hello Gemini! Please reply with 'Hello from Google OAuth Gemini!' to confirm connection.".to_string(),
            }],
        }],
    };

    let api_response = http_client
        .post(&url)
        .bearer_auth(&creds.access_token)
        .json(&gen_req)
        .send()
        .await?;

    let status = api_response.status();
    println!("API Response Status: {}", status);

    let body_text = api_response.text().await?;
    if status.is_success() {
        if let Ok(parsed) = serde_json::from_str::<GenerateContentResponse>(&body_text) {
            let mut reply = String::new();
            if let Some(candidates) = parsed.candidates {
                for candidate in candidates {
                    if let Some(content) = candidate.content {
                        if let Some(parts) = content.parts {
                            for part in parts {
                                if let Some(t) = part.text {
                                    reply.push_str(&t);
                                }
                            }
                        }
                    }
                }
            }

            if !reply.is_empty() {
                println!("\nGemini Response:\n{}", reply);
            } else {
                println!("Response JSON:\n{}", body_text);
            }
        } else {
            println!("Response JSON:\n{}", body_text);
        }
    } else {
        println!("Error Response Body:\n{}", body_text);
    }

    Ok(())
}
