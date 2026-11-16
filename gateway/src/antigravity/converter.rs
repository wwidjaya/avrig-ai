use super::state::AppState;
use super::types::{ChatMessage, ChatRequest};
use anyhow::{Result, anyhow};
use base64::Engine;
use base64::engine::general_purpose::URL_SAFE_NO_PAD;
use rand::RngCore;
use serde_json::{Map, Value, json};

pub const ALLOWED_SCHEMA_FIELDS: &[&str] = &[
    "type",
    "format",
    "description",
    "nullable",
    "enum",
    "maxItems",
    "minItems",
    "properties",
    "required",
    "items",
    "minProperties",
    "maxProperties",
    "minimum",
    "maximum",
    "default",
    "title",
    "anyOf",
    "allOf",
    "oneOf",
    "not",
    "pattern",
    "minLength",
    "maxLength",
    "example",
    "additionalProperties",
];

pub fn normalize_model_id(model: &str) -> String {
    let mut m = model.trim();
    if let Some(idx) = m.rfind('/') {
        m = &m[idx + 1..];
    }
    if m == "default" || m.is_empty() {
        "gemini-3.8-flash-tiered".to_string()
    } else {
        m.to_string()
    }
}

pub fn finish_reason(value: &str) -> String {
    match value.to_ascii_uppercase().as_str() {
        "MAX_TOKENS" => "length".to_string(),
        "STOP" => "stop".to_string(),
        "SAFETY" | "RECITATION" => "content_filter".to_string(),
        _ => "stop".to_string(),
    }
}

pub fn random_id() -> String {
    let mut b = [0u8; 16];
    rand::thread_rng().fill_bytes(&mut b);
    URL_SAFE_NO_PAD.encode(b)
}

pub fn message_text(content: &Option<Value>) -> Result<String> {
    match content {
        Some(Value::String(s)) => Ok(s.clone()),
        Some(Value::Array(arr)) => {
            let mut out = String::new();
            for item in arr {
                if let Value::Object(map) = item {
                    if let Some(Value::String(s)) = map.get("text") {
                        out.push_str(s);
                    }
                }
            }
            Ok(out)
        }
        None | Some(Value::Null) => Ok(String::new()),
        Some(other) => Err(anyhow!("unsupported message content type: {}", other)),
    }
}

pub fn message_character_count(messages: &[ChatMessage]) -> usize {
    let mut total = 0;
    for message in messages {
        if let Ok(text) = message_text(&message.content) {
            total += text.len();
        }
    }
    total
}

pub fn requested_max_tokens(input: &ChatRequest) -> i64 {
    if let Some(mt) = input.max_tokens {
        if mt > 0 {
            return mt;
        }
    }
    if let Some(mct) = input.max_completion_tokens {
        if mct > 0 {
            return mct;
        }
    }
    input.max_output_tokens.unwrap_or(0)
}

