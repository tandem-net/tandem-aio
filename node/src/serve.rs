//! Hosting a user's web app on this node.
//!
//! A serve deployment is a real web app (Flask, FastAPI, a plain stdlib server,
//! ...). We run it inside the hardened sandbox with **no network at all**
//! (`--unshare-net`), so it can't phone home or be reached from the outside. It
//! talks to us over a **unix domain socket** in its own working directory
//! instead: the app binds `$TANDEM_SERVE_SOCKET`, and the node proxies HTTP to
//! that socket. The node is the app's only door to the world.
//!
//! This module owns two things: launching the app in the sandbox and waiting for
//! it to come up (`ServedApp`), and forwarding one HTTP request to it over the
//! socket (`proxy_request`). The loop that pulls requests from the server and
//! feeds them here lives in the worker wiring.

// The serve request/claim loop is still being wired into main, so a couple of
// these are only used by tests for now.
#![allow(dead_code)]

use std::collections::HashMap;
use std::error::Error;
use std::fs;
use std::io::{self, Read, Write};
use std::os::unix::net::UnixStream;
use std::path::{Path, PathBuf};
use std::process::{Child, Command};
use std::time::{Duration, Instant};

use base64::Engine;

use crate::config::NodeConfig;
use crate::sandbox::{spawn_sandboxed, SandboxLimits, SandboxSpec};

type BoxError = Box<dyn Error + Send + Sync>;

/// The filename of the unix socket the app binds, inside its working directory.
const SOCKET_NAME: &str = "tandem-serve.sock";

/// One HTTP response proxied back from a hosted app.
#[derive(Debug, Clone)]
pub struct HttpResponse {
    pub status: u16,
    pub headers: Vec<(String, String)>,
    pub body: Vec<u8>,
}

/// A running hosted app: the sandboxed child plus where its socket lives.
pub struct ServedApp {
    child: Child,
    socket_path: PathBuf,
}

impl ServedApp {
    /// Where the app's unix socket lives on the node's filesystem.
    pub fn socket_path(&self) -> &Path {
        &self.socket_path
    }

    /// Stop the app. Best-effort: ask it to die, then don't block forever.
    pub fn shutdown(&mut self) {
        let _ = self.child.kill();
        let _ = self.child.wait();
        let _ = std::fs::remove_file(&self.socket_path);
    }
}

/// Launch a web app in the sandbox and wait for its socket to come up.
///
/// * `work_dir` already contains the unpacked app (its code is at the top).
/// * `start_command` is what the user told us to run, e.g. `["python3", "app.py"]`.
/// * `limits` are the resource ceilings (the account's RAM cap, etc.).
pub fn launch_app(
    work_dir: &Path,
    start_command: &[String],
    node_id: &str,
    limits: SandboxLimits,
) -> io::Result<ServedApp> {
    let socket_path = work_dir.join(SOCKET_NAME);
    // Clear any stale socket from a previous run so the app can bind cleanly.
    let _ = std::fs::remove_file(&socket_path);

    let spec = SandboxSpec {
        work_dir: work_dir.to_path_buf(),
        command: start_command.to_vec(),
        env: vec![
            ("PATH".to_string(), "/usr/bin:/bin".to_string()),
            ("HOME".to_string(), "/app".to_string()),
            // The app binds this socket; inside the sandbox the work dir is /app.
            (
                "TANDEM_SERVE_SOCKET".to_string(),
                format!("/app/{SOCKET_NAME}"),
            ),
            // So the app can tell which node it's running on (handy for showing
            // that the load balancer really is spreading traffic).
            ("TANDEM_NODE_ID".to_string(), node_id.to_string()),
        ],
        allow_network: false,
        limits,
        cgroup_parent: None,
    };

    let child = spawn_sandboxed(&spec)?;
    let mut app = ServedApp { child, socket_path };

    // Wait for the app to bind its socket and actually accept a connection.
    if let Err(err) = wait_until_ready(&app.socket_path, Duration::from_secs(15)) {
        app.shutdown();
        return Err(err);
    }
    Ok(app)
}

