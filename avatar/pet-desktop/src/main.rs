#![cfg_attr(target_os = "windows", windows_subsystem = "windows")]

mod bridge;

use std::sync::{Arc, Mutex};
use std::sync::mpsc::Receiver;
use bevy::{
    prelude::*,
    window::{PrimaryWindow, WindowLevel, WindowPlugin, WindowResolution},
};
use bridge::map_harness_status_to_bevy;
use avrig_harness::office::event::HarnessDesktopEvent;

const NOT_CONNECTED_ATLAS: &str = "bulb/not-connected-atlas.png";
const MESSAGE_ALERT_IMAGE: &str = "bulb/bulb-base-needs-attention-v1.png";
const CONNECTED_ATLAS: &str = "bulb/connected-atlas.png";
const JOB_DONE_ATLAS: &str = "bulb/job-done-atlas.png";

const FRAME_WIDTH: u32 = 192;
const FRAME_HEIGHT: u32 = 288;
const FRAME_COLUMNS: u32 = 12;
const FRAME_ROWS: u32 = 20;
const FRAME_COUNT: usize = 240;
const VIDEO_FPS: f32 = 24.0;

#[derive(Resource, Clone, Copy, PartialEq, Eq, Debug, Default)]
pub enum PetVisualState {
    #[default]
    NotConnected,
    Connected,
    JobDone,
    MessageAlert,
}

#[derive(Resource, Clone)]
pub struct HarnessEventReceiver(pub Arc<Mutex<Receiver<HarnessDesktopEvent>>>);

#[derive(Resource)]
struct PetAssets {
    not_connected: Handle<Image>,
    connected: Handle<Image>,
    job_done: Handle<Image>,
    message_alert: Handle<Image>,
    atlas_layout: Handle<TextureAtlasLayout>,
}

#[derive(Resource, Default)]
struct AnimationClock {
    elapsed: f32,
    displayed_frame: usize,
}

#[derive(Resource, Default)]
struct AssetLoadDiagnostics {
    reported_atlas: bool,
    reported_connected: bool,
    reported_job_done: bool,
    reported_alert: bool,
}

#[derive(Component)]
struct PetSprite;

fn main() {
    let runtime_assets = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("assets")
        .join("runtime")
        .to_string_lossy()
        .into_owned();

    App::new()
        .add_plugins((
            DefaultPlugins
                .set(WindowPlugin {
                    primary_window: Some(Window {
                        title: "Bulb Pet".into(),
                        resolution: WindowResolution::new(166.0, 166.0),
                        transparent: true,
                        decorations: false,
                        window_level: WindowLevel::AlwaysOnTop,
                        skip_taskbar: true,
                        ..default()
                    }),
                    ..default()
                })
                .set(AssetPlugin {
                    file_path: runtime_assets,
                    ..default()
                }),
            bevy_framepace::FramepacePlugin,
        ))
        .insert_resource(bevy_framepace::FramepaceSettings {
            limiter: bevy_framepace::Limiter::from_framerate(VIDEO_FPS as f64),
            ..default()
        })
        .insert_resource(ClearColor(Color::NONE))
        .init_resource::<PetVisualState>()
        .init_resource::<AnimationClock>()
        .init_resource::<AssetLoadDiagnostics>()
        .add_systems(Startup, setup)
        .add_systems(
            Update,
            (
                keyboard_controls,
                drag_window,
                animate_not_connected,
                sync_visual_state,
                poll_harness_events,
                report_asset_loads,
            ),
        )
        .run();
}

fn setup(
    mut commands: Commands,
    asset_server: Res<AssetServer>,
    mut atlas_layouts: ResMut<Assets<TextureAtlasLayout>>,
) {
    commands.spawn((
        Camera2d,
        Camera {
            clear_color: ClearColorConfig::Custom(Color::NONE),
            ..default()
        },
    ));

    let atlas_layout = TextureAtlasLayout::from_grid(
        UVec2::new(FRAME_WIDTH, FRAME_HEIGHT),
        FRAME_COLUMNS,
        FRAME_ROWS,
        None,
        None,
    );
    let atlas_layout = atlas_layouts.add(atlas_layout);

    let not_connected: Handle<Image> = asset_server.load(NOT_CONNECTED_ATLAS);
    let connected: Handle<Image> = asset_server.load(CONNECTED_ATLAS);
    let job_done: Handle<Image> = asset_server.load(JOB_DONE_ATLAS);
    let message_alert: Handle<Image> = asset_server.load(MESSAGE_ALERT_IMAGE);

    commands.insert_resource(PetAssets {
        not_connected: not_connected.clone(),
        connected,
        job_done,
        message_alert,
        atlas_layout: atlas_layout.clone(),
    });

    // The source atlas cell dimensions fit the compact overlay.
    commands.spawn((
        Sprite::from_atlas_image(
            not_connected,
            TextureAtlas {
                layout: atlas_layout,
                index: 0,
            },
        ),
        Transform::from_scale(Vec3::splat(0.5525)),
        PetSprite,
    ));

    // Initialize Harness bridge channel
    let (_tx, rx) = std::sync::mpsc::channel();
    commands.insert_resource(HarnessEventReceiver(Arc::new(Mutex::new(rx))));

    println!("Bulb Bevy overlay ready with Harness bridge. N: not connected, C: connected, J: job done, M: message/alert.");
}

