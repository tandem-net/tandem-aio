mod config;
mod crypto;
mod executor;
mod health;
mod registration;
mod worker;

use config::NodeConfig;

#[tokio::main]
async fn main() {
    // ── 1. Load .env (ignore errors — file may not exist) ───────────────
    let _ = dotenvy::dotenv();

    // ── 2. Read config ──────────────────────────────────────────────────
    let mut cfg = NodeConfig::from_env();

    eprintln!("[node] server_url = {}", cfg.server_url);

    // ── 3. Register if this is a first boot ─────────────────────────────
    if cfg.node_id.is_empty() {
        eprintln!("[node] no TANDEM_NODE_ID found — starting registration…");
        match registration::register_node(&cfg.server_url, &cfg.private_key_path).await {
            Ok((node_id, node_token)) => {
                cfg.node_id = node_id;
                cfg.node_token = node_token;
            }
            Err(e) => {
                eprintln!("[node] FATAL: registration failed — {e}");
                std::process::exit(1);
            }
        }
    }

    eprintln!("[node] node_id = {}", cfg.node_id);

    // ── 4. Load RSA private key ─────────────────────────────────────────
    let private_key = match crypto::load_private_key(&cfg.private_key_path) {
        Ok(k) => k,
        Err(e) => {
            eprintln!(
                "[node] FATAL: could not load private key from '{}': {e}",
                cfg.private_key_path
            );
            std::process::exit(1);
        }
    };

    // ── 5. Spawn background health loop ─────────────────────────────────
    let health_cfg = cfg.clone();
    tokio::spawn(async move {
        health::health_loop(health_cfg).await;
    });

    eprintln!("[node] health loop started (every 3 s)");
    eprintln!("[node] entering task claim loop…");

    // ── 6. Run the main task loop, with graceful shutdown ───────────────
    tokio::select! {
        _ = worker::task_loop(&cfg, &private_key) => {
            // task_loop runs forever; this arm only fires if it somehow returns.
        }
        _ = shutdown_signal() => {
            eprintln!("\n[node] shutdown signal received — exiting gracefully");
        }
    }
}

/// Wait for SIGINT (Ctrl-C) or SIGTERM.
async fn shutdown_signal() {
    use tokio::signal;

    let ctrl_c = async {
        signal::ctrl_c()
            .await
            .expect("failed to install Ctrl-C handler");
    };

    #[cfg(unix)]
    let terminate = async {
        signal::unix::signal(signal::unix::SignalKind::terminate())
            .expect("failed to install SIGTERM handler")
            .recv()
            .await;
    };

    #[cfg(not(unix))]
    let terminate = std::future::pending::<()>();

    tokio::select! {
        _ = ctrl_c => {}
        _ = terminate => {}
    }
}