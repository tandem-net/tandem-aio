import html
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class AppTestRequestHandler(BaseHTTPRequestHandler):
    posted_bodies = []

    def render_page(self):
        entries = "".join(
            f"<pre>{html.escape(body)}</pre>" for body in self.posted_bodies
        )
        return f"""<!doctype html>
<html>
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>person-b test server</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 40px; }}
      pre {{ background: #f5f5f5; padding: 12px; border-radius: 8px; overflow-x: auto; }}
    </style>
  </head>
  <body>
    <h1>Hello World</h1>
    <p>POST JSON to this server and the raw body will appear below.</p>
    <h2>Received JSON</h2>
    {entries if entries else '<p>No POST requests received yet.</p>'}
  </body>
</html>"""

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length).decode("utf-8") if content_length else ""

        self.posted_bodies.append(raw_body or "{}")
        print(f"Received POST on {self.path}: {raw_body}")

        response_body = self.render_page().encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(response_body)))
        self.end_headers()
        self.wfile.write(response_body)

    def do_GET(self):
        if self.path == "/health":
            response_body = json.dumps({"status": "ok"}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response_body)))
            self.end_headers()
            self.wfile.write(response_body)
            return

        response_body = self.render_page().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(response_body)))
        self.end_headers()
        self.wfile.write(response_body)

    def log_message(self, format, *args):
        return


def main():
    server = ThreadingHTTPServer(("localhost", 6767), AppTestRequestHandler)
    print("Test server listening on http://localhost:6767")
    print("Open / for the page and POST JSON to append raw bodies to it")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping test server")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()