#!/usr/bin/env python3
"""Build HuggingFace-ready dataset JSON from TeamBench task.yaml files and ablation results."""

import json
import os
import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).parent.parent
TASKS_DIR = REPO_ROOT / "tasks"
GENERATORS_DIR = REPO_ROOT / "generators"
ABLATION_SUMMARY = REPO_ROOT / "shared" / "paper" / "ablation_summary.json"
OUTPUT_PATH = REPO_ROOT / "shared" / "teambench_dataset.json"

# ---------------------------------------------------------------------------
# Category normalization
# ---------------------------------------------------------------------------

# Explicit mapping for values found in task.yaml category/domain fields
_CATEGORY_MAP = {
    # category field values
    "CodeReview": "Code Review",
    "code_review": "Code Review",
    "Cross-System": "Cross-System Integration",
    "Security": "Security",
    "Adversarial": "Adversarial",
    "Distributed": "Distributed Systems",
    "Multi-language": "Multi-language",
    "SWE": "Software Eng.",
    "Operations": "Operations",
    "Ops": "Operations",
    "Incident": "Incident Response",
    "Incident-Response": "Incident Response",
    "Information-Retrieval": "Information Retrieval",
    "Testing": "Testing",
    "Policy": "Policy",
    # domain field values
    "software": "Software Eng.",
    "data": "Data Engineering",
    "testing": "Testing",
    "security": "Security",
    "policy": "Policy",
    "long": "Long-Horizon",
    "long_horizon": "Long-Horizon",
    "ir": "Information Retrieval",
    "information_retrieval": "Information Retrieval",
    "incident": "Incident Response",
    "incident_response": "Incident Response",
    "pipeline": "Pipeline",
    "ops": "Operations",
    "operations": "Operations",
    "code_review": "Code Review",
    "specification": "Specification",
    "swe": "Software Eng.",
    "multi_language": "Multi-language",
    "integration": "Integration",
    "config": "Negotiation",
    "debugging": "Distributed Systems",
    "engineering": "Software Eng.",
    "javascript": "Multi-language",
}

# Fallback: infer from task_id prefix
_PREFIX_MAP = {
    "CR": "Code Review",
    "CROSS": "Cross-System Integration",
    "CRYPTO": "Security",
    "D": "Data Engineering",
    "DIST": "Distributed Systems",
    "EA": "Security",
    "GO": "Multi-language",
    "INC": "Incident Response",
    "INT": "Integration",
    "IR": "Information Retrieval",
    "JS": "Multi-language",
    "LH": "Long-Horizon",
    "MULTI": "Multi-language",
    "NEG": "Negotiation",
    "O": "Operations",
    "P": "Policy",
    "PIPE": "Pipeline",
    "S": "Software Eng.",
    "SCALE": "Software Eng.",
    "SEC": "Security",
    "SPEC": "Specification",
    "SQL": "Data Engineering",
    "SYNTH": "Distributed Systems",
    "TEST": "Testing",
    "TRAP": "Adversarial",
}


def normalize_category(raw_category: str | None, raw_domain: str | None, task_id: str) -> str:
    """Return a normalized human-readable category string."""
    for val in (raw_category, raw_domain):
        if val:
            mapped = _CATEGORY_MAP.get(val.strip())
            if mapped:
                return mapped

    # Infer from task_id prefix (longest match wins)
    prefix = re.match(r"^([A-Z]+)", task_id.upper())
    if prefix:
        key = prefix.group(1)
        # Try longest prefix first
        for length in range(len(key), 0, -1):
            candidate = _PREFIX_MAP.get(key[:length])
            if candidate:
                return candidate

    return "Other"


def infer_title(task_id: str, description: str | None) -> str:
    """Produce a readable title from the task_id slug."""
    if description:
        # Use first sentence of description if short enough
        first = description.split(".")[0].strip().strip('"')
        if len(first) <= 80:
            return first
    # Convert snake_case suffix to Title Case
    parts = task_id.split("_", 1)
    if len(parts) == 2:
        return parts[1].replace("_", " ").title()
    return task_id.replace("_", " ").title()


