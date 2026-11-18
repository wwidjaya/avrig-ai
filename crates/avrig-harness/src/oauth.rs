//! Native OAuth helpers and user-scoped credential persistence for model providers.
//!
//! Credentials are stored under the operating system's per-user configuration
//! directory, never in the repository. Replace `FileCredentialStore` with a
//! database-backed implementation when the harness has a user database.
use base64::{Engine, engine::general_purpose::URL_SAFE_NO_PAD};
use rand::{RngCore, rngs::OsRng};
use reqwest::{Client, StatusCode};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::{
    fs,
    path::PathBuf,
    time::{Duration, SystemTime, UNIX_EPOCH},
};
use url::Url;

const OPENAI_AUTH: &str = "https://auth.openai.com/api/accounts/authorize";
const OPENAI_TOKEN: &str = "https://auth.openai.com/api/accounts/oauth/token";
const GOOGLE_AUTH: &str = "https://accounts.google.com/o/oauth2/v2/auth";
const GOOGLE_TOKEN: &str = "https://oauth2.googleapis.com/token";
const OPENAI_SCOPES: &str =
    "openid profile email offline_access resource.invoke chatgpt.tokens.use.direct";
const GOOGLE_SCOPES: &str = "https://www.googleapis.com/auth/cloud-platform";

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Provider {
    OpenAi,
    Google,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Credentials {
    pub provider: Provider,
    pub access_token: String,
    pub refresh_token: Option<String>,
    pub client_id: String,
    pub expires_at_unix: u64,
}

#[derive(Clone, Debug)]
pub struct Pkce {
    pub verifier: String,
    pub challenge: String,
    pub state: String,
}

/// Bind only to loopback. The caller chooses a callback path and must pass
/// the exact redirect URI used to build the authorization request.
pub async fn bind_loopback_callback(port: u16) -> Result<tokio::net::TcpListener, OAuthError> {
    tokio::net::TcpListener::bind((std::net::Ipv4Addr::LOCALHOST, port))
        .await
        .map_err(|_| OAuthError::Transport)
}

/// Receive one OAuth callback and validate state before returning its code.
pub async fn receive_callback(
    listener: tokio::net::TcpListener,
    expected_path: &str,
    expected_state: &str,
) -> Result<String, OAuthError> {
    use tokio::io::{AsyncReadExt, AsyncWriteExt};
    let (mut stream, _) = listener.accept().await.map_err(|_| OAuthError::Transport)?;
    let mut request = vec![0u8; 8192];
    let count = stream
        .read(&mut request)
        .await
        .map_err(|_| OAuthError::Transport)?;
    let first_line = std::str::from_utf8(&request[..count])
        .ok()
        .and_then(|text| text.lines().next())
        .ok_or(OAuthError::InvalidResponse)?;
    let target = first_line
        .split_whitespace()
        .nth(1)
        .ok_or(OAuthError::InvalidResponse)?;
    let callback = Url::parse(&format!("http://127.0.0.1{target}"))
        .map_err(|_| OAuthError::InvalidResponse)?;
    let code = callback
        .query_pairs()
        .find(|(key, _)| key == "code")
        .map(|(_, value)| value.into_owned());
    let state = callback
        .query_pairs()
        .find(|(key, _)| key == "state")
        .map(|(_, value)| value.into_owned());
    let valid = callback.path() == expected_path
        && state.as_deref() == Some(expected_state)
        && code.is_some();
    let (status, body) = if valid {
        ("200 OK", "Sign-in received. You may close this window.")
    } else {
        (
            "400 Bad Request",
            "Sign-in callback was invalid. Return to the harness.",
        )
    };
    let response = format!(
        "HTTP/1.1 {status}\r\nContent-Type: text/plain\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}",
        body.len()
    );
    stream
        .write_all(response.as_bytes())
        .await
        .map_err(|_| OAuthError::Transport)?;
    if valid {
        code.ok_or(OAuthError::InvalidResponse)
    } else {
        Err(OAuthError::InvalidResponse)
    }
}

impl Pkce {
    pub fn generate() -> Self {
        let mut entropy = [0u8; 32];
        OsRng.fill_bytes(&mut entropy);
        let verifier = URL_SAFE_NO_PAD.encode(entropy);
        let challenge = URL_SAFE_NO_PAD.encode(Sha256::digest(verifier.as_bytes()));
        OsRng.fill_bytes(&mut entropy);
        Self {
            verifier,
            challenge,
            state: URL_SAFE_NO_PAD.encode(entropy),
        }
    }
}

pub fn openai_authorization_url(redirect_uri: &str, pkce: &Pkce) -> Result<Url, OAuthError> {
    let mut url = Url::parse(OPENAI_AUTH).map_err(|_| OAuthError::Configuration)?;
    url.query_pairs_mut()
        .append_pair("client_id", "dynamic_agent_client")
        .append_pair("response_type", "code")
        .append_pair("redirect_uri", redirect_uri)
        .append_pair("scope", OPENAI_SCOPES)
        .append_pair("state", &pkce.state)
        .append_pair("code_challenge", &pkce.challenge)
        .append_pair("code_challenge_method", "S256")
        .append_pair("resource", "https://api.openai.com/v1");
    Ok(url)
}

pub fn google_authorization_url(
    client_id: &str,
    redirect_uri: &str,
    pkce: &Pkce,
) -> Result<Url, OAuthError> {
    let mut url = Url::parse(GOOGLE_AUTH).map_err(|_| OAuthError::Configuration)?;
    url.query_pairs_mut()
        .append_pair("client_id", client_id)
        .append_pair("response_type", "code")
        .append_pair("redirect_uri", redirect_uri)
        .append_pair("scope", GOOGLE_SCOPES)
        .append_pair("state", &pkce.state)
        .append_pair("code_challenge", &pkce.challenge)
        .append_pair("code_challenge_method", "S256")
        .append_pair("access_type", "offline")
        .append_pair("prompt", "consent");
    Ok(url)
}

#[derive(Deserialize)]
struct TokenResponse {
    access_token: String,
    expires_in: u64,
    refresh_token: Option<String>,
    client_id: Option<String>,
}

pub async fn exchange_code(
    client: &Client,
    provider: Provider,
    client_id: &str,
    client_secret: Option<&str>,
    code: &str,
    verifier: &str,
    redirect_uri: &str,
) -> Result<Credentials, OAuthError> {
    let endpoint = match provider {
        Provider::OpenAi => OPENAI_TOKEN,
        Provider::Google => GOOGLE_TOKEN,
    };
    let mut form = vec![
        ("grant_type", "authorization_code"),
        ("code", code),
        ("redirect_uri", redirect_uri),
        ("client_id", client_id),
        ("code_verifier", verifier),
    ];
    if let Some(secret) = client_secret {
        form.push(("client_secret", secret));
    }
    let response = client
        .post(endpoint)
        .form(&form)
        .send()
        .await
        .map_err(|_| OAuthError::Transport)?;
    parse_token_response(response, provider, client_id).await
}

pub async fn refresh_credentials(
    client: &Client,
    credentials: &Credentials,
    client_secret: Option<&str>,
) -> Result<Credentials, OAuthError> {
    let refresh_token = credentials
        .refresh_token
        .as_deref()
        .ok_or(OAuthError::NoRefreshToken)?;
    let endpoint = match credentials.provider {
        Provider::OpenAi => OPENAI_TOKEN,
        Provider::Google => GOOGLE_TOKEN,
    };
    let mut form = vec![
        ("grant_type", "refresh_token"),
        ("refresh_token", refresh_token),
        ("client_id", credentials.client_id.as_str()),
    ];
    if let Some(secret) = client_secret {
        form.push(("client_secret", secret));
    }
    let response = client
        .post(endpoint)
        .form(&form)
        .send()
        .await
        .map_err(|_| OAuthError::Transport)?;
    let mut refreshed =
        parse_token_response(response, credentials.provider, &credentials.client_id).await?;
    if refreshed.refresh_token.is_none() {
        refreshed.refresh_token = credentials.refresh_token.clone();
    }
    Ok(refreshed)
}

async fn parse_token_response(
    response: reqwest::Response,
    provider: Provider,
    client_id: &str,
) -> Result<Credentials, OAuthError> {
    if !response.status().is_success() {
        return Err(OAuthError::Rejected(response.status()));
    }
    let token: TokenResponse = response
        .json()
        .await
        .map_err(|_| OAuthError::InvalidResponse)?;
    Ok(Credentials {
        provider,
        access_token: token.access_token,
        refresh_token: token.refresh_token,
        client_id: token.client_id.unwrap_or_else(|| client_id.to_owned()),
        expires_at_unix: now_unix().saturating_add(token.expires_in),
    })
}

pub trait CredentialStore: Send + Sync {
    fn load(&self, provider: Provider) -> Result<Option<Credentials>, OAuthError>;
    fn save(&self, credentials: &Credentials) -> Result<(), OAuthError>;
    fn delete(&self, provider: Provider) -> Result<(), OAuthError>;
}

pub struct FileCredentialStore {
    directory: PathBuf,
}

/// An in-progress interactive connection. The authorization URL is returned
/// to the caller for display/opening; this crate never launches a browser.
pub struct PendingAuthorization {
    pub authorization_url: Url,
    pub listener: tokio::net::TcpListener,
    pub redirect_uri: String,
    pkce: Pkce,
}

pub async fn begin_openai_authorization(port: u16) -> Result<PendingAuthorization, OAuthError> {
    begin_authorization(Provider::OpenAi, port, "dynamic_agent_client").await
}

/// `client_id` must be an OAuth client registered by the application owner for
/// Google's public Gemini API. No secret or client ID is embedded in this crate.
pub async fn begin_google_authorization(
    port: u16,
    client_id: &str,
) -> Result<PendingAuthorization, OAuthError> {
    begin_authorization(Provider::Google, port, client_id).await
}

async fn begin_authorization(
    provider: Provider,
    port: u16,
    client_id: &str,
) -> Result<PendingAuthorization, OAuthError> {
    let path = "/oauth-callback";
    let redirect_uri = format!("http://127.0.0.1:{port}{path}");
    let listener = bind_loopback_callback(port).await?;
    let pkce = Pkce::generate();
    let authorization_url = match provider {
        Provider::OpenAi => openai_authorization_url(&redirect_uri, &pkce)?,
        Provider::Google => google_authorization_url(client_id, &redirect_uri, &pkce)?,
    };
    Ok(PendingAuthorization {
        authorization_url,
        listener,
        redirect_uri,
        pkce,
    })
}

/// Complete the interactive flow after the user authorizes in their browser.
/// This waits for the loopback callback, validates OAuth state, exchanges the
/// code, and persists credentials before returning.
pub async fn complete_authorization(
    pending: PendingAuthorization,
    provider: Provider,
    client_id: &str,
    client_secret: Option<&str>,
    client: &Client,
    store: &dyn CredentialStore,
) -> Result<Credentials, OAuthError> {
    let code = receive_callback(pending.listener, "/oauth-callback", &pending.pkce.state).await?;
    let credentials = exchange_code(
        client,
        provider,
        client_id,
        client_secret,
        &code,
        &pending.pkce.verifier,
        &pending.redirect_uri,
    )
    .await?;
    store.save(&credentials)?;
    Ok(credentials)
}

/// Return usable credentials, refreshing within 60 seconds of expiry.
/// Refreshed credentials are persisted before being returned.
pub async fn credentials_for_use(
    provider: Provider,
    client: &Client,
    store: &dyn CredentialStore,
    client_secret: Option<&str>,
) -> Result<Credentials, OAuthError> {
    let credentials = store.load(provider)?.ok_or(OAuthError::NotConnected)?;
    if credentials.expires_at_unix > now_unix().saturating_add(60) {
        return Ok(credentials);
    }
    let refreshed = refresh_credentials(client, &credentials, client_secret).await?;
    store.save(&refreshed)?;
    Ok(refreshed)
}

impl FileCredentialStore {
    pub fn user_default() -> Result<Self, OAuthError> {
        let root = if cfg!(windows) {
            std::env::var_os("APPDATA")
                .map(PathBuf::from)
                .ok_or(OAuthError::Configuration)?
        } else {
            std::env::var_os("XDG_CONFIG_HOME")
                .map(PathBuf::from)
                .or_else(|| {
                    std::env::var_os("HOME").map(|home| PathBuf::from(home).join(".config"))
                })
                .ok_or(OAuthError::Configuration)?
        };
        Ok(Self {
            directory: root.join("avrig").join("harness").join("credentials"),
        })
    }
    fn path(&self, provider: Provider) -> PathBuf {
        self.directory.join(match provider {
            Provider::OpenAi => "openai.json",
            Provider::Google => "google.json",
        })
    }
}

impl CredentialStore for FileCredentialStore {
    fn load(&self, provider: Provider) -> Result<Option<Credentials>, OAuthError> {
        let path = self.path(provider);
        let bytes = match fs::read(path) {
            Ok(bytes) => bytes,
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok(None),
            Err(_) => return Err(OAuthError::Storage),
        };
        let credentials: Credentials =
            serde_json::from_slice(&bytes).map_err(|_| OAuthError::Storage)?;
        if credentials.provider != provider {
            return Err(OAuthError::Storage);
        }
        Ok(Some(credentials))
    }
    fn save(&self, credentials: &Credentials) -> Result<(), OAuthError> {
        fs::create_dir_all(&self.directory).map_err(|_| OAuthError::Storage)?;
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            fs::set_permissions(&self.directory, fs::Permissions::from_mode(0o700))
                .map_err(|_| OAuthError::Storage)?;
        }
        let path = self.path(credentials.provider);
        let temp = path.with_extension("json.tmp");
        let bytes = serde_json::to_vec(credentials).map_err(|_| OAuthError::Storage)?;
        fs::write(&temp, bytes).map_err(|_| OAuthError::Storage)?;
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            fs::set_permissions(&temp, fs::Permissions::from_mode(0o600))
                .map_err(|_| OAuthError::Storage)?;
        }
        fs::rename(temp, path).map_err(|_| OAuthError::Storage)
    }
    fn delete(&self, provider: Provider) -> Result<(), OAuthError> {
        match fs::remove_file(self.path(provider)) {
            Ok(()) => Ok(()),
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(()),
            Err(_) => Err(OAuthError::Storage),
        }
    }
}

