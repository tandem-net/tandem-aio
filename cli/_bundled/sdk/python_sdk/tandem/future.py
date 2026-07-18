"""Futures for compute work running on nodes.

Calling a ``@tandem.compute`` function normally just runs it locally. Calling
``.submit(...)`` sends the work to a node and hands you back a ``ComputeFuture``
right away, so you can fire off many at once and collect the answers when you
actually need them:

    future = crunch.submit(10_000_000)   # returns immediately
    future.done()                        # a single non-blocking check
    value = future.result(timeout=30)    # blocks until the node answers

    results = tandem.gather(*[crunch.submit(n) for n in sizes])  # in submit order
"""

from __future__ import annotations

import time
from typing import Any, Callable

# How long to wait between polls while blocking on a result. Short enough to feel
# responsive, long enough not to hammer the server.
_POLL_INTERVAL_SECONDS = 0.5


class ComputeFuture:
    """A handle to one piece of work running on a node.

    The rpc layer hands us a ``poll`` callable that does a single, non-blocking
    check and returns ``(done, value, error)``. We cache the outcome the first
    time it comes back so repeated ``.result()`` calls are cheap.
    """

    def __init__(self, poll: Callable[[], tuple[bool, Any, str | None]]) -> None:
        self._poll = poll
        self._done = False
        self._value: Any = None
        self._error: str | None = None

    def done(self) -> bool:
        """Check once, without blocking, whether the result is ready yet."""
        self._check_once()
        return self._done

    def result(self, timeout: float | None = None) -> Any:
        """Wait for the node to finish and return its result.

        Raises ``TimeoutError`` if a ``timeout`` (in seconds) is given and passes,
        or ``RuntimeError`` if the task itself failed.
        """
        deadline = None if timeout is None else time.monotonic() + timeout

        while not self._done:
            self._check_once()
            if self._done:
                break
            if deadline is not None and time.monotonic() >= deadline:
                raise TimeoutError(
                    f"compute task did not finish within {timeout} seconds"
                )
            time.sleep(_POLL_INTERVAL_SECONDS)

        if self._error is not None:
            raise RuntimeError(self._error)
        return self._value

    def _check_once(self) -> None:
        if self._done:
            return
        is_done, value, error = self._poll()
        if is_done:
            self._done = True
            self._value = value
            self._error = error


def gather(*futures: ComputeFuture) -> list[Any]:
    """Wait for several futures and return their results in the order given."""
    return [future.result() for future in futures]
