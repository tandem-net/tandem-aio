"""
Test suite for the Tandem Python SDK.

Run with:  python -m pytest tests/
or simply: python tests/test_tandem.py
"""

from __future__ import annotations

import sys
import threading
import time

import pytest

import tandem


def test_immutable_read_allowed():
    NUM = tandem.immutable(67)

    @tandem.compute()
    def foo(x):
        return NUM + x

    assert foo(3) == 70


def test_unmarked_global_read_rejected():
    counter = 0  # noqa: F841 -- intentionally referenced only inside foo below

    with pytest.raises(tandem.TandemValidationError):
        @tandem.compute()
        def foo():
            return counter


def test_immutable_mutation_rejected_with_global_keyword():
    counter = tandem.immutable(0)  # noqa: F841

    with pytest.raises(tandem.TandemValidationError):
        @tandem.compute()
        def foo():
            global counter
            counter += 1
            return counter


def test_immutable_mutation_rejected_without_global_keyword():
    counter2 = tandem.immutable(5)  # noqa: F841

    with pytest.raises(tandem.TandemValidationError):
        @tandem.compute()
        def bar():
            counter2 += 1
            return counter2


def test_split_basic_ordering():
    def foo(x):
        return x + 3

    goo = tandem.split(foo, 5)
    assert goo([7, 2, 9]) == [10, 5, 12]


def test_split_chunking_smaller_than_input():
    def double(x):
        return x * 2

    g = tandem.split(double, chunk=2)
    assert g([1, 2, 3, 4, 5]) == [2, 4, 6, 8, 10]


def test_split_empty_input():
    def noop(x):
        return x

    g = tandem.split(noop, chunk=3)
    assert g([]) == []


def test_split_rejects_non_independent_function():
    shared = 0  # noqa: F841

    def bad(x):
        return x + shared

    with pytest.raises(tandem.TandemValidationError):
        tandem.split(bad, 2)


def test_split_preserves_order_with_chunk_one():
    def square(x):
        return x * x

    g = tandem.split(square, chunk=1)
    assert g([1, 2, 3, 4]) == [1, 4, 9, 16]


def test_compute_batch_size_triggers_dispatch_before_timeout():
    @tandem.compute(batch=3, timeout_ms=5000)
    def foo(x):
        return x * 2

    results = {}

    def call(i, x):
        results[i] = foo(x)

    threads = [threading.Thread(target=call, args=(i, i)) for i in range(3)]
    start = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    elapsed = time.time() - start

    assert results == {0: 0, 1: 2, 2: 4}
    assert elapsed < 1.0  # should not have waited for the 5s timeout


def test_compute_timeout_triggers_dispatch_when_batch_not_full():
    @tandem.compute(batch=3, timeout_ms=100)
    def bar(x):
        return x + 100

    start = time.time()
    result = bar(5)
    elapsed = time.time() - start

    assert result == 105
    assert elapsed >= 0.09


def test_compute_default_batch_is_one():
    # Default batch=1 should dispatch immediately, no waiting.
    @tandem.compute()
    def identity(x):
        return x

    start = time.time()
    assert identity(42) == 42
    elapsed = time.time() - start
    assert elapsed < 0.5


def test_local_variables_derived_from_params_allowed():
    @tandem.compute()
    def normalize(values):
        total = sum(values)
        return [v / total for v in values]

    assert normalize([1, 1, 2]) == [0.25, 0.25, 0.5]


def test_list_comprehension_locals_not_flagged_as_free():
    STOP_WORDS = tandem.immutable({"the", "a"})

    @tandem.compute()
    def remove_stop_words(tokens):
        return [t for t in tokens if t not in STOP_WORDS]

    assert remove_stop_words(["the", "cat", "a", "dog"]) == ["cat", "dog"]


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
