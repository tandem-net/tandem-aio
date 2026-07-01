"""
tandem.Immutable

A read-only wrapper for module-level constants. All Tandem computed
tasks must only read globals that are wrapped in tandem.Immutable,
or else the independence validator will raise an error.

Usage forms:
---------------
    NUM = Immutable(15)
    NUM = Immutable[int](15)
    NUM = Immutable.of(existing)
    NUM = Immutable[int].of(existing)
    NUM = Immutable.of_type(int, existing)

Every form stores the value inside the wrapper. Access the inner value
via .value, or access its attributes directly (proxied via __getattr__).

Any attempt to modify the wrapper raises AttributeError.
"""

from __future__ import annotations

import inspect
from typing import Any, TypeVar

T = TypeVar("T")

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_IMMUTABLE_REGISTRY: dict[str, set[str]] = {}


def _register(module_name: str, var_name: str) -> None:
    _IMMUTABLE_REGISTRY.setdefault(module_name, set()).add(var_name)


def is_immutable(module_name: str, var_name: str) -> bool:
    return var_name in _IMMUTABLE_REGISTRY.get(module_name, set())


def all_immutable_names(module_name: str) -> set[str]:
    """All immutable names registered for a module.
    Called by the independence validator and the compiler scanner."""
    return set(_IMMUTABLE_REGISTRY.get(module_name, set()))


def register_immutable_name(module_name: str, var_name: str) -> None:
    """Explicitly register a name. For tests and programmatic tooling."""
    _register(module_name, var_name)


# ---------------------------------------------------------------------------
# Name inference
# ---------------------------------------------------------------------------

def _infer_name(depth: int) -> tuple[str, str | None]:
    """Return (module_name, var_name) from `depth` frames up."""
    frame = inspect.currentframe()
    try:
        for _ in range(depth):
            if frame is None:
                return "<unknown>", None
            frame = frame.f_back
        if frame is None:
            return "<unknown>", None
        module = frame.f_globals.get("__name__", "<unknown>")
        try:
            source_lines, _ = inspect.findsource(frame)
        except (OSError, TypeError):
            return module, None
        lineno = frame.f_lineno
        if not (0 <= lineno - 1 < len(source_lines)):
            return module, None
        line = source_lines[lineno - 1].strip()
        if "=" not in line:
            return module, None
        lhs = line.split("=", 1)[0].strip()
        if ":" in lhs:
            lhs = lhs.split(":", 1)[0].strip()
        return module, (lhs if lhs.isidentifier() else None)
    finally:
        del frame


# ---------------------------------------------------------------------------
# Immutable metaclass -- enables Immutable[T] subscript
# ---------------------------------------------------------------------------

class _ImmutableMeta(type):

    def __getitem__(cls, type_hint: Any) -> type:
        """Immutable[int], Immutable[str | None], Immutable[Point], etc."""
        hint_name = getattr(type_hint, "__name__", repr(type_hint))
        return _ImmutableMeta(
            f"Immutable[{hint_name}]",
            (cls,),
            {"_type_hint": type_hint},
        )


# ---------------------------------------------------------------------------
# Immutable wrapper
# ---------------------------------------------------------------------------

class Immutable(metaclass=_ImmutableMeta):
    """
    Read-only wrapper for a module-level constant.

    Forms:
        Immutable(value)
        Immutable[T](value)
        Immutable.of(value)
        Immutable[T].of(value)
        Immutable.of_type(T, value)
    """

    __slots__ = ("_value",)
    _type_hint: Any = None  # set on typed subclasses by __class_getitem__

    def __init__(self, value: Any) -> None:
        object.__setattr__(self, "_value", value)
        module, name = _infer_name(depth=2)
        if name:
            _register(module, name)

    # -- read-only enforcement -------------------------------------------

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("Immutable is read-only")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("Immutable is read-only")

    # -- inner value access ----------------------------------------------

    @property
    def value(self) -> Any:
        """Unwrap the inner value explicitly."""
        return object.__getattribute__(self, "_value")

    def __getattr__(self, name: str) -> Any:
        """Proxy attribute access to the inner value."""
        return getattr(object.__getattribute__(self, "_value"), name)

    # -- standard dunder proxies -----------------------------------------

    def __repr__(self) -> str:
        v = object.__getattribute__(self, "_value")
        t = type(self)._type_hint
        if t is not None:
            tname = getattr(t, "__name__", repr(t))
            return f"Immutable[{tname}]({v!r})"
        return f"Immutable({v!r})"

    def __eq__(self, other: Any) -> bool:
        v = object.__getattribute__(self, "_value")
        if isinstance(other, Immutable):
            return v == object.__getattribute__(other, "_value")
        return v == other

    def __hash__(self) -> int:
        v = object.__getattribute__(self, "_value")
        try:
            return hash(v)
        except TypeError:
            return id(v)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return object.__getattribute__(self, "_value")(*args, **kwargs)

    def __len__(self) -> int:
        return len(object.__getattribute__(self, "_value"))

    def __iter__(self):
        return iter(object.__getattribute__(self, "_value"))

    def __contains__(self, item: Any) -> bool:
        return item in object.__getattribute__(self, "_value")

    def __getitem__(self, key: Any) -> Any:
        return object.__getattribute__(self, "_value")[key]

    # -- alternative constructors ----------------------------------------

    @classmethod
    def of(cls, value: Any) -> "Immutable":
        """
        Wrap an existing value.

            ORIGIN = Immutable.of(raw_point)
            ORIGIN = Immutable[Point].of(raw_point)
        """
        inst = object.__new__(cls)
        object.__setattr__(inst, "_value", value)
        module, name = _infer_name(depth=2)
        if name:
            _register(module, name)
        return inst

    @classmethod
    def of_type(cls, type_hint: Any, value: Any) -> "Immutable":
        """
        Inline type declaration without subscript syntax.

            CONFIG = Immutable.of_type(Config, raw_config)
        """
        hint_name = getattr(type_hint, "__name__", repr(type_hint))
        typed_cls = _ImmutableMeta(
            f"Immutable[{hint_name}]",
            (cls,),
            {"_type_hint": type_hint},
        )
        inst = object.__new__(typed_cls)
        object.__setattr__(inst, "_value", value)
        module, name = _infer_name(depth=2)
        if name:
            _register(module, name)
        return inst
