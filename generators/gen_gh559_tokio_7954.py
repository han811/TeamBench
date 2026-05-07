"""
Parameterized generator for GH559_tokio_7954.

Source PR:    https://github.com/tokio-rs/tokio/pull/7954
Source Issue: N/A

Seed varies: renames 'assert_eq' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH559_tokio_7954'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH559_tokio_7954'
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
                files[fpath] = files[fpath].replace('assert_eq', 'assert_eq' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH559_tokio_7954',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'tokio-rs/tokio',
                "pr_number": 7954,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/tokio-rs/tokio/pull/7954",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'tokio-stream/src/stream_ext/collect.rs': 'use crate::Stream;\n\nuse core::future::Future;\nuse core::marker::{PhantomData, PhantomPinned};\nuse core::mem;\nuse core::pin::Pin;\nuse core::task::{ready, Context, Poll};\nuse pin_project_lite::pin_project;\n\n// Do not export this struct until `FromStream` can be unsealed.\npin_project! {\n    /// Future returned by the [`collect`](super::StreamExt::collect) method.\n    #[must_use = "futures do nothing unless you `.await` or poll them"]\n    #[derive(Debug)]\n    pub struct Collect<T, U, C>\n    {\n        #[pin]\n        stream: T,\n        collection: C,\n        _output: PhantomData<U>,\n        // Make this future `!Unpin` for compatibility with async trait methods.\n        #[pin]\n        _pin: PhantomPinned,\n    }\n}\n\n/// Convert from a [`Stream`].\n///\n/// This trait is not intended to be used directly. Instead, call\n/// [`StreamExt::collect()`](super::StreamExt::collect).\n///\n/// # Implementing\n///\n/// Currently, this trait may not be implemented by third parties. The trait is\n/// sealed in order to make changes in the future. Stabilization is pending\n/// enhancements to the Rust language.\npub trait FromStream<T>: sealed::FromStreamPriv<T> {}\n\nimpl<T, U> Collect<T, U, U::InternalCollection>\nwhere\n    T: Stream,\n    U: FromStream<T::Item>,\n{\n    pub(super) fn new(stream: T) -> Collect<T, U, U::InternalCollection> {\n        let (lower, upper) = stream.size_hint();\n        let collection = U::initialize(sealed::Internal, lower, upper);\n\n        Collect {\n            stream,\n            collection,\n            _output: PhantomData,\n            _pin: PhantomPinned,\n        }\n    }\n}\n\nimpl<T, U> Future for Collect<T, U, U::InternalCollection>\nwhere\n    T: Stream,\n    U: FromStream<T::Item>,\n{\n    type Output = U;\n\n    fn poll(mut self: Pin<&mut Self>, cx: &mut Context<\'_>) -> Poll<U> {\n        use Poll::Ready;\n\n        loop {\n            let me = self.as_mut().project();\n\n            let item = match ready!(me.stream.poll_next(cx)) {\n                Some(item) => item,\n                None => {\n                    return Ready(U::finalize(sealed::Internal, me.collection));\n                }\n            };\n\n            if !U::extend(sealed::Internal, me.collection, item) {\n                return Ready(U::finalize(sealed::Internal, me.collection));\n            }\n        }\n    }\n}\n\n// ===== FromStream implementations\n\nimpl FromStream<()> for () {}\n\nimpl sealed::FromStreamPriv<()> for () {\n    type InternalCollection = ();\n\n    fn initialize(_: sealed::Internal, _lower: usize, _upper: Option<usize>) {}\n\n    fn extend(_: sealed::Internal, _collection: &mut (), _item: ()) -> bool {\n        true\n    }\n\n    fn finalize(_: sealed::Internal, _collection: &mut ()) {}\n}\n\nimpl<T: AsRef<str>> FromStream<T> for String {}\n\nimpl<T: AsRef<str>> sealed::FromStreamPriv<T> for String {\n    type InternalCollection = String;\n\n    fn initialize(_: sealed::Internal, _lower: usize, _upper: Option<usize>) -> String {\n        String::new()\n    }\n\n    fn extend(_: sealed::Internal, collection: &mut String, item: T) -> bool {\n        collection.push_str(item.as_ref());\n        true\n    }\n\n    fn finalize(_: sealed::Internal, collection: &mut String) -> String {\n        mem::take(collection)\n    }\n}\n\nimpl<T> FromStream<T> for Vec<T> {}\n\nimpl<T> sealed::FromStreamPriv<T> for Vec<T> {\n    type InternalCollection = Vec<T>;\n\n    fn initialize(_: sealed::Internal, lower: usize, _upper: Option<usize>) -> Vec<T> {\n        Vec::with_capacity(lower)\n    }\n\n    fn extend(_: sealed::Internal, collection: &mut Vec<T>, item: T) -> bool {\n        collection.push(item);\n        true\n    }\n\n    fn finalize(_: sealed::Internal, collection: &mut Vec<T>) -> Vec<T> {\n        mem::take(collection)\n    }\n}\n\nimpl<T> FromStream<T> for Box<[T]> {}\n\nimpl<T> sealed::FromStreamPriv<T> for Box<[T]> {\n    type InternalCollection = Vec<T>;\n\n    fn initialize(_: sealed::Internal, lower: usize, upper: Option<usize>) -> Vec<T> {\n        <Vec<T> as sealed::FromStreamPriv<T>>::initialize(sealed::Internal, lower, upper)\n    }\n\n    fn extend(_: sealed::Internal, collection: &mut Vec<T>, item: T) -> bool {\n        <Vec<T> as sealed::FromStreamPriv<T>>::extend(sealed::Internal, collection, item)\n    }\n\n    fn finalize(_: sealed::Internal, collection: &mut Vec<T>) -> Box<[T]> {\n        <Vec<T> as sealed::FromStreamPriv<T>>::finalize(sealed::Internal, collection)\n            .into_boxed_slice()\n    }\n}\n\nimpl<T, U, E> FromStream<Result<T, E>> for Result<U, E> where U: FromStream<T> {}\n\nimpl<T, U, E> sealed::FromStreamPriv<Result<T, E>> for Result<U, E>\nwhere\n    U: FromStream<T>,\n{\n    type InternalCollection = Result<U::InternalCollection, E>;\n\n    fn initialize(\n        _: sealed::Internal,\n        lower: usize,\n        upper: Option<usize>,\n    ) -> Result<U::InternalCollection, E> {\n        Ok(U::initialize(sealed::Internal, lower, upper))\n    }\n\n    fn extend(\n        _: sealed::Internal,\n        collection: &mut Self::InternalCollection,\n        item: Result<T, E>,\n    ) -> bool {\n        assert!(collection.is_ok());\n        match item {\n            Ok(item) => {\n                let collection = collection.as_mut().ok().expect("invalid state");\n                U::extend(sealed::Internal, collection, item)\n            }\n            Err(err) => {\n                *collection = Err(err);\n                false\n            }\n        }\n    }\n\n    fn finalize(_: sealed::Internal, collection: &mut Self::InternalCollection) -> Result<U, E> {\n        if let Ok(collection) = collection.as_mut() {\n            Ok(U::finalize(sealed::Internal, collection))\n        } else {\n            let res = mem::replace(collection, Ok(U::initialize(sealed::Internal, 0, Some(0))));\n\n            Err(res.map(drop).unwrap_err())\n        }\n    }\n}\n\npub(crate) mod sealed {\n    #[doc(hidden)]\n    pub trait FromStreamPriv<T> {\n        /// Intermediate type used during collection process\n        ///\n        /// The name of this type is internal and cannot be relied upon.\n        type InternalCollection;\n\n        /// Initialize the collection\n        fn initialize(\n            internal: Internal,\n            lower: usize,\n            upper: Option<usize>,\n        ) -> Self::InternalCollection;\n\n        /// Extend the collection with the received item\n        ///\n        /// Return `true` to continue streaming, `false` complete collection.\n        fn extend(internal: Internal, collection: &mut Self::InternalCollection, item: T) -> bool;\n\n        /// Finalize collection into target type.\n        fn finalize(internal: Internal, collection: &mut Self::InternalCollection) -> Self;\n    }\n\n    #[allow(missing_debug_implementations)]\n    pub struct Internal;\n}\n',
            'tokio-stream/tests/stream_collect.rs': 'use tokio_stream::{self as stream, StreamExt};\nuse tokio_test::{assert_pending, assert_ready, assert_ready_err, assert_ready_ok, task};\n\nmod support {\n    pub(crate) mod mpsc;\n}\n\nuse support::mpsc;\n\n#[allow(clippy::let_unit_value)]\n#[tokio::test]\nasync fn empty_unit() {\n    // Drains the stream.\n    let mut iter = vec![(), (), ()].into_iter();\n    let _: () = stream::iter(&mut iter).collect().await;\n    assert!(iter.next().is_none());\n}\n\n#[tokio::test]\nasync fn empty_vec() {\n    let coll: Vec<u32> = stream::empty().collect().await;\n    assert!(coll.is_empty());\n}\n\n#[tokio::test]\nasync fn empty_box_slice() {\n    let coll: Box<[u32]> = stream::empty().collect().await;\n    assert!(coll.is_empty());\n}\n\n#[tokio::test]\nasync fn empty_string() {\n    let coll: String = stream::empty::<&str>().collect().await;\n    assert!(coll.is_empty());\n}\n\n#[tokio::test]\nasync fn empty_result() {\n    let coll: Result<Vec<u32>, &str> = stream::empty().collect().await;\n    assert_eq!(Ok(vec![]), coll);\n}\n\n#[tokio::test]\nasync fn collect_vec_items() {\n    let (tx, rx) = mpsc::unbounded_channel_stream();\n    let mut fut = task::spawn(rx.collect::<Vec<i32>>());\n\n    assert_pending!(fut.poll());\n\n    tx.send(1).unwrap();\n    assert!(fut.is_woken());\n    assert_pending!(fut.poll());\n\n    tx.send(2).unwrap();\n    assert!(fut.is_woken());\n    assert_pending!(fut.poll());\n\n    drop(tx);\n    assert!(fut.is_woken());\n    let coll = assert_ready!(fut.poll());\n    assert_eq!(vec![1, 2], coll);\n}\n\n#[tokio::test]\nasync fn collect_string_items() {\n    let (tx, rx) = mpsc::unbounded_channel_stream();\n\n    let mut fut = task::spawn(rx.collect::<String>());\n\n    assert_pending!(fut.poll());\n\n    tx.send("hello ".to_string()).unwrap();\n    assert!(fut.is_woken());\n    assert_pending!(fut.poll());\n\n    tx.send("world".to_string()).unwrap();\n    assert!(fut.is_woken());\n    assert_pending!(fut.poll());\n\n    drop(tx);\n    assert!(fut.is_woken());\n    let coll = assert_ready!(fut.poll());\n    assert_eq!("hello world", coll);\n}\n\n#[tokio::test]\nasync fn collect_str_items() {\n    let (tx, rx) = mpsc::unbounded_channel_stream();\n\n    let mut fut = task::spawn(rx.collect::<String>());\n\n    assert_pending!(fut.poll());\n\n    tx.send("hello ").unwrap();\n    assert!(fut.is_woken());\n    assert_pending!(fut.poll());\n\n    tx.send("world").unwrap();\n    assert!(fut.is_woken());\n    assert_pending!(fut.poll());\n\n    drop(tx);\n    assert!(fut.is_woken());\n    let coll = assert_ready!(fut.poll());\n    assert_eq!("hello world", coll);\n}\n\n#[tokio::test]\nasync fn collect_results_ok() {\n    let (tx, rx) = mpsc::unbounded_channel_stream();\n\n    let mut fut = task::spawn(rx.collect::<Result<String, &str>>());\n\n    assert_pending!(fut.poll());\n\n    tx.send(Ok("hello ")).unwrap();\n    assert!(fut.is_woken());\n    assert_pending!(fut.poll());\n\n    tx.send(Ok("world")).unwrap();\n    assert!(fut.is_woken());\n    assert_pending!(fut.poll());\n\n    drop(tx);\n    assert!(fut.is_woken());\n    let coll = assert_ready_ok!(fut.poll());\n    assert_eq!("hello world", coll);\n}\n\n#[tokio::test]\nasync fn collect_results_err() {\n    let (tx, rx) = mpsc::unbounded_channel_stream();\n\n    let mut fut = task::spawn(rx.collect::<Result<String, &str>>());\n\n    assert_pending!(fut.poll());\n\n    tx.send(Ok("hello ")).unwrap();\n    assert!(fut.is_woken());\n    assert_pending!(fut.poll());\n\n    tx.send(Err("oh no")).unwrap();\n    assert!(fut.is_woken());\n    let err = assert_ready_err!(fut.poll());\n    assert_eq!("oh no", err);\n}\n',
        }
