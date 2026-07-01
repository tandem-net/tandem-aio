"""Marker decorators for the Tandem Python SDK.

The Python SDK's role is to mark functions and values so the Tandem CLI can
later discover them, validate them, and compile the marked tasks to WASM. The
SDK does not submit executable Python objects at runtime.
"""

from __future__ import annotations

import functools
import inspect
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from threading import Lock
from types import ModuleType
from typing import Any, Generic, ParamSpec, TypeVar, cast

P = ParamSpec("P")
R = TypeVar("R")
T = TypeVar("T")

_MARKED_VALUES_LOCK = Lock()
_MARKED_VALUES: dict[int, str] = {}
_RUNTIME_CONTEXT: dict[str, Any] = {}
_MISSING = object()

_CANONICAL_ANNOTATIONS = {
    "async": "async_task",
    "parallel": "split",
    "scheduled": "cron",
}

_EXECUTION_CLASSES = {
    "compute": "compute",
    "split": "compute",
    "pipeline": "compute",
    "serve": "serve",
    "async_task": "serve",
    "cron": "scheduled",
    "deferred": "scheduled",
}


class TaskError(RuntimeError):
    """Error type that Tandem tasks may raise explicitly.

    The `retryable` flag mirrors the SDK plan's task-level error semantics so a
    future CLI/runtime can preserve retry intent in generated manifests.
    """

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


@dataclass(frozen=True)
class TaskMetadata:
    """Build-time task metadata exported by marker decorators."""

    annotation: str
    canonical_annotation: str
    execution_class: str
    aliases: tuple[str, ...]
    module: str
    name: str
    qualname: str
    source_file: str | None
    source_line: int
    parameters: tuple[str, ...]
    return_annotation: str | None
    options: dict[str, Any]
    referenced_values: dict[str, str]

    def as_manifest_entry(self) -> dict[str, Any]:
        """Return a manifest-like dictionary for future CLI consumption."""

        return {
            "annotation": self.annotation,
            "canonical_annotation": self.canonical_annotation,
            "execution_class": self.execution_class,
            "aliases": self.aliases,
            "module": self.module,
            "name": self.name,
            "qualname": self.qualname,
            "source_file": self.source_file,
            "source_line": self.source_line,
            "parameters": self.parameters,
            "return_annotation": self.return_annotation,
            "options": _normalize_option_value(self.options),
            "referenced_values": dict(self.referenced_values),
        }


class TandemTask(Generic[P, R]):
    """Callable wrapper that preserves the Python function and attached metadata."""

    def __init__(
        self,
        func: Callable[P, R],
        *,
        annotation: str,
        options: dict[str, Any],
        aliases: tuple[str, ...] = (),
    ) -> None:
        self._func = func
        self.annotation = annotation
        self.canonical_annotation = _canonical_annotation(annotation)
        self.execution_class = _execution_class_for(annotation)
        self.options = dict(options)
        self.aliases = tuple(aliases)
        self.__signature__ = inspect.signature(func)
        self.__tandem_task__ = True
        functools.update_wrapper(self, func)

    @property
    def function(self) -> Callable[P, R]:
        """Expose the underlying undecorated Python callable."""

        return self._func

    @property
    def metadata(self) -> TaskMetadata:
        signature = inspect.signature(self._func)
        return_annotation: str | None = None

        if signature.return_annotation is not inspect.Signature.empty:
            return_annotation = _annotation_to_string(signature.return_annotation)

        code = self._func.__code__
        return TaskMetadata(
            annotation=self.annotation,
            canonical_annotation=self.canonical_annotation,
            execution_class=self.execution_class,
            aliases=self.aliases,
            module=self._func.__module__,
            name=self._func.__name__,
            qualname=self._func.__qualname__,
            source_file=inspect.getsourcefile(self._func),
            source_line=code.co_firstlineno,
            parameters=tuple(signature.parameters.keys()),
            return_annotation=return_annotation,
            options=dict(self.options),
            referenced_values=_collect_marked_globals(self._func),
        )

    def manifest_entry(self) -> dict[str, Any]:
        """Return a manifest-like view of this task for CLI discovery."""

        return self.metadata.as_manifest_entry()

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R:
        """Preserve normal Python execution for local testing and debugging."""

        return self._func(*args, **kwargs)

    def __repr__(self) -> str:
        return (
            f"TandemTask(qualname={self._func.__qualname__!r}, "
            f"annotation={self.annotation!r}, options={self.options!r})"
        )


