"""
@tandem.compute(batch=1, timeout_ms=50)

Decorator that marks a function as a Tandem compute task, which will split function calls into batches and sent to separate nodes.

    @tandem.compute(batch=3, timeout_ms=50)
    def foo(x):
        return x * 2
        
    # foo(1), foo(2), foo(3), foo(4) will be dispatched as two batches: [foo(1), foo(2), foo(3)] and [foo(4)].

Parameters
----------
batch : int
    The server will collect this many calls before dispatching as
    a group to a node. Default 1 (dispatch immediately).
timeout_ms : int
    The server will dispatch whatever has been collected after
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
    Decorator factory. Validates that the function is split-independent,
    attaches Tandem metadata, and returns a wrapped callable.

    Raises
    ------
    TandemValidationError
        If the decorated function is not split-independent.
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
