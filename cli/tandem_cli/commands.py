from __future__ import annotations

import argparse
import base64
import json
import sys
import time
from typing import Any, Sequence

from .analysis import Diagnostic
from .app_config import write_project_config
from .build import AnalysisFailure, build_project, clean_project, inspect_project
from .manifest import build_manifest
from .remote import deploy_project, fetch_job_results, start_project


def _format_diagnostic(diagnostic: Diagnostic) -> str:
    location = f"{diagnostic.file}:{diagnostic.line}:{diagnostic.column}"
    return (
        f"[{diagnostic.level}] {diagnostic.code} task={diagnostic.task} "
        f"{location} - {diagnostic.message}"
    )


def _add_remote_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--server-url",
        default=None,
        help="Server base URL. Falls back to TANDEM_SERVER_URL or http://127.0.0.1:6767.",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="User API key. Falls back to TANDEM_API_KEY.",
    )


def _format_counts(counts: dict[str, Any]) -> str:
    ordered = ["queued", "claimed", "running", "completed", "failed"]
    parts: list[str] = []

    for key in ordered:
        if key in counts:
            parts.append(f"{key}={counts[key]}")

    for key in sorted(counts):
        if key not in ordered:
            parts.append(f"{key}={counts[key]}")

    return ", ".join(parts) if parts else "no counts yet"


def _decode_result_payload(result_b64: str) -> Any:
    raw = base64.b64decode(result_b64)
    if not raw:
        return None

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return {"binary_b64": result_b64}

    stripped = text.strip()
    if not stripped:
        return None

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return text


def _format_result_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, indent=2, sort_keys=True)
    if value is None:
        return "null"
    return str(value)


def _task_label(item: dict[str, Any]) -> str:
    label = (
        str(item.get("task_name") or "").strip()
        or str(item.get("filename") or "").strip()
        or str(item.get("tid") or "task")
    )

    shard_total = item.get("shard_total")
    shard_index = item.get("shard_index")
    if (
        isinstance(shard_total, int)
        and isinstance(shard_index, int)
        and shard_total > 1
    ):
        label = f"{label} shard {shard_index + 1}/{shard_total}"

    assigned_node = str(item.get("assigned_node") or "").strip()
    if assigned_node:
        label = f"{label} on {assigned_node}"

    return label


def _print_job_results(payload: dict[str, Any]) -> None:
    job_id = payload.get("job_id") or ""
    status = payload.get("status") or "unknown"
    print(f"Job {job_id} finished with status {status}")

    results = payload.get("results")
    if not isinstance(results, list) or not results:
        print("No task results were returned.")
        return

    for item in results:
        if not isinstance(item, dict):
            continue

        print(f"\n- {_task_label(item)}")
        if item.get("status") == "completed":
            result_b64 = item.get("result_b64")
            if isinstance(result_b64, str):
                print(_format_result_value(_decode_result_payload(result_b64)))
            else:
                print("completed, but no payload was returned")
            continue

        error_message = str(item.get("error") or "task failed")
        print(error_message)


def _report_analysis_failure(exc: AnalysisFailure) -> int:
    print(str(exc), file=sys.stderr)
    print("Diagnostics:", file=sys.stderr)
    for diagnostic in exc.report.diagnostics:
        print(f"  {_format_diagnostic(diagnostic)}", file=sys.stderr)
    return 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tandem",
        description="Discover Tandem SDK tasks, build `.wasm` artifacts, and run them through a Tandem server.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser(
        "init", help="Create a new Tandem project TOML file."
    )
    init_parser.add_argument("config_path", help="Path to the TOML config to create.")
    init_parser.add_argument("--name", required=True, help="Project name.")
    init_parser.add_argument(
        "--entry",
        required=True,
        help="Path to the Python source file containing Tandem-decorated tasks.",
    )
    init_parser.add_argument(
        "--output-dir",
        default=None,
        help="Build output directory relative to the config file.",
    )
    init_parser.add_argument("--version", default="0.1.0", help="Project version.")

    inspect_parser = subparsers.add_parser(
        "inspect", help="Load a project, discover tasks, and print analysis output."
    )
    inspect_parser.add_argument("config_path", help="Path to the Tandem TOML config.")

    manifest_parser = subparsers.add_parser(
        "manifest",
        help="Print the generated manifest JSON to stdout without writing files.",
    )
    manifest_parser.add_argument("config_path", help="Path to the Tandem TOML config.")

    build_parser = subparsers.add_parser(
        "build",
        help="Validate the project and emit `.wasm` artifacts plus `.tandem/manifest.json`.",
    )
    build_parser.add_argument("config_path", help="Path to the Tandem TOML config.")
    build_parser.add_argument(
        "--allow-analysis-errors",
        action="store_true",
        help="Write artifacts even if static validation reports errors.",
    )

    deploy_parser = subparsers.add_parser(
        "deploy",
        help="Create a deployment on the server and print its pid.",
    )
    deploy_parser.add_argument("config_path", help="Path to the Tandem TOML config.")
    _add_remote_options(deploy_parser)

    start_parser = subparsers.add_parser(
        "start",
        help="Build the project, upload its `.wasm` artifacts, and optionally wait for results.",
    )
    start_parser.add_argument("config_path", help="Path to the Tandem TOML config.")
    start_parser.add_argument(
        "--pid",
        default=None,
        help="Existing deployment pid. If omitted, Tandem creates one first.",
    )
    start_parser.add_argument(
        "--allow-analysis-errors",
        action="store_true",
        help="Upload artifacts even if static validation reports errors.",
    )
    start_parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Queue the job and return immediately instead of polling for results.",
    )
    start_parser.add_argument(
        "--poll-interval",
        type=float,
        default=0.5,
        help="Seconds between result polls while waiting.",
    )
    _add_remote_options(start_parser)

    clean_parser = subparsers.add_parser(
        "clean", help="Remove generated build artifacts."
    )
    clean_parser.add_argument("config_path", help="Path to the Tandem TOML config.")

    return parser


