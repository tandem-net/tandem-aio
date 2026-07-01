from __future__ import annotations

import functools
from typing import Any, Callable, Sequence, TypeVar

from tandem.validator import validate_independence

A = TypeVar("A")
R = TypeVar("R")


def split(chunk: int = 1) -> Callable:
    """
    Decorator factory. Marks a function as a Tandem split task.

    The server will dispatch calls in chunks of `chunk` items per node.
    The wrapper takes a list of arguments and returns results in the
    same order.

        @tandem.split(chunk=2)
        def foo(x):
            return x + 3

        foo([7, 2, 9, 3, 7])
        # chunks: [7, 2], [9, 3], [7] -> [10, 5, 12, 6, 10]

    Parameters
    ----------
    chunk : int
        Items per node when the server splits the input list. Default 1.
    """
    def decorator(func: Callable[[A], R]) -> Callable[[Sequence[A]], list[R]]:
        validate_independence(func)
        chunk_size = max(1, chunk)

        @functools.wraps(func)
        def wrapper(args: Sequence[Any]) -> list[Any]:
            return [func(item) for item in args]

        wrapper.__tandem_kind__ = "split"       # type: ignore[attr-defined]
        wrapper.__tandem_chunk__ = chunk_size   # type: ignore[attr-defined]
        wrapper.__tandem_original__ = func      # type: ignore[attr-defined]
        return wrapper  # type: ignore[return-value]

    return decorator