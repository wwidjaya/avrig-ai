use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

use crate::office::pet::PetStatusSync;
use crate::domain::decision::DecisionRequest;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", content = "payload")]
#[serde(rename_all = "snake_case")]
pub enum HarnessDesktopEvent {
    PetStatusChanged(PetStatusSync),
    HumanDecisionRequired {
        request: DecisionRequest,
        summary: String,
    },
    StageAdvanced {
        project_id: Uuid,
        new_stage: String,
    },
    OfficeNotification {
        title: String,
        body: String,
        level: String,
    },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DesktopEventEnvelope {
    pub id: Uuid,
    pub event: HarnessDesktopEvent,
    pub timestamp: DateTime<Utc>,
}

impl DesktopEventEnvelope {
    pub fn new(event: HarnessDesktopEvent) -> Self {
        Self {
            id: Uuid::new_v4(),
            event,
            timestamp: Utc::now(),
        }
    }
}
