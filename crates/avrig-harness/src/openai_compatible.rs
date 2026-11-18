//! OpenAI-compatible Chat Completions client for API-key authenticated endpoints.
//!
//! Configuration is stored in the user's avrig harness credential directory,
//! separate from OAuth credentials and never included in logs or debug output.
use reqwest::{Client, StatusCode, Url};
use serde::{Deserialize, Serialize};
use std::{fs, path::PathBuf};

const CONFIG_FILE: &str = "openai-compatible.json";

/// Endpoint settings and secret key. The API key is intentionally neither
/// serializable through public serde traits nor visible in `Debug` output.
pub struct OpenAiCompatibleConfig {
    pub base_url: String,
    pub model: String,
    api_key: String,
}

impl std::fmt::Debug for OpenAiCompatibleConfig {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        formatter
            .debug_struct("OpenAiCompatibleConfig")
            .field("base_url", &self.base_url)
            .field("model", &self.model)
            .field("api_key", &"[REDACTED]")
            .finish()
    }
}

impl OpenAiCompatibleConfig {
    pub fn new(
        base_url: impl Into<String>,
        model: impl Into<String>,
        api_key: impl Into<String>,
    ) -> Result<Self, OpenAiCompatibleError> {
        let config = Self {
            base_url: base_url.into(),
            model: model.into(),
            api_key: api_key.into(),
        };
        config.validate()?;
        Ok(config)
    }

    fn validate(&self) -> Result<(), OpenAiCompatibleError> {
        if self.model.trim().is_empty() || self.api_key.trim().is_empty() {
            return Err(OpenAiCompatibleError::Configuration);
        }
        let url = Url::parse(&self.base_url).map_err(|_| OpenAiCompatibleError::Configuration)?;
        if !matches!(url.scheme(), "http" | "https") || url.host_str().is_none() {
            return Err(OpenAiCompatibleError::Configuration);
        }
        Ok(())
    }

    fn endpoint(&self) -> Result<Url, OpenAiCompatibleError> {
        let mut url = Url::parse(self.base_url.trim_end_matches('/'))
            .map_err(|_| OpenAiCompatibleError::Configuration)?;
        let path = format!("{}/chat/completions", url.path().trim_end_matches('/'));
        url.set_path(&path);
        url.set_query(None);
        url.set_fragment(None);
        Ok(url)
    }

    /// Load the previously saved user-local endpoint configuration.
    pub fn load_user_default() -> Result<Self, OpenAiCompatibleError> {
        let path = Self::user_config_path()?;
        let bytes = fs::read(path).map_err(|_| OpenAiCompatibleError::Storage)?;
        let stored: StoredConfig =
            serde_json::from_slice(&bytes).map_err(|_| OpenAiCompatibleError::Storage)?;
        Self::new(stored.base_url, stored.model, stored.api_key)
    }

    /// Save settings under the per-user avrig harness credentials directory.
    pub fn save_user_default(&self) -> Result<(), OpenAiCompatibleError> {
        self.validate()?;
        let path = Self::user_config_path()?;
        let directory = path.parent().ok_or(OpenAiCompatibleError::Storage)?;
        fs::create_dir_all(directory).map_err(|_| OpenAiCompatibleError::Storage)?;
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            fs::set_permissions(directory, fs::Permissions::from_mode(0o700))
                .map_err(|_| OpenAiCompatibleError::Storage)?;
        }
        let bytes = serde_json::to_vec(&StoredConfig {
            base_url: self.base_url.clone(),
            model: self.model.clone(),
            api_key: self.api_key.clone(),
        })
        .map_err(|_| OpenAiCompatibleError::Storage)?;
        let temp = path.with_extension("json.tmp");
        fs::write(&temp, bytes).map_err(|_| OpenAiCompatibleError::Storage)?;
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            fs::set_permissions(&temp, fs::Permissions::from_mode(0o600))
                .map_err(|_| OpenAiCompatibleError::Storage)?;
        }
        fs::rename(temp, path).map_err(|_| OpenAiCompatibleError::Storage)
    }

    fn user_config_path() -> Result<PathBuf, OpenAiCompatibleError> {
        let root = if cfg!(windows) {
            std::env::var_os("APPDATA")
                .map(PathBuf::from)
                .ok_or(OpenAiCompatibleError::Configuration)?
        } else {
            std::env::var_os("XDG_CONFIG_HOME")
                .map(PathBuf::from)
                .or_else(|| {
                    std::env::var_os("HOME").map(|home| PathBuf::from(home).join(".config"))
                })
                .ok_or(OpenAiCompatibleError::Configuration)?
        };
        Ok(root
            .join("avrig")
            .join("harness")
            .join("credentials")
            .join(CONFIG_FILE))
    }
}

#[derive(Serialize, Deserialize)]
struct StoredConfig {
    base_url: String,
    model: String,
    api_key: String,
}