def _canonical_annotation(annotation: str) -> str:
    return _CANONICAL_ANNOTATIONS.get(annotation, annotation)


def _execution_class_for(annotation: str) -> str:
    canonical = _canonical_annotation(annotation)
    return _EXECUTION_CLASSES.get(canonical, "compute")


def _annotation_to_string(annotation: Any) -> str:
    if isinstance(annotation, str):
        return annotation

    return getattr(annotation, "__name__", repr(annotation))


def _normalize_option_value(value: Any) -> Any:
    if isinstance(value, TandemTask):
        metadata = value.metadata
        return {
            "task_ref": metadata.qualname,
            "module": metadata.module,
            "annotation": metadata.annotation,
            "canonical_annotation": metadata.canonical_annotation,
        }

    if isinstance(value, dict):
        return {key: _normalize_option_value(item) for key, item in value.items()}

    if isinstance(value, list):
        return [_normalize_option_value(item) for item in value]

    if isinstance(value, tuple):
        return tuple(_normalize_option_value(item) for item in value)

    if isinstance(value, set):
        return [_normalize_option_value(item) for item in value]

    return value


def _collect_marked_globals(func: Callable[..., Any]) -> dict[str, str]:
    code = getattr(func, "__code__", None)
    module_globals = getattr(func, "__globals__", {})

    if code is None or not module_globals:
        return {}

    referenced_values: dict[str, str] = {}

    with _MARKED_VALUES_LOCK:
        for name in code.co_names:
            if name not in module_globals:
                continue

            marker_kind = _MARKED_VALUES.get(id(module_globals[name]))
            if marker_kind is not None:
                referenced_values[name] = marker_kind

    return referenced_values


def _decorate_task(
    func: Callable[P, R] | None,
    *,
    annotation: str,
    options: dict[str, Any],
    aliases: tuple[str, ...] = (),
) -> TandemTask[P, R] | Callable[[Callable[P, R]], TandemTask[P, R]]:
    if func is not None:
        return TandemTask(func, annotation=annotation, options=options, aliases=aliases)

    def decorator(inner: Callable[P, R]) -> TandemTask[P, R]:
        return TandemTask(
            inner, annotation=annotation, options=dict(options), aliases=aliases
        )

    return decorator


def task(
    func: Callable[P, R] | None = None,
    /,
    *,
    mode: str = "compute",
    **options: Any,
) -> TandemTask[P, R] | Callable[[Callable[P, R]], TandemTask[P, R]]:
    """Low-level task decorator builder.

    Examples:
    - `@tandem.task`
    - `@tandem.task(mode="split", strategy="data_parallel")`
    - `@tandem.task(mode="scheduled", expression="0 0 * * *")`
    """

    if _canonical_annotation(mode) == "cron":
        expression = options.pop("expression", None)
        if not isinstance(expression, str) or not expression.strip():
            raise TypeError(
                "`task(..., mode='cron' | 'scheduled')` requires a non-empty "
                "`expression=` cron string."
            )

        options = {"schedule": expression, **options}

    return _decorate_task(func, annotation=mode, options=options)


def compute(
    func: Callable[P, R] | None = None,
    /,
    **options: Any,
) -> TandemTask[P, R] | Callable[[Callable[P, R]], TandemTask[P, R]]:
    """Mark a function as a one-shot compute task."""

    return _decorate_task(func, annotation="compute", options=options)


def split(
    func: Callable[P, R] | None = None,
    /,
    **options: Any,
) -> TandemTask[P, R] | Callable[[Callable[P, R]], TandemTask[P, R]]:
    """Mark a function as a splittable compute task."""

    return _decorate_task(
        func, annotation="split", options=options, aliases=("parallel",)
    )


def parallel(
    func: Callable[P, R] | None = None,
    /,
    **options: Any,
) -> TandemTask[P, R] | Callable[[Callable[P, R]], TandemTask[P, R]]:
    """Alias for `split` that preserves the alias name in metadata."""

    return _decorate_task(
        func, annotation="parallel", options=options, aliases=("split",)
    )


def serve(
    func: Callable[P, R] | None = None,
    /,
    **options: Any,
) -> TandemTask[P, R] | Callable[[Callable[P, R]], TandemTask[P, R]]:
    """Mark a function as a long-lived hosted task."""

    return _decorate_task(func, annotation="serve", options=options)


