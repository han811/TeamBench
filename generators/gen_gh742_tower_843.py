"""
Parameterized generator for GH742_tower_843.

Source PR:    https://github.com/tower-rs/tower/pull/843
Source Issue: N/A

Seed varies: renames 'clone' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH742_tower_843'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH742_tower_843'
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
                files[fpath] = files[fpath].replace('clone', 'clone' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH742_tower_843',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'tower-rs/tower',
                "pr_number": 843,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/tower-rs/tower/pull/843",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'tower/src/retry/backoff.rs': '//! This module contains generic [backoff] utilities to be used with the retry\n//! layer.\n//!\n//! The [`Backoff`] trait is a generic way to represent backoffs that can use\n//! any timer type.\n//!\n//! [`ExponentialBackoffMaker`] implements the maker type for  \n//! [`ExponentialBackoff`] which implements the [`Backoff`] trait and provides\n//! a batteries included exponential backoff and jitter strategy.\n//!\n//! [backoff]: https://en.wikipedia.org/wiki/Exponential_backoff\n\nuse std::fmt::Display;\nuse std::future::Future;\nuse std::time::Duration;\nuse tokio::time;\n\nuse crate::util::rng::{HasherRng, Rng};\n\n/// Trait used to construct [`Backoff`] trait implementors.\npub trait MakeBackoff {\n    /// The backoff type produced by this maker.\n    type Backoff: Backoff;\n\n    /// Constructs a new backoff type.\n    fn make_backoff(&mut self) -> Self::Backoff;\n}\n\n/// A backoff trait where a single mutable reference represents a single\n/// backoff session. Implementors must also implement [`Clone`] which will\n/// reset the backoff back to the default state for the next session.\npub trait Backoff {\n    /// The future associated with each backoff. This usually will be some sort\n    /// of timer.\n    type Future: Future<Output = ()>;\n\n    /// Initiate the next backoff in the sequence.\n    fn next_backoff(&mut self) -> Self::Future;\n}\n\n/// A maker type for [`ExponentialBackoff`].\n#[derive(Debug, Clone)]\npub struct ExponentialBackoffMaker<R = HasherRng> {\n    /// The minimum amount of time to wait before resuming an operation.\n    min: time::Duration,\n    /// The maximum amount of time to wait before resuming an operation.\n    max: time::Duration,\n    /// The ratio of the base timeout that may be randomly added to a backoff.\n    ///\n    /// Must be greater than or equal to 0.0.\n    jitter: f64,\n    rng: R,\n}\n\n/// A jittered [exponential backoff] strategy.\n///\n/// The backoff duration will increase exponentially for every subsequent\n/// backoff, up to a maximum duration. A small amount of [random jitter] is\n/// added to each backoff duration, in order to avoid retry spikes.\n///\n/// [exponential backoff]: https://en.wikipedia.org/wiki/Exponential_backoff\n/// [random jitter]: https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/\n#[derive(Debug, Clone)]\npub struct ExponentialBackoff<R = HasherRng> {\n    min: time::Duration,\n    max: time::Duration,\n    jitter: f64,\n    rng: R,\n    iterations: u32,\n}\n\nimpl<R> ExponentialBackoffMaker<R>\nwhere\n    R: Rng,\n{\n    /// Create a new `ExponentialBackoff`.\n    ///\n    /// # Error\n    ///\n    /// Returns a config validation error if:\n    /// - `min` > `max`\n    /// - `max` == 0\n    /// - `jitter` < `0.0`\n    /// - `jitter` > `100.0`\n    /// - `jitter` is not finite\n    pub fn new(\n        min: time::Duration,\n        max: time::Duration,\n        jitter: f64,\n        rng: R,\n    ) -> Result<Self, InvalidBackoff> {\n        if min > max {\n            return Err(InvalidBackoff("maximum must not be less than minimum"));\n        }\n        if max == time::Duration::from_millis(0) {\n            return Err(InvalidBackoff("maximum must be non-zero"));\n        }\n        if jitter < 0.0 {\n            return Err(InvalidBackoff("jitter must not be negative"));\n        }\n        if jitter > 100.0 {\n            return Err(InvalidBackoff("jitter must not be greater than 100"));\n        }\n        if !jitter.is_finite() {\n            return Err(InvalidBackoff("jitter must be finite"));\n        }\n\n        Ok(ExponentialBackoffMaker {\n            min,\n            max,\n            jitter,\n            rng,\n        })\n    }\n}\n\nimpl<R> MakeBackoff for ExponentialBackoffMaker<R>\nwhere\n    R: Rng + Clone,\n{\n    type Backoff = ExponentialBackoff<R>;\n\n    fn make_backoff(&mut self) -> Self::Backoff {\n        ExponentialBackoff {\n            max: self.max,\n            min: self.min,\n            jitter: self.jitter,\n            rng: self.rng.clone(),\n            iterations: 0,\n        }\n    }\n}\n\nimpl<R: Rng> ExponentialBackoff<R> {\n    fn base(&self) -> time::Duration {\n        debug_assert!(\n            self.min <= self.max,\n            "maximum backoff must not be less than minimum backoff"\n        );\n        debug_assert!(\n            self.max > time::Duration::from_millis(0),\n            "Maximum backoff must be non-zero"\n        );\n        self.min\n            .checked_mul(2_u32.saturating_pow(self.iterations))\n            .unwrap_or(self.max)\n            .min(self.max)\n    }\n\n    /// Returns a random, uniform duration on `[0, base*self.jitter]` no greater\n    /// than `self.max`.\n    fn jitter(&mut self, base: time::Duration) -> time::Duration {\n        if self.jitter == 0.0 {\n            time::Duration::default()\n        } else {\n            let jitter_factor = self.rng.next_f64();\n            debug_assert!(\n                jitter_factor > 0.0,\n                "rng returns values between 0.0 and 1.0"\n            );\n            let rand_jitter = jitter_factor * self.jitter;\n            let secs = (base.as_secs() as f64) * rand_jitter;\n            let nanos = (base.subsec_nanos() as f64) * rand_jitter;\n            let remaining = self.max - base;\n            time::Duration::new(secs as u64, nanos as u32).min(remaining)\n        }\n    }\n}\n\nimpl<R> Backoff for ExponentialBackoff<R>\nwhere\n    R: Rng,\n{\n    type Future = tokio::time::Sleep;\n\n    fn next_backoff(&mut self) -> Self::Future {\n        let base = self.base();\n        let next = base + self.jitter(base);\n\n        self.iterations += 1;\n\n        tokio::time::sleep(next)\n    }\n}\n\nimpl Default for ExponentialBackoffMaker {\n    fn default() -> Self {\n        ExponentialBackoffMaker::new(\n            Duration::from_millis(50),\n            Duration::from_millis(u64::MAX),\n            0.99,\n            HasherRng::default(),\n        )\n        .expect("Unable to create ExponentialBackoff")\n    }\n}\n\n/// Backoff validation error.\n#[derive(Debug)]\npub struct InvalidBackoff(&\'static str);\n\nimpl Display for InvalidBackoff {\n    fn fmt(&self, f: &mut std::fmt::Formatter<\'_>) -> std::fmt::Result {\n        write!(f, "invalid backoff: {}", self.0)\n    }\n}\n\nimpl std::error::Error for InvalidBackoff {}\n\n#[cfg(test)]\nmod tests {\n    use super::*;\n    use quickcheck::*;\n\n    quickcheck! {\n        fn backoff_base_first(min_ms: u64, max_ms: u64) -> TestResult {\n            let min = time::Duration::from_millis(min_ms);\n            let max = time::Duration::from_millis(max_ms);\n            let rng = HasherRng::default();\n            let mut backoff = match ExponentialBackoffMaker::new(min, max, 0.0, rng) {\n                Err(_) => return TestResult::discard(),\n                Ok(backoff) => backoff,\n            };\n            let backoff = backoff.make_backoff();\n\n            let delay = backoff.base();\n            TestResult::from_bool(min == delay)\n        }\n\n        fn backoff_base(min_ms: u64, max_ms: u64, iterations: u32) -> TestResult {\n            let min = time::Duration::from_millis(min_ms);\n            let max = time::Duration::from_millis(max_ms);\n            let rng = HasherRng::default();\n            let mut backoff = match ExponentialBackoffMaker::new(min, max, 0.0, rng) {\n                Err(_) => return TestResult::discard(),\n                Ok(backoff) => backoff,\n            };\n            let mut backoff = backoff.make_backoff();\n\n            backoff.iterations = iterations;\n            let delay = backoff.base();\n            TestResult::from_bool(min <= delay && delay <= max)\n        }\n\n        fn backoff_jitter(base_ms: u64, max_ms: u64, jitter: f64) -> TestResult {\n            let base = time::Duration::from_millis(base_ms);\n            let max = time::Duration::from_millis(max_ms);\n            let rng = HasherRng::default();\n            let mut backoff = match ExponentialBackoffMaker::new(base, max, jitter, rng) {\n                Err(_) => return TestResult::discard(),\n                Ok(backoff) => backoff,\n            };\n            let mut backoff = backoff.make_backoff();\n\n            let j = backoff.jitter(base);\n            if jitter == 0.0 || base_ms == 0 || max_ms == base_ms {\n                TestResult::from_bool(j == time::Duration::default())\n            } else {\n                TestResult::from_bool(j > time::Duration::default())\n            }\n        }\n    }\n}\n',
        }
