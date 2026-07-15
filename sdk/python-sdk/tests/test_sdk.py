from __future__ import annotations

import unittest

import tandem
from tandem.future import ComputeFuture, gather


class ComputeAndSplitLocalTests(unittest.TestCase):
    """A bare call to a compute/split function runs locally. This is what makes
    tasks easy to unit test, and it's what runs inside a node."""

    def test_compute_bare_call_runs_locally(self) -> None:
        @tandem.compute(batch=1, timeout_ms=50)
        def double(x):
            return x * 2

        self.assertEqual(double(21), 42)

    def test_compute_exposes_submit_and_markers(self) -> None:
        @tandem.compute()
        def noop(x):
            return x

        self.assertTrue(callable(noop.submit))
        self.assertEqual(noop.__tandem_kind__, "compute")
        self.assertIs(noop.function, noop.__tandem_original__)

    def test_split_bare_call_maps_locally_in_order(self) -> None:
        def add_three(x):
            return x + 3

        mapped = tandem.split(add_three, chunk=2)
        self.assertEqual(mapped([7, 2, 9]), [10, 5, 12])


class ComputeFutureTests(unittest.TestCase):
    """The future is driven by a poll callable that returns (done, value, error)."""

    def test_result_returns_value_once_done(self) -> None:
        future = ComputeFuture(lambda: (True, 42, None))
        self.assertTrue(future.done())
        self.assertEqual(future.result(), 42)

    def test_result_raises_when_task_failed(self) -> None:
        future = ComputeFuture(lambda: (True, None, "worker blew up"))
        with self.assertRaises(RuntimeError):
            future.result()

    def test_gather_preserves_submit_order(self) -> None:
        futures = [ComputeFuture(lambda value=value: (True, value, None)) for value in (3, 1, 2)]
        self.assertEqual(gather(*futures), [3, 1, 2])

    def test_polls_until_done(self) -> None:
        state = {"checks": 0}

        def poll():
            state["checks"] += 1
            if state["checks"] < 2:
                return (False, None, None)
            return (True, "ready", None)

        future = ComputeFuture(poll)
        self.assertFalse(future.done())  # first check: still pending
        self.assertEqual(future.result(), "ready")


class IndependenceValidationTests(unittest.TestCase):
    """Reading module globals (helpers, imports, constants) is fine -- the
    compiler freezes them in. Mutating shared module state is what's rejected."""

    def test_calling_a_module_helper_is_allowed(self):
        from tandem.validator import validate_independence

        def task(n):
            return some_helper(n) + OFFSET  # noqa: F821 -- free reads are fine now

        validate_independence(task)  # should not raise

    def test_mutating_a_module_global_is_rejected(self):
        from tandem.errors import TandemValidationError
        from tandem.validator import validate_independence

        def task(n):
            accumulator += n  # noqa: F821 -- mutating a shared global is the error
            return accumulator

        with self.assertRaises(TandemValidationError):
            validate_independence(task)


if __name__ == "__main__":
    unittest.main()
