"""Find the Tandem tasks a user marked in their module.

The CLI imports the user's module and calls `describe_target` to find every
function decorated with `@tandem.compute` or wrapped by `tandem.split`. It hands
back a small, plain description the CLI turns into a build manifest.

Keeping discovery here -- in the one SDK the user installs -- is what lets
build-time and run-time agree on exactly what a "task" is, instead of the two
sides each having their own idea.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from types import ModuleType
from typing import Any

# The decorator kinds we treat as runnable tasks.
_TASK_KINDS = ("compute", "split")


@dataclass(frozen=True)
class SdkInfo:
    """Which SDK produced this description."""

    package: str
    language: str
    version: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "package": self.package,
            "language": self.language,
            "version": self.version,
        }


@dataclass(frozen=True)
class TaskMetadata:
    """The facts about one task the CLI needs to build and route it."""

    name: str
    kind: str
    options: dict[str, Any]
    qualname: str
    source_file: str | None
    source_line: int | None
    parameters: list[str]
    return_annotation: str | None


@dataclass(frozen=True)
class TaskDescriptor:
    """One discovered task: the name it's exported under, the marked object
    itself, and the metadata we pulled off it."""

    export_name: str
    task: Any
    metadata: TaskMetadata

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.metadata.name,
            "export_name": self.export_name,
            "kind": self.metadata.kind,
            "qualname": self.metadata.qualname,
            "options": dict(self.metadata.options),
            "source_file": self.metadata.source_file,
            "source_line": self.metadata.source_line,
            "parameters": list(self.metadata.parameters),
            "return_annotation": self.metadata.return_annotation,
        }


@dataclass(frozen=True)
class SdkDescriptor:
    """Everything discovery found in a target module."""

    sdk: SdkInfo
    module_name: str | None
    source_file: str | None
    tasks: list[TaskDescriptor]

    def as_dict(self) -> dict[str, Any]:
        return {
            "sdk": self.sdk.as_dict(),
            "module_name": self.module_name,
            "source_file": self.source_file,
            "tasks": [task.as_dict() for task in self.tasks],
        }


def _raw_function(task: Any) -> Any:
    """Get the user's original function out of a Tandem wrapper.

    The decorators keep the real function around as `__tandem_original__`; we
    fall back to `.function` and then the object itself just to be safe.
    """
    return getattr(task, "__tandem_original__", getattr(task, "function", task))


def _options_for(task: Any, kind: str) -> dict[str, Any]:
    """Pull the decorator options back off a marked task."""
    options: dict[str, Any] = {}
    if kind == "compute":
        if hasattr(task, "__tandem_batch__"):
            options["batch"] = task.__tandem_batch__
        if hasattr(task, "__tandem_timeout_ms__"):
            options["timeout_ms"] = task.__tandem_timeout_ms__
    elif kind == "split":
        if hasattr(task, "__tandem_chunk__"):
            options["chunk"] = task.__tandem_chunk__
    return options


def _annotation_name(annotation: Any) -> str:
    """A readable name for a type annotation without importing typing tricks."""
    return getattr(annotation, "__name__", str(annotation))


def _metadata_for(export_name: str, kind: str, task: Any) -> TaskMetadata:
    raw = _raw_function(task)

    source_file: str | None = None
    source_line: int | None = None
    try:
        source_file = inspect.getsourcefile(raw)
        source_line = inspect.getsourcelines(raw)[1]
    except (TypeError, OSError):
        # Some callables have no Python source (builtins, C functions); fine.
        pass

    parameters: list[str] = []
    return_annotation: str | None = None
    try:
        signature = inspect.signature(raw)
        parameters = list(signature.parameters)
        if signature.return_annotation is not inspect.Signature.empty:
            return_annotation = _annotation_name(signature.return_annotation)
    except (TypeError, ValueError):
        pass

    return TaskMetadata(
        name=export_name,
        kind=kind,
        options=_options_for(task, kind),
        qualname=getattr(raw, "__qualname__", export_name),
        source_file=source_file,
        source_line=source_line,
        parameters=parameters,
        return_annotation=return_annotation,
    )


def describe_target(module: ModuleType) -> SdkDescriptor:
    """Find every Tandem task in `module` and describe it.

    We look for the marker the decorators leave behind (`__tandem_kind__`), so a
    task is simply anything the user wrapped with `@tandem.compute` or
    `tandem.split`.
    """
    from tandem import __version__

    tasks: list[TaskDescriptor] = []
    for export_name, value in vars(module).items():
        kind = getattr(value, "__tandem_kind__", None)
        if kind not in _TASK_KINDS:
            continue
        tasks.append(
            TaskDescriptor(
                export_name=export_name,
                task=value,
                metadata=_metadata_for(export_name, kind, value),
            )
        )

    tasks.sort(key=lambda task: task.export_name)

    return SdkDescriptor(
        sdk=SdkInfo(package="tandem", language="python", version=__version__),
        module_name=getattr(module, "__name__", None),
        source_file=getattr(module, "__file__", None),
        tasks=tasks,
    )
