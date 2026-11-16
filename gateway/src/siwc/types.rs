use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

pub const DEFAULT_AUTH_URL: &str = "https://auth.openai.com/api/accounts/authorize";
pub const DEFAULT_TOKEN_URL: &str = "https://auth.openai.com/api/accounts/oauth/token";
pub const DEFAULT_REDIRECT_URI: &str = "http://127.0.0.1:8080/callback";
pub const RESOURCE_URL: &str = "https://api.openai.com/v1";
pub const DYNAMIC_CLIENT_ID: &str = "dynamic_agent_client";
pub const SCOPES: &str =
    "openid profile email offline_access resource.invoke chatgpt.tokens.use.direct";
pub const DEFAULT_STORAGE_FILE: &str = "data/chatgpt.json";

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct StoredCredentials {
    pub access_token: String,
    pub refresh_token: Option<String>,
    pub client_id: String,
    pub expires_at: DateTime<Utc>,
}

#[derive(Debug, Deserialize)]
pub struct TokenResponse {
    pub access_token: String,
    pub refresh_token: Option<String>,
    pub expires_in: i64,
    pub token_type: Option<String>,
    pub client_id: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ResponsesRequest {
    pub model: String,
    pub input: Vec<InputMessage>,
    pub store: bool,
    pub stream: bool,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct InputMessage {
    pub role: String,
    pub content: String,
}
