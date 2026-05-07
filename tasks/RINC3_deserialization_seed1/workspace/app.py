"""
ConfigLoaderService: Loads user-provided YAML configuration.

WARNING: This code contains an unsafe deserialization vulnerability.
Inspiration: PyYAML yaml.load() RCE — CVE-2017-18342.
"""
import yaml
from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route("/load-config", methods=["POST"])
def load_config():
    """Accept a YAML configuration string and parse it.

    VULNERABLE: yaml.load() with full Loader supports !!python/object tags,
    which can instantiate arbitrary Python objects and execute code.
    """
    data = request.get_json()
    if not data or "config" not in data:
        return jsonify({"error": "missing config"}), 400

    try:
        # VULNERABILITY: yaml.Loader supports !!python/object/apply: os.system
        config = yaml.load(data["config"], Loader=yaml.Loader)
        if not isinstance(config, dict):
            return jsonify({"error": "config must be a YAML mapping"}), 400
        # Only return safe keys
        safe_keys = ["name", "version", "debug", "timeout", "max_retries"]
        result = {k: v for k, v in config.items() if k in safe_keys}
        return jsonify({"loaded": result})
    except yaml.YAMLError as e:
        return jsonify({"error": f"YAML parse error: {e}"}), 400


@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "ConfigLoaderService"})


if __name__ == "__main__":
    app.run(port=5217, debug=False)
