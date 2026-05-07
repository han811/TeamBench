"""
Parameterized generator for GH723_zap_1411.

Source PR:    https://github.com/uber-go/zap/pull/1411
Source Issue: N/A

Seed varies: renames 'above' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH723_zap_1411'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH723_zap_1411'
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
            task_id='GH723_zap_1411',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'uber-go/zap',
                "pr_number": 1411,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/uber-go/zap/pull/1411",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'exp/zapslog/handler.go': '// Copyright (c) 2023 Uber Technologies, Inc.\n//\n// Permission is hereby granted, free of charge, to any person obtaining a copy\n// of this software and associated documentation files (the "Software"), to deal\n// in the Software without restriction, including without limitation the rights\n// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n// copies of the Software, and to permit persons to whom the Software is\n// furnished to do so, subject to the following conditions:\n//\n// The above copyright notice and this permission notice shall be included in\n// all copies or substantial portions of the Software.\n//\n// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN\n// THE SOFTWARE.\n\n//go:build go1.21\n\npackage zapslog\n\nimport (\n\t"context"\n\t"log/slog"\n\t"runtime"\n\n\t"go.uber.org/zap"\n\t"go.uber.org/zap/internal/stacktrace"\n\t"go.uber.org/zap/zapcore"\n)\n\n// Handler implements the slog.Handler by writing to a zap Core.\ntype Handler struct {\n\tcore       zapcore.Core\n\tname       string // logger name\n\taddCaller  bool\n\taddStackAt slog.Level\n\tcallerSkip int\n\n\t// List of unapplied groups.\n\t//\n\t// These are applied only if we encounter a real field\n\t// to avoid creating empty namespaces -- which is disallowed by slog\'s\n\t// usage contract.\n\tgroups []string\n}\n\n// NewHandler builds a [Handler] that writes to the supplied [zapcore.Core]\n// with options.\nfunc NewHandler(core zapcore.Core, opts ...Option) *Handler {\n\th := &Handler{\n\t\tcore:       core,\n\t\taddStackAt: slog.LevelError,\n\t}\n\tfor _, v := range opts {\n\t\tv.apply(h)\n\t}\n\treturn h\n}\n\nvar _ slog.Handler = (*Handler)(nil)\n\n// groupObject holds all the Attrs saved in a slog.GroupValue.\ntype groupObject []slog.Attr\n\nfunc (gs groupObject) MarshalLogObject(enc zapcore.ObjectEncoder) error {\n\tfor _, attr := range gs {\n\t\tconvertAttrToField(attr).AddTo(enc)\n\t}\n\treturn nil\n}\n\nfunc convertAttrToField(attr slog.Attr) zapcore.Field {\n\tif attr.Equal(slog.Attr{}) {\n\t\t// Ignore empty attrs.\n\t\treturn zap.Skip()\n\t}\n\n\tswitch attr.Value.Kind() {\n\tcase slog.KindBool:\n\t\treturn zap.Bool(attr.Key, attr.Value.Bool())\n\tcase slog.KindDuration:\n\t\treturn zap.Duration(attr.Key, attr.Value.Duration())\n\tcase slog.KindFloat64:\n\t\treturn zap.Float64(attr.Key, attr.Value.Float64())\n\tcase slog.KindInt64:\n\t\treturn zap.Int64(attr.Key, attr.Value.Int64())\n\tcase slog.KindString:\n\t\treturn zap.String(attr.Key, attr.Value.String())\n\tcase slog.KindTime:\n\t\treturn zap.Time(attr.Key, attr.Value.Time())\n\tcase slog.KindUint64:\n\t\treturn zap.Uint64(attr.Key, attr.Value.Uint64())\n\tcase slog.KindGroup:\n\t\tif attr.Key == "" {\n\t\t\t// Inlines recursively.\n\t\t\treturn zap.Inline(groupObject(attr.Value.Group()))\n\t\t}\n\t\treturn zap.Object(attr.Key, groupObject(attr.Value.Group()))\n\tcase slog.KindLogValuer:\n\t\treturn convertAttrToField(slog.Attr{\n\t\t\tKey: attr.Key,\n\t\t\t// TODO: resolve the value in a lazy way.\n\t\t\t// This probably needs a new Zap field type\n\t\t\t// that can be resolved lazily.\n\t\t\tValue: attr.Value.Resolve(),\n\t\t})\n\tdefault:\n\t\treturn zap.Any(attr.Key, attr.Value.Any())\n\t}\n}\n\n// convertSlogLevel maps slog Levels to zap Levels.\n// Note that there is some room between slog levels while zap levels are continuous, so we can\'t 1:1 map them.\n// See also https://go.googlesource.com/proposal/+/master/design/56345-structured-logging.md?pli=1#levels\nfunc convertSlogLevel(l slog.Level) zapcore.Level {\n\tswitch {\n\tcase l >= slog.LevelError:\n\t\treturn zapcore.ErrorLevel\n\tcase l >= slog.LevelWarn:\n\t\treturn zapcore.WarnLevel\n\tcase l >= slog.LevelInfo:\n\t\treturn zapcore.InfoLevel\n\tdefault:\n\t\treturn zapcore.DebugLevel\n\t}\n}\n\n// Enabled reports whether the handler handles records at the given level.\nfunc (h *Handler) Enabled(ctx context.Context, level slog.Level) bool {\n\treturn h.core.Enabled(convertSlogLevel(level))\n}\n\n// Handle handles the Record.\nfunc (h *Handler) Handle(ctx context.Context, record slog.Record) error {\n\tent := zapcore.Entry{\n\t\tLevel:      convertSlogLevel(record.Level),\n\t\tTime:       record.Time,\n\t\tMessage:    record.Message,\n\t\tLoggerName: h.name,\n\t}\n\tce := h.core.Check(ent, nil)\n\tif ce == nil {\n\t\treturn nil\n\t}\n\n\tif h.addCaller && record.PC != 0 {\n\t\tframe, _ := runtime.CallersFrames([]uintptr{record.PC}).Next()\n\t\tif frame.PC != 0 {\n\t\t\tce.Caller = zapcore.EntryCaller{\n\t\t\t\tDefined:  true,\n\t\t\t\tPC:       frame.PC,\n\t\t\t\tFile:     frame.File,\n\t\t\t\tLine:     frame.Line,\n\t\t\t\tFunction: frame.Function,\n\t\t\t}\n\t\t}\n\t}\n\n\tif record.Level >= h.addStackAt {\n\t\t// Skipping 3:\n\t\t// zapslog/handler log/slog.(*Logger).log\n\t\t// slog/logger log/slog.(*Logger).log\n\t\t// slog/logger log/slog.(*Logger).<level>\n\t\tce.Stack = stacktrace.Take(3 + h.callerSkip)\n\t}\n\n\tfields := make([]zapcore.Field, 0, record.NumAttrs()+len(h.groups))\n\n\tvar addedNamespace bool\n\trecord.Attrs(func(attr slog.Attr) bool {\n\t\tf := convertAttrToField(attr)\n\t\tif !addedNamespace && len(h.groups) > 0 && f != zap.Skip() {\n\t\t\t// Namespaces are added only if at least one field is present\n\t\t\t// to avoid creating empty groups.\n\t\t\tfields = h.appendGroups(fields)\n\t\t\taddedNamespace = true\n\t\t}\n\t\tfields = append(fields, f)\n\t\treturn true\n\t})\n\n\tce.Write(fields...)\n\treturn nil\n}\n\nfunc (h *Handler) appendGroups(fields []zapcore.Field) []zapcore.Field {\n\tfor _, g := range h.groups {\n\t\tfields = append(fields, zap.Namespace(g))\n\t}\n\treturn fields\n}\n\n// WithAttrs returns a new Handler whose attributes consist of\n// both the receiver\'s attributes and the arguments.\nfunc (h *Handler) WithAttrs(attrs []slog.Attr) slog.Handler {\n\tfields := make([]zapcore.Field, 0, len(attrs)+len(h.groups))\n\tvar addedNamespace bool\n\tfor _, attr := range attrs {\n\t\tf := convertAttrToField(attr)\n\t\tif !addedNamespace && len(h.groups) > 0 && f != zap.Skip() {\n\t\t\t// Namespaces are added only if at least one field is present\n\t\t\t// to avoid creating empty groups.\n\t\t\tfields = h.appendGroups(fields)\n\t\t\taddedNamespace = true\n\t\t}\n\t\tfields = append(fields, f)\n\t}\n\n\tcloned := *h\n\tcloned.core = h.core.With(fields)\n\tif addedNamespace {\n\t\t// These groups have been applied so we can clear them.\n\t\tcloned.groups = nil\n\t}\n\treturn &cloned\n}\n\n// WithGroup returns a new Handler with the given group appended to\n// the receiver\'s existing groups.\nfunc (h *Handler) WithGroup(group string) slog.Handler {\n\tnewGroups := make([]string, len(h.groups)+1)\n\tcopy(newGroups, h.groups)\n\tnewGroups[len(h.groups)] = group\n\n\tcloned := *h\n\tcloned.groups = newGroups\n\treturn &cloned\n}\n',
            'exp/zapslog/options.go': '// Copyright (c) 2023 Uber Technologies, Inc.\n//\n// Permission is hereby granted, free of charge, to any person obtaining a copy\n// of this software and associated documentation files (the "Software"), to deal\n// in the Software without restriction, including without limitation the rights\n// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n// copies of the Software, and to permit persons to whom the Software is\n// furnished to do so, subject to the following conditions:\n//\n// The above copyright notice and this permission notice shall be included in\n// all copies or substantial portions of the Software.\n//\n// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN\n// THE SOFTWARE.\n\n//go:build go1.21\n\npackage zapslog\n\nimport "log/slog"\n\n// An Option configures a slog Handler.\ntype Option interface {\n\tapply(*Handler)\n}\n\n// optionFunc wraps a func so it satisfies the Option interface.\ntype optionFunc func(*Handler)\n\nfunc (f optionFunc) apply(handler *Handler) {\n\tf(handler)\n}\n\n// WithName configures the Logger to annotate each message with the logger name.\nfunc WithName(name string) Option {\n\treturn optionFunc(func(h *Handler) {\n\t\th.name = name\n\t})\n}\n\n// WithCaller configures the Logger to include the filename and line number\n// of the caller in log messages--if available.\nfunc WithCaller(enabled bool) Option {\n\treturn optionFunc(func(handler *Handler) {\n\t\thandler.addCaller = enabled\n\t})\n}\n\n// WithCallerSkip increases the number of callers skipped by caller annotation\n// (as enabled by the [WithCaller] option).\n//\n// When building wrappers around the Logger,\n// supplying this Option prevents Zap from always reporting\n// the wrapper code as the caller.\nfunc WithCallerSkip(skip int) Option {\n\treturn optionFunc(func(log *Handler) {\n\t\tlog.callerSkip += skip\n\t})\n}\n\n// AddStacktraceAt configures the Logger to record a stack trace\n// for all messages at or above a given level.\nfunc AddStacktraceAt(lvl slog.Level) Option {\n\treturn optionFunc(func(log *Handler) {\n\t\tlog.addStackAt = lvl\n\t})\n}\n',
        }
