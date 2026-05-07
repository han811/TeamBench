"""
Parameterized generator for GH671_tokio_7943.

Source PR:    https://github.com/tokio-rs/tokio/pull/7943
Source Issue: N/A

Seed varies: renames 'authors' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH671_tokio_7943'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH671_tokio_7943'
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
                files[fpath] = files[fpath].replace('authors', 'authors' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH671_tokio_7943',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'tokio-rs/tokio',
                "pr_number": 7943,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/tokio-rs/tokio/pull/7943",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'tokio-macros/CHANGELOG.md': "# 2.6.0 (Oct 14th, 2025)\n\nThe MSRV is raised to 1.71.\n\n- msrv: increase MSRV to 1.71 ([#7658])\n- macros: add `local` runtime flavor ([#7375], [#7597])\n- macros: suppress `clippy::unwrap_in_result` in `#[tokio::main]` ([#7651])\n\n[#7375]: https://github.com/tokio-rs/tokio/pull/7375\n[#7597]: https://github.com/tokio-rs/tokio/pull/7597\n[#7651]: https://github.com/tokio-rs/tokio/pull/7651\n[#7658]: https://github.com/tokio-rs/tokio/pull/7658\n\n# 2.5.0 (Jan 8th, 2025)\n\n- macros: suppress `clippy::needless_return` in `#[tokio::main]` ([#6874])\n\n[#6874]: https://github.com/tokio-rs/tokio/pull/6874\n\n# 2.4.0 (July 22nd, 2024)\n\n- msrv: increase MSRV to 1.70 ([#6645])\n- macros: allow `unhandled_panic` behavior for `#[tokio::main]` and `#[tokio::test]` ([#6593])\n\n[#6593]: https://github.com/tokio-rs/tokio/pull/6593\n[#6645]: https://github.com/tokio-rs/tokio/pull/6645\n\n# 2.3.0 (May 30th, 2024)\n\n- macros: make `#[tokio::test]` append `#[test]` at the end of the attribute list ([#6497])\n\n[#6497]: https://github.com/tokio-rs/tokio/pull/6497\n\n# 2.2.0 (November 19th, 2023)\n\n### Changed\n\n- use `::core` qualified imports instead of `::std` inside `tokio::test` macro ([#5973])\n\n[#5973]: https://github.com/tokio-rs/tokio/pull/5973\n\n# 2.1.0 (April 25th, 2023)\n\n- macros: fix typo in `#[tokio::test]` docs ([#5636])\n- macros: make entrypoints more efficient ([#5621])\n\n[#5621]: https://github.com/tokio-rs/tokio/pull/5621\n[#5636]: https://github.com/tokio-rs/tokio/pull/5636\n\n# 2.0.0 (March 24th, 2023)\n\nThis major release updates the dependency on the syn crate to 2.0.0, and\nincreases the MSRV to 1.56.\n\nAs part of this release, we are adopting a policy of depending on a specific minor\nrelease of tokio-macros. This prevents Tokio from being able to pull in many different\nversions of tokio-macros.\n\n- macros: update `syn` ([#5572])\n- macros: accept path as crate rename ([#5557])\n\n[#5572]: https://github.com/tokio-rs/tokio/pull/5572\n[#5557]: https://github.com/tokio-rs/tokio/pull/5557\n\n# 1.8.2 (November 30th, 2022)\n\n- fix a regression introduced in 1.8.1 ([#5244])\n\n[#5244]: https://github.com/tokio-rs/tokio/pull/5244\n\n# 1.8.1 (November 29th, 2022)\n\n(yanked)\n\n- macros: Pin Futures in `#[tokio::test]` to stack ([#5205])\n- macros: Reduce usage of last statement spans in proc-macros ([#5092])\n- macros: Improve the documentation for `#[tokio::test]` ([#4761])\n\n[#5205]: https://github.com/tokio-rs/tokio/pull/5205\n[#5092]: https://github.com/tokio-rs/tokio/pull/5092\n[#4761]: https://github.com/tokio-rs/tokio/pull/4761\n\n# 1.8.0 (June 4th, 2022)\n\n- macros: always emit return statement ([#4636])\n- macros: support setting a custom crate name for `#[tokio::main]` and `#[tokio::test]` ([#4613])\n\n[#4613]: https://github.com/tokio-rs/tokio/pull/4613\n[#4636]: https://github.com/tokio-rs/tokio/pull/4636\n\n# 1.7.0 (December 15th, 2021)\n\n- macros: address remaining `clippy::semicolon_if_nothing_returned` warning ([#4252])\n\n[#4252]: https://github.com/tokio-rs/tokio/pull/4252\n\n# 1.6.0 (November 16th, 2021)\n\n- macros: fix mut patterns in `select!` macro ([#4211])\n\n[#4211]: https://github.com/tokio-rs/tokio/pull/4211\n\n# 1.5.1 (October 29th, 2021)\n\n- macros: fix type resolution error in `#[tokio::main]` ([#4176])\n\n[#4176]: https://github.com/tokio-rs/tokio/pull/4176\n\n# 1.5.0 (October 13th, 2021)\n\n- macros: make tokio-macros attributes more IDE friendly ([#4162])\n\n[#4162]: https://github.com/tokio-rs/tokio/pull/4162\n\n# 1.4.1 (September 30th, 2021)\n\nReverted: run `current_thread` inside `LocalSet` ([#4027])\n\n# 1.4.0 (September 29th, 2021)\n\n(yanked)\n\n### Changed\n\n- macros: run `current_thread` inside `LocalSet` ([#4027])\n- macros: explicitly relaxed clippy lint for `.expect()` in runtime entry macro ([#4030])\n\n### Fixed\n\n- macros: fix invalid error messages in functions wrapped with `#[main]` or `#[test]` ([#4067])\n\n[#4027]: https://github.com/tokio-rs/tokio/pull/4027\n[#4030]: https://github.com/tokio-rs/tokio/pull/4030\n[#4067]: https://github.com/tokio-rs/tokio/pull/4067\n\n# 1.3.0 (July 7, 2021)\n\n- macros: don't trigger `clippy::unwrap_used` ([#3926])\n\n[#3926]: https://github.com/tokio-rs/tokio/pull/3926\n\n# 1.2.0 (May 14, 2021)\n\n- macros: forward input arguments in `#[tokio::test]` ([#3691])\n- macros: improve diagnostics on type mismatch ([#3766])\n- macros: various error message improvements ([#3677])\n\n[#3677]: https://github.com/tokio-rs/tokio/pull/3677\n[#3691]: https://github.com/tokio-rs/tokio/pull/3691\n[#3766]: https://github.com/tokio-rs/tokio/pull/3766\n\n# 1.1.0 (February 5, 2021)\n\n- add `start_paused` option to macros ([#3492])\n\n# 1.0.0 (December 23, 2020)\n\n- track `tokio` 1.0 release.\n\n# 0.3.1 (October 25, 2020)\n\n### Fixed\n\n- fix incorrect docs regarding `max_threads` option ([#3038])\n\n# 0.3.0 (October 15, 2020)\n\n- Track `tokio` 0.3 release.\n\n### Changed\n- options are renamed to track `tokio` runtime builder fn names.\n- `#[tokio::main]` macro requires `rt-multi-thread` when no `flavor` is specified.\n\n# 0.2.5 (February 27, 2019)\n\n### Fixed\n- doc improvements ([#2225]).\n\n# 0.2.4 (January 27, 2019)\n\n### Fixed\n- generics on `#[tokio::main]` function ([#2177]).\n\n### Added\n- support for `tokio::select!` ([#2152]).\n\n# 0.2.3 (January 7, 2019)\n\n### Fixed\n- Revert breaking change.\n\n# 0.2.2 (January 7, 2019)\n\n### Added\n- General refactoring and inclusion of additional runtime options ([#2022] and [#2038])\n\n# 0.2.1 (December 18, 2019)\n\n### Fixes\n- inherit visibility when wrapping async fn ([#1954]).\n\n# 0.2.0 (November 26, 2019)\n\n- Initial release\n\n[#1954]: https://github.com/tokio-rs/tokio/pull/1954\n[#2022]: https://github.com/tokio-rs/tokio/pull/2022\n[#2038]: https://github.com/tokio-rs/tokio/pull/2038\n[#2152]: https://github.com/tokio-rs/tokio/pull/2152\n[#2177]: https://github.com/tokio-rs/tokio/pull/2177\n[#2225]: https://github.com/tokio-rs/tokio/pull/2225\n[#3038]: https://github.com/tokio-rs/tokio/pull/3038\n[#3492]: https://github.com/tokio-rs/tokio/pull/3492\n",
            'tokio-macros/Cargo.toml': '[package]\nname = "tokio-macros"\n# When releasing to crates.io:\n# - Remove path dependencies (if any)\n# - Update CHANGELOG.md.\n# - Create "tokio-macros-x.y.z" git tag.\nversion = "2.6.0"\nedition = "2021"\nrust-version = "1.71"\nauthors = ["Tokio Contributors <team@tokio.rs>"]\nlicense = "MIT"\nrepository = "https://github.com/tokio-rs/tokio"\nhomepage = "https://tokio.rs"\ndescription = """\nTokio\'s proc macros.\n"""\ncategories = ["asynchronous"]\n\n[lib]\nproc-macro = true\n\n[features]\n\n[dependencies]\nproc-macro2 = "1.0.60"\nquote = "1"\nsyn = { version = "2.0", features = ["full"] }\n\n[dev-dependencies]\ntokio = { version = "1.0.0", features = ["full", "test-util"] }\n\n[package.metadata.docs.rs]\nall-features = true\n\n[lints]\nworkspace = true\n',
        }
