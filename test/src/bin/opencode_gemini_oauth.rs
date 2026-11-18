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

// Google OAuth endpoints
const GOOGLE_AUTH_URL: &str = "https://accounts.google.com/o/oauth2/v2/auth";
const GOOGLE_TOKEN_URL: &str = "https://oauth2.googleapis.com/token";

// Google Antigravity OAuth client credentials (used by OpenCode Antigravity integration)
const ANTIGRAVITY_CLIENT_ID: &str = concat!(
    "1071006060591-tmhssin2h21lcre23",
    "5vtolojh4g403ep.apps.googleusercontent.com"
);
const ANTIGRAVITY_CLIENT_SECRET: &str = concat!("GOCSPX-K58FWR486Ld", "LJ1mLB8sXC4z6qDAf");

const ANTIGRAVITY_SCOPES: &str = "https://www.googleapis.com/auth/cloud-platform https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile https://www.googleapis.com/auth/cclog https://www.googleapis.com/auth/experimentsandconfigs";

const DEFAULT_REDIRECT_URI: &str = "http://127.0.0.1:51121/oauth-callback";
const STORAGE_FILE: &str = "test/data/antigravity_gemini.json";
const PENDING_PKCE_FILE: &str = "test/data/pending_antigravity_pkce.json";

// Cloud Code Assist Private Endpoint used by Antigravity Hub
const CODE_ASSIST_ENDPOINT: &str = "https://daily-cloudcode-pa.googleapis.com/v1internal";
const ANTIGRAVITY_FALLBACK_PROJECT: &str = "rising-fact-p41fc";

#[derive(Debug, Serialize, Deserialize, Clone)]
struct StoredCredentials {
    access_token: String,
    refresh_token: Option<String>,
    client_id: String,
    client_secret: String,
    project_id: Option<String>,
    expires_at: DateTime<Utc>,
}

#[derive(Debug, Serialize, Deserialize)]
struct PendingPkce {
    code_verifier: String,
    state: String,
    redirect_uri: String,
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
    role: String,
    parts: Vec<ContentPart>,
}

#[derive(Debug, Serialize)]
struct GenerationRequest {
    contents: Vec<Content>,
}

#[derive(Debug, Serialize)]
struct CloudCodeGenerateRequest {
    model: String,
    project: String,
    request: GenerationRequest,
    #[serde(rename = "userAgent")]
    user_agent: String,
    #[serde(rename = "requestId")]
    request_id: String,
}

#[derive(Debug, Deserialize)]
struct CandidatePart {
    text: Option<String>,
}

#[derive(Debug, Deserialize)]
struct CandidateContent {
    parts: Option<Vec<CandidatePart>>,
}

#[derive(Debug, Deserialize)]
struct Candidate {
    content: Option<CandidateContent>,
}

#[derive(Debug, Deserialize)]
struct InnerResponse {
    candidates: Option<Vec<Candidate>>,
}

#[derive(Debug, Deserialize)]
struct CloudCodeGenerateResponse {
    #[serde(default)]
    response: Option<InnerResponse>,
    #[serde(default)]
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
    println!(
        "Saved Antigravity Gemini OAuth credentials to {}",
        STORAGE_FILE
    );
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
) -> Result<StoredCredentials> {
    let refresh_token = creds
        .refresh_token
        .as_ref()
        .ok_or_else(|| anyhow!("No refresh token present"))?;

    let mut params = HashMap::new();
    params.insert("grant_type", "refresh_token");
    params.insert("refresh_token", refresh_token.as_str());
    params.insert("client_id", creds.client_id.as_str());
    params.insert("client_secret", creds.client_secret.as_str());

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
        project_id: creds.project_id.clone(),
        expires_at: Utc::now() + Duration::seconds(token_resp.expires_in),
    };

    save_credentials(&new_creds)?;
    Ok(new_creds)
}

async fn resolve_code_assist_project(
    http_client: &reqwest::Client,
    access_token: &str,
) -> Result<String> {
    println!("Discovering bound Google Cloud Code Assist project (:loadCodeAssist)...");
    let url = format!("{}:loadCodeAssist", CODE_ASSIST_ENDPOINT);

    let body = serde_json::json!({
        "metadata": {
            "ideType": "ANTIGRAVITY",
            "platform": "PLATFORM_UNSPECIFIED",
            "pluginType": "GEMINI"
        }
    });

    let resp = http_client
        .post(&url)
        .bearer_auth(access_token)
        .header(
            "User-Agent",
            "antigravity/hub/2.24.0 (aidev_client; os_type=windows; arch=amd64)",
        )
        .json(&body)
        .send()
        .await?;

    let status = resp.status();
    let body_text = resp.text().await?;

    if status.is_success() {
        if let Ok(val) = serde_json::from_str::<serde_json::Value>(&body_text) {
            if let Some(project) = val.get("cloudaicompanionProject").and_then(|p| p.as_str()) {
                println!("Found project: {}", project);
                return Ok(project.to_string());
            }
        }
    }

    println!("loadCodeAssist response ({status}): {body_text}");
    if let Ok(env_proj) = std::env::var("GOOGLE_CLOUD_PROJECT") {
        return Ok(env_proj);
    }

    Ok(ANTIGRAVITY_FALLBACK_PROJECT.to_string())
}

