"""
Parameterized generator for GH621_gorm_7610.

Source PR:    https://github.com/go-gorm/gorm/pull/7610
Source Issue: https://github.com/go-gorm/gorm/issues/7609

Seed varies: renames 'appear' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH621_gorm_7610'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH621_gorm_7610'
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
                files[fpath] = files[fpath].replace('appear', 'appear' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH621_gorm_7610',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'go-gorm/gorm',
                "pr_number": 7610,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/go-gorm/gorm/pull/7610",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'logger/slog.go': '//go:build go1.21\n\npackage logger\n\nimport (\n\t"context"\n\t"errors"\n\t"fmt"\n\t"log/slog"\n\t"time"\n)\n\ntype slogLogger struct {\n\tLogger                    *slog.Logger\n\tLogLevel                  LogLevel\n\tSlowThreshold             time.Duration\n\tParameterized             bool\n\tColorful                  bool // Ignored in slog\n\tIgnoreRecordNotFoundError bool\n}\n\nfunc NewSlogLogger(logger *slog.Logger, config Config) Interface {\n\treturn &slogLogger{\n\t\tLogger:                    logger,\n\t\tLogLevel:                  config.LogLevel,\n\t\tSlowThreshold:             config.SlowThreshold,\n\t\tParameterized:             config.ParameterizedQueries,\n\t\tIgnoreRecordNotFoundError: config.IgnoreRecordNotFoundError,\n\t}\n}\n\nfunc (l *slogLogger) LogMode(level LogLevel) Interface {\n\tnewLogger := *l\n\tnewLogger.LogLevel = level\n\treturn &newLogger\n}\n\nfunc (l *slogLogger) Info(ctx context.Context, msg string, data ...interface{}) {\n\tif l.LogLevel >= Info {\n\t\tl.Logger.InfoContext(ctx, msg, slog.Any("data", data))\n\t}\n}\n\nfunc (l *slogLogger) Warn(ctx context.Context, msg string, data ...interface{}) {\n\tif l.LogLevel >= Warn {\n\t\tl.Logger.WarnContext(ctx, msg, slog.Any("data", data))\n\t}\n}\n\nfunc (l *slogLogger) Error(ctx context.Context, msg string, data ...interface{}) {\n\tif l.LogLevel >= Error {\n\t\tl.Logger.ErrorContext(ctx, msg, slog.Any("data", data))\n\t}\n}\n\nfunc (l *slogLogger) Trace(ctx context.Context, begin time.Time, fc func() (sql string, rowsAffected int64), err error) {\n\tif l.LogLevel <= Silent {\n\t\treturn\n\t}\n\n\telapsed := time.Since(begin)\n\tsql, rows := fc()\n\tfields := []slog.Attr{\n\t\tslog.String("duration", fmt.Sprintf("%.3fms", float64(elapsed.Nanoseconds())/1e6)),\n\t\tslog.String("sql", sql),\n\t}\n\n\tif rows != -1 {\n\t\tfields = append(fields, slog.Int64("rows", rows))\n\t}\n\n\tswitch {\n\tcase err != nil && (!l.IgnoreRecordNotFoundError || !errors.Is(err, ErrRecordNotFound)):\n\t\tfields = append(fields, slog.String("error", err.Error()))\n\t\tl.Logger.ErrorContext(ctx, "SQL executed", slog.Attr{\n\t\t\tKey:   "trace",\n\t\t\tValue: slog.GroupValue(fields...),\n\t\t})\n\n\tcase l.SlowThreshold != 0 && elapsed > l.SlowThreshold:\n\t\tl.Logger.WarnContext(ctx, "SQL executed", slog.Attr{\n\t\t\tKey:   "trace",\n\t\t\tValue: slog.GroupValue(fields...),\n\t\t})\n\n\tcase l.LogLevel >= Info:\n\t\tl.Logger.InfoContext(ctx, "SQL executed", slog.Attr{\n\t\t\tKey:   "trace",\n\t\t\tValue: slog.GroupValue(fields...),\n\t\t})\n\t}\n}\n\n// ParamsFilter filter params\nfunc (l *slogLogger) ParamsFilter(ctx context.Context, sql string, params ...interface{}) (string, []interface{}) {\n\tif l.Parameterized {\n\t\treturn sql, nil\n\t}\n\treturn sql, params\n}\n',
            'logger/slog_test.go': '//go:build go1.21\n\npackage logger\n\nimport (\n\t"bytes"\n\t"context"\n\t"log/slog"\n\t"strings"\n\t"testing"\n\t"time"\n)\n\nfunc TestSlogLogger(t *testing.T) {\n\tbuf := &bytes.Buffer{}\n\thandler := slog.NewTextHandler(buf, &slog.HandlerOptions{AddSource: true})\n\tlogger := NewSlogLogger(slog.New(handler), Config{LogLevel: Info})\n\n\tlogger.Trace(context.Background(), time.Now(), func() (string, int64) {\n\t\treturn "select count(*) from users", 0\n\t}, nil)\n\n\tif strings.Contains(buf.String(), "gorm/logger/slog.go") {\n\t\tt.Error("Found internal slog.go reference in caller frame. Expected only test file references.")\n\t}\n\n\tif !strings.Contains(buf.String(), "gorm/logger/slog_test.go") {\n\t\tt.Error("Missing expected test file reference. \'gorm/logger/slog_test.go\' should appear in caller frames.")\n\t}\n}\n',
            'utils/utils.go': 'package utils\n\nimport (\n\t"database/sql/driver"\n\t"fmt"\n\t"path/filepath"\n\t"reflect"\n\t"runtime"\n\t"strconv"\n\t"strings"\n\t"unicode"\n)\n\nvar gormSourceDir string\n\nfunc init() {\n\t_, file, _, _ := runtime.Caller(0)\n\t// compatible solution to get gorm source directory with various operating systems\n\tgormSourceDir = sourceDir(file)\n}\n\nfunc sourceDir(file string) string {\n\tdir := filepath.Dir(file)\n\tdir = filepath.Dir(dir)\n\n\ts := filepath.Dir(dir)\n\tif filepath.Base(s) != "gorm.io" {\n\t\ts = dir\n\t}\n\treturn filepath.ToSlash(s) + "/"\n}\n\n// FileWithLineNum return the file name and line number of the current file\nfunc FileWithLineNum() string {\n\tpcs := [13]uintptr{}\n\t// the third caller usually from gorm internal\n\tlen := runtime.Callers(3, pcs[:])\n\tframes := runtime.CallersFrames(pcs[:len])\n\tfor i := 0; i < len; i++ {\n\t\t// second return value is "more", not "ok"\n\t\tframe, _ := frames.Next()\n\t\tif (!strings.HasPrefix(frame.File, gormSourceDir) ||\n\t\t\tstrings.HasSuffix(frame.File, "_test.go")) && !strings.HasSuffix(frame.File, ".gen.go") {\n\t\t\treturn string(strconv.AppendInt(append([]byte(frame.File), \':\'), int64(frame.Line), 10))\n\t\t}\n\t}\n\n\treturn ""\n}\n\nfunc IsInvalidDBNameChar(c rune) bool {\n\treturn !unicode.IsLetter(c) && !unicode.IsNumber(c) && c != \'.\' && c != \'*\' && c != \'_\' && c != \'$\' && c != \'@\'\n}\n\n// CheckTruth check string true or not\nfunc CheckTruth(vals ...string) bool {\n\tfor _, val := range vals {\n\t\tif val != "" && !strings.EqualFold(val, "false") {\n\t\t\treturn true\n\t\t}\n\t}\n\treturn false\n}\n\nfunc ToStringKey(values ...interface{}) string {\n\tresults := make([]string, len(values))\n\n\tfor idx, value := range values {\n\t\tif valuer, ok := value.(driver.Valuer); ok {\n\t\t\tvalue, _ = valuer.Value()\n\t\t}\n\n\t\tswitch v := value.(type) {\n\t\tcase string:\n\t\t\tresults[idx] = v\n\t\tcase []byte:\n\t\t\tresults[idx] = string(v)\n\t\tcase uint:\n\t\t\tresults[idx] = strconv.FormatUint(uint64(v), 10)\n\t\tdefault:\n\t\t\tresults[idx] = "nil"\n\t\t\tvv := reflect.ValueOf(v)\n\t\t\tif vv.IsValid() && !vv.IsZero() {\n\t\t\t\tresults[idx] = fmt.Sprint(reflect.Indirect(vv).Interface())\n\t\t\t}\n\t\t}\n\t}\n\n\treturn strings.Join(results, "_")\n}\n\nfunc Contains(elems []string, elem string) bool {\n\tfor _, e := range elems {\n\t\tif elem == e {\n\t\t\treturn true\n\t\t}\n\t}\n\treturn false\n}\n\nfunc AssertEqual(x, y interface{}) bool {\n\tif reflect.DeepEqual(x, y) {\n\t\treturn true\n\t}\n\tif x == nil || y == nil {\n\t\treturn false\n\t}\n\n\txval := reflect.ValueOf(x)\n\tyval := reflect.ValueOf(y)\n\tif xval.Kind() == reflect.Ptr && xval.IsNil() ||\n\t\tyval.Kind() == reflect.Ptr && yval.IsNil() {\n\t\treturn false\n\t}\n\n\tif valuer, ok := x.(driver.Valuer); ok {\n\t\tx, _ = valuer.Value()\n\t}\n\tif valuer, ok := y.(driver.Valuer); ok {\n\t\ty, _ = valuer.Value()\n\t}\n\treturn reflect.DeepEqual(x, y)\n}\n\nfunc ToString(value interface{}) string {\n\tswitch v := value.(type) {\n\tcase string:\n\t\treturn v\n\tcase int:\n\t\treturn strconv.FormatInt(int64(v), 10)\n\tcase int8:\n\t\treturn strconv.FormatInt(int64(v), 10)\n\tcase int16:\n\t\treturn strconv.FormatInt(int64(v), 10)\n\tcase int32:\n\t\treturn strconv.FormatInt(int64(v), 10)\n\tcase int64:\n\t\treturn strconv.FormatInt(v, 10)\n\tcase uint:\n\t\treturn strconv.FormatUint(uint64(v), 10)\n\tcase uint8:\n\t\treturn strconv.FormatUint(uint64(v), 10)\n\tcase uint16:\n\t\treturn strconv.FormatUint(uint64(v), 10)\n\tcase uint32:\n\t\treturn strconv.FormatUint(uint64(v), 10)\n\tcase uint64:\n\t\treturn strconv.FormatUint(v, 10)\n\t}\n\treturn ""\n}\n\nconst nestedRelationSplit = "__"\n\n// NestedRelationName nested relationships like `Manager__Company`\nfunc NestedRelationName(prefix, name string) string {\n\treturn prefix + nestedRelationSplit + name\n}\n\n// SplitNestedRelationName Split nested relationships to `[]string{"Manager","Company"}`\nfunc SplitNestedRelationName(name string) []string {\n\treturn strings.Split(name, nestedRelationSplit)\n}\n\n// JoinNestedRelationNames nested relationships like `Manager__Company`\nfunc JoinNestedRelationNames(relationNames []string) string {\n\treturn strings.Join(relationNames, nestedRelationSplit)\n}\n\n// RTrimSlice Right trims the given slice by given length\nfunc RTrimSlice[T any](v []T, trimLen int) []T {\n\tif trimLen >= len(v) { // trimLen greater than slice len means fully sliced\n\t\treturn v[:0]\n\t}\n\tif trimLen < 0 { // negative trimLen is ignored\n\t\treturn v[:]\n\t}\n\treturn v[:len(v)-trimLen]\n}\n',
        }
