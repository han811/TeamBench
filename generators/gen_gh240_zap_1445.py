"""
Parameterized generator for GH240_zap_1445.

Source PR:    https://github.com/uber-go/zap/pull/1445
Source Issue: N/A

Seed varies: renames 'cmdtest' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH240_zap_1445'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH240_zap_1445'
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
            task_id='GH240_zap_1445',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'uber-go/zap',
                "pr_number": 1445,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/uber-go/zap/pull/1445",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'tools/go.mod': 'module go.uber.org/zap/tools\n\nrequire golang.org/x/vuln v1.1.1\n\nrequire (\n\tgolang.org/x/mod v0.17.0 // indirect\n\tgolang.org/x/sync v0.7.0 // indirect\n\tgolang.org/x/tools v0.21.1-0.20240514024235-59d9797072e7 // indirect\n)\n\ngo 1.20\n',
            'tools/go.sum': 'github.com/google/go-cmdtest v0.4.1-0.20220921163831-55ab3332a786 h1:rcv+Ippz6RAtvaGgKxc+8FQIpxHgsF+HBzPyYL2cyVU=\ngithub.com/google/go-cmp v0.6.0 h1:ofyhxvXcZhMsU5ulbFiLKl/XBFqE1GSq7atu8tAmTRI=\ngithub.com/google/renameio v0.1.0 h1:GOZbcHa3HfsPKPlmyPyN2KEohoMXOhdMbHrvbpl2QaA=\ngolang.org/x/mod v0.17.0 h1:zY54UmvipHiNd+pm+m0x9KhZ9hl1/7QNMyxXbc6ICqA=\ngolang.org/x/mod v0.17.0/go.mod h1:hTbmBsO62+eylJbnUtE2MGJUyE7QWk4xUqPFrRgJ+7c=\ngolang.org/x/sync v0.7.0 h1:YsImfSBoP9QPYL0xyKJPq0gcaJdG3rInoqxTWbfQu9M=\ngolang.org/x/sync v0.7.0/go.mod h1:Czt+wKu1gCyEFDUtn0jG5QVvpJ6rzVqr5aXyt9drQfk=\ngolang.org/x/tools v0.21.1-0.20240514024235-59d9797072e7 h1:DnP3aRQn/r68glNGB8/7+3iE77jA+YZZCxpfIXx2MdA=\ngolang.org/x/tools v0.21.1-0.20240514024235-59d9797072e7/go.mod h1:aiJjzUbINMkxbQROHiO6hDPo2LHcIPhhQsa9DLh0yGk=\ngolang.org/x/vuln v1.1.1 h1:4nYQg4OSr7uYQMtjuuYqLAEVuTjY4k/CPMYqvv5OPcI=\ngolang.org/x/vuln v1.1.1/go.mod h1:hNgE+SKMSp2wHVUpW0Ow2ejgKpNJePdML+4YjxrVxik=\n',
        }
