mod measure;
mod tasks;

use reqwest::Client;
use std::env;
use std::time::Duration;
use tokio::time::{Instant, interval, sleep};

fn server_base_url() -> String {
    env::var("TANDEM_SERVER_URL")
        .or_else(|_| env::var("SERVER_URL"))
        .unwrap_or_else(|_| String::from("http://127.0.0.1:6767"))
        .trim_end_matches('/')
        .to_string()
}

fn _env_flag(name: &str) -> bool {
    env::var(name)
        .ok()
        .map(|value| {
            matches!(
                value.trim().to_ascii_lowercase().as_str(),
                "1" | "true" | "yes" | "on"
            )
        })
        .unwrap_or(false)
}

fn _task_label(task: &tasks::ClaimedTask) -> String {
    let base = if task.task_name.trim().is_empty() {
        task.filename.clone()
    } else {
        task.task_name.clone()
    };

    match (task.shard_index, task.shard_total) {
        (Some(index), Some(total)) if total > 1 => {
            format!("{} shard {}/{}", base, index + 1, total)
        }
        _ => base,
    }
}

async fn _execute_claimed_task(
    task: &tasks::ClaimedTask,
    payload: Vec<u8>,
    task_timeout: Option<Duration>,
) -> Result<Vec<u8>, tasks::DynError> {
    match task.runtime.trim() {
        "wasm" => tasks::execute_wasm_task(payload, task_timeout).await,
        _ => tasks::execute_cloudpickle_task(payload, task_timeout).await,
    }
}

#[tokio::main]
async fn main() {
    dotenvy::dotenv().ok();

    let client = Client::new();
    let server_base_url = server_base_url();

    let register_url = format!("{}/nodes/register", server_base_url);
    let ping_url = format!("{}/nodes/ping", server_base_url);
    let health_url = format!("{}/nodes/health", server_base_url);
    let claim_url = format!("{}/nodes/tasks/claim", server_base_url);
    let download_benchmark_url = format!("{}/nodes/download", server_base_url);
    let upload_benchmark_url = format!("{}/nodes/upload", server_base_url);

    let metrics = if _env_flag("TANDEM_NODE_BENCHMARK_STARTUP") {
        let download = match tasks::benchmark_download(client.clone(), download_benchmark_url).await
        {
            Ok(speed) => Some(speed),
            Err(error) => {
                eprintln!("download benchmark failed: {}", error);
                None
            }
        };

        let upload_bytes = 300 * 1024 * 1024;
        let upload =
            match tasks::benchmark_upload(client.clone(), upload_benchmark_url, upload_bytes).await
            {
                Ok(speed) => Some(speed),
                Err(error) => {
                    eprintln!("upload benchmark failed: {}", error);
                    None
                }
            };

        let latency_start = Instant::now();
        let latency = match client.get(&server_base_url).send().await {
            Ok(_) => Some(latency_start.elapsed().as_secs_f32() * 1000.0),
            Err(error) => {
                eprintln!("latency probe failed: {}", error);
                None
            }
        };

        tasks::Metrics {
            latency,
            download,
            upload,
        }
    } else {
        tasks::Metrics::default()
    };

    let identity = match tasks::register(client.clone(), register_url, &metrics).await {
        Ok(identity) => identity,
        Err(error) => {
            eprintln!("node registration failed: {}", error);
            return;
        }
    };

    println!("Registered node {}", identity.node_id);

    if let Err(error) = tasks::ping(client.clone(), ping_url, &identity, &metrics).await {
        eprintln!("initial ping failed: {}", error);
    }

    let heartbeat_client = client.clone();
    let heartbeat_identity = identity.clone();
    let heartbeat_metrics = metrics.clone();
    let heartbeat_url = health_url.clone();

    tokio::spawn(async move {
        let mut ticker = interval(Duration::from_millis(250));

        loop {
            ticker.tick().await;

            if let Err(error) = tasks::health(
                heartbeat_client.clone(),
                heartbeat_url.clone(),
                &heartbeat_identity,
                &heartbeat_metrics,
            )
            .await
            {
                eprintln!("health failed: {}", error);
            }
        }
    });

    let task_timeout_secs = env::var("TANDEM_TASK_TIMEOUT_SECS")
        .ok()
        .and_then(|value| value.parse::<u64>().ok())
        .unwrap_or(300);

    loop {
        match tasks::claim_task(client.clone(), claim_url.clone(), &identity).await {
            Ok(Some(task)) => {
                let task_label = _task_label(&task);
                println!(
                    "Claimed task {} for job {} ({}, runtime={})",
                    task.tid, task.job_id, task_label, task.runtime
                );

                let task_timeout = tasks::resolve_task_timeout(&task, task_timeout_secs);
                let execution_result =
                    match tasks::download_task_payload(client.clone(), &task, &identity).await {
                        Ok(payload) => _execute_claimed_task(&task, payload, task_timeout).await,
                        Err(error) => Err(error),
                    };

                match execution_result {
                    Ok(result_bytes) => {
                        if let Err(error) = tasks::submit_task_result(
                            client.clone(),
                            &server_base_url,
                            &task,
                            &identity,
                            result_bytes,
                        )
                        .await
                        {
                            eprintln!("failed to submit result for {}: {}", task.tid, error);
                        } else {
                            println!("Completed task {} ({})", task.tid, task_label);
                        }
                    }
                    Err(error) => {
                        let error_text = error.to_string();
                        eprintln!("task {} failed: {}", task.tid, error_text);

                        if let Err(report_error) = tasks::submit_task_failure(
                            client.clone(),
                            &server_base_url,
                            &task,
                            &identity,
                            &error_text,
                        )
                        .await
                        {
                            eprintln!(
                                "failed to report task failure for {}: {}",
                                task.tid, report_error
                            );
                        }
                    }
                }
            }
            Ok(None) => {
                sleep(Duration::from_millis(250)).await;
            }
            Err(error) => {
                eprintln!("task claim failed: {}", error);
                sleep(Duration::from_secs(1)).await;
            }
        }
    }
}
