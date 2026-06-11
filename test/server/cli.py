import json
import socketserver
import threading


HOST = "127.0.0.1"
PORT = 6767


class AppTestTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, server_address, handler_class):
        super().__init__(server_address, handler_class)
        self.received_bodies = []
        self.received_bodies_lock = threading.Lock()


class AppTestRequestHandler(socketserver.StreamRequestHandler):
    def handle(self):
        raw_body = self.rfile.readline().decode("utf-8").strip()
        if not raw_body:
            self.send_response("error", "empty request")
            return

        try:
            json.loads(raw_body)
        except json.JSONDecodeError as exc:
            self.send_response("error", f"invalid JSON: {exc}")
            return

        with self.server.received_bodies_lock:
            self.server.received_bodies.append(raw_body)
            total_received = len(self.server.received_bodies)

        print(f"Received TCP message from {self.client_address}: {raw_body}")
        self.send_response("ok", f"received message #{total_received}")

    def send_response(self, status, message):
        response_body = json.dumps({
            "status": status,
            "message": message,
        }).encode("utf-8")
        self.wfile.write(response_body + b"\n")


def main():
    server = AppTestTCPServer((HOST, PORT), AppTestRequestHandler)
    print(f"Test server listening for TCP connections on {HOST}:{PORT}")
    print("Send one JSON object followed by a newline to deploy an app")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping test server")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