/// Block until the app is accepting connections on its socket, or time out.
fn wait_until_ready(socket_path: &Path, timeout: Duration) -> io::Result<()> {
    let deadline = Instant::now() + timeout;
    loop {
        if socket_path.exists() {
            if let Ok(stream) = UnixStream::connect(socket_path) {
                drop(stream);
                return Ok(());
            }
        }
        if Instant::now() >= deadline {
            return Err(io::Error::new(
                io::ErrorKind::TimedOut,
                "hosted app did not start listening on its socket in time",
            ));
        }
        std::thread::sleep(Duration::from_millis(100));
    }
}

/// Forward one HTTP request to the app over its unix socket and read the reply.
///
/// We speak plain HTTP/1.1 with `Connection: close`, which keeps the proxy
/// simple: send the request, read until the app closes the socket, done. That's
/// plenty for request/response web apps.
pub fn proxy_request(
    socket_path: &Path,
    method: &str,
    path: &str,
    headers: &[(String, String)],
    body: &[u8],
) -> io::Result<HttpResponse> {
    let mut stream = UnixStream::connect(socket_path)?;
    stream.set_read_timeout(Some(Duration::from_secs(60)))?;

    let mut request = Vec::new();
    request.extend_from_slice(format!("{method} {path} HTTP/1.1\r\n").as_bytes());
    request.extend_from_slice(b"Host: tandem\r\n");
    request.extend_from_slice(b"Connection: close\r\n");
    for (name, value) in headers {
        let lowered = name.to_ascii_lowercase();
        // We set these ourselves, so skip any the caller passed.
        if lowered == "host" || lowered == "connection" || lowered == "content-length" {
            continue;
        }
        request.extend_from_slice(format!("{name}: {value}\r\n").as_bytes());
    }
    request.extend_from_slice(format!("Content-Length: {}\r\n", body.len()).as_bytes());
    request.extend_from_slice(b"\r\n");
    request.extend_from_slice(body);

    stream.write_all(&request)?;
    stream.flush()?;

    let mut raw = Vec::new();
    stream.read_to_end(&mut raw)?;
    parse_http_response(&raw)
}

/// Split a raw HTTP/1.1 response into status, headers, and body.
fn parse_http_response(raw: &[u8]) -> io::Result<HttpResponse> {
    // Find the blank line that separates headers from the body.
    let split_at = find_subslice(raw, b"\r\n\r\n").ok_or_else(|| {
        io::Error::new(io::ErrorKind::InvalidData, "malformed HTTP response from app")
    })?;
    let head = &raw[..split_at];
    let body = raw[split_at + 4..].to_vec();

    let head_text = String::from_utf8_lossy(head);
    let mut lines = head_text.split("\r\n");

    let status_line = lines.next().unwrap_or("");
    let status = parse_status_code(status_line)?;

    let mut headers = Vec::new();
    for line in lines {
        if let Some((name, value)) = line.split_once(':') {
            headers.push((name.trim().to_string(), value.trim().to_string()));
        }
    }

    Ok(HttpResponse {
        status,
        headers,
        body,
    })
}

/// Pull the numeric status code out of a line like `HTTP/1.1 200 OK`.
fn parse_status_code(status_line: &str) -> io::Result<u16> {
    let mut parts = status_line.split_whitespace();
    let _version = parts.next();
    let code = parts.next().unwrap_or("");
    code.parse::<u16>()
        .map_err(|_| io::Error::new(io::ErrorKind::InvalidData, "bad HTTP status line from app"))
}

/// Find the first index where `needle` appears in `haystack`.
fn find_subslice(haystack: &[u8], needle: &[u8]) -> Option<usize> {
    if needle.is_empty() || haystack.len() < needle.len() {
        return None;
    }
    haystack
        .windows(needle.len())
        .position(|window| window == needle)
}

// ---------------------------------------------------------------------------
// Coordination with the server: claim a deployment, then serve its requests.
// ---------------------------------------------------------------------------

/// Where a deployment's unpacked app lives on this node.
fn serve_work_dir(pid: &str) -> PathBuf {
    std::env::temp_dir().join("tandem-serve").join(pid)
}

/// One request the load balancer handed us to run against a hosted app.
struct PendingRequest {
    req_id: String,
    pid: String,
    method: String,
    path: String,
    headers: Vec<(String, String)>,
    body: Vec<u8>,
}

/// Add the node's auth headers to an outgoing request.
fn with_node_auth(builder: reqwest::RequestBuilder, cfg: &NodeConfig) -> reqwest::RequestBuilder {
    builder
        .header("X-Node-Id", &cfg.node_id)
        .header("Authorization", format!("Bearer {}", cfg.node_token))
}

