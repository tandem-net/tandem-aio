# Tandem Python SDK

Lightweight annotation layer for marking Python functions as
distributable Tandem tasks.

**This SDK does not compile or execute code on a real Tandem cluster.**
That backend (CLI compiler + server + nodes) does not exist yet. What
this SDK gives you today:

- the exact decorator/function surface described in the protocol
- real, enforced static validation of split-independence (the rule that
  a tandemed function may only read its own parameters, locals, or
  values declared `tandem.immutable(...)`)
- real batching (`@tandem.compute`) and chunking (`tandem.split`)
  behavior, including timing semantics, running against a local
  in-process executor
- a pluggable `Executor` interface so the eventual real node-dispatching
  backend can be dropped in later without changing any decorated user
  code

---

## Install

```bash
cd tandem/sdk/python-sdk
pip install -e .
```

or just drop the `tandem/` package directory onto your `PYTHONPATH`.

---

## `@tandem.compute(batch=1, timeout_ms=50)`

Wraps a function so that calls to it are collected into a batch before
being dispatched (eventually to a node; today, to the local executor).
A batch is dispatched as soon as EITHER:

- `batch` calls have been collected, **or**
- `timeout_ms` has elapsed since the first call in the current batch arrived

whichever happens first. Every individual call still blocks and returns
its own result normally — batching is invisible at the call site.

```python
import tandem

@tandem.compute(batch=3, timeout_ms=50)
def foo(x):
    return x * 2
```

`foo(1)` handles up to 3 concurrent calls, or waits at most 50ms, before
sending the whole pending group to a node to compute.

If `batch=1` (the default), every call dispatches immediately — there's
nothing to wait for.

**The function MUST be split-independent.** This is validated *eagerly*,
at decoration time — so a bad function fails at import, not at first
call:

```python
counter = 0

@tandem.compute()
def foo():
    return counter
# tandem.TandemValidationError: global variable 'counter' is not immutable...
```

---

## `tandem.split(runnable, chunk=1) -> g(list[arg]) -> list[result]`

Creates a new function `g` from `runnable`. `g` takes a list of
arguments, splits them into chunks of size `chunk`, dispatches each
chunk (eventually to a node), and returns a list of results. **Order of
results is guaranteed to match the order of the input list.**

```python
def foo(x):
    return x + 3

goo = tandem.split(foo, 5)

goo([7, 2, 9])  # always == [foo(7), foo(2), foo(9)] == [10, 5, 12]
```

Unlike `@tandem.compute`, `tandem.split` is not async-over-time — one
call to `goo(...)` handles its entire input list right now (chunked),
and blocks until every chunk has returned.

`runnable` must be split-independent — validated immediately when
`tandem.split(...)` is called, not deferred until first use:

```python
shared = 0

def bad(x):
    return x + shared

tandem.split(bad, 2)
# tandem.TandemValidationError: global variable 'shared' is not immutable...
```

---

## `tandem.immutable(value)`

Marks a module-level variable as a compile-time constant that tandemed
functions are allowed to read.

```python
NUM = tandem.immutable(67)

@tandem.compute()
def foo(x):
    return NUM + x
```

`foo` is allowed to be tandemed because the variable it reads (`NUM`) is
declared immutable. `NUM` is treated as a compile-time constant once a
real compiler exists; today the SDK freezes the value at the point
`immutable()` is called.

### A note on syntax

The original design sketch shows:

```python
@tandem.immutable
NUM = 67
```

This reads nicely, but **it is not valid Python.** A `@decorator` can
only precede a `def` or `class` statement — there is no object for it to
wrap when it precedes a bare assignment. (Try it: it's a `SyntaxError`.)

A real Tandem CLI could support this exact spelling via a source-level
preprocessing pass (scan for `@tandem.immutable` followed by an
assignment, rewrite it before compiling). Since this SDK has no
compiler, it implements the equivalent semantics using the valid call
form:

```python
NUM = tandem.immutable(67)
```

Both forms are intended to mean the same thing once a preprocessor
exists. Use the call form for now.

### Enforcement

The independence validator enforces, for every tandemed function:

| Read/write | Allowed? |
|---|---|
| Function parameter | ✅ |
| Local variable derived from parameters | ✅ |
| Builtins (`len`, `sum`, etc.) | ✅ |
| Module-level variable declared `tandem.immutable(...)` | ✅ read, ❌ write |
| Any other module-level / outer-scope variable | ❌ |

```python
counter = 0

@tandem.compute()
def foo():
    return counter
# ERROR: global variable 'counter' is not immutable
```

```python
counter = tandem.immutable(0)

@tandem.compute()
def foo():
    counter += 1
    return counter
# ERROR: immutable variable 'counter' cannot be modified
```

This second case is flagged **even without an explicit `global`
keyword** — without `tandem`'s check, plain Python would actually raise
`UnboundLocalError` at runtime (since `counter += 1` implicitly tries to
create a local before any value is bound). The validator catches this
as a static error instead, with a clearer message, before the function
is ever called.

---

## How validation actually works (and its limits)

Validation is implemented as an **AST walk** over each tandemed
function's source (`tandem/validator.py`), not bytecode inspection. It:

- treats function parameters, locals, and comprehension/loop targets as
  bound names
- treats builtins as always allowed
- treats any other `Name` read in `Load` context as a "free" variable —
  allowed only if it's registered via `tandem.immutable(...)` in that
  function's defining module
- treats any `Store`/`AugStore` of an unbound name preceded by `global`
  (or an aug-assign on a name that was never locally bound) as a write
  to outer scope — always an error if the name isn't immutable, and
  *especially* an error if it is

**Known limitations** (the SDK is honest about these — there is no real
compiler yet):

- Only catches **direct** free-variable reads at the AST level. Indirect
  access via `globals()`, `getattr` tricks, `eval`/`exec` is not caught.
- Calls to *other* functions are not transitively validated. If `foo`
  calls `helper()` and `helper` reads a non-immutable global, that's
  only caught if `helper` is *also* decorated/validated separately. Full
  call-graph analysis is a CLI-level concern, not implemented here.
- Functions defined in a REPL or any context where `inspect.getsource`
  can't retrieve source text cannot be validated (you'll get a
  `TandemValidationError` explaining why, rather than a silent pass).

---

## Swapping in a real executor later

All batching/chunking dispatches calls through an `Executor` interface
(`tandem/executor.py`). Today the default is `LocalExecutor`, which just
runs everything in-process, in order. Once the real Tandem server/node
routing backend exists, point the SDK at it with:

```python
import tandem

class RealNodeExecutor(tandem.Executor):
    def run_batch(self, func, calls):
        # ship `func` (or its compiled WASM) + `calls` to the server,
        # get back results in the same order
        ...

tandem.set_default_executor(RealNodeExecutor())
```

No decorated user code needs to change when this happens.

---

## Project layout

```
tandem/sdk/python-sdk/
  tandem/
    __init__.py     # public API surface
    compute.py      # @tandem.compute(batch, timeout_ms)
    split.py        # tandem.split(runnable, chunk)
    immutable.py     # tandem.immutable(value)
    validator.py     # AST-based split-independence checker
    executor.py       # pluggable dispatch backend (LocalExecutor today)
    errors.py         # TandemValidationError, TandemRuntimeError
  tests/
    test_tandem.py    # pytest suite covering all of the above
  pyproject.toml
  README.md
```

## Running the tests

```bash
pip install -e ".[dev]"
pytest tests/ -v
```