fn poll_harness_events(
    rx: Option<Res<HarnessEventReceiver>>,
    mut state: ResMut<PetVisualState>,
) {
    if let Some(receiver) = rx {
        if let Ok(rx_guard) = receiver.0.lock() {
            while let Ok(event) = rx_guard.try_recv() {
                match event {
                    HarnessDesktopEvent::PetStatusChanged(status_sync) => {
                        let mapped = map_harness_status_to_bevy(status_sync.status);
                        if *state != mapped {
                            *state = mapped;
                            println!("Harness updated Pet state to: {:?}", mapped);
                        }
                    }
                    HarnessDesktopEvent::HumanDecisionRequired { summary, .. } => {
                        *state = PetVisualState::MessageAlert;
                        println!("Decision required: {}", summary);
                    }
                    HarnessDesktopEvent::StageAdvanced { new_stage, .. } => {
                        *state = PetVisualState::JobDone;
                        println!("Stage advanced to: {}", new_stage);
                    }
                    HarnessDesktopEvent::OfficeNotification { title, body, .. } => {
                        println!("[Office Notification] {}: {}", title, body);
                    }
                }
            }
        }
    }
}

fn drag_window(
    mouse: Res<ButtonInput<MouseButton>>,
    mut windows: Query<&mut Window, With<PrimaryWindow>>,
) {
    if mouse.just_pressed(MouseButton::Left) {
        if let Ok(mut window) = windows.single_mut() {
            window.start_drag_move();
        }
    }
}

fn keyboard_controls(
    keys: Res<ButtonInput<KeyCode>>,
    mut state: ResMut<PetVisualState>,
    mut app_exit: EventWriter<AppExit>,
) {
    if keys.just_pressed(KeyCode::KeyN) {
        *state = PetVisualState::NotConnected;
        println!("Pet state: Not connected");
    } else if keys.just_pressed(KeyCode::KeyC) {
        *state = PetVisualState::Connected;
        println!("Pet state: Connected");
    } else if keys.just_pressed(KeyCode::KeyJ) {
        *state = PetVisualState::JobDone;
        println!("Pet state: Job done");
    } else if keys.just_pressed(KeyCode::KeyM) {
        *state = PetVisualState::MessageAlert;
        println!("Pet state: Message / alert");
    } else if keys.just_pressed(KeyCode::Escape) {
        app_exit.write(AppExit::Success);
    }
}

fn animate_not_connected(
    time: Res<Time>,
    state: Res<PetVisualState>,
    mut clock: ResMut<AnimationClock>,
    mut sprites: Query<&mut Sprite, With<PetSprite>>,
) {
    if !matches!(
        *state,
        PetVisualState::NotConnected | PetVisualState::Connected | PetVisualState::JobDone
    ) {
        return;
    }

    clock.elapsed += time.delta_secs();
    let frame = ((clock.elapsed * VIDEO_FPS) as usize) % FRAME_COUNT;
    if frame == clock.displayed_frame {
        return;
    }
    clock.displayed_frame = frame;

    for mut sprite in &mut sprites {
        if let Some(atlas) = sprite.texture_atlas.as_mut() {
            atlas.index = frame;
        }
    }
}

fn sync_visual_state(
    state: Res<PetVisualState>,
    assets: Res<PetAssets>,
    mut clock: ResMut<AnimationClock>,
    mut sprites: Query<&mut Sprite, With<PetSprite>>,
) {
    if !state.is_changed() {
        return;
    }

    for mut sprite in &mut sprites {
        match *state {
            PetVisualState::NotConnected => {
                sprite.image = assets.not_connected.clone();
                sprite.texture_atlas = Some(TextureAtlas {
                    layout: assets.atlas_layout.clone(),
                    index: 0,
                });
            }
            PetVisualState::Connected => {
                sprite.image = assets.connected.clone();
                sprite.texture_atlas = Some(TextureAtlas {
                    layout: assets.atlas_layout.clone(),
                    index: 0,
                });
            }
            PetVisualState::JobDone => {
                sprite.image = assets.job_done.clone();
                sprite.texture_atlas = Some(TextureAtlas {
                    layout: assets.atlas_layout.clone(),
                    index: 0,
                });
            }
            PetVisualState::MessageAlert => {
                sprite.image = assets.message_alert.clone();
                sprite.texture_atlas = None;
            }
        }
    }

    clock.elapsed = 0.0;
    clock.displayed_frame = 0;
}

fn report_asset_loads(
    server: Res<AssetServer>,
    assets: Res<PetAssets>,
    mut diagnostics: ResMut<AssetLoadDiagnostics>,
) {
    report_asset(
        &server,
        NOT_CONNECTED_ATLAS,
        &assets.not_connected,
        &mut diagnostics.reported_atlas,
    );
    report_asset(
        &server,
        CONNECTED_ATLAS,
        &assets.connected,
        &mut diagnostics.reported_connected,
    );
    report_asset(
        &server,
        JOB_DONE_ATLAS,
        &assets.job_done,
        &mut diagnostics.reported_job_done,
    );
    report_asset(
        &server,
        MESSAGE_ALERT_IMAGE,
        &assets.message_alert,
        &mut diagnostics.reported_alert,
    );
}

fn report_asset(server: &AssetServer, name: &str, handle: &Handle<Image>, reported: &mut bool) {
    if *reported {
        return;
    }
    match server.get_load_state(handle) {
        Some(bevy::asset::LoadState::Loaded) => {
            println!("Loaded pet asset: {name}");
            *reported = true;
        }
        Some(bevy::asset::LoadState::Failed(error)) => {
            eprintln!("Failed to load pet asset {name}: {error}");
            *reported = true;
        }
        _ => {}
    }
}
