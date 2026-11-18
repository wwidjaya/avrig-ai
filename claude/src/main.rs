use anyhow::{Context, Result, anyhow};
use base64::Engine;
use base64::engine::general_purpose::{STANDARD as BASE64_STANDARD, URL_SAFE_NO_PAD};
use chrono::{DateTime, Duration, Utc};
use clap::{Parser, Subcommand};
use rand::RngCore;
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::fs;
use std::io::{self, Write};
use std::path::{Path, PathBuf};
use std::process::Command;
use std::sync::mpsc;
use std::time::Duration as StdDuration;
use tiny_http::{Header, Response, Server};
use tracing::info;
use url::Url;

pub const DEFAULT_CLIENT_ID: &str = "9d1c250a-e61b-44d9-88ed-5944d1962f5e";
pub const AUTH_URL: &str = "https://claude.ai/oauth/authorize";
pub const CONSOLE_AUTH_URL: &str = "https://platform.claude.com/oauth/authorize";
pub const TOKEN_URL: &str = "https://platform.claude.com/v1/oauth/token";
pub const MANUAL_REDIRECT_URI: &str = "https://platform.claude.com/oauth/code/callback";
pub const API_BASE_URL: &str = "https://api.anthropic.com";
pub const ANTHROPIC_VERSION: &str = "2023-06-01";
pub const OAUTH_BETA_HEADER: &str = "oauth-2025-04-20";
pub const DEFAULT_MODEL: &str = "claude-sonnet-4-20250514";

pub const SCOPES: &[&str] = &[
    "org:create_api_key",
    "user:profile",
    "user:inference",
    "user:sessions:claude_code",
];

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ClaudeOAuthCredentials {
    pub access_token: String,
    #[serde(default)]
    pub refresh_token: String,
    pub expires_at: DateTime<Utc>,
    #[serde(default)]
    pub client_id: String,
    #[serde(default)]
    pub scopes: Vec<String>,
    #[serde(default)]
    pub source: String,
}

#[derive(Parser, Debug)]
#[command(name = "claude-oauth", about = "Access Claude API via OAuth 2.0 PKCE or Claude Desktop session")]
struct Cli {
    /// Path to the OAuth credentials file
    #[arg(long, default_value = "claude/.claude-oauth.json")]
    creds: PathBuf,

    #[command(subcommand)]
    command: Option<Commands>,
}

#[derive(Subcommand, Debug)]
enum Commands {
    /// Authenticate with Claude via OAuth 2.0 PKCE in browser
    Login {
        /// Use manual copy-paste code flow instead of local callback server
        #[arg(long)]
        manual: bool,
        /// Use platform.claude.com instead of claude.ai for authorization
        #[arg(long)]
        console: bool,
        /// Local port for OAuth callback (when not using --manual)
        #[arg(long, default_value_t = 54545)]
        port: u16,
    },
    /// Import OAuth token from the installed Claude Desktop app (read-only on Desktop app files)
    ImportDesktop,
    /// Show current OAuth token status
    Status,
    /// Force refresh the OAuth access token
    Refresh,
    /// Send a chat message to Claude via OAuth (optionally testing tool calls)
    Chat {
        /// Prompt message to send
        #[arg(default_value = "What is the current weather in Tokyo? Use the get_weather tool.")]
        prompt: String,
        /// Claude model ID
        #[arg(short, long, default_value = DEFAULT_MODEL)]
        model: String,
        /// Enable sample tool definition (get_weather) and execute tool loop
        #[arg(long, default_value_t = true)]
        with_tools: bool,
        /// Max output tokens
        #[arg(long, default_value_t = 1024)]
        max_tokens: u32,
    },
}

