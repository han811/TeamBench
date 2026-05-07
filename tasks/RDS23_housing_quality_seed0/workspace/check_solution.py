#!/usr/bin/env python3
"""Auto-generated grading script — do not edit by hand."""
import json
import os
import pathlib
import subprocess
import sys

CHECKS = [{'id': 'C1', 'description': 'analysis.py runs without error', 'type': 'script_runs', 'path': 'analysis.py', 'timeout': 180}, {'id': 'C2', 'description': 'Implausible YearBuilt values addressed', 'type': 'custom_python', 'code': 'import pathlib\np = pathlib.Path(workspace_dir) / "analysis.py"\npassed = False\ndetail = ""\nyear_terms = [\n    "yearbuilt", "yearremodadd", "year", "2207", "implausible",\n    "typo", "clip", "filter", "range", "valid", "before",\n    "< 1900", "<1900", "> 2023", ">2023", "remod",\n]\ncol = "YearBuilt".lower()\nif p.exists():\n    content = p.read_text(encoding="utf-8").lower()\n    has_col = col in content\n    found = [t for t in year_terms if t in content]\n    passed = has_col and len(found) >= 2\n    detail = f"col mentioned={has_col}, year terms={found}"\nelse:\n    detail = "analysis.py not found"\n'}, {'id': 'C3', 'description': 'Extreme LotArea outliers addressed', 'type': 'custom_python', 'code': 'import pathlib\np = pathlib.Path(workspace_dir) / "analysis.py"\npassed = False\ndetail = ""\narea_terms = [\n    "outlier", "lotarea", "grlivarea", "area", "sqft",\n    "quantile", "percentile", "clip", "filter", "remove",\n    "iqr", "zscore", "z_score", "threshold", "large",\n]\ncol = "LotArea".lower()\nif p.exists():\n    content = p.read_text(encoding="utf-8").lower()\n    has_col = col in content\n    found = [t for t in area_terms if t in content]\n    passed = has_col and len(found) >= 2\n    detail = f"col mentioned={has_col}, area terms={found}"\nelse:\n    detail = "analysis.py not found"\n'}, {'id': 'C4', 'description': 'Zero-variance or constant features removed', 'type': 'custom_python', 'code': 'import pathlib\np = pathlib.Path(workspace_dir) / "analysis.py"\npassed = False\ndetail = ""\nvariance_terms = [\n    "variance", "constant", "nunique", "unique", "drop",\n    "utilities", "zero_var", "variancethreshold", "low_variance",\n    "single_value", "std()", ".std", "useless", "remove",\n]\nif p.exists():\n    content = p.read_text(encoding="utf-8").lower()\n    found = [t for t in variance_terms if t in content]\n    passed = len(found) >= 2\n    detail = f"variance terms found: {found}"\nelse:\n    detail = "analysis.py not found"\n'}, {'id': 'C5', 'description': 'Model RMSE < $100,000 in results.json', 'type': 'custom_python', 'code': 'import json, pathlib\np = pathlib.Path(workspace_dir) / "results.json"\npassed = False\ndetail = ""\nif p.exists():\n    try:\n        d = json.loads(p.read_text(encoding="utf-8"))\n        rmse = d.get("rmse", d.get("test_rmse", None))\n        if rmse is not None:\n            passed = 0.0 < float(rmse) < 100_000.0\n            detail = f"rmse={rmse}"\n        else:\n            detail = "rmse key not found"\n    except Exception as e:\n        detail = str(e)\nelse:\n    detail = "results.json not found"\n'}, {'id': 'C6', 'description': 'results.json contains required fields (model, rmse, r2)', 'type': 'custom_python', 'code': 'import json, pathlib\np = pathlib.Path(workspace_dir) / "results.json"\npassed = False\ndetail = ""\nrequired = ["model", "rmse", "r2"]\nalt_keys = {\n    "rmse": ["test_rmse", "rmse_score", "root_mean_squared_error"],\n    "r2": ["r2_score", "r_squared", "r_2"],\n}\nif p.exists():\n    try:\n        d = json.loads(p.read_text(encoding="utf-8"))\n        missing = []\n        for f in required:\n            alts = alt_keys.get(f, [])\n            if f not in d and not any(a in d for a in alts):\n                missing.append(f)\n        passed = len(missing) == 0\n        detail = f"missing={missing}" if missing else "all fields present"\n    except Exception as e:\n        detail = str(e)\nelse:\n    detail = "results.json not found"\n'}, {'id': 'C7', 'description': 'Data loaded correctly (expected ~1465 rows)', 'type': 'custom_python', 'code': 'import pathlib, csv\np = pathlib.Path(workspace_dir) / "data" / "housing.csv"\npassed = False\ndetail = ""\nexpected_rows = 1465\nif p.exists():\n    with open(p, newline="", encoding="utf-8") as fh:\n        actual = sum(1 for _ in csv.reader(fh)) - 1\n    passed = abs(actual - expected_rows) <= max(5, int(expected_rows * 0.01))\n    detail = f"actual={actual}, expected={expected_rows}"\nelse:\n    detail = "data/housing.csv not found"\n'}, {'id': 'C8', 'description': 'report.md discusses at least one data quality issue', 'type': 'custom_python', 'code': 'import pathlib\np = pathlib.Path(workspace_dir) / "report.md"\npassed = False\ndetail = ""\nquality_terms = [\n    "outlier", "typo", "year", "area", "constant", "variance",\n    "quality", "clean", "anomal", "invalid", "implausible",\n    "missing", "remove", "filter", "drop",\n]\nif p.exists():\n    content = p.read_text(encoding="utf-8").lower()\n    found = [t for t in quality_terms if t in content]\n    passed = len(found) >= 2\n    detail = f"quality terms found: {found}"\nelse:\n    detail = "report.md not found"\n'}]

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