fn now_unix() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or(Duration::ZERO)
        .as_secs()
}

#[derive(Debug, thiserror::Error)]
pub enum OAuthError {
    #[error("OAuth configuration is unavailable")]
    Configuration,
    #[error("OAuth request failed")]
    Transport,
    #[error("OAuth provider rejected the request ({0})")]
    Rejected(StatusCode),
    #[error("OAuth provider returned an invalid response")]
    InvalidResponse,
    #[error("No refresh token is available")]
    NoRefreshToken,
    #[error("Provider account is not connected")]
    NotConnected,
    #[error("Credential storage operation failed")]
    Storage,
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn pkce_uses_unpadded_url_safe_values_and_state_is_random() {
        let a = Pkce::generate();
        let b = Pkce::generate();
        assert!(!a.verifier.contains('='));
        assert!(!a.challenge.contains('='));
        assert_ne!(a.state, b.state);
        assert_eq!(
            a.challenge,
            URL_SAFE_NO_PAD.encode(Sha256::digest(a.verifier.as_bytes()))
        );
    }
    #[test]
    fn provider_auth_urls_use_expected_public_endpoints_and_scopes() {
        let pkce = Pkce::generate();
        let openai = openai_authorization_url("http://127.0.0.1:8000/callback", &pkce).unwrap();
        assert_eq!(openai.host_str(), Some("auth.openai.com"));
        assert!(
            openai
                .query()
                .unwrap()
                .contains("chatgpt.tokens.use.direct")
        );
        let google =
            google_authorization_url("public-client-id", "http://127.0.0.1:8001/callback", &pkce)
                .unwrap();
        assert_eq!(google.host_str(), Some("accounts.google.com"));
        assert!(google.query().unwrap().contains("cloud-platform"));
    }

    #[test]
    fn file_store_round_trips_user_credentials_and_deletes_them() {
        let dir = std::env::temp_dir().join(format!("avrig-oauth-test-{}", uuid::Uuid::new_v4()));
        let store = FileCredentialStore {
            directory: dir.clone(),
        };
        let credentials = Credentials {
            provider: Provider::OpenAi,
            access_token: "test-access".into(),
            refresh_token: Some("test-refresh".into()),
            client_id: "test-client".into(),
            expires_at_unix: now_unix() + 3600,
        };
        store.save(&credentials).unwrap();
        assert_eq!(
            store.load(Provider::OpenAi).unwrap().unwrap().access_token,
            "test-access"
        );
        assert!(store.load(Provider::Google).unwrap().is_none());
        store.delete(Provider::OpenAi).unwrap();
        assert!(store.load(Provider::OpenAi).unwrap().is_none());
        let _ = fs::remove_dir_all(dir);
    }
}
