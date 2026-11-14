use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum LifecycleStage {
    Project,
    Vision,
    Mission,
    Strategy,
    BusinessCapability,
    BusinessProcess,
    Activity,
    Role,
    UserStory,
    UiUxDesign,
    DataModel,
    NonFunctionalRequirement,
    SystemArchitecture,
    TechnologyArchitecture,
    Development,
    Test,
    Deploy, // Optional stage (cardinality 0..1)
}

impl LifecycleStage {
    pub const ALL: [LifecycleStage; 17] = [
        LifecycleStage::Project,
        LifecycleStage::Vision,
        LifecycleStage::Mission,
        LifecycleStage::Strategy,
        LifecycleStage::BusinessCapability,
        LifecycleStage::BusinessProcess,
        LifecycleStage::Activity,
        LifecycleStage::Role,
        LifecycleStage::UserStory,
        LifecycleStage::UiUxDesign,
        LifecycleStage::DataModel,
        LifecycleStage::NonFunctionalRequirement,
        LifecycleStage::SystemArchitecture,
        LifecycleStage::TechnologyArchitecture,
        LifecycleStage::Development,
        LifecycleStage::Test,
        LifecycleStage::Deploy,
    ];

    pub fn identifier(&self) -> &'static str {
        match self {
            Self::Project => "project",
            Self::Vision => "vision",
            Self::Mission => "mission",
            Self::Strategy => "strategy",
            Self::BusinessCapability => "business_capability",
            Self::BusinessProcess => "business_process",
            Self::Activity => "activity",
            Self::Role => "role",
            Self::UserStory => "user_story",
            Self::UiUxDesign => "ui_ux_design",
            Self::DataModel => "data_model",
            Self::NonFunctionalRequirement => "non_functional_requirement",
            Self::SystemArchitecture => "system_architecture",
            Self::TechnologyArchitecture => "technology_architecture",
            Self::Development => "development",
            Self::Test => "test",
            Self::Deploy => "deploy",
        }
    }

    pub fn is_mandatory_engineering_complete(&self) -> bool {
        matches!(self, Self::Test)
    }

    pub fn is_optional(&self) -> bool {
        matches!(self, Self::Deploy)
    }

    pub fn next(&self) -> Option<LifecycleStage> {
        let index = Self::ALL.iter().position(|s| s == self)?;
        if index + 1 < Self::ALL.len() {
            Some(Self::ALL[index + 1])
        } else {
            None
        }
    }

    pub fn previous(&self) -> Option<LifecycleStage> {
        let index = Self::ALL.iter().position(|s| s == self)?;
        if index > 0 {
            Some(Self::ALL[index - 1])
        } else {
            None
        }
    }
}
