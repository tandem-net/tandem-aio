from __future__ import annotations

from pathlib import Path
from typing import Any

from .app_config import ProjectConfig
from .discovery import DiscoveredProject


def _relative_or_absolute(path_value: str | None, *, base: Path) -> str | None:
    if path_value is None:
        return None

    path = Path(path_value)
    try:
        return str(path.resolve().relative_to(base.resolve()))
    except ValueError:
        return str(path.resolve())


def _manifest_execution_class(canonical_annotation: str) -> str:
    if canonical_annotation in {"serve", "async_task"}:
        return "serve"
    if canonical_annotation in {"cron", "deferred"}:
        return "scheduled"
    return "compute"


def _build_split_hint(
    canonical_annotation: str, options: dict[str, Any]
) -> dict[str, Any] | None:
    if canonical_annotation == "split":
        split = {"strategy": options.get("strategy", "data_parallel")}
        for field in (
            "max_shards",
            "min_shard_size",
            "reducer",
            "timeout_per_shard_ms",
            "retry_on_shard_failure",
            "max_retries_per_shard",
        ):
            if field in options:
                split[field] = options[field]
        return split

    if canonical_annotation == "pipeline":
        split = {"strategy": "pipeline"}
        if "next" in options:
            split["next"] = options["next"]
        return split

    if canonical_annotation == "serve":
        split = {"strategy": options.get("strategy", "replicated")}
        for field in (
            "replicas",
            "scale_policy",
            "scale_up_threshold",
            "scale_down_threshold",
            "port",
        ):
            if field in options:
                split[field] = options[field]
        return split

    if canonical_annotation == "async_task":
        split = {"strategy": options.get("strategy", "single")}
        for field in ("replicas", "queue", "port"):
            if field in options:
                split[field] = options[field]
        return split

    return None


def _build_schedule_hint(
    canonical_annotation: str, options: dict[str, Any]
) -> dict[str, Any] | None:
    if canonical_annotation != "cron":
        return None

    cron_expression = options.get("schedule")
    if not isinstance(cron_expression, str) or not cron_expression.strip():
        return None

    return {
        "cron": cron_expression,
        "timezone": options.get("timezone", "UTC"),
        "allow_overlap": bool(options.get("allow_overlap", False)),
    }


def build_manifest(
    config: ProjectConfig, discovered: DiscoveredProject
) -> dict[str, Any]:
    """Build a manifest.json-compatible structure from the SDK discovery payload."""

    manifest_tasks: list[dict[str, Any]] = []
    pipeline_edges: list[dict[str, str]] = []

    for task_descriptor_record in discovered.task_descriptors:
        task_descriptor = task_descriptor_record.as_dict()
        export_name = str(task_descriptor_record.export_name)
        options = dict(task_descriptor.get("options", {}))
        canonical_annotation = str(task_descriptor["canonical_annotation"])

        entry: dict[str, Any] = {
            "name": task_descriptor["name"],
            "export_name": export_name,
            "qualname": task_descriptor["qualname"],
            "wasm": f"tasks/{task_descriptor['name']}.wasm",
            "annotation": task_descriptor["annotation"],
            "canonical_annotation": canonical_annotation,
            "execution_class": _manifest_execution_class(canonical_annotation),
            "source": {
                "file": _relative_or_absolute(
                    task_descriptor.get("source_file"), base=config.project_root
                ),
                "line": task_descriptor["source_line"],
            },
            "parameters": list(task_descriptor.get("parameters", [])),
        }

        if task_descriptor.get("return_annotation") is not None:
            entry["return_annotation"] = task_descriptor["return_annotation"]

        split_hint = _build_split_hint(canonical_annotation, options)
        if split_hint:
            entry["split"] = split_hint

        schedule_hint = _build_schedule_hint(canonical_annotation, options)
        if schedule_hint:
            entry["schedule"] = schedule_hint

        immutable_bundles = sorted(
            name
            for name, marker_kind in task_descriptor.get(
                "referenced_values", {}
            ).items()
            if marker_kind == "immutable"
        )
        if immutable_bundles:
            entry["immutable_bundles"] = immutable_bundles

        embedded_constants = sorted(
            name
            for name, marker_kind in task_descriptor.get(
                "referenced_values", {}
            ).items()
            if marker_kind == "constant"
        )
        if embedded_constants:
            entry["embedded_constants"] = embedded_constants

        for field in ("memory_mb", "timeout_ms", "result_ttl_seconds"):
            if field in options:
                entry[field] = options[field]

        if options:
            entry["options"] = options

        manifest_tasks.append(entry)

        if canonical_annotation == "pipeline":
            next_stage = options.get("next")
            if isinstance(next_stage, str) and next_stage.strip():
                pipeline_edges.append(
                    {"from": task_descriptor["name"], "to": next_stage}
                )

    manifest: dict[str, Any] = {
        "name": config.name,
        "version": config.version,
        "runtime": config.runtime,
        "sdk": discovered.sdk_descriptor.sdk.as_dict(),
        "module": {
            "name": discovered.sdk_descriptor.module_name,
            "source_file": _relative_or_absolute(
                discovered.sdk_descriptor.source_file,
                base=config.project_root,
            ),
        },
        "entry": _relative_or_absolute(
            str(config.entry_path), base=config.project_root
        ),
        "tasks": manifest_tasks,
    }

    if pipeline_edges:
        manifest["graph"] = {"pipeline_stages": pipeline_edges}

    return manifest