#[tokio::main]
async fn main() -> Result<()> {
    let _ = dotenvy::dotenv();
    tracing_subscriber::fmt::init();

    let cli = Cli::parse();
    let creds_path = resolve_creds_path(&cli.creds);

    match cli.command.unwrap_or(Commands::Chat {
        prompt: "What is the current weather in Tokyo? Use the get_weather tool.".to_string(),
        model: DEFAULT_MODEL.to_string(),
        with_tools: true,
        max_tokens: 1024,
    }) {
        Commands::Login {
            manual,
            console,
            port,
        } => {
            let auth_base = if console { CONSOLE_AUTH_URL } else { AUTH_URL };
            let creds = oauth_login(&creds_path, DEFAULT_CLIENT_ID, auth_base, manual, port).await?;
            println!("Successfully authenticated with Claude OAuth!");
            println!("Credentials saved to: {}", creds_path.display());
            println!("Expires at: {}", creds.expires_at.to_rfc3339());
        }
        Commands::ImportDesktop => {
            let creds = extract_desktop_oauth_token()?;
            save_credentials(&creds_path, &creds)?;
            println!("Successfully imported OAuth session token from Claude Desktop!");
            println!("Saved to isolated file: {}", creds_path.display());
            println!("Token prefix          : {}...", &creds.access_token[..16.min(creds.access_token.len())]);
            println!("Expires at            : {}", creds.expires_at.to_rfc3339());
        }
        Commands::Status => {
            match load_or_extract_credentials(&creds_path) {
                Ok(creds) => {
                    let now = Utc::now();
                    let valid = creds.expires_at > now;
                    println!("Credentials file : {}", creds_path.display());
                    println!("Source           : {}", if creds.source.is_empty() { "oauth" } else { &creds.source });
                    println!("Status           : {}", if valid { "Valid" } else { "Expired (needs refresh)" });
                    println!("Token prefix     : {}...", &creds.access_token[..16.min(creds.access_token.len())]);
                    println!("Expires at       : {}", creds.expires_at.to_rfc3339());
                    println!("Has refresh token: {}", !creds.refresh_token.is_empty());
                    println!("Scopes           : {}", creds.scopes.join(" "));
                }
                Err(e) => {
                    println!("Not logged in ({})", e);
                    println!("Run `cargo run -p claude -- import-desktop` or `cargo run -p claude -- login`.");
                }
            }
        }
        Commands::Refresh => {
            let creds = load_credentials(&creds_path)?;
            let refreshed = refresh_access_token(&creds_path, &creds).await?;
            println!("Token refreshed successfully!");
            println!("New expiry: {}", refreshed.expires_at.to_rfc3339());
        }
        Commands::Chat {
            prompt,
            model,
            with_tools,
            max_tokens,
        } => {
            let creds = ensure_valid_credentials(&creds_path).await?;
            run_chat(&creds.access_token, &model, &prompt, with_tools, max_tokens).await?;
        }
    }

    Ok(())
}

fn resolve_creds_path(configured: &Path) -> PathBuf {
    if configured.exists() {
        return configured.to_path_buf();
    }
    let local_fallback = PathBuf::from(".claude-oauth.json");
    if local_fallback.exists() {
        return local_fallback;
    }
    configured.to_path_buf()
}

pub fn load_credentials(creds_path: &Path) -> Result<ClaudeOAuthCredentials> {
    if creds_path.exists() {
        let data = fs::read_to_string(creds_path)
            .with_context(|| format!("failed to read credentials file: {}", creds_path.display()))?;
        let creds: ClaudeOAuthCredentials = serde_json::from_str(&data)
            .with_context(|| format!("failed to parse credentials file: {}", creds_path.display()))?;
        return Ok(creds);
    }

    Err(anyhow!("credentials file not found at {}", creds_path.display()))
}

pub fn load_or_extract_credentials(creds_path: &Path) -> Result<ClaudeOAuthCredentials> {
    if let Ok(creds) = load_credentials(creds_path) {
        if creds.expires_at > Utc::now() {
            return Ok(creds);
        }
    }

    // Try extracting read-only from Claude Desktop session cache and saving to our isolated file
    if let Ok(desktop_creds) = extract_desktop_oauth_token() {
        let _ = save_credentials(creds_path, &desktop_creds);
        return Ok(desktop_creds);
    }

    load_credentials(creds_path)
}

