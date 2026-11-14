use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

use crate::domain::artifact::CandidateStatus;
use crate::domain::epistemic::EpistemicStatus;
use crate::error::{HarnessError, Result};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DecisionRequest {
    pub id: Uuid,
    pub project_id: Uuid,
    pub stage_id: String,
    pub agent_id: String,
    pub artifact_id: Uuid,
    pub artifact_version: u32,
    pub proposed_epistemic_status: EpistemicStatus,
    pub rationale: String,
    pub risks_and_tradeoffs: Vec<String>,
    pub created_at: DateTime<Utc>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum HumanAction {
    Approve,
    Reject { reason: String },
    RequestRefinement { guidance: String },
    Override { override_content: serde_json::Value, reason: String },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DecisionRecord {
    pub id: Uuid,
    pub request_id: Uuid,
    pub project_id: Uuid,
    pub artifact_id: Uuid,
    pub human_user_id: String,
    pub action: HumanAction,
    pub rationale: Option<String>,
    pub previous_status: CandidateStatus,
    pub resulting_status: CandidateStatus,
    pub decided_at: DateTime<Utc>,
}

pub struct AuthorityGate;

impl AuthorityGate {
    pub fn decide(
        request: &DecisionRequest,
        human_user_id: impl Into<String>,
        action: HumanAction,
        current_status: CandidateStatus,
        rationale: Option<String>,
    ) -> Result<(DecisionRecord, CandidateStatus, EpistemicStatus)> {
        let human_id = human_user_id.into();

        if human_id.trim().is_empty() {
            return Err(HarnessError::Unauthorized(
                "Human authority requires an authenticated user identity.".into(),
            ));
        }

        if human_id == request.agent_id {
            return Err(HarnessError::Unauthorized(
                "Agent cannot approve its own recommendation. Human decision required.".into(),
            ));
        }

        let (new_status, new_epistemic) = match &action {
            HumanAction::Approve => (
                CandidateStatus::Approved,
                EpistemicStatus::ApprovedBaseline,
            ),
            HumanAction::Reject { .. } => (
                CandidateStatus::Rejected,
                EpistemicStatus::AssumptionOrUnknown,
            ),
            HumanAction::RequestRefinement { .. } => (
                CandidateStatus::Draft,
                EpistemicStatus::AgentInference,
            ),
            HumanAction::Override { .. } => (
                CandidateStatus::Approved,
                EpistemicStatus::AuthoritativeRequirement,
            ),
        };

        let record = DecisionRecord {
            id: Uuid::new_v4(),
            request_id: request.id,
            project_id: request.project_id,
            artifact_id: request.artifact_id,
            human_user_id: human_id,
            action,
            rationale,
            previous_status: current_status,
            resulting_status: new_status,
            decided_at: Utc::now(),
        };

        Ok((record, new_status, new_epistemic))
    }
}
