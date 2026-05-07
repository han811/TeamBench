#!/usr/bin/env python3
"""Auto-generated grading script — do not edit by hand."""
import json
import os
import pathlib
import subprocess
import sys

CHECKS = [{'id': 'C1', 'description': "Post-event features ['SaleCondition', 'MoSold', 'YrSold'] absent from feature list in analysis.py", 'type': 'custom_python', 'code': 'import pathlib, ast\nsrc = (pathlib.Path(workspace_dir) / "analysis.py").read_text(encoding="utf-8")\nleaky = [\'SaleCondition\', \'MoSold\', \'YrSold\']\nstill_present = [f for f in leaky if f in src\n                 and "remove" not in src.lower().split(f)[0][-50:]]\n# Accept if none of the leaky features appear in a feature list context\nin_feature_list = []\nfor feat in leaky:\n    # Check if the feature appears in a list-like structure (not just a comment)\n    lines_with_feat = [l.strip() for l in src.splitlines()\n                       if feat in l and not l.strip().startswith("#")]\n    if any(\'"\' + feat + \'"\' in l or "\'" + feat + "\'" in l\n           for l in lines_with_feat):\n        in_feature_list.append(feat)\npassed = len(in_feature_list) == 0\ndetail = f"post-event features still in feature lists: {in_feature_list}"\n'}, {'id': 'C2', 'description': "results.json exists with 'r2' key", 'type': 'custom_python', 'code': 'import json, pathlib\nrpath = pathlib.Path(workspace_dir) / "results.json"\nif not rpath.exists():\n    passed = False\n    detail = "results.json not found"\nelse:\n    data = json.loads(rpath.read_text(encoding="utf-8"))\n    passed = "r2" in data\n    detail = f"keys present: {list(data.keys())}"\n'}, {'id': 'C3', 'description': 'R² in results.json <= 0.9 (leakage removed)', 'type': 'custom_python', 'code': 'import json, pathlib\nrpath = pathlib.Path(workspace_dir) / "results.json"\nif not rpath.exists():\n    passed = False\n    detail = "results.json not found"\nelse:\n    data = json.loads(rpath.read_text(encoding="utf-8"))\n    r2 = data.get("r2", 1.0)\n    passed = float(r2) <= 0.9\n    detail = f"r2={r2} (need <= 0.9)"\n'}, {'id': 'C4', 'description': "results.json contains 'n_features' key", 'type': 'custom_python', 'code': 'import json, pathlib\nrpath = pathlib.Path(workspace_dir) / "results.json"\nif not rpath.exists():\n    passed = False\n    detail = "results.json not found"\nelse:\n    data = json.loads(rpath.read_text(encoding="utf-8"))\n    passed = "n_features" in data\n    detail = f"n_features={data.get(\'n_features\', \'missing\')}"\n'}, {'id': 'C5', 'description': 'report.md mentions leakage or post-event features', 'type': 'custom_python', 'code': 'import pathlib\nrpath = pathlib.Path(workspace_dir) / "report.md"\nif not rpath.exists():\n    passed = False\n    detail = "report.md not found"\nelse:\n    content = rpath.read_text(encoding="utf-8").lower()\n    keywords = ["leakage", "leak", "post-event", "post event",\n                "sale condition", "removed", "future information"]\n    found = [kw for kw in keywords if kw in content]\n    passed = len(found) >= 1\n    detail = f"found keywords: {found}"\n'}, {'id': 'C6', 'description': 'analysis.py runs without error', 'type': 'script_runs', 'path': 'analysis.py', 'timeout': 120}]

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