#[cfg(target_os = "windows")]
fn dpapi_unprotect(encrypted: &[u8]) -> Result<Vec<u8>> {
    use windows_sys::Win32::Foundation::LocalFree;
    use windows_sys::Win32::Security::Cryptography::{CRYPT_INTEGER_BLOB, CryptUnprotectData};

    let mut in_blob = CRYPT_INTEGER_BLOB {
        cbData: encrypted.len() as u32,
        pbData: encrypted.as_ptr() as *mut u8,
    };
    let mut out_blob = CRYPT_INTEGER_BLOB {
        cbData: 0,
        pbData: std::ptr::null_mut(),
    };

    let ok = unsafe {
        CryptUnprotectData(
            &mut in_blob,
            std::ptr::null_mut(),
            std::ptr::null(),
            std::ptr::null_mut(),
            std::ptr::null(),
            0,
            &mut out_blob,
        )
    };

    if ok == 0 {
        return Err(anyhow!("CryptUnprotectData failed"));
    }

    let slice = unsafe { std::slice::from_raw_parts(out_blob.pbData, out_blob.cbData as usize) };
    let result = slice.to_vec();
    unsafe {
        LocalFree(out_blob.pbData as *mut core::ffi::c_void);
    }
    Ok(result)
}

#[cfg(not(target_os = "windows"))]
fn dpapi_unprotect(_encrypted: &[u8]) -> Result<Vec<u8>> {
    Err(anyhow!("Claude Desktop DPAPI extraction is only supported on Windows"))
}

pub fn extract_desktop_oauth_token() -> Result<ClaudeOAuthCredentials> {
    use aes_gcm::{
        Aes256Gcm, Nonce,
        aead::{Aead, KeyInit},
    };

    let local_app_data = std::env::var("LOCALAPPDATA")
        .or_else(|_| {
            std::env::var("USERPROFILE").map(|p| format!("{}\\AppData\\Local", p))
        })
        .context("LOCALAPPDATA not found")?;

    let base_dir = PathBuf::from(&local_app_data);
    let candidate_dirs = [
        base_dir.join("Claude-Data").join("claude_pzs8sxrjxfjjc"),
        base_dir.join("Packages").join("Claude_pzs8sxrjxfjjc").join("LocalCache").join("Roaming").join("Claude"),
        base_dir.join("AnthropicClaude"),
    ];

    let mut found_dir = None;
    for dir in &candidate_dirs {
        if dir.join("Local State").exists() && dir.join("config.json").exists() {
            found_dir = Some(dir.clone());
            break;
        }
    }

    let desktop_dir = found_dir.ok_or_else(|| {
        anyhow!("Claude Desktop data directory with Local State and config.json not found")
    })?;

    let local_state_str = fs::read_to_string(desktop_dir.join("Local State"))
        .context("failed to read Claude Desktop Local State")?;
    let local_state: Value = serde_json::from_str(&local_state_str)?;
    let enc_key_b64 = local_state
        .get("os_crypt")
        .and_then(|v| v.get("encrypted_key"))
        .and_then(|v| v.as_str())
        .ok_or_else(|| anyhow!("os_crypt.encrypted_key not found in Local State"))?;

    let enc_key_bytes = BASE64_STANDARD.decode(enc_key_b64)?;
    if enc_key_bytes.len() <= 5 || &enc_key_bytes[..5] != b"DPAPI" {
        return Err(anyhow!("unexpected os_crypt encrypted_key prefix"));
    }

    let master_key = dpapi_unprotect(&enc_key_bytes[5..])?;

    let config_str = fs::read_to_string(desktop_dir.join("config.json"))
        .context("failed to read Claude Desktop config.json")?;
    let config_json: Value = serde_json::from_str(&config_str)?;
    let token_cache_b64 = config_json
        .get("oauth:tokenCache")
        .and_then(|v| v.as_str())
        .ok_or_else(|| anyhow!("oauth:tokenCache not found in Claude Desktop config.json"))?;

    let blob = BASE64_STANDARD.decode(token_cache_b64)?;
    if blob.len() < 3 + 12 + 16 || &blob[..3] != b"v10" {
        return Err(anyhow!("unexpected oauth:tokenCache encryption format"));
    }

    let nonce = Nonce::from_slice(&blob[3..15]);
    let ciphertext_with_tag = &blob[15..];

    let cipher = Aes256Gcm::new_from_slice(&master_key)
        .map_err(|e| anyhow!("invalid AES-256-GCM key: {}", e))?;
    let plaintext = cipher
        .decrypt(nonce, ciphertext_with_tag)
        .map_err(|e| anyhow!("failed to decrypt oauth:tokenCache: {}", e))?;

    let cache_json: Value = serde_json::from_slice(&plaintext)?;
    let obj = cache_json
        .as_object()
        .ok_or_else(|| anyhow!("decrypted oauth:tokenCache is not a JSON object"))?;

    for (key, entry) in obj {
        if let Some(token) = entry.get("token").and_then(|v| v.as_str()) {
            if !token.is_empty() {
                let expires_ms = entry
                    .get("expiresAt")
                    .and_then(|v| v.as_i64())
                    .unwrap_or(0);
                let expires_at = DateTime::from_timestamp_millis(expires_ms)
                    .unwrap_or_else(|| Utc::now() + Duration::hours(24));

                let scopes: Vec<String> = key
                    .split(':')
                    .skip(4)
                    .map(String::from)
                    .collect();

                return Ok(ClaudeOAuthCredentials {
                    access_token: token.to_string(),
                    refresh_token: String::new(),
                    expires_at,
                    client_id: DEFAULT_CLIENT_ID.to_string(),
                    scopes: if scopes.is_empty() {
                        vec!["user:inference".to_string()]
                    } else {
                        scopes
                    },
                    source: "claude-desktop".to_string(),
                });
            }
        }
    }

    Err(anyhow!("no valid OAuth token entry found in Claude Desktop oauth:tokenCache"))
}

