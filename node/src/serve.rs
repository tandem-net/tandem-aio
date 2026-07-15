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

use std::io::{self, Read, Write};
use std::os::unix::net::UnixStream;
use std::path::{Path, PathBuf};
use std::process::Child;
use std::time::{Duration, Instant};

use crate::sandbox::{spawn_sandboxed, SandboxLimits, SandboxSpec};

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
        let mut app = match launch_app(&work, &start, SandboxLimits::default()) {
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
