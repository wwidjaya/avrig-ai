pub mod converter;
pub mod oauth;
pub mod quota;
pub mod server;
pub mod state;
pub mod types;

#[cfg(test)]
mod tests;

pub use converter::*;
pub use oauth::*;
pub use quota::*;
pub use server::*;
pub use state::*;
pub use types::*;

use anyhow::Result;
use clap::Parser;
use std::net::SocketAddr;
use std::path::PathBuf;
use tracing::info;

#[derive(Parser, Debug)]
#[command(
    name = "antigravity-openai",
    about = "Antigravity OpenAI-compatible test server"
)]
pub struct CliArgs {
    #[arg(
        short,
        long,
        default_value = "127.0.0.1:8085",
        help = "local OpenAI-compatible listen address"
    )]
    pub listen: String,

    #[arg(
        short,
        long,
        default_value = ".antigravity-token.json",
        help = "OAuth credentials file"
    )]
    pub credentials: PathBuf,
}

pub async fn run() -> Result<()> {
    tracing_subscriber::fmt::init();

    let args = CliArgs::parse();

    let client_id = env_or("ANTIGRAVITY_CLIENT_ID", DEFAULT_CLIENT_ID);
    let client_secret = env_or("ANTIGRAVITY_CLIENT_SECRET", DEFAULT_CLIENT_SECRET);

    let creds_file = if args.credentials.is_absolute() {
        args.credentials
    } else {
        std::env::current_dir()?.join(args.credentials)
    };

    let creds = match load_credentials(&creds_file) {
        Ok(c) => c,
        Err(err) => {
            info!(
                "Failed to load credentials from {:?}: {}. Starting OAuth login...",
                creds_file, err
            );
            login(&creds_file, &client_id, &client_secret)?
        }
    };

    let listen_addr: SocketAddr = args.listen.parse()?;
    info!(
        "Antigravity OpenAI-compatible endpoint listening at http://{}/v1",
        listen_addr
    );
    info!("Use model IDs from GET http://{}/v1/models", listen_addr);

    let state = AppState::new(creds_file, client_id, client_secret, creds);
    let app = build_router(state);

    let listener = tokio::net::TcpListener::bind(&listen_addr).await?;
    axum::serve(
        listener,
        app.into_make_service_with_connect_info::<SocketAddr>(),
    )
    .await?;

    Ok(())
}
