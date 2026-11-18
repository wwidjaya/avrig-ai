use super::types::{AvailableModel, Credentials, DEFAULT_THOUGHT_SIGNATURE};
use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::Arc;
use tokio::sync::RwLock;

#[derive(Clone)]
pub struct AppState {
    pub creds_path: PathBuf,
    pub client_id: String,
    pub secret: String,
    pub http: reqwest::Client,
    pub creds: Arc<RwLock<Credentials>>,
    pub models: Arc<RwLock<Option<Vec<String>>>>,
    pub model_info: Arc<RwLock<HashMap<String, AvailableModel>>>,
    pub call_name_cache: Arc<RwLock<HashMap<String, String>>>,
    pub thought_sig_cache: Arc<RwLock<HashMap<String, String>>>,
}

impl AppState {
    pub fn new(creds_path: PathBuf, client_id: String, secret: String, creds: Credentials) -> Self {
        let http = reqwest::Client::builder()
            .timeout(std::time::Duration::from_secs(90))
            .build()
            .expect("build reqwest client");

        Self {
            creds_path,
            client_id,
            secret,
            http,
            creds: Arc::new(RwLock::new(creds)),
            models: Arc::new(RwLock::new(None)),
            model_info: Arc::new(RwLock::new(HashMap::new())),
            call_name_cache: Arc::new(RwLock::new(HashMap::new())),
            thought_sig_cache: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    pub async fn set_call_info(&self, id: &str, name: &str, sig: &str) {
        if id.is_empty() {
            return;
        }
        if !name.is_empty() {
            let mut map = self.call_name_cache.write().await;
            map.insert(id.to_string(), name.to_string());
        }
        if !sig.is_empty() {
            let mut map = self.thought_sig_cache.write().await;
            map.insert(id.to_string(), sig.to_string());
        }
    }

    pub async fn get_call_info(&self, id: &str) -> (String, String) {
        let name = {
            let map = self.call_name_cache.read().await;
            map.get(id).cloned().unwrap_or_default()
        };
        let sig = {
            let map = self.thought_sig_cache.read().await;
            map.get(id)
                .cloned()
                .unwrap_or_else(|| DEFAULT_THOUGHT_SIGNATURE.to_string())
        };
        (name, sig)
    }
}
