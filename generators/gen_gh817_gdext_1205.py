"""
Parameterized generator for GH817_gdext_1205.

Source PR:    https://github.com/godot-rust/gdext/pull/1205
Source Issue: https://github.com/godot-rust/gdext/issues/1202

Seed varies: renames 'allows' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH817_gdext_1205'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH817_gdext_1205'
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
                files[fpath] = files[fpath].replace('allows', 'allows' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH817_gdext_1205',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'godot-rust/gdext',
                "pr_number": 1205,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/godot-rust/gdext/pull/1205",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'godot-macros/Cargo.toml': '[package]\nname = "godot-macros"\nversion = "0.3.1"\nedition = "2021"\nrust-version = "1.87"\nlicense = "MPL-2.0"\nkeywords = ["gamedev", "godot", "engine", "derive", "macro"]\ncategories = ["game-engines", "graphics"]\ndescription = "Internal crate used by godot-rust"\nrepository = "https://github.com/godot-rust/gdext"\nhomepage = "https://godot-rust.github.io"\n\n[features]\napi-custom = ["godot-bindings/api-custom"]\napi-custom-json = ["godot-bindings/api-custom-json"]\ncodegen-full = ["godot/__codegen-full"]\nexperimental-wasm = ["dep:libc"]\nregister-docs = ["dep:markdown", "dep:litrs"]\n\n[lib]\nproc-macro = true\n\n[dependencies]\nproc-macro2 = { workspace = true }\nquote = { workspace = true }\n# Enabled by `docs`.\nmarkdown = { workspace = true, optional = true }\nlitrs = { workspace = true, optional = true }\nvenial = { workspace = true }\n\n# Cannot use [target.\'cfg(target_family = "wasm")\'.dependencies], as proc-macro crates are always compiled for host platform, not target.\n# Thus solved via feature.\nlibc = { workspace = true, optional = true }\n\n[build-dependencies]\ngodot-bindings = { path = "../godot-bindings", version = "=0.3.1" } # emit_godot_version_cfg\n\n# Reverse dev dependencies so doctests can use `godot::` prefix.\n[dev-dependencies]\ngodot = { path = "../godot", default-features = false}\n\n# https://docs.rs/about/metadata\n[package.metadata.docs.rs]\nfeatures = ["experimental-godot-api"]\nrustdoc-args = ["--cfg", "published_docs"]\nrustc-args = ["--cfg", "published_docs"]\n\n# Currently causes "unused manifest key" warnings. Maybe re-enable in the future, to make `published_docs` known.\n#[lints.rust]\n#unexpected_cfgs = { level = "warn", check-cfg = [\'cfg(published_docs)\'] }\n',
            'godot-macros/src/ffi_macros.rs': '/*\n * Copyright (c) godot-rust; Bromeon and contributors.\n * This Source Code Form is subject to the terms of the Mozilla Public\n * License, v. 2.0. If a copy of the MPL was not distributed with this\n * file, You can obtain one at https://mozilla.org/MPL/2.0/.\n */\n\n//! Macro implementations used by `godot-ffi` crate.\n\n#![cfg(feature = "experimental-wasm")]\n\nuse crate::util::bail;\nuse crate::ParseResult;\nuse proc_macro2::TokenStream;\nuse quote::{format_ident, quote};\n\npub(super) fn wasm_declare_init_fn(input: TokenStream) -> ParseResult<TokenStream> {\n    if !input.is_empty() {\n        return bail!(input, "macro expects no arguments");\n    }\n\n    // Create sufficiently unique identifier without entire `uuid` (let alone `rand`) crate dependency.\n    let a = unsafe { libc::rand() };\n    let b = unsafe { libc::rand() };\n\n    // Rust presently requires that statics with a custom `#[link_section]` must be a simple\n    // list of bytes on the Wasm target (with no extra levels of indirection such as references).\n    //\n    // As such, instead we export a function with a random name of known prefix to be used by the embedder.\n    // This prefix is queried at load time, see godot-macros/src/gdextension.rs.\n    let function_name = format_ident!("__godot_rust_registrant_{a}_{b}");\n\n    let code = quote! {\n        #[cfg(target_family = "wasm")] // Strictly speaking not necessary, as this macro is only invoked for Wasm.\n        #[no_mangle]\n        extern "C" fn #function_name() {\n            __init();\n        }\n    };\n\n    Ok(code)\n}\n',
        }
