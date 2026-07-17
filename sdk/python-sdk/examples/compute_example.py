"""Tandem compute example -- exercises the compute SDK.

Run it directly to see the local behaviour (no server needed):

    python3 compute_example.py

To run the tasks on real nodes there are two paths.

1) The CLI -- build, deploy, start. `tandem start` runs every @tandem.compute
   task once with its default arguments, so the tasks below have defaults.
   Credentials come from your OS keyring after `tandem auth login`, so there are
   no environment variables to set:

       tandem auth login        # stores credentials in your OS keyring
       tandem node start        # if a node isn't already running
       tandem build             # compile the tasks to .wasm
       tandem deploy            # register a deployment (prints a PID)
       tandem start             # run crunch()/greet() on a node and print results
                                # (tandem start also builds + deploys, so on its
                                #  own it's enough)

2) From Python, with real arguments -- `.submit(...)`. This ships one call and
   hands back a future. `.submit()` reads your API key from TANDEM_API_KEY;
   since `tandem auth login` keeps the key in your keyring (not a .env file),
   print it once and export it (also set TANDEM_SERVER_URL for a non-local
   server):

       tandem auth login --show-api-key    # prints "API key: <key>"
       export TANDEM_API_KEY=<key>
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


# --- plain helper functions -------------------------------------------------
# Tasks may call helper functions defined in the same module -- they get frozen
# in alongside the task.
def _square(x):
    return x * x


def _double(x):
    return x * 2


# --- @tandem.compute --------------------------------------------------------
# Mark a function to run on a node. Give the parameters defaults so the task
# also runs under `tandem start`, which invokes every task once with no
# arguments. timeout_ms is the node's fuel budget -- a loop needs enough of it.
@tandem.compute(batch=1, timeout_ms=5000)
def crunch(n=1000):
    """Sum of squares 0..n-1, scaled by the Immutable SCALE."""
    total = 0
    for i in range(n):
        total += _square(i)
    return total * SCALE.value


@tandem.compute()
def greet(name="world"):
    return f"hello {name} from a tandem node"


def local_demo():
    print("== local execution (a bare call runs right here) ==")
    # A bare call runs locally -- great for testing, and it's exactly what runs
    # inside a node.
    print("  crunch(4)            =", crunch(4))           # (0+1+4+9)*10 = 140
    print("  greet('sam')         =", greet("sam"))

    # tandem.split(fn) returns a callable that applies fn to each item of a list.
    # A bare call just maps locally; the chunk hint is how many items to hand
    # each node when the work is fanned out. A split takes a list as input, so
    # it runs from Python -- not through the no-argument `tandem start` path.
    double_all = tandem.split(_double, chunk=4)
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
            "  (skipped -- run `tandem build`, make sure a node is running, then\n"
            "   export TANDEM_API_KEY from `tandem auth login --show-api-key`; see README.md)"
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
