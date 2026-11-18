use super::oauth::{refresh_access_token, save_credentials};
use super::types::{DEFAULT_TOKEN_URL, StoredCredentials};
use crate::antigravity::converter::{message_text, random_id};
use crate::antigravity::types::{
    ChatChoice, ChatChoiceMessage, ChatRequest, ChatResponse, FunctionCallData, OpenAIUsage,
    ToolCall,
};
use anyhow::{Context, Result, anyhow};
use axum::{
    Json,
    body::Body,
    http::{HeaderMap, HeaderValue, StatusCode},
    response::{IntoResponse, Response},
};
use chrono::{Duration, Utc};
use futures_util::StreamExt;
use serde_json::{Value, json};
use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::Arc;
use tokio::sync::RwLock;
use tracing::error;

#[derive(Clone)]
pub struct SiwcClient {
    pub creds_path: PathBuf,
    pub token_url: String,
    pub creds: Arc<RwLock<StoredCredentials>>,
    pub http: reqwest::Client,
}

impl SiwcClient {
    pub fn new(creds_path: PathBuf, token_url: Option<String>, creds: StoredCredentials) -> Self {
        let http = reqwest::Client::builder()
            .timeout(std::time::Duration::from_secs(300))
            .build()
            .expect("build reqwest client");

        Self {
            creds_path,
            token_url: token_url.unwrap_or_else(|| DEFAULT_TOKEN_URL.to_string()),
            creds: Arc::new(RwLock::new(creds)),
            http,
        }
    }

    pub async fn get_valid_access_token(&self) -> Result<String> {
        let (needs_refresh, creds_clone) = {
            let creds = self.creds.read().await;
            let expired = (creds.expires_at - Utc::now()) < Duration::seconds(60);
            (expired, creds.clone())
        };

        if !needs_refresh {
            return Ok(creds_clone.access_token);
        }

        let new_creds = refresh_access_token(&self.http, &self.token_url, &creds_clone).await?;
        let token = new_creds.access_token.clone();
        {
            let mut creds = self.creds.write().await;
            *creds = new_creds.clone();
        }
        let _ = save_credentials(&self.creds_path, &new_creds);
        Ok(token)
    }

    pub async fn available_models(&self) -> Result<Vec<String>> {
        let access_token = self.get_valid_access_token().await?;
        let response = self
            .http
            .get("https://api.openai.com/v1/models")
            .bearer_auth(access_token)
            .send()
            .await
            .context("request SIWC model catalog")?;
        let status = response.status();
        let body = response.text().await?;
        if !status.is_success() {
            return Err(anyhow!(
                "SIWC model catalog returned HTTP {}: {}",
                status,
                body
            ));
        }

        let catalog: Value =
            serde_json::from_str(&body).context("parse SIWC model catalog response")?;
        Ok(parse_model_slugs(&catalog))
    }

    pub fn to_responses_request(&self, input: &ChatRequest) -> Result<Value> {
        let mut input_items: Vec<Value> = Vec::new();

        for msg in &input.messages {
            match msg.role.as_str() {
                "system" | "developer" => {
                    let text = message_text(&msg.content)?;
                    if !text.is_empty() {
                        input_items.push(json!({
                            "role": "system",
                            "content": text
                        }));
                    }
                }
                "user" => {
                    let text = message_text(&msg.content)?;
                    input_items.push(json!({
                        "role": "user",
                        "content": text
                    }));
                }
                "assistant" => {
                    if let Ok(text) = message_text(&msg.content) {
                        if !text.is_empty() {
                            input_items.push(json!({
                                "role": "assistant",
                                "content": text
                            }));
                        }
                    }
                    if let Some(tool_calls) = &msg.tool_calls {
                        for tc in tool_calls {
                            input_items.push(json!({
                                "type": "function_call",
                                "call_id": tc.id,
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            }));
                        }
                    }
                }
                "tool" => {
                    let text = message_text(&msg.content)?;
                    let call_id = msg.tool_call_id.clone().unwrap_or_default();
                    input_items.push(json!({
                        "type": "function_call_output",
                        "call_id": call_id,
                        "output": text,
                    }));
                }
                other => return Err(anyhow!("Unsupported role for SIWC ChatGPT: {}", other)),
            }
        }

        let mut payload = json!({
            "model": input.model,
            "input": input_items,
            "store": false,
            "stream": true,
        });

        if let Some(tools) = &input.tools {
            let mut tools_val = Vec::new();
            for t in tools {
                let mut f_obj = json!({
                    "type": "function",
                    "name": t.function.name,
                });
                if let Some(desc) = &t.function.description {
                    f_obj["description"] = json!(desc);
                }
                if let Some(params) = &t.function.parameters {
                    f_obj["parameters"] = params.clone();
                }
                tools_val.push(f_obj);
            }
            if !tools_val.is_empty() {
                payload["tools"] = json!(tools_val);
            }
        }

        if let Some(tc) = &input.tool_choice {
            payload["tool_choice"] = tc.clone();
        }

        Ok(payload)
    }

