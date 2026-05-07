"""
TeamBench Leaderboard — HuggingFace Spaces Gradio Application

Evaluates LLM teamwork via OS-enforced role separation (Planner/Executor/Verifier).
Primary metric: TNI (Teamwork Necessity Index).
"""

from __future__ import annotations

import json
import os
import zipfile
import tempfile
from pathlib import Path

import gradio as gr
import pandas as pd

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).parent / "data"
SUBMISSIONS_DIR = Path(__file__).parent / "submissions"
SUBMISSIONS_DIR.mkdir(exist_ok=True)

_data: dict = {}


def _load() -> dict:
    global _data
    if _data:
        return _data
    path = DATA_DIR / "leaderboard_data.json"
    with open(path) as f:
        _data = json.load(f)
    return _data


# ---------------------------------------------------------------------------
# Display name maps
# ---------------------------------------------------------------------------

MODEL_DISPLAY = {
    # API models
    "gemini-3-flash-preview": "Gemini 3 Flash",
    "gemini-3.1-flash-lite-preview": "Gemini 3.1 Lite",
    "gpt-5-mini": "GPT-5 Mini",
    "gpt-5-nano": "GPT-5 Nano",
    "gpt-5.3-chat-latest": "GPT-5.3 Chat",
    "gpt-5.4": "GPT-5.4",
    "claude-sonnet-4-6": "Claude Sonnet 4.6",
    "claude-haiku-4-5-20251001": "Claude Haiku 4.5",
    # Open-source (vLLM-served)
    "Qwen3-4B": "Qwen3-4B",
    "Qwen3-8B": "Qwen3-8B",
    "Qwen3-14B": "Qwen3-14B",
    "Qwen3.5-0.8B": "Qwen3.5-0.8B",
    "Qwen3.5-2B": "Qwen3.5-2B",
    "Qwen3.5-4B": "Qwen3.5-4B",
    "Qwen3.5-9B": "Qwen3.5-9B",
    "Qwen3.5-27B": "Qwen3.5-27B",
    "Qwen3.5-35B-A3B": "Qwen3.5-35B-A3B",
    "Qwen2.5-Coder-32B": "Qwen2.5-Coder-32B",
    "Qwen3-Coder-30B-A3B": "Qwen3-Coder-30B-A3B",
    "DeepSeek-R1-Distill-32B": "DeepSeek-R1-Distill-32B",
    "Gemma 3 27B": "Gemma 3 27B",
    "GPT-OSS-20B": "GPT-OSS-20B",
    "Devstral-24B": "Devstral-24B",
    "CodeGemma 7B": "CodeGemma 7B",
}

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

