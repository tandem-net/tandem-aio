from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .analysis import Diagnostic
from .app_config import load_project_config, write_project_config
from .build import AnalysisFailure, build_project, clean_project, inspect_project
from .manifest import build_manifest


def _format_diagnostic(diagnostic: Diagnostic) -> str:
    location = f"{diagnostic.file}:{diagnostic.line}:{diagnostic.column}"
    return (
        f"[{diagnostic.level}] {diagnostic.code} task={diagnostic.task} "
        f"{location} - {diagnostic.message}"
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tandem-cli",
        description="Discover Tandem SDK tasks and build placeholder WASM artifacts.",
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
        print(str(exc), file=sys.stderr)
        print("Diagnostics:", file=sys.stderr)
        for diagnostic in exc.report.diagnostics:
            print(f"  {_format_diagnostic(diagnostic)}", file=sys.stderr)
        return 1

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
        if args.command == "clean":
            return _cmd_clean(args)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    parser.error(f"Unknown command: {args.command}")
    return 2
