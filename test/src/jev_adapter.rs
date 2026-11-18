use reqwest::header::{AUTHORIZATION, CONTENT_TYPE, HeaderMap, HeaderValue};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::time::Duration;
use thiserror::Error;

/// Canonical 6 moods defined by the JEV decision model specification.
pub const CANONICAL_MOODS: [&str; 6] = [
    "calm",
    "dark",
    "energetic",
    "melancholy",
    "quirky",
    "romantic",
];

pub const DEFAULT_SYSTEMONE_ENDPOINT: &str = "https://opencode.ai/inference/systemone/v1/systemone";
pub const DEFAULT_MODEL_ID: &str = "jev-1.13";

#[derive(Debug, Error)]
pub enum JevError {
    #[error("HTTP request error: {0}")]
    Http(#[from] reqwest::Error),
    #[error("Serialization error: {0}")]
    Serialization(#[from] serde_json::Error),
    #[error("Upstream SystemOne error (status {status}): {body}")]
    UpstreamStatus { status: u16, body: String },
    #[error("Missing answer for question key: '{0}'")]
    MissingAnswer(String),
    #[error("Invalid configuration: {0}")]
    Config(String),
}

/// System One Choice Question specification.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct SystemOneChoiceQuestion {
    #[serde(rename = "type")]
    pub question_type: String,
    pub instructions: String,
    pub criteria: HashMap<String, String>,
}

/// Request body for the OpenCode Console System One API.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct SystemOneRequest {
    pub model: String,
    pub state: String,
    pub questions: HashMap<String, SystemOneChoiceQuestion>,
}

/// Individual answer returned by System One.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct SystemOneAnswer {
    #[serde(rename = "type")]
    pub answer_type: String,
    pub choice: String,
    pub confidence: f64,
    #[serde(default)]
    pub probabilities: HashMap<String, f64>,
}

/// Response payload from the OpenCode Console System One API.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct SystemOneResponse {
    pub model: String,
    pub answers: HashMap<String, SystemOneAnswer>,
}

/// Client configuration for the JEV decision model.
#[derive(Debug, Clone)]
pub struct JevConfig {
    pub endpoint: String,
    pub model: String,
    pub api_key: String,
    pub timeout: Duration,
}

impl JevConfig {
    pub fn new(api_key: impl Into<String>) -> Self {
        Self {
            endpoint: DEFAULT_SYSTEMONE_ENDPOINT.to_string(),
            model: DEFAULT_MODEL_ID.to_string(),
            api_key: api_key.into(),
            timeout: Duration::from_secs(60),
        }
    }

    pub fn from_env() -> Result<Self, JevError> {
        let api_key = std::env::var("OPENCODE_API_KEY")
            .or_else(|_| std::env::var("SYSTEMONE_API_KEY"))
            .map_err(|_| {
                JevError::Config(
                    "Neither OPENCODE_API_KEY nor SYSTEMONE_API_KEY is set in environment"
                        .to_string(),
                )
            })?;

        let endpoint = std::env::var("SYSTEMONE_ENDPOINT")
            .unwrap_or_else(|_| DEFAULT_SYSTEMONE_ENDPOINT.to_string());

        let model =
            std::env::var("SYSTEMONE_MODEL").unwrap_or_else(|_| DEFAULT_MODEL_ID.to_string());

        let timeout_secs = std::env::var("SYSTEMONE_TIMEOUT_SECS")
            .ok()
            .and_then(|s| s.parse::<u64>().ok())
            .unwrap_or(60);

        Ok(Self {
            endpoint,
            model,
            api_key,
            timeout: Duration::from_secs(timeout_secs),
        })
    }
}

/// Client for interacting with the JEV System One decision model.
#[derive(Debug, Clone)]
pub struct JevDecisionClient {
    client: reqwest::Client,
    config: JevConfig,
}

impl JevDecisionClient {
    pub fn new(config: JevConfig) -> Result<Self, JevError> {
        let client = reqwest::Client::builder().timeout(config.timeout).build()?;

        Ok(Self { client, config })
    }

    /// Round a floating point number to 4 decimal places.
    pub fn round_precision(val: f64) -> f64 {
        if val.is_nan() || val.is_infinite() {
            return 0.0;
        }
        (val * 10000.0).round() / 10000.0
    }

    /// Build a standard 6-mood choice question payload according to the canonical specification.
    pub fn build_mood_request(model: &str, text: &str) -> SystemOneRequest {
        let mut criteria = HashMap::new();
        criteria.insert(
            "calm".to_string(),
            "Peaceful, serene, relaxed, gentle".to_string(),
        );
        criteria.insert(
            "dark".to_string(),
            "Grim, ominous, sinister, intense, heavy".to_string(),
        );
        criteria.insert(
            "energetic".to_string(),
            "High-energy, fast, vibrant, upbeat".to_string(),
        );
        criteria.insert(
            "melancholy".to_string(),
            "Sad, sorrowful, wistful, yearning".to_string(),
        );
        criteria.insert(
            "quirky".to_string(),
            "Playful, eccentric, unconventional, whimsical".to_string(),
        );
        criteria.insert(
            "romantic".to_string(),
            "Intimate, affectionate, loving, sentimental".to_string(),
        );

        let question = SystemOneChoiceQuestion {
            question_type: "choice".to_string(),
            instructions: "What is the primary mood conveyed by the text?".to_string(),
            criteria,
        };

        let mut questions = HashMap::new();
        questions.insert("mood".to_string(), question);

        SystemOneRequest {
            model: model.to_string(),
            state: text.to_string(),
            questions,
        }
    }

