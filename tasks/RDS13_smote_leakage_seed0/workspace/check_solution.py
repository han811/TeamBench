#!/usr/bin/env python3
"""Auto-generated grading script — do not edit by hand."""
import json
import os
import pathlib
import subprocess
import sys

CHECKS = [{'id': 'C1', 'description': 'Resampling called AFTER train_test_split in analysis.py', 'type': 'custom_python', 'code': 'import pathlib, re\nsrc = (pathlib.Path(workspace_dir) / "analysis.py").read_text(encoding="utf-8")\nlines = src.splitlines()\n# Find line indices of train_test_split and fit_resample\nsplit_idx = next((i for i, l in enumerate(lines) if "train_test_split" in l), None)\nresample_idx = next((i for i, l in enumerate(lines) if "fit_resample" in l), None)\nif split_idx is None:\n    passed = False\n    detail = "train_test_split not found in analysis.py"\nelif resample_idx is None:\n    passed = False\n    detail = "fit_resample not found in analysis.py"\nelse:\n    # Resampling must come AFTER split (higher line index)\n    passed = resample_idx > split_idx\n    detail = f"split at line {split_idx}, resample at line {resample_idx}"\n'}, {'id': 'C2', 'description': "results.json exists with 'auc' key", 'type': 'custom_python', 'code': 'import json, pathlib\nrpath = pathlib.Path(workspace_dir) / "results.json"\nif not rpath.exists():\n    passed = False\n    detail = "results.json not found"\nelse:\n    data = json.loads(rpath.read_text(encoding="utf-8"))\n    passed = "auc" in data\n    detail = f"keys present: {list(data.keys())}"\n'}, {'id': 'C3', 'description': 'AUC in results.json <= 0.97 (leakage removed, realistic result)', 'type': 'custom_python', 'code': 'import json, pathlib\nrpath = pathlib.Path(workspace_dir) / "results.json"\nif not rpath.exists():\n    passed = False\n    detail = "results.json not found"\nelse:\n    data = json.loads(rpath.read_text(encoding="utf-8"))\n    auc = data.get("auc", 1.0)\n    passed = float(auc) <= 0.97\n    detail = f"auc={auc} (need <= 0.97)"\n'}, {'id': 'C4', 'description': "results.json contains 'n_train' and 'n_test' keys", 'type': 'custom_python', 'code': 'import json, pathlib\nrpath = pathlib.Path(workspace_dir) / "results.json"\nif not rpath.exists():\n    passed = False\n    detail = "results.json not found"\nelse:\n    data = json.loads(rpath.read_text(encoding="utf-8"))\n    passed = "n_train" in data and "n_test" in data\n    detail = f"keys present: {list(data.keys())}"\n'}, {'id': 'C5', 'description': 'report.md mentions leakage/contamination/oversampling order', 'type': 'custom_python', 'code': 'import pathlib\nrpath = pathlib.Path(workspace_dir) / "report.md"\nif not rpath.exists():\n    passed = False\n    detail = "report.md not found"\nelse:\n    content = rpath.read_text(encoding="utf-8").lower()\n    keywords = ["leakage", "leak", "contamination", "before split",\n                "after split", "train only", "training set only"]\n    found = [kw for kw in keywords if kw in content]\n    passed = len(found) >= 1\n    detail = f"found keywords: {found}"\n'}, {'id': 'C6', 'description': 'analysis.py runs without error', 'type': 'script_runs', 'path': 'analysis.py', 'timeout': 180}]

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
            exec(check["code"], local_ns)  # noqa: S102
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
