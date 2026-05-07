"""
Parameterized generator for GH375_tokio_7944.

Source PR:    https://github.com/tokio-rs/tokio/pull/7944
Source Issue: N/A

Seed varies: renames 'across' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH375_tokio_7944'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH375_tokio_7944'
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
                files[fpath] = files[fpath].replace('across', 'across' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH375_tokio_7944',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'tokio-rs/tokio',
                "pr_number": 7944,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/tokio-rs/tokio/pull/7944",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'benches/Cargo.toml': '[package]\nname = "benches"\nversion = "0.0.0"\npublish = false\nedition = "2021"\nlicense = "MIT"\n\n[features]\ntest-util = ["tokio/test-util"]\n\n[dependencies]\ntokio = { version = "1.5.0", path = "../tokio", features = ["full"] }\ncriterion = "0.5.1"\nrand = "0.9"\nrand_chacha = "0.9"\n\n[dev-dependencies]\ntokio-util = { version = "0.7.0", path = "../tokio-util", features = ["full"] }\ntokio-stream = { version = "0.1", path = "../tokio-stream" }\n\n[target.\'cfg(unix)\'.dependencies]\nlibc = "0.2.42"\n\n[[bench]]\nname = "spawn"\npath = "spawn.rs"\nharness = false\n\n[[bench]]\nname = "sync_broadcast"\npath = "sync_broadcast.rs"\nharness = false\n\n[[bench]]\nname = "sync_mpsc"\npath = "sync_mpsc.rs"\nharness = false\n\n[[bench]]\nname = "sync_mpsc_oneshot"\npath = "sync_mpsc_oneshot.rs"\nharness = false\n\n[[bench]]\nname = "sync_watch"\npath = "sync_watch.rs"\nharness = false\n\n[[bench]]\nname = "rt_current_thread"\npath = "rt_current_thread.rs"\nharness = false\n\n[[bench]]\nname = "rt_multi_threaded"\npath = "rt_multi_threaded.rs"\nharness = false\n\n[[bench]]\nname = "sync_notify"\npath = "sync_notify.rs"\nharness = false\n\n[[bench]]\nname = "sync_rwlock"\npath = "sync_rwlock.rs"\nharness = false\n\n[[bench]]\nname = "sync_semaphore"\npath = "sync_semaphore.rs"\nharness = false\n\n[[bench]]\nname = "signal"\npath = "signal.rs"\nharness = false\n\n[[bench]]\nname = "fs"\npath = "fs.rs"\nharness = false\n\n[[bench]]\nname = "copy"\npath = "copy.rs"\nharness = false\n\n[[bench]]\nname = "time_now"\npath = "time_now.rs"\nharness = false\n\n[[bench]]\nname = "time_timeout"\npath = "time_timeout.rs"\nharness = false\n\n[[bench]]\nname = "spawn_blocking"\npath = "spawn_blocking.rs"\nharness = false\n\n[lints]\nworkspace = true\n',
        }