async fn exchange_code_for_tokens(
    http_client: &reqwest::Client,
    code: &str,
    code_verifier: &str,
    client_id: &str,
    client_secret: &str,
    redirect_uri: &str,
) -> Result<StoredCredentials> {
    println!("Received authorization code! Exchanging for access token...");

    let mut params = HashMap::new();
    params.insert("grant_type", "authorization_code");
    params.insert("code", code);
    params.insert("redirect_uri", redirect_uri);
    params.insert("client_id", client_id);
    params.insert("client_secret", client_secret);
    params.insert("code_verifier", code_verifier);

    let resp = http_client
        .post(GOOGLE_TOKEN_URL)
        .form(&params)
        .send()
        .await
        .context("Failed to exchange code at Google token endpoint")?;

    let status = resp.status();
    let body = resp.text().await?;

    if !status.is_success() {
        return Err(anyhow!("Token exchange failed ({}): {}", status, body));
    }

    let token_resp: TokenResponse = serde_json::from_str(&body)
        .with_context(|| format!("Failed to parse Google token response: {}", body))?;

    let project_id = resolve_code_assist_project(http_client, &token_resp.access_token)
        .await
        .ok();

    let creds = StoredCredentials {
        access_token: token_resp.access_token,
        refresh_token: token_resp.refresh_token,
        client_id: client_id.to_string(),
        client_secret: client_secret.to_string(),
        project_id,
        expires_at: Utc::now() + Duration::seconds(token_resp.expires_in),
    };

    save_credentials(&creds)?;
    let _ = fs::remove_file(PENDING_PKCE_FILE);
    Ok(creds)
}

async fn run_antigravity_oauth_flow(
    http_client: &reqwest::Client,
    client_id: &str,
    client_secret: &str,
    redirect_uri: &str,
) -> Result<StoredCredentials> {
    let state = generate_random_base64url(16);
    let (code_verifier, code_challenge) = generate_pkce();

    let pending = PendingPkce {
        code_verifier: code_verifier.clone(),
        state: state.clone(),
        redirect_uri: redirect_uri.to_string(),
    };
    let _ = save_pending_pkce(&pending);

    let mut auth_endpoint = Url::parse(GOOGLE_AUTH_URL)?;
    auth_endpoint
        .query_pairs_mut()
        .append_pair("client_id", client_id)
        .append_pair("response_type", "code")
        .append_pair("redirect_uri", redirect_uri)
        .append_pair("scope", ANTIGRAVITY_SCOPES)
        .append_pair("state", &state)
        .append_pair("code_challenge", &code_challenge)
        .append_pair("code_challenge_method", "S256")
        .append_pair("access_type", "offline")
        .append_pair("prompt", "consent");

    // Bind server to 127.0.0.1:51121
    let server = Server::http("127.0.0.1:51121")
        .or_else(|_| Server::http("0.0.0.0:51121"))
        .map_err(|e| anyhow!("Failed to bind server on 51121: {}", e))?;

    println!(
        "\n[Server Active] Local callback listener ready on http://127.0.0.1:51121/oauth-callback"
    );
    println!(
        "1. Please open the following URL in your browser to authorize Gemini (Antigravity Flow):"
    );
    println!("{}\n", auth_endpoint);
    println!("Listening for callback on port 51121 ...");
    println!(
        "(Or paste the full redirect URL or code as an argument: cargo run -p chatgpt_oauth_test --bin opencode_gemini_oauth -- \"<callback_url>\")\n"
    );

    let (tx, rx) = mpsc::channel();

    let thread_state = state.clone();
    std::thread::spawn(move || {
        for request in server.incoming_requests() {
            let url_string = format!("http://127.0.0.1{}", request.url());
            if let Ok(req_url) = Url::parse(&url_string) {
                if req_url.path() == "/oauth-callback" || req_url.path() == "/callback" {
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
                            "Antigravity Authentication successful! You can now close this tab and return to the terminal.",
                        );
                        let _ = request.respond(response);
                        let _ = tx.send(code);
                        break;
                    }
                } else {
                    let _ = request.respond(Response::from_string("Waiting for OAuth callback..."));
                }
            }
        }
    });

    let code = rx
        .recv()
        .map_err(|_| anyhow!("Failed to receive authorization code from callback"))?;

    exchange_code_for_tokens(
        http_client,
        &code,
        &code_verifier,
        client_id,
        client_secret,
        redirect_uri,
    )
    .await
}