    pub async fn handle_chat_completions(&self, input: ChatRequest) -> Response {
        let access_token = match self.get_valid_access_token().await {
            Ok(tok) => tok,
            Err(e) => {
                return (
                    StatusCode::UNAUTHORIZED,
                    Json(json!({
                        "error": {
                            "type": "siwc_auth_error",
                            "message": format!("Failed to get valid SIWC token: {}", e),
                        }
                    })),
                )
                    .into_response();
            }
        };

        let responses_payload = match self.to_responses_request(&input) {
            Ok(p) => p,
            Err(e) => {
                return (
                    StatusCode::BAD_REQUEST,
                    Json(json!({
                        "error": {
                            "type": "invalid_request_error",
                            "message": e.to_string(),
                        }
                    })),
                )
                    .into_response();
            }
        };

        let upstream_resp = match self
            .http
            .post("https://api.openai.com/v1/responses")
            .bearer_auth(&access_token)
            .json(&responses_payload)
            .send()
            .await
        {
            Ok(r) => r,
            Err(e) => {
                return (
                    StatusCode::BAD_GATEWAY,
                    Json(json!({
                        "error": {
                            "type": "siwc_upstream_error",
                            "message": format!("Network error calling OpenAI /v1/responses: {}", e),
                        }
                    })),
                )
                    .into_response();
            }
        };

        let status = upstream_resp.status();
        if !status.is_success() {
            let body = upstream_resp.text().await.unwrap_or_default();
            error!("SIWC upstream error (HTTP {}): {}", status, body);
            return (
                status,
                Json(json!({
                    "error": {
                        "type": "upstream_error",
                        "message": body,
                    }
                })),
            )
                .into_response();
        }

        if input.stream {
            self.stream_sse(upstream_resp, input.model).await
        } else {
            self.collect_non_stream(upstream_resp, input.model).await
        }
    }

