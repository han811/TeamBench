"""
Parameterized generator for GH268_tower_25.

Source PR:    https://github.com/tower-rs/tower/pull/25
Source Issue: N/A

Seed varies: renames 'able' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH268_tower_25'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH268_tower_25'
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
            task_id='GH268_tower_25',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'tower-rs/tower',
                "pr_number": 25,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/tower-rs/tower/pull/25",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'src/lib.rs': '//! Definition of the core `Service` trait to Tower\n//!\n//! More information can be found on [the trait] itself and online at\n//! [https://tower.rs](https://tower.rs)\n//!\n//! [the trait]: trait.Service.html\n\n#![deny(missing_docs)]\n#![doc(html_root_url = "https://docs.rs/tower/0.1")]\n\n#[macro_use]\nextern crate futures;\n\nuse futures::{Future, IntoFuture, Poll};\n\nuse std::rc::Rc;\nuse std::sync::Arc;\n\n/// An asynchronous function from `Request` to a `Response`.\n///\n/// The `Service` trait is a simplified interface making it easy to write\n/// network applications in a modular and reusable way, decoupled from the\n/// underlying protocol. It is one of Tower\'s fundamental abstractions.\n///\n/// # Functional\n///\n/// A `Service` is a function of a `Request`. It immediately returns a\n/// `Future` representing the eventual completion of processing the\n/// request. The actual request processing may happen at any time in the\n/// future, on any thread or executor. The processing may depend on calling\n/// other services. At some point in the future, the processing will complete,\n/// and the `Future` will resolve to a response or error.\n///\n/// At a high level, the `Service::call` represents an RPC request. The\n/// `Service` value can be a server or a client.\n///\n/// # Server\n///\n/// An RPC server *implements* the `Service` trait. Requests received by the\n/// server over the network are deserialized then passed as an argument to the\n/// server value. The returned response is sent back over the network.\n///\n/// As an example, here is how an HTTP request is processed by a server:\n///\n/// ```rust,ignore\n/// impl Service for HelloWorld {\n///     type Request = http::Request;\n///     type Response = http::Response;\n///     type Error = http::Error;\n///     type Future = Box<Future<Item = Self::Response, Error = http::Error>>;\n///\n///     fn poll_ready(&mut self) -> Poll<(), Self::Error> {\n///         Ok(Async::Ready(()))\n///     }\n///\n///     fn call(&mut self, req: http::Request) -> Self::Future {\n///         // Create the HTTP response\n///         let resp = http::Response::ok()\n///             .with_body(b"hello world\\n");\n///\n///         // Return the response as an immediate future\n///         futures::finished(resp).boxed()\n///     }\n/// }\n/// ```\n///\n/// # Client\n///\n/// A client consumes a service by using a `Service` value. The client may\n/// issue requests by invoking `call` and passing the request as an argument.\n/// It then receives the response by waiting for the returned future.\n///\n/// As an example, here is how a Redis request would be issued:\n///\n/// ```rust,ignore\n/// let client = redis::Client::new()\n///     .connect("127.0.0.1:6379".parse().unwrap())\n///     .unwrap();\n///\n/// let resp = client.call(Cmd::set("foo", "this is the value of foo"));\n///\n/// // Wait for the future to resolve\n/// println!("Redis response: {:?}", await(resp));\n/// ```\n///\n/// # Middleware\n///\n/// More often than not, all the pieces needed for writing robust, scalable\n/// network applications are the same no matter the underlying protocol. By\n/// unifying the API for both clients and servers in a protocol agnostic way,\n/// it is possible to write middleware that provide these pieces in a\n/// reusable way.\n///\n/// For example, take timeouts as an example:\n///\n/// ```rust,ignore\n/// use tower::Service;\n/// use futures::Future;\n/// use std::time::Duration;\n///\n/// use tokio_timer::Timer;\n///\n/// pub struct Timeout<T> {\n///     upstream: T,\n///     delay: Duration,\n///     timer: Timer,\n/// }\n///\n/// pub struct Expired;\n///\n/// impl<T> Timeout<T> {\n///     pub fn new(upstream: T, delay: Duration) -> Timeout<T> {\n///         Timeout {\n///             upstream: upstream,\n///             delay: delay,\n///             timer: Timer::default(),\n///         }\n///     }\n/// }\n///\n/// impl<T> Service for Timeout<T>\n///     where T: Service,\n///           T::Error: From<Expired>,\n/// {\n///     type Request = T::Request;\n///     type Response = T::Response;\n///     type Error = T::Error;\n///     type Future = Box<Future<Item = Self::Response, Error = Self::Error>>;\n///\n///     fn poll_ready(&mut self) -> Poll<(), Self::Error> {\n///         Ok(Async::Ready(()))\n///     }\n///\n///     fn call(&mut self, req: Self::Req) -> Self::Future {\n///         let timeout = self.timer.sleep(self.delay)\n///             .and_then(|_| Err(Self::Error::from(Expired)));\n///\n///         self.upstream.call(req)\n///             .select(timeout)\n///             .map(|(v, _)| v)\n///             .map_err(|(e, _)| e)\n///             .boxed()\n///     }\n/// }\n///\n/// ```\n///\n/// The above timeout implementation is decoupled from the underlying protocol\n/// and is also decoupled from client or server concerns. In other words, the\n/// same timeout middleware could be used in either a client or a server.\n///\n/// # Backpressure\n///\n/// Calling an at capacity `Service` (i.e., it temporarily unable to process a\n/// request) should result in an error. The caller is responsible for ensuring\n/// that the service is ready to receive the request before calling it.\n///\n/// `Service` provides a mechanism by which the caller is able to coordinate\n/// readiness. `Service::poll_ready` returns `Ready` if the service expects that\n/// it is able to process a request.\npub trait Service {\n\n    /// Requests handled by the service.\n    type Request;\n\n    /// Responses given by the service.\n    type Response;\n\n    /// Errors produced by the service.\n    type Error;\n\n    /// The future response value.\n    type Future: Future<Item = Self::Response, Error = Self::Error>;\n\n    /// A future yielding the service when it is ready to accept a request.\n    fn ready(self) -> Ready<Self> where Self: Sized {\n        Ready { inner: Some(self) }\n    }\n\n    /// Returns `Ready` when the service is able to process requests.\n    ///\n    /// If the service is at capacity, then `NotReady` is returned and the task\n    /// is notified when the service becomes ready again. This function is\n    /// expected to be called while on a task.\n    ///\n    /// This is a **best effort** implementation. False positives are permitted.\n    /// It is permitted for the service to return `Ready` from a `poll_ready`\n    /// call and the next invocation of `call` results in an error.\n    fn poll_ready(&mut self) -> Poll<(), Self::Error>;\n\n    /// Process the request and return the response asynchronously.\n    ///\n    /// This function is expected to be callable off task. As such,\n    /// implementations should take care to not call `poll_ready`. If the\n    /// service is at capacity and the request is unable to be handled, the\n    /// returned `Future` should resolve to an error.\n    fn call(&mut self, req: Self::Request) -> Self::Future;\n}\n\n/// Future yielding a `Service` once the service is ready to process a request\npub struct Ready<T> {\n    inner: Option<T>,\n}\n\n/// Creates new `Service` values.\npub trait NewService {\n    /// Requests handled by the service\n    type Request;\n\n    /// Responses given by the service\n    type Response;\n\n    /// Errors produced by the service\n    type Error;\n\n    /// The `Service` value created by this factory\n    type Service: Service<Request = Self::Request, Response = Self::Response, Error = Self::Error>;\n\n    /// Errors produced while building a service.\n    type InitError;\n\n    /// The future of the `Service` instance.\n    type Future: Future<Item = Self::Service, Error = Self::InitError>;\n\n    /// Create and return a new service value asynchronously.\n    fn new_service(&self) -> Self::Future;\n}\n\nimpl<T> Future for Ready<T>\nwhere T: Service,\n{\n    type Item = T;\n    type Error = T::Error;\n\n    fn poll(&mut self) -> Poll<T, T::Error> {\n        match self.inner {\n            Some(ref mut service) => {\n                let _ = try_ready!(service.poll_ready());\n            }\n            None => panic!("called `poll` after future completed"),\n        }\n\n        Ok(self.inner.take().unwrap().into())\n    }\n}\n\nimpl<F, R, E, S> NewService for F\n    where F: Fn() -> R,\n          R: IntoFuture<Item = S, Error = E>,\n          S: Service,\n{\n    type Request = S::Request;\n    type Response = S::Response;\n    type Error = S::Error;\n    type Service = S;\n    type InitError = E;\n    type Future = R::Future;\n\n    fn new_service(&self) -> Self::Future {\n        (*self)().into_future()\n    }\n}\n\nimpl<S: NewService + ?Sized> NewService for Arc<S> {\n    type Request = S::Request;\n    type Response = S::Response;\n    type Error = S::Error;\n    type Service = S::Service;\n    type InitError = S::InitError;\n    type Future = S::Future;\n\n    fn new_service(&self) -> Self::Future {\n        (**self).new_service()\n    }\n}\n\nimpl<S: NewService + ?Sized> NewService for Rc<S> {\n    type Request = S::Request;\n    type Response = S::Response;\n    type Error = S::Error;\n    type Service = S::Service;\n    type InitError = S::InitError;\n    type Future = S::Future;\n\n    fn new_service(&self) -> Self::Future {\n        (**self).new_service()\n    }\n}\n\nimpl<\'a, S: Service + \'a> Service for &\'a mut S {\n    type Request = S::Request;\n    type Response = S::Response;\n    type Error = S::Error;\n    type Future = S::Future;\n\n    fn poll_ready(&mut self) -> Poll<(), S::Error> {\n        (**self).poll_ready()\n    }\n\n    fn call(&mut self, request: S::Request) -> S::Future {\n        (**self).call(request)\n    }\n}\n\nimpl<S: Service + ?Sized> Service for Box<S> {\n    type Request = S::Request;\n    type Response = S::Response;\n    type Error = S::Error;\n    type Future = S::Future;\n\n    fn poll_ready(&mut self) -> Poll<(), S::Error> {\n        (**self).poll_ready()\n    }\n\n    fn call(&mut self, request: S::Request) -> S::Future {\n        (**self).call(request)\n    }\n}\n',
        }
