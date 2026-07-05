from __future__ import annotations

import argparse
import base64
import json
import sys
import time
from pathlib import Path
from typing import Any, Sequence

import os

from dotenv import find_dotenv, load_dotenv

from .analysis import Diagnostic
from .app_config import load_project_config, write_project_config
from .auth import (
    login_user,
    mask_secret,
    prompt_password,
    prompt_username,
    register_user,
    store_auth_session,
)
from .build import AnalysisFailure, build_project, clean_project, inspect_project
from .manifest import build_manifest
from .remote import deploy_project, fetch_job_results, start_project

# --- ANSI Color Constants ---
class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    RED = "\033[91m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


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
        help="User API key. Falls back to TANDEM_API_KEY loaded from the environment or a local .env file.",
    )


def _add_auth_options(
    parser: argparse.ArgumentParser, *, include_rotate: bool = False
) -> None:
    parser.add_argument(
        "--server-url",
        default=None,
        help="Server base URL. Falls back to TANDEM_SERVER_URL or http://127.0.0.1:6767.",
    )
    parser.add_argument(
        "--username",
        default=None,
        help="Username for the Tandem account. Prompts interactively when omitted.",
    )
    parser.add_argument(
        "--password",
        default=None,
        help="Password for the Tandem account. Prefer omitting this flag so the CLI can prompt securely.",
    )
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Path to the env file where TANDEM_SERVER_URL and TANDEM_API_KEY should be stored. Defaults to .env in the current directory.",
    )
    parser.add_argument(
        "--no-store",
        action="store_true",
        help="Do not persist TANDEM_SERVER_URL or TANDEM_API_KEY to an env file.",
    )
    parser.add_argument(
        "--show-api-key",
        action="store_true",
        help="Print the full API key to stdout. By default the CLI only shows a masked value when it also stores the key in an env file.",
    )
    if include_rotate:
        parser.add_argument(
            "--rotate-api-key",
            action="store_true",
            help="Rotate any existing API key for this user before saving the authenticated session.",
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


_DEFAULT_INIT_CONFIG_PATH = "tandem.toml"
_DEFAULT_INIT_ENTRY = "tasks.py"
_DEFAULT_INIT_VERSION = "0.1.0"


def _default_init_project_name() -> str:
    current_dir = Path.cwd().name.strip()
    return current_dir or "tandem-project"


def _default_init_output_dir(project_name: str) -> str:
    return f".tandem_build/{project_name}"


def _prompt_init_value(*, label: str, description: str, default: str) -> str:
    print(f"\n{label}")
    print(f"  {description}")
    print(f"  Press Enter to accept the default: {default}")

    try:
        value = input("> ").strip()
    except EOFError as exc:  # pragma: no cover - depends on terminal state.
        raise ValueError(
            "Interactive init could not read input. Re-run in a terminal or pass values explicitly."
        ) from exc

    return value or default


def _resolve_init_values(
    args: argparse.Namespace,
) -> tuple[str, str, str, str | None, str]:
    version = args.version or _DEFAULT_INIT_VERSION

    if args.config_path and args.name and args.entry:
        return (
            args.config_path,
            args.name,
            args.entry,
            args.output_dir,
            version,
        )

    print("Create a new Tandem project config.")
    print("We'll ask a few quick questions. Defaults are shown for optional values.")

    config_path = args.config_path or _prompt_init_value(
        label="Config path",
        description="Where should Tandem write the project TOML file?",
        default=_DEFAULT_INIT_CONFIG_PATH,
    )

    project_name = args.name or _prompt_init_value(
        label="Project name",
        description="Used for the project metadata and the default build output folder.",
        default=_default_init_project_name(),
    )

    entry = args.entry or _prompt_init_value(
        label="Python entry file",
        description="Path to the Python file containing your Tandem-decorated tasks.",
        default=_DEFAULT_INIT_ENTRY,
    )

    resolved_version = args.version or _prompt_init_value(
        label="Project version",
        description="Semantic version written into the project config.",
        default=version,
    )

    output_dir = args.output_dir or _prompt_init_value(
        label="Build output directory",
        description="Directory for generated build artifacts.",
        default=_default_init_output_dir(project_name),
    )

    return config_path, project_name, entry, output_dir, resolved_version


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tandem",
        description="Discover Tandem SDK tasks, build `.wasm` artifacts, and run them through a Tandem server.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser(
        "init", help="Create a new Tandem project TOML file."
    )
    init_parser.add_argument(
        "config_path",
        nargs="?",
        default=None,
        help="Path to the TOML config to create. Prompts interactively when omitted.",
    )
    init_parser.add_argument(
        "--name",
        default=None,
        help="Project name. Defaults to the current directory name during interactive init.",
    )
    init_parser.add_argument(
        "--entry",
        default=None,
        help="Path to the Python source file containing Tandem-decorated tasks. Defaults to `tasks.py` during interactive init.",
    )
    init_parser.add_argument(
        "--output-dir",
        default=None,
        help="Build output directory relative to the config file. Defaults to `.tandem_build/<project-name>`.",
    )
    init_parser.add_argument(
        "--version",
        default=None,
        help="Project version. Defaults to `0.1.0`.",
    )

    inspect_parser = subparsers.add_parser(
        "inspect", help="Load a project, discover tasks, and print analysis output."
    )
    inspect_parser.add_argument(
        "config_path",
        nargs="?",
        default=os.environ.get("TANDEM_CONFIG_PATH", "tandem.toml"),
        help="Path to the Tandem TOML config. Defaults to tandem.toml.",
    )

    manifest_parser = subparsers.add_parser(
        "manifest",
        help="Print the generated manifest JSON to stdout without writing files.",
    )
    manifest_parser.add_argument(
        "config_path",
        nargs="?",
        default=os.environ.get("TANDEM_CONFIG_PATH", "tandem.toml"),
        help="Path to the Tandem TOML config. Defaults to tandem.toml.",
    )

    build_parser = subparsers.add_parser(
        "build",
        help="Validate the project and emit `.wasm` artifacts plus `.tandem/manifest.json`.",
    )
    build_parser.add_argument(
        "config_path",
        nargs="?",
        default=os.environ.get("TANDEM_CONFIG_PATH", "tandem.toml"),
        help="Path to the Tandem TOML config. Defaults to tandem.toml.",
    )
    build_parser.add_argument(
        "--allow-analysis-errors",
        action="store_true",
        help="Write artifacts even if static validation reports errors.",
    )

    auth_parser = subparsers.add_parser(
        "auth",
        help="Register or authenticate a user and store Tandem credentials in a local env file.",
    )
    auth_subparsers = auth_parser.add_subparsers(dest="auth_command", required=True)

    auth_register_parser = auth_subparsers.add_parser(
        "register",
        help="Create a Tandem user, obtain an API key, and optionally store it in a local env file.",
    )
    _add_auth_options(auth_register_parser)

    auth_login_parser = auth_subparsers.add_parser(
        "login",
        help="Authenticate an existing Tandem user, obtain an API key, and optionally store it in a local env file.",
    )
    _add_auth_options(auth_login_parser, include_rotate=True)

    deploy_parser = subparsers.add_parser(
        "deploy",
        help="Create a deployment on the server and print its pid.",
    )
    deploy_parser.add_argument(
        "config_path",
        nargs="?",
        default=os.environ.get("TANDEM_CONFIG_PATH", "tandem.toml"),
        help="Path to the Tandem TOML config. Defaults to tandem.toml.",
    )
    _add_remote_options(deploy_parser)

    start_parser = subparsers.add_parser(
        "start",
        help="Build the project, upload its `.wasm` artifacts, and optionally wait for results.",
    )
    start_parser.add_argument(
        "config_path",
        nargs="?",
        default=os.environ.get("TANDEM_CONFIG_PATH", "tandem.toml"),
        help="Path to the Tandem TOML config. Defaults to tandem.toml.",
    )
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
    clean_parser.add_argument(
        "config_path",
        nargs="?",
        default=os.environ.get("TANDEM_CONFIG_PATH", "tandem.toml"),
        help="Path to the Tandem TOML config. Defaults to tandem.toml.",
    )

    return parser


