#!/usr/bin/env python3
"""Auto-generated grading script — do not edit by hand."""
import json
import os
import pathlib
import subprocess
import sys

CHECKS = [{'id': 'C1', 'description': 'Survivorship filter line removed from analysis.py', 'type': 'custom_python', 'code': 'import pathlib\nsrc = (pathlib.Path(workspace_dir) / "analysis.py").read_text(encoding="utf-8")\nfilter_expr = "df[\'education_num\'] < 10"\npassed = filter_expr not in src\ndetail = "filter expression still present in analysis.py" if not passed else "filter removed"\n'}, {'id': 'C2', 'description': 'Full dataset used: n_rows >= 29304 (90% of original 32561)', 'type': 'custom_python', 'code': 'import json, pathlib\nrpath = pathlib.Path(workspace_dir) / "results.json"\nif not rpath.exists():\n    passed = False\n    detail = "results.json not found"\nelse:\n    data = json.loads(rpath.read_text(encoding="utf-8"))\n    n = data.get("n_rows", 0)\n    passed = int(n) >= 29304\n    detail = f"n_rows={n} (need >= 29304)"\n'}, {'id': 'C3', 'description': "Filter column 'education_num' used as covariate in analysis.py", 'type': 'custom_python', 'code': 'import pathlib, re\nsrc = (pathlib.Path(workspace_dir) / "analysis.py").read_text(encoding="utf-8")\ncol = \'education_num\'\n# Check that the column name appears in the feature lists (not only as a filter)\nin_num = bool(re.search(r"num_features\\s*=\\s*\\[", src) and col in src)\nin_cat = bool(re.search(r"cat_features\\s*=\\s*\\[", src) and col in src)\npassed = bool(in_num or in_cat or (col in src and "feature" in src.lower()))\ndetail = "\'" + col + "\' covariate presence: " + str(passed)\n'}, {'id': 'C4', 'description': "results.json exists and contains 'model_results' key", 'type': 'custom_python', 'code': 'import json, pathlib\nrpath = pathlib.Path(workspace_dir) / "results.json"\nif not rpath.exists():\n    passed = False\n    detail = "results.json not found"\nelse:\n    data = json.loads(rpath.read_text(encoding="utf-8"))\n    passed = "model_results" in data\n    detail = f"keys present: {list(data.keys())}"\n'}, {'id': 'C5', 'description': 'report.md explains survivorship bias (mentions bias/survivor/filter/removed)', 'type': 'custom_python', 'code': 'import pathlib, re\nrpath = pathlib.Path(workspace_dir) / "report.md"\nif not rpath.exists():\n    passed = False\n    detail = "report.md not found"\nelse:\n    content = rpath.read_text(encoding="utf-8").lower()\n    keywords = ["bias", "survivor", "filter", "removed", "exclusion", "subset"]\n    found = [kw for kw in keywords if kw in content]\n    passed = len(found) >= 1\n    detail = f"found keywords: {found}"\n'}, {'id': 'C6', 'description': 'analysis.py runs without error', 'type': 'script_runs', 'path': 'analysis.py', 'timeout': 120}]

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
