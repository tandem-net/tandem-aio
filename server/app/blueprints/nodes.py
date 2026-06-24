from __future__ import annotations

import os
import secrets
import shutil
import time
import uuid

from app.extensions import redis_client, generate_api_key
from app.utils.task_queue import (
    TASK_LEASE_SECONDS,
    claim_task_for_node,
    compare_token,
    complete_task,
    extend_task_lease,
    fail_task,
    get_node,
    get_task,
)
from flask import Blueprint, Response, jsonify, request, send_file

nodes_bp = Blueprint("nodes", __name__)

# 300MB
STREAM_SIZE_BYTES = 300 * 1024 * 1024
DUMMY_DATA = os.urandom(STREAM_SIZE_BYTES)


# NODE ID SLOP

def _extract_node_id() -> str:
    header_node_id = (request.headers.get("X-Node-Id") or "").strip()
    if header_node_id:
        return header_node_id

    if request.is_json:
        data = request.get_json(silent=True) or {}
        return (data.get("node_id") or "").strip()

    return ""


def _require_node_auth():
    node_id = _extract_node_id()
    if not node_id:
        return None, None, (jsonify({"error": "Missing node_id"}), 400)

    auth_header = request.headers.get("Authorization") or ""
    if not auth_header.startswith("Bearer "):
        return None, None, (jsonify({"error": "Missing bearer token"}), 401)

    token = auth_header.split(" ", 1)[1].strip()
    node = get_node(node_id)
    if not node:
        return None, None, (jsonify({"error": "Unknown node_id"}), 404)

    if not compare_token(node.get("node_token"), token):
        return None, None, (jsonify({"error": "Invalid node token"}), 403)

    return node_id, node, None


# ROUTE SLOP

@nodes_bp.route("/download", methods=["GET"])
def download():
    return Response(
        DUMMY_DATA,
        mimetype="application/octet-stream",
        headers={"Content-Length": str(STREAM_SIZE_BYTES)},
    )


@nodes_bp.route("/upload", methods=["POST"])
def upload():
    start_time = time.time()

    with open(os.devnull, "wb") as sink:
        shutil.copyfileobj(request.stream, sink)

    duration = time.time() - start_time
    return jsonify({"duration": duration})


@nodes_bp.route("/ping", methods=["POST"])
def ping():
    node_id, _node, error = _require_node_auth()
    if error:
        return error

    data = request.get_json(silent=True) or {}
    timestamp = str(time.time())
    metrics = {"last_seen": timestamp}

    for field in ("latency", "download", "upload"):
        value = data.get(field)
        if value is not None:
            metrics[field] = str(value)

    redis_client.hset(f"node:{node_id}", mapping=metrics)
    redis_client.sadd("nodes", node_id)

    return jsonify({"status": "Metrics recorded"}), 200


@nodes_bp.route("/health", methods=["POST"])
def health():
    node_id, _node, error = _require_node_auth()
    if error:
        return error
    assert node_id is not None

    data = request.get_json(silent=True) or {}
    timestamp = str(time.time())
    mapping = {"last_seen": timestamp}

    for field in ("latency", "download", "upload"):
        value = data.get(field)
        if value is not None:
            mapping[field] = str(value)

    redis_client.hset(f"node:{node_id}", mapping=mapping)
    redis_client.sadd("nodes", node_id)
    extend_task_lease(node_id)

    return jsonify({"status": "Alive"}), 200


@nodes_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    node_id = f"node_{uuid.uuid4().hex[:12]}"
    node_token = secrets.token_urlsafe(32)
    timestamp = str(time.time())

    metrics = {
        "node_token": node_token,
        "last_seen": timestamp,
        "registered_at": timestamp,
        "current_task": "",
    }

    for field in ("latency", "download", "upload"):
        value = data.get(field)
        if value is not None:
            metrics[field] = str(value)

    redis_client.hset(f"node:{node_id}", mapping=metrics)
    redis_client.sadd("nodes", node_id)

    return (
        jsonify(
            {
                "status": "Registered",
                "node_id": node_id,
                "node_token": node_token,
            }
        ),
        201,
    )


@nodes_bp.route("/tasks/claim", methods=["POST"])
def claim_task():
    node_id, _node, error = _require_node_auth()
    if error:
        return error
    assert node_id is not None

    task = claim_task_for_node(node_id)
    if not task:
        return ("", 204)

    tid = task.get("tid") or ""
    download_token = task.get("download_token") or ""
    base_url = request.host_url.rstrip("/")

    return jsonify(
        {
            "tid": tid,
            "job_id": task.get("job_id") or "",
            "filename": task.get("filename") or "",
            "claim_token": task.get("claim_token") or "",
            "download_url": f"{base_url}/nodes/tasks/{tid}/download/{download_token}",
        }
    )


@nodes_bp.route("/tasks/<tid>/download/<download_token>", methods=["GET"])
def download_task_blob(tid: str, download_token: str):
    node_id, _node, error = _require_node_auth()
    if error:
        return error

    task = get_task(tid)
    if not task:
        return jsonify({"error": "Unknown task id"}), 404

    if task.get("assigned_node") != node_id:
        return jsonify({"error": "Task is assigned to another node"}), 403

    if not compare_token(task.get("download_token"), download_token):
        return jsonify({"error": "Invalid download token"}), 403

    blob_path = task.get("blob_path")
    if not blob_path or not os.path.exists(blob_path):
        return jsonify({"error": "Task payload is missing"}), 404

    timestamp = str(time.time())
    redis_client.hset(
        f"task:{tid}",
        mapping={
            "status": "running",
            "updated_at": timestamp,
            "lease_expires_at": str(time.time() + TASK_LEASE_SECONDS),
        },
    )

    return send_file(
        blob_path,
        mimetype="application/octet-stream",
        as_attachment=True,
        download_name=task.get("filename") or f"{tid}.pkl",
    )


@nodes_bp.route("/tasks/<tid>/result", methods=["POST"])
def submit_task_result(tid: str):
    node_id, _node, error = _require_node_auth()
    if error:
        return error
    assert node_id is not None

    task = get_task(tid)
    if not task:
        return jsonify({"error": "Unknown task id"}), 404

    if task.get("assigned_node") != node_id:
        return jsonify({"error": "Task is assigned to another node"}), 403

    claim_token = (request.headers.get("X-Task-Claim") or "").strip()
    if not compare_token(task.get("claim_token"), claim_token):
        return jsonify({"error": "Invalid claim token"}), 403

    if request.mimetype == "application/octet-stream":
        result_bytes = request.get_data()
        if not result_bytes:
            return jsonify({"error": "Missing result payload"}), 400

        summary = complete_task(tid, node_id, result_bytes=result_bytes)
        return jsonify(
            {
                "status": "completed",
                "job_status": summary["status"],
                "counts": summary["counts"],
            }
        ), 200

    data = request.get_json(silent=True) or {}
    error_message = (data.get("error") or "Task execution failed").strip()
    summary = fail_task(tid, node_id, error_message=error_message)

    return jsonify(
        {
            "status": "failed",
            "job_status": summary["status"],
            "counts": summary["counts"],
        }
    ), 200

if __name__ == '__main__':
    api_key = generate_api_key()
    print(api_key)