"""
Base classes for real-data DS/ML task generators.

Tasks in this family are anchored in real CSV datasets stored under
datasets/{dataset_name}.csv. Four archetypes are supported:

  Archetype 2 - SynthesisGenerator:       info distributed across spec + corpus
  Archetype 3 - OpenEndedGenerator:       raw data + question, rubric grading
  Archetype 4 - AdversarialWorkspaceGenerator: plausible-but-wrong workspace
  Archetype 5 - DiscoveryGenerator:       workspace with hidden quality issues

No pandas dependency inside generator code — only stdlib csv / io.
"""
from __future__ import annotations

import csv
import io
import textwrap
from abc import abstractmethod
from pathlib import Path
from typing import Any

from generators.base import GeneratedTask, TaskGenerator
from generators.primitives import SeededRandom

# Root of the repo  →  datasets/ lives here
_DATASETS_DIR = Path(__file__).parent.parent / "datasets"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _indent(text: str, prefix: str = "    ") -> str:
    """Indent every non-empty line of *text* by *prefix*."""
    return "\n".join(prefix + line if line.strip() else line
                     for line in text.splitlines())


# ── Core base class ───────────────────────────────────────────────────────────

class RealDataGenerator(TaskGenerator):
    """
    Base class for tasks anchored in real datasets.

    Subclasses must declare three class attributes and implement generate().
    """

    # --- required class attributes -------------------------------------------
    dataset_name: str = ""       # e.g. "iris" (maps to datasets/iris.csv)
    dataset_license: str = ""    # e.g. "CC BY 4.0"
    dataset_source: str = ""     # e.g. "UCI ML Repository"

    # ── Data loading ─────────────────────────────────────────────────────────

    def load_dataset(self) -> list[dict]:
        """Load CSV from datasets/{dataset_name}.csv.

        Lines beginning with '#' are treated as comments and skipped.
        Returns a list of row dicts (all values are strings as from csv.DictReader).
        """
        csv_path = _DATASETS_DIR / f"{self.dataset_name}.csv"
        with open(csv_path, newline="", encoding="utf-8") as fh:
            lines = [line for line in fh if not line.lstrip().startswith("#")]
        reader = csv.DictReader(lines)
        return [dict(row) for row in reader]

    # ── Manipulation helpers ──────────────────────────────────────────────────

    def subsample(
        self,
        rows: list[dict],
        seed: int,
        frac: float = 1.0,
    ) -> list[dict]:
        """Return a reproducible random subsample of *rows*.

        Parameters
        ----------
        rows:  source rows
        seed:  integer seed for SeededRandom
        frac:  fraction to keep (0 < frac <= 1.0)
        """
        if frac >= 1.0:
            return list(rows)
        k = max(1, int(len(rows) * frac))
        rng = SeededRandom(seed)
        return rng.sample(rows, k)

    def select_columns(
        self,
        rows: list[dict],
        columns: list[str],
    ) -> list[dict]:
        """Return rows containing only the specified *columns*."""
        return [{col: row[col] for col in columns} for row in rows]

    def rows_to_csv(
        self,
        rows: list[dict],
        columns: list[str] | None = None,
    ) -> str:
        """Convert a list of row dicts to a CSV string.

        If *columns* is None, all keys from the first row are used.
        """
        if not rows:
            return ""
        fieldnames = columns if columns is not None else list(rows[0].keys())
        buf = io.StringIO()
        writer = csv.DictWriter(
            buf,
            fieldnames=fieldnames,
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
        return buf.getvalue()

    # ── Task-level helpers ────────────────────────────────────────────────────

    def make_task_yaml(
        self,
        *,
        task_id: str | None = None,
        domain: str | None = None,
        difficulty: str | None = None,
        languages: list[str] | None = None,
        dataset_name: str | None = None,
        dataset_license: str | None = None,
        dataset_source: str | None = None,
    ) -> str:
        """Generate a task.yaml content string.

        Falls back to class-level attributes when keyword arguments are omitted.
        """
        tid = task_id or self.task_id
        dom = domain or getattr(self, "domain", "data")
        diff = difficulty or getattr(self, "difficulty", "medium")
        langs = languages or getattr(self, "languages", ["python"])
        d_name = dataset_name or self.dataset_name
        d_license = dataset_license or self.dataset_license
        d_source = dataset_source or self.dataset_source

        langs_yaml = "\n".join(f"  - {lang}" for lang in langs)
        return textwrap.dedent(f"""\
            task_id: {tid}
            domain: {dom}
            difficulty: {diff}
            languages:
            {langs_yaml}
            dataset:
              name: {d_name}
              license: {d_license}
              source: {d_source}
        """)

    # ── Rubric grader factory ─────────────────────────────────────────────────

    def make_check_solution(self, checks: list[dict]) -> str:
        """Generate a standalone check_solution.py script from rubric check dicts.

        Each check dict must have:
          id          : str   — short identifier, e.g. "C1"
          description : str   — human-readable description
          type        : str   — one of:
                          "file_exists"      → params: path (str)
                          "script_runs"      → params: path (str), timeout (int, opt)
                          "output_contains"  → params: path (str), patterns (list[str])
                          "value_in_range"   → params: path (str), key (str),
                                                        min (float), max (float)
                          "custom_python"    → params: code (str)
                                               code has access to `workspace_dir`
                                               must set local `passed` (bool) and
                                               optionally `detail` (str)

        The generated script:
          - runs each check independently (failures are isolated)
          - writes ../reports/score.json relative to workspace
          - prints a summary table to stdout
        """
        # Serialise the check list as an embedded Python literal so the
        # generated script is fully self-contained.
        checks_repr = repr(checks)

        script = textwrap.dedent(f"""\
            #!/usr/bin/env python3
            \"\"\"Auto-generated grading script — do not edit by hand.\"\"\"
            import json
            import os
            import pathlib
            import subprocess
            import sys

            CHECKS = {checks_repr}

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
                        detail = f"missing patterns: {{missing}}" if missing else ""

                    elif ctype == "value_in_range":
                        target = pathlib.Path(workspace_dir) / check["path"]
                        data = json.loads(target.read_text(encoding="utf-8"))
                        val = data[check["key"]]
                        lo = check["min"]
                        hi = check["max"]
                        passed = lo <= float(val) <= hi
                        detail = f"{{check['key']}}={{val}} (expected [{{lo}}, {{hi}}])"

                    elif ctype == "custom_python":
                        local_ns = {{"workspace_dir": workspace_dir, "passed": False, "detail": ""}}
                        exec(check["code"], local_ns)  # noqa: S102
                        passed = bool(local_ns.get("passed", False))
                        detail = str(local_ns.get("detail", ""))

                    else:
                        detail = f"unknown check type: {{ctype}}"

                except Exception as exc:  # noqa: BLE001
                    passed = False
                    detail = f"{{type(exc).__name__}}: {{exc}}"

                return passed, detail


            def main():
                workspace_dir = pathlib.Path(__file__).parent.resolve()
                reports_dir = workspace_dir.parent / "reports"
                reports_dir.mkdir(parents=True, exist_ok=True)

                results = []
                for check in CHECKS:
                    passed, detail = _run_check(check, workspace_dir)
                    results.append({{
                        "id": check["id"],
                        "description": check["description"],
                        "passed": passed,
                        "detail": detail,
                    }})

                checks_passed = sum(1 for r in results if r["passed"])
                checks_total = len(results)
                primary_success = checks_passed == checks_total
                partial_score = checks_passed / checks_total if checks_total else 0.0
                failure_modes = [
                    r["description"] for r in results if not r["passed"]
                ]

                score = {{
                    "pass": primary_success,
                    "primary": {{"success": primary_success}},
                    "secondary": {{
                        "partial_score": partial_score,
                        "checks_passed": checks_passed,
                        "checks_total": checks_total,
                    }},
                    "failure_modes": failure_modes,
                    "checklist": results,
                }}

                score_path = reports_dir / "score.json"
                score_path.write_text(json.dumps(score, indent=2), encoding="utf-8")

                # ── stdout summary ────────────────────────────────────────
                print(f"\\nGrading results: {{checks_passed}}/{{checks_total}} checks passed")
                print(f"Partial score  : {{partial_score:.3f}}")
                print(f"Overall pass   : {{primary_success}}")
                if failure_modes:
                    print("\\nFailed checks:")
                    for fm in failure_modes:
                        print(f"  - {{fm}}")
                print(f"\\nScore written to: {{score_path}}")
                return 0 if primary_success else 1


            if __name__ == "__main__":
                raise SystemExit(main())
        """)
        return script

    @abstractmethod
    def generate(self, seed: int) -> GeneratedTask:
        raise NotImplementedError


# ── Archetype base classes ────────────────────────────────────────────────────

class OpenEndedGenerator(RealDataGenerator):
    """Archetype 3 — open-ended analytical question.

    No scaffold code is provided; the agent receives raw data and a question
    and must produce an answer file graded by rubric checks.
    """

    def make_requirements_txt(
        self,
        packages: list[str] | None = None,
    ) -> str:
        """Return the content of a requirements.txt for the workspace.

        If *packages* is None, a sensible default for DS tasks is used.
        """
        default = [
            "pandas>=1.5",
            "numpy>=1.23",
            "scipy>=1.9",
            "scikit-learn>=1.1",
        ]
        pkgs = packages if packages is not None else default
        return "\n".join(pkgs) + "\n"

    @abstractmethod
    def generate(self, seed: int) -> GeneratedTask:
        raise NotImplementedError


class AdversarialWorkspaceGenerator(RealDataGenerator):
    """Archetype 4 — workspace contains a plausible-but-wrong solution.

    The agent must identify and correct the errors rather than build from
    scratch.  Subclasses supply a buggy solution in workspace_files and
    document the intentional mistakes in their spec.
    """

    @abstractmethod
    def generate(self, seed: int) -> GeneratedTask:
        raise NotImplementedError


class DiscoveryGenerator(RealDataGenerator):
    """Archetype 5 — workspace has hidden data quality issues.

    The agent must discover and remediate quality problems (e.g. label
    leakage, distribution shift, silent truncation) that are not explicitly
    described in the spec.
    """

    @abstractmethod
    def generate(self, seed: int) -> GeneratedTask:
        raise NotImplementedError


class SynthesisGenerator(RealDataGenerator):
    """Archetype 2 — information distributed across spec and corpus documents.

    The agent must synthesise knowledge from multiple sources (spec.md plus
    corpus files) to produce a correct solution.  Subclasses populate
    corpus_files in GeneratedTask alongside the usual workspace_files.
    """

    @abstractmethod
    def generate(self, seed: int) -> GeneratedTask:
        raise NotImplementedError