pub fn save_credentials(creds_path: &Path, creds: &ClaudeOAuthCredentials) -> Result<()> {
    if let Some(parent) = creds_path.parent() {
        if !parent.as_os_str().is_empty() {
            fs::create_dir_all(parent)?;
        }
    }
    let data = serde_json::to_string_pretty(creds)?;
    fs::write(creds_path, data)?;
    Ok(())
}

pub async fn ensure_valid_credentials(creds_path: &Path) -> Result<ClaudeOAuthCredentials> {
    if let Ok(creds) = load_or_extract_credentials(creds_path) {
        if (creds.expires_at - Utc::now()) >= Duration::seconds(60) {
            return Ok(creds);
        }
        if !creds.refresh_token.is_empty() {
            info!("Access token expired or expiring soon. Refreshing...");
            return refresh_access_token(creds_path, &creds).await;
        }
    }

    info!("No valid local or Claude Desktop token found. Starting OAuth PKCE login flow...");
    oauth_login(creds_path, DEFAULT_CLIENT_ID, AUTH_URL, false, 54545).await
}

pub async fn oauth_login(
    creds_path: &Path,
    client_id: &str,
    auth_base_url: &str,
    manual: bool,
    port: u16,
) -> Result<ClaudeOAuthCredentials> {
    let mut verifier_bytes = [0u8; 32];
    rand::thread_rng().fill_bytes(&mut verifier_bytes);
    let verifier = URL_SAFE_NO_PAD.encode(verifier_bytes);

    let mut hasher = Sha256::new();
    hasher.update(verifier.as_bytes());
    let challenge = URL_SAFE_NO_PAD.encode(hasher.finalize());

    let mut state_bytes = [0u8; 32];
    rand::thread_rng().fill_bytes(&mut state_bytes);
    let state = URL_SAFE_NO_PAD.encode(state_bytes);

    let redirect_uri = if manual {
        MANUAL_REDIRECT_URI.to_string()
    } else {
        format!("http://localhost:{}/callback", port)
    };

    let mut auth_url = Url::parse(auth_base_url)?;
    {
        let mut qp = auth_url.query_pairs_mut();
        if manual {
            qp.append_pair("code", "true");
        }
        qp.append_pair("client_id", client_id)
            .append_pair("response_type", "code")
            .append_pair("redirect_uri", &redirect_uri)
            .append_pair("scope", &SCOPES.join(" "))
            .append_pair("code_challenge", &challenge)
            .append_pair("code_challenge_method", "S256")
            .append_pair("state", &state);
    }

    let auth_url_str = auth_url.to_string();

    if manual {
        println!("\nOpen the following URL in your browser to authenticate with Claude:\n\n  {}\n", auth_url_str);
        open_browser(&auth_url_str);
        print!("Paste the authorization code (format: code#state or code): ");
        io::stdout().flush()?;
        let mut input = String::new();
        io::stdin().read_line(&mut input)?;
        let raw = input.trim();
        let (code, returned_state) = if let Some((c, s)) = raw.split_once('#') {
            (c.to_string(), Some(s.to_string()))
        } else {
            (raw.to_string(), None)
        };
        if let Some(ref s) = returned_state {
            if s != &state {
                return Err(anyhow!("OAuth state mismatch"));
            }
        }
        return exchange_code(
            creds_path,
            client_id,
            &code,
            returned_state.as_deref().unwrap_or(&state),
            &verifier,
            &redirect_uri,
        )
        .await;
    }

    let bind_addr = format!("127.0.0.1:{}", port);
    let server = Server::http(&bind_addr)
        .map_err(|e| anyhow!("failed to bind local OAuth callback server on {}: {}", bind_addr, e))?;

    println!("\nOpening browser for Claude OAuth login:\n  {}\n", auth_url_str);
    println!("Waiting for callback on http://localhost:{}/callback ...", port);
    open_browser(&auth_url_str);

    let (tx, rx) = mpsc::channel::<Result<(String, String)>>();
    let expected_state = state.clone();

    std::thread::spawn(move || {
        if let Ok(Some(rq)) = server.recv_timeout(StdDuration::from_secs(300)) {
            let full_url = format!("http://localhost{}", rq.url());
            let parsed = Url::parse(&full_url);
            if let Ok(parsed) = parsed {
                if parsed.path() == "/callback" {
                    let mut code = String::new();
                    let mut r_state = String::new();
                    let mut err = String::new();

                    for (k, v) in parsed.query_pairs() {
                        match k.as_ref() {
                            "code" => code = v.to_string(),
                            "state" => r_state = v.to_string(),
                            "error" => err = v.to_string(),
                            _ => {}
                        }
                    }

                    if !err.is_empty() {
                        let resp = Response::from_string(format!("OAuth error: {}", err)).with_status_code(400);
                        let _ = rq.respond(resp);
                        let _ = tx.send(Err(anyhow!("OAuth error: {}", err)));
                        return;
                    }

                    if r_state != expected_state {
                        let resp = Response::from_string("Invalid OAuth state").with_status_code(400);
                        let _ = rq.respond(resp);
                        let _ = tx.send(Err(anyhow!("Invalid OAuth state")));
                        return;
                    }

                    let html = "<html><body style=\"font-family:sans-serif;padding:2rem;\"><h2>Claude OAuth authentication complete!</h2><p>You may close this window and return to the terminal.</p></body></html>";
                    let header = Header::from_bytes(&b"Content-Type"[..], &b"text/html; charset=utf-8"[..]).unwrap();
                    let resp = Response::from_string(html).with_header(header);
                    let _ = rq.respond(resp);
                    let _ = tx.send(Ok((code, r_state)));
                }
            }
        } else {
            let _ = tx.send(Err(anyhow!("Timed out waiting for OAuth callback (5 minutes)")));
        }
    });

    let (code, returned_state) = rx.recv()??;
    exchange_code(
        creds_path,
        client_id,
        &code,
        &returned_state,
        &verifier,
        &redirect_uri,
    )
    .await
}