pub fn sanitize_gemini_schema(val: Value) -> Value {
    match val {
        Value::Object(mut map) => {
            // Handle type array, e.g. ["string", "null"]
            if let Some(Value::Array(type_arr)) = map.get("type").cloned() {
                let mut non_null_types = Vec::new();
                let mut is_nullable = false;
                for t in type_arr {
                    if let Value::String(s) = t {
                        if s == "null" {
                            is_nullable = true;
                        } else {
                            non_null_types.push(s);
                        }
                    }
                }
                if is_nullable {
                    map.insert("nullable".to_string(), Value::Bool(true));
                }
                if non_null_types.len() == 1 {
                    map.insert(
                        "type".to_string(),
                        Value::String(non_null_types[0].clone()),
                    );
                } else if non_null_types.len() > 1 {
                    map.remove("type");
                    let any_of_list: Vec<Value> = non_null_types
                        .into_iter()
                        .map(|nnt| json!({ "type": nnt }))
                        .collect();
                    map.insert("anyOf".to_string(), Value::Array(any_of_list));
                } else {
                    map.insert("type".to_string(), Value::String("string".to_string()));
                }
            }

            // Handle exclusiveMinimum -> minimum
            if let Some(em) = map.get("exclusiveMinimum").cloned() {
                if !map.contains_key("minimum") {
                    let is_integer = map.get("type").and_then(|t| t.as_str()) == Some("integer");
                    if is_integer {
                        if let Some(num) = em.as_i64() {
                            map.insert("minimum".to_string(), Value::from(num + 1));
                        } else if let Some(num) = em.as_f64() {
                            map.insert("minimum".to_string(), Value::from(num + 1.0));
                        } else {
                            map.insert("minimum".to_string(), em);
                        }
                    } else {
                        map.insert("minimum".to_string(), em);
                    }
                }
            }

            // Handle exclusiveMaximum -> maximum
            if let Some(em) = map.get("exclusiveMaximum").cloned() {
                if !map.contains_key("maximum") {
                    let is_integer = map.get("type").and_then(|t| t.as_str()) == Some("integer");
                    if is_integer {
                        if let Some(num) = em.as_i64() {
                            map.insert("maximum".to_string(), Value::from(num - 1));
                        } else if let Some(num) = em.as_f64() {
                            map.insert("maximum".to_string(), Value::from(num - 1.0));
                        } else {
                            map.insert("maximum".to_string(), em);
                        }
                    } else {
                        map.insert("maximum".to_string(), em);
                    }
                }
            }

            // Handle const -> enum
            if let Some(c) = map.get("const").cloned() {
                if !map.contains_key("enum") {
                    map.insert("enum".to_string(), Value::Array(vec![c]));
                }
            }

            let mut result = Map::new();
            for (k, v) in map {
                if !ALLOWED_SCHEMA_FIELDS.contains(&k.as_str()) {
                    continue;
                }
                match k.as_str() {
                    "properties" => {
                        if let Value::Object(props) = v {
                            let mut clean_props = Map::new();
                            for (pk, pv) in props {
                                clean_props.insert(pk, sanitize_gemini_schema(pv));
                            }
                            result.insert(k, Value::Object(clean_props));
                        }
                    }
                    "items" => {
                        result.insert(k, sanitize_gemini_schema(v));
                    }
                    "anyOf" | "allOf" | "oneOf" => {
                        if let Value::Array(list) = v {
                            let clean_list: Vec<Value> =
                                list.into_iter().map(sanitize_gemini_schema).collect();
                            result.insert(k, Value::Array(clean_list));
                        }
                    }
                    "not" => {
                        result.insert(k, sanitize_gemini_schema(v));
                    }
                    _ => {
                        result.insert(k, v);
                    }
                }
            }
            Value::Object(result)
        }
        Value::Array(arr) => {
            let clean_arr: Vec<Value> = arr.into_iter().map(sanitize_gemini_schema).collect();
            Value::Array(clean_arr)
        }
        other => other,
    }
}

pub fn parse_user_content_parts(content: &Option<Value>) -> Vec<Value> {
    let mut parts = Vec::new();
    match content {
        Some(Value::String(s)) => {
            if !s.is_empty() {
                parts.push(json!({ "text": s }));
            }
        }
        Some(Value::Array(arr)) => {
            for item in arr {
                if let Value::Object(part_map) = item {
                    let part_type = part_map.get("type").and_then(|t| t.as_str()).unwrap_or("");
                    match part_type {
                        "text" => {
                            if let Some(text) = part_map.get("text").and_then(|t| t.as_str()) {
                                if !text.is_empty() {
                                    parts.push(json!({ "text": text }));
                                }
                            }
                        }
                        "image_url" => {
                            if let Some(Value::Object(img_map)) = part_map.get("image_url") {
                                if let Some(raw_url) = img_map.get("url").and_then(|u| u.as_str()) {
                                    if raw_url.starts_with("data:") {
                                        if let Some((meta, data)) = raw_url.split_once(',') {
                                            let mut mime = "image/jpeg";
                                            if let Some(semi) = meta.find(';') {
                                                if let Some(m) = meta[..semi].strip_prefix("data:") {
                                                    mime = m;
                                                }
                                            }
                                            parts.push(json!({
                                                "inlineData": {
                                                    "mimeType": mime,
                                                    "data": data,
                                                }
                                            }));
                                        }
                                    }
                                }
                            }
                        }
                        _ => {}
                    }
                }
            }
        }
        _ => {}
    }
    parts
}

