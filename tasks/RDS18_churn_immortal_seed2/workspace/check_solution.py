#!/usr/bin/env python3
"""Auto-generated grading script — do not edit by hand."""
import json
import os
import pathlib
import subprocess
import sys

CHECKS = [{'id': 'C1', 'description': 'Landmark analysis or survival-aware method present in analysis.py', 'type': 'custom_python', 'code': 'import pathlib\nsrc = (pathlib.Path(workspace_dir) / "analysis.py").read_text(encoding="utf-8")\nsrc_lower = src.lower()\nterms = ["landmark", "survival", "kaplan", "km_", "lifelines",\n         "tenure >=", "tenure>=", "at_risk", "at risk",\n         "reached", "month_12", "month_24", "cohort"]\nfound = [t for t in terms if t in src_lower]\npassed = len(found) >= 1\ndetail = f"landmark/survival terms found: {found}"\n'}, {'id': 'C2', 'description': "results.json contains 'landmark_churn_rates' or 'corrected_churn_rates' key", 'type': 'custom_python', 'code': 'import json, pathlib\nrpath = pathlib.Path(workspace_dir) / "results.json"\nif not rpath.exists():\n    passed = False\n    detail = "results.json not found"\nelse:\n    data = json.loads(rpath.read_text(encoding="utf-8"))\n    keys = set(data.keys())\n    landmark_keys = {"landmark_churn_rates", "corrected_churn_rates",\n                     "landmark_results", "corrected_loyal_churn_rate",\n                     "landmark_loyal_churn_rate"}\n    found_keys = keys & landmark_keys\n    passed = len(found_keys) > 0\n    detail = f"landmark keys found: {found_keys}, all keys: {list(keys)}"\n'}, {'id': 'C3', 'description': 'Corrected loyal churn rate >= 0.1 (immortal bias reduced)', 'type': 'custom_python', 'code': 'import json, pathlib\nrpath = pathlib.Path(workspace_dir) / "results.json"\nif not rpath.exists():\n    passed = False\n    detail = "results.json not found"\nelse:\n    data = json.loads(rpath.read_text(encoding="utf-8"))\n    # Look for corrected/landmark loyal churn rate\n    candidate_keys = [\n        "landmark_loyal_churn_rate", "corrected_loyal_churn_rate",\n        "loyal_churn_rate_corrected", "landmark_churn_rate_loyal"\n    ]\n    rate = None\n    for k in candidate_keys:\n        if k in data:\n            rate = float(data[k])\n            break\n    # Also check nested dicts\n    if rate is None:\n        for k, v in data.items():\n            if isinstance(v, dict):\n                for sk in candidate_keys:\n                    if sk in v:\n                        rate = float(v[sk])\n                        break\n            if rate is not None:\n                break\n    if rate is None:\n        # Fall back: check if loyal_churn_rate increased from biased value\n        rate = float(data.get("loyal_churn_rate", 0.0))\n    passed = rate >= 0.1\n    detail = f"corrected loyal churn rate={rate} (need >= 0.1)"\n'}, {'id': 'C4', 'description': "results.json contains 'n_at_landmark' or 'n_landmark' key", 'type': 'custom_python', 'code': 'import json, pathlib\nrpath = pathlib.Path(workspace_dir) / "results.json"\nif not rpath.exists():\n    passed = False\n    detail = "results.json not found"\nelse:\n    data = json.loads(rpath.read_text(encoding="utf-8"))\n    landmark_n_keys = {"n_at_landmark", "n_landmark", "landmark_n",\n                       "n_landmark_cohort", "n_cohort"}\n    found = {k for k in data if any(lk in k.lower() for lk in\n                                     ["landmark", "cohort", "at_risk"])}\n    passed = len(found) > 0\n    detail = f"landmark N keys found: {found}"\n'}, {'id': 'C5', 'description': 'report.md mentions immortal time bias or landmark analysis', 'type': 'custom_python', 'code': 'import pathlib\nrpath = pathlib.Path(workspace_dir) / "report.md"\nif not rpath.exists():\n    passed = False\n    detail = "report.md not found"\nelse:\n    content = rpath.read_text(encoding="utf-8").lower()\n    keywords = ["immortal", "landmark", "survival", "bias",\n                "guaranteed", "time bias", "survival analysis"]\n    found = [kw for kw in keywords if kw in content]\n    passed = len(found) >= 1\n    detail = f"found keywords: {found}"\n'}, {'id': 'C6', 'description': 'analysis.py runs without error', 'type': 'script_runs', 'path': 'analysis.py', 'timeout': 120}]

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
