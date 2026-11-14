use std::sync::{Arc, Mutex};
use std::sync::mpsc::{channel, Receiver, Sender};
use avrig_harness::office::event::HarnessDesktopEvent;
use avrig_harness::office::pet::PetVisualStatus;

#[allow(dead_code)]
pub struct HarnessBridge {
    pub rx: Arc<Mutex<Receiver<HarnessDesktopEvent>>>,
    pub tx: Sender<HarnessDesktopEvent>,
}

impl Default for HarnessBridge {
    fn default() -> Self {
        let (tx, rx) = channel();
        Self {
            rx: Arc::new(Mutex::new(rx)),
            tx,
        }
    }
}

pub fn map_harness_status_to_bevy(status: PetVisualStatus) -> crate::PetVisualState {
    match status {
        PetVisualStatus::NotConnected => crate::PetVisualState::NotConnected,
        PetVisualStatus::Connected => crate::PetVisualState::Connected,
        PetVisualStatus::Thinking | PetVisualStatus::Working => crate::PetVisualState::Connected,
        PetVisualStatus::WaitingForUser => crate::PetVisualState::MessageAlert,
        PetVisualStatus::JobDone => crate::PetVisualState::JobDone,
        PetVisualStatus::MessageAlert => crate::PetVisualState::MessageAlert,
    }
}
