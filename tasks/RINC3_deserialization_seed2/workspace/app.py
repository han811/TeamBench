"""
ExpressionEvalService: Evaluates user-provided Python literal expressions.

WARNING: This code contains a code injection vulnerability.
Inspiration: eval() on untrusted input — a classic RCE vector.
"""
from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route("/evaluate", methods=["POST"])
def evaluate_expression():
    """Evaluate a Python expression (intended for literals like lists/dicts).

    VULNERABLE: eval() executes arbitrary Python code, not just literals.
    An attacker can call __import__('os').system('...') etc.
    """
    data = request.get_json()
    if not data or "expr" not in data:
        return jsonify({"error": "missing expr"}), 400

    expression = data["expr"]
    try:
        # VULNERABILITY: eval() executes arbitrary code
        result = eval(expression)
        return jsonify({"result": repr(result), "type": type(result).__name__})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "ExpressionEvalService"})


if __name__ == "__main__":
    app.run(port=5207, debug=False)
