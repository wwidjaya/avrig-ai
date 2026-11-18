use super::converter::{
    finish_reason, message_character_count, normalize_model_id, random_id, requested_max_tokens,
    to_antigravity_request,
};
use super::quota::{clamp_fraction, fetch_gemini_cli_quota, quota_group};
use super::state::AppState;
use super::types::{
    ChatChoice, ChatChoiceMessage, ChatRequest, ChatResponse, FetchAvailableModelsResponse,
    FunctionCallData, GATEWAY_URL, GoogleUsage, HUB_USER_AGENT, ToolCall, UpstreamError,
};
use axum::{
    Json, Router,
    body::Body,
    extract::{ConnectInfo, State},
    http::{HeaderMap, HeaderValue, StatusCode},
    middleware::{self, Next},
    response::{IntoResponse, Response},
    routing::{get, post},
};
use chrono::Utc;
use futures_util::StreamExt;
use serde_json::{Value, json};
use std::collections::HashMap;
use std::net::SocketAddr;
use tokio::time::Duration;
use tracing::{error, warn};

pub fn build_router(state: AppState) -> Router {
    Router::new()
        .route("/health", get(handle_health))
        .route("/v1/models", get(handle_models))
        .route("/v1/quota", get(handle_quota))
        .route("/v1/chat/completions", post(handle_chat_completions))
        .layer(middleware::from_fn(local_only))
        .with_state(state)
}

async fn local_only(
    ConnectInfo(addr): ConnectInfo<SocketAddr>,
    req: axum::extract::Request,
    next: Next,
) -> Result<Response, (StatusCode, &'static str)> {
    if !addr.ip().is_loopback() {
        return Err((StatusCode::FORBIDDEN, "localhost clients only"));
    }
    Ok(next.run(req).await)
}

fn api_error(status: StatusCode, kind: &str, message: &str) -> Response {
    let body = json!({
        "error": {
            "type": kind,
            "message": message,
        }
    });
    (status, Json(body)).into_response()
}

async fn available_models(state: &AppState) -> Result<Vec<String>, String> {
    {
        let cached = state.models.read().await;
        if let Some(list) = &*cached {
            return Ok(list.clone());
        }
    }

    if let Err(e) = state.refresh_token().await {
        return Err(format!("refresh token: {}", e));
    }

    let project = {
        let creds = state.creds.read().await;
        creds.project.clone()
    };

    let payload = json!({ "project": project });
    let resp_val = match state
        .google_post("/v1internal:fetchAvailableModels", &payload)
        .await
    {
        Ok(v) => v,
        Err(e) => return Err(e.to_string()),
    };

    let parsed: FetchAvailableModelsResponse = match serde_json::from_value(resp_val) {
        Ok(p) => p,
        Err(e) => return Err(format!("parse fetchAvailableModels: {}", e)),
    };

    if parsed.models.is_empty() {
        return Err("fetchAvailableModels returned no models".to_string());
    }

    let mut model_ids: Vec<String> = parsed.models.keys().cloned().collect();
    model_ids.sort();

    {
        let mut m = state.models.write().await;
        *m = Some(model_ids.clone());
    }
    {
        let mut mi = state.model_info.write().await;
        *mi = parsed.models;
    }

    Ok(model_ids)
}

pub async fn handle_health(State(state): State<AppState>) -> impl IntoResponse {
    let creds = state.creds.read().await;
    Json(json!({
        "ok": true,
        "provider": "google-antigravity",
        "email": creds.email,
    }))
}

pub async fn handle_models(State(state): State<AppState>) -> Response {
    let models = match tokio::time::timeout(Duration::from_secs(30), available_models(&state)).await
    {
        Ok(Ok(m)) => m,
        Ok(Err(e)) => return api_error(StatusCode::BAD_GATEWAY, "model_discovery_failed", &e),
        Err(_) => {
            return api_error(
                StatusCode::GATEWAY_TIMEOUT,
                "model_discovery_timeout",
                "timeout fetching models",
            );
        }
    };

    let data: Vec<Value> = models
        .into_iter()
        .map(|id| {
            json!({
                "id": id,
                "object": "model",
                "created": 0,
                "owned_by": "google-antigravity",
            })
        })
        .collect();

    Json(json!({
        "object": "list",
        "data": data,
    }))
    .into_response()
}

