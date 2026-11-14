use std::collections::HashMap;
use uuid::Uuid;
use avrig_harness::{CandidateArtifact, CandidateStatus};
use crate::error::{Result, SdlcError};
use crate::lifecycle::LifecycleStage;

#[derive(Debug, Clone)]
pub struct ProjectLifecycleState {
    pub project_id: Uuid,
    pub current_stage: LifecycleStage,
    pub stage_artifacts: HashMap<LifecycleStage, Vec<CandidateArtifact>>,
    pub is_deploy_in_scope: bool,
}

impl ProjectLifecycleState {
    pub fn new(project_id: Uuid, is_deploy_in_scope: bool) -> Self {
        Self {
            project_id,
            current_stage: LifecycleStage::Project,
            stage_artifacts: HashMap::new(),
            is_deploy_in_scope,
        }
    }

    pub fn add_artifact(&mut self, stage: LifecycleStage, artifact: CandidateArtifact) {
        self.stage_artifacts.entry(stage).or_default().push(artifact);
    }

    pub fn has_approved_baseline_for_stage(&self, stage: LifecycleStage) -> bool {
        self.stage_artifacts
            .get(&stage)
            .map(|artifacts| artifacts.iter().any(|a| a.status == CandidateStatus::Approved))
            .unwrap_or(false)
    }

    pub fn advance_stage(&mut self) -> Result<LifecycleStage> {
        if !self.has_approved_baseline_for_stage(self.current_stage) {
            return Err(SdlcError::PrerequisitesNotMet {
                stage: self.current_stage.identifier().to_string(),
                reason: "Current stage requires at least one approved authoritative artifact before advancing.".into(),
            });
        }

        let next = match self.current_stage.next() {
            Some(LifecycleStage::Deploy) if !self.is_deploy_in_scope => {
                return Ok(self.current_stage);
            }
            Some(next_stage) => next_stage,
            None => {
                return Ok(self.current_stage);
            }
        };

        self.current_stage = next;
        Ok(self.current_stage)
    }
}
