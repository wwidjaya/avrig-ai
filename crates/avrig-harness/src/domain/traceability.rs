use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RelationType {
    DerivedFrom,
    Satisfies,
    ConstrainedBy,
    RealizedBy,
    ImplementedBy,
    VerifiedBy,
    DeployedAs,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TraceabilityLink {
    pub id: Uuid,
    pub project_id: Uuid,
    pub source_artifact_id: Uuid,
    pub source_version: u32,
    pub target_artifact_id: Uuid,
    pub target_version: u32,
    pub relation: RelationType,
    pub rationale: Option<String>,
    pub created_at: DateTime<Utc>,
}

impl TraceabilityLink {
    pub fn new(
        project_id: Uuid,
        source_artifact_id: Uuid,
        source_version: u32,
        target_artifact_id: Uuid,
        target_version: u32,
        relation: RelationType,
        rationale: Option<String>,
    ) -> Self {
        Self {
            id: Uuid::new_v4(),
            project_id,
            source_artifact_id,
            source_version,
            target_artifact_id,
            target_version,
            relation,
            rationale,
            created_at: Utc::now(),
        }
    }
}
