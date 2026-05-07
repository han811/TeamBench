"""
Parameterized generator for GH356_logrus_1496.

Source PR:    https://github.com/sirupsen/logrus/pull/1496
Source Issue: N/A

Seed varies: renames 'base' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH356_logrus_1496'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH356_logrus_1496'
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
                files[fpath] = files[fpath].replace('base', 'base' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH356_logrus_1496',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'sirupsen/logrus',
                "pr_number": 1496,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/sirupsen/logrus/pull/1496",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'entry_bench_test.go': 'package logrus_test\n\nimport (\n\t"errors"\n\t"testing"\n\n\t"github.com/sirupsen/logrus"\n)\n\nfunc BenchmarkEntry_WithError(b *testing.B) {\n\tbase := &logrus.Entry{Data: logrus.Fields{"a": 1}}\n\terrBoom := errors.New("boom")\n\tb.ReportAllocs()\n\tb.ResetTimer()\n\n\tfor i := 0; i < b.N; i++ {\n\t\t_ = base.WithError(errBoom)\n\t}\n}\n\nfunc BenchmarkEntry_WithField_Chain(b *testing.B) {\n\tbase := &logrus.Entry{Data: logrus.Fields{"a": 1}}\n\terrBoom := errors.New("boom")\n\tb.ReportAllocs()\n\tb.ResetTimer()\n\n\tfor i := 0; i < b.N; i++ {\n\t\te := base\n\n\t\te = e.WithField("k0", 0)\n\t\te = e.WithField("k1", 1)\n\t\te = e.WithField("k2", 2)\n\t\te = e.WithField("k3", 3)\n\t\te = e.WithError(errBoom)\n\t\t_ = e\n\t}\n}\n\nfunc BenchmarkEntry_WithFields(b *testing.B) {\n\tfn := func() {}\n\tfnPtr := &fn\n\n\ttests := []struct {\n\t\tname string\n\t\tbase logrus.Fields\n\t\tfields logrus.Fields\n\t}{\n\t\t{\n\t\t\tname:   "valid_fields_only",\n\t\t\tbase:   logrus.Fields{"a": 1, "b": "two"},\n\t\t\tfields: logrus.Fields{"c": 3, "d": "four"},\n\t\t},\n\t\t{\n\t\t\tname:   "contains_func",\n\t\t\tbase:   logrus.Fields{"a": 1},\n\t\t\tfields: logrus.Fields{"bad": fn},\n\t\t},\n\t\t{\n\t\t\tname:   "contains_func_ptr",\n\t\t\tbase:   logrus.Fields{"a": 1},\n\t\t\tfields: logrus.Fields{"bad": fnPtr},\n\t\t},\n\t\t{\n\t\t\tname:   "mixed_valid_invalid",\n\t\t\tbase:   logrus.Fields{"a": 1, "b": 2},\n\t\t\tfields: logrus.Fields{"c": 3, "bad": fn, "d": 4},\n\t\t},\n\t\t{\n\t\t\tname:   "larger_map",\n\t\t\tbase:   logrus.Fields{"a": 1, "b": 2, "c": 3, "d": 4, "e": 5, "f": 6, "g": 7, "h": 8, "i": 9, "j": 10},\n\t\t\tfields: logrus.Fields{"k": 11, "l": 12, "m": 13, "n": 14, "o": 15},\n\t\t},\n\t}\n\n\tfor _, tc := range tests {\n\t\tb.Run(tc.name, func(b *testing.B) {\n\t\t\tb.ReportAllocs()\n\t\t\te := &logrus.Entry{Data: tc.base}\n\t\t\tb.ResetTimer()\n\t\t\tfor i := 0; i < b.N; i++ {\n\t\t\t\t_ = e.WithFields(tc.fields)\n\t\t\t}\n\t\t})\n\t}\n}\n',
        }