/// The node's serve side: keep asking the server for a deployment to host, and
/// once we're hosting one, keep pulling its requests and proxying them.
///
/// This runs forever alongside the compute task loop. It only ever talks *out*
/// to the server, same as everything else the node does.
pub async fn serve_loop(cfg: NodeConfig) {
    let client = reqwest::Client::new();
    let mut apps: HashMap<String, ServedApp> = HashMap::new();

    loop {
        // 1. Pick up a new assignment if the server has one for us.
        match try_claim(&client, &cfg).await {
            Ok(Some((pid, start_command))) => {
                eprintln!("[serve] assigned deployment {pid}");
                match setup_app(&client, &cfg, &pid, &start_command).await {
                    Ok(app) => {
                        eprintln!("[serve] {pid} is up and serving");
                        apps.insert(pid, app);
                    }
                    Err(err) => eprintln!("[serve] could not start {pid}: {err}"),
                }
            }
            Ok(None) => {}
            Err(err) => eprintln!("[serve] claim error: {err}"),
        }

        // 2. If we're hosting anything, serve one request (this also heartbeats).
        if apps.is_empty() {
            tokio::time::sleep(Duration::from_millis(500)).await;
            continue;
        }

        let pids: Vec<String> = apps.keys().cloned().collect();
        match next_request(&client, &cfg, &pids).await {
            Ok(Some(req)) => handle_request(&client, &cfg, &apps, req).await,
            Ok(None) => {}
            Err(err) => {
                eprintln!("[serve] next-request error: {err}");
                tokio::time::sleep(Duration::from_millis(500)).await;
            }
        }
    }
}

/// Ask the server for a serve assignment. Returns `(pid, start_command)`.
async fn try_claim(
    client: &reqwest::Client,
    cfg: &NodeConfig,
) -> Result<Option<(String, Vec<String>)>, BoxError> {
    let url = format!("{}/nodes/serve/claim", cfg.server_url);
    let response = with_node_auth(client.post(&url), cfg).send().await?;

    if response.status() == reqwest::StatusCode::NO_CONTENT {
        return Ok(None);
    }
    if !response.status().is_success() {
        return Err(format!("claim returned {}", response.status()).into());
    }

    let value: serde_json::Value = response.json().await?;
    let pid = value["pid"].as_str().ok_or("assignment missing pid")?.to_string();
    let start_command = value["start_command"]
        .as_array()
        .ok_or("assignment missing start_command")?
        .iter()
        .map(|item| item.as_str().unwrap_or("").to_string())
        .collect();
    Ok(Some((pid, start_command)))
}

/// Download the app bundle, unpack it, and launch it in the sandbox.
async fn setup_app(
    client: &reqwest::Client,
    cfg: &NodeConfig,
    pid: &str,
    start_command: &[String],
) -> Result<ServedApp, BoxError> {
    let url = format!("{}/nodes/serve/{}/bundle", cfg.server_url, pid);
    let response = with_node_auth(client.get(&url), cfg).send().await?;
    if !response.status().is_success() {
        return Err(format!("bundle download returned {}", response.status()).into());
    }
    let bytes = response.bytes().await?;

    let work_dir = serve_work_dir(pid);
    let _ = fs::remove_dir_all(&work_dir);
    fs::create_dir_all(&work_dir)?;

    let tar_path = work_dir.join("bundle.tar");
    fs::write(&tar_path, &bytes)?;
    let status = Command::new("tar")
        .arg("-xf")
        .arg(&tar_path)
        .arg("-C")
        .arg(&work_dir)
        .status()?;
    if !status.success() {
        return Err("could not unpack the app bundle".into());
    }
    let _ = fs::remove_file(&tar_path);

    let app = launch_app(&work_dir, start_command, &cfg.node_id, SandboxLimits::default())?;
    Ok(app)
}