    async fn stream_sse(
        &self,
        upstream_resp: reqwest::Response,
        requested_model: String,
    ) -> Response {
        let completion_id = format!("chatcmpl-{}", random_id());
        let created = Utc::now().timestamp();

        let (tx, rx) = tokio::sync::mpsc::channel::<Result<String, axum::Error>>(64);

        tokio::spawn(async move {
            let write_chunk = |delta: Value, finish: Option<&str>, model: &str| -> String {
                let choice = json!({
                    "index": 0,
                    "delta": delta,
                    "finish_reason": finish,
                });
                let chunk = json!({
                    "id": completion_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": model,
                    "choices": [choice],
                });
                format!("data: {}\n\n", chunk)
            };

            // Initial role chunk
            let init_chunk = write_chunk(json!({ "role": "assistant" }), None, &requested_model);
            if tx.send(Ok(init_chunk)).await.is_err() {
                return;
            }

            let mut byte_stream = upstream_resp.bytes_stream();
            let mut buffer = String::new();
            let mut current_model = requested_model;
            let mut usage = OpenAIUsage::default();
            let mut finish_reason = "stop".to_string();
            let mut had_tool_calls = false;
            let mut tool_index_map: HashMap<usize, (String, String, usize)> = HashMap::new();
            let mut next_tool_index = 0usize;

            while let Some(chunk_res) = byte_stream.next().await {
                let chunk_bytes = match chunk_res {
                    Ok(b) => b,
                    Err(e) => {
                        error!("SIWC stream read error: {}", e);
                        break;
                    }
                };

                let chunk_str = String::from_utf8_lossy(&chunk_bytes);
                buffer.push_str(&chunk_str);

                while let Some(newline_pos) = buffer.find('\n') {
                    let line: String = buffer.drain(..=newline_pos).collect();
                    let trimmed = line.trim();
                    if !trimmed.starts_with("data:") {
                        continue;
                    }
                    let event_data = trimmed.trim_start_matches("data:").trim();
                    if event_data.is_empty() || event_data == "[DONE]" {
                        continue;
                    }

                    let event: Value = match serde_json::from_str(event_data) {
                        Ok(v) => v,
                        Err(_) => continue,
                    };

                    let event_type = event.get("type").and_then(|t| t.as_str()).unwrap_or("");
                    match event_type {
                        "response.created" | "response.in_progress" => {
                            if let Some(resp_obj) = event.get("response") {
                                if let Some(m) = resp_obj.get("model").and_then(|m| m.as_str()) {
                                    if !m.is_empty() {
                                        current_model = m.to_string();
                                    }
                                }
                            }
                        }
                        "response.output_text.delta" => {
                            if let Some(delta) = event.get("delta").and_then(|d| d.as_str()) {
                                if !delta.is_empty() {
                                    let chunk = write_chunk(
                                        json!({ "content": delta }),
                                        None,
                                        &current_model,
                                    );
                                    if tx.send(Ok(chunk)).await.is_err() {
                                        return;
                                    }
                                }
                            }
                        }
                        "response.output_item.added" => {
                            if let Some(item) = event.get("item") {
                                let item_type =
                                    item.get("type").and_then(|t| t.as_str()).unwrap_or("");
                                if item_type == "function_call" {
                                    had_tool_calls = true;
                                    let out_idx = event
                                        .get("output_index")
                                        .and_then(|i| i.as_u64())
                                        .unwrap_or(0)
                                        as usize;
                                    let call_id = item
                                        .get("call_id")
                                        .and_then(|i| i.as_str())
                                        .unwrap_or("")
                                        .to_string();
                                    let name = item
                                        .get("name")
                                        .and_then(|n| n.as_str())
                                        .unwrap_or("")
                                        .to_string();

                                    let client_index = next_tool_index;
                                    next_tool_index += 1;
                                    tool_index_map.insert(
                                        out_idx,
                                        (call_id.clone(), name.clone(), client_index),
                                    );

                                    let chunk = write_chunk(
                                        json!({
                                            "tool_calls": [{
                                                "index": client_index,
                                                "id": call_id,
                                                "type": "function",
                                                "function": {
                                                    "name": name,
                                                    "arguments": ""
                                                }
                                            }]
                                        }),
                                        None,
                                        &current_model,
                                    );
                                    if tx.send(Ok(chunk)).await.is_err() {
                                        return;
                                    }
                                }
                            }
                        }
                        "response.function_call_arguments.delta" => {
                            let out_idx = event
                                .get("output_index")
                                .and_then(|i| i.as_u64())
                                .unwrap_or(0) as usize;
                            if let Some(delta) = event.get("delta").and_then(|d| d.as_str()) {
                                let client_index = tool_index_map
                                    .get(&out_idx)
                                    .map(|(_, _, idx)| *idx)
                                    .unwrap_or(0);
                                let chunk = write_chunk(
                                    json!({
                                        "tool_calls": [{
                                            "index": client_index,
                                            "function": {
                                                "arguments": delta
                                            }
                                        }]
                                    }),
                                    None,
                                    &current_model,
                                );
                                if tx.send(Ok(chunk)).await.is_err() {
                                    return;
                                }
                            }
                        }
                        "response.completed" => {
                            if let Some(resp_obj) = event.get("response") {
                                if let Some(m) = resp_obj.get("model").and_then(|m| m.as_str()) {
                                    if !m.is_empty() {
                                        current_model = m.to_string();
                                    }
                                }
                                if let Some(u) = resp_obj.get("usage") {
                                    let input_toks =
                                        u.get("input_tokens").and_then(|i| i.as_i64()).unwrap_or(0);
                                    let output_toks = u
                                        .get("output_tokens")
                                        .and_then(|i| i.as_i64())
                                        .unwrap_or(0);
                                    let total_toks = u
                                        .get("total_tokens")
                                        .and_then(|i| i.as_i64())
                                        .unwrap_or(input_toks + output_toks);
                                    usage = OpenAIUsage {
                                        prompt_tokens: input_toks,
                                        completion_tokens: output_toks,
                                        total_tokens: total_toks,
                                        prompt_tokens_details: None,
                                        completion_tokens_details: None,
                                    };
                                }
                            }
                        }
                        _ => {}
                    }
                }
            }

            if had_tool_calls {
                finish_reason = "tool_calls".to_string();
            }

            // Emit finish reason chunk
            let finish_chunk = write_chunk(json!({}), Some(&finish_reason), &current_model);
            if tx.send(Ok(finish_chunk)).await.is_err() {
                return;
            }

            // Emit usage chunk
            if usage.total_tokens > 0 {
                let usage_chunk = json!({
                    "id": completion_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": current_model,
                    "choices": [],
                    "usage": usage,
                });
                let msg = format!("data: {}\n\n", usage_chunk);
                if tx.send(Ok(msg)).await.is_err() {
                    return;
                }
            }

            let _ = tx.send(Ok("data: [DONE]\n\n".to_string())).await;
        });

        let stream = tokio_stream::wrappers::ReceiverStream::new(rx);
        let body = Body::from_stream(stream);

        let mut headers = HeaderMap::new();
        headers.insert(
            axum::http::header::CONTENT_TYPE,
            HeaderValue::from_static("text/event-stream"),
        );
        headers.insert(
            axum::http::header::CACHE_CONTROL,
            HeaderValue::from_static("no-cache"),
        );
        headers.insert(
            axum::http::header::CONNECTION,
            HeaderValue::from_static("keep-alive"),
        );

        (headers, body).into_response()
    }

