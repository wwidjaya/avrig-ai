//! OAuth-authenticated client for the public Vertex AI Gemini generateContent API.

use crate::oauth::{CredentialStore, OAuthError, Provider, credentials_for_use};
use reqwest::{Client, StatusCode, Url};
use serde::{Deserialize, Serialize};

/// Public Vertex AI target. `location` is a Vertex AI region, such as `us-central1`.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VertexAiConfig {
    pub project_id: String,
    pub location: String,
    pub model: String,
    #[cfg(test)]
    test_endpoint: Option<String>,
}

impl VertexAiConfig {
    pub fn new(
        project_id: impl Into<String>,
        location: impl Into<String>,
        model: impl Into<String>,
    ) -> Result<Self, VertexAiError> {
        let config = Self {
            project_id: project_id.into(),
            location: location.into(),
            model: model.into(),
            #[cfg(test)]
            test_endpoint: None,
        };
        config.validate()?;
        Ok(config)
    }

    fn validate(&self) -> Result<(), VertexAiError> {
        if self.project_id.trim().is_empty()
            || self.location.trim().is_empty()
            || self.model.trim().is_empty()
            || self.project_id.contains('/')
            || self.location.contains('/')
            || self.model.contains('/')
        {
            return Err(VertexAiError::Configuration);
        }
        Ok(())
    }

    fn endpoint(&self) -> Result<Url, VertexAiError> {
        self.validate()?;
        #[cfg(test)]
        if let Some(endpoint) = &self.test_endpoint {
            return Url::parse(endpoint).map_err(|_| VertexAiError::Configuration);
        }
        Url::parse(&format!(
            "https://{}-aiplatform.googleapis.com/v1/projects/{}/locations/{}/publishers/google/models/{}:generateContent",
            self.location, self.project_id, self.location, self.model
        ))
        .map_err(|_| VertexAiError::Configuration)
    }
}

#[derive(Clone, Debug, Serialize)]
pub struct GenerateContentRequest {
    pub contents: Vec<Content>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub generation_config: Option<GenerationConfig>,
}

impl GenerateContentRequest {
    pub fn text(prompt: impl Into<String>) -> Self {
        Self {
            contents: vec![Content {
                role: "user".into(),
                parts: vec![Part {
                    text: prompt.into(),
                }],
            }],
            generation_config: None,
        }
    }
}

#[derive(Clone, Debug, Serialize)]
pub struct Content {
    pub role: String,
    pub parts: Vec<Part>,
}

#[derive(Clone, Debug, Serialize)]
pub struct Part {
    pub text: String,
}

#[derive(Clone, Debug, Default, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct GenerationConfig {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub temperature: Option<f32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub max_output_tokens: Option<u32>,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct GenerateContentResponse {
    #[serde(default)]
    pub candidates: Vec<Candidate>,
    pub usage_metadata: Option<UsageMetadata>,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct Candidate {
    pub content: Option<ContentResponse>,
    pub finish_reason: Option<String>,
}

#[derive(Clone, Debug, Deserialize)]
pub struct ContentResponse {
    #[serde(default)]
    pub parts: Vec<ResponsePart>,
    pub role: Option<String>,
}

#[derive(Clone, Debug, Deserialize)]
pub struct ResponsePart {
    pub text: Option<String>,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct UsageMetadata {
    pub prompt_token_count: Option<u32>,
    pub candidates_token_count: Option<u32>,
    pub total_token_count: Option<u32>,
}

pub struct VertexAiClient {
    http: Client,
    config: VertexAiConfig,
    client_secret: Option<String>,
}

impl VertexAiClient {
    pub fn new(
        config: VertexAiConfig,
        client_secret: Option<String>,
    ) -> Result<Self, VertexAiError> {
        Self::with_http_client(Client::new(), config, client_secret)
    }

    /// Inject an HTTP client for local mock-server tests.
    pub fn with_http_client(
        http: Client,
        config: VertexAiConfig,
        client_secret: Option<String>,
    ) -> Result<Self, VertexAiError> {
        config.validate()?;
        Ok(Self {
            http,
            config,
            client_secret,
        })
    }

    /// Sends one request using saved Google credentials, refreshing near expiry.
    pub async fn generate_content(
        &self,
        request: &GenerateContentRequest,
        store: &dyn CredentialStore,
    ) -> Result<GenerateContentResponse, VertexAiError> {
        let credentials = credentials_for_use(
            Provider::Google,
            &self.http,
            store,
            self.client_secret.as_deref(),
        )
        .await?;
        let response = self
            .http
            .post(self.config.endpoint()?)
            .bearer_auth(credentials.access_token)
            .json(request)
            .send()
            .await
            .map_err(|_| VertexAiError::Transport)?;
        if !response.status().is_success() {
            return Err(VertexAiError::Rejected(response.status()));
        }
        response
            .json()
            .await
            .map_err(|_| VertexAiError::InvalidResponse)
    }

