#[cfg(test)]
mod tests {
    use uuid::Uuid;
    use serde_json::json;
    use avrig_harness::{CandidateArtifact, CandidateStatus, EpistemicStatus};
    use avrig_sdlc::coordinator::ProjectLifecycleState;
    use avrig_sdlc::lifecycle::LifecycleStage;

    #[test]
    fn test_canonical_lifecycle_order() {
        assert_eq!(LifecycleStage::Project.next(), Some(LifecycleStage::Vision));
        assert_eq!(LifecycleStage::Test.next(), Some(LifecycleStage::Deploy));
        assert_eq!(LifecycleStage::Deploy.next(), None);
    }

    #[test]
    fn test_stage_advance_requires_approval() {
        let project_id = Uuid::new_v4();
        let mut state = ProjectLifecycleState::new(project_id, false);

        assert_eq!(state.current_stage, LifecycleStage::Project);

        // Cannot advance without approved artifact
        let advance_fail = state.advance_stage();
        assert!(advance_fail.is_err());

        // Add an approved artifact
        let mut artifact = CandidateArtifact::new(
            project_id,
            "project",
            "project_charter",
            json!({"name": "Agentic Engine"}),
            "human_pm",
            false,
        );
        artifact.status = CandidateStatus::Approved;
        artifact.epistemic_status = EpistemicStatus::ApprovedBaseline;

        state.add_artifact(LifecycleStage::Project, artifact);

        // Can now advance
        let advanced = state.advance_stage().expect("Stage advance should succeed");
        assert_eq!(advanced, LifecycleStage::Vision);
        assert_eq!(state.current_stage, LifecycleStage::Vision);
    }
}
