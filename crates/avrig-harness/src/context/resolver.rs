use serde::{Deserialize, Serialize};
use uuid::Uuid;

use crate::domain::artifact::CandidateArtifact;
use crate::domain::epistemic::EpistemicStatus;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ContextItem {
    pub artifact_id: Uuid,
    pub stage_id: String,
    pub artifact_type: String,
    pub version: u32,
    pub epistemic_status: EpistemicStatus,
    pub is_authoritative: bool,
    pub payload: serde_json::Value,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct ResolvedContext {
    pub items: Vec<ContextItem>,
}

impl ResolvedContext {
    pub fn new() -> Self {
        Self { items: Vec::new() }
    }

    pub fn add_artifact(&mut self, artifact: &CandidateArtifact) {
        self.items.push(ContextItem {
            artifact_id: artifact.id,
            stage_id: artifact.stage_id.clone(),
            artifact_type: artifact.artifact_type.clone(),
            version: artifact.version,
            epistemic_status: artifact.epistemic_status,
            is_authoritative: artifact.epistemic_status.is_authoritative(),
            payload: artifact.content.clone(),
        });
    }

    pub fn authoritative_items(&self) -> impl Iterator<Item = &ContextItem> {
        self.items.iter().filter(|i| i.is_authoritative)
    }

    pub fn candidate_items(&self) -> impl Iterator<Item = &ContextItem> {
        self.items.iter().filter(|i| !i.is_authoritative)
    }
}