# ---------------------------------------------------------------------------
# Load helpers
# ---------------------------------------------------------------------------

def load_task_yaml(task_dir: Path) -> dict:
    yaml_path = task_dir / "task.yaml"
    if not yaml_path.exists():
        return {}
    with open(yaml_path) as f:
        return yaml.safe_load(f) or {}


def generator_exists(task_id: str) -> bool:
    """Return True if a generator script exists for this task_id."""
    slug = task_id.lower()
    gen_file = GENERATORS_DIR / f"gen_{slug}.py"
    return gen_file.exists()


def load_ablation_summary() -> dict[str, dict]:
    """Return {task_id: scores_dict} from ablation_summary.json."""
    if not ABLATION_SUMMARY.exists():
        return {}
    with open(ABLATION_SUMMARY) as f:
        data = json.load(f)
    result: dict[str, dict] = {}
    for entry in data.get("per_task", []):
        result[entry["task_id"]] = entry
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_dataset() -> list[dict]:
    ablation = load_ablation_summary()

    # Collect all task directories that have a task.yaml
    task_dirs = sorted(
        [d for d in TASKS_DIR.iterdir() if d.is_dir() and (d / "task.yaml").exists()]
    )

    records: list[dict] = []

    # Track which ablation task_ids we've matched (for deduplication / reporting)
    matched_ablation_ids: set[str] = set()

    for task_dir in task_dirs:
        meta = load_task_yaml(task_dir)
        task_id: str = meta.get("task_id") or task_dir.name

        raw_category = meta.get("category")
        raw_domain = meta.get("domain")
        category = normalize_category(raw_category, raw_domain, task_id)

        difficulty: str = meta.get("difficulty", "unknown")

        description: str | None = meta.get("description")
        title = infer_title(task_id, description)

        has_gen = generator_exists(task_id)

        # Find ablation scores: try exact match, then case-insensitive
        ab = ablation.get(task_id) or ablation.get(task_id.lower())
        ablation_scores: dict | None = None
        tni: float | None = None
        classification: str | None = None

        if ab:
            matched_ablation_ids.add(ab["task_id"])
            ablation_scores = {
                "oracle": ab.get("oracle"),
                "restricted": ab.get("restricted"),
                "team": ab.get("team"),
                "team_no_plan": ab.get("no_plan"),
                "team_no_verify": ab.get("no_verify"),
            }
            tni = ab.get("tni")
            classification = ab.get("classification")

        record = {
            "task_id": task_id,
            "title": title,
            "category": category,
            "difficulty": difficulty,
            "has_generator": has_gen,
        }
        if ablation_scores is not None:
            record["ablation_scores"] = ablation_scores
        if tni is not None:
            record["tni"] = round(tni, 4)
        if classification:
            record["classification"] = classification

        records.append(record)

    # Report any ablation entries without a matching task directory
    unmatched = set(ablation.keys()) - matched_ablation_ids
    if unmatched:
        print(f"[warn] {len(unmatched)} ablation entries have no matching task dir: "
              f"{sorted(unmatched)[:10]}{'...' if len(unmatched) > 10 else ''}")

    return records


def main() -> None:
    records = build_dataset()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(records, f, indent=2)

    # Summary stats
    total = len(records)
    with_ablation = sum(1 for r in records if "ablation_scores" in r)
    cats = {}
    diffs = {}
    for r in records:
        cats[r["category"]] = cats.get(r["category"], 0) + 1
        diffs[r["difficulty"]] = diffs.get(r["difficulty"], 0) + 1

    print(f"Wrote {total} tasks to {OUTPUT_PATH}")
    print(f"  Tasks with ablation scores: {with_ablation}")
    print(f"  Difficulty breakdown: {dict(sorted(diffs.items()))}")
    print(f"  Category breakdown ({len(cats)} categories):")
    for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"    {cat}: {count}")


if __name__ == "__main__":
    main()