    pub async fn generate_text(
        &self,
        prompt: impl Into<String>,
        store: &dyn CredentialStore,
    ) -> Result<GenerateContentResponse, VertexAiError> {
        self.generate_content(&GenerateContentRequest::text(prompt), store)
            .await
    }
}

#[derive(Debug, thiserror::Error)]
pub enum VertexAiError {
    #[error("Vertex AI configuration is invalid")]
    Configuration,
    #[error(transparent)]
    OAuth(#[from] OAuthError),
    #[error("Vertex AI request failed")]
    Transport,
    #[error("Vertex AI rejected the request ({0})")]
    Rejected(StatusCode),
    #[error("Vertex AI returned an invalid response")]
    InvalidResponse,
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::oauth::{CredentialStore, Credentials, OAuthError};
    use std::sync::{Arc, Mutex};
    use tokio::{
        io::{AsyncReadExt, AsyncWriteExt},
        net::TcpListener,
    };

    #[derive(Clone, Default)]
    struct MemoryStore(Arc<Mutex<Option<Credentials>>>);

    impl CredentialStore for MemoryStore {
        fn load(&self, provider: Provider) -> Result<Option<Credentials>, OAuthError> {
            let value = self.0.lock().map_err(|_| OAuthError::Storage)?.clone();
            Ok(value.filter(|credential| credential.provider == provider))
        }

        fn save(&self, credentials: &Credentials) -> Result<(), OAuthError> {
            *self.0.lock().map_err(|_| OAuthError::Storage)? = Some(credentials.clone());
            Ok(())
        }

        fn delete(&self, _provider: Provider) -> Result<(), OAuthError> {
            *self.0.lock().map_err(|_| OAuthError::Storage)? = None;
            Ok(())
        }
    }

    async fn mock_vertex_request(listener: TcpListener) -> String {
        let (mut stream, _) = listener.accept().await.expect("accept");
        let mut bytes = vec![0; 16 * 1024];
        let count = stream.read(&mut bytes).await.expect("read");
        let request = String::from_utf8_lossy(&bytes[..count]).into_owned();
        let body = r#"{"candidates":[{"content":{"role":"model","parts":[{"text":"hello"}]},"finishReason":"STOP"}]}"#;
        let response = format!(
            "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
            body.len(),
            body
        );
        stream.write_all(response.as_bytes()).await.expect("write");
        request
    }

    fn valid_store() -> MemoryStore {
        MemoryStore(Arc::new(Mutex::new(Some(Credentials {
            provider: Provider::Google,
            access_token: "mock-access-token".into(),
            refresh_token: None,
            client_id: "mock-client-id".into(),
            expires_at_unix: u64::MAX,
        }))))
    }

    #[tokio::test]
    async fn sends_vertex_generate_content_with_google_bearer_token() {
        let listener = TcpListener::bind("127.0.0.1:0").await.expect("bind");
        let address = listener.local_addr().expect("address");
        let server = tokio::spawn(mock_vertex_request(listener));
        let config =
            VertexAiConfig::new("test-project", "us-central1", "gemini-2.5-flash").expect("config");
        let endpoint = format!(
            "http://{address}/v1/projects/test-project/locations/us-central1/publishers/google/models/gemini-2.5-flash:generateContent"
        );
        let client = VertexAiClient::with_http_client(
            Client::new(),
            config.with_endpoint_for_test(endpoint),
            None,
        )
        .expect("client");

        let response = client
            .generate_text("Reply with one word.", &valid_store())
            .await
            .expect("generate content");
        assert_eq!(
            response.candidates[0].content.as_ref().unwrap().parts[0]
                .text
                .as_deref(),
            Some("hello")
        );
        let request = server.await.expect("server");
        let (headers, body) = request.split_once("\r\n\r\n").expect("HTTP body");
        let request_line = headers.lines().next().unwrap_or_default();
        assert!(request_line.starts_with("POST /v1/projects/test-project/locations/us-central1/publishers/google/models/gemini-2.5-flash"));
        assert!(request_line.contains("generateContent HTTP/1.1"));
        assert!(
            headers
                .to_ascii_lowercase()
                .contains("authorization: bearer mock-access-token")
        );
        let json: serde_json::Value = serde_json::from_str(body).expect("request JSON");
        assert_eq!(json["contents"][0]["role"], "user");
        assert_eq!(
            json["contents"][0]["parts"][0]["text"],
            "Reply with one word."
        );
    }

    #[test]
    fn rejects_empty_or_path_injected_configuration() {
        assert!(VertexAiConfig::new("", "us-central1", "gemini-2.5-flash").is_err());
        assert!(VertexAiConfig::new("project", "us-central1/evil", "model").is_err());
        assert!(VertexAiConfig::new("project", "us-central1", "model/evil").is_err());
    }

    #[tokio::test]
    async fn requires_connected_google_account() {
        let client = VertexAiClient::new(
            VertexAiConfig::new("project", "us-central1", "gemini-2.5-flash").unwrap(),
            None,
        )
        .unwrap();
        let empty = MemoryStore::default();
        assert!(matches!(
            client.generate_text("hello", &empty).await,
            Err(VertexAiError::OAuth(OAuthError::NotConnected))
        ));
    }
}

#[cfg(test)]
impl VertexAiConfig {
    fn with_endpoint_for_test(mut self, endpoint: String) -> Self {
        // Only unit tests can redirect requests to a loopback mock server.
        self.test_endpoint = Some(endpoint);
        self
    }
}