async fn exchange_code(
    creds_path: &Path,
    client_id: &str,
    code: &str,
    state: &str,
    verifier: &str,
    redirect_uri: &str,
) -> Result<ClaudeOAuthCredentials> {
    let client = reqwest::Client::new();
    let payload = json!({
        "grant_type": "authorization_code",
        "client_id": client_id,
        "code": code,
        "redirect_uri": redirect_uri,
        "code_verifier": verifier,
        "state": state,
    });

    let resp = client
        .post(TOKEN_URL)
        .header("Content-Type", "application/json")
        .json(&payload)
        .send()
        .await
        .context("failed to send token exchange request")?;

    let status = resp.status();
    let body_text = resp.text().await.unwrap_or_default();
    if !status.is_success() {
        return Err(anyhow!("token exchange failed (HTTP {}): {}", status, body_text));
    }

    let token_json: Value = serde_json::from_str(&body_text)
        .with_context(|| format!("failed to parse token response: {}", body_text))?;

    let access_token = token_json
        .get("access_token")
        .and_then(|v| v.as_str())
        .ok_or_else(|| anyhow!("missing access_token in response"))?
        .to_string();

    let refresh_token = token_json
        .get("refresh_token")
        .and_then(|v| v.as_str())
        .unwrap_or_default()
        .to_string();

    let expires_in = token_json
        .get("expires_in")
        .and_then(|v| v.as_i64())
        .unwrap_or(3600);

    let scopes = token_json
        .get("scope")
        .and_then(|v| v.as_str())
        .map(|s| s.split_whitespace().map(String::from).collect())
        .unwrap_or_else(|| SCOPES.iter().map(|s| s.to_string()).collect());

    let creds = ClaudeOAuthCredentials {
        access_token,
        refresh_token,
        expires_at: Utc::now() + Duration::seconds(expires_in),
        client_id: client_id.to_string(),
        scopes,
        source: "oauth-pkce".to_string(),
    };

    save_credentials(creds_path, &creds)?;
    Ok(creds)
}

