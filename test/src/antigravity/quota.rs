use super::state::AppState;
use super::types::{GEMINI_CLI_URL, GeminiCliQuotaResponse};
use anyhow::{Context, Result};
use serde_json::{Value, json};

pub fn quota_group(model_id: &str, display_name: &str) -> &'static str {
    let name = format!("{} {}", model_id, display_name).to_lowercase();
    if name.contains("claude") {
        "claude"
    } else if name.contains("gemini") {
        if name.contains("flash") || name.contains("lite") {
            "gemini-flash"
        } else {
            "gemini-pro"
        }
    } else {
        ""
    }
}

pub fn clamp_fraction(value: f64) -> f64 {
    if value < 0.0 {
        0.0
    } else if value > 1.0 {
        1.0
    } else {
        value
    }
}

pub async fn fetch_gemini_cli_quota(state: &AppState, project: &str) -> Result<Vec<Value>> {
    state.refresh_token().await?;
    let access_token = {
        let creds = state.creds.read().await;
        creds.access_token.clone()
    };

    let url = format!("{}/v1internal:retrieveUserQuota", GEMINI_CLI_URL);
    let payload = json!({ "project": project });

    let resp = state
        .http
        .post(&url)
        .header("Authorization", format!("Bearer {}", access_token))
        .header("Content-Type", "application/json")
        .header("User-Agent", "google-api-nodejs-client/9.15.1")
        .header("X-Goog-Api-Client", "gl-node/22.17.0")
        .header(
            "Client-Metadata",
            "ideType=IDE_UNSPECIFIED,platform=PLATFORM_UNSPECIFIED,pluginType=GEMINI",
        )
        .json(&payload)
        .send()
        .await
        .with_context(|| format!("POST to {}", url))?;

    let status = resp.status();
    let body = resp.text().await.unwrap_or_default();
    if !status.is_success() {
        return Err(anyhow::anyhow!(
            "Gemini CLI quota HTTP {}: {}",
            status,
            body
        ));
    }

    let parsed: GeminiCliQuotaResponse = serde_json::from_str(&body)
        .with_context(|| format!("parse retrieveUserQuota response: {}", body))?;

    let mut quotas = Vec::new();
    for bucket in parsed.buckets {
        if !bucket.model_id.starts_with("gemini-") {
            continue;
        }
        quotas.push(json!({
            "modelId": bucket.model_id,
            "remainingFraction": clamp_fraction(bucket.remaining_fraction),
            "resetTime": bucket.reset_time,
        }));
    }

    Ok(quotas)
}
