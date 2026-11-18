use crate::antigravity::AppState as AntigravityState;
use crate::antigravity::server::local_only;
use crate::antigravity::types::ChatRequest;
use crate::siwc::client::SiwcClient;
use crate::version::VersionInfo;
use axum::{
    Json, Router,
    body::Body,
    extract::{Request, State},
    http::{HeaderValue, Method, StatusCode, header},
    middleware,
    response::{IntoResponse, Response},
    routing::{get, post},
};
use rust_embed::RustEmbed;
use serde_json::{Value, json};
use std::sync::Arc;
use tokio::time::Duration;
use tower_http::cors::{AllowOrigin, CorsLayer};
use tracing::info;

#[derive(RustEmbed)]
#[folder = "../apps/web/dist"]
struct WebAssets;

pub fn strip_model_prefix(model: &str) -> (Option<&str>, String) {
    let mut m = model.trim();
    if let Some(idx) = m.rfind('/') {
        m = &m[idx + 1..];
    }
    if let Some(rest) = m.strip_prefix("chatgpt/") {
        (Some("chatgpt"), rest.to_string())
    } else if let Some(rest) = m.strip_prefix("chatgpt-") {
        (Some("chatgpt"), rest.to_string())
    } else if let Some(rest) = m.strip_prefix("chatgpt:") {
        (Some("chatgpt"), rest.to_string())
    } else if let Some(rest) = m.strip_prefix("agy/") {
        (Some("agy"), rest.to_string())
    } else if let Some(rest) = m.strip_prefix("agy-") {
        (Some("agy"), rest.to_string())
    } else if let Some(rest) = m.strip_prefix("agy:") {
        (Some("agy"), rest.to_string())
    } else {
        (None, m.to_string())
    }
}

pub fn is_siwc_model(model: &str) -> bool {
    let (prefix, base) = strip_model_prefix(model);
    if let Some(p) = prefix {
        return p == "chatgpt";
    }

    let m = base.to_lowercase();
    if m == "gpt-oss-120b" {
        return false;
    }
    m.starts_with("gpt-")
        || m.starts_with("o1")
        || m.starts_with("o3")
        || m.starts_with("chatgpt")
        || m.starts_with("openai")
}

pub fn resolve_upstream_model_id(model: &str) -> String {
    let (prefix, base) = strip_model_prefix(model);
    match prefix {
        Some("chatgpt") => {
            if base.is_empty() || base == "default" {
                "gpt-5.6-luna".to_string()
            } else {
                base
            }
        }
        Some("agy") => {
            if base.is_empty() || base == "default" {
                "gemini-3.8-flash-tiered".to_string()
            } else {
                base
            }
        }
        _ => {
            if base.is_empty() || base == "default" {
                "gemini-3.8-flash-tiered".to_string()
            } else {
                base
            }
        }
    }
}

#[derive(Clone)]
pub struct GatewayState {
    pub antigravity: Option<AntigravityState>,
    pub siwc: Option<SiwcClient>,
}

pub fn build_gateway_router(state: GatewayState) -> Router {
    let cors = CorsLayer::new()
        .allow_origin(AllowOrigin::predicate(|origin: &HeaderValue, _| {
            if let Ok(s) = origin.to_str() {
                s == "https://app.avrig.ai"
                    || s == "tauri://localhost"
                    || s == "http://tauri.localhost"
                    || s == "capacitor://localhost"
                    || s == "http://localhost"
                    || s.starts_with("http://localhost:")
                    || s.starts_with("http://127.0.0.1:")
            } else {
                false
            }
        }))
        .allow_methods([
            Method::GET,
            Method::POST,
            Method::PUT,
            Method::PATCH,
            Method::DELETE,
            Method::OPTIONS,
        ])
        .allow_headers([
            header::AUTHORIZATION,
            header::CONTENT_TYPE,
            header::ACCEPT,
            header::UPGRADE,
            header::CONNECTION,
        ])
        .allow_credentials(true);

    let public_v1_router = Router::new()
        .route("/version", get(handle_version))
        .route("/health", get(handle_health));

    let v1_router = Router::new()
        .route("/models", get(handle_models))
        .route("/quota", get(handle_quota))
        .route("/chat/completions", post(handle_chat_completions))
        .layer(middleware::from_fn(local_only));

    let api_router = Router::new()
        .route("/health", get(handle_health))
        .route("/version", get(handle_version))
        .nest("/v1", v1_router.clone());

    Router::new()
        .nest("/api", api_router)
        .nest("/api/v1", public_v1_router.clone())
        .nest("/v1", v1_router)
        .merge(public_v1_router)
        .fallback(static_asset_handler)
        .layer(cors)
        .with_state(Arc::new(state))
}

