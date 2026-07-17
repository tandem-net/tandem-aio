"""Tandem web-hosting example -- a real Flask app, intermeshed with compute.

Tandem hosts this app on your nodes inside a locked-down, network-isolated
sandbox. Instead of a TCP port it binds the unix socket Tandem gives it in
$TANDEM_SERVE_SOCKET; the node proxies HTTP to that socket and the load balancer
spreads traffic across however many nodes run it.

Two things are worth calling out because they're what makes Flask work here:

  1. No network on the node. So Flask can't be pip-installed at run time -- it
     has to travel inside the bundle. web.toml has a [build] install step
     (`pip install flask --target libs`) that `tandem serve` runs for you before
     it ships the app, dropping Flask into ./libs. We add that folder to the
     import path below, before importing Flask.

  2. No TCP port. A normal Flask app calls app.run() and listens on a port.
     Here we hand the app to Werkzeug's run_simple() bound to a `unix://` socket
     instead -- the one Tandem put in $TANDEM_SERVE_SOCKET.

The **intermeshing**: the request handlers reuse the very same
`@tandem.compute` functions you'd otherwise run as distributed tasks. Here they
run locally inside the app -- one function, usable as a distributed compute task
*and* as ordinary code inside a hosted web service. (The serve sandbox has no
network by design, so the app does its compute in-process rather than dispatching
it back out.)

Deploy it onto your nodes (log in first -- `tandem serve` uses your OS-keyring
credentials -- and have a node running):

    tandem auth login        # stores credentials in your OS keyring
    tandem serve web.toml

Or run it directly for a quick local check (needs Flask on your machine, e.g.
`pip install flask`, then it binds ./demo.sock):

    TANDEM_SERVE_SOCKET=./demo.sock python3 web_example.py &
    curl --unix-socket ./demo.sock http://localhost/
    curl --unix-socket ./demo.sock http://localhost/crunch/1000
    curl --unix-socket ./demo.sock http://localhost/double
"""

import os
import sys

# The node runs this app with its own bare Python and no network, so our
# dependencies ride along inside the bundle. `tandem serve` runs the [build]
# install step from web.toml, which puts Flask in ./libs -- add that to the
# import path before we import it.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "libs"))

from flask import Flask, jsonify
from werkzeug.serving import run_simple

import tandem

SOCKET = os.environ.get("TANDEM_SERVE_SOCKET", "./demo.sock")
NODE = os.environ.get("TANDEM_NODE_ID", "local")

# The same compute building blocks as the compute example -- a constant marked
# immutable, a helper, a @compute task, and a split.
SCALE = tandem.Immutable(10)


def _square(x):
    return x * x


@tandem.compute(timeout_ms=5000)
def crunch(n):
    total = 0
    for i in range(n):
        total += _square(i)
    return total * SCALE.value


def _double(x):
    return x * 2


double_all = tandem.split(_double, chunk=8)


# A normal Flask app -- the only unusual part is how we start it, down in main().
app = Flask(__name__)


@app.route("/")
def index():
    # A greeting plus which node answered, so you can see the load balancer
    # spreading traffic when more than one node is serving.
    return jsonify({"app": "tandem flask demo", "served_by": NODE})


@app.route("/crunch/<int:n>")
def do_crunch(n):
    # Run the @compute task locally, right inside the request handler.
    return jsonify({"crunch": crunch(n), "served_by": NODE})


@app.route("/double")
def do_double():
    # Use split() to map over a fixed list.
    return jsonify({"doubled": double_all([1, 2, 3, 4, 5]), "served_by": NODE})


def main():
    # Clear any leftover socket from a previous run so we can bind cleanly, then
    # serve on the unix socket Tandem handed us instead of a TCP port. threaded
    # lets a slow request not hold up the next one.
    if os.path.exists(SOCKET):
        os.remove(SOCKET)
    print(f"tandem flask demo listening on {SOCKET} (node {NODE})")
    run_simple(f"unix://{SOCKET}", 0, app, threaded=True)


if __name__ == "__main__":
    main()
