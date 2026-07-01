"""
@tandem.compute(batch=1, timeout_ms=50)

Marks a function as a Tandem compute task. The decorator:
  - validates split-independence at decoration time
  - attaches metadata attributes the compiler reads during `tandem build`
  - returns the original function unchanged

It does NOT batch calls, dispatch to nodes, or execute anything.
Batching and dispatch are compiler + node concerns, not SDK concerns.

    @tandem.compute(batch=3, timeout_ms=50)
    def foo(x):
        return x * 2

    foo(3)   # calls the real function directly, locally
             # batching only happens when running on a Tandem node

Parameters
----------
batch : int
    Hint to the server: collect this many calls before dispatching as
    a group to a node. Default 1 (dispatch immediately).
timeout_ms : int
    Hint to the server: dispatch whatever has been collected after
    this many milliseconds even if batch hasn't been reached.
    Default 50ms.
"""

from __future__ import annotations

import functools
from typing import Any, Callable, TypeVar

from tandem.validator import validate_independence
F = TypeVar("F", bound=Callable[..., Any])


def compute(batch: int = 1, timeout_ms: int = 50) -> Callable[[F], F]:
    """
    Decorator factory. Validates independence and attaches metadata.
    Returns the original function unchanged.

    Raises TandemValidationError at decoration time if the function
    reads any global that is not declared tandem.immutable().
    """
    def decorator(func: F) -> F:
        validate_independence(func)

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        wrapper.__tandem_kind__ = "compute"       # type: ignore[attr-defined]
        wrapper.__tandem_batch__ = batch           # type: ignore[attr-defined]
        wrapper.__tandem_timeout_ms__ = timeout_ms # type: ignore[attr-defined]
        wrapper.__tandem_original__ = func         # type: ignore[attr-defined]
        return wrapper  # type: ignore[return-value]

    return decorator