CUSTOM_CSS = """
:root {
    --bench-blue: #2563eb; --bench-green: #16a34a; --bench-red: #dc2626;
    --bench-amber: #d97706; --bench-purple: #7c3aed; --bench-gray: #6b7280;
    --badge-radius: 4px;
}

.tb-header {
    background: linear-gradient(135deg, #1e3a8a 0%, #1d4ed8 50%, #2563eb 100%);
    border-radius: 12px; padding: 28px 32px 24px; margin-bottom: 8px;
}
.tb-header h1 {
    margin: 0 0 6px; font-size: 2rem; font-weight: 700;
    letter-spacing: -0.5px; color: #ffffff !important;
}
.tb-header p {
    margin: 0; font-size: 1rem; color: #ffffff !important; opacity: 0.92;
}

.stat-grid {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 12px; margin-bottom: 16px;
}
.stat-card {
    background: var(--background-fill-primary, #fff);
    border: 1px solid var(--border-color-primary, #e5e7eb);
    border-radius: 10px; padding: 16px 18px; text-align: center;
}
.stat-card .stat-value { font-size: 1.5rem; font-weight: 700; color: var(--bench-blue); line-height: 1; }
.stat-card .stat-label { font-size: 0.78rem; color: var(--bench-gray); margin-top: 4px; }

.badge-HIGH-TNI   { background:#dbeafe; color:#1e40af; padding:2px 8px; border-radius:var(--badge-radius); font-size:0.78rem; font-weight:600; }
.badge-TEAM-HELPS { background:#dcfce7; color:#166534; padding:2px 8px; border-radius:var(--badge-radius); font-size:0.78rem; font-weight:600; }
.badge-NEUTRAL    { background:#f3f4f6; color:#374151; padding:2px 8px; border-radius:var(--badge-radius); font-size:0.78rem; font-weight:600; }
.badge-TEAM-HURTS { background:#fee2e2; color:#991b1b; padding:2px 8px; border-radius:var(--badge-radius); font-size:0.78rem; font-weight:600; }

.section-title {
    font-size: 1.05rem; font-weight: 600; margin: 20px 0 10px;
    padding-bottom: 6px; border-bottom: 2px solid var(--border-color-primary, #e5e7eb);
}

.about-card {
    background: var(--background-fill-primary, #fff);
    border: 1px solid var(--border-color-primary, #e5e7eb);
    border-radius: 10px; padding: 20px 24px; margin-bottom: 12px;
}
.about-card h3 { margin: 0 0 10px; font-size: 1rem; font-weight: 700; }
.about-card p, .about-card li { font-size: 0.9rem; line-height: 1.65; }
.about-card ul { padding-left: 20px; margin: 8px 0; }

.role-planner  { background:#ede9fe; color:#5b21b6; padding:3px 10px; border-radius:20px; font-size:0.82rem; font-weight:600; }
.role-executor { background:#fef3c7; color:#92400e; padding:3px 10px; border-radius:20px; font-size:0.82rem; font-weight:600; }
.role-verifier { background:#d1fae5; color:#065f46; padding:3px 10px; border-radius:20px; font-size:0.82rem; font-weight:600; }

.submit-info {
    background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 10px;
    padding: 18px 22px; margin-bottom: 16px; font-size: 0.9rem; line-height: 1.7;
}
.submit-info code {
    background: #dbeafe; padding: 2px 6px; border-radius: 4px; font-size: 0.82rem;
}
.submit-step {
    background: var(--background-fill-primary, #fff);
    border: 1px solid var(--border-color-primary, #e5e7eb);
    border-radius: 10px; padding: 16px 20px; margin-bottom: 12px;
}
.submit-step h4 { margin: 0 0 8px; font-size: 0.95rem; }

.gr-dataframe table { width: 100%; font-size: 0.875rem; }
.gr-dataframe th { font-weight: 600; }
"""

# ---------------------------------------------------------------------------
# HTML builders
# ---------------------------------------------------------------------------

def create_header() -> str:
    return """
<div class="tb-header">
  <h1>TeamBench Leaderboard</h1>
  <p>Multi-agent benchmark evaluating LLM teamwork with OS-enforced role separation</p>
</div>
"""


def create_stat_cards() -> str:
    d = _load()
    agg = d["aggregate"]
    n = d["total_tasks"]
    n_hard = d["total_hard"]
    cats = len(d["categories"])
    helps = agg["team_helps_count"]
    high_tni = agg["high_tni_count"]
    avg_tni = agg["avg_tni"]
    return f"""
<div class="stat-grid">
  <div class="stat-card">
    <div class="stat-value">{n}</div>
    <div class="stat-label">Total Tasks</div>
  </div>
  <div class="stat-card">
    <div class="stat-value">{n_hard}</div>
    <div class="stat-label">Hard / Expert Tasks</div>
  </div>
  <div class="stat-card">
    <div class="stat-value">{cats}</div>
    <div class="stat-label">Categories</div>
  </div>
  <div class="stat-card">
    <div class="stat-value">{helps}</div>
    <div class="stat-label">Team-Helps Tasks</div>
  </div>
  <div class="stat-card">
    <div class="stat-value">{high_tni}</div>
    <div class="stat-label">High-TNI (team &ge; oracle)</div>
  </div>
  <div class="stat-card">
    <div class="stat-value">{avg_tni:.2f}</div>
    <div class="stat-label">Avg TNI</div>
  </div>
</div>
"""


# ---------------------------------------------------------------------------
# Tab: Performance — Cross-Model (28 tasks, 4 models)
# ---------------------------------------------------------------------------

def build_crossmodel_leaderboard() -> pd.DataFrame:
    d = _load()
    cm = d["cross_model"]
    models_ordered = sorted(cm["per_model"].items(),
                            key=lambda kv: kv[1]["avg_uplift"], reverse=True)
    rows = []
    for i, (mid, stats) in enumerate(models_ordered):
        u = stats["avg_uplift"]
        rows.append({
            "Rank": f"#{i+1}",
            "Model": MODEL_DISPLAY.get(mid, mid),
            "Team Score": f"{stats['avg_team']:.1%}",
            "Oracle Score": f"{stats['avg_oracle']:.1%}",
            "Team Uplift": f"+{u:.1%}" if u >= 0 else f"{u:.1%}",
            "Avg TNI": f"{stats['avg_tni']:.3f}",
            "Team > Oracle": f"{stats['team_helps_pct']:.0%}",
        })
    return pd.DataFrame(rows)


