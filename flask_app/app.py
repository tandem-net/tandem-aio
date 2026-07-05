from flask import Flask, jsonify
import tandem

app = Flask(__name__)

@tandem.task
def hello_world_task(name: str) -> str:
    """A sample tandem task."""
    return f"Hello {name} from tandem!"

@app.route("/")
def home():
    return jsonify({"status": "running", "message": "Welcome to tandem flask app"})

if __name__ == "__main__":
    app.run(port=5000, debug=True)
