"""
Parameterized generator for GH311_fiber_4060.

Source PR:    https://github.com/gofiber/fiber/pull/4060
Source Issue: N/A

Seed varies: renames 'after' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH311_fiber_4060'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH311_fiber_4060'
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
                files[fpath] = files[fpath].replace('after', 'after' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH311_fiber_4060',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'gofiber/fiber',
                "pr_number": 4060,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/gofiber/fiber/pull/4060",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'addon/retry/exponential_backoff.go': 'package retry\n\nimport (\n\t"crypto/rand"\n\t"math/big"\n\t"time"\n)\n\n// ExponentialBackoff is a retry mechanism for retrying some calls.\ntype ExponentialBackoff struct {\n\t// InitialInterval is the initial time interval for backoff algorithm.\n\tInitialInterval time.Duration\n\n\t// MaxBackoffTime is the maximum time duration for backoff algorithm. It limits\n\t// the maximum sleep time.\n\tMaxBackoffTime time.Duration\n\n\t// Multiplier is a multiplier number of the backoff algorithm.\n\tMultiplier float64\n\n\t// MaxRetryCount is the maximum number of retry count.\n\tMaxRetryCount int\n\n\t// currentInterval tracks the current sleep time.\n\tcurrentInterval time.Duration\n}\n\n// NewExponentialBackoff creates a ExponentialBackoff with default values.\nfunc NewExponentialBackoff(config ...Config) *ExponentialBackoff {\n\tcfg := configDefault(config...)\n\treturn &ExponentialBackoff{\n\t\tInitialInterval: cfg.InitialInterval,\n\t\tMaxBackoffTime:  cfg.MaxBackoffTime,\n\t\tMultiplier:      cfg.Multiplier,\n\t\tMaxRetryCount:   cfg.MaxRetryCount,\n\t\tcurrentInterval: cfg.currentInterval,\n\t}\n}\n\n// Retry is the core logic of the retry mechanism. If the calling function returns\n// nil as an error, then the Retry method is terminated with returning nil. Otherwise,\n// if all function calls are returned error, then the method returns this error.\nfunc (e *ExponentialBackoff) Retry(f func() error) error {\n\tif e.currentInterval <= 0 {\n\t\te.currentInterval = e.InitialInterval\n\t}\n\tvar err error\n\tfor range e.MaxRetryCount {\n\t\terr = f()\n\t\tif err == nil {\n\t\t\treturn nil\n\t\t}\n\t\tnext := e.next()\n\t\ttime.Sleep(next)\n\t}\n\treturn err\n}\n\n// next calculates the next sleeping time interval.\nfunc (e *ExponentialBackoff) next() time.Duration {\n\t// generate a random value between [0, 1000)\n\tn, err := rand.Int(rand.Reader, big.NewInt(1000))\n\tif err != nil {\n\t\treturn e.MaxBackoffTime\n\t}\n\tt := e.currentInterval + (time.Duration(n.Int64()) * time.Millisecond)\n\te.currentInterval = time.Duration(float64(e.currentInterval) * e.Multiplier)\n\tif t >= e.MaxBackoffTime {\n\t\te.currentInterval = e.MaxBackoffTime\n\t\treturn e.MaxBackoffTime\n\t}\n\treturn t\n}\n',
            'addon/retry/exponential_backoff_test.go': 'package retry\n\nimport (\n\t"crypto/rand"\n\t"errors"\n\t"testing"\n\t"time"\n\n\t"github.com/stretchr/testify/require"\n)\n\nfunc Test_ExponentialBackoff_Retry(t *testing.T) {\n\tt.Parallel()\n\ttests := []struct {\n\t\texpErr     error\n\t\texpBackoff *ExponentialBackoff\n\t\tf          func() error\n\t\tname       string\n\t}{\n\t\t{\n\t\t\tname:       "With default values - successful",\n\t\t\texpBackoff: NewExponentialBackoff(),\n\t\t\tf: func() error {\n\t\t\t\treturn nil\n\t\t\t},\n\t\t},\n\t\t{\n\t\t\tname: "Successful function",\n\t\t\texpBackoff: &ExponentialBackoff{\n\t\t\t\tInitialInterval: 1 * time.Millisecond,\n\t\t\t\tMaxBackoffTime:  100 * time.Millisecond,\n\t\t\t\tMultiplier:      2.0,\n\t\t\t\tMaxRetryCount:   5,\n\t\t\t},\n\t\t\tf: func() error {\n\t\t\t\treturn nil\n\t\t\t},\n\t\t},\n\t\t{\n\t\t\tname: "Unsuccessful function",\n\t\t\texpBackoff: &ExponentialBackoff{\n\t\t\t\tInitialInterval: 2 * time.Millisecond,\n\t\t\t\tMaxBackoffTime:  100 * time.Millisecond,\n\t\t\t\tMultiplier:      2.0,\n\t\t\t\tMaxRetryCount:   5,\n\t\t\t},\n\t\t\tf: func() error {\n\t\t\t\treturn errors.New("failed function")\n\t\t\t},\n\t\t\texpErr: errors.New("failed function"),\n\t\t},\n\t}\n\n\tfor _, tt := range tests {\n\t\tt.Run(tt.name, func(t *testing.T) {\n\t\t\tt.Parallel()\n\t\t\terr := tt.expBackoff.Retry(tt.f)\n\t\t\trequire.Equal(t, tt.expErr, err)\n\t\t})\n\t}\n}\n\nfunc Test_ExponentialBackoff_Next(t *testing.T) {\n\tt.Parallel()\n\ttests := []struct {\n\t\tname                 string\n\t\texpBackoff           *ExponentialBackoff\n\t\texpNextTimeIntervals []time.Duration\n\t}{\n\t\t{\n\t\t\tname:       "With default values",\n\t\t\texpBackoff: NewExponentialBackoff(),\n\t\t\texpNextTimeIntervals: []time.Duration{\n\t\t\t\t1 * time.Second,\n\t\t\t\t2 * time.Second,\n\t\t\t\t4 * time.Second,\n\t\t\t\t8 * time.Second,\n\t\t\t\t16 * time.Second,\n\t\t\t\t32 * time.Second,\n\t\t\t\t32 * time.Second,\n\t\t\t\t32 * time.Second,\n\t\t\t\t32 * time.Second,\n\t\t\t\t32 * time.Second,\n\t\t\t},\n\t\t},\n\t\t{\n\t\t\tname: "Custom values",\n\t\t\texpBackoff: &ExponentialBackoff{\n\t\t\t\tInitialInterval: 2.0 * time.Second,\n\t\t\t\tMaxBackoffTime:  64 * time.Second,\n\t\t\t\tMultiplier:      3.0,\n\t\t\t\tMaxRetryCount:   8,\n\t\t\t\tcurrentInterval: 2.0 * time.Second,\n\t\t\t},\n\t\t\texpNextTimeIntervals: []time.Duration{\n\t\t\t\t2 * time.Second,\n\t\t\t\t6 * time.Second,\n\t\t\t\t18 * time.Second,\n\t\t\t\t54 * time.Second,\n\t\t\t\t64 * time.Second,\n\t\t\t\t64 * time.Second,\n\t\t\t\t64 * time.Second,\n\t\t\t\t64 * time.Second,\n\t\t\t},\n\t\t},\n\t}\n\n\tfor _, tt := range tests {\n\t\tt.Run(tt.name, func(t *testing.T) {\n\t\t\tt.Parallel()\n\t\t\tfor i := range tt.expBackoff.MaxRetryCount {\n\t\t\t\tnext := tt.expBackoff.next()\n\t\t\t\tif next < tt.expNextTimeIntervals[i] || next > tt.expNextTimeIntervals[i]+1*time.Second {\n\t\t\t\t\tt.Errorf("wrong next time:\\n"+\n\t\t\t\t\t\t"actual:%v\\n"+\n\t\t\t\t\t\t"expected range:%v-%v\\n",\n\t\t\t\t\t\tnext, tt.expNextTimeIntervals[i], tt.expNextTimeIntervals[i]+1*time.Second)\n\t\t\t\t}\n\t\t\t}\n\t\t})\n\t}\n}\n\nfunc Test_ExponentialBackoff_NextRandFailure(t *testing.T) {\n\t// Backup original reader and restore at the end\n\toriginal := rand.Reader\n\tdefer func() { rand.Reader = original }()\n\trand.Reader = failingReader{}\n\n\texpBackoff := &ExponentialBackoff{\n\t\tInitialInterval: 1 * time.Second,\n\t\tMaxBackoffTime:  10 * time.Second,\n\t\tMultiplier:      2,\n\t\tMaxRetryCount:   3,\n\t\tcurrentInterval: 1 * time.Second,\n\t}\n\tnext := expBackoff.next()\n\trequire.Equal(t, expBackoff.MaxBackoffTime, next)\n\t// currentInterval should not change when random fails\n\trequire.Equal(t, 1*time.Second, expBackoff.currentInterval)\n}\n\ntype failingReader struct{}\n\nfunc (failingReader) Read(_ []byte) (int, error) { return 0, errors.New("fail") }\n',
        }