def build_crossmodel_task_df(category: str = "All",
                             classification: str = "All") -> pd.DataFrame:
    d = _load()
    cm = d["cross_model"]
    models = cm["models"]

    rows = []
    for task in cm["per_task"]:
        cat = task["category"]
        if category != "All" and cat != category:
            continue

        classes = [task["models"][m]["classification"] for m in models if m in task["models"]]
        counts: dict[str, int] = {}
        for c in classes:
            counts[c] = counts.get(c, 0) + 1
        agg_class = max(counts, key=counts.get) if counts else "NEUTRAL"
        if classification != "All" and agg_class != classification:
            continue

        row: dict = {"Task": task["task_id"], "Category": cat}
        for mid in models:
            short = MODEL_DISPLAY.get(mid, mid)
            mdata = task["models"].get(mid, {})
            team = mdata.get("team", 0) or 0
            uplift = mdata.get("team_uplift", 0) or 0
            row[f"{short}"] = f"{team:.0%}"
            row[f"{short} Uplift"] = f"+{uplift:.0%}" if uplift >= 0 else f"{uplift:.0%}"
        row["Class"] = agg_class
        rows.append(row)

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("Task").reset_index(drop=True)


# ---------------------------------------------------------------------------
# Tab: Overview — All 155 tasks (reference model)
# ---------------------------------------------------------------------------

def build_overview_df(track: str = "Full", category: str = "All",
                      classification: str = "All") -> pd.DataFrame:
    d = _load()
    rows = []
    for t in d["per_task"]:
        if track == "Hard" and t["difficulty_track"] != "hard":
            continue
        if category != "All" and t["category"] != category:
            continue
        if classification != "All" and t["classification"] != classification:
            continue
        uplift = t["team_uplift"]
        rows.append({
            "Task": t["task_id"],
            "Category": t["category"],
            "Difficulty": t["difficulty"].capitalize(),
            "Oracle": f"{t['oracle']:.0%}",
            "Restricted": f"{t['restricted']:.0%}",
            "Team": f"{t['team']:.0%}",
            "Uplift": f"+{uplift:.0%}" if uplift >= 0 else f"{uplift:.0%}",
            "TNI": f"{t['tni']:.2f}" if t["tni"] is not None else "—",
            "Class": t["classification"],
        })
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("Task").reset_index(drop=True)


def build_category_summary_df(track: str = "Full") -> pd.DataFrame:
    d = _load()
    cat_data: dict[str, list] = {}
    for t in d["per_task"]:
        if track == "Hard" and t["difficulty_track"] != "hard":
            continue
        cat = t["category"]
        if cat not in cat_data:
            cat_data[cat] = []
        cat_data[cat].append(t)

    rows = []
    for cat in sorted(cat_data):
        tasks = cat_data[cat]
        n = len(tasks)
        avg_team = sum(t["team"] for t in tasks) / n
        avg_oracle = sum(t["oracle"] for t in tasks) / n
        avg_uplift = sum(t["team_uplift"] for t in tasks) / n
        helps = sum(1 for t in tasks if t["team_uplift"] > 0.05)
        high = sum(1 for t in tasks if t["classification"] == "HIGH-TNI")
        rows.append({
            "Category": cat,
            "Tasks": n,
            "Avg Team": f"{avg_team:.0%}",
            "Avg Oracle": f"{avg_oracle:.0%}",
            "Avg Uplift": f"+{avg_uplift:.0%}" if avg_uplift >= 0 else f"{avg_uplift:.0%}",
            "Team Helps": f"{helps}/{n}",
            "High-TNI": high,
        })
    return pd.DataFrame(rows).sort_values("Category").reset_index(drop=True)


# ---------------------------------------------------------------------------
# Submission handler — workspace artifact zip (server-graded)
# ---------------------------------------------------------------------------

MAX_UPLOAD_MB = 100


def _get_valid_task_ids() -> set[str]:
    return {t["task_id"] for t in _load()["per_task"]}


