#[cfg(test)]
mod tests {
    use super::super::client::{SiwcClient, parse_model_slugs};
    use super::super::types::StoredCredentials;
    use crate::antigravity::types::{ChatMessage, ChatRequest, FunctionCallData, FunctionDefinition, Tool, ToolCall};
    use crate::server::{GatewayState, build_gateway_router, is_siwc_model};
    use axum::body::to_bytes;
    use axum::extract::connect_info::MockConnectInfo;
    use axum::http::{Request, StatusCode};
    use chrono::Utc;
    use serde_json::json;
    use std::net::SocketAddr;
    use std::path::PathBuf;
    use tower::ServiceExt;

    #[test]
    fn test_is_siwc_model() {
        assert!(is_siwc_model("chatgpt/gpt-5.6-luna"));
        assert!(is_siwc_model("chatgpt-gpt-4o"));
        assert!(is_siwc_model("chatgpt:gpt-4o-mini"));
        assert!(is_siwc_model("gpt-5.6-luna"));
        assert!(is_siwc_model("gpt-4o"));
        assert!(is_siwc_model("gpt-4o-mini"));
        assert!(is_siwc_model("o1"));
        assert!(is_siwc_model("o3-mini"));
        assert!(is_siwc_model("chatgpt-4o-latest"));
        assert!(is_siwc_model("openai/gpt-4o"));

        // Google Antigravity models
        assert!(!is_siwc_model("agy/gemini-3.8-flash"));
        assert!(!is_siwc_model("agy-claude-sonnet-5-5"));
        assert!(!is_siwc_model("agy:gpt-oss-120b"));
        assert!(!is_siwc_model("gpt-oss-120b"));
        assert!(!is_siwc_model("gemini-3.8-flash"));
        assert!(!is_siwc_model("gemini-2.5-pro"));
        assert!(!is_siwc_model("claude-sonnet-5-5"));
        assert!(!is_siwc_model("default"));
    }

    #[test]
    fn test_parse_dynamic_model_catalog() {
        let catalog = json!({
            "models": [
                {"slug": "gpt-6-luna", "display_name": "GPT-6 Luna"},
                {"slug": "gpt-5.6-luna"},
                {"slug": "gpt-6-luna"},
                {"display_name": "Missing slug"},
                {"slug": ""}
            ]
        });
        assert_eq!(
            parse_model_slugs(&catalog),
            vec!["gpt-5.6-luna".to_string(), "gpt-6-luna".to_string()]
        );
    }