def _cmd_init(args: argparse.Namespace) -> int:
    path = write_project_config(
        args.config_path,
        name=args.name,
        entry=args.entry,
        output_dir=args.output_dir,
        version=args.version,
    )
    print(f"Created Tandem project config at {path}")
    return 0


def _cmd_inspect(args: argparse.Namespace) -> int:
    config, discovered, report = inspect_project(args.config_path)
    sdk_info = discovered.sdk_descriptor.sdk
    print(f"Project: {config.name}")
    print(f"Runtime: {config.runtime}")
    print(f"Entry:   {config.entry_path}")
    print(f"Output:  {config.output_dir}")
    print(
        f"SDK:     {sdk_info.package} language={sdk_info.language} "
        f"protocol={sdk_info.protocol_version}"
    )
    print(f"Tasks:   {len(discovered.tasks)}")

    for export_name, task in sorted(discovered.tasks.items()):
        metadata = task.metadata
        print(
            f"  - {export_name}: annotation={metadata.annotation} "
            f"canonical={metadata.canonical_annotation} "
            f"execution_class={metadata.execution_class}"
        )

    if report.diagnostics:
        print("\nDiagnostics:")
        for diagnostic in report.diagnostics:
            print(f"  {_format_diagnostic(diagnostic)}")
    else:
        print("\nDiagnostics: none")

    return 1 if report.has_errors else 0


def _cmd_manifest(args: argparse.Namespace) -> int:
    config, discovered, _ = inspect_project(args.config_path)
    manifest = build_manifest(config, discovered)
    json.dump(manifest, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


def _cmd_build(args: argparse.Namespace) -> int:
    try:
        result = build_project(
            args.config_path,
            strict=not args.allow_analysis_errors,
        )
    except AnalysisFailure as exc:
        return _report_analysis_failure(exc)

    print(f"Built {result.task_count} task(s) into {result.output_dir}")
    print(f"Manifest:   {result.manifest_path}")
    print(f"Analysis:   {result.analysis_path}")
    print(f"SDK bridge: {result.sdk_bridge_path}")
    print("WASM artifacts:")
    for path in result.wasm_paths:
        print(f"  - {path}")

    if result.diagnostics:
        print("\nDiagnostics:")
        for diagnostic in result.diagnostics:
            print(f"  {_format_diagnostic(diagnostic)}")

    return 0


def _cmd_deploy(args: argparse.Namespace) -> int:
    result = deploy_project(
        args.config_path,
        server_url=args.server_url,
        api_key=args.api_key,
    )
    print(f"Deployment name: {result.name}")
    print(f"PID: {result.pid}")
    return 0


def _cmd_start(args: argparse.Namespace) -> int:
    try:
        result = start_project(
            args.config_path,
            server_url=args.server_url,
            api_key=args.api_key,
            pid=args.pid,
            strict=not args.allow_analysis_errors,
        )
    except AnalysisFailure as exc:
        return _report_analysis_failure(exc)

    print(f"Built artifacts into {result.output_dir}")
    print(f"Deployment pid: {result.pid}")
    print(f"Queued job: {result.job_id}")
    print(f"Initial counts: {_format_counts(result.counts)}")

    if args.no_wait:
        print(f"Job token:   {result.job_token}")
        print(f"Status URL:  {result.status_url}")
        print(f"Results URL: {result.results_url}")
        return 0

    print("Waiting for results...")
    last_counts: dict[str, Any] | None = result.counts
    poll_interval = max(args.poll_interval, 0.1)

    while True:
        status_code, payload = fetch_job_results(result, api_key=args.api_key)
        raw_counts = payload.get("counts")
        counts: dict[str, Any] = raw_counts if isinstance(raw_counts, dict) else {}

        if counts != last_counts:
            print(f"Counts: {_format_counts(counts)}")
            last_counts = counts

        if status_code == 200:
            _print_job_results(payload)
            return 0 if payload.get("status") == "completed" else 1

        time.sleep(poll_interval)


def _cmd_clean(args: argparse.Namespace) -> int:
    output_dir = clean_project(args.config_path)
    print(f"Removed build directory {output_dir}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "init":
            return _cmd_init(args)
        if args.command == "inspect":
            return _cmd_inspect(args)
        if args.command == "manifest":
            return _cmd_manifest(args)
        if args.command == "build":
            return _cmd_build(args)
        if args.command == "deploy":
            return _cmd_deploy(args)
        if args.command == "start":
            return _cmd_start(args)
        if args.command == "clean":
            return _cmd_clean(args)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    parser.error(f"Unknown command: {args.command}")
    return 2