    async fn collect_non_stream(
        &self,
        upstream_resp: reqwest::Response,
        requested_model: String,
    ) -> Response {
        let completion_id = format!("chatcmpl-{}", random_id());
        let created = Utc::now().timestamp();

        let mut byte_stream = upstream_resp.bytes_stream();
        let mut buffer = String::new();
        let mut full_content = String::new();
        let mut current_model = requested_model;
        let mut usage = OpenAIUsage::default();
        let mut tool_calls: Vec<ToolCall> = Vec::new();
        let mut tool_args_map: HashMap<usize, (String, String, String)> = HashMap::new();

        while let Some(chunk_res) = byte_stream.next().await {
            let chunk_bytes = match chunk_res {
                Ok(b) => b,
                Err(e) => {
                    return (
                        StatusCode::BAD_GATEWAY,
                        Json(json!({
                            "error": {
                                "type": "stream_read_error",
                                "message": e.to_string(),
                            }
                        })),
                    )
                        .into_response();
                }
            };

            let chunk_str = String::from_utf8_lossy(&chunk_bytes);
            buffer.push_str(&chunk_str);

            while let Some(newline_pos) = buffer.find('\n') {
                let line: String = buffer.drain(..=newline_pos).collect();
                let trimmed = line.trim();
                if !trimmed.starts_with("data:") {
                    continue;
                }
                let event_data = trimmed.trim_start_matches("data:").trim();
                if event_data.is_empty() || event_data == "[DONE]" {
                    continue;
                }

                let event: Value = match serde_json::from_str(event_data) {
                    Ok(v) => v,
                    Err(_) => continue,
                };

                let event_type = event.get("type").and_then(|t| t.as_str()).unwrap_or("");
                match event_type {
                    "response.created" | "response.in_progress" => {
                        if let Some(resp_obj) = event.get("response") {
                            if let Some(m) = resp_obj.get("model").and_then(|m| m.as_str()) {
                                if !m.is_empty() {
                                    current_model = m.to_string();
                                }
                            }
                        }
                    }
                    "response.output_text.delta" => {
                        if let Some(delta) = event.get("delta").and_then(|d| d.as_str()) {
                            full_content.push_str(delta);
                        }
                    }
                    "response.output_item.added" => {
                        if let Some(item) = event.get("item") {
                            let item_type = item.get("type").and_then(|t| t.as_str()).unwrap_or("");
                            if item_type == "function_call" {
                                let out_idx = event
                                    .get("output_index")
                                    .and_then(|i| i.as_u64())
                                    .unwrap_or(0)
                                    as usize;
                                let call_id = item
                                    .get("call_id")
                                    .and_then(|i| i.as_str())
                                    .unwrap_or("")
                                    .to_string();
                                let name = item
                                    .get("name")
                                    .and_then(|n| n.as_str())
                                    .unwrap_or("")
                                    .to_string();
                                tool_args_map.insert(out_idx, (call_id, name, String::new()));
                            }
                        }
                    }
                    "response.function_call_arguments.delta" => {
                        let out_idx = event
                            .get("output_index")
                            .and_then(|i| i.as_u64())
                            .unwrap_or(0) as usize;
                        if let Some(delta) = event.get("delta").and_then(|d| d.as_str()) {
                            if let Some(entry) = tool_args_map.get_mut(&out_idx) {
                                entry.2.push_str(delta);
                            }
                        }
                    }
                    "response.function_call_arguments.done" => {
                        let out_idx = event
                            .get("output_index")
                            .and_then(|i| i.as_u64())
                            .unwrap_or(0) as usize;
                        if let Some(args) = event.get("arguments").and_then(|a| a.as_str()) {
                            if let Some(entry) = tool_args_map.get_mut(&out_idx) {
                                entry.2 = args.to_string();
                            }
                        }
                    }
                    "response.completed" => {
                        if let Some(resp_obj) = event.get("response") {
                            if let Some(m) = resp_obj.get("model").and_then(|m| m.as_str()) {
                                if !m.is_empty() {
                                    current_model = m.to_string();
                                }
                            }
                            if let Some(u) = resp_obj.get("usage") {
                                let input_toks =
                                    u.get("input_tokens").and_then(|i| i.as_i64()).unwrap_or(0);
                                let output_toks =
                                    u.get("output_tokens").and_then(|i| i.as_i64()).unwrap_or(0);
                                let total_toks = u
                                    .get("total_tokens")
                                    .and_then(|i| i.as_i64())
                                    .unwrap_or(input_toks + output_toks);
                                usage = OpenAIUsage {
                                    prompt_tokens: input_toks,
                                    completion_tokens: output_toks,
                                    total_tokens: total_toks,
                                    prompt_tokens_details: None,
                                    completion_tokens_details: None,
                                };
                            }
                        }
                    }
                    _ => {}
                }
            }
        }

        let mut sorted_indices: Vec<usize> = tool_args_map.keys().cloned().collect();
        sorted_indices.sort();
        for (i, out_idx) in sorted_indices.into_iter().enumerate() {
            if let Some((call_id, name, args)) = tool_args_map.remove(&out_idx) {
                tool_calls.push(ToolCall {
                    index: Some(i),
                    id: call_id,
                    tool_type: "function".to_string(),
                    function: FunctionCallData {
                        name,
                        arguments: args,
                    },
                });
            }
        }

        let finish_reason = if !tool_calls.is_empty() {
            "tool_calls".to_string()
        } else {
            "stop".to_string()
        };

        let message = ChatChoiceMessage {
            role: "assistant".to_string(),
            content: if !full_content.is_empty() || tool_calls.is_empty() {
                Some(full_content)
            } else {
                None
            },
            reasoning_content: None,
            tool_calls,
        };

        let chat_response = ChatResponse {
            id: completion_id,
            object: "chat.completion".to_string(),
            created,
            model: current_model,
            choices: vec![ChatChoice {
                index: 0,
                message,
                finish_reason,
            }],
            usage,
        };

        Json(chat_response).into_response()
    }
}

pub fn parse_model_slugs(catalog: &Value) -> Vec<String> {
    let Some(models) = catalog.get("models").and_then(Value::as_array) else {
        return Vec::new();
    };

    let mut slugs: Vec<String> = models
        .iter()
        .filter_map(|model| model.get("slug").and_then(Value::as_str))
        .filter(|slug| !slug.trim().is_empty())
        .map(str::to_string)
        .collect();
    slugs.sort();
    slugs.dedup();
    slugs
}
