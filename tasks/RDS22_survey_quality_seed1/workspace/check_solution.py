#!/usr/bin/env python3
"""Auto-generated grading script — do not edit by hand."""
import json
import os
import pathlib
import subprocess
import sys

CHECKS = [{'id': 'C1', 'description': 'analysis.py runs without error', 'type': 'script_runs', 'path': 'analysis.py', 'timeout': 120}, {'id': 'C2', 'description': 'JobSat scale harmonized (consistent numeric encoding)', 'type': 'custom_python', 'code': 'import pathlib\np = pathlib.Path(workspace_dir) / "analysis.py"\npassed = False\ndetail = ""\nscale_terms = [\n    "jobsat", "satisfaction", "map", "replace", "encode",\n    "numeric", "ordinal", "scale", "harmonize", "normalize",\n    "convert", "label", "likert",\n]\nif p.exists():\n    content = p.read_text(encoding="utf-8").lower()\n    has_jobsat = "jobsat" in content\n    found = [t for t in scale_terms if t in content]\n    passed = has_jobsat and len(found) >= 3\n    detail = f"jobsat mentioned={has_jobsat}, terms={found}"\nelse:\n    detail = "analysis.py not found"\n'}, {'id': 'C3', 'description': 'Extreme compensation outliers handled', 'type': 'custom_python', 'code': 'import pathlib\np = pathlib.Path(workspace_dir) / "analysis.py"\npassed = False\ndetail = ""\noutlier_terms = [\n    "outlier", "clip", "quantile", "percentile", "cap",\n    "winsoriz", "compt", "salary", "compTotal", "log",\n    "iqr", "zscore", "z_score", "filter", "threshold",\n]\nif p.exists():\n    content = p.read_text(encoding="utf-8").lower()\n    has_comp = "comptotal" in content or "comp" in content or "salary" in content\n    found = [t for t in outlier_terms if t in content]\n    passed = has_comp and len(found) >= 2\n    detail = f"comp mentioned={has_comp}, terms={found}"\nelse:\n    detail = "analysis.py not found"\n'}, {'id': 'C4', 'description': 'YearsCode / YearsCodePro parsed correctly (strings handled, logical check)', 'type': 'custom_python', 'code': 'import pathlib\np = pathlib.Path(workspace_dir) / "analysis.py"\npassed = False\ndetail = ""\nyears_terms = [\n    "yearscode", "years_code", "years_pro", "yrs",\n    "less than", "more than", "parse", "replace",\n    "extract", "numeric", "int(", "float(",\n]\nif p.exists():\n    content = p.read_text(encoding="utf-8").lower()\n    has_yc = "yearscode" in content\n    found = [t for t in years_terms if t in content]\n    passed = has_yc and len(found) >= 2\n    detail = f"yearscode mentioned={has_yc}, terms={found}"\nelse:\n    detail = "analysis.py not found"\n'}, {'id': 'C5', 'description': 'At least one predictor of satisfaction identified in results.json', 'type': 'custom_python', 'code': 'import json, pathlib\np = pathlib.Path(workspace_dir) / "results.json"\npassed = False\ndetail = ""\nif p.exists():\n    try:\n        d = json.loads(p.read_text(encoding="utf-8"))\n        preds = d.get("top_predictors", d.get("predictors", d.get("features", [])))\n        passed = isinstance(preds, list) and len(preds) >= 1\n        detail = f"top_predictors={preds}"\n    except Exception as e:\n        detail = str(e)\nelse:\n    detail = "results.json not found"\n'}, {'id': 'C6', 'description': 'results.json contains required fields', 'type': 'custom_python', 'code': 'import json, pathlib\np = pathlib.Path(workspace_dir) / "results.json"\npassed = False\ndetail = ""\nrequired = ["top_predictors", "compensation_correlation", "n_valid_responses"]\nalt_keys = {\n    "top_predictors": ["predictors", "features", "important_features"],\n    "compensation_correlation": ["comp_corr", "salary_correlation", "comp_correlation"],\n    "n_valid_responses": ["n_valid", "valid_n", "n_responses"],\n}\nif p.exists():\n    try:\n        d = json.loads(p.read_text(encoding="utf-8"))\n        missing = []\n        for f in required:\n            alts = alt_keys.get(f, [])\n            if f not in d and not any(a in d for a in alts):\n                missing.append(f)\n        passed = len(missing) == 0\n        detail = f"missing={missing}" if missing else "all fields present"\n    except Exception as e:\n        detail = str(e)\nelse:\n    detail = "results.json not found"\n'}, {'id': 'C7', 'description': 'Data loaded correctly (expected ~4000 rows)', 'type': 'custom_python', 'code': 'import pathlib, csv\np = pathlib.Path(workspace_dir) / "data" / "survey_responses.csv"\npassed = False\ndetail = ""\nexpected_rows = 4000\nif p.exists():\n    with open(p, newline="", encoding="utf-8") as fh:\n        actual = sum(1 for _ in csv.reader(fh)) - 1\n    passed = abs(actual - expected_rows) <= max(5, int(expected_rows * 0.01))\n    detail = f"actual={actual}, expected={expected_rows}"\nelse:\n    detail = "data/survey_responses.csv not found"\n'}, {'id': 'C8', 'description': 'report.md discusses a data quality issue discovered', 'type': 'custom_python', 'code': 'import pathlib\np = pathlib.Path(workspace_dir) / "report.md"\npassed = False\ndetail = ""\nquality_terms = [\n    "outlier", "scale", "inconsisten", "missing", "clean",\n    "quality", "parse", "encoding", "salary", "compensation",\n    "yearscode", "satisfaction", "harmonize", "anomal",\n]\nif p.exists():\n    content = p.read_text(encoding="utf-8").lower()\n    found = [t for t in quality_terms if t in content]\n    passed = len(found) >= 2\n    detail = f"quality terms found: {found}"\nelse:\n    detail = "report.md not found"\n'}]

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
