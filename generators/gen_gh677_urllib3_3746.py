"""
Parameterized generator for GH677_urllib3_3746.

Source PR:    https://github.com/urllib3/urllib3/pull/3746
Source Issue: N/A

Seed varies: renames 'after' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH677_urllib3_3746'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH677_urllib3_3746'
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
                files[fpath] = files[fpath].replace('after', 'after' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH677_urllib3_3746',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'urllib3/urllib3',
                "pr_number": 3746,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/urllib3/urllib3/pull/3746",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            '.github/SECURITY.md': '# Security Policy\n\n## Reporting a Vulnerability\n\nTo report a security vulnerability, please use the [Tidelift security contact](https://tidelift.com/security).\nTidelift will coordinate the fix and disclosure with maintainers.\n\n> [!WARNING]\n> Please do **not** file a public GitHub issue for security reports.\n\nWhen reporting, if possible, include:\n- A clear description of the issue and potential impact\n- Steps to reproduce or a proof of concept\n- Affected urllib3 version(s) and environment details\n- Any suggested mitigations\n\nWe typically acknowledge reports within a few business days.\n\n\n## Supported Versions\n\nOnly the main branch (the 2.x release line) receives updates, including\nsecurity fixes. Older release lines (e.g., 1.x) are not maintained. If you are\nusing an older version, please upgrade to the latest 2.x release to receive\nfixes.\n\nWhen reporting a potential vulnerability, confirm that it reproduces against\nthe latest 2.x version.\n\n\n## Our Process\n\nWe follow the [Tidelift security process](https://support.tidelift.com/hc/en-us/articles/4406287910036-Security-process)\nfor coordinated vulnerability disclosure. In brief:\n- Intake and triage: Reports are received privately via Tidelift, validated,\n  and scoped (affected versions, severity).\n- Private coordination: Tidelift facilitates communication between the reporter\n  and the urllib3 maintainers.\n- Fix and review: We develop, review, and prepare patches (including backports\n  to supported versions when appropriate) and mitigation guidance.\n- Timeline and embargo: We agree on a reasonable disclosure timeline based on\n  impact and fix complexity; timelines may be accelerated for active\n  exploitation or extended for complex fixes.\n- CVE and advisory: We request and manage CVE IDs via GitHub Security\n  Advisories and prepare public guidance. If desired, we credit the reporter\n  and involved maintainers in the advisory.\n- Coordinated release: We publish patched releases and the advisory at the\n  agreed time.\n\n\n## Advisories and CVEs\n\nWe publish our security advisories on GitHub at [the following page](https://github.com/urllib3/urllib3/security/advisories).\nWe request and manage CVE IDs using GitHub Security Advisories, and published\nadvisories include CVE identifiers (when assigned) and severity information.\n\nTo receive notifications when new advisories are published, open the repository\npage, choose *Watch* → *Custom*, and enable *Security alerts*. You can also\nenable *Releases* to be notified when patched versions are published.\n',
        }
