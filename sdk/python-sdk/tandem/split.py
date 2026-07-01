"""
tandem.split(runnable, chunk=1) -> g(list[arg]) -> list[result]

Marks a function as a Tandem split task and returns a wrapper g that
takes a list of arguments and calls the original function for each one.
The wrapper:
  - validates split-independence of runnable at call time
  - attaches metadata the compiler reads during `tandem build`
  - locally, calls runnable(item) for each item and returns results in order

It does NOT chunk or dispatch to nodes. Chunking is a server/node
concern determined at dispatch time using the chunk hint in the manifest.

    def foo(x):
        return x + 3

    goo = tandem.split(foo, 5)
    goo([7, 2, 9])   # locally: [foo(7), foo(2), foo(9)] == [10, 5, 12]
                     # on a node: dispatched in chunks of 5 per node

Parameters
----------
runnable : callable
    A single-argument, split-independent function.
chunk : int
    Hint to the server: group this many items per node when splitting.
    Default 1.
"""

from __future__ import annotations

import functools
from typing import Any, Callable, Sequence, TypeVar

from tandem.validator import validate_independence

A = TypeVar("A")
R = TypeVar("R")


def split(runnable: Callable[[A], R], chunk: int = 1) -> Callable[[Sequence[A]], list[R]]:
    """
    Validate independence of runnable, attach metadata, return a wrapper.

    Raises TandemValidationError immediately if runnable reads any
    global that is not declared tandem.immutable().
    """
    validate_independence(runnable)
    chunk_size = max(1, chunk)

    @functools.wraps(runnable)
    def g(args: Sequence[Any]) -> list[Any]:
        return [runnable(item) for item in args]

    g.__tandem_kind__ = "split"          # type: ignore[attr-defined]
    g.__tandem_chunk__ = chunk_size      # type: ignore[attr-defined]
    g.__tandem_original__ = runnable     # type: ignore[attr-defined]
    return g