pub struct OpenAiCompatibleClient {
    http: Client,
    config: OpenAiCompatibleConfig,
}

impl OpenAiCompatibleClient {
    pub fn new(config: OpenAiCompatibleConfig) -> Result<Self, OpenAiCompatibleError> {
        Self::with_http_client(Client::new(), config)
    }

    /// Construct with an injected HTTP client, allowing local mock-server tests.
    pub fn with_http_client(
        http: Client,
        config: OpenAiCompatibleConfig,
    ) -> Result<Self, OpenAiCompatibleError> {
        config.validate()?;
        Ok(Self { http, config })
    }

    /// Send a Chat Completions request body. The `model` field is set from the
    /// configured model, overriding any model value supplied in `request`.
    pub async fn chat_completions(
        &self,
        mut request: serde_json::Value,
    ) -> Result<serde_json::Value, OpenAiCompatibleError> {
        let object = request
            .as_object_mut()
            .ok_or(OpenAiCompatibleError::InvalidRequest)?;
        object.insert(
            "model".into(),
            serde_json::Value::String(self.config.model.clone()),
        );
        let response = self
            .http
            .post(self.config.endpoint()?)
            .bearer_auth(&self.config.api_key)
            .json(&request)
            .send()
            .await
            .map_err(|_| OpenAiCompatibleError::Transport)?;
        if !response.status().is_success() {
            return Err(OpenAiCompatibleError::Rejected(response.status()));
        }
        response
            .json()
            .await
            .map_err(|_| OpenAiCompatibleError::InvalidResponse)
    }
}

#[derive(Debug, thiserror::Error)]
pub enum OpenAiCompatibleError {
    #[error("OpenAI-compatible endpoint configuration is invalid")]
    Configuration,
    #[error("OpenAI-compatible request is invalid")]
    InvalidRequest,
    #[error("OpenAI-compatible request failed")]
    Transport,
    #[error("OpenAI-compatible endpoint rejected the request ({0})")]
    Rejected(StatusCode),
    #[error("OpenAI-compatible endpoint returned an invalid response")]
    InvalidResponse,
    #[error("OpenAI-compatible credential storage operation failed")]
    Storage,
}

#[cfg(test)]
mod tests {
    use super::*;
    use tokio::{
        io::{AsyncReadExt, AsyncWriteExt},
        net::TcpListener,
    };

    async fn receive_request(listener: TcpListener) -> String {
        let (mut stream, _) = listener.accept().await.expect("accept local request");
        let mut bytes = vec![0; 8192];
        let count = stream.read(&mut bytes).await.expect("read local request");
        let request = String::from_utf8_lossy(&bytes[..count]).into_owned();
        let body = r#"{"id":"test","choices":[]}"#;
        let response = format!(
            "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
            body.len(),
            body
        );
        stream
            .write_all(response.as_bytes())
            .await
            .expect("write local response");
        request
    }

    #[tokio::test]
    async fn posts_chat_completion_to_derived_url_with_bearer_auth() {
        let listener = TcpListener::bind("127.0.0.1:0")
            .await
            .expect("bind local server");
        let address = listener.local_addr().expect("local address");
        let server = tokio::spawn(receive_request(listener));
        let config = OpenAiCompatibleConfig::new(
            format!("http://{address}/v1/"),
            "local-model",
            "unit-test-key",
        )
        .expect("valid configuration");
        let client = OpenAiCompatibleClient::new(config).expect("client");
        let response = client
            .chat_completions(serde_json::json!({
                "model": "untrusted-model",
                "messages": [{"role": "user", "content": "hello"}]
            }))
            .await
            .expect("request succeeds");
        assert_eq!(response["id"], "test");
        let request = server.await.expect("server task");
        let head = request.split("\r\n\r\n").next().unwrap_or_default();
        assert!(head.starts_with("POST /v1/chat/completions HTTP/1.1"));
        assert!(
            head.to_ascii_lowercase()
                .contains("authorization: bearer unit-test-key")
        );
        assert!(request.contains(r#""model":"local-model""#));
        assert!(!request.contains("untrusted-model"));
    }

    #[test]
    fn rejects_invalid_urls_and_empty_secrets() {
        assert!(OpenAiCompatibleConfig::new("file:///tmp", "model", "key").is_err());
        assert!(OpenAiCompatibleConfig::new("https://example.test/v1", "model", " ").is_err());
    }

    #[test]
    fn secret_is_not_in_debug_output() {
        let config =
            OpenAiCompatibleConfig::new("https://example.test/v1", "model", "secret-value")
                .expect("valid configuration");
        assert!(!format!("{config:?}").contains("secret-value"));
    }

    #[test]
    fn config_path_is_user_scoped() {
        let path = OpenAiCompatibleConfig::user_config_path().expect("user config path");
        assert!(path.ends_with(std::path::Path::new(
            "avrig/harness/credentials/openai-compatible.json"
        )));
    }
}
