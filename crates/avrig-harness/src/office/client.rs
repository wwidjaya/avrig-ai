use tokio::sync::broadcast;
use crate::office::event::DesktopEventEnvelope;

pub struct DesktopEventBus {
    sender: broadcast::Sender<DesktopEventEnvelope>,
}

impl DesktopEventBus {
    pub fn new(capacity: usize) -> Self {
        let (sender, _) = broadcast::channel(capacity);
        Self { sender }
    }

    pub fn subscribe(&self) -> broadcast::Receiver<DesktopEventEnvelope> {
        self.sender.subscribe()
    }

    pub fn publish(&self, event: DesktopEventEnvelope) -> Result<usize, broadcast::error::SendError<DesktopEventEnvelope>> {
        self.sender.send(event)
    }
}
