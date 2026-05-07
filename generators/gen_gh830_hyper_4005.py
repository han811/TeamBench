"""
Parameterized generator for GH830_hyper_4005.

Source PR:    https://github.com/hyperium/hyper/pull/4005
Source Issue: N/A

Seed varies: renames 'action' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH830_hyper_4005'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH830_hyper_4005'
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
            task_id='GH830_hyper_4005',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'hyperium/hyper',
                "pr_number": 4005,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/hyperium/hyper/pull/4005",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            '.github/workflows/CI.yml': 'name: CI\non:\n  pull_request:\n  push:\n    branches:\n      - master\n\nenv:\n  RUST_BACKTRACE: 1\n\npermissions:\n  contents: read # to fetch code (actions/checkout)\n\njobs:\n  ci-pass:\n    name: CI is green\n    runs-on: ubuntu-latest\n    needs:\n      - style\n      - test\n      - msrv\n      - miri\n      - features\n      - ffi\n      - ffi-header\n      - ffi-cargo-c\n      - doc\n      - check-external-types\n      - udeps\n      - minimal-versions\n      - semver\n    steps:\n      - run: exit 0\n\n  style:\n    name: Check Style\n    runs-on: ubuntu-latest\n    steps:\n      - name: Checkout\n        uses: actions/checkout@v5\n\n      - name: Install Rust\n        uses: dtolnay/rust-toolchain@stable\n        with:\n          components: rustfmt\n\n      - name: cargo fmt --check\n        run: |\n          if ! rustfmt --check --edition 2021 $(git ls-files \'*.rs\'); then\n            printf "Please run \\`rustfmt --edition 2021 \\$(git ls-files \'*.rs\')\\` to fix rustfmt errors.\\nSee docs/CODE_STYLE.md for more details.\\n" >&2\n            exit 1\n          fi\n\n  test:\n    name: Test ${{ matrix.rust }} on ${{ matrix.os }}\n    needs: [style]\n    strategy:\n      matrix:\n        rust:\n          - stable\n          - beta\n          - nightly\n\n        os:\n          - ubuntu-latest\n          - windows-latest\n          - macOS-latest\n\n        include:\n          - rust: stable\n            features: "--features full"\n          - rust: beta\n            features: "--features full"\n          - rust: nightly\n            features: "--features full,nightly"\n            benches: true\n\n    runs-on: ${{ matrix.os }}\n\n    steps:\n      - name: Checkout\n        uses: actions/checkout@v5\n\n      - name: Install Rust (${{ matrix.rust }})\n        uses: dtolnay/rust-toolchain@master\n        with:\n          toolchain: ${{ matrix.rust }}\n\n      - uses: Swatinem/rust-cache@v2\n\n      - name: Test\n        run: cargo test ${{ matrix.features }}\n\n      - name: Test all benches\n        if: matrix.benches\n        run: cargo test --benches ${{ matrix.features }}\n\n  msrv:\n    name: Check MSRV\n    needs: [style]\n\n    runs-on: ubuntu-latest\n\n    steps:\n      - name: Checkout\n        uses: actions/checkout@v5\n\n      - uses: dtolnay/rust-toolchain@stable\n\n      - name: Resolve MSRV aware dependencies\n        run: cargo update\n        env:\n          CARGO_RESOLVER_INCOMPATIBLE_RUST_VERSIONS: fallback\n\n      - name: Get MSRV from package metadata\n        id: msrv\n        run: echo "version=$(yq \'.package.rust-version\' Cargo.toml)" >> $GITHUB_OUTPUT\n\n      - name: Install Rust (${{ steps.msrv.outputs.version }})\n        uses: dtolnay/rust-toolchain@master\n        with:\n          toolchain: ${{ steps.msrv.outputs.version }}\n\n      - uses: Swatinem/rust-cache@v2\n\n      - name: Check\n        run: cargo check --features full\n\n  miri:\n    name: Test with Miri\n    needs: [style]\n    runs-on: ubuntu-latest\n\n    steps:\n      - name: Checkout\n        uses: actions/checkout@v5\n\n      - name: Install Rust\n        uses: dtolnay/rust-toolchain@nightly\n        with:\n          components: miri\n\n      - uses: Swatinem/rust-cache@v2\n\n      - name: Test\n        # Can\'t enable tcp feature since Miri does not support the tokio runtime\n        run: MIRIFLAGS="-Zmiri-disable-isolation" cargo miri test --features http1,http2,client,server,nightly\n\n  features:\n    name: features\n    needs: [style]\n    runs-on: ubuntu-latest\n    steps:\n      - name: Checkout\n        uses: actions/checkout@v5\n\n      - name: Install Rust\n        uses: dtolnay/rust-toolchain@stable\n\n      - name: Install cargo-hack\n        uses: taiki-e/install-action@cargo-hack\n\n      - uses: Swatinem/rust-cache@v2\n\n      - name: check --feature-powerset\n        run: cargo hack --no-dev-deps check --feature-powerset --depth 2 --skip ffi,tracing\n        env:\n          RUSTFLAGS: "-D dead_code -D unused_imports"\n\n      - name: check --feature-powerset with tracing feature\n        run: cargo hack --no-dev-deps check --feature-powerset --depth 2 --features tracing --skip ffi\n        env:\n          RUSTFLAGS: "--cfg hyper_unstable_tracing -D dead_code -D unused_imports"\n\n  ffi:\n    name: Test C API (FFI)\n    needs: [style]\n    runs-on: ubuntu-latest\n    steps:\n      - name: Checkout\n        uses: actions/checkout@v5\n\n      - name: Install Rust\n        uses: dtolnay/rust-toolchain@stable\n\n      - uses: Swatinem/rust-cache@v2\n\n      - name: Build FFI\n        env:\n          RUSTFLAGS: --cfg hyper_unstable_ffi\n        run: cargo rustc --features client,http1,http2,ffi --crate-type cdylib\n\n      - name: Make Examples\n        run: cd capi/examples && make client\n\n      - name: Run FFI unit tests\n        env:\n          RUSTFLAGS: --cfg hyper_unstable_ffi\n        run: cargo test --features client,http1,http2,ffi --lib\n\n  ffi-header:\n    name: Verify hyper.h is up to date\n    runs-on: ubuntu-latest\n    steps:\n      - name: Checkout\n        uses: actions/checkout@v5\n\n      - name: Install Rust\n        uses: dtolnay/rust-toolchain@stable\n\n      - name: Install cbindgen\n        uses: taiki-e/cache-cargo-install-action@v2\n        with:\n          tool: cbindgen\n\n      - name: Install cargo-expand\n        uses: taiki-e/cache-cargo-install-action@v2\n        with:\n          tool: cargo-expand\n\n      - uses: Swatinem/rust-cache@v2\n\n      - name: Build FFI\n        env:\n          RUSTFLAGS: --cfg hyper_unstable_ffi\n        run: cargo build --features client,http1,http2,ffi\n\n      - name: Ensure that hyper.h is up to date\n        run: ./capi/gen_header.sh --verify\n\n  ffi-cargo-c:\n    name: Test cargo-c support (FFI)\n    needs: [style]\n    runs-on: ubuntu-latest\n    steps:\n      - name: Checkout\n        uses: actions/checkout@v5\n\n      - name: Install Rust\n        uses: dtolnay/rust-toolchain@stable\n\n      - uses: Swatinem/rust-cache@v2\n\n      - name: Install cargo-c\n        env:\n          LINK: https://github.com/lu-zero/cargo-c/releases/latest/download\n          CARGO_C_FILE: cargo-c-x86_64-unknown-linux-musl.tar.gz\n        run: |\n          curl -L $LINK/$CARGO_C_FILE | tar xz -C ~/.cargo/bin\n\n      - name: Build with cargo-c\n        env:\n          RUSTFLAGS: --cfg hyper_unstable_ffi\n        run: cargo cbuild --features client,http1,http2,ffi\n\n  doc:\n    name: Build docs\n    needs: [style, test]\n    runs-on: ubuntu-latest\n    steps:\n      - name: Checkout\n        uses: actions/checkout@v5\n\n      - name: Install Rust\n        uses: dtolnay/rust-toolchain@nightly\n\n      - uses: Swatinem/rust-cache@v2\n\n      - name: cargo doc\n        run: cargo rustdoc --features full,ffi -- --cfg docsrs --cfg hyper_unstable_ffi -D rustdoc::broken-intra-doc-links\n\n  check-external-types:\n    name: Check exposed types\n    needs: [style, test]\n    runs-on: ubuntu-latest\n    steps:\n      - name: Checkout\n        uses: actions/checkout@v5\n\n      - name: Install Rust\n        uses: dtolnay/rust-toolchain@master\n        with:\n          toolchain: nightly-2025-08-06 # Compatible version for cargo-check-external-types\n\n      - name: Install cargo-check-external-types\n        uses: taiki-e/cache-cargo-install-action@v2\n        with:\n          tool: cargo-check-external-types@0.3.0\n\n      - uses: Swatinem/rust-cache@v2\n\n      - name: check-external-types\n        run: cargo check-external-types --config .github/workflows/external-types.toml\n\n  udeps:\n    needs: [style]\n    runs-on: ubuntu-latest\n    steps:\n      - name: Checkout\n        uses: actions/checkout@v5\n\n      - name: Install Rust\n        uses: dtolnay/rust-toolchain@nightly\n\n      - name: Install cargo-udeps\n        uses: taiki-e/install-action@cargo-udeps\n\n      - uses: Swatinem/rust-cache@v2\n\n      - name: Check unused dependencies on default features\n        run: cargo udeps\n\n      - name: Check unused dependencies on full features\n        run: cargo udeps --features full\n\n  minimal-versions:\n    runs-on: ubuntu-latest\n    needs: [style]\n    steps:\n      - uses: actions/checkout@v5\n      - uses: dtolnay/rust-toolchain@nightly\n      - uses: dtolnay/rust-toolchain@stable\n      - uses: taiki-e/install-action@cargo-hack\n      - uses: taiki-e/install-action@cargo-minimal-versions\n      - uses: Swatinem/rust-cache@v2\n      - run: cargo minimal-versions check\n      - run: cargo minimal-versions check --features full\n\n  semver:\n    name: semver\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v5\n      - name: Check semver\n        uses: obi1kenobi/cargo-semver-checks-action@v2\n        with:\n          feature-group: only-explicit-features\n          features: full\n          release-type: minor\n',
            '.github/workflows/bench.yml': "name: Benchmark\non:\n  push:\n    branches:\n      - master\n\njobs:\n  benchmark:\n    name: Benchmark\n    runs-on: ubuntu-latest\n    strategy:\n      matrix:\n        bench:\n          - end_to_end\n          - pipeline\n    steps:\n      - uses: actions/checkout@v4\n\n      - name: Install Rust\n        uses: dtolnay/rust-toolchain@nightly\n\n      # Run benchmark and stores the output to a file\n      - name: Run benchmark\n        run: cargo bench --features full --bench ${{ matrix.bench }} | tee output.txt\n\n      # Download previous benchmark result from cache (if exists)\n      - name: Download previous benchmark data\n        uses: actions/cache@v3\n        with:\n          path: ./cache\n          key: ${{ runner.os }}-benchmark\n\n      # Run `github-action-benchmark` action\n      - name: Store benchmark result\n        uses: seanmonstar/github-action-benchmark@v1-patch-1\n        with:\n          name: ${{ matrix.bench }}\n          # What benchmark tool the output.txt came from\n          tool: 'cargo'\n          # Where the output from the benchmark tool is stored\n          output-file-path: output.txt\n          # # Where the previous data file is stored\n          # external-data-json-path: ./cache/benchmark-data.json\n          # Workflow will fail when an alert happens\n          fail-on-alert: true\n          # GitHub API token to make a commit comment\n          github-token: ${{ secrets.GITHUB_TOKEN }}\n          # Enable alert commit comment\n          comment-on-alert: true\n          #alert-comment-cc-users: '@seanmonstar'\n          auto-push: true\n\n      # Upload the updated cache file for the next job by actions/cache\n",
            '.github/workflows/cargo-audit.yml': "name: cargo-audit\non:\n  push:\n    paths: \n      - '**/Cargo.toml'\n      - '**/Cargo.lock'\n  schedule:\n    - cron: '0 16 * * Mon'\n\njobs:\n  security_audit:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v5\n      - uses: rustsec/audit-check@v2\n        with:\n          token: ${{ secrets.GITHUB_TOKEN }}\n",
        }
