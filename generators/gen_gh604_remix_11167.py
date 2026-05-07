"""
Parameterized generator for GH604_remix_11167.

Source PR:    https://github.com/remix-run/remix/pull/11167
Source Issue: N/A

Seed varies: renames 'addressed' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH604_remix_11167'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH604_remix_11167'
        )
        with open(os.path.join(tasks_dir, "spec.md")) as f:
            spec_md = f.read()
        with open(os.path.join(tasks_dir, "brief.md")) as f:
            brief_md = f.read()

        files = self._base_workspace()
        # Apply seed-based renaming to prevent direct memorization
        suffixes = ["", "_alt", "_impl"]
        suffix = suffixes[seed % len(suffixes)]
        if suffix:
            for fpath in list(files.keys()):
                files[fpath] = files[fpath].replace('addressed', 'addressed' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH604_remix_11167',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'remix-run/remix',
                "pr_number": 11167,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/remix-run/remix/pull/11167",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            '.agents/skills/make-pr/SKILL.md': '---\nname: make-pr\ndescription: Create GitHub pull requests with clear, reviewer-friendly descriptions. Use when asked to open or prepare a PR, especially when the PR needs strong context, related links, and feature usage examples. This skill enforces concise PR structure, avoids redundant sections like validation/testing, and creates the PR with gh CLI.\n---\n\n# Make PR\n\n## Overview\n\nUse this skill to draft and open a PR with consistent, high-signal writing.\nKeep headings sparse and focus on the problem/feature explanation, context links, and practical code examples.\n\n## Workflow\n\n1. Gather context from branch diff and related work.\n\n- Capture what changed, why it changed, and who it affects.\n- Find related issues/PRs and include links when relevant.\n\n1. Draft the PR body with minimal structure.\n\n- Start with 1-2 short introductory paragraphs.\n- In those intro paragraphs, include clear bullets describing:\n  - the feature and/or issue addressed\n  - key behavior/API changes\n  - expected impact\n- If the change is extensive, expand to up to 3-4 paragraphs and include background context with related links.\n\n1. Add required usage examples for feature work.\n\n- If the PR introduces a new feature, include a comprehensive usage snippet.\n- If it replaces or improves an older approach, include before/after examples.\n\n1. Exclude redundant sections.\n\n- Do not include `Validation`, `Testing`, or other process sections that are already implicit in PR workflow.\n- Do not add boilerplate sections that do not help review.\n\n1. Create the PR.\n\n- Save the body to a temporary file and run:\n\n```bash\ngh pr create --base main --head <branch> --title "<title>" --body-file <file>\n```\n\n## Body Template\n\nUse this as a base and fill with concrete repo-specific details:\n\n````md\n<One or two short intro paragraphs explaining the change and why it matters.>\n\n- <Feature/issue addressed>\n- <What changed in behavior or API>\n- <Why this is needed now>\n\n<Optional additional context paragraph(s), up to 3-4 total for large changes, including links to related PRs/issues.>\n\n```ts\n// New feature usage example\n```\n````\n\n```ts\n// Before\n```\n\n```ts\n// After\n```\n\n```\n\n```\n',
        }
