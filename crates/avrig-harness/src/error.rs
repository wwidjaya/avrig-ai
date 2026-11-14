use thiserror::Error;

#[derive(Error, Debug)]
pub enum HarnessError {
    #[error("Unauthorized: {0}")]
    Unauthorized(String),

    #[error("Invalid state transition from {from:?} to {to:?}: {reason}")]
    InvalidStateTransition {
        from: String,
        to: String,
        reason: String,
    },

    #[error("Artifact not found: {0}")]
    ArtifactNotFound(String),

    #[error("Validation failed: {0}")]
    ValidationFailed(String),

    #[error("Internal harness error: {0}")]
    Internal(String),
}

pub type Result<T> = std::result::Result<T, HarnessError>;
