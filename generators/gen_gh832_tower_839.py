"""
Parameterized generator for GH832_tower_839.

Source PR:    https://github.com/tower-rs/tower/pull/839
Source Issue: N/A

Seed varies: renames 'action' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH832_tower_839'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH832_tower_839'
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
                files[fpath] = files[fpath].replace('action', 'action' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH832_tower_839',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'tower-rs/tower',
                "pr_number": 839,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/tower-rs/tower/pull/839",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            '.github/workflows/CI.yml': 'name: CI\n\non:\n  push:\n    branches:\n      - master\n  pull_request: {}\n\nenv:\n  MSRV: 1.64.0\n\njobs:\n  check-stable:\n    # Run `cargo check` first to ensure that the pushed code at least compiles.\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - uses: dtolnay/rust-toolchain@stable\n      - name: Check\n        run: cargo check --workspace --all-features --all-targets\n\n  check-docs:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - uses: dtolnay/rust-toolchain@stable\n      - name: cargo doc\n        working-directory: ${{ matrix.subcrate }}\n        env:\n          RUSTDOCFLAGS: "-D rustdoc::broken_intra_doc_links"\n        run: cargo doc --all-features --no-deps\n\n  check-msrv:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - name: "install Rust ${{ env.MSRV }}"\n        uses: dtolnay/rust-toolchain@master\n        with:\n          toolchain: ${{ env.MSRV }}\n      - name: "install Rust nightly"\n        uses: dtolnay/rust-toolchain@nightly\n      - name: Select minimal versions\n        run: |\n          cargo update -Z minimal-versions\n          cargo update -p lazy_static --precise 1.5.0\n      - name: Check\n        run: |\n          rustup default ${{ env.MSRV }}\n          cargo check --all --all-targets --all-features --locked\n\n  cargo-hack:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - uses: dtolnay/rust-toolchain@stable\n      - name: install cargo-hack\n        uses: taiki-e/install-action@cargo-hack\n      - name: cargo hack check\n        working-directory: ${{ matrix.subcrate }}\n        run: cargo hack check --each-feature --no-dev-deps --workspace\n\n  test-versions:\n    # Test against the stable, beta, and nightly Rust toolchains on ubuntu-latest.\n    needs: check-stable\n    runs-on: ubuntu-latest\n    strategy:\n      # Disable fail-fast. If the test run for a particular Rust version fails,\n      # don\'t cancel the other test runs, so that we can determine whether a\n      # failure only occurs on a particular version.\n      fail-fast: false\n      matrix:\n        rust: [stable, beta, nightly]\n    steps:\n      - uses: actions/checkout@v4\n      - name: "install Rust ${{ matrix.rust }}"\n        uses: dtolnay/rust-toolchain@master\n        with:\n          toolchain: ${{ matrix.rust }}\n      - name: Run tests\n        run: cargo test --workspace --all-features\n\n  test-msrv:\n    needs: check-msrv\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - name: "install Rust ${{ env.MSRV }}"\n        uses: dtolnay/rust-toolchain@master\n        with:\n          toolchain: ${{ env.MSRV }}\n      - name: "install Rust nightly"\n        uses: dtolnay/rust-toolchain@nightly\n      - name: Select minimal versions\n        run: |\n          cargo update -Z minimal-versions\n          cargo update -p lazy_static --precise 1.5.0\n      - name: test\n        run: |\n          rustup default ${{ env.MSRV }}\n          cargo check --workspace --all-features --locked\n\n  style:\n    needs: check-stable\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - uses: dtolnay/rust-toolchain@stable\n        with:\n          components: rustfmt\n      - name: rustfmt\n        run: cargo fmt --all -- --check\n\n  deny-check:\n    name: cargo-deny check\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - uses: EmbarkStudios/cargo-deny-action@v1\n        with:\n          command: check\n',
            '.github/workflows/publish.yml': 'name: Deploy API Documentation\n\non:\n  push:\n    branches:\n      - master\n\njobs:\n  publish:\n\n    runs-on: ubuntu-latest\n\n    steps:\n      - name: Checkout code\n        uses: actions/checkout@v4\n      - name: Install nightly Rust\n        uses: dtolnay/rust-toolchain@master\n        with:\n          toolchain: nightly\n      - name: Generate documentation\n        run: cargo doc --workspace --no-deps --all-features\n        env:\n          # Enable the RustDoc `#[doc(cfg(...))]` attribute.\n          RUSTDOCFLAGS: --cfg docsrs\n      - name: Deploy documentation\n        if: success()\n        uses: crazy-max/ghaction-github-pages@v1\n        with:\n          target_branch: gh-pages\n          build_dir: target/doc\n        env:\n          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}\n',
            '.github/workflows/release.yml': 'name: create github release\n\non:\n  push:\n    tags:\n      - tower-[0-9]+.*\n      - tower-[a-z]+-[0-9]+.*\n\njobs:\n  create-release:\n    name: Create GitHub release\n    # only publish from the origin repository\n    if: github.repository_owner == \'tower-rs\'\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - uses: taiki-e/create-gh-release-action@v1.3.0\n        with:\n          prefix: "(tower)|(tower-[a-z]+)"\n          changelog: "$prefix/CHANGELOG.md"\n          title: "$prefix $version"\n          branch: "(master)|(v[0-9]+.[0-9]+.x)"\n        env:\n          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}',
        }