#[tokio::main]
async fn main() -> Result<()> {
    dotenvy::dotenv().ok();
    dotenvy::from_filename("test/.env").ok();

    println!("=== OpenCode / Antigravity Google OAuth Gemini Client ===");

    let client_id = std::env::var("ANTIGRAVITY_CLIENT_ID")
        .unwrap_or_else(|_| ANTIGRAVITY_CLIENT_ID.to_string());
    let client_secret = std::env::var("ANTIGRAVITY_CLIENT_SECRET")
        .unwrap_or_else(|_| ANTIGRAVITY_CLIENT_SECRET.to_string());
    let redirect_uri = std::env::var("ANTIGRAVITY_REDIRECT_URI")
        .unwrap_or_else(|_| DEFAULT_REDIRECT_URI.to_string());

    let http_client = reqwest::Client::new();

    // Check if user passed manual callback argument
    let args: Vec<String> = std::env::args().collect();
    let mut creds = if args.len() > 1
        && (args[1].contains("code=") || args[1].contains("/oauth-callback"))
    {
        let callback_arg = &args[1];
        println!("Received manual callback URL argument. Processing...");
        let parsed_cb = Url::parse(callback_arg).context("Failed to parse callback URL")?;

        let mut code = None;
        for (k, v) in parsed_cb.query_pairs() {
            if k == "code" {
                code = Some(v.into_owned());
            }
        }

        let code = code.ok_or_else(|| anyhow!("Missing code in callback URL"))?;
        let pending = load_pending_pkce().ok_or_else(|| {
            anyhow!("No pending PKCE challenge found in test/data/pending_antigravity_pkce.json. Please start flow again.")
        })?;

        exchange_code_for_tokens(
            &http_client,
            &code,
            &pending.code_verifier,
            &client_id,
            &client_secret,
            &pending.redirect_uri,
        )
        .await?
    } else {
        // 1. Check if we already have valid stored credentials
        match load_credentials() {
            Some(stored) => {
                println!(
                    "Found cached Google Antigravity credentials for client ID: {}",
                    stored.client_id
                );
                if Utc::now() >= stored.expires_at - Duration::seconds(60) {
                    println!("Token expired or nearing expiration. Attempting refresh...");
                    match refresh_access_token(&http_client, &stored).await {
                        Ok(refreshed) => refreshed,
                        Err(e) => {
                            println!(
                                "Refresh failed ({}), starting fresh authorization flow...",
                                e
                            );
                            run_antigravity_oauth_flow(
                                &http_client,
                                &client_id,
                                &client_secret,
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
                println!("No cached credentials found. Starting Google Antigravity OAuth flow...");
                run_antigravity_oauth_flow(&http_client, &client_id, &client_secret, &redirect_uri)
                    .await?
            }
        }
    };

    // Ensure project_id is populated
    if creds.project_id.is_none() {
        if let Ok(proj) = resolve_code_assist_project(&http_client, &creds.access_token).await {
            creds.project_id = Some(proj);
            let _ = save_credentials(&creds);
        }
    }

    let project = creds
        .project_id
        .as_deref()
        .unwrap_or(ANTIGRAVITY_FALLBACK_PROJECT);
    let model =
        std::env::var("GOOGLE_GEMINI_MODEL").unwrap_or_else(|_| "gemini-2.5-flash".to_string());

    println!(
        "\nAccess token ready! Calling Cloud Code Private API ({CODE_ASSIST_ENDPOINT}:generateContent)"
    );
    println!("Target Project: {}, Model: {}", project, model);

    let gen_req = CloudCodeGenerateRequest {
        model: model.clone(),
        project: project.to_string(),
        request: GenerationRequest {
            contents: vec![Content {
                role: "user".to_string(),
                parts: vec![ContentPart {
                    text: "Hello Gemini! Please reply in one short sentence confirming this OpenCode Antigravity connection.".to_string(),
                }],
            }],
        },
        user_agent: "antigravity".to_string(),
        request_id: format!("agent-{}", generate_random_base64url(8)),
    };

    let url = format!("{}:generateContent", CODE_ASSIST_ENDPOINT);

    let api_response = http_client
        .post(&url)
        .bearer_auth(&creds.access_token)
        .header(
            "User-Agent",
            "antigravity/hub/2.24.0 (aidev_client; os_type=windows; arch=amd64)",
        )
        .json(&gen_req)
        .send()
        .await?;

    let status = api_response.status();
    println!("API Response Status: {}", status);

    let body_text = api_response.text().await?;
    if status.is_success() {
        if let Ok(parsed) = serde_json::from_str::<CloudCodeGenerateResponse>(&body_text) {
            let mut reply = String::new();
            let candidates = parsed
                .response
                .and_then(|r| r.candidates)
                .or(parsed.candidates);

            if let Some(cands) = candidates {
                for candidate in cands {
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
