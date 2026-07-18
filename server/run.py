from app import create_app

app = create_app()

# threaded=True so the load balancer and node long-polls (which block on Redis
# while waiting for a request or a response) don't stall the whole server.
app.run("0.0.0.0", port=6767, threaded=True)
