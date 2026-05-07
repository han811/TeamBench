"""
Parameterized generator for GH184_zap_1432.

Source PR:    https://github.com/uber-go/zap/pull/1432
Source Issue: N/A

Seed varies: renames 'cmdtest' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH184_zap_1432'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH184_zap_1432'
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
            task_id='GH184_zap_1432',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'uber-go/zap',
                "pr_number": 1432,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/uber-go/zap/pull/1432",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'tools/go.mod': 'module go.uber.org/zap/tools\n\nrequire golang.org/x/vuln v1.0.1\n\nrequire (\n\tgolang.org/x/mod v0.12.0 // indirect\n\tgolang.org/x/sync v0.3.0 // indirect\n\tgolang.org/x/sys v0.11.0 // indirect\n\tgolang.org/x/tools v0.12.1-0.20230815132531-74c255bcf846 // indirect\n)\n\ngo 1.20\n',
            'tools/go.sum': 'github.com/google/go-cmdtest v0.4.1-0.20220921163831-55ab3332a786 h1:rcv+Ippz6RAtvaGgKxc+8FQIpxHgsF+HBzPyYL2cyVU=\ngithub.com/google/go-cmp v0.5.8 h1:e6P7q2lk1O+qJJb4BtCQXlK8vWEO8V1ZeuEdJNOqZyg=\ngithub.com/google/renameio v0.1.0 h1:GOZbcHa3HfsPKPlmyPyN2KEohoMXOhdMbHrvbpl2QaA=\ngolang.org/x/mod v0.12.0 h1:rmsUpXtvNzj340zd98LZ4KntptpfRHwpFOHG188oHXc=\ngolang.org/x/mod v0.12.0/go.mod h1:iBbtSCu2XBx23ZKBPSOrRkjjQPZFPuis4dIYUhu/chs=\ngolang.org/x/sync v0.3.0 h1:ftCYgMx6zT/asHUrPw8BLLscYtGznsLAnjq5RH9P66E=\ngolang.org/x/sync v0.3.0/go.mod h1:FU7BRWz2tNW+3quACPkgCx/L+uEAv1htQ0V83Z9Rj+Y=\ngolang.org/x/sys v0.11.0 h1:eG7RXZHdqOJ1i+0lgLgCpSXAp6M3LYlAo6osgSi0xOM=\ngolang.org/x/sys v0.11.0/go.mod h1:oPkhp1MJrh7nUepCBck5+mAzfO9JrbApNNgaTdGDITg=\ngolang.org/x/tools v0.12.1-0.20230815132531-74c255bcf846 h1:Vve/L0v7CXXuxUmaMGIEK/dEeq7uiqb5qBgQrZzIE7E=\ngolang.org/x/tools v0.12.1-0.20230815132531-74c255bcf846/go.mod h1:Sc0INKfu04TlqNoRA1hgpFZbhYXHPr4V5DzpSBTPqQM=\ngolang.org/x/vuln v1.0.1 h1:KUas02EjQK5LTuIx1OylBQdKKZ9jeugs+HiqO5HormU=\ngolang.org/x/vuln v1.0.1/go.mod h1:bb2hMwln/tqxg32BNY4CcxHWtHXuYa3SbIBmtsyjxtM=\n',
        }