def validate_and_accept_submission(
    file, model_name: str, team_name: str, framework: str,
    contact: str, description: str, seed: str,
) -> str:
    """Validate a workspace artifact zip and queue it for server-side grading."""

    # --- basic field validation ---
    if not file:
        return "Please upload a workspace artifact zip file."
    if not model_name or not model_name.strip():
        return "Please provide a model name."
    if not team_name or not team_name.strip():
        return "Please provide a team or organization name."

    file_path = file.name if hasattr(file, "name") else str(file)

    # --- file size check ---
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if file_size_mb > MAX_UPLOAD_MB:
        return f"File too large ({file_size_mb:.1f} MB). Maximum is {MAX_UPLOAD_MB} MB."

    # --- zip validation ---
    if not zipfile.is_zipfile(file_path):
        return "Uploaded file is not a valid zip archive."

    valid_tasks = _get_valid_task_ids()
    found_tasks: dict[str, list[str]] = {}  # task_id -> list of files
    has_meta = False

    try:
        with zipfile.ZipFile(file_path, "r") as zf:
            names = zf.namelist()

            # Security: reject paths with .. or absolute paths
            for name in names:
                if ".." in name or name.startswith("/"):
                    return f"Rejected: unsafe path in zip: `{name}`"

            # Check for meta.json
            for name in names:
                if name.endswith("meta.json") and name.count("/") <= 1:
                    has_meta = True

            # Find workspace directories. Accept multiple layouts:
            #   tasks/{TASK_ID}/workspace/...
            #   tasks/{TASK_ID}/{condition}/workspace/...
            #   {TASK_ID}/workspace/...
            #   {TASK_ID}/{condition}/workspace/...
            valid_upper = {t.upper(): t for t in valid_tasks}

            for name in names:
                parts = name.split("/")
                if "workspace" not in parts:
                    continue
                ws_idx = parts.index("workspace")
                # Try task_id at ws_idx-1 or ws_idx-2
                for offset in [1, 2]:
                    candidate_idx = ws_idx - offset
                    if candidate_idx < 0:
                        continue
                    candidate = parts[candidate_idx]
                    matched = (
                        candidate if candidate in valid_tasks
                        else valid_upper.get(candidate.upper())
                    )
                    if matched:
                        if matched not in found_tasks:
                            found_tasks[matched] = []
                        found_tasks[matched].append(name)
                        break

    except zipfile.BadZipFile:
        return "Corrupted zip file. Please re-create and upload again."

    if not found_tasks:
        return (
            "No valid task workspaces found in the zip.\n\n"
            "Expected structure:\n"
            "```\n"
            "submission.zip/\n"
            "  meta.json\n"
            "  tasks/\n"
            "    S1_hidden_spec/\n"
            "      workspace/\n"
            "        <files your agent produced>\n"
            "    D1_schema_drift/\n"
            "      workspace/\n"
            "        ...\n"
            "```"
        )

    # --- save submission ---
    safe_model = "".join(c if c.isalnum() or c in "-_" else "_" for c in model_name.strip())
    safe_team = "".join(c if c.isalnum() or c in "-_" else "_" for c in team_name.strip())
    submission_id = f"{safe_team}__{safe_model}"

    # Save metadata
    meta = {
        "submission_id": submission_id,
        "model": model_name.strip(),
        "team": team_name.strip(),
        "framework": framework.strip() if framework else "",
        "contact": contact.strip() if contact else "",
        "description": description.strip() if description else "",
        "seed": int(seed) if seed and seed.isdigit() else 0,
        "tasks_submitted": sorted(found_tasks.keys()),
        "task_count": len(found_tasks),
        "file_count": sum(len(v) for v in found_tasks.values()),
        "status": "pending_grading",
    }

    meta_path = SUBMISSIONS_DIR / f"{submission_id}.json"
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    # Save the zip itself
    import shutil
    zip_path = SUBMISSIONS_DIR / f"{submission_id}.zip"
    shutil.copy2(file_path, zip_path)

    # --- build response ---
    missing = valid_tasks - set(found_tasks.keys())
    conditions = ["oracle", "restricted", "full", "team_no_plan", "team_no_verify"]

    response_parts = [
        f"### Submission Received",
        f"",
        f"**Model**: {model_name.strip()}",
        f"**Team**: {team_name.strip()}",
        f"**Tasks**: {len(found_tasks)} / {len(valid_tasks)}",
        f"**Files**: {sum(len(v) for v in found_tasks.values())} workspace artifacts",
        f"**Seed**: {meta['seed']}",
    ]

    if framework and framework.strip():
        response_parts.append(f"**Framework**: {framework.strip()}")

    response_parts.append("")

    if len(found_tasks) < len(valid_tasks):
        response_parts.append(
            f"*{len(missing)} tasks not included (partial submission accepted).*"
        )

    response_parts += [
        "",
        "**Status: Queued for server-side grading.**",
        "",
        "Your workspace artifacts will be graded against our hidden test suites. "
        "Scores are computed server-side — not self-reported — to ensure benchmark integrity.",
        "",
        "Results will appear on the leaderboard once grading completes (typically within 24-48 hours). "
        "You will be contacted at the provided email if there are any issues.",
    ]

    return "\n".join(response_parts)