    #[test]
    fn test_to_responses_request_conversion() {
        let creds = StoredCredentials {
            access_token: "fake-tok".to_string(),
            refresh_token: Some("fake-ref".to_string()),
            client_id: "fake-client".to_string(),
            expires_at: Utc::now() + chrono::Duration::hours(1),
        };
        let client = SiwcClient::new(PathBuf::from("fake.json"), None, creds);

        let chat_req = ChatRequest {
            model: "gpt-5.6-luna".to_string(),
            messages: vec![
                ChatMessage {
                    role: "system".to_string(),
                    content: Some(json!("You are an AI assistant")),
                    name: None,
                    tool_calls: None,
                    tool_call_id: None,
                    reasoning_content: None,
                },
                ChatMessage {
                    role: "user".to_string(),
                    content: Some(json!("What is the weather?")),
                    name: None,
                    tool_calls: None,
                    tool_call_id: None,
                    reasoning_content: None,
                },
                ChatMessage {
                    role: "assistant".to_string(),
                    content: None,
                    name: None,
                    tool_calls: Some(vec![ToolCall {
                        index: Some(0),
                        id: "call_abc123".to_string(),
                        tool_type: "function".to_string(),
                        function: FunctionCallData {
                            name: "get_weather".to_string(),
                            arguments: "{\"city\":\"Jakarta\"}".to_string(),
                        },
                    }]),
                    tool_call_id: None,
                    reasoning_content: None,
                },
                ChatMessage {
                    role: "tool".to_string(),
                    content: Some(json!("{\"temp\": 30}")),
                    name: Some("get_weather".to_string()),
                    tool_calls: None,
                    tool_call_id: Some("call_abc123".to_string()),
                    reasoning_content: None,
                },
            ],
            temperature: None,
            top_p: None,
            max_tokens: None,
            max_completion_tokens: None,
            max_output_tokens: None,
            stream: false,
            stream_options: None,
            stop: None,
            tools: Some(vec![Tool {
                tool_type: "function".to_string(),
                function: FunctionDefinition {
                    name: "get_weather".to_string(),
                    description: Some("Fetch weather".to_string()),
                    parameters: Some(json!({"type": "object"})),
                },
            }]),
            tool_choice: Some(json!("auto")),
            response_format: None,
            reasoning_effort: None,
        };

        let responses_req = client.to_responses_request(&chat_req).expect("conversion");

        assert_eq!(responses_req["model"], "gpt-5.6-luna");
        assert_eq!(responses_req["stream"], true);
        assert_eq!(responses_req["store"], false);

        let input_arr = responses_req["input"].as_array().expect("input array");
        assert_eq!(input_arr.len(), 4);

        // System
        assert_eq!(input_arr[0]["role"], "system");
        assert_eq!(input_arr[0]["content"], "You are an AI assistant");

        // User
        assert_eq!(input_arr[1]["role"], "user");
        assert_eq!(input_arr[1]["content"], "What is the weather?");

        // Assistant function_call
        assert_eq!(input_arr[2]["type"], "function_call");
        assert_eq!(input_arr[2]["call_id"], "call_abc123");
        assert_eq!(input_arr[2]["name"], "get_weather");
        assert_eq!(input_arr[2]["arguments"], "{\"city\":\"Jakarta\"}");

        // Tool function_call_output
        assert_eq!(input_arr[3]["type"], "function_call_output");
        assert_eq!(input_arr[3]["call_id"], "call_abc123");
        assert_eq!(input_arr[3]["output"], "{\"temp\": 30}");

        // Tools
        let tools_arr = responses_req["tools"].as_array().expect("tools array");
        assert_eq!(tools_arr[0]["name"], "get_weather");
    }

    #[tokio::test]
    async fn test_unified_gateway_server() {
        let fake_creds = StoredCredentials {
            access_token: "fake-tok".to_string(),
            refresh_token: Some("fake-ref".to_string()),
            client_id: "fake-client".to_string(),
            expires_at: Utc::now() + chrono::Duration::hours(1),
        };
        let siwc = SiwcClient::new(PathBuf::from("fake.json"), None, fake_creds);

        let gateway_state = GatewayState {
            antigravity: None,
            siwc: Some(siwc),
        };

        let app = build_gateway_router(gateway_state);

        // Test /health
        let loopback_addr: SocketAddr = "127.0.0.1:54321".parse().unwrap();
        let req = Request::builder()
            .uri("/health")
            .extension(MockConnectInfo(loopback_addr))
            .body(axum::body::Body::empty())
            .unwrap();

        let resp = app.clone().oneshot(req).await.unwrap();
        assert_eq!(resp.status(), StatusCode::OK);

        let bytes = to_bytes(resp.into_body(), 1024).await.unwrap();
        let json_val: serde_json::Value = serde_json::from_slice(&bytes).unwrap();
        assert_eq!(json_val["ok"], true);
        assert_eq!(json_val["providers"][0], "openai-siwc");

        // Test /v1/models
        let req_models = Request::builder()
            .uri("/v1/models")
            .extension(MockConnectInfo(loopback_addr))
            .body(axum::body::Body::empty())
            .unwrap();

        let resp_models = app.clone().oneshot(req_models).await.unwrap();
        assert_eq!(resp_models.status(), StatusCode::OK);
        let bytes_m = to_bytes(resp_models.into_body(), 2048).await.unwrap();
        let json_models: serde_json::Value = serde_json::from_slice(&bytes_m).unwrap();
        let models_data = json_models["data"].as_array().expect("data array");
        assert!(
            models_data.iter().all(|model| {
                model["id"]
                    .as_str()
                    .is_some_and(|id| id.starts_with("agy/") || id.starts_with("chatgpt/"))
            }),
            "enumerated model IDs should carry their provider prefix"
        );
    }
}
