use thiserror::Error;

#[derive(Error, Debug)]
pub enum SdlcError {
    #[error("Harness error: {0}")]
    Harness(#[from] avrig_harness::HarnessError),

    #[error("Invalid lifecycle stage transition from {from} to {to}: {reason}")]
    InvalidStageTransition {
        from: String,
        to: String,
        reason: String,
    },

    #[error("Stage prerequisites not met for stage {stage}: {reason}")]
    PrerequisitesNotMet {
        stage: String,
        reason: String,
    },

    #[error("Stage not found: {0}")]
    StageNotFound(String),
}

pub type Result<T> = std::result::Result<T, SdlcError>;
