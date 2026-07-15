"""Tandem compute example -- exercises every feature of the compute SDK.

Run it directly to see the local behaviour (no server needed):

    python3 compute_example.py

To also see distributed execution on real nodes, build the project and run it
against a Tandem server (see README.md in this folder):

    tandem build
    export TANDEM_SERVER_URL=http://127.0.0.1:6767
    export TANDEM_API_KEY=<your key from `tandem auth login`>
    python3 compute_example.py
"""

import os
import sys

import tandem


# --- tandem.Immutable -------------------------------------------------------
# A read-only wrapper for a module-level constant. The compiler freezes the
# whole module into each task, so tasks can read module globals freely; wrapping
# a constant in Immutable documents that intent and stops anything from mutating
# it by accident.
SCALE = tandem.Immutable(10)


# --- a plain helper function ------------------------------------------------
# Tasks may call helper functions defined in the same module -- they get frozen
# in alongside the task.
def _square(x):
    return x * x


# --- @tandem.compute --------------------------------------------------------
# Mark a function to run on a node. Options are optional; batch and timeout_ms
# are hints (timeout_ms becomes the node's fuel budget).
@tandem.compute(batch=1, timeout_ms=5000)
def crunch(n):
    """Sum of squares 0..n-1, scaled by the Immutable SCALE."""
    total = 0
    for i in range(n):
        total += _square(i)
    return total * SCALE.value


@tandem.compute()
def greet(name):
    return f"hello {name} from a tandem node"


# --- tandem.split -----------------------------------------------------------
# split(fn) returns a callable that applies fn to each item of a list and returns
# the results in order. Called locally it just maps.
def _double(x):
    return x * 2


double_all = tandem.split(_double, chunk=4)


def local_demo():
    print("== local execution (a bare call runs right here) ==")
    # A bare call runs locally -- great for testing, and it's exactly what runs
    # inside a node.
    print("  crunch(4)            =", crunch(4))           # (0+1+4+9)*10 = 140
    print("  greet('sam')         =", greet("sam"))
    print("  double_all([1,2,3])  =", double_all([1, 2, 3]))
    print("  SCALE.value          =", SCALE.value, " repr:", repr(SCALE))

    # Immutable really is read-only.
    try:
        SCALE.value = 99  # type: ignore[misc]
    except AttributeError as exc:
        print("  writing to an Immutable is blocked:", exc)


def introspection_demo():
    print("\n== introspection (describe_target finds the tasks) ==")
    described = tandem.describe_target(sys.modules[__name__])
    for task in described.tasks:
        print(
            f"  - {task.export_name}: kind={task.metadata.kind} "
            f"params={task.metadata.parameters}"
        )


def validation_demo():
    print("\n== validation (mutating shared state is rejected) ==")
    try:

        @tandem.compute()
        def bad(n):
            counter += n  # noqa: F821 -- mutating a module global isn't allowed
            return counter

    except tandem.TandemValidationError as exc:
        print("  rejected as expected:", exc)


def distributed_demo():
    print("\n== distributed execution (.submit / .done / .result / gather) ==")
    if not os.environ.get("TANDEM_API_KEY"):
        print(
            "  (skipped -- run `tandem build` first, make sure a node is running,\n"
            "   and set TANDEM_SERVER_URL + TANDEM_API_KEY; see README.md)"
        )
        return

    # .submit() sends the work to a node and hands back a ComputeFuture right away.
    future = crunch.submit(1000)
    print("  submitted crunch(1000); done() immediately? ->", future.done())
    print("  future.result(timeout=60) ->", future.result(timeout=60))

    # Fire several at once and collect them, in submit order.
    futures = [crunch.submit(n) for n in (10, 100, 1000)]
    print("  gather(...) ->", tandem.gather(*futures))


def main():
    local_demo()
    introspection_demo()
    validation_demo()
    distributed_demo()


if __name__ == "__main__":
    main()
