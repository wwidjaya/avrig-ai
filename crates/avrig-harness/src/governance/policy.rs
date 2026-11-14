use crate::error::{HarnessError, Result};

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ActionType {
    ReadArtifact,
    GenerateCandidate,
    ExecuteTool { tool_name: String, mutating: bool },
    ApproveArtifact,
}

pub struct Guardrail;

impl Guardrail {
    pub fn check_action(is_agent: bool, action: &ActionType) -> Result<()> {
        match action {
            ActionType::ApproveArtifact if is_agent => Err(HarnessError::Unauthorized(
                "Autonomous approval is forbidden. Only human authority can approve candidates.".into(),
            )),
            ActionType::ExecuteTool { mutating, tool_name } if is_agent && *mutating => {
                tracing::warn!(tool = %tool_name, "Agent executing mutating tool; audit record required.");
                Ok(())
            }
            _ => Ok(()),
        }
    }
}
