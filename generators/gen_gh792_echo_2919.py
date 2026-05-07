"""
Parameterized generator for GH792_echo_2919.

Source PR:    https://github.com/labstack/echo/pull/2919
Source Issue: N/A

Seed varies: renames 'casbin' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH792_echo_2919'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH792_echo_2919'
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
                files[fpath] = files[fpath].replace('casbin', 'casbin' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH792_echo_2919',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'labstack/echo',
                "pr_number": 2919,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/labstack/echo/pull/2919",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'README.md': '[![Sourcegraph](https://sourcegraph.com/github.com/labstack/echo/-/badge.svg?style=flat-square)](https://sourcegraph.com/github.com/labstack/echo?badge)\n[![GoDoc](http://img.shields.io/badge/go-documentation-blue.svg?style=flat-square)](https://pkg.go.dev/github.com/labstack/echo/v4)\n[![Go Report Card](https://goreportcard.com/badge/github.com/labstack/echo?style=flat-square)](https://goreportcard.com/report/github.com/labstack/echo)\n[![GitHub Workflow Status (with event)](https://img.shields.io/github/actions/workflow/status/labstack/echo/echo.yml?style=flat-square)](https://github.com/labstack/echo/actions)\n[![Codecov](https://img.shields.io/codecov/c/github/labstack/echo.svg?style=flat-square)](https://codecov.io/gh/labstack/echo)\n[![Forum](https://img.shields.io/badge/community-forum-00afd1.svg?style=flat-square)](https://github.com/labstack/echo/discussions)\n[![Twitter](https://img.shields.io/badge/twitter-@labstack-55acee.svg?style=flat-square)](https://twitter.com/labstack)\n[![License](http://img.shields.io/badge/license-mit-blue.svg?style=flat-square)](https://raw.githubusercontent.com/labstack/echo/master/LICENSE)\n\n## Echo\n\nHigh performance, extensible, minimalist Go web framework.\n\n* [Official website](https://echo.labstack.com)\n* [Quick start](https://echo.labstack.com/docs/quick-start)\n* [Middlewares](https://echo.labstack.com/docs/category/middleware)\n\nHelp and questions: [Github Discussions](https://github.com/labstack/echo/discussions)\n\n### Feature Overview\n\n- Optimized HTTP router which smartly prioritize routes\n- Build robust and scalable RESTful APIs\n- Group APIs\n- Extensible middleware framework\n- Define middleware at root, group or route level\n- Data binding for JSON, XML and form payload\n- Handy functions to send variety of HTTP responses\n- Centralized HTTP error handling\n- Template rendering with any template engine\n- Define your format for the logger\n- Highly customizable\n- Automatic TLS via Let’s Encrypt\n- HTTP/2 support\n\n## Sponsors\n\n<div>\n  <a href="https://encore.dev" style="display: inline-flex; align-items: center; gap: 10px">\n    <img src="https://user-images.githubusercontent.com/78424526/214602214-52e0483a-b5fc-4d4c-b03e-0b7b23e012df.svg" height="28px" alt="encore icon"></img>\n  <b>Encore – the platform for building Go-based cloud backends</b>\n    </a>\n</div>\n<br/>\n\nClick [here](https://github.com/sponsors/labstack) for more information on sponsorship.\n\n## [Guide](https://echo.labstack.com/guide)\n\n### Supported Echo versions\n\n- Latest major version of Echo is `v5` as of 2026-01-18.\n  - Until 2026-03-31, any critical issues requiring breaking API changes will be addressed, even if this violates\n    semantic versioning.\n  - See [API_CHANGES_V5.md](./API_CHANGES_V5.md) for public API changes between `v4` and `v5`, notes on upgrading.\n  - If you are using Echo in a production environment, it is recommended to wait until after 2026-03-31 before\n    upgrading.\n- Echo `v4` is supported with **security*** updates and **bug** fixes until **2026-12-31**\n\n### Installation\n\n```sh\n// go get github.com/labstack/echo/{version}\ngo get github.com/labstack/echo/v5\n```\n\nLatest version of Echo supports last four Go major [releases](https://go.dev/doc/devel/release) and might work with\nolder versions.\n\n### Example\n\n```go\npackage main\n\nimport (\n  "github.com/labstack/echo/v5"\n  "github.com/labstack/echo/v5/middleware"\n  "log/slog"\n  "net/http"\n)\n\nfunc main() {\n  // Echo instance\n  e := echo.New()\n\n  // Middleware\n  e.Use(middleware.RequestLogger()) // use the RequestLogger middleware with slog logger\n  e.Use(middleware.Recover())       // recover panics as errors for proper error handling\n\n  // Routes\n  e.GET("/", hello)\n\n  // Start server\n  if err := e.Start(":8080"); err != nil {\n    slog.Error("failed to start server", "error", err)\n  }\n}\n\n// Handler\nfunc hello(c *echo.Context) error {\n  return c.String(http.StatusOK, "Hello, World!")\n}\n```\n\n# Official middleware repositories\n\nFollowing list of middleware is maintained by Echo team.\n\n| Repository                                                                               | Description                                                                                                                                                                                                                                                                                                                           |\n|------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|\n| [github.com/labstack/echo-jwt](https://github.com/labstack/echo-jwt)                     | [JWT](https://github.com/golang-jwt/jwt) middleware                                                                                                                                                                                                                                                                                   | \n| [github.com/labstack/echo-contrib](https://github.com/labstack/echo-contrib)             | [casbin](https://github.com/casbin/casbin), [gorilla/sessions](https://github.com/gorilla/sessions), [jaegertracing](https://github.com/uber/jaeger-client-go), [prometheus](https://github.com/prometheus/client_golang/), [pprof](https://pkg.go.dev/net/http/pprof), [zipkin](https://github.com/openzipkin/zipkin-go) middlewares | \n| [github.com/labstack/echo-opentelemetry](https://github.com/labstack/echo-opentelemetry) | [OpenTelemetry](https://opentelemetry.io/) middleware for tracing and metrics                                                                                                                                                                                                                                                         |\n\n# Third-party middleware repositories\n\nBe careful when adding 3rd party middleware. Echo teams does not have time or manpower to guarantee safety and quality\nof middlewares in this list.\n\n| Repository                                                                                           | Description                                                                                                                                                                                              |\n|------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|\n| [oapi-codegen/oapi-codegen](https://github.com/oapi-codegen/oapi-codegen)                            | Automatically generate RESTful API documentation with [OpenAPI](https://swagger.io/specification/) Client and Server Code Generator                                                                      |\n| [github.com/swaggo/echo-swagger](https://github.com/swaggo/echo-swagger)                             | Automatically generate RESTful API documentation with [Swagger](https://swagger.io/) 2.0.                                                                                                                |\n| [github.com/ziflex/lecho](https://github.com/ziflex/lecho)                                           | [Zerolog](https://github.com/rs/zerolog) logging library wrapper for Echo logger interface.                                                                                                              |\n| [github.com/brpaz/echozap](https://github.com/brpaz/echozap)                                         | Uber´s [Zap](https://github.com/uber-go/zap) logging library wrapper for Echo logger interface.                                                                                                          |\n| [github.com/samber/slog-echo](https://github.com/samber/slog-echo)                                   | Go [slog](https://pkg.go.dev/golang.org/x/exp/slog) logging library wrapper for Echo logger interface.                                                                                                   |\n| [github.com/darkweak/souin/plugins/echo](https://github.com/darkweak/souin/tree/master/plugins/echo) | HTTP cache system based on [Souin](https://github.com/darkweak/souin) to automatically get your endpoints cached. It supports some distributed and non-distributed storage systems depending your needs. |\n| [github.com/mikestefanello/pagoda](https://github.com/mikestefanello/pagoda)                         | Rapid, easy full-stack web development starter kit built with Echo.                                                                                                                                      |\n| [github.com/go-woo/protoc-gen-echo](https://github.com/go-woo/protoc-gen-echo)                       | ProtoBuf generate Echo server side code                                                                                                                                                                  |\n\nPlease send a PR to add your own library here.\n\n## Contribute\n\n**Use issues for everything**\n\n- For a small change, just send a PR.\n- For bigger changes open an issue for discussion before sending a PR.\n- PR should have:\n  - Test case\n  - Documentation\n  - Example (If it makes sense)\n- You can also contribute by:\n  - Reporting issues\n  - Suggesting new features or enhancements\n  - Improve/fix documentation\n\n## Credits\n\n- [Vishal Rana](https://github.com/vishr) (Author)\n- [Nitin Rana](https://github.com/nr17) (Consultant)\n- [Roland Lammel](https://github.com/lammel) (Maintainer)\n- [Martti T.](https://github.com/aldas) (Maintainer)\n- [Pablo Andres Fuente](https://github.com/pafuent) (Maintainer)\n- [Contributors](https://github.com/labstack/echo/graphs/contributors)\n\n## License\n\n[MIT](https://github.com/labstack/echo/blob/master/LICENSE)\n',
        }
