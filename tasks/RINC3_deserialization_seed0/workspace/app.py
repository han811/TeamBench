"""
TaskQueueService: Accepts serialized task objects from clients.

WARNING: This code contains an unsafe deserialization vulnerability.
Inspiration: Python pickle RCE — any class with __reduce__ executes on load.
"""
import pickle
import base64
from flask import Flask, request, jsonify

app = Flask(__name__)


def process_task(task_data: dict) -> dict:
    """Process a deserialized task object."""
    return {"status": "processed", "task_type": task_data.get("type", "unknown")}


@app.route("/submit", methods=["POST"])
def submit_task():
    """Accept a base64-encoded pickled task object.

    VULNERABLE: deserializes untrusted pickle data — RCE possible via __reduce__.
    """
    data = request.get_json()
    if not data or "payload" not in data:
        return jsonify({"error": "missing payload"}), 400

    try:
        raw = base64.b64decode(data["payload"])
        # VULNERABILITY: pickle.loads on untrusted data allows arbitrary code execution
        task = pickle.loads(raw)
        result = process_task(task)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "TaskQueueService"})


if __name__ == "__main__":
    app.run(port=5249, debug=False)
