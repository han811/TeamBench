"""
Parameterized generator for GH812_tower_834.

Source PR:    https://github.com/tower-rs/tower/pull/834
Source Issue: N/A

Seed varies: renames 'allows' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH812_tower_834'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH812_tower_834'
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
            task_id='GH812_tower_834',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'tower-rs/tower',
                "pr_number": 834,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/tower-rs/tower/pull/834",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'tower-layer/src/identity.rs': 'use super::Layer;\nuse core::fmt;\n\n/// A no-op middleware.\n///\n/// When wrapping a [`Service`], the [`Identity`] layer returns the provided\n/// service without modifying it.\n///\n/// [`Service`]: https://docs.rs/tower-service/latest/tower_service/trait.Service.html\n#[derive(Default, Clone)]\npub struct Identity {\n    _p: (),\n}\n\nimpl Identity {\n    /// Create a new [`Identity`] value\n    pub const fn new() -> Identity {\n        Identity { _p: () }\n    }\n}\n\n/// Decorates a [`Service`], transforming either the request or the response.\n///\n/// [`Service`]: https://docs.rs/tower-service/latest/tower_service/trait.Service.html\nimpl<S> Layer<S> for Identity {\n    type Service = S;\n\n    fn layer(&self, inner: S) -> Self::Service {\n        inner\n    }\n}\n\nimpl fmt::Debug for Identity {\n    fn fmt(&self, f: &mut fmt::Formatter<\'_>) -> fmt::Result {\n        f.debug_struct("Identity").finish()\n    }\n}\n',
            'tower-layer/src/layer_fn.rs': 'use super::Layer;\nuse core::fmt;\n\n/// Returns a new [`LayerFn`] that implements [`Layer`] by calling the\n/// given function.\n///\n/// The [`Layer::layer`] method takes a type implementing [`Service`] and\n/// returns a different type implementing [`Service`]. In many cases, this can\n/// be implemented by a function or a closure. The [`LayerFn`] helper allows\n/// writing simple [`Layer`] implementations without needing the boilerplate of\n/// a new struct implementing [`Layer`].\n///\n/// # Example\n/// ```rust\n/// # use tower::Service;\n/// # use core::task::{Poll, Context};\n/// # use tower_layer::{Layer, layer_fn};\n/// # use core::fmt;\n/// # use core::convert::Infallible;\n/// #\n/// // A middleware that logs requests before forwarding them to another service\n/// pub struct LogService<S> {\n///     target: &\'static str,\n///     service: S,\n/// }\n///\n/// impl<S, Request> Service<Request> for LogService<S>\n/// where\n///     S: Service<Request>,\n///     Request: fmt::Debug,\n/// {\n///     type Response = S::Response;\n///     type Error = S::Error;\n///     type Future = S::Future;\n///\n///     fn poll_ready(&mut self, cx: &mut Context<\'_>) -> Poll<Result<(), Self::Error>> {\n///         self.service.poll_ready(cx)\n///     }\n///\n///     fn call(&mut self, request: Request) -> Self::Future {\n///         // Log the request\n///         println!("request = {:?}, target = {:?}", request, self.target);\n///\n///         self.service.call(request)\n///     }\n/// }\n///\n/// // A `Layer` that wraps services in `LogService`\n/// let log_layer = layer_fn(|service| {\n///     LogService {\n///         service,\n///         target: "tower-docs",\n///     }\n/// });\n///\n/// // An example service. This one uppercases strings\n/// let uppercase_service = tower::service_fn(|request: String| async move {\n///     Ok::<_, Infallible>(request.to_uppercase())\n/// });\n///\n/// // Wrap our service in a `LogService` so requests are logged.\n/// let wrapped_service = log_layer.layer(uppercase_service);\n/// ```\n///\n/// [`Service`]: https://docs.rs/tower-service/latest/tower_service/trait.Service.html\n/// [`Layer::layer`]: crate::Layer::layer\npub fn layer_fn<T>(f: T) -> LayerFn<T> {\n    LayerFn { f }\n}\n\n/// A `Layer` implemented by a closure. See the docs for [`layer_fn`] for more details.\n#[derive(Clone, Copy)]\npub struct LayerFn<F> {\n    f: F,\n}\n\nimpl<F, S, Out> Layer<S> for LayerFn<F>\nwhere\n    F: Fn(S) -> Out,\n{\n    type Service = Out;\n\n    fn layer(&self, inner: S) -> Self::Service {\n        (self.f)(inner)\n    }\n}\n\nimpl<F> fmt::Debug for LayerFn<F> {\n    fn fmt(&self, f: &mut fmt::Formatter<\'_>) -> fmt::Result {\n        f.debug_struct("LayerFn")\n            .field("f", &format_args!("{}", core::any::type_name::<F>()))\n            .finish()\n    }\n}\n\n#[cfg(test)]\nmod tests {\n    use super::*;\n    use alloc::{format, string::ToString};\n\n    #[allow(dead_code)]\n    #[test]\n    fn layer_fn_has_useful_debug_impl() {\n        struct WrappedService<S> {\n            inner: S,\n        }\n        let layer = layer_fn(|svc| WrappedService { inner: svc });\n        let _svc = layer.layer("foo");\n\n        assert_eq!(\n            "LayerFn { f: tower_layer::layer_fn::tests::layer_fn_has_useful_debug_impl::{{closure}} }".to_string(),\n            format!("{layer:?}"),\n        );\n    }\n}\n',
            'tower-layer/src/stack.rs': 'use super::Layer;\nuse core::fmt;\n\n/// Two middlewares chained together.\n#[derive(Clone)]\npub struct Stack<Inner, Outer> {\n    inner: Inner,\n    outer: Outer,\n}\n\nimpl<Inner, Outer> Stack<Inner, Outer> {\n    /// Create a new `Stack`.\n    pub const fn new(inner: Inner, outer: Outer) -> Self {\n        Stack { inner, outer }\n    }\n}\n\nimpl<S, Inner, Outer> Layer<S> for Stack<Inner, Outer>\nwhere\n    Inner: Layer<S>,\n    Outer: Layer<Inner::Service>,\n{\n    type Service = Outer::Service;\n\n    fn layer(&self, service: S) -> Self::Service {\n        let inner = self.inner.layer(service);\n\n        self.outer.layer(inner)\n    }\n}\n\nimpl<Inner, Outer> fmt::Debug for Stack<Inner, Outer>\nwhere\n    Inner: fmt::Debug,\n    Outer: fmt::Debug,\n{\n    fn fmt(&self, f: &mut fmt::Formatter<\'_>) -> fmt::Result {\n        // The generated output of nested `Stack`s is very noisy and makes\n        // it harder to understand what is in a `ServiceBuilder`.\n        //\n        // Instead, this output is designed assuming that a `Stack` is\n        // usually quite nested, and inside a `ServiceBuilder`. Therefore,\n        // this skips using `f.debug_struct()`, since each one would force\n        // a new layer of indentation.\n        //\n        // - In compact mode, a nested stack ends up just looking like a flat\n        //   list of layers.\n        //\n        // - In pretty mode, while a newline is inserted between each layer,\n        //   the `DebugStruct` used in the `ServiceBuilder` will inject padding\n        //   to that each line is at the same indentation level.\n        //\n        // Also, the order of [outer, inner] is important, since it reflects\n        // the order that the layers were added to the stack.\n        if f.alternate() {\n            // pretty\n            write!(f, "{:#?},\\n{:#?}", self.outer, self.inner)\n        } else {\n            write!(f, "{:?}, {:?}", self.outer, self.inner)\n        }\n    }\n}\n',
        }
