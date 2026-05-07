"""
Parameterized generator for GH229_zap_1440.

Source PR:    https://github.com/uber-go/zap/pull/1440
Source Issue: N/A

Seed varies: renames 'cmdtest' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH229_zap_1440'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH229_zap_1440'
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
                files[fpath] = files[fpath].replace('cmdtest', 'cmdtest' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH229_zap_1440',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'uber-go/zap',
                "pr_number": 1440,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/uber-go/zap/pull/1440",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'tools/go.mod': 'module go.uber.org/zap/tools\n\nrequire golang.org/x/vuln v1.1.0\n\nrequire (\n\tgolang.org/x/mod v0.17.0 // indirect\n\tgolang.org/x/sync v0.7.0 // indirect\n\tgolang.org/x/tools v0.20.0 // indirect\n)\n\ngo 1.20\n',
            'tools/go.sum': 'github.com/google/go-cmdtest v0.4.1-0.20220921163831-55ab3332a786 h1:rcv+Ippz6RAtvaGgKxc+8FQIpxHgsF+HBzPyYL2cyVU=\ngithub.com/google/go-cmp v0.5.8 h1:e6P7q2lk1O+qJJb4BtCQXlK8vWEO8V1ZeuEdJNOqZyg=\ngithub.com/google/renameio v0.1.0 h1:GOZbcHa3HfsPKPlmyPyN2KEohoMXOhdMbHrvbpl2QaA=\ngolang.org/x/mod v0.17.0 h1:zY54UmvipHiNd+pm+m0x9KhZ9hl1/7QNMyxXbc6ICqA=\ngolang.org/x/mod v0.17.0/go.mod h1:hTbmBsO62+eylJbnUtE2MGJUyE7QWk4xUqPFrRgJ+7c=\ngolang.org/x/sync v0.7.0 h1:YsImfSBoP9QPYL0xyKJPq0gcaJdG3rInoqxTWbfQu9M=\ngolang.org/x/sync v0.7.0/go.mod h1:Czt+wKu1gCyEFDUtn0jG5QVvpJ6rzVqr5aXyt9drQfk=\ngolang.org/x/tools v0.20.0 h1:hz/CVckiOxybQvFw6h7b/q80NTr9IUQb4s1IIzW7KNY=\ngolang.org/x/tools v0.20.0/go.mod h1:WvitBU7JJf6A4jOdg4S1tviW9bhUxkgeCui/0JHctQg=\ngolang.org/x/vuln v1.1.0 h1:ECEdI+aEtjpF90eqEcDL5Q11DWSZAw5PJQWlp0+gWqc=\ngolang.org/x/vuln v1.1.0/go.mod h1:HT/Ar8fE34tbxWG2s7PYjVl+iIE4Er36/940Z+K540Y=\n',
        }
