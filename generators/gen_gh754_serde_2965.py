"""
Parameterized generator for GH754_serde_2965.

Source PR:    https://github.com/serde-rs/serde/pull/2965
Source Issue: N/A

Seed varies: renames 'alloc' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH754_serde_2965'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH754_serde_2965'
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
                files[fpath] = files[fpath].replace('alloc', 'alloc' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH754_serde_2965',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'serde-rs/serde',
                "pr_number": 2965,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/serde-rs/serde/pull/2965",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'serde/Cargo.toml': '[package]\nname = "serde"\nversion = "1.0.219"\nauthors = ["Erick Tryzelaar <erick.tryzelaar@gmail.com>", "David Tolnay <dtolnay@gmail.com>"]\nbuild = "build.rs"\ncategories = ["encoding", "no-std", "no-std::no-alloc"]\ndescription = "A generic serialization/deserialization framework"\ndocumentation = "https://docs.rs/serde"\nedition = "2021"\nhomepage = "https://serde.rs"\nkeywords = ["serde", "serialization", "no_std"]\nlicense = "MIT OR Apache-2.0"\nreadme = "crates-io.md"\nrepository = "https://github.com/serde-rs/serde"\nrust-version = "1.56"\n\n[dependencies]\nserde_core = { version = "=1.0.219", path = "../serde_core", default-features = false }\nserde_derive = { version = "1", optional = true, path = "../serde_derive" }\n\n[dev-dependencies]\nserde_derive = { version = "1", path = "../serde_derive" }\n\n[package.metadata.playground]\nfeatures = ["derive", "rc", "result"]\n\n[package.metadata.docs.rs]\nfeatures = ["derive", "rc", "result", "unstable"]\ntargets = ["x86_64-unknown-linux-gnu"]\nrustdoc-args = [\n    "--generate-link-to-definition",\n    "--extern-html-root-url=core=https://doc.rust-lang.org",\n    "--extern-html-root-url=alloc=https://doc.rust-lang.org",\n    "--extern-html-root-url=std=https://doc.rust-lang.org",\n]\n\n# This cfg cannot be enabled, but it still forces Cargo to keep serde_derive\'s\n# version in lockstep with serde\'s, even if someone depends on the two crates\n# separately with serde\'s "derive" feature disabled. Every serde_derive release\n# is compatible with exactly one serde release because the generated code\n# involves nonpublic APIs which are not bound by semver.\n[target.\'cfg(any())\'.dependencies]\nserde_derive = { version = "=1.0.219", path = "../serde_derive" }\n\n\n### FEATURES #################################################################\n\n[features]\ndefault = ["std", "result"]\n\n# Provide derive(Serialize, Deserialize) macros.\nderive = ["serde_derive"]\n\n# Provide impls for common standard library types like Vec<T> and HashMap<K, V>.\n# Requires a dependency on the Rust standard library.\nstd = ["serde_core/std"]\n\n# Provide impls for types that require unstable functionality. For tracking and\n# discussion of unstable functionality please refer to this issue:\n#\n#    https://github.com/serde-rs/serde/issues/812\nunstable = ["serde_core/unstable"]\n\n# Provide impls for types in the Rust core allocation and collections library\n# including String, Box<T>, Vec<T>, and Cow<T>. This is a subset of std but may\n# be enabled without depending on all of std.\nalloc = ["serde_core/alloc"]\n\n# Opt into impls for Rc<T> and Arc<T>. Serializing and deserializing these types\n# does not preserve identity and may result in multiple copies of the same data.\n# Be sure that this is what you want before enabling this feature.\nrc = ["serde_core/rc"]\n\n# Provide impls for Result<T, E>. Convenient in some contexts but can lead to\n# confusion if ? or unwrap are used incautiously.\nresult = ["serde_core/result"]\n',
        }
