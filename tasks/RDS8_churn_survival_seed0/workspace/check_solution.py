#!/usr/bin/env python3
"""Auto-generated grading script — do not edit by hand."""
import json
import os
import pathlib
import subprocess
import sys

CHECKS = [{'id': 'C1', 'description': 'analysis.py runs without error', 'type': 'script_runs', 'path': 'analysis.py', 'timeout': 120}, {'id': 'C2', 'description': 'Survival analysis or churn prediction method implemented', 'type': 'custom_python', 'code': 'import pathlib\np = pathlib.Path(workspace_dir) / "analysis.py"\npassed = False\ndetail = ""\nmethod_terms = [\n    "kaplan", "km", "survival", "cox", "hazard",\n    "lifelines", "churn", "predict", "classifier",\n    "logistic", "auc", "roc",\n]\nif p.exists():\n    content = p.read_text(encoding="utf-8").lower()\n    found = [t for t in method_terms if t in content]\n    passed = len(found) >= 2\n    detail = f"found method terms: {found}"\nelse:\n    detail = "analysis.py not found"\n'}, {'id': 'C3', 'description': 'Key metric (median_survival_month_to_month) present in results.json', 'type': 'custom_python', 'code': 'import json, pathlib\np = pathlib.Path(workspace_dir) / "results.json"\npassed = False\ndetail = ""\nif p.exists():\n    try:\n        d = json.loads(p.read_text())\n        has_metric = "median_survival_month_to_month" in d\n        passed = has_metric\n        detail = f"median_survival_month_to_month present={has_metric}"\n    except Exception as e:\n        detail = str(e)\nelse:\n    detail = "results.json not found"\n'}, {'id': 'C4', 'description': 'Key columns (tenure, Contract) referenced in analysis.py', 'type': 'custom_python', 'code': 'import pathlib\np = pathlib.Path(workspace_dir) / "analysis.py"\npassed = False\ndetail = ""\nkeywords = [\'tenure\', \'Contract\']\nif p.exists():\n    content = p.read_text(encoding="utf-8").lower()\n    found = [kw for kw in keywords if kw.lower() in content]\n    passed = len(found) == len(keywords)\n    detail = f"found={found}, missing={[kw for kw in keywords if kw.lower() not in content]}"\nelse:\n    detail = "analysis.py not found"\n'}, {'id': 'C5', 'description': 'Group comparison or covariate analysis present in analysis.py', 'type': 'custom_python', 'code': 'import pathlib\np = pathlib.Path(workspace_dir) / "analysis.py"\npassed = False\ndetail = ""\ncomparison_terms = [\n    "groupby", "group_by", "contract", "compare", "covariate",\n    "coefficient", "hazard", "feature_importance", "feature",\n    "log_rank", "logrank",\n]\nif p.exists():\n    content = p.read_text(encoding="utf-8").lower()\n    found = [t for t in comparison_terms if t in content]\n    passed = len(found) >= 1\n    detail = f"found comparison terms: {found}"\nelse:\n    detail = "analysis.py not found"\n'}, {'id': 'C6', 'description': 'Limitations discussed in report.md', 'type': 'custom_python', 'code': 'import pathlib\np = pathlib.Path(workspace_dir) / "report.md"\npassed = False\ndetail = ""\ncaveat_terms = ["limitation", "caveat", "assumption", "bias",\n                "censor", "confound", "selection", "missing"]\nif p.exists():\n    content = p.read_text(encoding="utf-8").lower()\n    found = [t for t in caveat_terms if t in content]\n    passed = len(found) >= 1\n    detail = f"found caveat terms: {found}"\nelse:\n    detail = "report.md not found"\n'}, {'id': 'C7', 'description': 'Data loaded correctly (expected ~1408 rows)', 'type': 'custom_python', 'code': 'import pathlib, csv\np = pathlib.Path(workspace_dir) / "data" / "telco_churn.csv"\npassed = False\ndetail = ""\nexpected_rows = 1408\nif p.exists():\n    with open(p, newline="", encoding="utf-8") as fh:\n        actual = sum(1 for _ in csv.reader(fh)) - 1\n    passed = abs(actual - expected_rows) <= max(5, int(expected_rows * 0.01))\n    detail = f"actual={actual}, expected={expected_rows}"\nelse:\n    detail = "data/telco_churn.csv not found"\n'}, {'id': 'C8', 'description': 'results.json is valid JSON with required fields', 'type': 'custom_python', 'code': 'import json, pathlib\np = pathlib.Path(workspace_dir) / "results.json"\npassed = False\ndetail = ""\nrequired_fields = ["analysis_type", "median_survival_month_to_month", "n_churned", "n_retained"]\nif p.exists():\n    try:\n        d = json.loads(p.read_text(encoding="utf-8"))\n        missing = [f for f in required_fields if f not in d]\n        passed = len(missing) == 0\n        detail = f"missing fields: {missing}" if missing else "all required fields present"\n    except json.JSONDecodeError as e:\n        detail = f"JSON parse error: {e}"\nelse:\n    detail = "results.json not found"\n'}]

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