def _cmd_init(args: argparse.Namespace) -> int:
    config_path, name, entry, output_dir, version = _resolve_init_values(args)
    path = write_project_config(
        config_path,
        name=name,
        entry=entry,
        output_dir=output_dir,
        version=version,
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

    print(f"{Colors.GREEN}{Colors.BOLD}Built {result.task_count} task(s) into {result.output_dir}{Colors.RESET}")
    print(f"{Colors.CYAN}Manifest:   {result.manifest_path}{Colors.RESET}")
    print(f"{Colors.CYAN}Analysis:   {result.analysis_path}{Colors.RESET}")
    print(f"{Colors.CYAN}SDK bridge: {result.sdk_bridge_path}{Colors.RESET}")
    print(f"{Colors.BOLD}WASM artifacts:{Colors.RESET}")
    for path in result.wasm_paths:
        print(f"  - {Colors.BLUE}{path}{Colors.RESET}")

    if result.diagnostics:
        print(f"\n{Colors.YELLOW}Diagnostics:{Colors.RESET}")
        for diagnostic in result.diagnostics:
            print(f"  {_format_diagnostic(diagnostic)}")

    return 0


def _warn_on_password_flag(args: argparse.Namespace) -> None:
    if getattr(args, "password", None) is not None:
        print(
            "warning: passing passwords via --password can leak them into shell history and process lists; prefer the secure interactive prompt when possible.",
            file=sys.stderr,
        )


def _print_auth_result(
    *,
    action: str,
    username: str,
    api_key: str,
    env_path: Path | None,
    show_api_key: bool,
) -> None:
    print(f"{action} user: {username}")
    if env_path is not None:
        print(f"Stored TANDEM_SERVER_URL and TANDEM_API_KEY in {env_path}")
        print(f"API key: {api_key if show_api_key else mask_secret(api_key)}")
        return

    print("Credentials were not written to disk.")
    print(f"API key: {api_key}")


def _cmd_auth_register(args: argparse.Namespace) -> int:
    _warn_on_password_flag(args)
    username = prompt_username(args.username)
    password = prompt_password(args.password, confirm=args.password is None)

    register_user(
        username=username,
        password=password,
        server_url=args.server_url,
    )
    session = login_user(
        username=username,
        password=password,
        server_url=args.server_url,
    )

    env_path = None
    if not args.no_store:
        env_path = store_auth_session(session, env_file=args.env_file)

    _print_auth_result(
        action="Registered",
        username=session.username,
        api_key=session.api_key,
        env_path=env_path,
        show_api_key=args.show_api_key,
    )
    return 0


def _cmd_auth_login(args: argparse.Namespace) -> int:
    _warn_on_password_flag(args)
    username = prompt_username(args.username)
    password = prompt_password(args.password)

    session = login_user(
        username=username,
        password=password,
        server_url=args.server_url,
        rotate_api_key=args.rotate_api_key,
    )

    env_path = None
    if not args.no_store:
        env_path = store_auth_session(session, env_file=args.env_file)

    _print_auth_result(
        action="Authenticated",
        username=session.username,
        api_key=session.api_key,
        env_path=env_path,
        show_api_key=args.show_api_key,
    )
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
    config = load_project_config(args.config_path)
    if config.build_start:
        import subprocess
        if config.build_install:
            print(f"{Colors.YELLOW}Running install command: {config.build_install}{Colors.RESET}")
            subprocess.run(config.build_install, shell=True, check=True)
        print(f"{Colors.GREEN}Running start command: {config.build_start}{Colors.RESET}")
        return subprocess.run(config.build_start, shell=True).returncode

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

    print(f"{Colors.GREEN}{Colors.BOLD}Built artifacts into {result.output_dir}{Colors.RESET}")
    print(f"{Colors.CYAN}Deployment pid: {result.pid}{Colors.RESET}")
    print(f"{Colors.MAGENTA}Queued job: {result.job_id}{Colors.RESET}")
    print(f"{Colors.YELLOW}Initial counts: {_format_counts(result.counts)}{Colors.RESET}")

    if args.no_wait:
        print(f"{Colors.BLUE}Job token:   {result.job_token}{Colors.RESET}")
        print(f"{Colors.BLUE}Status URL:  {result.status_url}{Colors.RESET}")
        print(f"{Colors.BLUE}Results URL: {result.results_url}{Colors.RESET}")
        return 0

    print(f"\n{Colors.BOLD}Waiting for results...{Colors.RESET}")
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
    load_dotenv(find_dotenv(usecwd=True))

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
        if args.command == "auth":
            if args.auth_command == "register":
                return _cmd_auth_register(args)
            if args.auth_command == "login":
                return _cmd_auth_login(args)
            parser.error(f"Unknown auth command: {args.auth_command}")
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
