use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use thiserror::Error;

/// Default avatar ID for the PET collection (Bulb).
pub const DEFAULT_AVATAR_ID: &str = "AV-01";
pub const DEFAULT_AVATAR_SLUG: &str = "bulb";

/// Connection state as defined in `avatar/STATE_MODEL.md`.
///
/// Only a current, affirmatively confirmed `Connected` state resolves to the
/// `Connected` outfit (with jacket and shared chest badge). All other states
/// resolve to the `Base` outfit (without jacket).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize, Default)]
#[serde(rename_all = "snake_case")]
pub enum ConnectionState {
    #[default]
    NotConnected,
    Connecting,
    Connected,
    ConnectionLost,
    Unknown,
}

impl ConnectionState {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::NotConnected => "not_connected",
            Self::Connecting => "connecting",
            Self::Connected => "connected",
            Self::ConnectionLost => "connection_lost",
            Self::Unknown => "unknown",
        }
    }

    pub fn accessible_text(self) -> &'static str {
        match self {
            Self::NotConnected => "not connected (without jacket)",
            Self::Connecting => "connecting (without jacket)",
            Self::Connected => "connected (with jacket)",
            Self::ConnectionLost => "connection lost (without jacket)",
            Self::Unknown => "connection unknown (without jacket)",
        }
    }
}

/// Visual outfit layer resolved from connection state and freshness.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize, Default)]
#[serde(rename_all = "snake_case")]
pub enum OutfitVariant {
    /// Base outfit: cream T-shirt, jeans, sneakers (no jacket, no badge).
    #[default]
    Base,
    /// Connected outfit: base outfit plus navy jacket and glowing chest badge.
    Connected,
}

impl OutfitVariant {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Base => "base",
            Self::Connected => "connected",
        }
    }

    pub fn has_jacket(self) -> bool {
        matches!(self, Self::Connected)
    }

    pub fn has_badge(self) -> bool {
        matches!(self, Self::Connected)
    }
}

/// Independent activity state as defined in `avatar/STATE_MODEL.md`.
/// Activity changes never alter connection clothing.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize, Default)]
#[serde(rename_all = "snake_case")]
pub enum ActivityState {
    #[default]
    Idle,
    Listening,
    Thinking,
    Working,
    WaitingForUser,
    Error,
}

impl ActivityState {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Idle => "idle",
            Self::Listening => "listening",
            Self::Thinking => "thinking",
            Self::Working => "working",
            Self::WaitingForUser => "waiting_for_user",
            Self::Error => "error",
        }
    }

    pub fn accessible_suffix(self) -> &'static str {
        match self {
            Self::Idle => "idle",
            Self::Listening => "listening",
            Self::Thinking => "thinking",
            Self::Working => "working",
            Self::WaitingForUser => "waiting for you",
            Self::Error => "needs attention",
        }
    }
}

/// Motion rendering preference (`full`, `reduced`, `static`).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize, Default)]
#[serde(rename_all = "snake_case")]
pub enum MotionPreference {
    #[default]
    Full,
    Reduced,
    Static,
}

/// Input to the avatar presentation runtime.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PresentationInput {
    pub avatar_id: String,
    pub connection: ConnectionState,
    pub is_connection_fresh: bool,
    pub sequence: u64,
    pub activity: ActivityState,
    pub motion_preference: MotionPreference,
    pub surface_active: bool,
}

impl Default for PresentationInput {
    fn default() -> Self {
        Self {
            avatar_id: DEFAULT_AVATAR_ID.to_string(),
            connection: ConnectionState::NotConnected,
            is_connection_fresh: true,
            sequence: 1,
            activity: ActivityState::Idle,
            motion_preference: MotionPreference::Full,
            surface_active: true,
        }
    }
}

/// Data-only asset entry from `avatar/definitions/bulb-v1.json`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StateAssetMeta {
    pub file: String,
    pub width: u32,
    pub height: u32,
    pub format: String,
    pub sha256: String,
    pub source: String,
}

/// Frame strip animation metadata (e.g., 8-frame wave).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AnimationStripMeta {
    pub outfit: String,
    pub file: String,
    pub frame_count: u32,
    pub frame_width: u32,
    pub frame_height: u32,
    pub fps: u32,
    pub loop_anim: bool,
    pub sha256: String,
    pub source: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OutfitMeta {
    pub description: String,
    pub has_jacket: bool,
    pub has_badge: bool,
}

