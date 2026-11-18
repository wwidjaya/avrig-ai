use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

pub const DEFAULT_CLIENT_ID: &str = "";
pub const DEFAULT_CLIENT_SECRET: &str = "";
pub const REDIRECT_URI: &str = "http://localhost:51121/oauth-callback";
pub const AUTH_URL: &str = "https://accounts.google.com/o/oauth2/v2/auth";
pub const TOKEN_URL: &str = "https://oauth2.googleapis.com/token";
pub const USER_INFO_URL: &str = "https://www.googleapis.com/oauth2/v1/userinfo?alt=json";
pub const GATEWAY_URL: &str = "https://daily-cloudcode-pa.googleapis.com";
pub const GEMINI_CLI_URL: &str = "https://cloudcode-pa.googleapis.com";
pub const HUB_USER_AGENT: &str =
    "antigravity/hub/2.24.0 (aidev_client; os_type=windows; arch=amd64; cl=1000335682)";

pub const SCOPES: &[&str] = &[
    "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/cclog",
    "https://www.googleapis.com/auth/experimentsandconfigs",
];

pub const DEFAULT_THOUGHT_SIGNATURE: &str = "EtcCCtQCAWkUfRPm89wedn0ZXiXQDmgjj817TCQLmCnKTOI4dnJ5EGyHBuQ4bguOuk3VzwwOKe/f1nN9kbmoBD1y+bi0paJpQ0c8YKGPSwwF5vD/lE2SBW4qgs1TBS2V8SS7+EKjS8QkPe4EpoeLXilTsMrr4f0WGjhtKut8Q/n8dXUSE/12TFTGpTj+3WttfYBOj6Rz89Q5a7+lUVJksNLhC1dtgj1Y1wt9/ymaO7iW/RTVwO4IF1XFXs2Q+qVIxaSjkyZx4e02WmFrf7hkMXKcpwwtF0kSXiPqUYmH9kYIbNPUxT+db/S/cVBSSycc2L2AJuapyZTY9J30ZBjHQHj0uUmNcwqPh+zKi4gkbSjG8sNl0gK3erQUMgtpqTtqTI3P/ClIsGdoExOxD4SECyC/PBd3eVP4C/yF+xYTb0bODyo+bJmB7NcJ01s5Mh3pIBJGuXIt61OzEA==";

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Credentials {
    pub access_token: String,
    pub refresh_token: String,
    #[serde(alias = "project_id")]
    pub project: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub client_id: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub client_secret: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub email: Option<String>,
    pub expires_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
#[serde(rename_all = "camelCase")]
pub struct AvailableModel {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub display_name: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub max_tokens: Option<i64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub max_output_tokens: Option<i64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub supports_images: Option<bool>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub supports_thinking: Option<bool>,
    #[serde(default)]
    pub disabled: bool,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub selectable: Option<bool>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub quota_info: Option<QuotaInfo>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
#[serde(rename_all = "camelCase")]
pub struct QuotaInfo {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub remaining_fraction: Option<f64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub reset_time: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct TokenResponse {
    #[serde(default)]
    pub access_token: Option<String>,
    #[serde(default)]
    pub refresh_token: Option<String>,
    #[serde(default)]
    pub expires_in: Option<i64>,
    #[serde(default)]
    pub error: Option<String>,
    #[serde(default)]
    pub error_description: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct UpstreamError {
    #[serde(default)]
    pub error: UpstreamErrorBody,
}

#[derive(Debug, Deserialize, Default)]
pub struct UpstreamErrorBody {
    #[serde(default)]
    pub code: i32,
    #[serde(default)]
    pub message: String,
    #[serde(default)]
    pub status: String,
    #[serde(default)]
    pub details: Vec<serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Tool {
    #[serde(rename = "type", default = "default_tool_type")]
    pub tool_type: String,
    pub function: FunctionDefinition,
}

fn default_tool_type() -> String {
    "function".to_string()
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FunctionDefinition {
    pub name: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub parameters: Option<serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolCall {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub index: Option<usize>,
    #[serde(default)]
    pub id: String,
    #[serde(rename = "type", default = "default_tool_type")]
    pub tool_type: String,
    pub function: FunctionCallData,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FunctionCallData {
    #[serde(default)]
    pub name: String,
    pub arguments: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChatMessage {
    pub role: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub content: Option<serde_json::Value>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub name: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub tool_calls: Option<Vec<ToolCall>>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub tool_call_id: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub reasoning_content: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResponseFormat {
    #[serde(rename = "type")]
    pub format_type: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub json_schema: Option<serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct StreamOptions {
    #[serde(default)]
    pub include_usage: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChatRequest {
    pub model: String,
    pub messages: Vec<ChatMessage>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub temperature: Option<f64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub top_p: Option<f64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub max_tokens: Option<i64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub max_completion_tokens: Option<i64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub max_output_tokens: Option<i64>,
    #[serde(default)]
    pub stream: bool,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub stream_options: Option<StreamOptions>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub stop: Option<serde_json::Value>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub tools: Option<Vec<Tool>>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub tool_choice: Option<serde_json::Value>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub response_format: Option<ResponseFormat>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub reasoning_effort: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct GoogleUsage {
    #[serde(rename = "promptTokenCount", default)]
    pub prompt: Option<i64>,
    #[serde(rename = "candidatesTokenCount", default)]
    pub candidates: Option<i64>,
    #[serde(rename = "totalTokenCount", default)]
    pub total: Option<i64>,
    #[serde(rename = "thoughtsTokenCount", default)]
    pub thoughts: Option<i64>,
    #[serde(rename = "cachedContentTokenCount", default)]
    pub cached_content: Option<i64>,
}

impl GoogleUsage {
    pub fn to_openai(&self) -> OpenAIUsage {
        let mut result = OpenAIUsage::default();
        if let Some(p) = self.prompt {
            result.prompt_tokens = p;
        }
        if let Some(c) = self.candidates {
            result.completion_tokens = c;
        }
        if let Some(t) = self.thoughts {
            result.completion_tokens += t;
            result.completion_tokens_details = Some(CompletionTokenDetails {
                reasoning_tokens: t,
            });
        }
        if let Some(total) = self.total {
            result.total_tokens = total;
            if let Some(prompt) = self.prompt {
                if total >= prompt {
                    result.completion_tokens = total - prompt;
                }
            }
        } else {
            result.total_tokens = result.prompt_tokens + result.completion_tokens;
        }
        if let Some(cached) = self.cached_content {
            if cached > 0 {
                result.prompt_tokens_details = Some(PromptTokenDetails {
                    cached_tokens: cached,
                });
            }
        }
        result
    }

    pub fn merge(&mut self, next: GoogleUsage) {
        if next.prompt.is_some() {
            self.prompt = next.prompt;
        }
        if next.candidates.is_some() {
            self.candidates = next.candidates;
        }
        if next.total.is_some() {
            self.total = next.total;
        }
        if next.thoughts.is_some() {
            self.thoughts = next.thoughts;
        }
        if next.cached_content.is_some() {
            self.cached_content = next.cached_content;
        }
    }

    pub fn has_any(&self) -> bool {
        self.prompt.is_some()
            || self.candidates.is_some()
            || self.total.is_some()
            || self.thoughts.is_some()
            || self.cached_content.is_some()
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct OpenAIUsage {
    pub prompt_tokens: i64,
    pub completion_tokens: i64,
    pub total_tokens: i64,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub prompt_tokens_details: Option<PromptTokenDetails>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub completion_tokens_details: Option<CompletionTokenDetails>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct PromptTokenDetails {
    pub cached_tokens: i64,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct CompletionTokenDetails {
    pub reasoning_tokens: i64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChatChoiceMessage {
    pub role: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub content: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub reasoning_content: Option<String>,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub tool_calls: Vec<ToolCall>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChatChoice {
    pub index: usize,
    pub message: ChatChoiceMessage,
    pub finish_reason: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChatResponse {
    pub id: String,
    pub object: String,
    pub created: i64,
    pub model: String,
    pub choices: Vec<ChatChoice>,
    pub usage: OpenAIUsage,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct StoredAntigravityAccountFile {
    pub accounts: Vec<StoredAntigravityAccount>,
}

#[derive(Debug, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct StoredAntigravityAccount {
    pub refresh_token: String,
    #[serde(default)]
    pub email: String,
    #[serde(default)]
    pub project_id: String,
    #[serde(default)]
    pub managed_project_id: String,
    #[serde(default)]
    pub enabled: Option<bool>,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct FetchAvailableModelsResponse {
    #[serde(default)]
    pub models: HashMap<String, AvailableModel>,
}

#[derive(Debug, Deserialize)]
pub struct GeminiCliQuotaResponse {
    #[serde(default)]
    pub buckets: Vec<GeminiCliQuotaBucket>,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct GeminiCliQuotaBucket {
    pub model_id: String,
    pub remaining_fraction: f64,
    #[serde(default)]
    pub reset_time: String,
}
