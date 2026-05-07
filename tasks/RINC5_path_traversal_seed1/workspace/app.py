"""
StaticFileServer: Serves files from the 'static/' directory.

WARNING: This code contains a path traversal vulnerability.
Inspiration: CWE-22 Path Traversal — one of the most common file-serving bugs.
"""
import os
from flask import Flask, request, send_file, jsonify, abort

app = Flask(__name__)
BASE_DIR = os.path.abspath("static")


def resolve_file_path(filename: str) -> str:
    """Resolve a filename to an absolute path within BASE_DIR.

    VULNERABLE: does not check that the resolved path stays within BASE_DIR.
    An attacker can use ../ sequences to escape the base directory.
    """
    # VULNERABILITY: os.path.join with an absolute path or ../ sequences
    # can escape BASE_DIR entirely
    path = os.path.join(BASE_DIR, filename)
    # NOTE: no realpath() normalization, no prefix check
    return path


@app.route("/serve")
def download_file():
    """Download a file by name from the static/ directory."""
    filename = request.args.get("file", "")
    if not filename:
        return jsonify({"error": "missing file parameter"}), 400

    try:
        file_path = resolve_file_path(filename)
        if not os.path.isfile(file_path):
            return jsonify({"error": "file not found"}), 404
        return send_file(file_path)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/list")
def list_files():
    """List available files in the base directory."""
    if not os.path.isdir(BASE_DIR):
        return jsonify({"files": []})
    files = [f for f in os.listdir(BASE_DIR) if os.path.isfile(os.path.join(BASE_DIR, f))]
    return jsonify({"files": files, "base_dir": "static"})


@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "StaticFileServer"})


if __name__ == "__main__":
    app.run(port=5417, debug=False)