/// Complete data-only avatar manifest.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AvatarManifest {
    pub avatar_id: String,
    pub slug: String,
    pub name: String,
    pub version: u32,
    pub author: String,
    pub license: String,
    pub minimum_renderer_version: String,
    pub description: String,
    pub connection_outfit_mapping: HashMap<String, String>,
    pub outfits: HashMap<String, OutfitMeta>,
    pub states: HashMap<String, HashMap<String, StateAssetMeta>>,
}

/// Resolved presentation output consumed by the desktop overlay renderer.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResolvedPresentation {
    pub avatar_id: String,
    pub stored_avatar_id: String,
    pub avatar_name: String,
    pub connection: ConnectionState,
    pub effective_connection: ConnectionState,
    pub outfit: OutfitVariant,
    pub has_jacket: bool,
    pub has_badge: bool,
    pub activity: ActivityState,
    pub effective_motion: MotionPreference,
    pub sprite_file: String,
    pub accessible_label: String,
    pub status_badge_text: String,
    pub is_stale: bool,
    pub used_fallback: bool,
    pub diagnostic: Option<String>,
    pub sequence: u64,
}

#[derive(Debug, Error)]
pub enum RuntimeError {
    #[error("failed to parse avatar manifest JSON: {0}")]
    InvalidManifestJson(#[from] serde_json::Error),
    #[error("out-of-order state update rejected: incoming sequence {incoming} < current {current}")]
    StaleSequence { incoming: u64, current: u64 },
}

/// Stateful avatar presentation resolver enforcing sequence ordering,
/// outfit safety rules, and accessibility labels.
#[derive(Debug, Clone)]
pub struct AvatarRuntime {
    manifest: AvatarManifest,
    last_input: PresentationInput,
    last_resolved: ResolvedPresentation,
}

impl AvatarRuntime {
    pub fn from_manifest_json(json_str: &str) -> Result<Self, RuntimeError> {
        let manifest: AvatarManifest = serde_json::from_str(json_str)?;
        let initial_input = PresentationInput::default();
        let initial_resolved = Self::resolve_stateless(&manifest, &initial_input);
        Ok(Self {
            manifest,
            last_input: initial_input,
            last_resolved: initial_resolved,
        })
    }

    pub fn manifest(&self) -> &AvatarManifest {
        &self.manifest
    }

    pub fn current_state(&self) -> &ResolvedPresentation {
        &self.last_resolved
    }

    pub fn current_input(&self) -> &PresentationInput {
        &self.last_input
    }

    /// Apply a new state update. Rejects out-of-order sequence numbers so an
    /// older async event cannot overwrite a newer state.
    pub fn update(
        &mut self,
        input: PresentationInput,
    ) -> Result<&ResolvedPresentation, RuntimeError> {
        if input.sequence < self.last_input.sequence {
            return Err(RuntimeError::StaleSequence {
                incoming: input.sequence,
                current: self.last_input.sequence,
            });
        }
        self.last_resolved = Self::resolve_stateless(&self.manifest, &input);
        self.last_input = input;
        Ok(&self.last_resolved)
    }

    /// Quick helper to toggle between `Connected` (with jacket) and `NotConnected` (without jacket).
    pub fn set_connected(&mut self, connected: bool) -> &ResolvedPresentation {
        let mut next = self.last_input.clone();
        next.sequence += 1;
        next.connection = if connected {
            ConnectionState::Connected
        } else {
            ConnectionState::NotConnected
        };
        next.is_connection_fresh = true;
        self.last_resolved = Self::resolve_stateless(&self.manifest, &next);
        self.last_input = next;
        &self.last_resolved
    }

    /// Quick helper to change the activity pose without altering connection clothing.
    pub fn set_activity(&mut self, activity: ActivityState) -> &ResolvedPresentation {
        let mut next = self.last_input.clone();
        next.sequence += 1;
        next.activity = activity;
        self.last_resolved = Self::resolve_stateless(&self.manifest, &next);
        self.last_input = next;
        &self.last_resolved
    }

