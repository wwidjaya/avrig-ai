use super::converter::{
    finish_reason, message_text, normalize_model_id, sanitize_gemini_schema,
    to_antigravity_request,
};
use super::quota::{clamp_fraction, quota_group};
use super::state::AppState;
use super::types::{ChatMessage, ChatRequest, Credentials, GoogleUsage};
use chrono::Utc;
use serde_json::json;
use std::path::PathBuf;

fn create_test_state() -> AppState {
    AppState::new(
        PathBuf::from(".test-token.json"),
        "test-client-id".to_string(),
        "test-secret".to_string(),
        Credentials {
            access_token: "test-token".to_string(),
            refresh_token: "test-refresh".to_string(),
            project: "test-project".to_string(),
            client_id: None,
            client_secret: None,
            email: Some("test@example.com".to_string()),
            expires_at: Utc::now() + chrono::Duration::hours(1),
        },
    )
}

#[tokio::test]
async fn test_to_antigravity_request() {
    let state = create_test_state();
    let temp = 0.25;
    let input = ChatRequest {
        model: "gemini-3.8-flash".to_string(),
        temperature: Some(temp),
        max_tokens: Some(64),
        messages: vec![
            ChatMessage {
                role: "system".to_string(),
                content: Some(json!("Be concise.")),
                name: None,
                tool_calls: None,
                tool_call_id: None,
                reasoning_content: None,
            },
            ChatMessage {
                role: "user".to_string(),
                content: Some(json!("Hi")),
                name: None,
                tool_calls: None,
                tool_call_id: None,
                reasoning_content: None,
            },
            ChatMessage {
                role: "assistant".to_string(),
                content: Some(json!("Hello")),
                name: None,
                tool_calls: None,
                tool_call_id: None,
                reasoning_content: None,
            },
            ChatMessage {
                role: "user".to_string(),
                content: Some(json!("How are you?")),
                name: None,
                tool_calls: None,
                tool_call_id: None,
                reasoning_content: None,
            },
        ],
        top_p: None,
        max_completion_tokens: None,
        max_output_tokens: None,
        stream: false,
        stream_options: None,
        stop: None,
        tools: None,
        tool_choice: None,
        response_format: None,
        reasoning_effort: None,
    };

    let got = to_antigravity_request(&state, &input, "project-123")
        .await
        .expect("to_antigravity_request failed");

    assert_eq!(got["project"], "project-123");
    assert_eq!(got["model"], "gemini-3.8-flash");

    let request = &got["request"];
    let contents = request["contents"].as_array().expect("contents array");
    assert_eq!(contents.len(), 3);
    assert_eq!(contents[1]["role"], "model");

    // Verify system instruction is prepended to the first user message
    let first_turn = &contents[0];
    assert_eq!(first_turn["role"], "user");
    let parts = first_turn["parts"].as_array().expect("first parts array");
    assert_eq!(parts[0]["text"], "Be concise.\n\nHi");

    let config = &request["generationConfig"];
    assert_eq!(config["maxOutputTokens"], 64);
    assert_eq!(config["temperature"], temp);
    assert_eq!(config["thinkingConfig"]["includeThoughts"], true);
}

#[test]
fn test_message_text() {
    let got = message_text(&Some(json!([
        { "type": "text", "text": "one" },
        { "type": "text", "text": " two" }
    ])))
    .expect("message_text failed");
    assert_eq!(got, "one two");

    let string_got = message_text(&Some(json!("hello world"))).expect("string message_text failed");
    assert_eq!(string_got, "hello world");
}

#[test]
fn test_quota_group() {
    let tests = [
        ("claude-opus-5", "", "claude"),
        ("gemini-3.8-flash-medium", "Gemini Flash", "gemini-flash"),
        ("gemini-2.5-pro", "Gemini Pro", "gemini-pro"),
        ("gpt-oss-120b", "", ""),
    ];
    for (model, display, want) in tests {
        assert_eq!(quota_group(model, display), want);
    }
}

#[test]
fn test_clamp_fraction() {
    assert_eq!(clamp_fraction(-0.1), 0.0);
    assert_eq!(clamp_fraction(0.5), 0.5);
    assert_eq!(clamp_fraction(1.1), 1.0);
}

#[test]
fn test_google_usage_openai_includes_thought_tokens() {
    let usage = GoogleUsage {
        prompt: Some(8),
        candidates: Some(3),
        total: Some(68),
        thoughts: Some(57),
        cached_content: Some(2),
    };
    let got = usage.to_openai();
    assert_eq!(got.prompt_tokens, 8);
    assert_eq!(got.completion_tokens, 60);
    assert_eq!(got.total_tokens, 68);
    assert_eq!(
        got.completion_tokens_details
            .expect("completion token details")
            .reasoning_tokens,
        57
    );
    assert_eq!(
        got.prompt_tokens_details
            .expect("prompt token details")
            .cached_tokens,
        2
    );
}

