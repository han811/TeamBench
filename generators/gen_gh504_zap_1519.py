"""
Parameterized generator for GH504_zap_1519.

Source PR:    https://github.com/uber-go/zap/pull/1519
Source Issue: N/A

Seed varies: renames 'above' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH504_zap_1519'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH504_zap_1519'
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
                files[fpath] = files[fpath].replace('above', 'above' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH504_zap_1519',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'uber-go/zap',
                "pr_number": 1519,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/uber-go/zap/pull/1519",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'zapcore/lazy_with.go': '// Copyright (c) 2023 Uber Technologies, Inc.\n//\n// Permission is hereby granted, free of charge, to any person obtaining a copy\n// of this software and associated documentation files (the "Software"), to deal\n// in the Software without restriction, including without limitation the rights\n// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n// copies of the Software, and to permit persons to whom the Software is\n// furnished to do so, subject to the following conditions:\n//\n// The above copyright notice and this permission notice shall be included in\n// all copies or substantial portions of the Software.\n//\n// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN\n// THE SOFTWARE.\n\npackage zapcore\n\nimport "sync"\n\ntype lazyWithCore struct {\n\tcore   Core\n\tsync.Once\n\tfields []Field\n}\n\n// NewLazyWith wraps a Core with a "lazy" Core that will only encode fields if\n// the logger is written to (or is further chained in a lon-lazy manner).\nfunc NewLazyWith(core Core, fields []Field) Core {\n\treturn &lazyWithCore{\n\t\tcore:   core,\n\t\tfields: fields,\n\t}\n}\n\nfunc (d *lazyWithCore) initOnce() {\n\td.Once.Do(func() {\n\t\td.core = d.core.With(d.fields)\n\t})\n}\n\nfunc (d *lazyWithCore) With(fields []Field) Core {\n\td.initOnce()\n\treturn d.core.With(fields)\n}\n\nfunc (d *lazyWithCore) Check(e Entry, ce *CheckedEntry) *CheckedEntry {\n\td.initOnce()\n\treturn d.core.Check(e, ce)\n}\n\nfunc (d *lazyWithCore) Enabled(level Level) bool {\n\td.initOnce()\n\treturn d.core.Enabled(level)\n}\n\nfunc (d *lazyWithCore) Write(e Entry, fields []Field) error {\n\td.initOnce()\n\treturn d.core.Write(e, fields)\n}\n\nfunc (d *lazyWithCore) Sync() error {\n\td.initOnce()\n\treturn d.core.Sync()\n}\n',
            'zapcore/lazy_with_test.go': '// Copyright (c) 2023 Uber Technologies, Inc.\n//\n// Permission is hereby granted, free of charge, to any person obtaining a copy\n// of this software and associated documentation files (the "Software"), to deal\n// in the Software without restriction, including without limitation the rights\n// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n// copies of the Software, and to permit persons to whom the Software is\n// furnished to do so, subject to the following conditions:\n//\n// The above copyright notice and this permission notice shall be included in\n// all copies or substantial portions of the Software.\n//\n// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN\n// THE SOFTWARE.\n\npackage zapcore_test\n\nimport (\n\t"sync"\n\t"sync/atomic"\n\t"testing"\n\n\t"github.com/stretchr/testify/assert"\n\t"go.uber.org/zap/zapcore"\n\t"go.uber.org/zap/zaptest/observer"\n)\n\ntype proxyCore struct {\n\tzapcore.Core\n\n\twithCount  atomic.Int64\n\tcheckCount atomic.Int64\n}\n\nfunc newProxyCore(inner zapcore.Core) *proxyCore {\n\treturn &proxyCore{Core: inner}\n}\n\nfunc (p *proxyCore) With(fields []zapcore.Field) zapcore.Core {\n\tp.withCount.Add(1)\n\treturn p.Core.With(fields)\n}\n\nfunc (p *proxyCore) Check(e zapcore.Entry, ce *zapcore.CheckedEntry) *zapcore.CheckedEntry {\n\tp.checkCount.Add(1)\n\treturn p.Core.Check(e, ce)\n}\n\nfunc withLazyCore(f func(zapcore.Core, *proxyCore, *observer.ObservedLogs), initialFields ...zapcore.Field) {\n\tinfoLogger, infoLogs := observer.New(zapcore.InfoLevel)\n\tproxyCore := newProxyCore(infoLogger)\n\tlazyCore := zapcore.NewLazyWith(proxyCore, initialFields)\n\tf(lazyCore, proxyCore, infoLogs)\n}\n\nfunc TestLazyCore(t *testing.T) {\n\ttests := []struct {\n\t\tname          string\n\t\tentries       []zapcore.Entry\n\t\tinitialFields []zapcore.Field\n\t\twithChains    [][]zapcore.Field\n\t\twantLogs      []observer.LoggedEntry\n\t}{\n\t\t{\n\t\t\tname:     "no logging, no with, inner core with never called, inner core check never called",\n\t\t\twantLogs: []observer.LoggedEntry{},\n\t\t},\n\t\t{\n\t\t\tname: "2 logs, 1 dropped, no with, inner core with called once, inner core check never called",\n\t\t\tentries: []zapcore.Entry{\n\t\t\t\t{Level: zapcore.DebugLevel, Message: "log-at-debug"},\n\t\t\t\t{Level: zapcore.WarnLevel, Message: "log-at-warn"},\n\t\t\t},\n\t\t\twantLogs: []observer.LoggedEntry{\n\t\t\t\t{\n\t\t\t\t\tEntry: zapcore.Entry{\n\t\t\t\t\t\tLevel:   zapcore.WarnLevel,\n\t\t\t\t\t\tMessage: "log-at-warn",\n\t\t\t\t\t},\n\t\t\t\t\tContext: []zapcore.Field{},\n\t\t\t\t},\n\t\t\t},\n\t\t},\n\t\t{\n\t\t\tname: "no logs, 2-chained with, inner core with called once, inner core check never called",\n\t\t\twithChains: [][]zapcore.Field{\n\t\t\t\t{makeInt64Field("a", 11), makeInt64Field("b", 22)},\n\t\t\t\t{makeInt64Field("c", 33), makeInt64Field("d", 44)},\n\t\t\t},\n\t\t\twantLogs: []observer.LoggedEntry{},\n\t\t},\n\t\t{\n\t\t\tname: "2 logs, 1 dropped, 2-chained with, inner core with called once, inner core check never called",\n\t\t\tentries: []zapcore.Entry{\n\t\t\t\t{Level: zapcore.DebugLevel, Message: "log-at-debug"},\n\t\t\t\t{Level: zapcore.WarnLevel, Message: "log-at-warn"},\n\t\t\t},\n\t\t\twithChains: [][]zapcore.Field{\n\t\t\t\t{makeInt64Field("a", 11), makeInt64Field("b", 22)},\n\t\t\t\t{makeInt64Field("c", 33), makeInt64Field("d", 44)},\n\t\t\t},\n\t\t\twantLogs: []observer.LoggedEntry{\n\t\t\t\t{\n\t\t\t\t\tEntry: zapcore.Entry{\n\t\t\t\t\t\tLevel:   zapcore.WarnLevel,\n\t\t\t\t\t\tMessage: "log-at-warn",\n\t\t\t\t\t},\n\t\t\t\t\tContext: []zapcore.Field{\n\t\t\t\t\t\tmakeInt64Field("a", 11),\n\t\t\t\t\t\tmakeInt64Field("b", 22),\n\t\t\t\t\t\tmakeInt64Field("c", 33),\n\t\t\t\t\t\tmakeInt64Field("d", 44),\n\t\t\t\t\t},\n\t\t\t\t},\n\t\t\t},\n\t\t},\n\t}\n\tfor _, tt := range tests {\n\t\tt.Run(tt.name, func(t *testing.T) {\n\t\t\twithLazyCore(func(lazy zapcore.Core, proxy *proxyCore, logs *observer.ObservedLogs) {\n\t\t\t\tcheckCounts := func(withCount int64, msg string) {\n\t\t\t\t\tassert.Equal(t, withCount, proxy.withCount.Load(), msg)\n\t\t\t\t}\n\t\t\t\tcheckCounts(0, "expected no with calls because the logger is not used yet")\n\n\t\t\t\tfor _, chain := range tt.withChains {\n\t\t\t\t\tlazy = lazy.With(chain)\n\t\t\t\t}\n\t\t\t\tif len(tt.withChains) > 0 {\n\t\t\t\t\tcheckCounts(1, "expected with calls because the logger was with-chained")\n\t\t\t\t} else {\n\t\t\t\t\tcheckCounts(0, "expected no with calls because the logger is not used yet")\n\t\t\t\t}\n\n\t\t\t\tfor _, ent := range tt.entries {\n\t\t\t\t\tif ce := lazy.Check(ent, nil); ce != nil {\n\t\t\t\t\t\tce.Write()\n\t\t\t\t\t}\n\t\t\t\t}\n\t\t\t\tif len(tt.entries) > 0 || len(tt.withChains) > 0 {\n\t\t\t\t\tcheckCounts(1, "expected with calls because the logger had entries or with chains")\n\t\t\t\t} else {\n\t\t\t\t\tcheckCounts(0, "expected no with calls because the logger is not used yet")\n\t\t\t\t}\n\t\t\t\tassert.Zero(t, proxy.checkCount.Load(), "expected no check calls because the inner core is copied")\n\t\t\t\tassert.Equal(t, tt.wantLogs, logs.AllUntimed())\n\t\t\t}, tt.initialFields...)\n\t\t})\n\t}\n}\n\n// TestLazyCoreRace tests concurrent access to lazyWithCore methods\n// This is a regression test for issue #1426\nfunc TestLazyCoreRace(t *testing.T) {\n\tcore, _ := observer.New(zapcore.InfoLevel)\n\tlazyCore := zapcore.NewLazyWith(core, []zapcore.Field{\n\t\tmakeInt64Field("lazy", 42),\n\t})\n\n\tvar wg sync.WaitGroup\n\tconst numGoroutines = 50\n\n\t// Test concurrent access to Enabled() method which was the source of the race\n\tfor i := 0; i < numGoroutines; i++ {\n\t\twg.Add(1)\n\t\tgo func() {\n\t\t\tdefer wg.Done()\n\n\t\t\t// These operations should not race\n\t\t\t_ = lazyCore.Enabled(zapcore.InfoLevel)\n\t\t\t_ = lazyCore.Enabled(zapcore.DebugLevel)\n\n\t\t\t// Also test other methods for good measure\n\t\t\tif ce := lazyCore.Check(zapcore.Entry{Level: zapcore.InfoLevel, Message: "test"}, nil); ce != nil {\n\t\t\t\t_ = lazyCore.Write(zapcore.Entry{Level: zapcore.InfoLevel, Message: "test"}, nil)\n\t\t\t}\n\t\t}()\n\t}\n\n\twg.Wait()\n}\n',
        }
