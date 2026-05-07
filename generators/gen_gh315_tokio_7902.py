"""
Parameterized generator for GH315_tokio_7902.

Source PR:    https://github.com/tokio-rs/tokio/pull/7902
Source Issue: N/A

Seed varies: renames 'atomic' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH315_tokio_7902'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH315_tokio_7902'
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
                files[fpath] = files[fpath].replace('atomic', 'atomic' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH315_tokio_7902',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'tokio-rs/tokio',
                "pr_number": 7902,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/tokio-rs/tokio/pull/7902",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'tokio/src/loom/mocked.rs': "pub(crate) use loom::*;\n\npub(crate) mod sync {\n\n    pub(crate) use loom::sync::{MutexGuard, RwLockReadGuard, RwLockWriteGuard};\n\n    #[derive(Debug)]\n    pub(crate) struct Mutex<T>(loom::sync::Mutex<T>);\n\n    #[allow(dead_code)]\n    impl<T> Mutex<T> {\n        #[inline]\n        pub(crate) fn new(t: T) -> Mutex<T> {\n            Mutex(loom::sync::Mutex::new(t))\n        }\n\n        #[inline]\n        #[track_caller]\n        pub(crate) fn lock(&self) -> MutexGuard<'_, T> {\n            self.0.lock().unwrap()\n        }\n\n        #[inline]\n        pub(crate) fn try_lock(&self) -> Option<MutexGuard<'_, T>> {\n            self.0.try_lock().ok()\n        }\n    }\n\n    #[derive(Debug)]\n    pub(crate) struct RwLock<T>(loom::sync::RwLock<T>);\n\n    #[allow(dead_code)]\n    impl<T> RwLock<T> {\n        #[inline]\n        pub(crate) fn new(t: T) -> Self {\n            Self(loom::sync::RwLock::new(t))\n        }\n\n        #[inline]\n        pub(crate) fn read(&self) -> RwLockReadGuard<'_, T> {\n            self.0.read().unwrap()\n        }\n\n        #[inline]\n        pub(crate) fn try_read(&self) -> Option<RwLockReadGuard<'_, T>> {\n            self.0.try_read().ok()\n        }\n\n        #[inline]\n        pub(crate) fn write(&self) -> RwLockWriteGuard<'_, T> {\n            self.0.write().unwrap()\n        }\n\n        #[inline]\n        pub(crate) fn try_write(&self) -> Option<RwLockWriteGuard<'_, T>> {\n            self.0.try_write().ok()\n        }\n    }\n\n    pub(crate) use loom::sync::*;\n\n    pub(crate) mod atomic {\n        pub(crate) use loom::sync::atomic::*;\n\n        // TODO: implement a loom version\n        pub(crate) type StaticAtomicU64 = std::sync::atomic::AtomicU64;\n    }\n}\n\npub(crate) mod rand {\n    pub(crate) fn seed() -> u64 {\n        1\n    }\n}\n\npub(crate) mod sys {\n    pub(crate) fn num_cpus() -> usize {\n        2\n    }\n}\n\npub(crate) mod thread {\n    pub use loom::lazy_static::AccessError;\n    pub use loom::thread::*;\n}\n",
            'tokio/src/loom/std/atomic_u64.rs': '//! Implementation of an atomic `u64` cell. On 64 bit platforms, this is a\n//! re-export of `AtomicU64`. On 32 bit platforms, this is implemented using a\n//! `Mutex`.\n\n// `AtomicU64` can only be used on targets with `target_has_atomic` is 64 or greater.\n// Once `cfg_target_has_atomic` feature is stable, we can replace it with\n// `#[cfg(target_has_atomic = "64")]`.\n// Refs: https://github.com/rust-lang/rust/tree/master/src/librustc_target\ncfg_has_atomic_u64! {\n    #[path = "atomic_u64_native.rs"]\n    mod imp;\n}\n\ncfg_not_has_atomic_u64! {\n    #[path = "atomic_u64_as_mutex.rs"]\n    mod imp;\n}\n\npub(crate) use imp::{AtomicU64, StaticAtomicU64};\n',
            'tokio/src/loom/std/mod.rs': '#![cfg_attr(any(not(feature = "full"), loom), allow(unused_imports, dead_code))]\n\nmod atomic_u16;\nmod atomic_u32;\nmod atomic_u64;\nmod atomic_usize;\nmod barrier;\nmod mutex;\n#[cfg(all(feature = "parking_lot", not(miri)))]\nmod parking_lot;\nmod rwlock;\nmod unsafe_cell;\n\npub(crate) mod cell {\n    pub(crate) use super::unsafe_cell::UnsafeCell;\n}\n\n#[cfg(any(\n    feature = "net",\n    feature = "process",\n    feature = "signal",\n    feature = "sync",\n))]\npub(crate) mod future {\n    pub(crate) use crate::sync::AtomicWaker;\n}\n\npub(crate) mod hint {\n    pub(crate) use std::hint::spin_loop;\n}\n\npub(crate) mod rand {\n    use std::collections::hash_map::RandomState;\n    use std::hash::{BuildHasher, Hash, Hasher};\n    use std::sync::atomic::AtomicU32;\n    use std::sync::atomic::Ordering::Relaxed;\n\n    static COUNTER: AtomicU32 = AtomicU32::new(1);\n\n    pub(crate) fn seed() -> u64 {\n        let rand_state = RandomState::new();\n        // Hash some unique-ish data to generate some new state\n        rand_state.hash_one(COUNTER.fetch_add(1, Relaxed))\n    }\n}\n\npub(crate) mod sync {\n    pub(crate) use std::sync::{Arc, Weak};\n\n    // Below, make sure all the feature-influenced types are exported for\n    // internal use. Note however that some are not _currently_ named by\n    // consuming code.\n\n    // Not using parking_lot in Miri due to <https://github.com/Amanieu/parking_lot/issues/477>.\n    #[cfg(all(feature = "parking_lot", not(miri)))]\n    #[allow(unused_imports)]\n    pub(crate) use crate::loom::std::parking_lot::{\n        Condvar, Mutex, MutexGuard, RwLock, RwLockReadGuard, WaitTimeoutResult,\n    };\n\n    #[cfg(not(all(feature = "parking_lot", not(miri))))]\n    #[allow(unused_imports)]\n    pub(crate) use std::sync::{Condvar, MutexGuard, RwLockReadGuard, WaitTimeoutResult};\n\n    #[cfg(not(all(feature = "parking_lot", not(miri))))]\n    pub(crate) use crate::loom::std::mutex::Mutex;\n\n    #[cfg(not(all(feature = "parking_lot", not(miri))))]\n    pub(crate) use crate::loom::std::rwlock::RwLock;\n\n    pub(crate) mod atomic {\n        pub(crate) use crate::loom::std::atomic_u16::AtomicU16;\n        pub(crate) use crate::loom::std::atomic_u32::AtomicU32;\n        pub(crate) use crate::loom::std::atomic_u64::{AtomicU64, StaticAtomicU64};\n        pub(crate) use crate::loom::std::atomic_usize::AtomicUsize;\n\n        pub(crate) use std::sync::atomic::{fence, AtomicBool, AtomicPtr, AtomicU8, Ordering};\n    }\n\n    pub(crate) use super::barrier::Barrier;\n}\n\npub(crate) mod sys {\n    #[cfg(feature = "rt-multi-thread")]\n    pub(crate) fn num_cpus() -> usize {\n        use std::num::NonZeroUsize;\n\n        const ENV_WORKER_THREADS: &str = "TOKIO_WORKER_THREADS";\n\n        match std::env::var(ENV_WORKER_THREADS) {\n            Ok(s) => {\n                let n = s.parse().unwrap_or_else(|e| {\n                    panic!("\\"{ENV_WORKER_THREADS}\\" must be usize, error: {e}, value: {s}")\n                });\n                assert!(n > 0, "\\"{ENV_WORKER_THREADS}\\" cannot be set to 0");\n                n\n            }\n            Err(std::env::VarError::NotPresent) => {\n                std::thread::available_parallelism().map_or(1, NonZeroUsize::get)\n            }\n            Err(std::env::VarError::NotUnicode(e)) => {\n                panic!("\\"{ENV_WORKER_THREADS}\\" must be valid unicode, error: {e:?}")\n            }\n        }\n    }\n\n    #[cfg(not(feature = "rt-multi-thread"))]\n    pub(crate) fn num_cpus() -> usize {\n        1\n    }\n}\n\npub(crate) mod thread {\n    #[inline]\n    pub(crate) fn yield_now() {\n        std::hint::spin_loop();\n    }\n\n    #[allow(unused_imports)]\n    pub(crate) use std::thread::{\n        current, panicking, park, park_timeout, sleep, spawn, AccessError, Builder, JoinHandle,\n        LocalKey, Result, Thread, ThreadId,\n    };\n}\n',
            'tokio/src/runtime/task/id.rs': 'use crate::runtime::context;\n\nuse std::{fmt, num::NonZeroU64};\n\n/// An opaque ID that uniquely identifies a task relative to all other currently\n/// running tasks.\n///\n/// A task\'s ID may be re-used for another task only once *both* of the\n/// following happen:\n/// 1. The task itself exits.\n/// 2. There is no active [`JoinHandle`] associated with this task.\n///\n/// A [`JoinHandle`] is considered active in the following situations:\n/// - You are explicitly holding a [`JoinHandle`], [`AbortHandle`], or\n///   `tokio_util::task::AbortOnDropHandle`.\n/// - The task is being tracked by a [`JoinSet`] or `tokio_util::task::JoinMap`.\n///\n/// # Notes\n///\n/// - Task IDs are *not* sequential, and do not indicate the order in which\n///   tasks are spawned, what runtime a task is spawned on, or any other data.\n/// - The task ID of the currently running task can be obtained from inside the\n///   task via the [`task::try_id()`](crate::task::try_id()) and\n///   [`task::id()`](crate::task::id()) functions and from outside the task via\n///   the [`JoinHandle::id()`](crate::task::JoinHandle::id()) function.\n///\n/// [`JoinHandle`]: crate::task::JoinHandle\n/// [`AbortHandle`]: crate::task::AbortHandle\n/// [`JoinSet`]: crate::task::JoinSet\n#[cfg_attr(docsrs, doc(cfg(all(feature = "rt"))))]\n#[derive(Clone, Copy, Debug, Hash, Eq, PartialEq, PartialOrd, Ord)]\npub struct Id(pub(crate) NonZeroU64);\n\n/// Returns the [`Id`] of the currently running task.\n///\n/// # Panics\n///\n/// This function panics if called from outside a task. Please note that calls\n/// to `block_on` do not have task IDs, so the method will panic if called from\n/// within a call to `block_on`. For a version of this function that doesn\'t\n/// panic, see [`task::try_id()`](crate::runtime::task::try_id()).\n///\n/// [task ID]: crate::task::Id\n#[track_caller]\npub fn id() -> Id {\n    context::current_task_id().expect("Can\'t get a task id when not inside a task")\n}\n\n/// Returns the [`Id`] of the currently running task, or `None` if called outside\n/// of a task.\n///\n/// This function is similar to  [`task::id()`](crate::runtime::task::id()), except\n/// that it returns `None` rather than panicking if called outside of a task\n/// context.\n///\n/// [task ID]: crate::task::Id\n#[track_caller]\npub fn try_id() -> Option<Id> {\n    context::current_task_id()\n}\n\nimpl fmt::Display for Id {\n    fn fmt(&self, f: &mut fmt::Formatter<\'_>) -> fmt::Result {\n        self.0.fmt(f)\n    }\n}\n\nimpl Id {\n    pub(crate) fn next() -> Self {\n        use crate::loom::sync::atomic::Ordering::Relaxed;\n        use crate::loom::sync::atomic::StaticAtomicU64;\n\n        #[cfg(all(test, loom))]\n        crate::loom::lazy_static! {\n            static ref NEXT_ID: StaticAtomicU64 = StaticAtomicU64::new(1);\n        }\n\n        #[cfg(not(all(test, loom)))]\n        static NEXT_ID: StaticAtomicU64 = StaticAtomicU64::new(1);\n\n        loop {\n            let id = NEXT_ID.fetch_add(1, Relaxed);\n            if let Some(id) = NonZeroU64::new(id) {\n                return Self(id);\n            }\n        }\n    }\n\n    pub(crate) fn as_u64(&self) -> u64 {\n        self.0.get()\n    }\n}\n',
            'tokio/src/runtime/thread_id.rs': 'use std::num::NonZeroU64;\n\n#[derive(Eq, PartialEq, Clone, Copy, Hash, Debug)]\npub(crate) struct ThreadId(NonZeroU64);\n\nimpl ThreadId {\n    pub(crate) fn next() -> Self {\n        use crate::loom::sync::atomic::{Ordering::Relaxed, StaticAtomicU64};\n\n        static NEXT_ID: StaticAtomicU64 = StaticAtomicU64::new(0);\n\n        let mut last = NEXT_ID.load(Relaxed);\n        loop {\n            let id = match last.checked_add(1) {\n                Some(id) => id,\n                None => exhausted(),\n            };\n\n            match NEXT_ID.compare_exchange_weak(last, id, Relaxed, Relaxed) {\n                Ok(_) => return ThreadId(NonZeroU64::new(id).unwrap()),\n                Err(id) => last = id,\n            }\n        }\n    }\n}\n\n#[cold]\n#[allow(dead_code)]\nfn exhausted() -> ! {\n    panic!("failed to generate unique thread ID: bitspace exhausted")\n}\n',
        }
