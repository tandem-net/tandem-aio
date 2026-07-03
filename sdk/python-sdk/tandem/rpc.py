import json
import base64
import os
import time
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

# Try to use tomli for Python < 3.11
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore


def _resolve_server_url() -> str:
    url = os.environ.get("TANDEM_SERVER_URL") or os.environ.get("SERVER_URL") or "http://127.0.0.1:6767"
    return url.rstrip("/")


def _resolve_api_key() -> str:
    api_key = (os.environ.get("TANDEM_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("Missing API key. Set TANDEM_API_KEY in the environment.")
    return api_key


def _get_project_config() -> dict[str, Any]:
    # Look for tandem.toml in current directory
    config_path = Path("tandem.toml").resolve()
    if not config_path.exists():
        raise FileNotFoundError("tandem.toml not found in the current directory.")
    with open(config_path, "rb") as f:
        data = tomllib.load(f)
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
        "config_path": config_path
    }


def _deploy_project(server_url: str, api_key: str, config_path: Path) -> str:
    with open(config_path, "rb") as f:
        resp = requests.post(
            f"{server_url}/deploy/",
            headers={"X-API-Key": api_key},
            files=[("toml_file", (config_path.name, f, "application/toml"))],
            timeout=10,
        )
    resp.raise_for_status()
    return resp.json()["pid"]


def dispatch_task(task_name: str, args: tuple[Any, ...], kwargs: dict[str, Any]) -> Any:
    load_dotenv()
    server_url = _resolve_server_url()
    api_key = _resolve_api_key()

    config = _get_project_config()
    output_dir: Path = config["output_dir"]
    manifest_path = output_dir / ".tandem" / "manifest.json"
    
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found at {manifest_path}. Did you run `tandem build`?")
        
    with open(manifest_path, "rb") as f:
        manifest_bytes = f.read()
    manifest = json.loads(manifest_bytes.decode("utf-8"))
    
    tasks = manifest.get("tasks", [])
    task_info = None
    for t in tasks:
        # Match by name or qualname
        if t.get("name") == task_name.split(":")[-1] or t.get("qualname") == task_name.split(":")[-1]:
            task_info = t
            break
            
    if not task_info:
        raise ValueError(f"Task {task_name} not found in manifest.")
        
    wasm_rel_path = task_info.get("wasm")
    if not wasm_rel_path:
        raise ValueError(f"No WASM file specified for task {task_name}.")
        
    wasm_path = output_dir / wasm_rel_path
    if not wasm_path.exists():
        raise FileNotFoundError(f"WASM file not found at {wasm_path}.")
        
    with open(wasm_path, "rb") as f:
        wasm_bytes = f.read()

    # Combine WASM and JSON inputs: MAGIC(4) + LEN(4) + WASM + INPUT
    # We use magic "TNDM" to let the worker know how to parse this
    input_json = json.dumps([args, kwargs]).encode("utf-8")
    magic = b"TNDM"
    wasm_len = len(wasm_bytes).to_bytes(4, "little")
    combined_payload = magic + wasm_len + wasm_bytes + input_json

    pid = os.environ.get("TANDEM_PID")
    if not pid:
        pid = _deploy_project(server_url, api_key, config["config_path"])

    files = [
        ("toml_file", (config["config_path"].name, config["config_path"].read_bytes(), "application/toml")),
        ("manifest_file", ("manifest.json", manifest_bytes, "application/json")),
    ]
    
    for t in tasks:
        t_wasm_rel = t.get("wasm")
        if not t_wasm_rel:
            continue
        t_wasm_path = output_dir / t_wasm_rel
        if t == task_info:
            files.append(("wasm_files", (Path(t_wasm_rel).name, combined_payload, "application/wasm")))
        else:
            files.append(("wasm_files", (Path(t_wasm_rel).name, t_wasm_path.read_bytes(), "application/wasm")))

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
    results_url = start_result["results_url"]
    job_token = start_result["job_token"]
    # Poll for results
    job_token = start_result["job_token"]
    headers = {"X-API-Key": api_key, "X-Job-Token": job_token}
    job_id = start_result["job_id"]
    while True:
        status_resp = requests.get(f"{server_url}/start/{job_id}/results", headers=headers, timeout=10)
        status_resp.raise_for_status()
        summary = status_resp.json()
        
        if summary.get("done"):
            if summary.get("status") == "completed":
                # Find the result of the specific task
                for t_result in summary.get("results", []):
                    if t_result.get("task_name") == task_name.split(":")[-1]:
                        if t_result.get("status") == "completed":
                            try:
                                return json.loads(base64.b64decode(t_result.get("result_b64")).decode("utf-8"))
                            except Exception:
                                return base64.b64decode(t_result.get("result_b64")).decode("utf-8")
                        else:
                            raise RuntimeError(f"Worker failed: {t_result.get('error')}")
                raise RuntimeError(f"Task {task_name} not found in results.")
            else:
                raise RuntimeError(f"Task failed or cancelled: {summary}")
        
        import time
        time.sleep(1.0)
