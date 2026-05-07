"""
Parameterized generator for GH488_tokio_7923.

Source PR:    https://github.com/tokio-rs/tokio/pull/7923
Source Issue: N/A

Seed varies: renames 'additional' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH488_tokio_7923'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH488_tokio_7923'
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
                files[fpath] = files[fpath].replace('additional', 'additional' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH488_tokio_7923',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'tokio-rs/tokio',
                "pr_number": 7923,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/tokio-rs/tokio/pull/7923",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'tokio/src/task/blocking.rs': 'use crate::task::JoinHandle;\n\ncfg_rt_multi_thread! {\n    /// Runs the provided blocking function on the current thread without\n    /// blocking the executor.\n    ///\n    /// In general, issuing a blocking call or performing a lot of compute in a\n    /// future without yielding is problematic, as it may prevent the executor\n    /// from driving other tasks forward. Calling this function informs the\n    /// executor that the currently executing task is about to block the thread,\n    /// so the executor is able to hand off any other tasks it has to a new\n    /// worker thread before that happens. See the [CPU-bound tasks and blocking\n    /// code][blocking] section for more information.\n    ///\n    /// Be aware that although this function avoids starving other independently\n    /// spawned tasks, any other code running concurrently in the same task will\n    /// be suspended during the call to `block_in_place`. This can happen e.g.\n    /// when using the [`join!`] macro. To avoid this issue, use\n    /// [`spawn_blocking`] instead of `block_in_place`.\n    ///\n    /// Note that this function cannot be used within a [`current_thread`] runtime\n    /// because in this case there are no other worker threads to hand off tasks\n    /// to. On the other hand, calling the function outside a runtime is\n    /// allowed. In this case, `block_in_place` just calls the provided closure\n    /// normally.\n    ///\n    /// Code running behind `block_in_place` cannot be cancelled. When you shut\n    /// down the executor, it will wait indefinitely for all blocking operations\n    /// to finish. You can use [`shutdown_timeout`] to stop waiting for them\n    /// after a certain timeout. Be aware that this will still not cancel the\n    /// tasks — they are simply allowed to keep running after the method\n    /// returns.\n    ///\n    /// [blocking]: ../index.html#cpu-bound-tasks-and-blocking-code\n    /// [`spawn_blocking`]: fn@crate::task::spawn_blocking\n    /// [`join!`]: macro@join\n    /// [`thread::spawn`]: fn@std::thread::spawn\n    /// [`shutdown_timeout`]: fn@crate::runtime::Runtime::shutdown_timeout\n    ///\n    /// # Examples\n    ///\n    /// ```\n    /// use tokio::task;\n    ///\n    /// # async fn docs() {\n    /// task::block_in_place(move || {\n    ///     // do some compute-heavy work or call synchronous code\n    /// });\n    /// # }\n    /// ```\n    ///\n    /// Code running inside `block_in_place` may use `block_on` to reenter the\n    /// async context.\n    ///\n    /// ```\n    /// use tokio::task;\n    /// use tokio::runtime::Handle;\n    ///\n    /// # async fn docs() {\n    /// task::block_in_place(move || {\n    ///     Handle::current().block_on(async move {\n    ///         // do something async\n    ///     });\n    /// });\n    /// # }\n    /// ```\n    ///\n    /// # Panics\n    ///\n    /// This function panics if called from a [`current_thread`] runtime.\n    ///\n    /// [`current_thread`]: fn@crate::runtime::Builder::new_current_thread\n    #[track_caller]\n    pub fn block_in_place<F, R>(f: F) -> R\n    where\n        F: FnOnce() -> R,\n    {\n        crate::runtime::scheduler::block_in_place(f)\n    }\n}\n\ncfg_rt! {\n    /// Runs the provided closure on a thread where blocking is acceptable.\n    ///\n    /// In general, issuing a blocking call or performing a lot of compute in a\n    /// future without yielding is problematic, as it may prevent the executor from\n    /// driving other futures forward. This function runs the provided closure on a\n    /// thread dedicated to blocking operations. See the [CPU-bound tasks and\n    /// blocking code][blocking] section for more information.\n    ///\n    /// Tokio will spawn more blocking threads when they are requested through this\n    /// function until the upper limit configured on the [`Builder`] is reached.\n    /// After reaching the upper limit, the tasks are put in a queue.\n    /// The thread limit is very large by default, because `spawn_blocking` is often\n    /// used for various kinds of IO operations that cannot be performed\n    /// asynchronously.  When you run CPU-bound code using `spawn_blocking`, you\n    /// should keep this large upper limit in mind. When running many CPU-bound\n    /// computations, a semaphore or some other synchronization primitive should be\n    /// used to limit the number of computations executed in parallel. Specialized\n    /// CPU-bound executors, such as [rayon], may also be a good fit.\n    ///\n    /// This function is intended for non-async operations that eventually finish on\n    /// their own. If you want to spawn an ordinary thread, you should use\n    /// [`thread::spawn`] instead.\n    ///\n    /// Be aware that tasks spawned using `spawn_blocking` cannot be aborted\n    /// because they are not async. If you call [`abort`] on a `spawn_blocking`\n    /// task, then this *will not have any effect*, and the task will continue\n    /// running normally. The exception is if the task has not started running\n    /// yet; in that case, calling `abort` may prevent the task from starting.\n    ///\n    /// When you shut down the executor, it will attempt to `abort` all tasks\n    /// including `spawn_blocking` tasks. However, `spawn_blocking` tasks\n    /// cannot be aborted once they start running, which means that runtime\n    /// shutdown will wait indefinitely for all started `spawn_blocking` to\n    /// finish running. You can use [`shutdown_timeout`] to stop waiting for\n    /// them after a certain timeout. Be aware that this will still not cancel\n    /// the tasks — they are simply allowed to keep running after the method\n    /// returns. It is possible for a blocking task to be cancelled if it has\n    /// not yet started running, but this is not guaranteed.\n    ///\n    /// Note that if you are using the single threaded runtime, this function will\n    /// still spawn additional threads for blocking operations. The current-thread\n    /// scheduler\'s single thread is only used for asynchronous code.\n    ///\n    /// # Related APIs and patterns for bridging asynchronous and blocking code\n    ///\n    /// In simple cases, it is sufficient to have the closure accept input\n    /// parameters at creation time and return a single value (or struct/tuple, etc.).\n    ///\n    /// For more complex situations in which it is desirable to stream data to or from\n    /// the synchronous context, the [`mpsc channel`] has `blocking_send` and\n    /// `blocking_recv` methods for use in non-async code such as the thread created\n    /// by `spawn_blocking`.\n    ///\n    /// Another option is [`SyncIoBridge`] for cases where the synchronous context\n    /// is operating on byte streams.  For example, you might use an asynchronous\n    /// HTTP client such as [hyper] to fetch data, but perform complex parsing\n    /// of the payload body using a library written for synchronous I/O.\n    ///\n    /// Finally, see also [Bridging with sync code][bridgesync] for discussions\n    /// around the opposite case of using Tokio as part of a larger synchronous\n    /// codebase.\n    ///\n    /// [`Builder`]: struct@crate::runtime::Builder\n    /// [blocking]: ../index.html#cpu-bound-tasks-and-blocking-code\n    /// [rayon]: https://docs.rs/rayon\n    /// [`mpsc channel`]: crate::sync::mpsc\n    /// [`SyncIoBridge`]: https://docs.rs/tokio-util/latest/tokio_util/io/struct.SyncIoBridge.html\n    /// [hyper]: https://docs.rs/hyper\n    /// [`thread::spawn`]: fn@std::thread::spawn\n    /// [`shutdown_timeout`]: fn@crate::runtime::Runtime::shutdown_timeout\n    /// [bridgesync]: https://tokio.rs/tokio/topics/bridging\n    /// [`AtomicBool`]: struct@std::sync::atomic::AtomicBool\n    /// [`abort`]: crate::task::JoinHandle::abort\n    ///\n    /// # Examples\n    ///\n    /// Pass an input value and receive result of computation:\n    ///\n    /// ```\n    /// use tokio::task;\n    ///\n    /// # async fn docs() -> Result<(), Box<dyn std::error::Error>>{\n    /// // Initial input\n    /// let mut v = "Hello, ".to_string();\n    /// let res = task::spawn_blocking(move || {\n    ///     // Stand-in for compute-heavy work or using synchronous APIs\n    ///     v.push_str("world");\n    ///     // Pass ownership of the value back to the asynchronous context\n    ///     v\n    /// }).await?;\n    ///\n    /// // `res` is the value returned from the thread\n    /// assert_eq!(res.as_str(), "Hello, world");\n    /// # Ok(())\n    /// # }\n    /// ```\n    ///\n    /// Use a channel:\n    ///\n    /// ```\n    /// use tokio::task;\n    /// use tokio::sync::mpsc;\n    ///\n    /// # async fn docs() {\n    /// let (tx, mut rx) = mpsc::channel(2);\n    /// let start = 5;\n    /// let worker = task::spawn_blocking(move || {\n    ///     for x in 0..10 {\n    ///         // Stand in for complex computation\n    ///         tx.blocking_send(start + x).unwrap();\n    ///     }\n    /// });\n    ///\n    /// let mut acc = 0;\n    /// while let Some(v) = rx.recv().await {\n    ///     acc += v;\n    /// }\n    /// assert_eq!(acc, 95);\n    /// worker.await.unwrap();\n    /// # }\n    /// ```\n    #[track_caller]\n    pub fn spawn_blocking<F, R>(f: F) -> JoinHandle<R>\n    where\n        F: FnOnce() -> R + Send + \'static,\n        R: Send + \'static,\n    {\n        crate::runtime::spawn_blocking(f)\n    }\n}\n',
        }
