use base64::Engine as _;
use base64::engine::general_purpose::STANDARD as BASE64;
use reqwest::{Client, StatusCode};
use serde::{Deserialize, Serialize};
use serde_json::json;
use std::env;
use std::fs;
use std::process::Stdio;
use std::time::Duration;
use tokio::io::AsyncWriteExt;
use tokio::process::Command;
use tokio::time::timeout;
use wasmtime::{Engine, Instance, Module, Store};

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

#[derive(Serialize, Clone, Debug, Default)]
pub struct Metrics {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub latency: Option<f32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub download: Option<f32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub upload: Option<f32>,
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
    #[serde(default)]
    pub task_name: String,
    pub filename: String,
    #[serde(default = "_default_runtime")]
    pub runtime: String,
    pub claim_token: String,
    pub download_url: String,
    #[serde(default)]
    pub timeout_ms: Option<u64>,
    #[serde(default)]
    pub shard_index: Option<u64>,
    #[serde(default)]
    pub shard_total: Option<u64>,
}

fn _default_runtime() -> String {
    String::from("cloudpickle")
}

fn _node_registration_token() -> Option<String> {
    let token = env::var("TANDEM_NODE_REGISTRATION_TOKEN").ok()?;
    let trimmed = token.trim();
    if trimmed.is_empty() {
        return None;
    }
    Some(trimmed.to_string())
}

fn _register_payload(metrics: &Metrics) -> serde_json::Value {
    let mut payload = serde_json::Map::new();
    payload.insert("supports_wasm".to_string(), serde_json::Value::Bool(true));

    if let Some(latency) = metrics.latency {
        payload.insert("latency".to_string(), json!(latency));
    }
    if let Some(download) = metrics.download {
        payload.insert("download".to_string(), json!(download));
    }
    if let Some(upload) = metrics.upload {
        payload.insert("upload".to_string(), json!(upload));
    }

    serde_json::Value::Object(payload)
}

fn _call_tandem_entry(store: &mut Store<()>, instance: &Instance) -> Result<Vec<u8>, DynError> {
    if let Ok(entry) = instance.get_typed_func::<(), ()>(&mut *store, "tandem_entry") {
        entry.call(&mut *store, ())?;
        // zatar would absolutely pick the one task that returns nothing.
        return Ok(b"null".to_vec());
    }

    if let Ok(entry) = instance.get_typed_func::<(), i32>(&mut *store, "tandem_entry") {
        return Ok(serde_json::to_vec(&entry.call(&mut *store, ())?)?);
    }
    if let Ok(entry) = instance.get_typed_func::<(), i64>(&mut *store, "tandem_entry") {
        return Ok(serde_json::to_vec(&entry.call(&mut *store, ())?)?);
    }
    if let Ok(entry) = instance.get_typed_func::<(), f32>(&mut *store, "tandem_entry") {
        return Ok(serde_json::to_vec(&entry.call(&mut *store, ())?)?);
    }
    if let Ok(entry) = instance.get_typed_func::<(), f64>(&mut *store, "tandem_entry") {
        return Ok(serde_json::to_vec(&entry.call(&mut *store, ())?)?);
    }

    Err(String::from(
        "`tandem_entry` must take no parameters and return either unit or a numeric value",
    )
    .into())
}

fn _execute_wasm_task_sync(payload: Vec<u8>) -> Result<Vec<u8>, DynError> {
    let engine = Engine::default();
    let module = Module::from_binary(&engine, &payload)?;
    let mut store = Store::new(&engine, ());
    let instance = Instance::new(&mut store, &module, &[])?;
    _call_tandem_entry(&mut store, &instance)
}

pub fn resolve_task_timeout(task: &ClaimedTask, default_timeout_secs: u64) -> Option<Duration> {
    match task.timeout_ms {
        Some(0) => None,
        Some(timeout_ms) => Some(Duration::from_millis(timeout_ms)),
        None if default_timeout_secs == 0 => None,
        None => Some(Duration::from_secs(default_timeout_secs)),
    }
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
    let mut request = client.post(url.into()).json(&_register_payload(metrics));
    if let Some(token) = _node_registration_token() {
        request = request.bearer_auth(token);
    }

    let response = request.send().await?.error_for_status()?;

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
    task_timeout: Option<Duration>,
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

    let output = match task_timeout {
        Some(limit) => timeout(limit, child.wait_with_output())
            .await
            .map_err(|_| String::from("python worker timed out"))??,
        None => child.wait_with_output().await?,
    };

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

pub async fn execute_wasm_task(
    payload: Vec<u8>,
    task_timeout: Option<Duration>,
) -> Result<Vec<u8>, DynError> {
    let worker = tokio::task::spawn_blocking(move || _execute_wasm_task_sync(payload));

    let worker_result = match task_timeout {
        Some(limit) => timeout(limit, worker)
            .await
            .map_err(|_| String::from("wasm task timed out"))?,
        None => worker.await,
    };

    let wasm_result = worker_result.map_err(|error| format!("wasm worker join error: {error}"))?;
    wasm_result
}
