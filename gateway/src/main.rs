use anyhow::Result;
use clap::Parser;
use gateway::antigravity::oauth::{env_or, load_credentials};
use gateway::antigravity::state::AppState as AntigravityState;
use gateway::antigravity::types::{DEFAULT_CLIENT_ID, DEFAULT_CLIENT_SECRET};
use gateway::server::{GatewayState, build_gateway_router};
use gateway::siwc::client::SiwcClient;
use gateway::siwc::oauth::load_credentials as load_siwc_credentials;
use gateway::version::VersionInfo;
use std::net::SocketAddr;
use std::path::{Path, PathBuf};
use tracing::{info, warn};

#[derive(Parser, Debug)]
#[command(
    name = "gateway",
    about = "Avrig Unified AI Gateway with Antigravity and SIWC ChatGPT support",
    version = env!("AVRIG_PKG_VERSION")
)]
pub struct CliArgs {
    #[arg(
        short,
        long,
        default_value = "127.0.0.1:8085",
        help = "local OpenAI-compatible listen address"
    )]
    pub listen: String,

    #[arg(short = 'a', long, help = "Antigravity OAuth credentials file")]
    pub antigravity_credentials: Option<PathBuf>,

    #[arg(short = 'c', long, help = "ChatGPT SIWC OAuth credentials file")]
    pub chatgpt_credentials: Option<PathBuf>,

    #[arg(
        long,
        default_value_t = false,
        help = "Disable Google Antigravity provider"
    )]
    pub no_antigravity: bool,

    #[arg(long, default_value_t = false, help = "Disable ChatGPT SIWC provider")]
    pub no_siwc: bool,

    #[arg(long, default_value_t = false, help = "Print verbose build and version information and exit")]
    pub verbose_version: bool,
}

fn find_existing_path(candidates: &[&str]) -> Option<PathBuf> {
    for c in candidates {
        let p = Path::new(c);
        if p.exists() {
            return Some(p.to_path_buf());
        }
    }
    None
}

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt::init();

    let args = CliArgs::parse();

    if args.verbose_version {
        println!("{}", VersionInfo::current().verbose_string());
        return Ok(());
    }

    let listen_addr: SocketAddr = args.listen.parse()?;

    // 1. Antigravity State Setup
    let antigravity_state = if !args.no_antigravity {
        let client_id = env_or("ANTIGRAVITY_CLIENT_ID", DEFAULT_CLIENT_ID);
        let client_secret = env_or("ANTIGRAVITY_CLIENT_SECRET", DEFAULT_CLIENT_SECRET);

        let creds_file = args.antigravity_credentials.unwrap_or_else(|| {
            find_existing_path(&[
                ".antigravity-token.json",
                "test/data/antigravity_gemini.json",
                "test/data/opencode_gemini.json",
                "../test/data/antigravity_gemini.json",
                "../test/data/opencode_gemini.json",
            ])
            .unwrap_or_else(|| PathBuf::from(".antigravity-token.json"))
        });

        match load_credentials(&creds_file) {
            Ok(creds) => {
                info!("Loaded Antigravity credentials from {:?}", creds_file);
                Some(AntigravityState::new(
                    creds_file,
                    client_id,
                    client_secret,
                    creds,
                ))
            }
            Err(err) => {
                warn!(
                    "Could not load Antigravity credentials from {:?}: {}",
                    creds_file, err
                );
                None
            }
        }
    } else {
        None
    };

    // 2. SIWC ChatGPT Setup
    let siwc_client = if !args.no_siwc {
        let creds_file = args.chatgpt_credentials.unwrap_or_else(|| {
            find_existing_path(&[
                "data/chatgpt.json",
                "test/data/chatgpt.json",
                "../test/data/chatgpt.json",
            ])
            .unwrap_or_else(|| PathBuf::from("data/chatgpt.json"))
        });

        match load_siwc_credentials(&creds_file) {
            Ok(creds) => {
                info!("Loaded SIWC ChatGPT credentials from {:?}", creds_file);
                Some(SiwcClient::new(creds_file, None, creds))
            }
            Err(err) => {
                warn!(
                    "Could not load SIWC ChatGPT credentials from {:?}: {}",
                    creds_file, err
                );
                None
            }
        }
    } else {
        None
    };

    let gateway_state = GatewayState {
        antigravity: antigravity_state,
        siwc: siwc_client,
    };

    let app = build_gateway_router(gateway_state);

    info!("Unified Gateway listening at http://{}/v1", listen_addr);
    info!("Models endpoint: http://{}/v1/models", listen_addr);
    info!(
        "Chat completions: http://{}/v1/chat/completions",
        listen_addr
    );

    let listener = tokio::net::TcpListener::bind(&listen_addr).await?;
    axum::serve(
        listener,
        app.into_make_service_with_connect_info::<SocketAddr>(),
    )
    .await?;

    Ok(())
}