pub async fn to_antigravity_request(
    state: &AppState,
    input: &ChatRequest,
    project: &str,
) -> Result<Value> {
    let mut contents: Vec<Value> = Vec::new();
    let mut system_parts: Vec<String> = Vec::new();

    for message in &input.messages {
        match message.role.as_str() {
            "system" | "developer" => {
                let text = message_text(&message.content)?;
                if !text.is_empty() {
                    system_parts.push(text);
                }
            }
            "user" => {
                let parts = parse_user_content_parts(&message.content);
                if !parts.is_empty() {
                    contents.push(json!({
                        "role": "user",
                        "parts": parts,
                    }));
                }
            }
            "assistant" => {
                let mut parts: Vec<Value> = Vec::new();
                let text = message_text(&message.content)?;
                if !text.is_empty() {
                    parts.push(json!({ "text": text }));
                }
                if let Some(tool_calls) = &message.tool_calls {
                    for tc in tool_calls {
                        let args: Value = serde_json::from_str(&tc.function.arguments)
                            .unwrap_or_else(|_| json!({ "raw": tc.function.arguments }));

                        let (cached_name, sig) = state.get_call_info(&tc.id).await;
                        let name = if !tc.function.name.is_empty() {
                            tc.function.name.clone()
                        } else {
                            cached_name
                        };
                        state.set_call_info(&tc.id, &name, &sig).await;

                        let mut fc_part = json!({
                            "functionCall": {
                                "name": name,
                                "args": args,
                                "id": tc.id,
                            }
                        });
                        if input.model.contains("gemini") {
                            fc_part["thoughtSignature"] = json!(sig);
                        }
                        parts.push(fc_part);
                    }
                }
                if !parts.is_empty() {
                    contents.push(json!({
                        "role": "model",
                        "parts": parts,
                    }));
                }
            }
            "tool" => {
                let tc_id = message.tool_call_id.clone().unwrap_or_default();
                let (cached_name, _) = state.get_call_info(&tc_id).await;
                let name = if let Some(n) = &message.name {
                    n.clone()
                } else {
                    cached_name
                };
                let raw_str = message_text(&message.content)?;
                let resp_obj: Value = match serde_json::from_str::<Value>(&raw_str) {
                    Ok(Value::Object(map)) => Value::Object(map),
                    Ok(val) => json!({ "output": val }),
                    Err(_) => json!({ "output": raw_str }),
                };

                let fr_part = json!({
                    "functionResponse": {
                        "name": name,
                        "response": resp_obj,
                        "id": tc_id,
                    }
                });

                // Merge consecutive tool responses into a single user turn
                let mut merged = false;
                if let Some(last_turn) = contents.last_mut() {
                    if last_turn.get("role").and_then(|r| r.as_str()) == Some("user") {
                        if let Some(parts_arr) = last_turn.get_mut("parts").and_then(|p| p.as_array_mut()) {
                            if parts_arr.first().and_then(|p| p.get("functionResponse")).is_some() {
                                parts_arr.push(fr_part.clone());
                                merged = true;
                            }
                        }
                    }
                }
                if !merged {
                    contents.push(json!({
                        "role": "user",
                        "parts": [fr_part],
                    }));
                }
            }
            other => return Err(anyhow!("unsupported message role \"{}\"", other)),
        }
    }

    let sys_text = system_parts
        .into_iter()
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty())
        .collect::<Vec<_>>()
        .join("\n\n");

    if contents.is_empty() {
        if !sys_text.is_empty() {
            contents.push(json!({
                "role": "user",
                "parts": [{ "text": sys_text }],
            }));
        } else {
            return Err(anyhow!("messages must include at least one message"));
        }
    } else if !sys_text.is_empty() {
        let mut prepended = false;
        for c in &mut contents {
            if c.get("role").and_then(|r| r.as_str()) == Some("user") {
                if let Some(parts) = c.get_mut("parts").and_then(|p| p.as_array_mut()) {
                    if let Some(first_part) = parts.first_mut() {
                        if let Some(orig_text) = first_part.get("text").and_then(|t| t.as_str()) {
                            let new_text = format!("{}\n\n{}", sys_text, orig_text);
                            first_part["text"] = json!(new_text);
                            prepended = true;
                            break;
                        }
                    }
                }
            }
        }
        if !prepended {
            contents.insert(
                0,
                json!({
                    "role": "user",
                    "parts": [{ "text": sys_text }],
                }),
            );
        }
    }

    let mut request = json!({
        "contents": contents,
    });

    // Tools
    if let Some(tools) = &input.tools {
        let mut decls: Vec<Value> = Vec::new();
        for tool in tools {
            if tool.tool_type == "function" || tool.tool_type.is_empty() {
                let mut decl = json!({
                    "name": tool.function.name,
                });
                if let Some(desc) = &tool.function.description {
                    decl["description"] = json!(desc);
                }
                if let Some(params) = &tool.function.parameters {
                    decl["parameters"] = sanitize_gemini_schema(params.clone());
                }
                decls.push(decl);
            }
        }
        if !decls.is_empty() {
            request["tools"] = json!([{
                "functionDeclarations": decls,
            }]);
        }
    }

    // Tool Choice
    if let Some(tc) = &input.tool_choice {
        match tc {
            Value::String(s) => match s.to_ascii_lowercase().as_str() {
                "none" => {
                    request["toolConfig"] = json!({
                        "functionCallingConfig": { "mode": "NONE" }
                    });
                }
                "auto" => {
                    request["toolConfig"] = json!({
                        "functionCallingConfig": { "mode": "AUTO" }
                    });
                }
                "required" => {
                    request["toolConfig"] = json!({
                        "functionCallingConfig": { "mode": "ANY" }
                    });
                }
                _ => {}
            },
            Value::Object(map) => {
                if let Some(Value::Object(fn_map)) = map.get("function") {
                    if let Some(name) = fn_map.get("name").and_then(|n| n.as_str()) {
                        if !name.is_empty() {
                            request["toolConfig"] = json!({
                                "functionCallingConfig": {
                                    "mode": "ANY",
                                    "allowedFunctionNames": [name],
                                }
                            });
                        }
                    }
                }
            }
            _ => {}
        }
    }

    // Generation Config
    let mut generation = json!({});
    if let Some(temp) = input.temperature {
        generation["temperature"] = json!(temp);
    }
    if let Some(top_p) = input.top_p {
        generation["topP"] = json!(top_p);
    }
    let max_tokens = requested_max_tokens(input);
    if max_tokens > 0 {
        generation["maxOutputTokens"] = json!(max_tokens);
    }
    if let Some(stop) = &input.stop {
        match stop {
            Value::String(s) if !s.is_empty() => {
                generation["stopSequences"] = json!([s]);
            }
            Value::Array(arr) if !arr.is_empty() => {
                let seqs: Vec<String> = arr
                    .iter()
                    .filter_map(|item| item.as_str().map(|s| s.to_string()))
                    .collect();
                if !seqs.is_empty() {
                    generation["stopSequences"] = json!(seqs);
                }
            }
            _ => {}
        }
    }
    if let Some(rf) = &input.response_format {
        match rf.format_type.to_ascii_lowercase().as_str() {
            "json_object" => {
                generation["responseMimeType"] = json!("application/json");
            }
            "json_schema" => {
                generation["responseMimeType"] = json!("application/json");
                if let Some(schema) = &rf.json_schema {
                    generation["responseSchema"] = sanitize_gemini_schema(schema.clone());
                }
            }
            _ => {}
        }
    }

    // Always include thoughts in generation config
    generation["thinkingConfig"] = json!({
        "includeThoughts": true,
    });

    request["generationConfig"] = generation;

    Ok(json!({
        "project": project,
        "model": input.model,
        "request": request,
        "userAgent": "antigravity",
        "requestType": "agent",
        "requestId": format!("agent-{}", random_id()),
    }))
}
