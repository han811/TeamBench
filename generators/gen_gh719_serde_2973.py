"""
Parameterized generator for GH719_serde_2973.

Source PR:    https://github.com/serde-rs/serde/pull/2973
Source Issue: N/A

Seed varies: renames 'able' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH719_serde_2973'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH719_serde_2973'
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
                files[fpath] = files[fpath].replace('able', 'able' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH719_serde_2973',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'serde-rs/serde',
                "pr_number": 2973,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/serde-rs/serde/pull/2973",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'serde_core/README.md': "The `serde_core` crate contains Serde's trait definitions with **no support for\n#\\[derive()\\]**.\n\nIn crates that derive an implementation of `Serialize` or `Deserialize`, you\nmust depend on the [`serde`] crate, not `serde_core`.\n\nIn crates that handwrite implementations of Serde traits, or only use them as\ntrait bounds, depending on `serde_core` is permitted. But `serde` re-exports all\nof these traits and can be used for this use case too. If in doubt, disregard\n`serde_core` and always use `serde`.\n\n[`serde`]: https://crates.io/crates/serde\n",
            'serde_core/src/lib.rs': '//! Serde is a framework for ***ser***ializing and ***de***serializing Rust data\n//! structures efficiently and generically.\n//!\n//! The `serde_core` crate contains Serde\'s trait definitions with **no support\n//! for #\\[derive()\\]**.\n//!\n//! In crates that derive an implementation of `Serialize` or `Deserialize`, you\n//! must depend on the [`serde`] crate, not `serde_core`.\n//!\n//! In crates that handwrite implementations of Serde traits, or only use them\n//! as trait bounds, depending on `serde_core` is permitted. But `serde`\n//! re-exports all of these traits and can be used for this use case too. If in\n//! doubt, disregard `serde_core` and always use `serde`.\n//!\n//! [`serde`]: https://crates.io/crates/serde\n\n////////////////////////////////////////////////////////////////////////////////\n\n// Serde types in rustdoc of other crates get linked to here.\n#![doc(html_root_url = "https://docs.rs/serde/1.0.220")]\n// Support using Serde without the standard library!\n#![cfg_attr(not(feature = "std"), no_std)]\n// Show which crate feature enables conditionally compiled APIs in documentation.\n#![cfg_attr(docsrs, feature(doc_cfg, rustdoc_internals))]\n#![cfg_attr(docsrs, allow(internal_features))]\n// Unstable functionality only if the user asks for it. For tracking and\n// discussion of these features please refer to this issue:\n//\n//    https://github.com/serde-rs/serde/issues/812\n#![cfg_attr(feature = "unstable", feature(never_type))]\n#![allow(unknown_lints, bare_trait_objects, deprecated)]\n// Ignored clippy and clippy_pedantic lints\n#![allow(\n    // clippy bug: https://github.com/rust-lang/rust-clippy/issues/5704\n    clippy::unnested_or_patterns,\n    // clippy bug: https://github.com/rust-lang/rust-clippy/issues/7768\n    clippy::semicolon_if_nothing_returned,\n    // not available in our oldest supported compiler\n    clippy::empty_enum,\n    clippy::type_repetition_in_bounds, // https://github.com/rust-lang/rust-clippy/issues/8772\n    // integer and float ser/de requires these sorts of casts\n    clippy::cast_possible_truncation,\n    clippy::cast_possible_wrap,\n    clippy::cast_precision_loss,\n    clippy::cast_sign_loss,\n    // things are often more readable this way\n    clippy::cast_lossless,\n    clippy::module_name_repetitions,\n    clippy::single_match_else,\n    clippy::type_complexity,\n    clippy::use_self,\n    clippy::zero_prefixed_literal,\n    // correctly used\n    clippy::derive_partial_eq_without_eq,\n    clippy::enum_glob_use,\n    clippy::explicit_auto_deref,\n    clippy::incompatible_msrv,\n    clippy::let_underscore_untyped,\n    clippy::map_err_ignore,\n    clippy::new_without_default,\n    clippy::result_unit_err,\n    clippy::wildcard_imports,\n    // not practical\n    clippy::needless_pass_by_value,\n    clippy::similar_names,\n    clippy::too_many_lines,\n    // preference\n    clippy::doc_markdown,\n    clippy::elidable_lifetime_names,\n    clippy::needless_lifetimes,\n    clippy::unseparated_literal_suffix,\n    // false positive\n    clippy::needless_doctest_main,\n    // noisy\n    clippy::missing_errors_doc,\n    clippy::must_use_candidate,\n)]\n// Restrictions\n#![deny(clippy::question_mark_used)]\n// Rustc lints.\n#![deny(missing_docs, unused_imports)]\n\n////////////////////////////////////////////////////////////////////////////////\n\n#[cfg(feature = "alloc")]\nextern crate alloc;\n\n/// A facade around all the types we need from the `std`, `core`, and `alloc`\n/// crates. This avoids elaborate import wrangling having to happen in every\n/// module.\nmod lib {\n    mod core {\n        #[cfg(not(feature = "std"))]\n        pub use core::*;\n        #[cfg(feature = "std")]\n        pub use std::*;\n    }\n\n    pub use self::core::{f32, f64};\n    pub use self::core::{iter, num, str};\n\n    #[cfg(any(feature = "std", feature = "alloc"))]\n    pub use self::core::{cmp, mem};\n\n    pub use self::core::cell::{Cell, RefCell};\n    pub use self::core::cmp::Reverse;\n    pub use self::core::fmt::{self, Debug, Display, Write as FmtWrite};\n    pub use self::core::marker::PhantomData;\n    pub use self::core::num::Wrapping;\n    pub use self::core::ops::{Bound, Range, RangeFrom, RangeInclusive, RangeTo};\n    pub use self::core::result;\n    pub use self::core::time::Duration;\n\n    #[cfg(all(feature = "alloc", not(feature = "std")))]\n    pub use alloc::borrow::{Cow, ToOwned};\n    #[cfg(feature = "std")]\n    pub use std::borrow::{Cow, ToOwned};\n\n    #[cfg(all(feature = "alloc", not(feature = "std")))]\n    pub use alloc::string::{String, ToString};\n    #[cfg(feature = "std")]\n    pub use std::string::{String, ToString};\n\n    #[cfg(all(feature = "alloc", not(feature = "std")))]\n    pub use alloc::vec::Vec;\n    #[cfg(feature = "std")]\n    pub use std::vec::Vec;\n\n    #[cfg(all(feature = "alloc", not(feature = "std")))]\n    pub use alloc::boxed::Box;\n    #[cfg(feature = "std")]\n    pub use std::boxed::Box;\n\n    #[cfg(all(feature = "rc", feature = "alloc", not(feature = "std")))]\n    pub use alloc::rc::{Rc, Weak as RcWeak};\n    #[cfg(all(feature = "rc", feature = "std"))]\n    pub use std::rc::{Rc, Weak as RcWeak};\n\n    #[cfg(all(feature = "rc", feature = "alloc", not(feature = "std")))]\n    pub use alloc::sync::{Arc, Weak as ArcWeak};\n    #[cfg(all(feature = "rc", feature = "std"))]\n    pub use std::sync::{Arc, Weak as ArcWeak};\n\n    #[cfg(all(feature = "alloc", not(feature = "std")))]\n    pub use alloc::collections::{BTreeMap, BTreeSet, BinaryHeap, LinkedList, VecDeque};\n    #[cfg(feature = "std")]\n    pub use std::collections::{BTreeMap, BTreeSet, BinaryHeap, LinkedList, VecDeque};\n\n    #[cfg(all(not(no_core_cstr), not(feature = "std")))]\n    pub use self::core::ffi::CStr;\n    #[cfg(feature = "std")]\n    pub use std::ffi::CStr;\n\n    #[cfg(all(not(no_core_cstr), feature = "alloc", not(feature = "std")))]\n    pub use alloc::ffi::CString;\n    #[cfg(feature = "std")]\n    pub use std::ffi::CString;\n\n    #[cfg(all(not(no_core_net), not(feature = "std")))]\n    pub use self::core::net;\n    #[cfg(feature = "std")]\n    pub use std::net;\n\n    #[cfg(feature = "std")]\n    pub use std::error;\n\n    #[cfg(feature = "std")]\n    pub use std::collections::{HashMap, HashSet};\n    #[cfg(feature = "std")]\n    pub use std::ffi::{OsStr, OsString};\n    #[cfg(feature = "std")]\n    pub use std::hash::{BuildHasher, Hash};\n    #[cfg(feature = "std")]\n    pub use std::io::Write;\n    #[cfg(feature = "std")]\n    pub use std::path::{Path, PathBuf};\n    #[cfg(feature = "std")]\n    pub use std::sync::{Mutex, RwLock};\n    #[cfg(feature = "std")]\n    pub use std::time::{SystemTime, UNIX_EPOCH};\n\n    #[cfg(all(feature = "std", no_target_has_atomic, not(no_std_atomic)))]\n    pub use std::sync::atomic::{\n        AtomicBool, AtomicI16, AtomicI32, AtomicI8, AtomicIsize, AtomicU16, AtomicU32, AtomicU8,\n        AtomicUsize, Ordering,\n    };\n    #[cfg(all(feature = "std", no_target_has_atomic, not(no_std_atomic64)))]\n    pub use std::sync::atomic::{AtomicI64, AtomicU64};\n\n    #[cfg(all(feature = "std", not(no_target_has_atomic)))]\n    pub use std::sync::atomic::Ordering;\n    #[cfg(all(feature = "std", not(no_target_has_atomic), target_has_atomic = "8"))]\n    pub use std::sync::atomic::{AtomicBool, AtomicI8, AtomicU8};\n    #[cfg(all(feature = "std", not(no_target_has_atomic), target_has_atomic = "16"))]\n    pub use std::sync::atomic::{AtomicI16, AtomicU16};\n    #[cfg(all(feature = "std", not(no_target_has_atomic), target_has_atomic = "32"))]\n    pub use std::sync::atomic::{AtomicI32, AtomicU32};\n    #[cfg(all(feature = "std", not(no_target_has_atomic), target_has_atomic = "64"))]\n    pub use std::sync::atomic::{AtomicI64, AtomicU64};\n    #[cfg(all(feature = "std", not(no_target_has_atomic), target_has_atomic = "ptr"))]\n    pub use std::sync::atomic::{AtomicIsize, AtomicUsize};\n\n    #[cfg(not(no_core_num_saturating))]\n    pub use self::core::num::Saturating;\n}\n\n// None of this crate\'s error handling needs the `From::from` error conversion\n// performed implicitly by the `?` operator or the standard library\'s `try!`\n// macro. This simplified macro gives a 5.5% improvement in compile time\n// compared to standard `try!`, and 9% improvement compared to `?`.\nmacro_rules! tri {\n    ($expr:expr) => {\n        match $expr {\n            Ok(val) => val,\n            Err(err) => return Err(err),\n        }\n    };\n}\n\n////////////////////////////////////////////////////////////////////////////////\n\n#[macro_use]\nmod macros;\n\n#[macro_use]\nmod integer128;\n\npub mod de;\npub mod ser;\n\nmod format;\n\n#[doc(inline)]\npub use crate::de::{Deserialize, Deserializer};\n#[doc(inline)]\npub use crate::ser::{Serialize, Serializer};\n\n// Used by generated code. Not public API.\n#[doc(hidden)]\n#[path = "private/mod.rs"]\npub mod __private;\nuse self::__private as private;\n\n#[cfg(all(not(feature = "std"), no_core_error))]\nmod std_error;\n\n#[macro_export]\n#[doc(hidden)]\nmacro_rules! __require_serde_not_serde_core {\n    () => {\n        ::core::compile_error!(\n            "Serde derive requires a dependency on the serde crate, not serde_core"\n        );\n    };\n}\n',
        }