# ---------------------------------------------------------------------------
# About HTML
# ---------------------------------------------------------------------------

def create_about_html() -> str:
    return """
<div class="about-card">
  <h3>What is TeamBench?</h3>
  <p>TeamBench is a multi-agent benchmark that evaluates whether structured LLM teamwork
  improves task performance beyond what a single all-capable (oracle) agent can achieve.
  155 tasks span 19 categories including Security, Data Engineering, Distributed Systems,
  Testing, and Adversarial Specification &mdash; designed to require coordination, verification,
  and planning across roles.</p>
  <p>All roles execute in isolated Docker containers with OS-enforced permission boundaries,
  preventing role confusion and ensuring genuine separation of concerns.</p>
</div>

<div class="about-card">
  <h3>The Three Roles</h3>
  <ul>
    <li><span class="role-planner">Planner</span> &mdash; reads code and documentation, identifies what needs to change,
    produces a structured plan. Has read-only filesystem access plus static analysis tools.</li>
    <li><span class="role-executor">Executor</span> &mdash; implements the plan. Has read-write access to the workspace
    but cannot run tests or arbitrary shell commands.</li>
    <li><span class="role-verifier">Verifier</span> &mdash; runs tests and validates the implementation. Has pytest,
    hypothesis, and mutation testing but cannot modify source files.</li>
  </ul>
</div>

<div class="about-card">
  <h3>Ablation Conditions</h3>
  <ul>
    <li><strong>Oracle</strong> &mdash; single agent with full unrestricted access (upper bound).</li>
    <li><strong>Restricted</strong> &mdash; single agent with only executor-level permissions (lower bound).</li>
    <li><strong>Full Team</strong> &mdash; all three roles: Planner &rarr; Executor &rarr; Verifier.</li>
    <li><strong>Team (No Plan)</strong> &mdash; Executor + Verifier only; measures planning value.</li>
    <li><strong>Team (No Verify)</strong> &mdash; Planner + Executor only; measures verification value.</li>
  </ul>
</div>

<div class="about-card">
  <h3>TNI &mdash; Teamwork Necessity Index</h3>
  <p style="font-family:monospace; background:#f3f4f6; padding:8px 12px; border-radius:6px; display:inline-block;">
    TNI = (team &minus; restricted) / (oracle &minus; restricted)
  </p>
  <p>TNI = 1.0 means the team matches the oracle. TNI &gt; 1.0 means the team <em>exceeds</em>
  the oracle &mdash; true super-additive teamwork.</p>
  <ul>
    <li><span class="badge-HIGH-TNI">HIGH-TNI</span> TNI &ge; 1.0: team closes or exceeds the oracle gap.</li>
    <li><span class="badge-TEAM-HELPS">TEAM-HELPS</span> positive uplift, TNI &lt; 1.0.</li>
    <li><span class="badge-NEUTRAL">NEUTRAL</span> no significant change.</li>
    <li><span class="badge-TEAM-HURTS">TEAM-HURTS</span> coordination degrades performance.</li>
  </ul>
</div>

<div class="about-card">
  <h3>Difficulty Tracks</h3>
  <ul>
    <li><strong>Full</strong> &mdash; all 155 tasks (easy + medium + hard + expert).</li>
    <li><strong>Hard</strong> &mdash; 122 tasks rated hard or expert only.</li>
  </ul>
</div>

<div class="about-card">
  <h3>Citation</h3>
  <p>If you use TeamBench in your research, please cite:</p>
  <pre style="background:#f3f4f6; padding:12px 16px; border-radius:8px; font-size:0.82rem; line-height:1.6; overflow-x:auto;">@misc{kim2026teambench,
  title   = {TeamBench: Evaluating Structured LLM Teamwork
             via OS-Enforced Role Separation},
  author  = {Kim, Yubin},
  year    = {2026},
  url     = {https://github.com/ybkim95/TeamBench}
}</pre>
</div>

<div class="about-card">
  <h3>Links</h3>
  <ul>
    <li>Repository: <a href="https://github.com/ybkim95/TeamBench" target="_blank">github.com/ybkim95/TeamBench</a></li>
    <li>Leaderboard: <a href="https://huggingface.co/spaces/ybkim95/teambench-leaderboard" target="_blank">huggingface.co/spaces/ybkim95/teambench-leaderboard</a></li>
  </ul>
</div>
"""


# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------

def build_app() -> gr.Blocks:
    _load()

    categories_all = ["All"] + _load()["categories"]
    classifications = ["All", "HIGH-TNI", "TEAM-HELPS", "NEUTRAL", "TEAM-HURTS"]
    cm_categories = ["All"] + sorted({
        t["category"] for t in _load()["cross_model"]["per_task"]
    })

    _theme = gr.themes.Default(
        primary_hue="blue",
        secondary_hue="emerald",
        font=[gr.themes.GoogleFont("Inter"), "ui-sans-serif", "sans-serif"],
    )

    with gr.Blocks(title="TeamBench Leaderboard", theme=_theme, css=CUSTOM_CSS) as demo:
        gr.HTML(create_header())

        with gr.Tabs():

            # ==============================================================
            # TAB 1: Performance (Cross-Model) — default tab
            # ==============================================================
            with gr.Tab("Performance"):
                gr.HTML(create_stat_cards())

                gr.Markdown(
                    "### Cross-Model Leaderboard\n"
                    "28 tasks evaluated across 4 models. "
                    "Ranked by average team uplift over oracle."
                )
                gr.Dataframe(
                    value=build_crossmodel_leaderboard(),
                    interactive=False, wrap=False,
                    column_widths=["70px", "180px", "110px", "110px", "110px", "90px", "120px"],
                )

                gr.Markdown("### Per-Task Breakdown (28 tasks)")
                with gr.Row():
                    cm_cat_dd = gr.Dropdown(
                        choices=cm_categories, value="All",
                        label="Category", scale=2,
                    )
                    cm_cls_dd = gr.Dropdown(
                        choices=classifications, value="All",
                        label="Classification", scale=2,
                    )

                cm_task_table = gr.Dataframe(
                    value=build_crossmodel_task_df(),
                    interactive=False, wrap=False,
                )

                def _update_cm_tasks(cat, cls):
                    return build_crossmodel_task_df(cat, cls)

                for w in [cm_cat_dd, cm_cls_dd]:
                    w.change(fn=_update_cm_tasks,
                             inputs=[cm_cat_dd, cm_cls_dd],
                             outputs=cm_task_table)

            # ==============================================================
            # TAB 2: About
            # ==============================================================
            with gr.Tab("About"):
                gr.HTML(create_about_html())

            # ==============================================================
            # TAB 3: Overview (all 155 tasks)
            # ==============================================================
            with gr.Tab("Overview"):
                gr.Markdown(
                    "### All 155 Tasks\n"
                    "Evaluated across 5 ablation conditions at seed 0. "
                    "Use **Track** to switch between Full (all) and Hard (hard + expert only)."
                )

                with gr.Row():
                    track_dd = gr.Dropdown(
                        choices=["Full", "Hard"],
                        value="Full", label="Track", scale=1,
                    )
                    cat_dd = gr.Dropdown(
                        choices=categories_all,
                        value="All", label="Category", scale=2,
                    )
                    class_dd = gr.Dropdown(
                        choices=classifications,
                        value="All", label="Classification", scale=2,
                    )

                task_table = gr.Dataframe(
                    value=build_overview_df(), interactive=False, wrap=False,
                )

                def _update_overview(track, cat, cls):
                    return build_overview_df(track, cat, cls)

                for w in [track_dd, cat_dd, class_dd]:
                    w.change(fn=_update_overview,
                             inputs=[track_dd, cat_dd, class_dd],
                             outputs=task_table)

                gr.Markdown("### Per-Category Summary")
                cat_summary = gr.Dataframe(
                    value=build_category_summary_df(), interactive=False, wrap=False,
                )

                def _update_cat_summary(track):
                    return build_category_summary_df(track)

                track_dd.change(fn=_update_cat_summary,
                                inputs=[track_dd], outputs=cat_summary)

            # ==============================================================
            # TAB 4: Submit
            # ==============================================================
            with gr.Tab("Submit"):
                gr.HTML("""
<div class="submit-info">
  <h3 style="margin:0 0 12px;">Submit Your Results</h3>
  <p>TeamBench uses <strong>server-side grading</strong> to ensure benchmark integrity.
  You submit workspace artifacts (the files your agent produced) &mdash;
  not self-reported scores. We grade them against hidden test suites.</p>
</div>
""")

                gr.HTML("""
<div class="submit-step">
  <h4>Step 1: Install and Run</h4>
  <pre style="background:#f3f4f6; padding:10px 14px; border-radius:6px; font-size:0.82rem; overflow-x:auto; margin:8px 0;">pip install teambench
teambench run --model your-model --seed 0 --output submission/</pre>
  <p style="font-size:0.85rem; color:#6b7280; margin:4px 0 0;">
    This runs your agent on all tasks and saves the workspace artifacts (files your agent wrote).
    You must run all 5 conditions: <code>oracle</code>, <code>restricted</code>, <code>full</code>,
    <code>team_no_plan</code>, <code>team_no_verify</code>.
  </p>
</div>

<div class="submit-step">
  <h4>Step 2: Package</h4>
  <pre style="background:#f3f4f6; padding:10px 14px; border-radius:6px; font-size:0.82rem; overflow-x:auto; margin:8px 0;">teambench package submission/ --output submission.zip</pre>
  <p style="font-size:0.85rem; color:#6b7280; margin:4px 0 0;">
    Creates a zip with the required structure. Partial submissions (subset of 155 tasks) are accepted.
  </p>
</div>

<div class="submit-step">
  <h4>Step 3: Upload</h4>
  <p style="font-size:0.85rem; color:#6b7280;">
    Fill in the fields below and upload your <code>submission.zip</code>.
    Results appear on the leaderboard after server-side grading (24-48 hours).
  </p>
</div>
""")

                gr.HTML("""
<details style="margin-bottom:16px;">
  <summary style="cursor:pointer; font-weight:600; font-size:0.9rem; padding:8px 0;">
    Expected zip structure
  </summary>
  <pre style="background:#f3f4f6; padding:12px 16px; border-radius:6px; font-size:0.82rem; margin-top:8px;">submission.zip/
  meta.json                        # auto-generated by teambench package
  tasks/
    S1_hidden_spec/
      oracle/workspace/            # workspace after oracle condition
      restricted/workspace/        # workspace after restricted condition
      full/workspace/              # workspace after full team condition
      team_no_plan/workspace/      # workspace after no-plan condition
      team_no_verify/workspace/    # workspace after no-verify condition
    D1_schema_drift/
      oracle/workspace/
      ...
    ...</pre>
</details>
""")

                with gr.Row():
                    model_input = gr.Textbox(
                        label="Model Name *",
                        placeholder="e.g. gpt-5, claude-opus-4, gemini-3-pro",
                        scale=2,
                    )
                    team_input = gr.Textbox(
                        label="Team / Organization *",
                        placeholder="e.g. OpenAI, Google DeepMind, your-lab-name",
                        scale=2,
                    )
                with gr.Row():
                    framework_input = gr.Textbox(
                        label="Framework (optional)",
                        placeholder="e.g. langgraph, crewai, google-adk, custom",
                        scale=2,
                    )
                    contact_input = gr.Textbox(
                        label="Contact Email (optional)",
                        placeholder="your@email.com",
                        scale=2,
                    )
                with gr.Row():
                    description_input = gr.Textbox(
                        label="Description (optional)",
                        placeholder="Brief description of your agent setup, tools used, etc.",
                        lines=2,
                        scale=3,
                    )
                    seed_input = gr.Textbox(
                        label="Seed",
                        value="0",
                        placeholder="0",
                        scale=1,
                    )

                file_input = gr.File(
                    label="Upload submission.zip (workspace artifacts, max 100 MB)",
                    file_types=[".zip"],
                )

                submit_btn = gr.Button("Submit for Grading", variant="primary")
                result_output = gr.Markdown("")

                submit_btn.click(
                    fn=validate_and_accept_submission,
                    inputs=[file_input, model_input, team_input,
                            framework_input, contact_input,
                            description_input, seed_input],
                    outputs=result_output,
                )

    return demo


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app = build_app()
    app.launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("PORT", 7860)),
        share=False,
    )
