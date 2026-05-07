#!/usr/bin/env python3
"""Auto-generated grading script — do not edit by hand."""
import json
import os
import pathlib
import subprocess
import sys

CHECKS = [{'id': 'C1', 'description': 'analysis.py runs without error', 'type': 'script_runs', 'path': 'analysis.py', 'timeout': 120}, {'id': 'C2', 'description': 'Healthcare policy / defunding factor identified', 'type': 'custom_python', 'code': 'import pathlib\npassed = False\ndetail = ""\nterms = ["policy", "healthcare", "hospital", "defund", "budget cut",\n         "health expenditure", "physicians", "health system",\n         "health_expenditure", "medical", "clinic"]\nfor fname in ["analysis.py", "report.md"]:\n    p = pathlib.Path(workspace_dir) / fname\n    if p.exists():\n        content = p.read_text(encoding="utf-8").lower()\n        found = [t for t in terms if t in content]\n        if len(found) >= 2:\n            passed = True\n            detail = f"found in {fname}: {found}"\n            break\nif not passed:\n    detail = "healthcare policy terms not found"\n'}, {'id': 'C3', 'description': 'Conflict / displacement factor identified', 'type': 'custom_python', 'code': 'import pathlib\npassed = False\ndetail = ""\nterms = ["conflict", "war", "armed", "displacement", "refugee",\n         "fatalities", "instability", "insurgency", "civil war",\n         "displaced", "violence"]\nfor fname in ["analysis.py", "report.md"]:\n    p = pathlib.Path(workspace_dir) / fname\n    if p.exists():\n        content = p.read_text(encoding="utf-8").lower()\n        found = [t for t in terms if t in content]\n        if found:\n            passed = True\n            detail = f"found in {fname}: {found}"\n            break\nif not passed:\n    detail = "conflict terms not found"\n'}, {'id': 'C4', 'description': 'Sanctions / economic factor identified', 'type': 'custom_python', 'code': 'import pathlib\npassed = False\ndetail = ""\nterms = ["sanction", "embargo", "trade restriction", "economic",\n         "import", "financial", "gdp", "restriction", "trade_sanction",\n         "trade sanctions"]\nfor fname in ["analysis.py", "report.md"]:\n    p = pathlib.Path(workspace_dir) / fname\n    if p.exists():\n        content = p.read_text(encoding="utf-8").lower()\n        found = [t for t in terms if t in content]\n        if found:\n            passed = True\n            detail = f"found in {fname}: {found}"\n            break\nif not passed:\n    detail = "sanctions/economic terms not found"\n'}, {'id': 'C5', 'description': 'results.json has contributing_factors with >= 2 entries', 'type': 'custom_python', 'code': 'import json, pathlib\np = pathlib.Path(workspace_dir) / "results.json"\npassed = False\ndetail = ""\nif p.exists():\n    try:\n        d = json.loads(p.read_text(encoding="utf-8"))\n        factors = d.get("contributing_factors", [])\n        passed = isinstance(factors, list) and len(factors) >= 2\n        detail = f"contributing_factors={factors}"\n    except Exception as e:\n        detail = str(e)\nelse:\n    detail = "results.json not found"\n'}, {'id': 'C6', 'description': 'report.md identifies a causal timeline connecting factors', 'type': 'custom_python', 'code': 'import pathlib\np = pathlib.Path(workspace_dir) / "report.md"\npassed = False\ndetail = ""\ntimeline_terms = ["timeline", "sequence", "following", "led to",\n                  "resulted in", "caused by", "compound",\n                  "exacerbat", "first", "then", "subsequently",\n                  "period", "between"]\nif p.exists():\n    content = p.read_text(encoding="utf-8").lower()\n    found = [t for t in timeline_terms if t in content]\n    passed = len(found) >= 3\n    detail = f"found timeline terms: {found}"\nelse:\n    detail = "report.md not found"\n'}, {'id': 'C7', 'description': 'Data loaded correctly (expected ~264 rows)', 'type': 'custom_python', 'code': 'import pathlib, csv\np = pathlib.Path(workspace_dir) / "data" / "who_gho.csv"\npassed = False\ndetail = ""\nexpected_rows = 264\nif p.exists():\n    with open(p, newline="", encoding="utf-8") as fh:\n        actual = sum(1 for _ in csv.reader(fh)) - 1\n    passed = abs(actual - expected_rows) <= max(5, int(expected_rows * 0.05))\n    detail = f"actual={actual}, expected={expected_rows}"\nelse:\n    detail = "data/who_gho.csv not found"\n'}, {'id': 'C8', 'description': 'results.json valid JSON with required fields', 'type': 'custom_python', 'code': 'import json, pathlib\np = pathlib.Path(workspace_dir) / "results.json"\npassed = False\ndetail = ""\nrequired = ["contributing_factors", "primary_factor", "life_exp_drop_years"]\nif p.exists():\n    try:\n        d = json.loads(p.read_text(encoding="utf-8"))\n        missing = [f for f in required if f not in d]\n        passed = len(missing) == 0\n        detail = f"missing={missing}" if missing else "all fields present"\n    except json.JSONDecodeError as e:\n        detail = f"JSON error: {e}"\nelse:\n    detail = "results.json not found"\n'}]

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