pub async fn handle_quota(State(state): State<AppState>) -> Response {
    // Invalidate model discovery cache to refresh upstream metadata
    {
        let mut m = state.models.write().await;
        *m = None;
    }

    if let Err(_e) = tokio::time::timeout(Duration::from_secs(15), available_models(&state)).await {
        return api_error(
            StatusCode::GATEWAY_TIMEOUT,
            "quota_fetch_timeout",
            "timeout fetching available models",
        );
    }

    let (model_info, project) = {
        let mi = state.model_info.read().await;
        let creds = state.creds.read().await;
        (mi.clone(), creds.project.clone())
    };

    let mut groups: HashMap<String, Value> = HashMap::new();
    let mut quota_model_count = 0;

    for (id, model) in &model_info {
        if model.disabled {
            continue;
        }
        let group_name = quota_group(id, model.display_name.as_deref().unwrap_or(""));
        if group_name.is_empty() {
            continue;
        }
        quota_model_count += 1;

        let entry = groups.entry(group_name.to_string()).or_insert_with(|| {
            json!({
                "modelCount": 0,
            })
        });

        let current_count = entry
            .get("modelCount")
            .and_then(|c| c.as_i64())
            .unwrap_or(0);
        entry["modelCount"] = json!(current_count + 1);

        if let Some(quota) = &model.quota_info {
            if let Some(rf) = quota.remaining_fraction {
                let fraction = clamp_fraction(rf);
                let existing_rf = entry.get("remainingFraction").and_then(|f| f.as_f64());
                if existing_rf.is_none() || fraction < existing_rf.unwrap() {
                    entry["remainingFraction"] = json!(fraction);
                    if let Some(reset) = &quota.reset_time {
                        entry["remainingFractionResetTime"] = json!(reset);
                    }
                }
            }
            if let Some(reset) = &quota.reset_time {
                if !reset.is_empty() {
                    let existing_reset = entry.get("resetTime").and_then(|s| s.as_str());
                    if existing_reset.is_none() || reset.as_str() < existing_reset.unwrap() {
                        entry["resetTime"] = json!(reset);
                    }
                }
            }
        }
    }

    let cli_res = fetch_gemini_cli_quota(&state, &project).await;
    let mut result = json!({
        "groups": groups,
        "modelCount": quota_model_count,
        "models": model_info,
    });

    match cli_res {
        Ok(quotas) => {
            result["geminiCliQuota"] = json!(quotas);
        }
        Err(e) => {
            result["geminiCliQuota"] = json!([]);
            result["geminiCliQuotaError"] = json!(e.to_string());
        }
    }

    Json(result).into_response()
}

