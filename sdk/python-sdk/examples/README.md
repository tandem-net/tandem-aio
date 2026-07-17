# Tandem SDK examples

Two small scripts that between them exercise every feature of the Tandem SDK --
compute, web hosting, and the way the two mesh together.

| File | Shows |
|---|---|
| [`compute_example.py`](compute_example.py) | The compute side: `@tandem.compute`, bare (local) calls, `.submit()` / `ComputeFuture` (`.done()`, `.result()`), `tandem.gather`, `tandem.split`, `tandem.Immutable`, `describe_target`, and the validation error you get for mutating shared state. |
| [`web_example.py`](web_example.py) | The web side: a real **Flask** app Tandem hosts on your nodes and load-balances to -- **intermeshed** with compute, because its request handlers reuse the same `@tandem.compute` functions. |

## Compute

Run it directly -- the local parts need no server:

```bash
python3 compute_example.py
```

There are two ways to run the tasks on real nodes.

### Build, deploy, start (the CLI)

`tandem start` runs every `@tandem.compute` task once with its **default**
arguments, so the example's tasks have defaults. Credentials come from your OS
keyring after `tandem auth login` -- there's nothing to put in the environment.
A node has to be running first (`tandem node start`).

```bash
tandem auth login        # stores credentials in your OS keyring
tandem build             # compile the tasks to .wasm
tandem deploy            # register a deployment (prints a PID)
tandem start             # run crunch() and greet() on a node, print results
```

which prints something like:

```
- crunch on node_...
3328335000
- greet on node_...
hello world from a tandem node
```

`tandem start` also builds and deploys, so on its own it's enough.

### From Python, with arguments (`.submit()`)

A bare call like `crunch(5)` runs **locally**; `crunch.submit(5)` runs it on a
**node** and hands back a `ComputeFuture` you await with `.result()` (or collect
many at once with `tandem.gather`).

`.submit()` reads your API key from `TANDEM_API_KEY`. Since `tandem auth login`
stores the key in your keyring rather than a `.env` file, print it once and
export it (add `TANDEM_SERVER_URL` too if your server isn't the local default):

```bash
tandem auth login --show-api-key    # prints "API key: <key>"
export TANDEM_API_KEY=<key>
python3 compute_example.py
```

## Web hosting (intermeshed with compute)

Deploy the app across your nodes, behind Tandem's load balancer (log in first --
`tandem serve` uses your keyring credentials -- and have a node running):

```bash
tandem auth login        # if you haven't already; credentials go in your keyring
tandem serve web.toml
```

`web.toml` has a `[build] install` step (`pip install flask --target libs`) that
`tandem serve` runs before it ships the app -- that's how Flask gets into the
bundle, since the node runs the app with **no network** and can't pip-install
anything itself. Tandem then tars up the project (Flask and all), runs it on your
nodes inside a network-isolated sandbox where it binds the unix socket in
`$TANDEM_SERVE_SOCKET`, and gives you a `/app/<pid>/` URL. Hit it and you'll see
requests spread across nodes:

```
GET /              -> {"app": "tandem flask demo", "served_by": "node_..."}
GET /crunch/1000   -> {"crunch": 3328335000, "served_by": "node_..."}
GET /double        -> {"doubled": [2, 4, 6, 8, 10], "served_by": "node_..."}
```

The `/crunch` and `/double` handlers call the same `@tandem.compute` /
`tandem.split` functions from the compute example -- that's the intermeshing:
one function is usable both as a distributed task and as ordinary code inside a
hosted service. (The serve sandbox has no network of its own, on purpose, so a
hosted app does its compute in-process rather than dispatching it back out.)

Manage what's running with `tandem serve list` and `tandem serve stop <pid>`.

You can also run the web app directly, without Tandem, to poke at it (this one
needs Flask on your machine -- `pip install flask`):

```bash
TANDEM_SERVE_SOCKET=./demo.sock python3 web_example.py &
curl --unix-socket ./demo.sock http://localhost/crunch/1000
```