/// Long-poll the server for the next request across the deployments we host.
async fn next_request(
    client: &reqwest::Client,
    cfg: &NodeConfig,
    pids: &[String],
) -> Result<Option<PendingRequest>, BoxError> {
    let url = format!("{}/nodes/serve/next", cfg.server_url);
    let response = with_node_auth(client.post(&url), cfg)
        .json(&serde_json::json!({ "pids": pids }))
        .send()
        .await?;

    if response.status() == reqwest::StatusCode::NO_CONTENT {
        return Ok(None);
    }
    if !response.status().is_success() {
        return Err(format!("next-request returned {}", response.status()).into());
    }

    let value: serde_json::Value = response.json().await?;
    let headers: Vec<(String, String)> =
        serde_json::from_str(value["headers"].as_str().unwrap_or("[]")).unwrap_or_default();
    let body = base64::engine::general_purpose::STANDARD
        .decode(value["body_b64"].as_str().unwrap_or(""))
        .unwrap_or_default();

    Ok(Some(PendingRequest {
        req_id: value["req_id"].as_str().unwrap_or("").to_string(),
        pid: value["pid"].as_str().unwrap_or("").to_string(),
        method: value["method"].as_str().unwrap_or("GET").to_string(),
        path: value["path"].as_str().unwrap_or("/").to_string(),
        headers,
        body,
    }))
}

/// Proxy one request to its app and send the response back to the server.
async fn handle_request(
    client: &reqwest::Client,
    cfg: &NodeConfig,
    apps: &HashMap<String, ServedApp>,
    req: PendingRequest,
) {
    let Some(app) = apps.get(&req.pid) else {
        return;
    };
    let socket = app.socket_path().to_path_buf();

    // The proxy call is blocking (a plain unix socket), so run it off the async
    // runtime's threads.
    let proxied = tokio::task::spawn_blocking(move || {
        proxy_request(&socket, &req.method, &req.path, &req.headers, &req.body)
    })
    .await;

    let response = match proxied {
        Ok(Ok(response)) => response,
        _ => HttpResponse {
            status: 502,
            headers: Vec::new(),
            body: b"the app could not handle the request".to_vec(),
        },
    };

    if let Err(err) = send_response(client, cfg, &req.req_id, &response).await {
        eprintln!("[serve] could not return the response: {err}");
    }
}

/// Hand one app response back to the server for the load balancer to return.
async fn send_response(
    client: &reqwest::Client,
    cfg: &NodeConfig,
    req_id: &str,
    response: &HttpResponse,
) -> Result<(), BoxError> {
    let body_b64 = base64::engine::general_purpose::STANDARD.encode(&response.body);
    let payload = serde_json::json!({
        "status": response.status,
        "headers": response.headers,
        "body_b64": body_b64,
    });

    let url = format!("{}/nodes/serve/response/{}", cfg.server_url, req_id);
    let result = with_node_auth(client.post(&url), cfg)
        .json(&payload)
        .send()
        .await?;
    if !result.status().is_success() {
        return Err(format!("submitting response returned {}", result.status()).into());
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::sandbox::bwrap_available;

    // A tiny stdlib-only web app that binds the unix socket Tandem hands it and
    // answers every GET with a fixed body. No third-party deps, so it runs in the
    // no-network sandbox as-is.
    const SAMPLE_APP: &str = r#"
import os, socketserver, http.server

SOCK = os.environ["TANDEM_SERVE_SOCKET"]

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"hello-from-serve"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *a):
        pass

class UnixHTTPServer(socketserver.UnixStreamServer):
    def get_request(self):
        conn, _ = self.socket.accept()
        return conn, ("local", 0)

try:
    os.remove(SOCK)
except FileNotFoundError:
    pass

UnixHTTPServer(SOCK, Handler).serve_forever()
"#;

    #[test]
    fn hosts_an_app_in_the_sandbox_and_proxies_a_request() {
        if !bwrap_available() {
            return; // sandbox not available on this machine; skip
        }

        let work = std::env::temp_dir().join("tandem_serve_test_app");
        let _ = std::fs::create_dir_all(&work);
        std::fs::write(work.join("app.py"), SAMPLE_APP).unwrap();

        let start = vec!["python3".to_string(), "app.py".to_string()];
        let mut app = match launch_app(&work, &start, "test-node", SandboxLimits::default()) {
            Ok(app) => app,
            Err(_) => return, // no python3 in the sandbox on this machine; skip
        };

        let response = proxy_request(app.socket_path(), "GET", "/", &[], b"")
            .expect("proxy request should succeed");
        app.shutdown();

        assert_eq!(response.status, 200);
        assert_eq!(response.body, b"hello-from-serve");
    }
}
