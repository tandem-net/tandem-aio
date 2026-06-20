import base64
import math
import os
import time
from functools import reduce
from operator import mul

import cloudpickle
import requests

SERVER_URL = os.environ.get("TANDEM_SERVER_URL", "http://127.0.0.1:6767").rstrip("/")
APP_NAME = os.environ.get("TANDEM_APP_NAME", "prime-demo")
LIMIT = int(os.environ.get("TANDEM_LIMIT", "10000"))
NUM_CHUNKS = int(os.environ.get("TANDEM_NUM_CHUNKS", "10"))
POLL_INTERVAL_SECONDS = float(os.environ.get("TANDEM_POLL_INTERVAL", "0.5"))
RESULT_TIMEOUT_SECONDS = int(os.environ.get("TANDEM_RESULT_TIMEOUT", "300"))

CHUNK_SIZE = max(1, LIMIT // max(1, NUM_CHUNKS))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "pickles", APP_NAME)
PID_DIR = os.path.join(BASE_DIR, "temp_pid")
PID_FILE = os.path.join(PID_DIR, f"{APP_NAME}.pid")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(PID_DIR, exist_ok=True)


def calculate_prime_product_range(start, end):
    def is_prime(n):
        if n < 2:
            return False
        for i in range(2, int(math.isqrt(n)) + 1):
            if n % i == 0:
                return False
        return True

    product = 1
    actual_start = max(2, start)

    for num in range(actual_start, end):
        if is_prime(num):
            product *= num

    return product


def toml_bytes() -> bytes:
    return f'[app]\nname = "{APP_NAME}"\nlanguage = "python"\n'.encode("utf-8")


def make_task_closure(start_range, end_range):
    def task_closure():
        return calculate_prime_product_range(start_range, end_range)

    return task_closure


def generate_pickles() -> list[str]:
    pickle_paths: list[str] = []

    for i in range(NUM_CHUNKS):
        start_range = i * CHUNK_SIZE
        end_range = LIMIT if i == NUM_CHUNKS - 1 else min(LIMIT, (i + 1) * CHUNK_SIZE)
        task_closure = make_task_closure(start_range, end_range)

        pickle_filename = f"prime_chunk_{i + 1}.pkl"
        pickle_path = os.path.join(OUTPUT_DIR, pickle_filename)

        with open(pickle_path, "wb") as f:
            cloudpickle.dump(task_closure, f)

        pickle_paths.append(pickle_path)
        print(
            f"Created executable pickle: {pickle_path} for range {start_range} to {end_range}"
        )

    return pickle_paths


def ensure_deployed() -> str:
    if os.path.exists(PID_FILE):
        with open(PID_FILE, "r", encoding="utf-8") as pid_file:
            pid = pid_file.read().strip()
        if pid:
            print(f"Using existing PID {pid}")
            return pid

    resp = requests.post(
        f"{SERVER_URL}/deploy/",
        files={"toml_file": (f"{APP_NAME}.toml", toml_bytes(), "text/plain")},
        timeout=10,
    )
    resp.raise_for_status()
    payload = resp.json()

    pid = payload.get("pid")
    if not pid:
        raise RuntimeError("Server did not return a PID during deploy")

    with open(PID_FILE, "w", encoding="utf-8") as pid_file:
        pid_file.write(pid)

    print(f"Deployment ready. PID={pid}")
    return pid


def submit_job(pid: str, pickle_paths: list[str]) -> dict:
    file_objects = []
    files = []

    try:
        files.append(("toml_file", (f"{APP_NAME}.toml", toml_bytes(), "text/plain")))

        for pickle_path in pickle_paths:
            handle = open(pickle_path, "rb")
            file_objects.append(handle)
            files.append(
                (
                    "pickle_files",
                    (os.path.basename(pickle_path), handle, "application/octet-stream"),
                )
            )

        resp = requests.post(
            f"{SERVER_URL}/start/",
            data={"pid": pid},
            files=files,
            timeout=30,
        )
        resp.raise_for_status()
        payload = resp.json()
        print(
            f"Queued job {payload.get('job_id')} with {len(payload.get('task_ids', []))} task(s)"
        )
        return payload
    finally:
        for handle in file_objects:
            handle.close()


def wait_for_results(job_id: str, job_token: str) -> dict:
    headers = {"X-Job-Token": job_token}
    url = f"{SERVER_URL}/start/{job_id}/results"
    started_at = time.time()
    last_snapshot = None

    while time.time() - started_at <= RESULT_TIMEOUT_SECONDS:
        resp = requests.get(url, headers=headers, timeout=15)
        payload = resp.json()

        if resp.status_code == 200:
            return payload
        if resp.status_code != 202:
            raise RuntimeError(
                f"Unexpected status while waiting for results: {resp.status_code} {resp.text}"
            )

        snapshot = (payload.get("status"), str(payload.get("counts")))
        if snapshot != last_snapshot:
            print(
                f"Job {job_id}: status={payload.get('status')} counts={payload.get('counts')}"
            )
            last_snapshot = snapshot

        time.sleep(POLL_INTERVAL_SECONDS)

    raise TimeoutError(f"Timed out waiting for results for job {job_id}")


def decode_results(result_payload: dict) -> list[int]:
    decoded: list[int] = []
    failures = []

    for item in result_payload.get("results", []):
        if item.get("status") != "completed":
            failures.append({"tid": item.get("tid"), "error": item.get("error")})
            continue

        raw = base64.b64decode(item.get("result_b64", ""))
        decoded.append(cloudpickle.loads(raw))

    if failures:
        raise RuntimeError(f"One or more tasks failed: {failures}")

    return decoded


def combine_results(values: list[int]) -> int:
    if not values:
        return 1
    return reduce(mul, values, 1)


def main():
    pickle_paths = generate_pickles()
    pid = ensure_deployed()
    job_payload = submit_job(pid, pickle_paths)

    job_id = job_payload.get("job_id")
    job_token = job_payload.get("job_token")
    if not job_id or not job_token:
        raise RuntimeError("Server did not return job credentials")

    result_payload = wait_for_results(job_id, job_token)
    chunk_results = decode_results(result_payload)
    final_result = combine_results(chunk_results)

    print("\nChunk results:")
    for index, value in enumerate(chunk_results, start=1):
        print(f"  chunk {index}: {value}")

    print("\nFinal combined result:")
    print(final_result)


if __name__ == "__main__":
    main()
