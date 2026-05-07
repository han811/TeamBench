#!/usr/bin/env python3
"""Auto-generated grading script — do not edit by hand."""
import json
import os
import pathlib
import subprocess
import sys

CHECKS = [{'id': 'C1', 'description': 'analysis.py runs without error', 'type': 'script_runs', 'path': 'analysis.py', 'timeout': 120}, {'id': 'C2', 'description': 'Stockout / inventory depletion identified', 'type': 'custom_python', 'code': 'import pathlib\npassed = False\ndetail = ""\nterms = ["stockout", "stock out", "out of stock", "out_of_stock",\n         "inventory", "depleted", "zero stock", "backorder",\n         "unavailable", "sold out", "no stock"]\nfor fname in ["analysis.py", "report.md"]:\n    p = pathlib.Path(workspace_dir) / fname\n    if p.exists():\n        content = p.read_text(encoding="utf-8").lower()\n        found = [t for t in terms if t in content]\n        if found:\n            passed = True\n            detail = f"found in {fname}: {found}"\n            break\nif not passed:\n    detail = "stockout/inventory terms not found"\n'}, {'id': 'C3', 'description': 'Marketing campaign overlap with revenue drop identified', 'type': 'custom_python', 'code': 'import pathlib\npassed = False\ndetail = ""\nterms = ["campaign", "marketing", "promotion", "promotional",\n         "email", "advertisement", "advertis", "marketing_campaign",\n         "campaign running", "campaign was"]\nfor fname in ["analysis.py", "report.md"]:\n    p = pathlib.Path(workspace_dir) / fname\n    if p.exists():\n        content = p.read_text(encoding="utf-8").lower()\n        found = [t for t in terms if t in content]\n        if found:\n            passed = True\n            detail = f"found in {fname}: {found}"\n            break\nif not passed:\n    detail = "campaign/marketing terms not found"\n'}, {'id': 'C4', 'description': 'Counter-intuitive diagnosis: campaign + stockout (not demand failure)', 'type': 'custom_python', 'code': 'import pathlib\npassed = False\ndetail = ""\n# Must connect campaign to stockout as the mechanism\ncombined_terms = [\n    "campaign drove", "campaign increased", "campaign generated",\n    "demand was", "not demand", "sufficient demand", "demand existed",\n    "campaign during", "running during", "despite campaign",\n    "stockout during", "during the campaign", "campaign period",\n    "inventory could not", "supply could not", "unable to fulfill",\n    "inventory shortage", "fulfill demand",\n]\nfor fname in ["analysis.py", "report.md"]:\n    p = pathlib.Path(workspace_dir) / fname\n    if p.exists():\n        content = p.read_text(encoding="utf-8").lower()\n        found = [t for t in combined_terms if t in content]\n        if len(found) >= 1:\n            passed = True\n            detail = f"found in {fname}: {found}"\n            break\nif not passed:\n    detail = "counter-intuitive diagnosis terms not found"\n'}, {'id': 'C5', 'description': 'results.json has root_cause key indicating stockout/inventory', 'type': 'custom_python', 'code': 'import json, pathlib\np = pathlib.Path(workspace_dir) / "results.json"\npassed = False\ndetail = ""\nif p.exists():\n    try:\n        d = json.loads(p.read_text(encoding="utf-8"))\n        root_cause = str(d.get("root_cause", "")).lower()\n        stockout_terms = ["stockout", "stock", "inventory", "out_of_stock",\n                          "supply", "backorder", "depletion"]\n        found = [t for t in stockout_terms if t in root_cause]\n        passed = len(found) > 0\n        detail = f"root_cause=\'{root_cause}\', matched={found}"\n    except Exception as e:\n        detail = str(e)\nelse:\n    detail = "results.json not found"\n'}, {'id': 'C6', 'description': 'report.md quantifies or estimates lost revenue', 'type': 'custom_python', 'code': 'import pathlib, re\np = pathlib.Path(workspace_dir) / "report.md"\npassed = False\ndetail = ""\nif p.exists():\n    content = p.read_text(encoding="utf-8").lower()\n    # Look for currency amounts or percentage loss\n    has_currency = bool(re.search(r\'[£$€]\\s*\\d\', content))\n    has_pct = bool(re.search(r\'\\d+\\s*%\', content))\n    has_revenue_est = any(t in content for t in [\n        "lost revenue", "revenue loss", "estimated loss",\n        "lost sales", "foregone revenue", "missed revenue",\n        "revenue impact", "lost £", "lost $"\n    ])\n    passed = has_currency or has_revenue_est or has_pct\n    detail = f"currency={has_currency}, pct={has_pct}, revenue_est={has_revenue_est}"\nelse:\n    detail = "report.md not found"\n'}, {'id': 'C7', 'description': 'Data loaded correctly (expected ~5000 rows)', 'type': 'custom_python', 'code': 'import pathlib, csv\np = pathlib.Path(workspace_dir) / "data" / "online_retail.csv"\npassed = False\ndetail = ""\nexpected_rows = 5000\nif p.exists():\n    with open(p, newline="", encoding="utf-8") as fh:\n        actual = sum(1 for _ in csv.reader(fh)) - 1\n    passed = abs(actual - expected_rows) <= max(5, int(expected_rows * 0.02))\n    detail = f"actual={actual}, expected={expected_rows}"\nelse:\n    detail = "data/online_retail.csv not found"\n'}, {'id': 'C8', 'description': 'results.json valid JSON with required fields', 'type': 'custom_python', 'code': 'import json, pathlib\np = pathlib.Path(workspace_dir) / "results.json"\npassed = False\ndetail = ""\nrequired = ["root_cause", "campaign_was_running", "recommendation"]\nif p.exists():\n    try:\n        d = json.loads(p.read_text(encoding="utf-8"))\n        missing = [f for f in required if f not in d]\n        passed = len(missing) == 0\n        detail = f"missing={missing}" if missing else "all fields present"\n    except json.JSONDecodeError as e:\n        detail = f"JSON error: {e}"\nelse:\n    detail = "results.json not found"\n'}]