    /// Normalize probabilities from System One into all 6 canonical mood keys rounded to 4 decimals.
    pub fn normalize_mood_probabilities(answer: &SystemOneAnswer) -> HashMap<String, f64> {
        let mut result = HashMap::with_capacity(CANONICAL_MOODS.len());
        for &mood in &CANONICAL_MOODS {
            let prob = answer.probabilities.get(mood).copied().unwrap_or(0.0);
            result.insert(mood.to_string(), Self::round_precision(prob));
        }
        result
    }

    /// Evaluate text against the canonical 6-mood state space.
    pub async fn classify_mood(&self, text: &str) -> Result<HashMap<String, f64>, JevError> {
        let req_payload = Self::build_mood_request(&self.config.model, text);
        let resp = self.evaluate(&req_payload).await?;

        let mood_answer = resp
            .answers
            .get("mood")
            .ok_or_else(|| JevError::MissingAnswer("mood".to_string()))?;

        Ok(Self::normalize_mood_probabilities(mood_answer))
    }

    /// Submit a raw System One request to the configured upstream endpoint.
    pub async fn evaluate(
        &self,
        req_payload: &SystemOneRequest,
    ) -> Result<SystemOneResponse, JevError> {
        let mut headers = HeaderMap::new();
        headers.insert(CONTENT_TYPE, HeaderValue::from_static("application/json"));

        let auth_val = format!("Bearer {}", self.config.api_key);
        let mut auth_header = HeaderValue::from_str(&auth_val)
            .map_err(|e| JevError::Config(format!("Invalid characters in API key: {}", e)))?;
        auth_header.set_sensitive(true);
        headers.insert(AUTHORIZATION, auth_header);

        let response = self
            .client
            .post(&self.config.endpoint)
            .headers(headers)
            .json(req_payload)
            .send()
            .await?;

        let status = response.status();
        if !status.is_success() {
            let body = response.text().await.unwrap_or_default();
            return Err(JevError::UpstreamStatus {
                status: status.as_u16(),
                body,
            });
        }

        let resp_body: SystemOneResponse = response.json().await?;
        Ok(resp_body)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_round_precision() {
        assert_eq!(JevDecisionClient::round_precision(0.123456), 0.1235);
        assert_eq!(JevDecisionClient::round_precision(0.12344), 0.1234);
        assert_eq!(JevDecisionClient::round_precision(0.0), 0.0);
        assert_eq!(JevDecisionClient::round_precision(1.0), 1.0);
        assert_eq!(JevDecisionClient::round_precision(f64::NAN), 0.0);
    }

    #[test]
    fn test_request_serialization() {
        let req = JevDecisionClient::build_mood_request(
            "jev-1.13",
            "The rain fell silently across the deserted platform.",
        );
        let json_str = serde_json::to_string(&req).expect("Failed to serialize request");

        assert!(json_str.contains("\"model\":\"jev-1.13\""));
        assert!(
            json_str.contains("\"state\":\"The rain fell silently across the deserted platform.\"")
        );
        assert!(json_str.contains("\"mood\":{"));
        assert!(json_str.contains("\"type\":\"choice\""));
        assert!(json_str.contains("\"calm\":\"Peaceful, serene, relaxed, gentle\""));
        assert!(json_str.contains("\"melancholy\":\"Sad, sorrowful, wistful, yearning\""));
    }

    #[test]
    fn test_response_deserialization_and_normalization() {
        let raw_json = r#"{
            "model": "jev-1.13",
            "answers": {
                "mood": {
                    "type": "choice",
                    "choice": "melancholy",
                    "confidence": 0.823456,
                    "probabilities": {
                        "melancholy": 0.823456,
                        "calm": 0.10001,
                        "dark": 0.05555,
                        "energetic": 0.01001,
                        "quirky": 0.00502,
                        "romantic": 0.00596
                    }
                }
            }
        }"#;

        let resp: SystemOneResponse =
            serde_json::from_str(raw_json).expect("Deserialization failed");
        assert_eq!(resp.model, "jev-1.13");
        let mood_ans = resp.answers.get("mood").expect("mood answer expected");
        assert_eq!(mood_ans.choice, "melancholy");

        let normalized = JevDecisionClient::normalize_mood_probabilities(mood_ans);
        assert_eq!(normalized.len(), 6);
        assert_eq!(normalized.get("melancholy").copied(), Some(0.8235));
        assert_eq!(normalized.get("calm").copied(), Some(0.1000));
        assert_eq!(normalized.get("dark").copied(), Some(0.0556));
        assert_eq!(normalized.get("energetic").copied(), Some(0.0100));
        assert_eq!(normalized.get("quirky").copied(), Some(0.0050));
        assert_eq!(normalized.get("romantic").copied(), Some(0.0060));
    }

    #[test]
    fn test_normalization_with_missing_keys() {
        let answer = SystemOneAnswer {
            answer_type: "choice".to_string(),
            choice: "calm".to_string(),
            confidence: 0.9,
            probabilities: {
                let mut map = HashMap::new();
                map.insert("calm".to_string(), 0.9);
                map
            },
        };

        let normalized = JevDecisionClient::normalize_mood_probabilities(&answer);
        assert_eq!(normalized.len(), 6);
        assert_eq!(normalized.get("calm").copied(), Some(0.9000));
        assert_eq!(normalized.get("dark").copied(), Some(0.0));
        assert_eq!(normalized.get("melancholy").copied(), Some(0.0));
    }

    #[test]
    fn test_missing_mood_answer_error() {
        let resp = SystemOneResponse {
            model: "jev-1.13".to_string(),
            answers: HashMap::new(),
        };

        let err = resp
            .answers
            .get("mood")
            .ok_or_else(|| JevError::MissingAnswer("mood".to_string()));
        assert!(matches!(err, Err(JevError::MissingAnswer(_))));
    }
}
