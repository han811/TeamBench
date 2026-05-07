#!/usr/bin/env python3
"""Auto-generated grading script — do not edit by hand."""
import json
import os
import pathlib
import subprocess
import sys

CHECKS = [{'id': 'C1', 'description': 'analysis.py runs without error', 'type': 'script_runs', 'path': 'analysis.py', 'timeout': 180}, {'id': 'C2', 'description': 'emp_length converted to numeric (not used as raw string in model)', 'type': 'custom_python', 'code': 'import pathlib, re\np = pathlib.Path(workspace_dir) / "analysis.py"\npassed = False\ndetail = ""\nnumeric_terms = [\n    "int(", "float(", "replace", "extract", "str.replace",\n    "to_numeric", "astype", "parse", "map", "apply",\n    "strip", "split", "years", "numeric",\n]\nif p.exists():\n    content = p.read_text(encoding="utf-8").lower()\n    # check emp_length is mentioned AND some numeric conversion nearby\n    has_emp = "emp_length" in content\n    has_conv = any(t in content for t in numeric_terms)\n    passed = has_emp and has_conv\n    detail = f"emp_length mentioned={has_emp}, conversion term found={has_conv}"\nelse:\n    detail = "analysis.py not found"\n'}, {'id': 'C3', 'description': 'Outliers in annual_inc addressed (clipping, removal, or log transform)', 'type': 'custom_python', 'code': 'import pathlib\np = pathlib.Path(workspace_dir) / "analysis.py"\npassed = False\ndetail = ""\noutlier_terms = [\n    "clip", "outlier", "quantile", "percentile", "log",\n    "9999999", "cap", "winsoriz", "iqr", "zscore", "z_score",\n    "annual_inc",\n]\nif p.exists():\n    content = p.read_text(encoding="utf-8").lower()\n    has_inc = "annual_inc" in content\n    found_terms = [t for t in outlier_terms if t in content]\n    passed = has_inc and len(found_terms) >= 2\n    detail = f"annual_inc mentioned={has_inc}, terms={found_terms}"\nelse:\n    detail = "analysis.py not found"\n'}, {'id': 'C4', 'description': 'purpose column cleaned (consistent values, typo/case handled)', 'type': 'custom_python', 'code': 'import pathlib\np = pathlib.Path(workspace_dir) / "analysis.py"\npassed = False\ndetail = ""\nclean_terms = [\n    "lower", "strip", "replace", "map", "str.", "clean",\n    "purpose", "consolidat", "normalize", "standardize",\n]\nif p.exists():\n    content = p.read_text(encoding="utf-8").lower()\n    has_purpose = "purpose" in content\n    found = [t for t in clean_terms if t in content]\n    passed = has_purpose and len(found) >= 2\n    detail = f"purpose mentioned={has_purpose}, clean terms={found}"\nelse:\n    detail = "analysis.py not found"\n'}, {'id': 'C5', 'description': 'Model AUC > 0.5 reported in results.json', 'type': 'custom_python', 'code': 'import json, pathlib\np = pathlib.Path(workspace_dir) / "results.json"\npassed = False\ndetail = ""\nif p.exists():\n    try:\n        d = json.loads(p.read_text(encoding="utf-8"))\n        auc = d.get("auc_roc", d.get("auc", d.get("roc_auc", None)))\n        if auc is not None:\n            passed = float(auc) > 0.5\n            detail = f"auc_roc={auc}"\n        else:\n            detail = "auc_roc key not found in results.json"\n    except Exception as e:\n        detail = str(e)\nelse:\n    detail = "results.json not found"\n'}, {'id': 'C6', 'description': 'results.json contains required fields (model, auc_roc, accuracy)', 'type': 'custom_python', 'code': 'import json, pathlib\np = pathlib.Path(workspace_dir) / "results.json"\npassed = False\ndetail = ""\nrequired = ["model", "auc_roc", "accuracy"]\nalt_keys = {"auc_roc": ["auc", "roc_auc", "auc_score"]}\nif p.exists():\n    try:\n        d = json.loads(p.read_text(encoding="utf-8"))\n        missing = []\n        for f in required:\n            alts = alt_keys.get(f, [])\n            if f not in d and not any(a in d for a in alts):\n                missing.append(f)\n        passed = len(missing) == 0\n        detail = f"missing={missing}" if missing else "all fields present"\n    except Exception as e:\n        detail = str(e)\nelse:\n    detail = "results.json not found"\n'}, {'id': 'C7', 'description': 'Data loaded correctly (expected ~2000 rows)', 'type': 'custom_python', 'code': 'import pathlib, csv\np = pathlib.Path(workspace_dir) / "data" / "loans.csv"\npassed = False\ndetail = ""\nexpected_rows = 2000\nif p.exists():\n    with open(p, newline="", encoding="utf-8") as fh:\n        actual = sum(1 for _ in csv.reader(fh)) - 1\n    passed = abs(actual - expected_rows) <= max(5, int(expected_rows * 0.01))\n    detail = f"actual={actual}, expected={expected_rows}"\nelse:\n    detail = "data/loans.csv not found"\n'}, {'id': 'C8', 'description': 'report.md discusses at least one data quality issue', 'type': 'custom_python', 'code': 'import pathlib\np = pathlib.Path(workspace_dir) / "report.md"\npassed = False\ndetail = ""\nquality_terms = [\n    "missing", "outlier", "null", "nan", "inconsistent",\n    "clean", "quality", "typo", "encoding", "parsing",\n    "emp_length", "annual_inc", "purpose", "duplicate",\n]\nif p.exists():\n    content = p.read_text(encoding="utf-8").lower()\n    found = [t for t in quality_terms if t in content]\n    passed = len(found) >= 2\n    detail = f"quality terms found: {found}"\nelse:\n    detail = "report.md not found"\n'}]

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
