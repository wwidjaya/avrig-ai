use serde::{Deserialize, Serialize};
use uuid::Uuid;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize, Default)]
#[serde(rename_all = "snake_case")]
pub enum PetVisualStatus {
    #[default]
    NotConnected,
    Connected,
    Thinking,
    Working,
    WaitingForUser,
    JobDone,
    MessageAlert,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PetStatusSync {
    pub pet_id: Uuid,
    pub office_id: Uuid,
    pub status: PetVisualStatus,
    pub active_project_id: Option<Uuid>,
    pub active_stage_id: Option<String>,
    pub pending_decision_id: Option<Uuid>,
    pub status_message: String,
}

impl PetStatusSync {
    pub fn idle(pet_id: Uuid, office_id: Uuid) -> Self {
        Self {
            pet_id,
            office_id,
            status: PetVisualStatus::Connected,
            active_project_id: None,
            active_stage_id: None,
            pending_decision_id: None,
            status_message: "Bulb is online and ready.".into(),
        }
    }

    pub fn working_on_task(pet_id: Uuid, office_id: Uuid, project_id: Uuid, stage_id: String, task_name: String) -> Self {
        Self {
            pet_id,
            office_id,
            status: PetVisualStatus::Working,
            active_project_id: Some(project_id),
            active_stage_id: Some(stage_id),
            pending_decision_id: None,
            status_message: format!("Bulb is working on: {}", task_name),
        }
    }

    pub fn waiting_for_approval(pet_id: Uuid, office_id: Uuid, project_id: Uuid, stage_id: String, decision_id: Uuid) -> Self {
        Self {
            pet_id,
            office_id,
            status: PetVisualStatus::WaitingForUser,
            active_project_id: Some(project_id),
            active_stage_id: Some(stage_id),
            pending_decision_id: Some(decision_id),
            status_message: "Bulb requires human review and decision.".into(),
        }
    }

    pub fn task_completed(pet_id: Uuid, office_id: Uuid, project_id: Uuid, stage_id: String) -> Self {
        Self {
            pet_id,
            office_id,
            status: PetVisualStatus::JobDone,
            active_project_id: Some(project_id),
            active_stage_id: Some(stage_id),
            pending_decision_id: None,
            status_message: "Bulb finished task!".into(),
        }
    }
}
