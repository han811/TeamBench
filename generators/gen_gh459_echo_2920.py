"""
Parameterized generator for GH459_echo_2920.

Source PR:    https://github.com/labstack/echo/pull/2920
Source Issue: N/A

Seed varies: renames 'actual' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH459_echo_2920'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH459_echo_2920'
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
                files[fpath] = files[fpath].replace('actual', 'actual' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH459_echo_2920',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'labstack/echo',
                "pr_number": 2920,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/labstack/echo/pull/2920",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'server.go': '// SPDX-License-Identifier: MIT\n// SPDX-FileCopyrightText: © 2015 LabStack LLC and Echo contributors\n\npackage echo\n\nimport (\n\tstdContext "context"\n\t"crypto/tls"\n\t"errors"\n\t"fmt"\n\t"io/fs"\n\t"log/slog"\n\t"net"\n\t"net/http"\n\t"os"\n\t"sync"\n\t"time"\n)\n\nconst (\n\tbanner = "Echo (v%s). High performance, minimalist Go web framework https://echo.labstack.com"\n)\n\n// StartConfig is for creating configured http.Server instance to start serve http(s) requests with given Echo instance\ntype StartConfig struct {\n\t// Address specifies the address where listener will start listening on to serve HTTP(s) requests\n\tAddress string\n\n\t// HideBanner instructs Start* method not to print banner when starting the Server.\n\tHideBanner bool\n\t// HidePort instructs Start* method not to print port when starting the Server.\n\tHidePort bool\n\n\t// CertFilesystem is filesystem is used to read `certFile` and `keyFile` when StartTLS method is called.\n\tCertFilesystem fs.FS\n\tTLSConfig      *tls.Config\n\n\t// ListenerNetwork is used configure on which Network listener will use.\n\tListenerNetwork string\n\t// ListenerAddrFunc will be called after listener is created and started to listen for connections. This is useful in\n\t// testing situations when server is started on random port `address = ":0"` in that case you can get actual port where\n\t// listener is listening on.\n\tListenerAddrFunc func(addr net.Addr)\n\n\t// GracefulTimeout is timeout value (defaults to 10sec) graceful shutdown will wait for server to handle ongoing requests\n\t// before shutting down the server.\n\tGracefulTimeout time.Duration\n\t// OnShutdownError is called when graceful shutdown results an error. for example when listeners are not shut down within\n\t// given timeout\n\tOnShutdownError func(err error)\n\n\t// BeforeServeFunc is callback that is called just before server starts to serve HTTP request.\n\t// Use this callback when you want to configure http.Server different timeouts/limits/etc\n\tBeforeServeFunc func(s *http.Server) error\n}\n\n// Start starts given Handler with HTTP(s) server.\nfunc (sc StartConfig) Start(ctx stdContext.Context, h http.Handler) error {\n\treturn sc.start(ctx, h)\n}\n\n// StartTLS starts given Handler with HTTPS server.\n// If `certFile` or `keyFile` is `string` the values are treated as file paths.\n// If `certFile` or `keyFile` is `[]byte` the values are treated as the certificate or key as-is.\nfunc (sc StartConfig) StartTLS(ctx stdContext.Context, h http.Handler, certFile, keyFile any) error {\n\tcertFs := sc.CertFilesystem\n\tif certFs == nil {\n\t\tcertFs = os.DirFS(".")\n\t}\n\tcert, err := filepathOrContent(certFile, certFs)\n\tif err != nil {\n\t\treturn err\n\t}\n\tkey, err := filepathOrContent(keyFile, certFs)\n\tif err != nil {\n\t\treturn err\n\t}\n\tcer, err := tls.X509KeyPair(cert, key)\n\tif err != nil {\n\t\treturn err\n\t}\n\tif sc.TLSConfig == nil {\n\t\tsc.TLSConfig = &tls.Config{\n\t\t\tMinVersion: tls.VersionTLS12,\n\t\t\tNextProtos: []string{"h2"},\n\t\t\t//NextProtos: []string{"http/1.1"}, // Disallow "h2", allow http\n\t\t}\n\t}\n\tsc.TLSConfig.Certificates = []tls.Certificate{cer}\n\treturn sc.start(ctx, h)\n}\n\n// start starts handler with HTTP(s) server.\nfunc (sc StartConfig) start(ctx stdContext.Context, h http.Handler) error {\n\tvar logger *slog.Logger\n\tif e, ok := h.(*Echo); ok {\n\t\tlogger = e.Logger\n\t} else {\n\t\tlogger = slog.New(slog.NewJSONHandler(os.Stdout, nil))\n\t}\n\n\tserver := http.Server{\n\t\tHandler:  h,\n\t\tErrorLog: slog.NewLogLogger(logger.Handler(), slog.LevelError),\n\t\t// defaults for GoSec rule G112 // https://github.com/securego/gosec\n\t\t// G112 (CWE-400): Potential Slowloris Attack because ReadHeaderTimeout is not configured in the http.Server\n\t\tReadTimeout:  30 * time.Second,\n\t\tWriteTimeout: 30 * time.Second,\n\t}\n\n\tlistenerNetwork := sc.ListenerNetwork\n\tif listenerNetwork == "" {\n\t\tlistenerNetwork = "tcp"\n\t}\n\tvar listener net.Listener\n\tvar err error\n\tif sc.TLSConfig != nil {\n\t\tlistener, err = tls.Listen(listenerNetwork, sc.Address, sc.TLSConfig)\n\t} else {\n\t\tlistener, err = net.Listen(listenerNetwork, sc.Address)\n\t}\n\tif err != nil {\n\t\treturn err\n\t}\n\tif sc.ListenerAddrFunc != nil {\n\t\tsc.ListenerAddrFunc(listener.Addr())\n\t}\n\n\tif sc.BeforeServeFunc != nil {\n\t\tif err := sc.BeforeServeFunc(&server); err != nil {\n\t\t\t_ = listener.Close()\n\t\t\treturn err\n\t\t}\n\t}\n\tif !sc.HideBanner {\n\t\tbannerText := fmt.Sprintf(banner, Version)\n\t\tlogger.Info(bannerText, "version", Version)\n\t}\n\tif !sc.HidePort {\n\t\tlogger.Info("http(s) server started", "address", listener.Addr().String())\n\t}\n\n\twg := sync.WaitGroup{}\n\tdefer wg.Wait() // wait for graceful shutdown goroutine to finish\n\n\tgCtx, cancel := stdContext.WithCancel(ctx) // end graceful goroutine when Serve returns early\n\tdefer cancel()\n\n\tif sc.GracefulTimeout >= 0 {\n\t\twg.Add(1)\n\t\tgo func() {\n\t\t\tdefer wg.Done()\n\t\t\tgracefulShutdown(gCtx, &sc, &server, logger)\n\t\t}()\n\t}\n\n\tif err := server.Serve(listener); err != nil && !errors.Is(err, http.ErrServerClosed) {\n\t\treturn err\n\t}\n\treturn nil\n}\n\nfunc filepathOrContent(fileOrContent any, certFilesystem fs.FS) (content []byte, err error) {\n\tswitch v := fileOrContent.(type) {\n\tcase string:\n\t\treturn fs.ReadFile(certFilesystem, v)\n\tcase []byte:\n\t\treturn v, nil\n\tdefault:\n\t\treturn nil, ErrInvalidCertOrKeyType\n\t}\n}\n\nfunc gracefulShutdown(shutdownCtx stdContext.Context, sc *StartConfig, server *http.Server, logger *slog.Logger) {\n\t<-shutdownCtx.Done() // wait until shutdown context is closed.\n\t// note: is server if closed by other means this method is still run but is good as no-op\n\n\ttimeout := sc.GracefulTimeout\n\tif timeout == 0 {\n\t\ttimeout = 10 * time.Second\n\t}\n\twaitShutdownCtx, cancel := stdContext.WithTimeout(stdContext.Background(), timeout)\n\tdefer cancel()\n\n\tif err := server.Shutdown(waitShutdownCtx); err != nil {\n\t\t// we end up here when listeners are not shut down within given timeout\n\t\tif sc.OnShutdownError != nil {\n\t\t\tsc.OnShutdownError(err)\n\t\t\treturn\n\t\t}\n\t\tlogger.Error("failed to shut down server within given timeout", "error", err)\n\t}\n}\n',
        }
