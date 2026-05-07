"""
Parameterized generator for GH142_tower_30.

Source PR:    https://github.com/tower-rs/tower/pull/30
Source Issue: https://github.com/tower-rs/tower/issues/21

Seed varies: renames 'backed' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH142_tower_30'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH142_tower_30'
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
                files[fpath] = files[fpath].replace('backed', 'backed' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH142_tower_30',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'tower-rs/tower',
                "pr_number": 30,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/tower-rs/tower/pull/30",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'tower-util/src/lib.rs': '//! Various utility types and functions that are generally with Tower.\n\nextern crate futures;\nextern crate tower;\n\npub mod either;\npub mod option;\npub mod boxed;\nmod service_fn;\n\npub use boxed::BoxService;\npub use either::EitherService;\npub use service_fn::NewServiceFn;\npub use option::OptionService;\n',
            'tower-util/src/service_fn.rs': 'use futures::IntoFuture;\nuse tower::{Service, NewService};\n\n/// A `NewService` implemented by a closure.\npub struct NewServiceFn<T> {\n    f: T,\n}\n\n// ===== impl NewServiceFn =====\n\nimpl<T, N> NewServiceFn<T>\nwhere T: Fn() -> N,\n      N: Service,\n{\n    /// Returns a new `NewServiceFn` with the given closure.\n    pub fn new(f: T) -> Self {\n        NewServiceFn { f }\n    }\n}\n\nimpl<T, R, S> NewService for NewServiceFn<T>\nwhere T: Fn() -> R,\n      R: IntoFuture<Item = S>,\n      S: Service,\n{\n    type Request = S::Request;\n    type Response = S::Response;\n    type Error = S::Error;\n    type Service = R::Item;\n    type InitError = R::Error;\n    type Future = R::Future;\n\n    fn new_service(&self) -> Self::Future {\n        (self.f)().into_future()\n    }\n}\n',
        }
