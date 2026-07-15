# Tandem SDK examples

Two small scripts that between them exercise every feature of the Tandem SDK --
compute, web hosting, and the way the two mesh together.

| File | Shows |
|---|---|
| [`compute_example.py`](compute_example.py) | The compute side: `@tandem.compute`, bare (local) calls, `.submit()` / `ComputeFuture` (`.done()`, `.result()`), `tandem.gather`, `tandem.split`, `tandem.Immutable`, `describe_target`, and the validation error you get for mutating shared state. |
| [`web_example.py`](web_example.py) | The web side: a real HTTP app Tandem hosts on your nodes and load-balances to -- **intermeshed** with compute, because its request handlers reuse the same `@tandem.compute` functions. |

## Compute

Run it directly -- the local parts need no server:

```bash
python3 compute_example.py
```

To see distributed execution on real nodes as well, build the project and point
it at a running Tandem server (a node must be running -- `tandem node start`):

```bash
tandem build
export TANDEM_SERVER_URL=http://127.0.0.1:6767
export TANDEM_API_KEY=$(tandem auth login >/dev/null; echo "$TANDEM_API_KEY")  # or set it by hand
python3 compute_example.py
```

A bare call like `crunch(5)` runs **locally**; `crunch.submit(5)` runs it on a
**node** and hands back a `ComputeFuture` you await with `.result()` (or collect
many at once with `tandem.gather`).

## Web hosting (intermeshed with compute)

Deploy the app across your nodes, behind Tandem's load balancer:

```bash
tandem serve web.toml
```

Tandem tars up the project, runs it on your nodes inside a network-isolated
sandbox (the app binds the unix socket in `$TANDEM_SERVE_SOCKET`), and gives you
a `/app/<pid>/` URL. Hit it and you'll see requests spread across nodes:

```
GET /              -> {"app": "tandem web demo", "served_by": "node_..."}
GET /crunch/1000   -> {"crunch": 3328335000, "served_by": "node_..."}
GET /double        -> {"doubled": [2, 4, 6, 8, 10], "served_by": "node_..."}
```

The `/crunch` and `/double` handlers call the same `@tandem.compute` /
`tandem.split` functions from the compute example -- that's the intermeshing:
one function is usable both as a distributed task and as ordinary code inside a
hosted service. (The serve sandbox has no network of its own, on purpose, so a
hosted app does its compute in-process rather than dispatching it back out.)

You can also run the web app directly, without Tandem, to poke at it:

```bash
TANDEM_SERVE_SOCKET=./demo.sock python3 web_example.py &
curl --unix-socket ./demo.sock http://localhost/crunch/1000
```
