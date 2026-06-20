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

#[tokio::main]
async fn main() {
    let client = Client::new();
    let server_base_url = server_base_url();

    let register_url = format!("{}/nodes/register", server_base_url);
    let ping_url = format!("{}/nodes/ping", server_base_url);
    let health_url = format!("{}/nodes/health", server_base_url);
    let claim_url = format!("{}/nodes/tasks/claim", server_base_url);
    let download_benchmark_url = format!("{}/nodes/download", server_base_url);
    let upload_benchmark_url = format!("{}/nodes/upload", server_base_url);

    let download_speed =
        match tasks::benchmark_download(client.clone(), download_benchmark_url).await {
            Ok(speed) => speed,
            Err(error) => {
                eprintln!("download benchmark failed: {}", error);
                0.0
            }
        };

    let upload_bytes = 300 * 1024 * 1024;
    let upload_speed =
        match tasks::benchmark_upload(client.clone(), upload_benchmark_url, upload_bytes).await {
            Ok(speed) => speed,
            Err(error) => {
                eprintln!("upload benchmark failed: {}", error);
                0.0
            }
        };

    let latency_start = Instant::now();
    let latency = match client.get(&server_base_url).send().await {
        Ok(_) => latency_start.elapsed().as_secs_f32() * 1000.0,
        Err(error) => {
            eprintln!("latency probe failed: {}", error);
            0.0
        }
    };

    let metrics = tasks::Metrics {
        latency,
        download: download_speed,
        upload: upload_speed,
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
                println!(
                    "Claimed task {} for job {} ({})",
                    task.tid, task.job_id, task.filename
                );

                let execution_result =
                    match tasks::download_task_payload(client.clone(), &task, &identity).await {
                        Ok(payload) => {
                            tasks::execute_cloudpickle_task(
                                payload,
                                Duration::from_secs(task_timeout_secs),
                            )
                            .await
                        }
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
                            println!("Completed task {}", task.tid);
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
