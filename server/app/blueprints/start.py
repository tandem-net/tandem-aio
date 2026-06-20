"""
Start a deployed Tandem app.

This blueprint accepts uploaded cloudpickle tasks from the CLI, stores them
under task IDs (TIDs), assigns them to healthy nodes in a round-robin pattern,
and exposes secure job status/result endpoints for the CLI.
"""

from __future__ import annotations

import json
from itertools import cycle

from app.extensions import redis_client
from app.models import Deployment
from app.utils.task_queue import (
    compare_token,
    create_job,
    create_task,
    get_available_nodes,
    get_job,
    get_job_results,
    refresh_job_status,
)
from app.utils.toml_reader import extract_name, get_relevant, parse_toml_string
from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

start_bp = Blueprint("start", __name__)


def _require_job_token(job_id: str):
    job = get_job(job_id)
    if not job:
        return None, (jsonify({"error": "Unknown job id"}), 404)

    provided = request.headers.get("X-Job-Token") or request.args.get("token")
    if not compare_token(job.get("job_token"), provided):
        return None, (jsonify({"error": "Invalid or missing job token"}), 403)

    return job, None


@start_bp.route("/", methods=["POST"])
def start():
    """
    Queue one job made up of one or more cloudpickle tasks.

    Required multipart form-data fields:
    - toml_file: deployment config
    - pickle_files: one or more cloudpickle files
    - pid: deployment PID previously issued by /deploy/
    """

    if "toml_file" not in request.files:
        return jsonify({"error": "Missing TOML config file"}), 400

    pid = (request.form.get("pid") or "").strip()
    if not pid:
        return jsonify({"error": "Missing deployment pid"}), 400

    deployment = Deployment.query.filter_by(pid=pid).first()
    if not deployment:
        return jsonify({"error": "Unknown deployment pid"}), 404

    toml_file = request.files["toml_file"]
    toml_bytes = toml_file.read()
    parsed = parse_toml_string(toml_bytes)
    name = extract_name(parsed) or deployment.name
    relevant = get_relevant(parsed)

    if deployment.name and name and deployment.name != name:
        return jsonify(
            {
                "error": "Deployment PID does not match uploaded app config",
                "expected_name": deployment.name,
                "received_name": name,
            }
        ), 400

    pickle_files = request.files.getlist("pickle_files")
    if not pickle_files:
        return jsonify({"error": "No cloudpickle files provided"}), 400

    available_nodes = get_available_nodes()
    if not available_nodes:
        return jsonify({"error": "No healthy nodes found in Redis"}), 503

    job_info = create_job(
        pid=pid, name=name, metadata=relevant, total_tasks=len(pickle_files)
    )
    job_id = job_info["job_id"]
    job_token = job_info["job_token"]
    node_pool = cycle(available_nodes)
    task_ids: list[dict[str, str]] = []

    for pickle_file in pickle_files:
        filename = secure_filename(pickle_file.filename or "") or "task.pkl"
        payload = pickle_file.read()
        if not payload:
            continue

        assigned_node = next(node_pool)
        tid = create_task(
            job_id=job_id,
            pid=pid,
            name=name,
            filename=filename,
            payload=payload,
            assigned_node=assigned_node,
        )
        task_ids.append(
            {"tid": tid, "assigned_node": assigned_node, "filename": filename}
        )

    if not task_ids:
        redis_client.delete(f"job:{job_id}", f"job:{job_id}:tasks")
        return jsonify({"error": "No non-empty cloudpickle files were uploaded"}), 400

    summary = refresh_job_status(job_id)
    base_url = request.host_url.rstrip("/")

    return (
        jsonify(
            {
                "message": "Tasks queued successfully",
                "pid": pid,
                "job_id": job_id,
                "job_token": job_token,
                "name": name,
                "task_ids": task_ids,
                "counts": summary["counts"],
                "status": summary["status"],
                "status_url": f"{base_url}/start/{job_id}",
                "results_url": f"{base_url}/start/{job_id}/results",
            }
        ),
        202,
    )


@start_bp.route("/<job_id>", methods=["GET"])
def job_status(job_id: str):
    job, error = _require_job_token(job_id)
    if error:
        return error
    assert job is not None

    summary = refresh_job_status(job_id)
    metadata_json = job.get("metadata_json") or "{}"
    try:
        metadata = json.loads(metadata_json)
    except json.JSONDecodeError:
        metadata = {}

    return jsonify(
        {
            "job_id": job_id,
            "pid": job.get("pid") or "",
            "name": job.get("name") or "",
            "status": summary["status"],
            "done": summary["done"],
            "counts": summary["counts"],
            "tasks": summary["tasks"],
            "metadata": metadata,
            "created_at": job.get("created_at") or "",
            "updated_at": job.get("updated_at") or "",
        }
    )


@start_bp.route("/<job_id>/results", methods=["GET"])
def job_results(job_id: str):
    job, error = _require_job_token(job_id)
    if error:
        return error
    assert job is not None

    summary = refresh_job_status(job_id)
    if not summary["done"]:
        return (
            jsonify(
                {
                    "job_id": job_id,
                    "pid": job.get("pid") or "",
                    "status": summary["status"],
                    "done": False,
                    "counts": summary["counts"],
                    "tasks": summary["tasks"],
                }
            ),
            202,
        )

    return jsonify(
        {
            "job_id": job_id,
            "pid": job.get("pid") or "",
            "name": job.get("name") or "",
            "status": summary["status"],
            "done": True,
            "counts": summary["counts"],
            "results": get_job_results(job_id),
        }
    )
