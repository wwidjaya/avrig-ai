use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum OfficeType {
    EngineeringSdlc,
    Operations,
    Consulting,
    Custom(String),
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ActorKind {
    Human,
    AiPet,
    AiAgent,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OfficeActor {
    pub id: Uuid,
    pub office_id: Uuid,
    pub name: String,
    pub kind: ActorKind,
    pub role_title: String,
    pub is_owner: bool,
    pub created_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Department {
    pub id: Uuid,
    pub office_id: Uuid,
    pub name: String,
    pub floor_level: u32,
    pub head_actor_id: Option<Uuid>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VirtualOffice {
    pub id: Uuid,
    pub name: String,
    pub office_type: OfficeType,
    pub primary_owner_id: String, // Keycloak `sub`
    pub pet_actor_id: Option<Uuid>,
    pub created_at: DateTime<Utc>,
}

impl VirtualOffice {
    pub fn new(name: impl Into<String>, owner_id: impl Into<String>, office_type: OfficeType) -> Self {
        Self {
            id: Uuid::new_v4(),
            name: name.into(),
            office_type,
            primary_owner_id: owner_id.into(),
            pet_actor_id: None,
            created_at: Utc::now(),
        }
    }
}
