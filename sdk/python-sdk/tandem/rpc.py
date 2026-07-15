"""Send a compute call to a Tandem server and hand back a future.

`submit_task` does the non-blocking half of a remote call: it makes sure the
project is deployed, ships the compiled task plus its inputs to the server, and
returns a `ComputeFuture` immediately. The blocking half -- waiting for the node
to answer -- lives on the future itself (`.result()` / `.done()`), so you can
fire off many tasks at once.
"""

import base64
import json
import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

from tandem.future import ComputeFuture

# Try to use tomllib on 3.11+, fall back to tomli for older Pythons.
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore


def _resolve_server_url() -> str:
    url = (
        os.environ.get("TANDEM_SERVER_URL")
        or os.environ.get("SERVER_URL")
        or "http://127.0.0.1:6767"
    )
    return url.rstrip("/")


def _resolve_api_key() -> str:
    api_key = (os.environ.get("TANDEM_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("Missing API key. Set TANDEM_API_KEY in the environment.")
    return api_key


def _get_project_config() -> dict[str, Any]:
    config_path = Path("tandem.toml").resolve()
    if not config_path.exists():
        raise FileNotFoundError("tandem.toml not found in the current directory.")
    with open(config_path, "rb") as handle:
        data = tomllib.load(handle)
    project = data.get("project", {})
    if not project:
        raise ValueError("Invalid tandem.toml: missing [project] table.")
    name = project.get("name")
    if not name:
        raise ValueError("Invalid tandem.toml: missing project.name.")
    output_dir = project.get("output_dir", f".tandem_build/{name}")
    return {
        "name": name,
        "output_dir": Path(output_dir).resolve(),
        "config_path": config_path,
    }


def _deploy_project(server_url: str, api_key: str, config_path: Path) -> str:
    with open(config_path, "rb") as handle:
        resp = requests.post(
            f"{server_url}/deploy/",
            headers={"X-API-Key": api_key},
            files=[("toml_file", (config_path.name, handle, "application/toml"))],
            timeout=10,
        )
    resp.raise_for_status()
    return resp.json()["pid"]


def _find_task(manifest: dict[str, Any], short_name: str) -> dict[str, Any]:
    for task in manifest.get("tasks", []):
        if task.get("name") == short_name or task.get("qualname") == short_name:
            return task
    raise ValueError(f"Task {short_name} not found in the build manifest.")


def _build_start_files(
    config: dict[str, Any],
    manifest_bytes: bytes,
    manifest: dict[str, Any],
    task_info: dict[str, Any],
    combined_payload: bytes,
) -> list[tuple[str, tuple[str, bytes, str]]]:
    """Assemble the multipart upload for POST /start/.

    The task being called ships with its inputs folded into a TNDM payload; every
    other task in the project ships as plain WASM so the server has the whole set.
    """
    output_dir: Path = config["output_dir"]
    config_path: Path = config["config_path"]

    files: list[tuple[str, tuple[str, bytes, str]]] = [
        ("toml_file", (config_path.name, config_path.read_bytes(), "application/toml")),
        ("manifest_file", ("manifest.json", manifest_bytes, "application/json")),
    ]

    for task in manifest.get("tasks", []):
        wasm_rel = task.get("wasm")
        if not wasm_rel:
            continue
        filename = Path(wasm_rel).name
        if task is task_info:
            files.append(("wasm_files", (filename, combined_payload, "application/wasm")))
        else:
            wasm_bytes = (output_dir / wasm_rel).read_bytes()
            files.append(("wasm_files", (filename, wasm_bytes, "application/wasm")))
    return files


def _make_poll(server_url: str, api_key: str, job_id: str, job_token: str, short_name: str):
    """Build the zero-arg poll a ComputeFuture uses to check on its job once."""
    headers = {"X-API-Key": api_key, "X-Job-Token": job_token}
    results_url = f"{server_url}/start/{job_id}/results"

    def poll() -> tuple[bool, Any, str | None]:
        resp = requests.get(results_url, headers=headers, timeout=10)
        resp.raise_for_status()
        summary = resp.json()

        if not summary.get("done"):
            return (False, None, None)

        if summary.get("status") != "completed":
            return (True, None, f"Job failed or was cancelled: {summary}")

        for task_result in summary.get("results", []):
            if task_result.get("task_name") != short_name:
                continue
            if task_result.get("status") != "completed":
                return (True, None, f"Worker failed: {task_result.get('error')}")
            raw = base64.b64decode(task_result.get("result_b64"))
            try:
                return (True, json.loads(raw.decode("utf-8")), None)
            except Exception:
                return (True, raw.decode("utf-8"), None)

        return (True, None, f"Task {short_name} not found in the job results.")

    return poll


def submit_task(task_name: str, args: tuple[Any, ...], kwargs: dict[str, Any]) -> ComputeFuture:
    """Send one compute call to the server and return a future for its result."""
    load_dotenv()
    server_url = _resolve_server_url()
    api_key = _resolve_api_key()

    config = _get_project_config()
    output_dir: Path = config["output_dir"]
    manifest_path = output_dir / ".tandem" / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"Manifest not found at {manifest_path}. Did you run `tandem build`?"
        )

    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes.decode("utf-8"))

    short_name = task_name.split(":")[-1]
    task_info = _find_task(manifest, short_name)

    wasm_rel = task_info.get("wasm")
    if not wasm_rel:
        raise ValueError(f"No WASM file specified for task {short_name}.")
    wasm_path = output_dir / wasm_rel
    if not wasm_path.exists():
        raise FileNotFoundError(f"WASM file not found at {wasm_path}.")
    wasm_bytes = wasm_path.read_bytes()

    # Combine WASM and JSON inputs: MAGIC(4) + LEN(4) + WASM + INPUT. The "TNDM"
    # magic tells the worker how to split the module from its input.
    input_json = json.dumps([args, kwargs]).encode("utf-8")
    combined_payload = b"TNDM" + len(wasm_bytes).to_bytes(4, "little") + wasm_bytes + input_json

    pid = os.environ.get("TANDEM_PID")
    if not pid:
        pid = _deploy_project(server_url, api_key, config["config_path"])

    files = _build_start_files(config, manifest_bytes, manifest, task_info, combined_payload)
    resp = requests.post(
        f"{server_url}/start/",
        headers={"X-API-Key": api_key},
        data={"pid": pid},
        files=files,
        timeout=60,
    )
    if resp.status_code != 202:
        raise RuntimeError(f"Failed to start task: {resp.text}")

    start_result = resp.json()
    poll = _make_poll(
        server_url,
        api_key,
        start_result["job_id"],
        start_result["job_token"],
        short_name,
    )
    return ComputeFuture(poll)