#[test]
fn test_normalize_model_id() {
    assert_eq!(normalize_model_id("default"), "gemini-3.8-flash-tiered");
    assert_eq!(normalize_model_id(""), "gemini-3.8-flash-tiered");
    assert_eq!(
        normalize_model_id("provider/model-name"),
        "model-name"
    );
    assert_eq!(
        normalize_model_id("gemini-2.5-pro"),
        "gemini-2.5-pro"
    );
}

#[test]
fn test_finish_reason() {
    assert_eq!(finish_reason("MAX_TOKENS"), "length");
    assert_eq!(finish_reason("STOP"), "stop");
    assert_eq!(finish_reason("SAFETY"), "content_filter");
    assert_eq!(finish_reason("RECITATION"), "content_filter");
    assert_eq!(finish_reason("OTHER"), "stop");
}

#[test]
fn test_sanitize_gemini_schema() {
    let schema = json!({
        "type": ["string", "null"],
        "exclusiveMinimum": 5,
        "const": "constant_val",
        "description": "a field",
        "unsupportedField": "ignore me",
        "properties": {
            "sub": {
                "type": "integer",
                "exclusiveMaximum": 10,
                "extra": 123
            }
        }
    });

    let sanitized = sanitize_gemini_schema(schema);
    assert_eq!(sanitized["type"], "string");
    assert_eq!(sanitized["nullable"], true);
    assert_eq!(sanitized["minimum"], 5.0);
    assert_eq!(sanitized["enum"], json!(["constant_val"]));
    assert_eq!(sanitized["description"], "a field");
    assert!(sanitized.get("unsupportedField").is_none());

    let sub = &sanitized["properties"]["sub"];
    assert_eq!(sub["type"], "integer");
    assert_eq!(sub["maximum"], 9);
    assert!(sub.get("extra").is_none());
}

#[tokio::test]
async fn test_tool_calls_and_responses_conversion() {
    let state = create_test_state();

    let input = ChatRequest {
        model: "gemini-3.8-flash".to_string(),
        temperature: None,
        top_p: None,
        max_tokens: None,
        max_completion_tokens: None,
        max_output_tokens: None,
        stream: false,
        stream_options: None,
        stop: None,
        tools: Some(vec![super::types::Tool {
            tool_type: "function".to_string(),
            function: super::types::FunctionDefinition {
                name: "get_weather".to_string(),
                description: Some("Get weather info".to_string()),
                parameters: Some(json!({
                    "type": "object",
                    "properties": {
                        "location": { "type": "string" }
                    },
                    "required": ["location"]
                })),
            },
        }]),
        tool_choice: Some(json!("auto")),
        response_format: None,
        reasoning_effort: None,
        messages: vec![
            ChatMessage {
                role: "user".to_string(),
                content: Some(json!("What is the weather in Tokyo?")),
                name: None,
                tool_calls: None,
                tool_call_id: None,
                reasoning_content: None,
            },
            ChatMessage {
                role: "assistant".to_string(),
                content: None,
                name: None,
                tool_calls: Some(vec![super::types::ToolCall {
                    index: Some(0),
                    id: "call_tokyo_123".to_string(),
                    tool_type: "function".to_string(),
                    function: super::types::FunctionCallData {
                        name: "get_weather".to_string(),
                        arguments: "{\"location\":\"Tokyo\"}".to_string(),
                    },
                }]),
                tool_call_id: None,
                reasoning_content: None,
            },
            ChatMessage {
                role: "tool".to_string(),
                content: Some(json!("{\"temperature\": 22, \"condition\": \"Sunny\"}")),
                name: Some("get_weather".to_string()),
                tool_calls: None,
                tool_call_id: Some("call_tokyo_123".to_string()),
                reasoning_content: None,
            },
        ],
    };

    let got = to_antigravity_request(&state, &input, "test-project")
        .await
        .expect("to_antigravity_request failed");

    let req = &got["request"];
    assert!(req.get("tools").is_some());
    assert_eq!(
        req["toolConfig"]["functionCallingConfig"]["mode"],
        "AUTO"
    );

    let contents = req["contents"].as_array().expect("contents array");
    assert_eq!(contents.len(), 3);

    // Assistant call
    let model_turn = &contents[1];
    assert_eq!(model_turn["role"], "model");
    let model_part = &model_turn["parts"][0]["functionCall"];
    assert_eq!(model_part["name"], "get_weather");
    assert_eq!(model_part["args"]["location"], "Tokyo");
    assert_eq!(model_part["id"], "call_tokyo_123");
    // Since model is gemini, thoughtSignature should be present
    assert!(model_turn["parts"][0].get("thoughtSignature").is_some());

    // Tool response
    let tool_turn = &contents[2];
    assert_eq!(tool_turn["role"], "user");
    let tool_resp = &tool_turn["parts"][0]["functionResponse"];
    assert_eq!(tool_resp["name"], "get_weather");
    assert_eq!(tool_resp["id"], "call_tokyo_123");
    assert_eq!(tool_resp["response"]["condition"], "Sunny");

    // Tool response with non-object JSON (array, string, etc.) wrapped in object
    let tool_req_array = ChatRequest {
        model: "gemini-3.8-flash".to_string(),
        temperature: None,
        top_p: None,
        max_tokens: None,
        max_completion_tokens: None,
        max_output_tokens: None,
        stream: false,
        stream_options: None,
        stop: None,
        tools: None,
        tool_choice: None,
        response_format: None,
        reasoning_effort: None,
        messages: vec![ChatMessage {
            role: "tool".to_string(),
            content: Some(json!("[1, 2, 3]")),
            name: Some("list_items".to_string()),
            tool_calls: None,
            tool_call_id: Some("call_arr_123".to_string()),
            reasoning_content: None,
        }],
    };
    let got_arr = to_antigravity_request(&state, &tool_req_array, "test-project").await.unwrap();
    let resp_val = &got_arr["request"]["contents"][0]["parts"][0]["functionResponse"]["response"];
    assert!(resp_val.is_object());
    assert_eq!(resp_val["output"], json!([1, 2, 3]));
}

