from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .analysis import AnalysisReport, Diagnostic, analyze_tasks
from .app_config import ProjectConfig, load_project_config
from .discovery import DiscoveredProject, discover_project
from .manifest import build_manifest
from .wasm import build_placeholder_wasm


class AnalysisFailure(RuntimeError):
    """Raised when static validation fails in strict build mode."""

    def __init__(self, report: AnalysisReport) -> None:
        self.report = report
        super().__init__(
            f"Build aborted due to {report.error_count} analysis error(s)."
        )


@dataclass(frozen=True)
class BuildResult:
    config: ProjectConfig
    output_dir: Path
    manifest_path: Path
    analysis_path: Path
    sdk_bridge_path: Path
    wasm_paths: tuple[Path, ...]
    task_count: int
    diagnostics: tuple[Diagnostic, ...]


def inspect_project(
    config_path: str | Path,
) -> tuple[ProjectConfig, DiscoveredProject, AnalysisReport]:
    """Load project config, discover tasks, and run analysis."""

    config = load_project_config(config_path)
    discovered = discover_project(config)
    if not discovered.tasks:
        raise RuntimeError(
            f"No Tandem tasks were discovered in {config.entry_path}. Add decorators like `@tandem.compute`."
        )

    report = analyze_tasks(discovered.module, discovered.tasks)
    return config, discovered, report


def build_project(config_path: str | Path, *, strict: bool = True) -> BuildResult:
    """Build discovered tasks into placeholder WASM artifacts plus a manifest."""

    config, discovered, report = inspect_project(config_path)
    if strict and report.has_errors:
        raise AnalysisFailure(report)

    if config.output_dir.exists():
        shutil.rmtree(config.output_dir)

    tasks_dir = config.output_dir / "tasks"
    tandem_dir = config.output_dir / ".tandem"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    tandem_dir.mkdir(parents=True, exist_ok=True)

    manifest = build_manifest(config, discovered)
    manifest_path = tandem_dir / "manifest.json"
    analysis_path = tandem_dir / "analysis.json"
    sdk_bridge_path = tandem_dir / "sdk-bridge.json"

    entry_lookup = {entry["name"]: entry for entry in manifest["tasks"]}
    wasm_paths: list[Path] = []

    for _, task in sorted(discovered.tasks.items()):
        manifest_entry = entry_lookup[task.metadata.name]
        wasm_path = config.output_dir / manifest_entry["wasm"]
        wasm_path.parent.mkdir(parents=True, exist_ok=True)
        wasm_path.write_bytes(
            build_placeholder_wasm(
                task,
                manifest_entry,
                sdk_info=discovered.sdk_descriptor.sdk.as_dict(),
            )
        )
        wasm_paths.append(wasm_path)

    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    analysis_path.write_text(
        json.dumps(
            {
                "diagnostics": [
                    diagnostic.as_dict() for diagnostic in report.diagnostics
                ]
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    sdk_bridge_path.write_text(
        json.dumps(discovered.sdk_descriptor.as_dict(), indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )

    return BuildResult(
        config=config,
        output_dir=config.output_dir,
        manifest_path=manifest_path,
        analysis_path=analysis_path,
        sdk_bridge_path=sdk_bridge_path,
        wasm_paths=tuple(wasm_paths),
        task_count=len(discovered.tasks),
        diagnostics=report.diagnostics,
    )


def clean_project(config_path: str | Path) -> Path:
    """Remove generated build artifacts for a project."""

    config = load_project_config(config_path)
    if config.output_dir.exists():
        shutil.rmtree(config.output_dir)
    return config.output_dir
