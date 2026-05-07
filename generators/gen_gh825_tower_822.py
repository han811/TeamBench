"""
Parameterized generator for GH825_tower_822.

Source PR:    https://github.com/tower-rs/tower/pull/822
Source Issue: N/A

Seed varies: renames 'ansi' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH825_tower_822'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH825_tower_822'
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
                files[fpath] = files[fpath].replace('ansi', 'ansi' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH825_tower_822',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'tower-rs/tower',
                "pr_number": 822,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/tower-rs/tower/pull/822",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            '.github/workflows/CI.yml': 'name: CI\n\non:\n  push:\n    branches:\n      - master\n  pull_request: {}\n\nenv:\n  MSRV: 1.64.0\n\njobs:\n  check-stable:\n    # Run `cargo check` first to ensure that the pushed code at least compiles.\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - uses: dtolnay/rust-toolchain@stable\n      - name: Check\n        run: cargo check --workspace --all-features --all-targets\n\n  check-docs:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - uses: dtolnay/rust-toolchain@stable\n      - name: cargo doc\n        working-directory: ${{ matrix.subcrate }}\n        env:\n          RUSTDOCFLAGS: "-D rustdoc::broken_intra_doc_links"\n        run: cargo doc --all-features --no-deps\n\n  check-msrv:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - name: "install Rust ${{ env.MSRV }}"\n        uses: dtolnay/rust-toolchain@master\n        with:\n          toolchain: ${{ env.MSRV }}\n      - name: "install Rust nightly"\n        uses: dtolnay/rust-toolchain@nightly\n      - name: Select minimal versions\n        run: cargo update -Z minimal-versions\n      - name: Check\n        run: |\n          rustup default ${{ env.MSRV }}\n          cargo check --all --all-targets --all-features --locked\n\n  cargo-hack:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - uses: dtolnay/rust-toolchain@stable\n      - name: install cargo-hack\n        uses: taiki-e/install-action@cargo-hack\n      - name: cargo hack check\n        working-directory: ${{ matrix.subcrate }}\n        run: cargo hack check --each-feature --no-dev-deps --workspace\n\n  test-versions:\n    # Test against the stable, beta, and nightly Rust toolchains on ubuntu-latest.\n    needs: check-stable\n    runs-on: ubuntu-latest\n    strategy:\n      # Disable fail-fast. If the test run for a particular Rust version fails,\n      # don\'t cancel the other test runs, so that we can determine whether a\n      # failure only occurs on a particular version.\n      fail-fast: false\n      matrix:\n        rust: [stable, beta, nightly]\n    steps:\n      - uses: actions/checkout@v4\n      - name: "install Rust ${{ matrix.rust }}"\n        uses: dtolnay/rust-toolchain@master\n        with:\n          toolchain: ${{ matrix.rust }}\n      - name: Run tests\n        run: cargo test --workspace --all-features\n\n  test-msrv:\n    needs: check-msrv\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - name: "install Rust ${{ env.MSRV }}"\n        uses: dtolnay/rust-toolchain@master\n        with:\n          toolchain: ${{ env.MSRV }}\n      - name: "install Rust nightly"\n        uses: dtolnay/rust-toolchain@nightly\n      - name: Select minimal versions\n        run: cargo update -Z minimal-versions\n      - name: test\n        run: |\n          rustup default ${{ env.MSRV }}\n          cargo check --workspace --all-features --locked\n\n  style:\n    needs: check-stable\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - uses: dtolnay/rust-toolchain@stable\n        with:\n          components: rustfmt\n      - name: rustfmt\n        run: cargo fmt --all -- --check\n\n  deny-check:\n    name: cargo-deny check\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - uses: EmbarkStudios/cargo-deny-action@v1\n        with:\n          command: check\n',
            'Cargo.toml': '[workspace]\n\nmembers = [\n  "tower",\n  "tower-layer",\n  "tower-service",\n  "tower-test",\n]\n\n[workspace.dependencies]\nfutures = "0.3.22"\nfutures-core = "0.3.22"\nfutures-util = { version = "0.3.22", default-features = false }\nhdrhistogram = { version = "7.0", default-features = false }\nhttp = "1"\nindexmap = "2.0.2"\nlazy_static = "1.4.0"\npin-project-lite = "0.2.7"\nquickcheck = "1"\nrand = "0.8"\nslab = "0.4.9"\nsync_wrapper = "1"\ntokio = "1.6.2"\ntokio-stream = "0.1.0"\ntokio-test = "0.4"\ntokio-util = { version = "0.7.0", default-features = false }\ntracing = { version = "0.1.2", default-features = false }\ntracing-subscriber = { version = "0.3", default-features = false }\n',
            'tower/Cargo.toml': '[package]\nname = "tower"\n# When releasing to crates.io:\n# - Update README.md\n# - Update CHANGELOG.md.\n# - Create "vX.X.X" git tag.\nversion = "0.5.2"\nauthors = ["Tower Maintainers <team@tower-rs.com>"]\nlicense = "MIT"\nreadme = "README.md"\nrepository = "https://github.com/tower-rs/tower"\nhomepage = "https://github.com/tower-rs/tower"\ndescription = """\nTower is a library of modular and reusable components for building robust\nclients and servers.\n"""\ncategories = ["asynchronous", "network-programming"]\nkeywords = ["io", "async", "non-blocking", "futures", "service"]\nedition = "2018"\nrust-version = "1.64.0"\n\n[features]\nfull = [\n  "balance",\n  "buffer",\n  "discover",\n  "filter",\n  "hedge",\n  "limit",\n  "load",\n  "load-shed",\n  "make",\n  "ready-cache",\n  "reconnect",\n  "retry",\n  "spawn-ready",\n  "steer",\n  "timeout",\n  "util",\n]\n# FIXME: Use weak dependency once available (https://github.com/rust-lang/cargo/issues/8832)\nlog = ["tracing/log"]\nbalance = ["discover", "load", "ready-cache", "make", "slab", "util"]\nbuffer = ["tokio/sync", "tokio/rt", "tokio-util", "tracing", "pin-project-lite"]\ndiscover = ["futures-core", "pin-project-lite"]\nfilter = ["futures-util", "pin-project-lite"]\nhedge = ["util", "filter", "futures-util", "hdrhistogram", "tokio/time", "tracing"]\nlimit = ["tokio/time", "tokio/sync", "tokio-util", "tracing", "pin-project-lite"]\nload = ["tokio/time", "tracing", "pin-project-lite"]\nload-shed = ["pin-project-lite"]\nmake = ["pin-project-lite", "tokio/io-std"]\nready-cache = ["futures-core", "futures-util", "indexmap", "tokio/sync", "tracing", "pin-project-lite"]\nreconnect = ["make", "tokio/io-std", "tracing"]\nretry = ["tokio/time", "util"]\nspawn-ready = ["futures-util", "tokio/sync", "tokio/rt", "util", "tracing"]\nsteer = []\ntimeout = ["pin-project-lite", "tokio/time"]\nutil = ["futures-core", "futures-util", "pin-project-lite", "sync_wrapper"]\n\n[dependencies]\ntower-layer = { version = "0.3.3", path = "../tower-layer" }\ntower-service = { version = "0.3.3", path = "../tower-service" }\n\nfutures-core = { workspace = true, optional = true }\nfutures-util = { workspace = true, features = ["alloc"], optional = true }\nhdrhistogram = { workspace = true, optional = true }\nindexmap = { workspace = true, optional = true }\nslab = { workspace = true, optional = true }\ntokio = { workspace = true, features = ["sync"], optional = true }\ntokio-stream = { workspace = true, optional = true }\ntokio-util = { workspace = true, optional = true }\ntracing = { workspace = true, features = ["std"], optional = true }\npin-project-lite = { workspace = true, optional = true }\nsync_wrapper = { workspace = true, optional = true }\n\n[dev-dependencies]\nfutures = { workspace = true }\nhdrhistogram = { workspace = true }\npin-project-lite = { workspace = true }\ntokio = { workspace = true, features = ["macros", "sync", "test-util", "rt-multi-thread"] }\ntokio-stream = { workspace = true }\ntokio-test = { workspace = true }\ntower-test = { version = "0.4", path = "../tower-test" }\ntracing = { workspace = true, features = ["std"] }\ntracing-subscriber = { workspace = true, features = ["fmt", "ansi"] }\nhttp = { workspace = true }\nlazy_static = { workspace = true }\nrand = { workspace = true, features = ["small_rng"] }\nquickcheck = { workspace = true }\n\n[package.metadata.docs.rs]\nall-features = true\nrustdoc-args = ["--cfg", "docsrs"]\n\n[package.metadata.playground]\nfeatures = ["full"]\n\n[[example]]\nname = "tower-balance"\npath = "examples/tower-balance.rs"\nrequired-features = ["full"]\n',
        }
