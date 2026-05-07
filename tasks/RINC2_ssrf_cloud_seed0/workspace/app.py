"""
LinkPreviewService: Fetches remote URLs and returns their content.

WARNING: This code contains an SSRF vulnerability for training purposes.
Inspiration: Capital One breach (2019) — SSRF to AWS instance metadata.
"""
import ipaddress
import socket
import urllib.parse
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)
TIMEOUT = 5


def is_safe_url(url: str) -> tuple[bool, str]:
    """Validate that a URL is safe to fetch.

    VULNERABLE: This function is incomplete — it does not block private IP
    ranges or cloud metadata endpoints. An attacker can reach internal
    services and cloud metadata APIs.
    """
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False, "Only http/https allowed"
        # BUG: no check for private/link-local IP ranges
        # BUG: no check for metadata hostnames (e.g. 169.254.169.254)
        return True, ""
    except Exception as e:
        return False, str(e)


@app.route("/fetch")
def fetch_url():
    """Fetch a remote URL and return the response body.

    VULNERABLE: accepts any URL including internal/metadata endpoints.
    """
    url = request.args.get("target", "")
    if not url:
        return jsonify({"error": "missing target parameter"}), 400

    safe, reason = is_safe_url(url)
    if not safe:
        return jsonify({"error": reason}), 400

    try:
        resp = requests.get(url, timeout=TIMEOUT, allow_redirects=False)
        return jsonify({
            "status_code": resp.status_code,
            "content_length": len(resp.text),
            "content": resp.text[:500],
        })
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 502


@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "LinkPreviewService"})


if __name__ == "__main__":
    app.run(port=5149, debug=False)
