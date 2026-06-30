"""
@tandem.compute(batch=1, timeout_ms=50)

Wraps a split-independent function so that calls to it are collected
into a batch. The batch is dispatched (to the executor -- ultimately a
node, once the real backend exists) once EITHER:

  - `batch` calls have been collected, OR
  - `timeout_ms` has elapsed since the first call in the current batch
    arrived

whichever happens first. Every individual call still looks synchronous
to its caller -- `foo(x)` blocks and returns `x * 2` as normal -- the
batching/timeout/dispatch machinery is invisible to call sites; it just
determines how calls get grouped before being handed to the executor.

    @tandem.compute(batch=3, timeout_ms=50)
    def foo(x):
        return x * 2

    foo(1)   # blocks until this call's batch is dispatched:
             #   either 2 more calls arrive within the window, making 3,
             #   or 50ms passes, whichever is first -- then ALL pending
             #   calls in that window are sent to a node together.

The function MUST be split-independent (see validator.py); this is
checked once, eagerly, at decoration time, so violations are caught at
import time rather than at first call.
"""

from __future__ import annotations

import functools
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, TypeVar

from tandem.errors import TandemRuntimeError
from tandem.executor import get_default_executor
from tandem.validator import validate_independence

F = TypeVar("F", bound=Callable[..., Any])


@dataclass
class _PendingCall:
    args: tuple
    kwargs: dict
    result: Any = None
    error: BaseException | None = None
    done: threading.Event = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        self.done = threading.Event()


class _BatchCollector:
    """
    Owns the "current batch" for one decorated function and the timer
    that flushes it. Thread-safe: multiple caller threads may call the
    wrapped function concurrently.
    """

    def __init__(self, func: Callable, batch_size: int, timeout_ms: int) -> None:
        self._func = func
        self._batch_size = max(1, batch_size)
        self._timeout_s = max(0, timeout_ms) / 1000.0
        self._lock = threading.Lock()
        self._pending: list[_PendingCall] = []
        self._timer: threading.Timer | None = None

    def submit(self, args: tuple, kwargs: dict) -> Any:
        call = _PendingCall(args=args, kwargs=kwargs)
        flush_now = False

        with self._lock:
            self._pending.append(call)

            if len(self._pending) == 1:
                # First call in a fresh batch -- start the timeout clock.
                self._start_timer()

            if len(self._pending) >= self._batch_size:
                flush_now = True

        if flush_now:
            self._flush()

        # Block this caller's thread until its result is ready. Other
        # threads' calls into `submit` are not blocked by this wait.
        call.done.wait()

        if call.error is not None:
            raise call.error
        return call.result

    def _start_timer(self) -> None:
        if self._timer is not None:
            self._timer.cancel()
        if self._timeout_s == 0:
            # timeout_ms=0 means "flush immediately", handled by caller
            return
        self._timer = threading.Timer(self._timeout_s, self._on_timeout)
        self._timer.daemon = True
        self._timer.start()

    def _on_timeout(self) -> None:
        self._flush()

    def _flush(self) -> None:
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
            if not self._pending:
                return
            batch = self._pending
            self._pending = []

        executor = get_default_executor()
        call_specs = [(c.args, c.kwargs) for c in batch]
        try:
            results = executor.run_batch(self._func, call_specs)
            if len(results) != len(batch):
                raise TandemRuntimeError(
                    f"Executor returned {len(results)} results for a "
                    f"batch of {len(batch)} calls; result count must "
                    f"match call count, in order."
                )
            for call, result in zip(batch, results):
                call.result = result
                call.done.set()
        except BaseException as e:  # noqa: BLE001 -- propagate to every caller in the batch
            for call in batch:
                call.error = e
                call.done.set()


def compute(batch: int = 1, timeout_ms: int = 50) -> Callable[[F], F]:
    """
    Decorator factory. See module docstring for batching semantics.

    Args:
        batch: number of calls to collect before dispatching as a group.
        timeout_ms: max time to wait for the batch to fill before
            dispatching whatever has been collected so far.

    Raises:
        TandemValidationError: if the decorated function reads any
            global that is not declared `tandem.immutable`, eagerly at
            decoration time.
    """

    def decorator(func: F) -> F:
        validate_independence(func)

        collector = _BatchCollector(func, batch_size=batch, timeout_ms=timeout_ms)

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return collector.submit(args, kwargs)

        wrapper.__tandem_kind__ = "compute"  # type: ignore[attr-defined]
        wrapper.__tandem_batch__ = batch  # type: ignore[attr-defined]
        wrapper.__tandem_timeout_ms__ = timeout_ms  # type: ignore[attr-defined]
        wrapper.__tandem_original__ = func  # type: ignore[attr-defined]
        return wrapper  # type: ignore[return-value]

    return decorator
