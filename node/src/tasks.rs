use base64::Engine;
use base64::engine::general_purpose::STANDARD as BASE64;
use reqwest::{Client, StatusCode};
use serde::{Deserialize, Serialize};
use serde_json::json;
use std::fs;
use std::process::Stdio;
use std::time::Duration;
use tokio::io::AsyncWriteExt;
use tokio::process::Command;
use tokio::time::timeout;

use crate::measure;

pub type DynError = Box<dyn std::error::Error + Send + Sync>;

const IDENTITY_FILE: &str = "node_identity.json";
const PYTHON_WORKER: &str = r#"
import base64
import cloudpickle
import sys
import traceback

payload = sys.stdin.buffer.read()

try:
    task = cloudpickle.loads(payload)
    result = task()
    encoded = base64.b64encode(cloudpickle.dumps(result)).decode('ascii')
    sys.stdout.write(encoded)
except Exception:
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
"#;

#[derive(Serialize, Clone, Debug)]
pub struct Metrics {
    pub latency: f32,
    pub download: f32,
    pub upload: f32,
}

#[derive(Serialize, Deserialize, Clone, Debug)]
pub struct NodeIdentity {
    pub node_id: String,
    pub node_token: String,
}

#[derive(Deserialize, Debug)]
struct RegisterResponse {
    node_id: String,
    node_token: String,
}

#[derive(Deserialize, Debug, Clone)]
pub struct ClaimedTask {
    pub tid: String,
    pub job_id: String,
    pub filename: String,
    pub claim_token: String,
    pub download_url: String,
}

pub async fn benchmark_download(client: Client, url: impl Into<String>) -> Result<f32, DynError> {
    let url = url.into();
    let (bytes, duration) = measure::measure_download(client, &url).await?;
    let mb = bytes as f64 / (1024.0 * 1024.0);
    let speed = (mb / duration) as f32;

    println!(
        "downloaded {:.2} MB in {:.2}s ({:.2} MB/s)",
        mb, duration, speed
    );
    Ok(speed)
}

pub async fn benchmark_upload(
    client: Client,
    url: impl Into<String>,
    bytes: usize,
) -> Result<f32, DynError> {
    let url = url.into();
    let duration = measure::measure_upload(client, &url, bytes, 65536).await?;
    let mb = bytes as f64 / (1024.0 * 1024.0);
    let speed = (mb / duration) as f32;

    println!(
        "uploaded {:.2} MB in {:.2}s ({:.2} MB/s)",
        mb, duration, speed
    );
    Ok(speed)
}

pub fn save_node_identity(identity: &NodeIdentity) -> Result<(), DynError> {
    let contents = serde_json::to_vec_pretty(identity)?;
    fs::write(IDENTITY_FILE, contents)?;
    Ok(())
}

pub async fn register(
    client: Client,
    url: impl Into<String>,
    metrics: &Metrics,
) -> Result<NodeIdentity, DynError> {
    let response = client
        .post(url.into())
        .json(metrics)
        .send()
        .await?
        .error_for_status()?;

    let parsed: RegisterResponse = response.json().await?;
    let identity = NodeIdentity {
        node_id: parsed.node_id,
        node_token: parsed.node_token,
    };

    save_node_identity(&identity)?;
    Ok(identity)
}

pub async fn ping(
    client: Client,
    url: impl Into<String>,
    identity: &NodeIdentity,
    metrics: &Metrics,
) -> Result<(), DynError> {
    client
        .post(url.into())
        .bearer_auth(&identity.node_token)
        .header("X-Node-Id", &identity.node_id)
        .json(metrics)
        .send()
        .await?
        .error_for_status()?;

    Ok(())
}

pub async fn health(
    client: Client,
    url: impl Into<String>,
    identity: &NodeIdentity,
    metrics: &Metrics,
) -> Result<(), DynError> {
    client
        .post(url.into())
        .bearer_auth(&identity.node_token)
        .header("X-Node-Id", &identity.node_id)
        .json(metrics)
        .send()
        .await?
        .error_for_status()?;

    Ok(())
}

pub async fn claim_task(
    client: Client,
    url: impl Into<String>,
    identity: &NodeIdentity,
) -> Result<Option<ClaimedTask>, DynError> {
    let response = client
        .post(url.into())
        .bearer_auth(&identity.node_token)
        .header("X-Node-Id", &identity.node_id)
        .json(&json!({}))
        .send()
        .await?;

    if response.status() == StatusCode::NO_CONTENT {
        return Ok(None);
    }

    let response = response.error_for_status()?;
    let task: ClaimedTask = response.json().await?;
    Ok(Some(task))
}

pub async fn download_task_payload(
    client: Client,
    task: &ClaimedTask,
    identity: &NodeIdentity,
) -> Result<Vec<u8>, DynError> {
    let response = client
        .get(&task.download_url)
        .bearer_auth(&identity.node_token)
        .header("X-Node-Id", &identity.node_id)
        .send()
        .await?
        .error_for_status()?;

    let payload = response.bytes().await?;
    Ok(payload.to_vec())
}

pub async fn submit_task_result(
    client: Client,
    server_base_url: &str,
    task: &ClaimedTask,
    identity: &NodeIdentity,
    result_bytes: Vec<u8>,
) -> Result<(), DynError> {
    let url = format!(
        "{}/nodes/tasks/{}/result",
        server_base_url.trim_end_matches('/'),
        task.tid
    );

    client
        .post(url)
        .bearer_auth(&identity.node_token)
        .header("X-Node-Id", &identity.node_id)
        .header("X-Task-Claim", &task.claim_token)
        .header("Content-Type", "application/octet-stream")
        .body(result_bytes)
        .send()
        .await?
        .error_for_status()?;

    Ok(())
}

pub async fn submit_task_failure(
    client: Client,
    server_base_url: &str,
    task: &ClaimedTask,
    identity: &NodeIdentity,
    error_message: &str,
) -> Result<(), DynError> {
    let url = format!(
        "{}/nodes/tasks/{}/result",
        server_base_url.trim_end_matches('/'),
        task.tid
    );

    client
        .post(url)
        .bearer_auth(&identity.node_token)
        .header("X-Node-Id", &identity.node_id)
        .header("X-Task-Claim", &task.claim_token)
        .json(&json!({ "error": error_message }))
        .send()
        .await?
        .error_for_status()?;

    Ok(())
}

pub async fn execute_cloudpickle_task(
    payload: Vec<u8>,
    task_timeout: Duration,
) -> Result<Vec<u8>, DynError> {
    let python_bin =
        std::env::var("TANDEM_NODE_PYTHON").unwrap_or_else(|_| String::from("python3"));

    let mut child = Command::new(&python_bin)
        .arg("-c")
        .arg(PYTHON_WORKER)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()?;

    let mut stdin = child
        .stdin
        .take()
        .ok_or_else(|| String::from("Failed to open python worker stdin"))?;
    stdin.write_all(&payload).await?;
    drop(stdin);

    let output = timeout(task_timeout, child.wait_with_output()).await??;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr).trim().to_string();
        let message = if stderr.is_empty() {
            format!("python worker exited with status {}", output.status)
        } else {
            stderr
        };
        return Err(message.into());
    }

    let stdout = String::from_utf8(output.stdout)?;
    let trimmed = stdout.trim();
    if trimmed.is_empty() {
        return Err(String::from("python worker returned an empty payload").into());
    }

    let decoded = BASE64.decode(trimmed)?;
    Ok(decoded)
}
