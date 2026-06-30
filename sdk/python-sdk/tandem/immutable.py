"""
tandem.immutable

Designates a module-level variable as a compile-time constant that is
safe to read from inside a tandemed (@tandem.compute / tandem.split)
function. Tandemed functions may ONLY read global state that has been
registered as immutable this way — everything else must come in through
function parameters.

Usage
-----
    NUM = tandem.immutable(67)

    @tandem.compute()
    def foo(x):
        return NUM + x

NOTE ON SYNTAX: the design doc shows the form

    @tandem.immutable
    NUM = 67

This reads naturally but is NOT valid Python — `@decorator` can only
precede a `def`/`class` statement, not a bare assignment, since there is
no assignment object for the decorator to wrap. The real Tandem CLI will
likely support this via a source-level preprocessor / AST rewrite pass
(detecting the `@tandem.immutable` marker followed by an assignment, and
rewriting it before compilation). The SDK, having no compiler yet,
implements the equivalent semantics with the valid form
`NAME = tandem.immutable(value)`, which:

  1. registers NAME as immutable in the defining module
  2. freezes the value as a compile-time constant for that name
  3. returns the value unchanged, so the assignment still works normally

Both spellings should produce the same registry entry once a
preprocessor exists; until then, use the function-call form below.
"""

from __future__ import annotations

import inspect
from typing import Any, TypeVar

T = TypeVar("T")

# module __name__ -> set of variable names declared immutable in that module.
# This is what the static validator (validator.py) checks against when it
# sees a global Name being read inside a tandemed function.
_IMMUTABLE_REGISTRY: dict[str, set[str]] = {}

# (module_name, var_name) -> frozen value, captured at the moment
# `immutable()` was called. Used by LocalExecutor to resolve immutable
# globals deterministically without re-reading mutable module state.
_IMMUTABLE_VALUES: dict[tuple[str, str], Any] = {}


def immutable(value: T, *, name: str | None = None) -> T:
    """
    Mark a value as immutable and register it against the variable name
    it is being assigned to in the caller's module.

        NUM = tandem.immutable(67)

    The binding name is recovered by inspecting the caller's source line
    (best-effort, via `inspect`). If source inspection fails (e.g. in a
    REPL, or if the call isn't a simple `NAME = tandem.immutable(...)`
    statement), pass the name explicitly:

        NUM = tandem.immutable(67, name="NUM")
    """
    frame = inspect.currentframe()
    try:
        caller = frame.f_back
        if caller is None:
            return value
        module_name = caller.f_globals.get("__name__", "<unknown>")

        target_name = name or _infer_assignment_target(caller)
        if target_name:
            _IMMUTABLE_REGISTRY.setdefault(module_name, set()).add(target_name)
            _IMMUTABLE_VALUES[(module_name, target_name)] = value
    finally:
        del frame
    return value


def _infer_assignment_target(caller_frame) -> str | None:
    """Best-effort: read the source line currently executing and pull
    out the left-hand side of a simple `NAME = ...` assignment."""
    try:
        source_lines, _ = inspect.findsource(caller_frame)
    except (OSError, TypeError):
        return None
    lineno = caller_frame.f_lineno
    if lineno - 1 >= len(source_lines) or lineno - 1 < 0:
        return None
    line = source_lines[lineno - 1].strip()
    if "=" not in line:
        return None
    lhs = line.split("=", 1)[0].strip()
    return lhs if lhs.isidentifier() else None


def is_immutable(module_name: str, var_name: str) -> bool:
    """Check whether `var_name` in `module_name` was declared immutable."""
    return var_name in _IMMUTABLE_REGISTRY.get(module_name, set())


def get_immutable_value(module_name: str, var_name: str) -> Any:
    """Fetch the frozen value recorded for an immutable binding."""
    return _IMMUTABLE_VALUES.get((module_name, var_name))


def all_immutable_names(module_name: str) -> set[str]:
    """Return the full set of immutable names registered for a module."""
    return set(_IMMUTABLE_REGISTRY.get(module_name, set()))


def register_immutable_name(module_name: str, var_name: str, value: Any = None) -> None:
    """Explicitly register a name as immutable without going through
    `immutable()`'s source inspection. Useful for tests or programmatic
    registration."""
    _IMMUTABLE_REGISTRY.setdefault(module_name, set()).add(var_name)
    if value is not None:
        _IMMUTABLE_VALUES[(module_name, var_name)] = value