def _run_check(check, workspace_dir):
    ctype = check["type"]
    passed = False
    detail = ""
    try:
        if ctype == "file_exists":
            target = pathlib.Path(workspace_dir) / check["path"]
            passed = target.exists()
            detail = str(target)

        elif ctype == "script_runs":
            script_path = pathlib.Path(workspace_dir) / check["path"]
            timeout = check.get("timeout", 60)
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(workspace_dir),
            )
            passed = result.returncode == 0
            detail = result.stderr.strip()[:500] if result.stderr else ""

        elif ctype == "output_contains":
            target = pathlib.Path(workspace_dir) / check["path"]
            content = target.read_text(encoding="utf-8") if target.exists() else ""
            patterns = check.get("patterns", [])
            missing = [p for p in patterns if p not in content]
            passed = len(missing) == 0
            detail = f"missing patterns: {missing}" if missing else ""

        elif ctype == "value_in_range":
            target = pathlib.Path(workspace_dir) / check["path"]
            data = json.loads(target.read_text(encoding="utf-8"))
            val = data[check["key"]]
            lo = check["min"]
            hi = check["max"]
            passed = lo <= float(val) <= hi
            detail = f"{check['key']}={val} (expected [{lo}, {hi}])"

        elif ctype == "custom_python":
            local_ns = {"workspace_dir": workspace_dir, "passed": False, "detail": ""}
            exec(check["code"], {}, local_ns)  # noqa: S102
            passed = bool(local_ns.get("passed", False))
            detail = str(local_ns.get("detail", ""))

        else:
            detail = f"unknown check type: {ctype}"

    except Exception as exc:  # noqa: BLE001
        passed = False
        detail = f"{type(exc).__name__}: {exc}"

    return passed, detail


def main():
    workspace_dir = pathlib.Path(__file__).parent.resolve()
    reports_dir = workspace_dir.parent / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for check in CHECKS:
        passed, detail = _run_check(check, workspace_dir)
        results.append({
            "id": check["id"],
            "description": check["description"],
            "passed": passed,
            "detail": detail,
        })

    checks_passed = sum(1 for r in results if r["passed"])
    checks_total = len(results)
    primary_success = checks_passed == checks_total
    partial_score = checks_passed / checks_total if checks_total else 0.0
    failure_modes = [
        r["description"] for r in results if not r["passed"]
    ]

    score = {
        "pass": primary_success,
        "primary": {"success": primary_success},
        "secondary": {
            "partial_score": partial_score,
            "checks_passed": checks_passed,
            "checks_total": checks_total,
        },
        "failure_modes": failure_modes,
        "checklist": results,
    }

    score_path = reports_dir / "score.json"
    score_path.write_text(json.dumps(score, indent=2), encoding="utf-8")

    # ── stdout summary ────────────────────────────────────────
    print(f"\nGrading results: {checks_passed}/{checks_total} checks passed")
    print(f"Partial score  : {partial_score:.3f}")
    print(f"Overall pass   : {primary_success}")
    if failure_modes:
        print("\nFailed checks:")
        for fm in failure_modes:
            print(f"  - {fm}")
    print(f"\nScore written to: {score_path}")
    return 0 if primary_success else 1


if __name__ == "__main__":
    raise SystemExit(main())