#[tokio::test]
async fn test_multimodal_image_url_conversion() {
    let state = create_test_state();

    let input = ChatRequest {
        model: "gemini-3.8-flash".to_string(),
        temperature: None,
        top_p: None,
        max_tokens: None,
        max_completion_tokens: None,
        max_output_tokens: None,
        stream: false,
        stream_options: None,
        stop: None,
        tools: None,
        tool_choice: None,
        response_format: None,
        reasoning_effort: None,
        messages: vec![ChatMessage {
            role: "user".to_string(),
            content: Some(json!([
                { "type": "text", "text": "Describe this image" },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
                    }
                }
            ])),
            name: None,
            tool_calls: None,
            tool_call_id: None,
            reasoning_content: None,
        }],
    };

    let got = to_antigravity_request(&state, &input, "test-project")
        .await
        .expect("to_antigravity_request failed");

    let parts = &got["request"]["contents"][0]["parts"];
    assert_eq!(parts[0]["text"], "Describe this image");
    assert_eq!(parts[1]["inlineData"]["mimeType"], "image/png");
    assert!(parts[1]["inlineData"]["data"].as_str().unwrap().starts_with("iVBORw0K"));
}

#[tokio::test]
async fn test_server_health_and_loopback_filter() {
    use axum::body::to_bytes;
    use axum::extract::connect_info::MockConnectInfo;
    use axum::http::{Request, StatusCode};
    use std::net::SocketAddr;
    use tower::ServiceExt;

    let state = create_test_state();
    let app = super::server::build_router(state);

    // 1. Loopback request -> Should succeed (200 OK)
    let loopback_addr: SocketAddr = "127.0.0.1:54321".parse().unwrap();
    let req = Request::builder()
        .uri("/health")
        .extension(MockConnectInfo(loopback_addr))
        .body(axum::body::Body::empty())
        .unwrap();

    let resp = app.clone().oneshot(req).await.unwrap();
    assert_eq!(resp.status(), StatusCode::OK);

    let bytes = to_bytes(resp.into_body(), 1024).await.unwrap();
    let health_json: serde_json::Value = serde_json::from_slice(&bytes).unwrap();
    assert_eq!(health_json["ok"], true);
    assert_eq!(health_json["provider"], "google-antigravity");
    assert_eq!(health_json["email"], "test@example.com");

    // 2. Non-loopback request -> Should be blocked (403 Forbidden)
    let external_addr: SocketAddr = "192.168.1.50:54321".parse().unwrap();
    let req_external = Request::builder()
        .uri("/health")
        .extension(MockConnectInfo(external_addr))
        .body(axum::body::Body::empty())
        .unwrap();

    let resp_blocked = app.oneshot(req_external).await.unwrap();
    assert_eq!(resp_blocked.status(), StatusCode::FORBIDDEN);
}
