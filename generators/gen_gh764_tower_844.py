"""
Parameterized generator for GH764_tower_844.

Source PR:    https://github.com/tower-rs/tower/pull/844
Source Issue: N/A

Seed varies: renames 'as_pin_mut' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH764_tower_844'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH764_tower_844'
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
                files[fpath] = files[fpath].replace('as_pin_mut', 'as_pin_mut' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH764_tower_844',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'tower-rs/tower',
                "pr_number": 844,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/tower-rs/tower/pull/844",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'tower/src/limit/concurrency/future.rs': "//! [`Future`] types\n//!\n//! [`Future`]: std::future::Future\nuse pin_project_lite::pin_project;\nuse std::{\n    future::Future,\n    pin::Pin,\n    task::{ready, Context, Poll},\n};\nuse tokio::sync::OwnedSemaphorePermit;\n\npin_project! {\n    /// Future for the [`ConcurrencyLimit`] service.\n    ///\n    /// [`ConcurrencyLimit`]: crate::limit::ConcurrencyLimit\n    #[derive(Debug)]\n    pub struct ResponseFuture<T> {\n        #[pin]\n        inner: T,\n        // Keep this around so that it is dropped when the future completes\n        _permit: OwnedSemaphorePermit,\n    }\n}\n\nimpl<T> ResponseFuture<T> {\n    pub(crate) fn new(inner: T, _permit: OwnedSemaphorePermit) -> ResponseFuture<T> {\n        ResponseFuture { inner, _permit }\n    }\n}\n\nimpl<F, T, E> Future for ResponseFuture<F>\nwhere\n    F: Future<Output = Result<T, E>>,\n{\n    type Output = Result<T, E>;\n\n    fn poll(self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<Self::Output> {\n        Poll::Ready(ready!(self.project().inner.poll(cx)))\n    }\n}\n",
            'tower/src/limit/rate/service.rs': 'use super::Rate;\nuse std::{\n    future::Future,\n    pin::Pin,\n    task::{ready, Context, Poll},\n};\nuse tokio::time::{Instant, Sleep};\nuse tower_service::Service;\n\n/// Enforces a rate limit on the number of requests the underlying\n/// service can handle over a period of time.\n#[derive(Debug)]\npub struct RateLimit<T> {\n    inner: T,\n    rate: Rate,\n    state: State,\n    sleep: Pin<Box<Sleep>>,\n}\n\n#[derive(Debug)]\nenum State {\n    // The service has hit its limit\n    Limited,\n    Ready { until: Instant, rem: u64 },\n}\n\nimpl<T> RateLimit<T> {\n    /// Create a new rate limiter\n    pub fn new(inner: T, rate: Rate) -> Self {\n        let until = Instant::now();\n        let state = State::Ready {\n            until,\n            rem: rate.num(),\n        };\n\n        RateLimit {\n            inner,\n            rate,\n            state,\n            // The sleep won\'t actually be used with this duration, but\n            // we create it eagerly so that we can reset it in place rather than\n            // `Box::pin`ning a new `Sleep` every time we need one.\n            sleep: Box::pin(tokio::time::sleep_until(until)),\n        }\n    }\n\n    /// Get a reference to the inner service\n    pub fn get_ref(&self) -> &T {\n        &self.inner\n    }\n\n    /// Get a mutable reference to the inner service\n    pub fn get_mut(&mut self) -> &mut T {\n        &mut self.inner\n    }\n\n    /// Consume `self`, returning the inner service\n    pub fn into_inner(self) -> T {\n        self.inner\n    }\n}\n\nimpl<S, Request> Service<Request> for RateLimit<S>\nwhere\n    S: Service<Request>,\n{\n    type Response = S::Response;\n    type Error = S::Error;\n    type Future = S::Future;\n\n    fn poll_ready(&mut self, cx: &mut Context<\'_>) -> Poll<Result<(), Self::Error>> {\n        match self.state {\n            State::Ready { .. } => return Poll::Ready(ready!(self.inner.poll_ready(cx))),\n            State::Limited => {\n                if Pin::new(&mut self.sleep).poll(cx).is_pending() {\n                    tracing::trace!("rate limit exceeded; sleeping.");\n                    return Poll::Pending;\n                }\n            }\n        }\n\n        self.state = State::Ready {\n            until: Instant::now() + self.rate.per(),\n            rem: self.rate.num(),\n        };\n\n        Poll::Ready(ready!(self.inner.poll_ready(cx)))\n    }\n\n    fn call(&mut self, request: Request) -> Self::Future {\n        match self.state {\n            State::Ready { mut until, mut rem } => {\n                let now = Instant::now();\n\n                // If the period has elapsed, reset it.\n                if now >= until {\n                    until = now + self.rate.per();\n                    rem = self.rate.num();\n                }\n\n                if rem > 1 {\n                    rem -= 1;\n                    self.state = State::Ready { until, rem };\n                } else {\n                    // The service is disabled until further notice\n                    // Reset the sleep future in place, so that we don\'t have to\n                    // deallocate the existing box and allocate a new one.\n                    self.sleep.as_mut().reset(until);\n                    self.state = State::Limited;\n                }\n\n                // Call the inner future\n                self.inner.call(request)\n            }\n            State::Limited => panic!("service not ready; poll_ready must be called first"),\n        }\n    }\n}\n\n#[cfg(feature = "load")]\nimpl<S> crate::load::Load for RateLimit<S>\nwhere\n    S: crate::load::Load,\n{\n    type Metric = S::Metric;\n    fn load(&self) -> Self::Metric {\n        self.inner.load()\n    }\n}\n',
            'tower/src/load_shed/future.rs': '//! Future types\n\nuse std::fmt;\nuse std::future::Future;\nuse std::pin::Pin;\nuse std::task::{ready, Context, Poll};\n\nuse pin_project_lite::pin_project;\n\nuse super::error::Overloaded;\n\npin_project! {\n    /// Future for the [`LoadShed`] service.\n    ///\n    /// [`LoadShed`]: crate::load_shed::LoadShed\n    pub struct ResponseFuture<F> {\n        #[pin]\n        state: ResponseState<F>,\n    }\n}\n\npin_project! {\n    #[project = ResponseStateProj]\n    enum ResponseState<F> {\n        Called {\n            #[pin]\n            fut: F\n        },\n        Overloaded,\n    }\n}\n\nimpl<F> ResponseFuture<F> {\n    pub(crate) fn called(fut: F) -> Self {\n        ResponseFuture {\n            state: ResponseState::Called { fut },\n        }\n    }\n\n    pub(crate) fn overloaded() -> Self {\n        ResponseFuture {\n            state: ResponseState::Overloaded,\n        }\n    }\n}\n\nimpl<F, T, E> Future for ResponseFuture<F>\nwhere\n    F: Future<Output = Result<T, E>>,\n    E: Into<crate::BoxError>,\n{\n    type Output = Result<T, crate::BoxError>;\n\n    fn poll(self: Pin<&mut Self>, cx: &mut Context<\'_>) -> Poll<Self::Output> {\n        match self.project().state.project() {\n            ResponseStateProj::Called { fut } => {\n                Poll::Ready(ready!(fut.poll(cx)).map_err(Into::into))\n            }\n            ResponseStateProj::Overloaded => Poll::Ready(Err(Overloaded::new().into())),\n        }\n    }\n}\n\nimpl<F> fmt::Debug for ResponseFuture<F>\nwhere\n    // bounds for future-proofing...\n    F: fmt::Debug,\n{\n    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {\n        f.write_str("ResponseFuture")\n    }\n}\n',
            'tower/src/util/optional/future.rs': "use super::error;\nuse pin_project_lite::pin_project;\nuse std::{\n    future::Future,\n    pin::Pin,\n    task::{ready, Context, Poll},\n};\n\npin_project! {\n    /// Response future returned by [`Optional`].\n    ///\n    /// [`Optional`]: crate::util::Optional\n    #[derive(Debug)]\n    pub struct ResponseFuture<T> {\n        #[pin]\n        inner: Option<T>,\n    }\n}\n\nimpl<T> ResponseFuture<T> {\n    pub(crate) fn new(inner: Option<T>) -> ResponseFuture<T> {\n        ResponseFuture { inner }\n    }\n}\n\nimpl<F, T, E> Future for ResponseFuture<F>\nwhere\n    F: Future<Output = Result<T, E>>,\n    E: Into<crate::BoxError>,\n{\n    type Output = Result<T, crate::BoxError>;\n\n    fn poll(self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<Self::Output> {\n        match self.project().inner.as_pin_mut() {\n            Some(inner) => Poll::Ready(Ok(ready!(inner.poll(cx)).map_err(Into::into)?)),\n            None => Poll::Ready(Err(error::None::new().into())),\n        }\n    }\n}\n",
        }
