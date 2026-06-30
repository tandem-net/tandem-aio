"""
Executor abstraction.

The real Tandem server/node routing layer does not exist yet. This
module defines the interface the SDK dispatches batched/chunked calls
through, plus a `LocalExecutor` default implementation that just runs
the calls in-process. This keeps `@tandem.compute` and `tandem.split`
fully usable today, and gives a single seam to swap in real
network-based node dispatch later without changing any decorated user
code.
"""

from __future__ import annotations

import abc
from typing import Any, Callable, Sequence


class Executor(abc.ABC):
    """
    Interface a Tandem executor backend must implement.

    `run_batch` receives the *validated, split-independent* function and
    a list of (args, kwargs) call specs, and must return a list of
    results in the SAME ORDER as the input call specs. This ordering
    guarantee is required by both @tandem.compute batching and
    tandem.split chunking.
    """

    @abc.abstractmethod
    def run_batch(
        self,
        func: Callable,
        calls: Sequence[tuple[tuple, dict]],
    ) -> list[Any]:
        """Execute `func` once per (args, kwargs) pair in `calls`, in order."""
        raise NotImplementedError


class LocalExecutor(Executor):
    """
    Default executor: runs everything in-process, synchronously, in
    call order. Used until a real node-dispatching executor exists.

    This is intentionally simple -- no real "node" exists locally to
    contact, so this is a faithful stand-in for "send this batch to a
    node and get results back in order".
    """

    def run_batch(
        self,
        func: Callable,
        calls: Sequence[tuple[tuple, dict]],
    ) -> list[Any]:
        results = []
        for args, kwargs in calls:
            results.append(func(*args, **kwargs))
        return results


_default_executor: Executor = LocalExecutor()


def set_default_executor(executor: Executor) -> None:
    """
    Swap the executor used by @tandem.compute / tandem.split. This is
    the seam a future networked executor (one that actually talks to the
    Tandem server and routes to nodes) will plug into.
    """
    global _default_executor
    _default_executor = executor


def get_default_executor() -> Executor:
    return _default_executor