pub async fn refresh_access_token(
    creds_path: &Path,
    creds: &ClaudeOAuthCredentials,
) -> Result<ClaudeOAuthCredentials> {
    if creds.refresh_token.is_empty() {
        return Err(anyhow!("no refresh_token available"));
    }

    let client_id = if creds.client_id.is_empty() {
        DEFAULT_CLIENT_ID
    } else {
        &creds.client_id
    };

    let client = reqwest::Client::new();
    let payload = json!({
        "grant_type": "refresh_token",
        "client_id": client_id,
        "refresh_token": creds.refresh_token,
    });

    let resp = client
        .post(TOKEN_URL)
        .header("Content-Type", "application/json")
        .json(&payload)
        .send()
        .await
        .context("failed to send token refresh request")?;

    let status = resp.status();
    let body_text = resp.text().await.unwrap_or_default();
    if !status.is_success() {
        return Err(anyhow!("token refresh failed (HTTP {}): {}", status, body_text));
    }

    let token_json: Value = serde_json::from_str(&body_text)?;
    let access_token = token_json
        .get("access_token")
        .and_then(|v| v.as_str())
        .ok_or_else(|| anyhow!("missing access_token in refresh response"))?
        .to_string();

    let refresh_token = token_json
        .get("refresh_token")
        .and_then(|v| v.as_str())
        .map(String::from)
        .unwrap_or_else(|| creds.refresh_token.clone());

    let expires_in = token_json
        .get("expires_in")
        .and_then(|v| v.as_i64())
        .unwrap_or(3600);

    let updated = ClaudeOAuthCredentials {
        access_token,
        refresh_token,
        expires_at: Utc::now() + Duration::seconds(expires_in),
        client_id: client_id.to_string(),
        scopes: creds.scopes.clone(),
        source: creds.source.clone(),
    };

    save_credentials(creds_path, &updated)?;
    Ok(updated)
}

