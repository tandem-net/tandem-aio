from __future__ import annotations

from pathlib import Path
from typing import Any

from .app_config import ProjectConfig
from .discovery import DiscoveredProject


def _manifest_module_name(discovered: DiscoveredProject) -> str | None:
    source_file = discovered.sdk_descriptor.source_file
    if isinstance(source_file, str) and source_file:
        return Path(source_file).stem

    module_name = discovered.sdk_descriptor.module_name
    if isinstance(module_name, str) and module_name:
        return module_name

    return None


def _relative_or_absolute(path_value: str | None, *, base: Path) -> str | None:
    if path_value is None:
        return None

    path = Path(path_value)
    try:
        return str(path.resolve().relative_to(base.resolve()))
    except ValueError:
        return str(path.resolve())


def _split_hint(kind: str, options: dict[str, Any]) -> dict[str, Any] | None:
    """A `split` task fans its input list out across nodes; the server shards it
    data-parallel. `chunk` is the user's hint for how big each shard should be."""
    if kind != "split":
        return None

    hint: dict[str, Any] = {"strategy": "data_parallel"}
    if "chunk" in options:
        hint["chunk"] = options["chunk"]
    return hint


def build_manifest(
    config: ProjectConfig, discovered: DiscoveredProject
) -> dict[str, Any]:
    """Build a manifest.json-compatible structure from the SDK discovery payload."""

    manifest_tasks: list[dict[str, Any]] = []

    for descriptor in discovered.task_descriptors:
        record = descriptor.as_dict()
        name = record["name"]
        kind = record["kind"]
        options = dict(record.get("options", {}))

        entry: dict[str, Any] = {
            "name": name,
            "export_name": record["export_name"],
            "qualname": record["qualname"],
            "wasm": f"tasks/{name}.wasm",
            "kind": kind,
            "parameters": list(record.get("parameters", [])),
            "source": {
                "file": _relative_or_absolute(
                    record.get("source_file"), base=config.project_root
                ),
                "line": record.get("source_line"),
            },
        }

        if record.get("return_annotation") is not None:
            entry["return_annotation"] = record["return_annotation"]

        # timeout_ms is the one option that flows all the way to the node (it
        # sets the fuel budget), so hoist it to the top level for the server.
        if "timeout_ms" in options:
            entry["timeout_ms"] = options["timeout_ms"]

        split_hint = _split_hint(kind, options)
        if split_hint:
            entry["split"] = split_hint

        if options:
            entry["options"] = options

        manifest_tasks.append(entry)

    return {
        "name": config.name,
        "version": config.version,
        "runtime": config.runtime,
        "sdk": discovered.sdk_descriptor.sdk.as_dict(),
        "module": {
            "name": _manifest_module_name(discovered),
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
