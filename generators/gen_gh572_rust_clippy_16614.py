"""
Parameterized generator for GH572_rust-clippy_16614.

Source PR:    https://github.com/rust-lang/rust-clippy/pull/16614
Source Issue: N/A

Seed varies: renames 'approve' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH572_rust-clippy_16614'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH572_rust-clippy_16614'
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
                files[fpath] = files[fpath].replace('approve', 'approve' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH572_rust-clippy_16614',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'rust-lang/rust-clippy',
                "pr_number": 16614,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/rust-lang/rust-clippy/pull/16614",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'triagebot.toml': '[relabel]\nallow-unauthenticated = [\n    "A-*", "C-*", "E-*", "I-*", "L-*", "P-*", "S-*", "T-*",\n    "good first issue", "beta-nominated"\n]\n\n# Allows shortcuts like `@rustbot ready`\n#\n# See https://forge.rust-lang.org/triagebot/shortcuts.html\n[shortcut]\n\n[merge-conflicts]\n\n[note]\n\n[close]\n\n[transfer]\n\n[issue-links]\n\n[mentions."clippy_lints/src/doc"]\ncc = ["@notriddle"]\n\n# Have rustbot inform users about the *No Merge Policy*\n[no-merges]\nexclude_titles = ["Rustup"] # exclude syncs from rust-lang/rust\nlabels = ["has-merge-commits", "S-waiting-on-author"]\n\n[review-requested]\n# Those labels are removed when PR author requests a review from an assignee\nremove_labels = ["S-waiting-on-author"]\n# Those labels are added when PR author requests a review from an assignee\nadd_labels = ["S-waiting-on-review"]\n\n[review-submitted]\n# These labels are removed when a review is submitted.\nreview_labels = ["S-waiting-on-review"]\n# This label is added when a review is submitted.\nreviewed_label = "S-waiting-on-author"\n\n[autolabel."S-waiting-on-review"]\nnew_pr = true\n\n[autolabel."needs-fcp"]\ntrigger_files = ["clippy_lints/src/declared_lints.rs"]\n\n[concern]\n# These labels are set when there are unresolved concerns, removed otherwise\nlabels = ["S-waiting-on-concerns"]\n\n# Show differences when a PR is rebased\n[range-diff]\n\n# Amend a review to include a link to what was changed since the review\n[review-changes-since]\n\n# Adds a "View all comments" link on the issue/PR body that shows all the comments of it\n# Documentation at: https://forge.rust-lang.org/triagebot/view-all-comments-link.html\n[view-all-comments-link]\nthreshold = 20\n\n[assign]\ncontributing_url = "https://github.com/rust-lang/rust-clippy/blob/master/CONTRIBUTING.md"\nusers_on_vacation = [\n    "matthiaskrgr",\n    "Manishearth",\n    "Alexendoo",\n    "y21",\n    "blyxyas",\n]\n\n[assign.owners]\n"/.github" = ["@flip1995"]\n"/triagebot.toml" = ["@flip1995"]\n"/book" = ["@flip1995"]\n"*" = [\n    "@Manishearth",\n    "@llogiq",\n    "@Alexendoo",\n    "@dswij",\n    "@Jarcho",\n    "@y21",\n    "@samueltardieu",\n]\n',
        }
