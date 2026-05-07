#!/usr/bin/env python3
"""Auto-generated grading script — do not edit by hand."""
import json
import os
import pathlib
import subprocess
import sys

CHECKS = [{'id': 'C1', 'description': 'analysis.py runs without error', 'type': 'script_runs', 'path': 'analysis.py', 'timeout': 120}, {'id': 'C2', 'description': 'EDA present in analysis.py (describe/hist/scatter/corr/etc.)', 'type': 'output_contains', 'path': 'analysis.py', 'patterns': ['describe|hist|scatter|boxplot|distribution|summary|corr|head|info|value_counts']}, {'id': 'C3', 'description': 'Missing-value handling present in analysis.py', 'type': 'output_contains', 'path': 'analysis.py', 'patterns': ['fillna|impute|dropna|missing|isnull|isna|SimpleImputer|KNNImputer']}, {'id': 'C4', 'description': 'Uncertainty metric reported in results.json or report.md', 'type': 'custom_python', 'code': 'import pathlib, re\nws = pathlib.Path(workspace_dir)\ntext = ""\nfor fname in ("results.json", "report.md"):\n    p = ws / fname\n    if p.exists():\n        text += p.read_text(encoding="utf-8", errors="ignore")\npatterns = [\'rmse\', \'r2\', \'r2_score\', \'mean_squared_error\', \'mean_absolute_error\', \'score\', \'mse\', \'mae\']\npassed = bool(re.search("|".join(patterns), text, re.IGNORECASE))\ndetail = "uncertainty metric found" if passed else "no uncertainty metric found in results.json or report.md"\n'}, {'id': 'C5', 'description': 'Report documents at least one formal assumption test', 'type': 'custom_python', 'code': 'import pathlib, re\nws = pathlib.Path(workspace_dir)\ntext = ""\nfor fname in ("analysis.py", "results.json", "report.md"):\n    p = ws / fname\n    if p.exists():\n        text += p.read_text(encoding="utf-8", errors="ignore")\npatterns = [\'shapiro|breusch|normality|homoscedasticity|qqplot|q-q|residual\']\npassed = bool(re.search("|".join(patterns), text, re.IGNORECASE))\ndetail = "focus criteria found" if passed else "focus-specific criteria not found in analysis.py / results.json / report.md"\n'}, {'id': 'C6', 'description': 'Random seed set in analysis.py', 'type': 'output_contains', 'path': 'analysis.py', 'patterns': ['random_state|np.random.seed|random.seed|torch.manual_seed|set_seed']}, {'id': 'C7', 'description': 'Outlier handling documented in report.md', 'type': 'custom_python', 'code': 'import pathlib, re\nws = pathlib.Path(workspace_dir)\np = ws / "report.md"\ntext = p.read_text(encoding="utf-8", errors="ignore") if p.exists() else ""\npatterns = [\'outlier\', \'extreme\', \'influential\', \'leverage\', \'clip\', \'winsoriz\', \'cook\', \'zscore\', \'z-score\', \'IQR\', \'iqr\']\npassed = bool(re.search("|".join(patterns), text, re.IGNORECASE))\ndetail = "outlier documentation found" if passed else "no outlier documentation in report.md"\n'}, {'id': 'C8', 'description': 'report.md exists', 'type': 'file_exists', 'path': 'report.md'}]

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
