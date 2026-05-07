"""
Parameterized generator for GH581_logrus_1500.

Source PR:    https://github.com/sirupsen/logrus/pull/1500
Source Issue: N/A

Seed varies: renames 'about' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH581_logrus_1500'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH581_logrus_1500'
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
                files[fpath] = files[fpath].replace('about', 'about' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH581_logrus_1500',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'sirupsen/logrus',
                "pr_number": 1500,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/sirupsen/logrus/pull/1500",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'hook_test.go': 'package logrus_test\n\nimport (\n\t"bytes"\n\t"encoding/json"\n\t"fmt"\n\t"sync"\n\t"testing"\n\n\t"github.com/stretchr/testify/assert"\n\t"github.com/stretchr/testify/require"\n\n\t. "github.com/sirupsen/logrus"\n\t"github.com/sirupsen/logrus/hooks/test"\n\t. "github.com/sirupsen/logrus/internal/testutils"\n)\n\ntype TestHook struct {\n\tFired bool\n}\n\nfunc (hook *TestHook) Fire(entry *Entry) error {\n\thook.Fired = true\n\treturn nil\n}\n\nfunc (hook *TestHook) Levels() []Level {\n\treturn []Level{\n\t\tTraceLevel,\n\t\tDebugLevel,\n\t\tInfoLevel,\n\t\tWarnLevel,\n\t\tErrorLevel,\n\t\tFatalLevel,\n\t\tPanicLevel,\n\t}\n}\n\nfunc TestHookFires(t *testing.T) {\n\thook := new(TestHook)\n\n\tLogAndAssertJSON(t, func(log *Logger) {\n\t\tlog.Hooks.Add(hook)\n\t\tassert.False(t, hook.Fired)\n\n\t\tlog.Print("test")\n\t}, func(fields Fields) {\n\t\tassert.True(t, hook.Fired)\n\t})\n}\n\ntype ModifyHook struct {\n}\n\nfunc (hook *ModifyHook) Fire(entry *Entry) error {\n\tentry.Data["wow"] = "whale"\n\treturn nil\n}\n\nfunc (hook *ModifyHook) Levels() []Level {\n\treturn []Level{\n\t\tTraceLevel,\n\t\tDebugLevel,\n\t\tInfoLevel,\n\t\tWarnLevel,\n\t\tErrorLevel,\n\t\tFatalLevel,\n\t\tPanicLevel,\n\t}\n}\n\nfunc TestHookCanModifyEntry(t *testing.T) {\n\thook := new(ModifyHook)\n\n\tLogAndAssertJSON(t, func(log *Logger) {\n\t\tlog.Hooks.Add(hook)\n\t\tlog.WithField("wow", "elephant").Print("test")\n\t}, func(fields Fields) {\n\t\tassert.Equal(t, "whale", fields["wow"])\n\t})\n}\n\nfunc TestCanFireMultipleHooks(t *testing.T) {\n\thook1 := new(ModifyHook)\n\thook2 := new(TestHook)\n\n\tLogAndAssertJSON(t, func(log *Logger) {\n\t\tlog.Hooks.Add(hook1)\n\t\tlog.Hooks.Add(hook2)\n\n\t\tlog.WithField("wow", "elephant").Print("test")\n\t}, func(fields Fields) {\n\t\tassert.Equal(t, "whale", fields["wow"])\n\t\tassert.True(t, hook2.Fired)\n\t})\n}\n\ntype SingleLevelModifyHook struct {\n\tModifyHook\n}\n\nfunc (h *SingleLevelModifyHook) Levels() []Level {\n\treturn []Level{InfoLevel}\n}\n\nfunc TestHookEntryIsPristine(t *testing.T) {\n\tl := New()\n\tb := &bytes.Buffer{}\n\tl.Formatter = &JSONFormatter{}\n\tl.Out = b\n\tl.AddHook(&SingleLevelModifyHook{})\n\n\tl.Error("error message")\n\tdata := map[string]string{}\n\terr := json.Unmarshal(b.Bytes(), &data)\n\trequire.NoError(t, err)\n\t_, ok := data["wow"]\n\trequire.False(t, ok)\n\tb.Reset()\n\n\tl.Info("error message")\n\tdata = map[string]string{}\n\terr = json.Unmarshal(b.Bytes(), &data)\n\trequire.NoError(t, err)\n\t_, ok = data["wow"]\n\trequire.True(t, ok)\n\tb.Reset()\n\n\tl.Error("error message")\n\tdata = map[string]string{}\n\terr = json.Unmarshal(b.Bytes(), &data)\n\trequire.NoError(t, err)\n\t_, ok = data["wow"]\n\trequire.False(t, ok)\n\tb.Reset()\n}\n\ntype ErrorHook struct {\n\tFired bool\n}\n\nfunc (hook *ErrorHook) Fire(entry *Entry) error {\n\thook.Fired = true\n\treturn nil\n}\n\nfunc (hook *ErrorHook) Levels() []Level {\n\treturn []Level{\n\t\tErrorLevel,\n\t}\n}\n\nfunc TestErrorHookShouldntFireOnInfo(t *testing.T) {\n\thook := new(ErrorHook)\n\n\tLogAndAssertJSON(t, func(log *Logger) {\n\t\tlog.Hooks.Add(hook)\n\t\tlog.Info("test")\n\t}, func(fields Fields) {\n\t\tassert.False(t, hook.Fired)\n\t})\n}\n\nfunc TestErrorHookShouldFireOnError(t *testing.T) {\n\thook := new(ErrorHook)\n\n\tLogAndAssertJSON(t, func(log *Logger) {\n\t\tlog.Hooks.Add(hook)\n\t\tlog.Error("test")\n\t}, func(fields Fields) {\n\t\tassert.True(t, hook.Fired)\n\t})\n}\n\nfunc TestAddHookRace(t *testing.T) {\n\tvar wg sync.WaitGroup\n\twg.Add(2)\n\thook := new(ErrorHook)\n\tLogAndAssertJSON(t, func(log *Logger) {\n\t\tgo func() {\n\t\t\tdefer wg.Done()\n\t\t\tlog.AddHook(hook)\n\t\t}()\n\t\tgo func() {\n\t\t\tdefer wg.Done()\n\t\t\tlog.Error("test")\n\t\t}()\n\t\twg.Wait()\n\t}, func(fields Fields) {\n\t\t// the line may have been logged\n\t\t// before the hook was added, so we can\'t\n\t\t// actually assert on the hook\n\t})\n}\n\nfunc TestAddHookRace2(t *testing.T) {\n\tt.Parallel()\n\n\tfor i := range 3 {\n\t\ttestname := fmt.Sprintf("Test %d", i)\n\t\tt.Run(testname, func(t *testing.T) {\n\t\t\tt.Parallel()\n\n\t\t\t_ = test.NewGlobal()\n\t\t\tInfo(testname)\n\t\t})\n\t}\n}\n\ntype HookCallFunc struct {\n\tF func()\n}\n\nfunc (h *HookCallFunc) Levels() []Level {\n\treturn AllLevels\n}\n\nfunc (h *HookCallFunc) Fire(e *Entry) error {\n\th.F()\n\treturn nil\n}\n\nfunc TestHookFireOrder(t *testing.T) {\n\tcheckers := []string{}\n\th := LevelHooks{}\n\th.Add(&HookCallFunc{F: func() { checkers = append(checkers, "first hook") }})\n\th.Add(&HookCallFunc{F: func() { checkers = append(checkers, "second hook") }})\n\th.Add(&HookCallFunc{F: func() { checkers = append(checkers, "third hook") }})\n\n\tif err := h.Fire(InfoLevel, &Entry{}); err != nil {\n\t\tt.Error("unexpected error:", err)\n\t}\n\trequire.Equal(t, []string{"first hook", "second hook", "third hook"}, checkers)\n}\n',
        }