async fn run_chat(
    access_token: &str,
    model: &str,
    prompt: &str,
    with_tools: bool,
    max_tokens: u32,
) -> Result<()> {
    let client = reqwest::Client::new();
    let url = format!("{}/v1/messages", API_BASE_URL);

    let mut messages = vec![json!({
        "role": "user",
        "content": prompt
    })];

    let tools = if with_tools {
        Some(json!([
            {
                "name": "get_weather",
                "description": "Get the current weather in a given location",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The city and country/state, e.g. Tokyo, Japan"
                        }
                    },
                    "required": ["location"]
                }
            }
        ]))
    } else {
        None
    };

    loop {
        let mut req_body = json!({
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages,
        });

        if let Some(ref t) = tools {
            req_body["tools"] = t.clone();
        }

        let resp = client
            .post(&url)
            .header("Authorization", format!("Bearer {}", access_token))
            .header("anthropic-version", ANTHROPIC_VERSION)
            .header("anthropic-beta", OAUTH_BETA_HEADER)
            .header("Content-Type", "application/json")
            .json(&req_body)
            .send()
            .await
            .context("failed to call Claude /v1/messages")?;

        let status = resp.status();
        let text = resp.text().await.unwrap_or_default();
        if !status.is_success() {
            return Err(anyhow!("Claude API error (HTTP {}): {}", status, text));
        }

        let resp_json: Value = serde_json::from_str(&text)?;
        let stop_reason = resp_json
            .get("stop_reason")
            .and_then(|v| v.as_str())
            .unwrap_or("");

        let content = resp_json
            .get("content")
            .and_then(|v| v.as_array())
            .cloned()
            .unwrap_or_default();

        let mut tool_results = Vec::new();

        for block in &content {
            match block.get("type").and_then(|v| v.as_str()) {
                Some("text") => {
                    if let Some(t) = block.get("text").and_then(|v| v.as_str()) {
                        println!("{}", t);
                    }
                }
                Some("tool_use") => {
                    let id = block.get("id").and_then(|v| v.as_str()).unwrap_or("");
                    let name = block.get("name").and_then(|v| v.as_str()).unwrap_or("");
                    let input = block.get("input").cloned().unwrap_or(json!({}));
                    println!("\n[Tool Call] id={} name={} input={}", id, name, input);

                    let result_str = if name == "get_weather" {
                        let loc = input
                            .get("location")
                            .and_then(|v| v.as_str())
                            .unwrap_or("Unknown");
                        json!({
                            "location": loc,
                            "temperature_c": 22,
                            "condition": "Sunny and clear"
                        })
                        .to_string()
                    } else {
                        json!({ "error": format!("unknown tool: {}", name) }).to_string()
                    };

                    println!("[Tool Result] id={} -> {}\n", id, result_str);
                    tool_results.push(json!({
                        "type": "tool_result",
                        "tool_use_id": id,
                        "content": result_str
                    }));
                }
                _ => {}
            }
        }

        if stop_reason == "tool_use" && !tool_results.is_empty() {
            messages.push(json!({
                "role": "assistant",
                "content": content
            }));
            messages.push(json!({
                "role": "user",
                "content": tool_results
            }));
        } else {
            break;
        }
    }

    Ok(())
}

pub fn open_browser(target: &str) {
    #[cfg(target_os = "windows")]
    {
        let _ = Command::new("rundll32")
            .args(["url.dll,FileProtocolHandler", target])
            .spawn();
    }
    #[cfg(target_os = "macos")]
    {
        let _ = Command::new("open").arg(target).spawn();
    }
    #[cfg(all(unix, not(target_os = "macos")))]
    {
        let _ = Command::new("xdg-open").arg(target).spawn();
    }
}
