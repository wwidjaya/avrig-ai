#[cfg(test)]
mod tests {
    use uuid::Uuid;
    use serde_json::json;
    use avrig_harness::domain::epistemic::EpistemicStatus;
    use avrig_harness::domain::artifact::{CandidateArtifact, CandidateStatus};
    use avrig_harness::domain::decision::{AuthorityGate, DecisionRequest, HumanAction};
    use avrig_harness::context::resolver::ResolvedContext;
    use avrig_harness::governance::policy::{Guardrail, ActionType};

    #[test]
    fn test_authority_gate_enforces_human_decision() {
        let project_id = Uuid::new_v4();
        let artifact = CandidateArtifact::new(
            project_id,
            "vision",
            "vision_statement",
            json!({"vision": "Next-gen Autonomous Engineering"}),
            "agent_visionary",
            true,
        );

        assert_eq!(artifact.epistemic_status, EpistemicStatus::AgentInference);
        assert_eq!(artifact.status, CandidateStatus::Draft);

        let request = DecisionRequest {
            id: Uuid::new_v4(),
            project_id,
            stage_id: "vision".into(),
            agent_id: "agent_visionary".into(),
            artifact_id: artifact.id,
            artifact_version: artifact.version,
            proposed_epistemic_status: EpistemicStatus::ApprovedBaseline,
            rationale: "Vision meets all strategic goals.".into(),
            risks_and_tradeoffs: vec![],
            created_at: chrono::Utc::now(),
        };

        // Agent trying to self-approve should fail
        let self_approval = AuthorityGate::decide(
            &request,
            "agent_visionary",
            HumanAction::Approve,
            artifact.status,
            None,
        );
        assert!(self_approval.is_err());

        // Human decision succeeds
        let (record, new_status, new_epistemic) = AuthorityGate::decide(
            &request,
            "human_lead_engineer",
            HumanAction::Approve,
            artifact.status,
            Some("Reviewed and approved by tech lead".into()),
        ).expect("Human approval must succeed");

        assert_eq!(record.human_user_id, "human_lead_engineer");
        assert_eq!(new_status, CandidateStatus::Approved);
        assert_eq!(new_epistemic, EpistemicStatus::ApprovedBaseline);
    }

    #[test]
    fn test_guardrail_rejects_agent_approval() {
        let err = Guardrail::check_action(true, &ActionType::ApproveArtifact);
        assert!(err.is_err());

        let ok = Guardrail::check_action(false, &ActionType::ApproveArtifact);
        assert!(ok.is_ok());
    }

    #[test]
    fn test_context_resolver_epistemic_separation() {
        let project_id = Uuid::new_v4();
        let mut context = ResolvedContext::new();

        let req = CandidateArtifact {
            id: Uuid::new_v4(),
            project_id,
            stage_id: "requirements".into(),
            artifact_type: "user_story".into(),
            version: 1,
            status: CandidateStatus::Approved,
            epistemic_status: EpistemicStatus::AuthoritativeRequirement,
            content: json!({"as_a": "user"}),
            created_by: "human_analyst".into(),
            is_agent_author: false,
            created_at: chrono::Utc::now(),
            updated_at: chrono::Utc::now(),
        };

        let inference = CandidateArtifact::new(
            project_id,
            "ui_ux",
            "wireframe",
            json!({"layout": "grid"}),
            "agent_designer",
            true,
        );

        context.add_artifact(&req);
        context.add_artifact(&inference);

        assert_eq!(context.authoritative_items().count(), 1);
        assert_eq!(context.candidate_items().count(), 1);
    }
}