pub async fn handle_chat_completions(
    State(state): State<AppState>,
    Json(mut input): Json<ChatRequest>,
) -> Response {
    input.model = normalize_model_id(&input.model);

    if input.stream {
        return stream_chat_completion(state, input).await;
    }

    if input.model.is_empty() || input.messages.is_empty() {
        return api_error(
            StatusCode::BAD_REQUEST,
            "invalid_request_error",
            "model and non-empty messages are required",
        );
    }

    let models = match available_models(&state).await {
        Ok(m) => m,
        Err(e) => return api_error(StatusCode::BAD_GATEWAY, "model_discovery_failed", &e),
    };

    if !models.contains(&input.model) {
        return api_error(
            StatusCode::BAD_REQUEST,
            "model_not_found",
            &format!(
                "Model \"{}\" is not in this account's available model list",
                input.model
            ),
        );
    }

    let project = {
        let creds = state.creds.read().await;
        creds.project.clone()
    };

    let payload = match to_antigravity_request(&state, &input, &project).await {
        Ok(p) => p,
        Err(e) => {
            return api_error(
                StatusCode::BAD_REQUEST,
                "invalid_request_error",
                &e.to_string(),
            );
        }
    };

    let upstream_resp = match tokio::time::timeout(
        Duration::from_secs(120),
        state.google_post("/v1internal:generateContent", &payload),
    )
    .await
    {
        Ok(Ok(val)) => val,
        Ok(Err(e)) => {
            error!("Antigravity generation failed: {}", e);
            return api_error(StatusCode::BAD_GATEWAY, "antigravity_error", &e.to_string());
        }
        Err(_) => {
            return api_error(
                StatusCode::GATEWAY_TIMEOUT,
                "antigravity_timeout",
                "timed out waiting for upstream response",
            );
        }
    };

    let resp_obj = match upstream_resp.get("response") {
        Some(r) => r,
        None => {
            return api_error(
                StatusCode::BAD_GATEWAY,
                "empty_response",
                "Antigravity returned no response envelope",
            );
        }
    };

    let candidates = resp_obj
        .get("candidates")
        .and_then(|c| c.as_array())
        .cloned()
        .unwrap_or_default();

    if candidates.is_empty() {
        return api_error(
            StatusCode::BAD_GATEWAY,
            "empty_response",
            "Antigravity returned no candidates",
        );
    }

    let candidate = &candidates[0];
    let mut content_builder = String::new();
    let mut reasoning_builder = String::new();
    let mut tool_calls: Vec<ToolCall> = Vec::new();

    if let Some(parts) = candidate
        .get("content")
        .and_then(|c| c.get("parts"))
        .and_then(|p| p.as_array())
    {
        for part in parts {
            let is_thought = part
                .get("thought")
                .and_then(|t| t.as_bool())
                .unwrap_or(false);
            let text = part.get("text").and_then(|t| t.as_str()).unwrap_or("");
            if is_thought {
                reasoning_builder.push_str(text);
            } else if !text.is_empty() {
                content_builder.push_str(text);
            }

            if let Some(fc) = part.get("functionCall") {
                let name = fc
                    .get("name")
                    .and_then(|n| n.as_str())
                    .unwrap_or("")
                    .to_string();
                let mut id = fc
                    .get("id")
                    .and_then(|i| i.as_str())
                    .unwrap_or("")
                    .to_string();
                if id.is_empty() {
                    id = format!("call_{}", random_id());
                }
                let sig = part
                    .get("thoughtSignature")
                    .and_then(|s| s.as_str())
                    .unwrap_or("");
                state.set_call_info(&id, &name, sig).await;

                let args_val = fc.get("args").cloned().unwrap_or(json!({}));
                let args_str =
                    serde_json::to_string(&args_val).unwrap_or_else(|_| "{}".to_string());

                let tc_index = tool_calls.len();
                tool_calls.push(ToolCall {
                    index: Some(tc_index),
                    id,
                    tool_type: "function".to_string(),
                    function: FunctionCallData {
                        name,
                        arguments: args_str,
                    },
                });
            }
        }
    }

    let response_id = resp_obj
        .get("responseId")
        .and_then(|r| r.as_str())
        .filter(|s| !s.is_empty())
        .map(|s| s.to_string())
        .unwrap_or_else(|| format!("chatcmpl-{}", random_id()));

    let model_version = resp_obj
        .get("modelVersion")
        .and_then(|m| m.as_str())
        .filter(|s| !s.is_empty())
        .unwrap_or(&input.model)
        .to_string();

    let candidate_finish = candidate
        .get("finishReason")
        .and_then(|f| f.as_str())
        .unwrap_or("");
    let mut finish = finish_reason(candidate_finish);
    if !tool_calls.is_empty() {
        finish = "tool_calls".to_string();
    }

    let mut choice_msg = ChatChoiceMessage {
        role: "assistant".to_string(),
        content: None,
        reasoning_content: if !reasoning_builder.is_empty() {
            Some(reasoning_builder)
        } else {
            None
        },
        tool_calls: tool_calls.clone(),
    };

    if !content_builder.is_empty() || tool_calls.is_empty() {
        choice_msg.content = Some(content_builder);
    }

    let google_usage: GoogleUsage = resp_obj
        .get("usageMetadata")
        .and_then(|u| serde_json::from_value(u.clone()).ok())
        .unwrap_or_default();

    let response = ChatResponse {
        id: response_id,
        object: "chat.completion".to_string(),
        created: Utc::now().timestamp(),
        model: model_version,
        choices: vec![ChatChoice {
            index: 0,
            message: choice_msg,
            finish_reason: finish,
        }],
        usage: google_usage.to_openai(),
    };

    Json(response).into_response()
}