    /// Quick helper to update motion preference (`Full`, `Reduced`, `Static`).
    pub fn set_motion_preference(&mut self, pref: MotionPreference) -> &ResolvedPresentation {
        let mut next = self.last_input.clone();
        next.sequence += 1;
        next.motion_preference = pref;
        self.last_resolved = Self::resolve_stateless(&self.manifest, &next);
        self.last_input = next;
        &self.last_resolved
    }

    /// Pure deterministic resolution following `avatar/STATE_MODEL.md`.
    pub fn resolve_stateless(
        manifest: &AvatarManifest,
        input: &PresentationInput,
    ) -> ResolvedPresentation {
        let mut diagnostics = Vec::new();
        let mut used_fallback = false;

        // 1. Validate avatar ID; preserve stored ID if unknown/retired and fall back to Bulb.
        let resolved_avatar_id = if input.avatar_id == manifest.avatar_id
            || input.avatar_id.eq_ignore_ascii_case(&manifest.slug)
        {
            manifest.avatar_id.clone()
        } else {
            used_fallback = true;
            diagnostics.push(format!(
                "Unknown avatar_id '{}'; falling back to default '{}'",
                input.avatar_id, manifest.avatar_id
            ));
            manifest.avatar_id.clone()
        };

        // 2. Enforce strict connection & freshness rule:
        // Only a current, affirmatively confirmed `Connected` state may show the connected jacket & badge.
        let is_stale = !input.is_connection_fresh;
        let effective_connection = if is_stale {
            if input.connection == ConnectionState::Connected {
                diagnostics.push(
                    "Connection status is stale; removing connected jacket and falling back to base outfit"
                        .to_string(),
                );
            }
            ConnectionState::Unknown
        } else {
            input.connection
        };

        let outfit = match effective_connection {
            ConnectionState::Connected => OutfitVariant::Connected,
            ConnectionState::NotConnected
            | ConnectionState::Connecting
            | ConnectionState::ConnectionLost
            | ConnectionState::Unknown => OutfitVariant::Base,
        };

        // 3. Resolve sprite file for (outfit, activity) with safe fallback.
        let outfit_key = outfit.as_str();
        let activity_key = input.activity.as_str();

        let sprite_file = manifest
            .states
            .get(outfit_key)
            .and_then(|acts| acts.get(activity_key))
            .map(|meta| meta.file.clone())
            .unwrap_or_else(|| {
                used_fallback = true;
                diagnostics.push(format!(
                    "Missing asset for outfit='{}', activity='{}'; using neutral base idle fallback",
                    outfit_key, activity_key
                ));
                "bulb/bulb-base-idle-v1.png".to_string()
            });

        // 4. Resolve effective motion preference (inactive surface reduces motion).
        let effective_motion =
            if !input.surface_active && input.motion_preference == MotionPreference::Full {
                MotionPreference::Reduced
            } else {
                input.motion_preference
            };

        // 5. Build accessible label and concise status pill text.
        let accessible_label = format!(
            "PET ({}) {}, {}",
            manifest.name,
            effective_connection.accessible_text(),
            input.activity.accessible_suffix()
        );

        let conn_short = match effective_connection {
            ConnectionState::Connected => "Connected (Jacket)",
            ConnectionState::Connecting => "Connecting (No Jacket)",
            ConnectionState::ConnectionLost => "Connection Lost (No Jacket)",
            ConnectionState::NotConnected => "Not Connected (No Jacket)",
            ConnectionState::Unknown => "Disconnected / Stale (No Jacket)",
        };
        let status_badge_text = format!("{} · {}", conn_short, input.activity.accessible_suffix());

        ResolvedPresentation {
            avatar_id: resolved_avatar_id,
            stored_avatar_id: input.avatar_id.clone(),
            avatar_name: manifest.name.clone(),
            connection: input.connection,
            effective_connection,
            outfit,
            has_jacket: outfit.has_jacket(),
            has_badge: outfit.has_badge(),
            activity: input.activity,
            effective_motion,
            sprite_file,
            accessible_label,
            status_badge_text,
            is_stale,
            used_fallback,
            diagnostic: if diagnostics.is_empty() {
                None
            } else {
                Some(diagnostics.join("; "))
            },
            sequence: input.sequence,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const BULB_MANIFEST: &str = include_str!("../../../avatar/definitions/bulb-v1.json");

    #[test]
    fn test_connected_vs_not_connected_jacket_rule() {
        let mut rt = AvatarRuntime::from_manifest_json(BULB_MANIFEST).unwrap();

        // Default is NotConnected (without jacket)
        let s0 = rt.current_state();
        assert_eq!(s0.connection, ConnectionState::NotConnected);
        assert_eq!(s0.outfit, OutfitVariant::Base);
        assert!(!s0.has_jacket);
        assert!(!s0.has_badge);
        assert_eq!(s0.sprite_file, "bulb/bulb-base-idle-v1.png");

        // Switch to Connected (with jacket)
        let s1 = rt.set_connected(true);
        assert_eq!(s1.connection, ConnectionState::Connected);
        assert_eq!(s1.outfit, OutfitVariant::Connected);
        assert!(s1.has_jacket);
        assert!(s1.has_badge);
        assert_eq!(s1.sprite_file, "bulb/bulb-connected-idle-v1.png");

        // Switch back to NotConnected (without jacket)
        let s2 = rt.set_connected(false);
        assert_eq!(s2.connection, ConnectionState::NotConnected);
        assert_eq!(s2.outfit, OutfitVariant::Base);
        assert!(!s2.has_jacket);
        assert_eq!(s2.sprite_file, "bulb/bulb-base-idle-v1.png");
    }

    #[test]
    fn test_activity_never_changes_connection_outfit() {
        let mut rt = AvatarRuntime::from_manifest_json(BULB_MANIFEST).unwrap();

        let activities = [
            (ActivityState::Idle, "idle"),
            (ActivityState::Listening, "listening"),
            (ActivityState::Thinking, "thinking"),
            (ActivityState::Working, "working"),
            (ActivityState::WaitingForUser, "waiting-for-user"),
            (ActivityState::Error, "needs-attention"),
        ];

        // While NotConnected (without jacket)
        for (act, slug) in activities {
            let state = rt.set_activity(act);
            assert_eq!(state.outfit, OutfitVariant::Base);
            assert!(!state.has_jacket);
            assert_eq!(state.sprite_file, format!("bulb/bulb-base-{}-v1.png", slug));
        }

        // While Connected (with jacket)
        rt.set_connected(true);
        for (act, slug) in activities {
            let state = rt.set_activity(act);
            assert_eq!(state.outfit, OutfitVariant::Connected);
            assert!(state.has_jacket);
            assert_eq!(
                state.sprite_file,
                format!("bulb/bulb-connected-{}-v1.png", slug)
            );
        }
    }

    #[test]
    fn test_stale_or_unconfirmed_connection_never_shows_jacket() {
        let rt = AvatarRuntime::from_manifest_json(BULB_MANIFEST).unwrap();

        for conn in [
            ConnectionState::NotConnected,
            ConnectionState::Connecting,
            ConnectionState::ConnectionLost,
            ConnectionState::Unknown,
        ] {
            let res = AvatarRuntime::resolve_stateless(
                rt.manifest(),
                &PresentationInput {
                    connection: conn,
                    is_connection_fresh: true,
                    ..Default::default()
                },
            );
            assert_eq!(res.outfit, OutfitVariant::Base);
            assert!(!res.has_jacket);
        }

        // Stale Connected must strip the jacket immediately
        let stale_connected = AvatarRuntime::resolve_stateless(
            rt.manifest(),
            &PresentationInput {
                connection: ConnectionState::Connected,
                is_connection_fresh: false,
                ..Default::default()
            },
        );
        assert!(stale_connected.is_stale);
        assert_eq!(stale_connected.outfit, OutfitVariant::Base);
        assert!(!stale_connected.has_jacket);
    }

    #[test]
    fn test_sequence_ordering_rejects_old_updates() {
        let mut rt = AvatarRuntime::from_manifest_json(BULB_MANIFEST).unwrap();
        rt.update(PresentationInput {
            sequence: 10,
            connection: ConnectionState::Connected,
            ..Default::default()
        })
        .unwrap();

        let err = rt.update(PresentationInput {
            sequence: 9,
            connection: ConnectionState::NotConnected,
            ..Default::default()
        });
        assert!(err.is_err());
        assert_eq!(rt.current_state().connection, ConnectionState::Connected);
    }
}
