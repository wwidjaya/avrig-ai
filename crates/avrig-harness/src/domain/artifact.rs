use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

use crate::domain::epistemic::EpistemicStatus;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum CandidateStatus {
    Draft,
    Candidate,
    ValidatedCandidate,
    ReviewedCandidate,
    Approved,
    Superseded,
    Rejected,
}

impl CandidateStatus {
    pub fn is_terminal(&self) -> bool {
        matches!(self, Self::Superseded | Self::Rejected)
    }

    pub fn is_approved(&self) -> bool {
        matches!(self, Self::Approved)
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CandidateArtifact {
    pub id: Uuid,
    pub project_id: Uuid,
    pub stage_id: String,
    pub artifact_type: String,
    pub version: u32,
    pub status: CandidateStatus,
    pub epistemic_status: EpistemicStatus,
    pub content: serde_json::Value,
    pub created_by: String,
    pub is_agent_author: bool,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

impl CandidateArtifact {
    pub fn new(
        project_id: Uuid,
        stage_id: impl Into<String>,
        artifact_type: impl Into<String>,
        content: serde_json::Value,
        author: impl Into<String>,
        is_agent: bool,
    ) -> Self {
        let now = Utc::now();
        let epistemic = if is_agent {
            EpistemicStatus::AgentInference
        } else {
            EpistemicStatus::AuthoritativeRequirement
        };

        Self {
            id: Uuid::new_v4(),
            project_id,
            stage_id: stage_id.into(),
            artifact_type: artifact_type.into(),
            version: 1,
            status: CandidateStatus::Draft,
            epistemic_status: epistemic,
            content,
            created_by: author.into(),
            is_agent_author: is_agent,
            created_at: now,
            updated_at: now,
        }
    }
}
