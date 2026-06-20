from __future__ import annotations

import base64
import json
import pathlib
import secrets
import time
from typing import Any

from app.extensions import redis_client
from flask import current_app

NODE_STALE_SECONDS = 5.0
TASK_LEASE_SECONDS = 30.0


def decode_value(value: Any) -> Any:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value


def decode_mapping(raw: dict[Any, Any] | None) -> dict[str, str]:
    if not raw:
        return {}

    decoded: dict[str, str] = {}
    for key, value in raw.items():
        decoded[str(decode_value(key))] = str(decode_value(value))
    return decoded


def decode_list(values: list[Any] | None) -> list[str]:
    if not values:
        return []
    return [str(decode_value(value)) for value in values]


def now_ts() -> str:
    return str(time.time())


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def compare_token(expected: str | None, provided: str | None) -> bool:
    if not expected or not provided:
        return False
    return secrets.compare_digest(expected, provided)


def storage_root() -> pathlib.Path:
    configured = current_app.config.get("TASK_STORAGE_ROOT")
    if configured:
        root = pathlib.Path(configured)
    else:
        root = pathlib.Path(current_app.root_path).resolve().parent / "runtime"

    root.mkdir(parents=True, exist_ok=True)
    return root


def task_blob_path(job_id: str, tid: str) -> pathlib.Path:
    path = storage_root() / "tasks" / job_id / f"{tid}.pkl"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def result_blob_path(job_id: str, tid: str) -> pathlib.Path:
    path = storage_root() / "results" / job_id / f"{tid}.bin"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write_bytes(path: pathlib.Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def read_bytes(path_string: str | None) -> bytes | None:
    if not path_string:
        return None

    path = pathlib.Path(path_string)
    if not path.exists():
        return None

    return path.read_bytes()


def remove_file(path_string: str | None) -> None:
    if not path_string:
        return

    path = pathlib.Path(path_string)
    try:
        if path.exists():
            path.unlink()
    except OSError:
        pass


def generate_job_id() -> str:
    return f"job_{secrets.token_hex(12)}"


def generate_tid() -> str:
    return f"tid_{secrets.token_hex(12)}"


def generate_token() -> str:
    return secrets.token_urlsafe(24)


def get_job(job_id: str) -> dict[str, str]:
    job = decode_mapping(redis_client.hgetall(f"job:{job_id}"))
    if job:
        job["job_id"] = job_id
    return job


def get_task(tid: str) -> dict[str, str]:
    task = decode_mapping(redis_client.hgetall(f"task:{tid}"))
    if task:
        task["tid"] = tid
    return task


def get_job_task_ids(job_id: str) -> list[str]:
    return decode_list(redis_client.lrange(f"job:{job_id}:tasks", 0, -1))


def get_all_node_ids() -> list[str]:
    return sorted(decode_list(list(redis_client.smembers("nodes") or [])))


def get_node(node_id: str) -> dict[str, str]:
    node = decode_mapping(redis_client.hgetall(f"node:{node_id}"))
    if node:
        node["node_id"] = node_id
    return node


def is_node_healthy(node: dict[str, str] | None, *, now: float | None = None) -> bool:
    if not node:
        return False

    if now is None:
        now = time.time()

    last_seen = safe_float(node.get("last_seen"))
    if last_seen <= 0:
        return False

    return (now - last_seen) <= NODE_STALE_SECONDS


def get_healthy_node_ids(*, exclude: str | None = None) -> list[str]:
    current = time.time()
    healthy: list[str] = []

    for node_id in get_all_node_ids():
        if exclude and node_id == exclude:
            continue

        node = get_node(node_id)
        if is_node_healthy(node, now=current):
            healthy.append(node_id)

    return healthy


def create_job(
    pid: str, name: str, metadata: dict[str, Any], total_tasks: int
) -> dict[str, str]:
    job_id = generate_job_id()
    job_token = generate_token()
    timestamp = now_ts()

    redis_client.hset(
        f"job:{job_id}",
        mapping={
            "job_id": job_id,
            "job_token": job_token,
            "pid": pid,
            "name": name or "",
            "status": "queued",
            "total_tasks": str(total_tasks),
            "created_at": timestamp,
            "updated_at": timestamp,
            "metadata_json": json.dumps(metadata or {}, default=str),
        },
    )

    return {
        "job_id": job_id,
        "job_token": job_token,
    }


def create_task(
    *,
    job_id: str,
    pid: str,
    name: str,
    filename: str,
    payload: bytes,
    assigned_node: str | None,
) -> str:
    tid = generate_tid()
    timestamp = now_ts()
    blob_path = task_blob_path(job_id, tid)
    write_bytes(blob_path, payload)

    redis_client.hset(
        f"task:{tid}",
        mapping={
            "tid": tid,
            "job_id": job_id,
            "pid": pid,
            "name": name or "",
            "filename": filename,
            "status": "queued",
            "assigned_node": assigned_node or "",
            "blob_path": str(blob_path),
            "result_path": "",
            "error": "",
            "claim_token": "",
            "download_token": "",
            "created_at": timestamp,
            "updated_at": timestamp,
            "claimed_at": "",
            "completed_at": "",
            "lease_expires_at": "",
        },
    )

    redis_client.rpush(f"job:{job_id}:tasks", tid)

    if assigned_node:
        redis_client.rpush(f"node:{assigned_node}:queue", tid)
    else:
        redis_client.rpush("tasks:unassigned", tid)

    return tid


def requeue_task(tid: str, assigned_node: str | None) -> None:
    task = get_task(tid)
    if not task:
        return

    timestamp = now_ts()
    redis_client.hset(
        f"task:{tid}",
        mapping={
            "status": "queued",
            "assigned_node": assigned_node or "",
            "claim_token": "",
            "download_token": "",
            "lease_expires_at": "",
            "updated_at": timestamp,
        },
    )

    if assigned_node:
        redis_client.rpush(f"node:{assigned_node}:queue", tid)
    else:
        redis_client.rpush("tasks:unassigned", tid)


def requeue_stale_tasks() -> None:
    current = time.time()

    for node_id in get_all_node_ids():
        node = get_node(node_id)
        if not node or is_node_healthy(node, now=current):
            continue

        current_tid = (node.get("current_task") or "").strip()
        if not current_tid:
            continue

        task = get_task(current_tid)
        if not task:
            redis_client.hset(f"node:{node_id}", mapping={"current_task": ""})
            continue

        if task.get("status") not in {"claimed", "running"}:
            redis_client.hset(f"node:{node_id}", mapping={"current_task": ""})
            continue

        healthy_destinations = get_healthy_node_ids(exclude=node_id)
        destination = healthy_destinations[0] if healthy_destinations else None

        requeue_task(current_tid, destination)
        redis_client.hset(f"node:{node_id}", mapping={"current_task": ""})


def get_available_nodes() -> list[str]:
    requeue_stale_tasks()
    return get_healthy_node_ids()


def claim_task_for_node(node_id: str) -> dict[str, str] | None:
    requeue_stale_tasks()

    node = get_node(node_id)
    if not node:
        return None

    current_tid = (node.get("current_task") or "").strip()
    if current_tid:
        existing_task = get_task(current_tid)
        if existing_task and existing_task.get("status") in {"claimed", "running"}:
            return existing_task
        redis_client.hset(f"node:{node_id}", mapping={"current_task": ""})

    claimed_tid = redis_client.lpop(f"node:{node_id}:queue")
    if claimed_tid is None:
        claimed_tid = redis_client.lpop("tasks:unassigned")

    if claimed_tid is None:
        return None

    tid = str(decode_value(claimed_tid))
    task = get_task(tid)
    if not task:
        return None

    claim_token = generate_token()
    download_token = generate_token()
    current = time.time()
    timestamp = str(current)

    redis_client.hset(
        f"task:{tid}",
        mapping={
            "status": "claimed",
            "assigned_node": node_id,
            "claim_token": claim_token,
            "download_token": download_token,
            "claimed_at": timestamp,
            "lease_expires_at": str(current + TASK_LEASE_SECONDS),
            "updated_at": timestamp,
        },
    )

    redis_client.hset(
        f"node:{node_id}",
        mapping={
            "current_task": tid,
            "last_seen": timestamp,
        },
    )

    task = get_task(tid)
    task["claim_token"] = claim_token
    task["download_token"] = download_token
    return task


def extend_task_lease(node_id: str) -> None:
    node = get_node(node_id)
    if not node:
        return

    current_tid = (node.get("current_task") or "").strip()
    if not current_tid:
        return

    task = get_task(current_tid)
    if not task or task.get("status") not in {"claimed", "running"}:
        return

    current = time.time()
    redis_client.hset(
        f"task:{current_tid}",
        mapping={
            "lease_expires_at": str(current + TASK_LEASE_SECONDS),
            "updated_at": str(current),
        },
    )


def complete_task(tid: str, node_id: str, *, result_bytes: bytes) -> dict[str, Any]:
    task = get_task(tid)
    if not task:
        raise KeyError(f"Unknown task id: {tid}")

    result_path = result_blob_path(task["job_id"], tid)
    write_bytes(result_path, result_bytes)

    timestamp = now_ts()
    redis_client.hset(
        f"task:{tid}",
        mapping={
            "status": "completed",
            "result_path": str(result_path),
            "error": "",
            "claim_token": "",
            "download_token": "",
            "lease_expires_at": "",
            "completed_at": timestamp,
            "updated_at": timestamp,
        },
    )
    redis_client.hset(
        f"node:{node_id}", mapping={"current_task": "", "last_seen": timestamp}
    )

    remove_file(task.get("blob_path"))
    return refresh_job_status(task["job_id"])


def fail_task(tid: str, node_id: str, *, error_message: str) -> dict[str, Any]:
    task = get_task(tid)
    if not task:
        raise KeyError(f"Unknown task id: {tid}")

    timestamp = now_ts()
    redis_client.hset(
        f"task:{tid}",
        mapping={
            "status": "failed",
            "error": error_message,
            "claim_token": "",
            "download_token": "",
            "lease_expires_at": "",
            "completed_at": timestamp,
            "updated_at": timestamp,
        },
    )
    redis_client.hset(
        f"node:{node_id}", mapping={"current_task": "", "last_seen": timestamp}
    )

    remove_file(task.get("blob_path"))
    return refresh_job_status(task["job_id"])


def refresh_job_status(job_id: str) -> dict[str, Any]:
    task_ids = get_job_task_ids(job_id)
    counts = {
        "queued": 0,
        "claimed": 0,
        "running": 0,
        "completed": 0,
        "failed": 0,
    }
    tasks: list[dict[str, Any]] = []

    for tid in task_ids:
        task = get_task(tid)
        if not task:
            continue

        status = task.get("status") or "queued"
        if status not in counts:
            counts[status] = 0
        counts[status] += 1

        tasks.append(
            {
                "tid": tid,
                "filename": task.get("filename") or "",
                "status": status,
                "assigned_node": task.get("assigned_node") or "",
                "error": task.get("error") or None,
                "created_at": task.get("created_at") or "",
                "claimed_at": task.get("claimed_at") or "",
                "completed_at": task.get("completed_at") or "",
            }
        )

    total_tasks = len(task_ids)
    done = total_tasks > 0 and (counts["completed"] + counts["failed"] == total_tasks)

    if done and counts["failed"]:
        overall_status = "failed"
    elif done:
        overall_status = "completed"
    elif counts["running"] or counts["claimed"]:
        overall_status = "running"
    else:
        overall_status = "queued"

    redis_client.hset(
        f"job:{job_id}",
        mapping={
            "status": overall_status,
            "updated_at": now_ts(),
        },
    )

    return {
        "job_id": job_id,
        "status": overall_status,
        "done": done,
        "total_tasks": total_tasks,
        "counts": counts,
        "tasks": tasks,
    }


def get_job_results(job_id: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    for tid in get_job_task_ids(job_id):
        task = get_task(tid)
        if not task:
            continue

        item: dict[str, Any] = {
            "tid": tid,
            "filename": task.get("filename") or "",
            "status": task.get("status") or "queued",
            "assigned_node": task.get("assigned_node") or "",
        }

        if item["status"] == "completed":
            result_bytes = read_bytes(task.get("result_path")) or b""
            item["result_b64"] = base64.b64encode(result_bytes).decode("ascii")
        elif task.get("error"):
            item["error"] = task.get("error")

        results.append(item)

    return results
