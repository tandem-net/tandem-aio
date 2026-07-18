# Tandem SDK guide

This walks through each piece of the SDK: what it's for, when you'd reach for it,
and a small example. If you just want the command list and a quick start, that's
in the [README](README.md).

## The one idea to hold onto

When a task runs on a node, it runs on that node's **own frozen copy** of your
code. Nothing is shared back. So a task can *read* module-level values, but it
can't *change* anything and expect the change to stick anywhere else. You move
data in through arguments and get results back through the return value. Most of
the rules below come straight from this.

There are two ways to actually run tasks:

- `tandem build` then `tandem start` runs every task once with no arguments and
  prints the results. Good for a quick "run it across my machines."
- `.submit()` from your own Python runs one call with real arguments and hands
  you back a result you can wait on. Good when you have inputs and want the
  answers in your program.

---

## `@tandem.compute` — turn a function into a task

**Use it when** you have a slow, self-contained piece of work you'd like to run
on a node (or many nodes) instead of tying up your own machine. Think counting
primes, running a simulation for one set of parameters, or scoring one record.

You write an ordinary function and put the marker on it:

```python
import tandem

@tandem.compute(timeout_ms=10_000)
def count_primes(limit=100_000):
    count = 0
    for n in range(2, limit):
        prime = True
        for d in range(2, int(n ** 0.5) + 1):
            if n % d == 0:
                prime = False
                break
        if prime:
            count += 1
    return count
```

Two things about the options:

- `timeout_ms` is how long the task may run on a node before it's cut off. It
  defaults to **50 milliseconds**, which is fine for something instant but far
  too short for a real loop, so set it yourself whenever your task does actual
  work. The one above gets 10 seconds.
- `batch` is a hint and you can usually ignore it.

Calling it two ways:

```python
count_primes(1000)          # runs right here, in this process
count_primes.submit(1000)   # runs on a node (see the next section)
```

The bare call is handy for testing, and it's exactly what runs inside a node, so
if it works locally it'll work there. Your task can also call plain helper
functions defined in the same file; they get frozen in alongside it.

---

## `.submit()` and `ComputeFuture` — run it on a node and get the answer later

**Use it when** you want the work to happen on a node while your own program
keeps going, and you'll collect the result when you need it.

`.submit()` sends one call and immediately hands back a `ComputeFuture` -- it does
not wait. The future has two methods:

- `future.done()` returns `True` once the result is ready, and never blocks. Use
  it to poll, show progress, or check in without stopping.
- `future.result(timeout=None)` waits for the answer and returns it (or raises if
  the task failed). Pass a `timeout` in seconds so a stuck node can't hang your
  program forever.

```python
import time

future = count_primes.submit(1_000_000)   # returns straight away

while not future.done():                   # get on with other work
    print("still counting...")
    time.sleep(1)

print("there are", future.result(timeout=60), "primes")
```

`.submit()` needs your API key in the environment. Print it once with
`tandem auth login --show-api-key` and `export TANDEM_API_KEY=<key>` before you
run the script.

---

## `tandem.gather()` — wait for a whole batch at once

**Use it when** you've submitted several tasks and you want all the results back
together, in the same order you submitted them, without writing your own wait
loop.

```python
limits = [100_000, 500_000, 1_000_000]

futures = [count_primes.submit(limit) for limit in limits]
counts = tandem.gather(*futures)

for limit, count in zip(limits, counts):
    print(limit, "->", count)
```

`gather` blocks until every future is done and returns a plain list lined up with
your inputs. It's the natural way to fan out a batch and pull it back in.

---

## `tandem.split()` — a parallel map over a list

**Use it when** you have one function that handles a single item and a big list
of items, and you want them spread across your nodes. It's like Python's `map()`,
but the pieces can run on different machines.

You give `split` a function that takes one item, and it hands back a function that
takes the whole list:

```python
def primes_below(limit):
    count = 0
    for n in range(2, limit):
        if all(n % d for d in range(2, int(n ** 0.5) + 1)):
            count += 1
    return count

count_all = tandem.split(primes_below, chunk=4)

count_all([100_000, 200_000, 300_000, 400_000])   # -> a list, in order
```

`chunk` is how many items to hand each node at a time. Bigger chunks mean less
back-and-forth but fewer nodes sharing the load; smaller chunks spread the work
wider. The results always come back in the original order.

A split needs a list to work on, so you call it from your own script (or from
inside a hosted web app). It isn't something `tandem start` can run on its own,
since that runs tasks with no arguments. A bare call runs the map locally, which
is great for checking your logic before you scale it out.

---

## `tandem.Immutable` — a read-only constant your tasks share

**Use it when** several tasks all read the same fixed value -- a rate, a
threshold, a version tag, a small lookup table -- and you want to make clear that
it's shared configuration nobody should be writing to.

```python
TAX_RATE = tandem.Immutable(0.07)

@tandem.compute()
def price_with_tax(subtotal=100.0):
    return round(subtotal * (1 + TAX_RATE.value), 2)
```

You read it with `.value`. Trying to assign to it raises, which is the point: it
turns "oops, I overwrote the config" into an error you catch immediately. (Each
node gets its own frozen copy of the module anyway, so writing to a normal global
wouldn't travel -- `Immutable` just makes that intent obvious and safe.)

---

## `tandem.describe_target()` — see what Tandem found

**Use it when** you want to check what Tandem will actually build before you build
it: which functions it picked up as tasks, whether each is a `compute` or a
`split`, and what parameters they take. Good for a sanity check or a test.

```python
import sys
import tandem

described = tandem.describe_target(sys.modules[__name__])
for task in described.tasks:
    print(task.export_name, task.metadata.kind, task.metadata.parameters)

# count_primes compute ['limit']
# price_with_tax compute ['subtotal']
```

If a function you expected is missing here, it usually means the marker isn't on
it, or it's defined inside another function instead of at the top level.

---

## `TandemValidationError` — why a task got rejected

**You'll see it when** a task does something that can't work under the frozen-copy
model. The classic case is changing a shared global:

```python
counter = 0

@tandem.compute()
def broken(n):
    counter += n        # changing a shared global isn't allowed
    return counter
# raises TandemValidationError right here, when the marker is applied
```

The fix is to stop leaning on shared state -- take what you need as an argument
and return the new value:

```python
@tandem.compute()
def fixed(counter, n):
    return counter + n
```

The same check runs on the function you hand to `tandem.split`. Catch the error
if you want to react to it, or just read the message, which tells you exactly
what it didn't like.

## `TandemBuildError`

Raised when the build itself can't finish (for example, a task references
something that can't be compiled). It's the "something went wrong turning your
code into a runnable task" error, versus `TandemValidationError`, which is "this
task isn't allowed."

---

## Things that trip people up

- **Set `timeout_ms`.** The default is 50 ms. Any real loop needs more or it gets
  cut off partway through.
- **Give parameters defaults if you want `tandem start` to run them.** That path
  calls every task with no arguments. Without a default the task has nothing to
  run with. `.submit()` and `split` don't care, since you pass real values.
- **A `split` needs a list.** Run it from a script or a hosted app, not from a
  bare `tandem start`.
- **`.submit()` needs `TANDEM_API_KEY`.** Get it from
  `tandem auth login --show-api-key`. The `tandem` commands themselves use your
  keyring login and don't need it.
- **Read globals, don't write them.** Tasks each run their own frozen copy of the
  module, so reading module-level values is fine; changing them isn't.
