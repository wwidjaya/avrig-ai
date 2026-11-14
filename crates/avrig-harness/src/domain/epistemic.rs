use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum EpistemicStatus {
    AuthoritativeRequirement,
    ApprovedBaseline,
    ExistingPractice,
    BestPractice,
    AgentInference,
    AssumptionOrUnknown,
}

impl EpistemicStatus {
    pub fn is_authoritative(&self) -> bool {
        matches!(
            self,
            Self::AuthoritativeRequirement | Self::ApprovedBaseline
        )
    }

    pub fn is_agent_generated(&self) -> bool {
        matches!(self, Self::AgentInference | Self::AssumptionOrUnknown)
    }
}
