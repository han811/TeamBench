#!/usr/bin/env python3
"""Auto-generated grading script — do not edit by hand."""
import json
import os
import pathlib
import subprocess
import sys

CHECKS = [{'id': 'C1', 'description': 'analysis.py runs without error', 'type': 'script_runs', 'path': 'analysis.py', 'timeout': 120}, {'id': 'C2', 'description': 'Missing data pattern analyzed or documented', 'type': 'custom_python', 'code': 'import pathlib\np = pathlib.Path(workspace_dir) / "analysis.py"\npassed = False\ndetail = ""\nmissing_terms = [\n    "missing", "null", "nan", "isna", "isnull",\n    "fillna", "dropna", "impute", "missing_pct",\n    "missing_pattern", "mnar", "mcar", "mar",\n]\nif p.exists():\n    content = p.read_text(encoding="utf-8").lower()\n    found = [t for t in missing_terms if t in content]\n    passed = len(found) >= 2\n    detail = f"missing terms found: {found}"\nelse:\n    detail = "analysis.py not found"\n'}, {'id': 'C3', 'description': 'Country name inconsistencies addressed', 'type': 'custom_python', 'code': 'import pathlib\np = pathlib.Path(workspace_dir) / "analysis.py"\npassed = False\ndetail = ""\nnorm_terms = [\n    "replace", "map", "rename", "normalize", "standardize",\n    "country", "strip", "lower", "alias", "merge", "unify",\n]\nif p.exists():\n    content = p.read_text(encoding="utf-8").lower()\n    has_country = "country" in content\n    found = [t for t in norm_terms if t in content]\n    passed = has_country and len(found) >= 2\n    detail = f"country mentioned={has_country}, norm terms={found}"\nelse:\n    detail = "analysis.py not found"\n'}, {'id': 'C4', 'description': 'Scale anomaly or outlier in under5_mortality detected/handled', 'type': 'custom_python', 'code': 'import pathlib\np = pathlib.Path(workspace_dir) / "analysis.py"\npassed = False\ndetail = ""\nscale_terms = [\n    "outlier", "scale", "anomal", "range", "quantile",\n    "clip", "filter", "inconsisten", "unit", "zscore",\n    "z_score", "iqr", "threshold", "plausible",\n]\ncol = "under5_mortality"\nif p.exists():\n    content = p.read_text(encoding="utf-8").lower()\n    has_col = col.lower() in content\n    found = [t for t in scale_terms if t in content]\n    passed = has_col and len(found) >= 2\n    detail = f"col mentioned={has_col}, scale terms={found}"\nelse:\n    detail = "analysis.py not found"\n'}, {'id': 'C5', 'description': 'Trend analysis produces meaningful output (country/indicator trends)', 'type': 'custom_python', 'code': 'import json, pathlib\nrj = pathlib.Path(workspace_dir) / "results.json"\nrm = pathlib.Path(workspace_dir) / "report.md"\npassed = False\ndetail = ""\nif rj.exists() or rm.exists():\n    trend_terms = [\n        "trend", "increase", "decrease", "improve", "decline",\n        "progress", "change", "over time", "year",\n    ]\n    content = ""\n    if rj.exists():\n        content += rj.read_text(encoding="utf-8").lower()\n    if rm.exists():\n        content += rm.read_text(encoding="utf-8").lower()\n    found = [t for t in trend_terms if t in content]\n    passed = len(found) >= 2\n    detail = f"trend terms found: {found}"\nelse:\n    detail = "neither results.json nor report.md found"\n'}, {'id': 'C6', 'description': 'results.json contains required fields (n_countries, missing_pct)', 'type': 'custom_python', 'code': 'import json, pathlib\np = pathlib.Path(workspace_dir) / "results.json"\npassed = False\ndetail = ""\nrequired = ["n_countries", "missing_pct"]\nalt_keys = {\n    "missing_pct": ["missing_rate", "pct_missing", "missing_fraction"],\n    "n_countries": ["num_countries", "country_count"],\n}\nif p.exists():\n    try:\n        d = json.loads(p.read_text(encoding="utf-8"))\n        missing = []\n        for f in required:\n            alts = alt_keys.get(f, [])\n            if f not in d and not any(a in d for a in alts):\n                missing.append(f)\n        passed = len(missing) == 0\n        detail = f"missing={missing}" if missing else "all fields present"\n    except Exception as e:\n        detail = str(e)\nelse:\n    detail = "results.json not found"\n'}, {'id': 'C7', 'description': 'Data loaded correctly (expected ~92 rows)', 'type': 'custom_python', 'code': 'import pathlib, csv\np = pathlib.Path(workspace_dir) / "data" / "health_indicators.csv"\npassed = False\ndetail = ""\nexpected_rows = 92\nif p.exists():\n    with open(p, newline="", encoding="utf-8") as fh:\n        actual = sum(1 for _ in csv.reader(fh)) - 1\n    passed = abs(actual - expected_rows) <= max(5, int(expected_rows * 0.01))\n    detail = f"actual={actual}, expected={expected_rows}"\nelse:\n    detail = "data/health_indicators.csv not found"\n'}, {'id': 'C8', 'description': 'report.md discusses missing data mechanism', 'type': 'custom_python', 'code': 'import pathlib\np = pathlib.Path(workspace_dir) / "report.md"\npassed = False\ndetail = ""\nmissing_terms = [\n    "missing", "null", "nan", "incomplete", "not reported",\n    "mnar", "mcar", "mar", "imputation", "excluded",\n    "pattern", "mechanism", "bias",\n]\nif p.exists():\n    content = p.read_text(encoding="utf-8").lower()\n    found = [t for t in missing_terms if t in content]\n    passed = len(found) >= 2\n    detail = f"missing data terms found: {found}"\nelse:\n    detail = "report.md not found"\n'}]

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
