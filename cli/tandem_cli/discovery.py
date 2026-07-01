from __future__ import annotations

import hashlib
import importlib
import importlib.util
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Iterator

from .app_config import ProjectConfig


@dataclass(frozen=True)
class DiscoveredProject:
    """Loaded Python module plus the SDK discovery payload derived from it."""

    module: ModuleType
    sdk_descriptor: Any
    task_descriptors: tuple[Any, ...]
    tasks: dict[str, Any]


@contextmanager
def _prepend_sys_path(paths: list[Path]) -> Iterator[None]:
    original = list(sys.path)
    try:
        for path in reversed(paths):
            value = str(path)
            if value not in sys.path:
                sys.path.insert(0, value)
        yield
    finally:
        sys.path[:] = original


def _unique_module_name(entry_path: Path) -> str:
    digest = hashlib.sha256(str(entry_path).encode("utf-8")).hexdigest()[:12]
    return f"_tandem_target_{entry_path.stem}_{digest}"


def load_entry_module(config: ProjectConfig) -> ModuleType:
    """Load the configured Python entry file as an isolated module."""

    module_name = _unique_module_name(config.entry_path)
    spec = importlib.util.spec_from_file_location(module_name, config.entry_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not create an import spec for {config.entry_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module

    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # pragma: no cover - depends on user module behavior.
        sys.modules.pop(module_name, None)
        raise RuntimeError(
            f"Failed to import Tandem entry module {config.entry_path}"
        ) from exc

    return module


def _sdk_import_paths(config: ProjectConfig) -> list[Path]:
    paths = [config.project_root, config.entry_path.parent]
    if config.sdk_path is not None:
        paths.insert(0, config.sdk_path)
    return paths


def discover_project(config: ProjectConfig) -> DiscoveredProject:
    """Import the project entrypoint and collect the SDK discovery payload."""

    with _prepend_sys_path(_sdk_import_paths(config)):
        module = load_entry_module(config)

        try:
            sdk_module = importlib.import_module(config.sdk_import_name)
            describe_target = sdk_module.describe_target
        except ImportError as exc:
            raise RuntimeError(
                "Could not import the Tandem runtime SDK "
                f"`{config.sdk_import_name}` for runtime `{config.runtime}`. "
                "The CLI now bundles runtime SDKs automatically; if you need a "
                "custom SDK checkout, set `project.sdk_path` in the CLI config."
            ) from exc

        sdk_descriptor = describe_target(module)
        task_descriptors = tuple(sdk_descriptor.tasks)
        tasks = {task.export_name: task.task for task in task_descriptors}

    return DiscoveredProject(
        module=module,
        sdk_descriptor=sdk_descriptor,
        task_descriptors=task_descriptors,
        tasks=tasks,
    )