def async_task(
    func: Callable[P, R] | None = None,
    /,
    **options: Any,
) -> TandemTask[P, R] | Callable[[Callable[P, R]], TandemTask[P, R]]:
    """Mark a function as a fire-and-forget task."""

    return _decorate_task(func, annotation="async_task", options=options)


def cron(
    expression: str, /, **options: Any
) -> Callable[[Callable[P, R]], TandemTask[P, R]]:
    """Schedule a task using a cron expression."""

    if not expression.strip():
        raise ValueError("Cron expressions must be non-empty strings.")

    return cast(
        Callable[[Callable[P, R]], TandemTask[P, R]],
        _decorate_task(
            None,
            annotation="cron",
            options={"schedule": expression, **options},
            aliases=("scheduled",),
        ),
    )


def scheduled(
    expression: str, /, **options: Any
) -> Callable[[Callable[P, R]], TandemTask[P, R]]:
    """Alias for `cron` that preserves the alias name in metadata."""

    if not expression.strip():
        raise ValueError("Cron expressions must be non-empty strings.")

    return cast(
        Callable[[Callable[P, R]], TandemTask[P, R]],
        _decorate_task(
            None,
            annotation="scheduled",
            options={"schedule": expression, **options},
            aliases=("cron",),
        ),
    )


def deferred(
    func: Callable[P, R] | None = None,
    /,
    **options: Any,
) -> TandemTask[P, R] | Callable[[Callable[P, R]], TandemTask[P, R]]:
    """Mark a function whose result is delivered asynchronously by the runtime."""

    return _decorate_task(func, annotation="deferred", options=options)


def pipeline(
    func: Callable[P, R] | None = None,
    /,
    **options: Any,
) -> TandemTask[P, R] | Callable[[Callable[P, R]], TandemTask[P, R]]:
    """Mark a function as a pipeline stage."""

    return _decorate_task(func, annotation="pipeline", options=options)


def immutable(value: T) -> T:
    """Mark a module-level value as an immutable bundle dependency."""

    with _MARKED_VALUES_LOCK:
        _MARKED_VALUES[id(value)] = "immutable"

    return value


def constant(value: T) -> T:
    """Mark a module-level value as a compile-time constant."""

    with _MARKED_VALUES_LOCK:
        _MARKED_VALUES[id(value)] = "constant"

    return value


def param(value: T) -> T:
    """Explicit parameter marker placeholder for the scaffolded SDK."""

    return value


def context(name: str, default: Any = _MISSING) -> Any:
    """Read a context value for local execution.

    In the full Tandem system these values are injected by the runtime. The SDK
    keeps a simple in-process store so marked tasks can still be exercised
    locally when desired.
    """

    if name in _RUNTIME_CONTEXT:
        return _RUNTIME_CONTEXT[name]

    if default is not _MISSING:
        return default

    raise KeyError(
        f"Context value {name!r} is not available in the local Tandem SDK context store."
    )


def _set_context(values: Mapping[str, Any]) -> None:
    """Internal helper for tests and future CLI/runtime integration."""

    _RUNTIME_CONTEXT.clear()
    _RUNTIME_CONTEXT.update(dict(values))


def discover_tasks(
    target: ModuleType | Mapping[str, Any],
) -> dict[str, TandemTask[Any, Any]]:
    """Discover Tandem tasks from a module object or namespace mapping."""

    namespace = vars(target) if isinstance(target, ModuleType) else dict(target)
    discovered: dict[str, TandemTask[Any, Any]] = {}

    for name, value in namespace.items():
        if isinstance(value, TandemTask):
            discovered[name] = value

    return discovered


def manifest(target: ModuleType | Mapping[str, Any]) -> list[dict[str, Any]]:
    """Produce manifest-like entries for all discovered tasks in a namespace."""

    tasks = discover_tasks(target)
    return [tasks[name].manifest_entry() for name in sorted(tasks)]


def __getattr__(name: str) -> Any:
    if name == "async":
        return async_task

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# Backwards-compatible alias from the initial scaffold.
distribute = compute


__all__ = [
    "TaskError",
    "TandemTask",
    "TaskMetadata",
    "async_task",
    "compute",
    "constant",
    "context",
    "cron",
    "deferred",
    "discover_tasks",
    "distribute",
    "immutable",
    "manifest",
    "parallel",
    "param",
    "pipeline",
    "scheduled",
    "serve",
    "split",
    "task",
]