pub async fn static_asset_handler(req: Request) -> Response {
    let path = req.uri().path().trim_start_matches('/');
    let clean_path = if path.is_empty() { "index.html" } else { path };

    if let Some(content) = WebAssets::get(clean_path) {
        let mime = mime_guess::from_path(clean_path).first_or_octet_stream();
        let mut response = Response::builder()
            .status(StatusCode::OK)
            .header(header::CONTENT_TYPE, mime.as_ref());

        if clean_path.starts_with("assets/") {
            response = response.header(
                header::CACHE_CONTROL,
                "public, max-age=31536000, immutable",
            );
        } else if clean_path == "index.html" {
            response = response.header(
                header::CACHE_CONTROL,
                "no-cache, no-store, must-revalidate",
            );
        } else {
            response = response.header(header::CACHE_CONTROL, "public, max-age=86400");
        }

        response
            .body(Body::from(content.data))
            .unwrap_or_else(|_| (StatusCode::INTERNAL_SERVER_ERROR, "Static asset error").into_response())
    } else {
        // SPA Fallback: serve index.html for unknown frontend routes
        if let Some(index_content) = WebAssets::get("index.html") {
            Response::builder()
                .status(StatusCode::OK)
                .header(header::CONTENT_TYPE, "text/html; charset=utf-8")
                .header(
                    header::CACHE_CONTROL,
                    "no-cache, no-store, must-revalidate",
                )
                .body(Body::from(index_content.data))
                .unwrap_or_else(|_| (StatusCode::INTERNAL_SERVER_ERROR, "Static fallback error").into_response())
        } else {
            (StatusCode::NOT_FOUND, "Web dist not embedded").into_response()
        }
    }
}

pub async fn handle_version() -> impl IntoResponse {
    Json(VersionInfo::current())
}

pub async fn handle_health(State(state): State<Arc<GatewayState>>) -> impl IntoResponse {
    let mut providers = Vec::new();
    let mut details = json!({});
    let version = VersionInfo::current();

    if let Some(ag) = &state.antigravity {
        providers.push("google-antigravity");
        let creds = ag.creds.read().await;
        details["antigravity"] = json!({
            "status": "connected",
            "email": creds.email,
            "project": creds.project,
        });
    }

    if let Some(siwc) = &state.siwc {
        providers.push("openai-siwc");
        let creds = siwc.creds.read().await;
        details["siwc"] = json!({
            "status": "connected",
            "client_id": creds.client_id,
            "expires_at": creds.expires_at.to_rfc3339(),
        });
    }

    Json(json!({
        "ok": true,
        "version": version.semver,
        "build": {
            "commit_sha": version.commit_sha,
            "commit_short_sha": version.commit_short_sha,
            "build_timestamp": version.build_timestamp,
            "target_triple": version.target_triple,
            "dirty": version.dirty,
        },
        "providers": providers,
        "details": details,
    }))
}

pub async fn handle_models(State(state): State<Arc<GatewayState>>) -> Response {
    let mut models_list: Vec<Value> = Vec::new();

    // 1. Antigravity models (prefixed with agy/)
    if let Some(ag) = &state.antigravity {
        if let Ok(Ok(models)) = tokio::time::timeout(
            Duration::from_secs(10),
            crate::antigravity::server::available_models(ag),
        )
        .await
        {
            for m in &models {
                models_list.push(json!({
                    "id": format!("agy/{}", m),
                    "object": "model",
                    "created": 0,
                    "owned_by": "google-antigravity",
                }));
            }
        }
    }

    // 2. SIWC ChatGPT models from the upstream model catalog.
    if let Some(siwc) = &state.siwc {
        match tokio::time::timeout(Duration::from_secs(10), siwc.available_models()).await {
            Ok(Ok(models)) => {
                for model in models {
                    models_list.push(json!({
                        "id": format!("chatgpt/{}", model),
                        "object": "model",
                        "created": 0,
                        "owned_by": "openai-siwc",
                    }));
                }
            }
            Ok(Err(error)) => {
                tracing::warn!("SIWC model discovery failed: {}", error);
            }
            Err(_) => {
                tracing::warn!("SIWC model discovery timed out");
            }
        }
    }

    Json(json!({
        "object": "list",
        "data": models_list,
    }))
    .into_response()
}

pub async fn handle_quota(State(state): State<Arc<GatewayState>>) -> Response {
    if let Some(ag) = &state.antigravity {
        crate::antigravity::server::handle_quota(State(ag.clone())).await
    } else {
        (
            StatusCode::NOT_FOUND,
            Json(json!({
                "error": {
                    "type": "no_quota_provider",
                    "message": "Antigravity provider is not enabled",
                }
            })),
        )
            .into_response()
    }
}

pub async fn handle_chat_completions(
    State(state): State<Arc<GatewayState>>,
    Json(mut input): Json<ChatRequest>,
) -> Response {
    let original_model = input.model.clone();
    let upstream_model = resolve_upstream_model_id(&original_model);
    let is_siwc = is_siwc_model(&original_model);

    input.model = upstream_model;

    // Check if this is an SIWC ChatGPT model
    if is_siwc {
        if let Some(siwc) = &state.siwc {
            info!(
                "Routing model '{}' (resolved: '{}') to SIWC ChatGPT endpoint",
                original_model, input.model
            );
            return siwc.handle_chat_completions(input).await;
        } else {
            return (
                StatusCode::BAD_REQUEST,
                Json(json!({
                    "error": {
                        "type": "provider_unavailable",
                        "message": format!("Model '{}' requires SIWC ChatGPT, but SIWC credentials are not configured", original_model),
                    }
                })),
            )
                .into_response();
        }
    }

    // Otherwise route to Google Antigravity
    if let Some(ag) = &state.antigravity {
        info!(
            "Routing model '{}' (resolved: '{}') to Google Antigravity endpoint",
            original_model, input.model
        );
        crate::antigravity::server::handle_chat_completions(State(ag.clone()), Json(input)).await
    } else {
        (
            StatusCode::BAD_REQUEST,
            Json(json!({
                "error": {
                    "type": "provider_unavailable",
                    "message": format!("Model '{}' requires Google Antigravity, but Antigravity credentials are not configured", original_model),
                }
            })),
        )
            .into_response()
    }
}
