"""
Parameterized generator for GH239_zap_1453.

Source PR:    https://github.com/uber-go/zap/pull/1453
Source Issue: N/A

Seed varies: renames 'cmdtest' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH239_zap_1453'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH239_zap_1453'
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
            task_id='GH239_zap_1453',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'uber-go/zap',
                "pr_number": 1453,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/uber-go/zap/pull/1453",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'tools/go.mod': 'module go.uber.org/zap/tools\n\nrequire golang.org/x/vuln v1.1.2\n\nrequire (\n\tgolang.org/x/mod v0.18.0 // indirect\n\tgolang.org/x/sync v0.7.0 // indirect\n\tgolang.org/x/sys v0.21.0 // indirect\n\tgolang.org/x/telemetry v0.0.0-20240522233618-39ace7a40ae7 // indirect\n\tgolang.org/x/tools v0.22.0 // indirect\n)\n\ngo 1.20\n',
            'tools/go.sum': 'github.com/google/go-cmdtest v0.4.1-0.20220921163831-55ab3332a786 h1:rcv+Ippz6RAtvaGgKxc+8FQIpxHgsF+HBzPyYL2cyVU=\ngithub.com/google/go-cmp v0.6.0 h1:ofyhxvXcZhMsU5ulbFiLKl/XBFqE1GSq7atu8tAmTRI=\ngithub.com/google/renameio v0.1.0 h1:GOZbcHa3HfsPKPlmyPyN2KEohoMXOhdMbHrvbpl2QaA=\ngolang.org/x/mod v0.18.0 h1:5+9lSbEzPSdWkH32vYPBwEpX8KwDbM52Ud9xBUvNlb0=\ngolang.org/x/mod v0.18.0/go.mod h1:hTbmBsO62+eylJbnUtE2MGJUyE7QWk4xUqPFrRgJ+7c=\ngolang.org/x/sync v0.7.0 h1:YsImfSBoP9QPYL0xyKJPq0gcaJdG3rInoqxTWbfQu9M=\ngolang.org/x/sync v0.7.0/go.mod h1:Czt+wKu1gCyEFDUtn0jG5QVvpJ6rzVqr5aXyt9drQfk=\ngolang.org/x/sys v0.21.0 h1:rF+pYz3DAGSQAxAu1CbC7catZg4ebC4UIeIhKxBZvws=\ngolang.org/x/sys v0.21.0/go.mod h1:/VUhepiaJMQUp4+oa/7Zr1D23ma6VTLIYjOOTFZPUcA=\ngolang.org/x/telemetry v0.0.0-20240522233618-39ace7a40ae7 h1:FemxDzfMUcK2f3YY4H+05K9CDzbSVr2+q/JKN45pey0=\ngolang.org/x/telemetry v0.0.0-20240522233618-39ace7a40ae7/go.mod h1:pRgIJT+bRLFKnoM1ldnzKoxTIn14Yxz928LQRYYgIN0=\ngolang.org/x/tools v0.22.0 h1:gqSGLZqv+AI9lIQzniJ0nZDRG5GBPsSi+DRNHWNz6yA=\ngolang.org/x/tools v0.22.0/go.mod h1:aCwcsjqvq7Yqt6TNyX7QMU2enbQ/Gt0bo6krSeEri+c=\ngolang.org/x/vuln v1.1.2 h1:UkLxe+kAMcrNBpGrFbU0Mc5l7cX97P2nhy21wx5+Qbk=\ngolang.org/x/vuln v1.1.2/go.mod h1:2o3fRKD8Uz9AraAL3lwd/grWBv+t+SeJnPcqBUJrY24=\n',
        }