async fn stream_chat_completion(state: AppState, input: ChatRequest) -> Response {
    if input.model.is_empty() || input.messages.is_empty() {
        return api_error(
            StatusCode::BAD_REQUEST,
            "invalid_request_error",
            "model and non-empty messages are required",
        );
    }

    let models = match available_models(&state).await {
        Ok(m) => m,
        Err(e) => return api_error(StatusCode::BAD_GATEWAY, "model_discovery_failed", &e),
    };

    if !models.contains(&input.model) {
        return api_error(
            StatusCode::BAD_REQUEST,
            "model_not_found",
            &format!(
                "Model \"{}\" is not in this account's available model list",
                input.model
            ),
        );
    }

    let project = {
        let creds = state.creds.read().await;
        creds.project.clone()
    };

    let payload = match to_antigravity_request(&state, &input, &project).await {
        Ok(p) => p,
        Err(e) => {
            return api_error(
                StatusCode::BAD_REQUEST,
                "invalid_request_error",
                &e.to_string(),
            );
        }
    };

    if let Err(e) = state.refresh_token().await {
        return api_error(StatusCode::BAD_GATEWAY, "oauth_error", &e.to_string());
    }

    let access_token = {
        let creds = state.creds.read().await;
        creds.access_token.clone()
    };

    let url = format!("{}/v1internal:streamGenerateContent?alt=sse", GATEWAY_URL);

    let stream_client = reqwest::Client::builder()
        .timeout(Duration::from_secs(300))
        .build()
        .unwrap_or_else(|_| state.http.clone());

    let resp = match stream_client
        .post(&url)
        .header("Authorization", format!("Bearer {}", access_token))
        .header("Content-Type", "application/json")
        .header("Accept", "text/event-stream")
        .header("User-Agent", HUB_USER_AGENT)
        .json(&payload)
        .send()
        .await
    {
        Ok(r) => r,
        Err(e) => {
            return api_error(
                StatusCode::BAD_GATEWAY,
                "antigravity_transport_error",
                &e.to_string(),
            );
        }
    };

    let status = resp.status();
    if !status.is_success() {
        let body = resp.text().await.unwrap_or_default();
        warn!(
            "Antigravity stream rejected: status={} model={} project={} messages={} prompt_chars={} max_output_tokens={} body={}",
            status.as_u16(),
            input.model,
            project,
            input.messages.len(),
            message_character_count(&input.messages),
            requested_max_tokens(&input),
            body.trim()
        );

        let mut message = body.trim().to_string();
        if let Ok(api_err) = serde_json::from_str::<UpstreamError>(&body) {
            if !api_err.error.message.is_empty() {
                message = api_err.error.message;
                if !api_err.error.details.is_empty() {
                    if let Ok(details) = serde_json::to_string(&api_err.error.details) {
                        message = format!("{} details={}", message, details);
                    }
                }
                if !api_err.error.status.is_empty() {
                    message = format!("{}: {}", api_err.error.status, message);
                }
            }
        }
        return api_error(
            StatusCode::BAD_GATEWAY,
            "antigravity_error",
            &format!("upstream HTTP {}: {}", status.as_u16(), message),
        );
    }

    let completion_id = format!("chatcmpl-{}", random_id());
    let created = Utc::now().timestamp();
    let initial_model = input.model.clone();

    // Stream transformation using an async generator / channel
    let (tx, rx) = tokio::sync::mpsc::channel::<Result<String, axum::Error>>(64);

    tokio::spawn(async move {
        let completion_id = completion_id;
        let mut current_model = initial_model;
        let mut usage = GoogleUsage::default();
        let mut finish_reason_value: Option<String> = None;
        let mut had_tool_calls = false;
        let mut tool_call_index = 0usize;

        let write_chunk = |delta: Value, finish: Option<String>, model: &str| -> String {
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

        // Emit initial role chunk
        let initial_chunk = write_chunk(json!({ "role": "assistant" }), None, &current_model);
        if tx.send(Ok(initial_chunk)).await.is_err() {
            return;
        }

        let mut byte_stream = resp.bytes_stream();
        let mut buffer = String::new();

        while let Some(chunk_res) = byte_stream.next().await {
            let chunk_bytes = match chunk_res {
                Ok(b) => b,
                Err(e) => {
                    error!("Antigravity stream read error: {}", e);
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

                let resp_val = match event.get("response") {
                    Some(r) => r,
                    None => continue,
                };

                if let Some(mv) = resp_val.get("modelVersion").and_then(|m| m.as_str()) {
                    if !mv.is_empty() {
                        current_model = mv.to_string();
                    }
                }

                if let Some(u) = resp_val.get("usageMetadata") {
                    if let Ok(next_usage) = serde_json::from_value::<GoogleUsage>(u.clone()) {
                        usage.merge(next_usage);
                    }
                }

                let candidates = resp_val
                    .get("candidates")
                    .and_then(|c| c.as_array())
                    .cloned()
                    .unwrap_or_default();

                if candidates.is_empty() {
                    continue;
                }

                let candidate = &candidates[0];
                if let Some(parts) = candidate
                    .get("content")
                    .and_then(|c| c.get("parts"))
                    .and_then(|p| p.as_array())
                {
                    for part in parts {
                        let is_thought = part
                            .get("thought")
                            .and_then(|t| t.as_bool())
                            .unwrap_or(false);
                        let text = part.get("text").and_then(|t| t.as_str()).unwrap_or("");
                        if is_thought && !text.is_empty() {
                            let msg = write_chunk(
                                json!({ "reasoning_content": text }),
                                None,
                                &current_model,
                            );
                            if tx.send(Ok(msg)).await.is_err() {
                                return;
                            }
                        } else if !text.is_empty() {
                            let msg = write_chunk(json!({ "content": text }), None, &current_model);
                            if tx.send(Ok(msg)).await.is_err() {
                                return;
                            }
                        }

                        if let Some(fc) = part.get("functionCall") {
                            had_tool_calls = true;
                            let name = fc
                                .get("name")
                                .and_then(|n| n.as_str())
                                .unwrap_or("")
                                .to_string();
                            let mut id = fc
                                .get("id")
                                .and_then(|i| i.as_str())
                                .unwrap_or("")
                                .to_string();
                            if id.is_empty() {
                                id = format!("call_{}", random_id());
                            }
                            let sig = part
                                .get("thoughtSignature")
                                .and_then(|s| s.as_str())
                                .unwrap_or("");
                            state.set_call_info(&id, &name, sig).await;

                            let args_val = fc.get("args").cloned().unwrap_or(json!({}));
                            let args_str = serde_json::to_string(&args_val)
                                .unwrap_or_else(|_| "{}".to_string());

                            let tc_delta = json!([{
                                "index": tool_call_index,
                                "id": id,
                                "type": "function",
                                "function": {
                                    "name": name,
                                    "arguments": args_str,
                                }
                            }]);
                            tool_call_index += 1;

                            let msg = write_chunk(
                                json!({ "tool_calls": tc_delta }),
                                None,
                                &current_model,
                            );
                            if tx.send(Ok(msg)).await.is_err() {
                                return;
                            }
                        }
                    }
                }

                if let Some(fr) = candidate.get("finishReason").and_then(|f| f.as_str()) {
                    if !fr.is_empty() {
                        finish_reason_value = Some(finish_reason(fr));
                    }
                }
            }
        }

        let final_finish = if had_tool_calls {
            "tool_calls".to_string()
        } else {
            finish_reason_value.unwrap_or_else(|| "stop".to_string())
        };

        // Emit finish reason chunk
        let finish_chunk = write_chunk(json!({}), Some(final_finish), &current_model);
        if tx.send(Ok(finish_chunk)).await.is_err() {
            return;
        }

        // Emit usage chunk if present
        if usage.has_any() {
            let openai_usage = usage.to_openai();
            let usage_chunk = json!({
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": current_model,
                "choices": [],
                "usage": openai_usage,
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
    headers.insert(
        axum::http::HeaderName::from_static("x-accel-buffering"),
        HeaderValue::from_static("no"),
    );

    (headers, body).into_response()
}
