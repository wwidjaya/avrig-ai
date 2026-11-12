use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum TaskState {
    Queued,
    Executing,
    AwaitingInput,
    AwaitingHumanDecision,
    Completed,
    Failed,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentTask {
    pub id: Uuid,
    pub project_id: Uuid,
    pub stage_id: String,
    pub agent_id: String,
    pub state: TaskState,
    pub input_context: serde_json::Value,
    pub output_result: Option<serde_json::Value>,
    pub error_message: Option<String>,
    pub created_at: DateTime<Utc>,
    pub completed_at: Option<DateTime<Utc>>,
}

impl AgentTask {
    pub fn new(
        project_id: Uuid,
        stage_id: impl Into<String>,
        agent_id: impl Into<String>,
        input_context: serde_json::Value,
    ) -> Self {
        Self {
            id: Uuid::new_v4(),
            project_id,
            stage_id: stage_id.into(),
            agent_id: agent_id.into(),
            state: TaskState::Queued,
            input_context,
            output_result: None,
            error_message: None,
            created_at: Utc::now(),
            completed_at: None,
        }
    }

    pub fn start(&mut self) {
        self.state = TaskState::Executing;
    }

    pub fn complete(&mut self, result: serde_json::Value) {
        self.state = TaskState::Completed;
        self.output_result = Some(result);
        self.completed_at = Some(Utc::now());
    }

    pub fn fail(&mut self, err: impl Into<String>) {
        self.state = TaskState::Failed;
        self.error_message = Some(err.into());
        self.completed_at = Some(Utc::now());
    }
}
