"""Tandem web-hosting example -- a real web app, intermeshed with compute.

Tandem hosts this app on your nodes inside a locked-down, network-isolated
sandbox. Instead of a TCP port it binds the unix socket Tandem gives it in
$TANDEM_SERVE_SOCKET; the node proxies HTTP to that socket and the load balancer
spreads traffic across however many nodes run it.

The **intermeshing**: the request handlers reuse the very same
`@tandem.compute` functions you'd otherwise run as distributed tasks. Here they
run locally inside the app -- which is the point: one function, usable as a
distributed compute task *and* as ordinary code inside a hosted web service.
(The serve sandbox has no network by design, so the app does its compute in-
process rather than dispatching it back out.)

Deploy it onto your nodes:

    tandem serve web.toml

Or run it directly for a quick local check (binds ./demo.sock):

    TANDEM_SERVE_SOCKET=./demo.sock python3 web_example.py &
    curl --unix-socket ./demo.sock http://localhost/
    curl --unix-socket ./demo.sock http://localhost/crunch/1000
    curl --unix-socket ./demo.sock http://localhost/double
"""

import http.server
import json
import os
import socketserver

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


class Handler(http.server.BaseHTTPRequestHandler):
    def _send(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parts = [p for p in self.path.split("?")[0].split("/") if p]

        # GET /            -> a greeting plus which node answered
        if not parts:
            return self._send(200, {"app": "tandem web demo", "served_by": NODE})

        # GET /crunch/<n>  -> run the @compute task locally inside the handler
        if len(parts) == 2 and parts[0] == "crunch":
            try:
                n = int(parts[1])
            except ValueError:
                return self._send(400, {"error": "n must be an integer"})
            return self._send(200, {"crunch": crunch(n), "served_by": NODE})

        # GET /double      -> use split() to map over a fixed list
        if parts == ["double"]:
            return self._send(
                200, {"doubled": double_all([1, 2, 3, 4, 5]), "served_by": NODE}
            )

        return self._send(
            404, {"error": "not found", "try": ["/", "/crunch/1000", "/double"]}
        )

    def log_message(self, *args):
        pass


class UnixHTTPServer(socketserver.UnixStreamServer):
    # BaseHTTPRequestHandler expects a (host, port) client address; give it a stub.
    def get_request(self):
        connection, _ = self.socket.accept()
        return connection, ("local", 0)


def main():
    if os.path.exists(SOCKET):
        os.remove(SOCKET)
    print(f"tandem web demo listening on {SOCKET} (node {NODE})")
    UnixHTTPServer(SOCKET, Handler).serve_forever()


if __name__ == "__main__":
    main()
