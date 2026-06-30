"""
tandem.split(runnable, chunk=1) -> g(list[arg]) -> list[result]

Creates a new function `g` from `runnable`. `g` takes a single list of
arguments, splits it into chunks of size `chunk`, dispatches each chunk
(eventually to a different node; for now, to the configured Executor),
and returns a list of results in the SAME ORDER as the input list.

    def foo(x):
        return x + 3

    goo = tandem.split(foo, 5)
    goo([7, 2, 9])  # always == [foo(7), foo(2), foo(9)] == [10, 5, 12]

Unlike @tandem.compute, this is NOT async/batched-over-time -- one call
to `goo(...)` handles its entire input list right now, chunked across
(eventually) multiple nodes, and returns once every chunk has come back.
`runnable` MUST be split-independent (see validator.py); checked eagerly
at the time `tandem.split(...)` is called, not deferred to first use.
"""

from __future__ import annotations

import functools
from typing import Callable, Sequence, TypeVar

from tandem.errors import TandemRuntimeError
from tandem.executor import get_default_executor
from tandem.validator import validate_independence

A = TypeVar("A")
R = TypeVar("R")


def split(runnable: Callable[[A], R], chunk: int = 1) -> Callable[[Sequence[A]], list[R]]:
    """
    Args:
        runnable: a single-purpose, split-independent function taking
            one argument (positional) and returning one result.
        chunk: how many elements of the input list to group together
            per dispatched unit (eventually: per node).

    Returns:
        A function `g(args: list) -> list[result]`, order-preserving.

    Raises:
        TandemValidationError: if `runnable` is not split-independent,
            raised immediately when `split()` is called.
    """
    validate_independence(runnable)
    chunk_size = max(1, chunk)

    @functools.wraps(runnable)
    def g(args: Sequence[A]) -> list[R]:
        args = list(args)
        if not args:
            return []

        chunks: list[list[A]] = [
            args[i : i + chunk_size] for i in range(0, len(args), chunk_size)
        ]

        executor = get_default_executor()
        results: list[R] = []

        # Each chunk is dispatched as its own batch to the executor, and
        # chunks are processed in order, so overall ordering matches the
        # input list exactly -- this is the documented ordering guarantee.
        for c in chunks:
            call_specs = [((item,), {}) for item in c]
            chunk_results = executor.run_batch(runnable, call_specs)
            if len(chunk_results) != len(c):
                raise TandemRuntimeError(
                    f"Executor returned {len(chunk_results)} results for "
                    f"a chunk of {len(c)} inputs; result count must match "
                    f"input count, in order."
                )
            results.extend(chunk_results)

        return results

    g.__tandem_kind__ = "split"  # type: ignore[attr-defined]
    g.__tandem_chunk__ = chunk_size  # type: ignore[attr-defined]
    g.__tandem_original__ = runnable  # type: ignore[attr-defined]
    return g
