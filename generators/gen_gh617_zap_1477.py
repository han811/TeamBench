"""
Parameterized generator for GH617_zap_1477.

Source PR:    https://github.com/uber-go/zap/pull/1477
Source Issue: N/A

Seed varies: renames 'alert' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH617_zap_1477'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH617_zap_1477'
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
                files[fpath] = files[fpath].replace('alert', 'alert' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH617_zap_1477',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'uber-go/zap',
                "pr_number": 1477,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/uber-go/zap/pull/1477",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'http_handler_test.go': '// Copyright (c) 2016 Uber Technologies, Inc.\n//\n// Permission is hereby granted, free of charge, to any person obtaining a copy\n// of this software and associated documentation files (the "Software"), to deal\n// in the Software without restriction, including without limitation the rights\n// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n// copies of the Software, and to permit persons to whom the Software is\n// furnished to do so, subject to the following conditions:\n//\n// The above copyright notice and this permission notice shall be included in\n// all copies or substantial portions of the Software.\n//\n// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN\n// THE SOFTWARE.\n\npackage zap_test\n\nimport (\n\t"encoding/json"\n\t"errors"\n\t"net/http"\n\t"net/http/httptest"\n\t"strings"\n\t"testing"\n\n\t"go.uber.org/zap"\n\t"go.uber.org/zap/zapcore"\n\n\t"github.com/stretchr/testify/assert"\n\t"github.com/stretchr/testify/require"\n)\n\nfunc TestAtomicLevelServeHTTP(t *testing.T) {\n\ttests := []struct {\n\t\tdesc          string\n\t\tmethod        string\n\t\tquery         string\n\t\tcontentType   string\n\t\tbody          string\n\t\texpectedCode  int\n\t\texpectedLevel zapcore.Level\n\t}{\n\t\t{\n\t\t\tdesc:          "GET",\n\t\t\tmethod:        http.MethodGet,\n\t\t\texpectedCode:  http.StatusOK,\n\t\t\texpectedLevel: zap.InfoLevel,\n\t\t},\n\t\t{\n\t\t\tdesc:          "PUT JSON",\n\t\t\tmethod:        http.MethodPut,\n\t\t\texpectedCode:  http.StatusOK,\n\t\t\texpectedLevel: zap.WarnLevel,\n\t\t\tbody:          `{"level":"warn"}`,\n\t\t},\n\t\t{\n\t\t\tdesc:          "PUT URL encoded",\n\t\t\tmethod:        http.MethodPut,\n\t\t\texpectedCode:  http.StatusOK,\n\t\t\texpectedLevel: zap.WarnLevel,\n\t\t\tcontentType:   "application/x-www-form-urlencoded",\n\t\t\tbody:          "level=warn",\n\t\t},\n\t\t{\n\t\t\tdesc:          "PUT query parameters",\n\t\t\tmethod:        http.MethodPut,\n\t\t\tquery:         "?level=warn",\n\t\t\texpectedCode:  http.StatusOK,\n\t\t\texpectedLevel: zap.WarnLevel,\n\t\t\tcontentType:   "application/x-www-form-urlencoded",\n\t\t},\n\t\t{\n\t\t\tdesc:          "body takes precedence over query",\n\t\t\tmethod:        http.MethodPut,\n\t\t\tquery:         "?level=info",\n\t\t\texpectedCode:  http.StatusOK,\n\t\t\texpectedLevel: zap.WarnLevel,\n\t\t\tcontentType:   "application/x-www-form-urlencoded",\n\t\t\tbody:          "level=warn",\n\t\t},\n\t\t{\n\t\t\tdesc:          "JSON ignores query",\n\t\t\tmethod:        http.MethodPut,\n\t\t\tquery:         "?level=info",\n\t\t\texpectedCode:  http.StatusOK,\n\t\t\texpectedLevel: zap.WarnLevel,\n\t\t\tbody:          `{"level":"warn"}`,\n\t\t},\n\t\t{\n\t\t\tdesc:         "PUT JSON unrecognized",\n\t\t\tmethod:       http.MethodPut,\n\t\t\texpectedCode: http.StatusBadRequest,\n\t\t\tbody:         `{"level":"unrecognized"}`,\n\t\t},\n\t\t{\n\t\t\tdesc:         "PUT URL encoded unrecognized",\n\t\t\tmethod:       http.MethodPut,\n\t\t\texpectedCode: http.StatusBadRequest,\n\t\t\tcontentType:  "application/x-www-form-urlencoded",\n\t\t\tbody:         "level=unrecognized",\n\t\t},\n\t\t{\n\t\t\tdesc:         "PUT JSON malformed",\n\t\t\tmethod:       http.MethodPut,\n\t\t\texpectedCode: http.StatusBadRequest,\n\t\t\tbody:         `{"level":"warn`,\n\t\t},\n\t\t{\n\t\t\tdesc:         "PUT URL encoded malformed",\n\t\t\tmethod:       http.MethodPut,\n\t\t\tquery:        "?level=%",\n\t\t\texpectedCode: http.StatusBadRequest,\n\t\t\tcontentType:  "application/x-www-form-urlencoded",\n\t\t},\n\t\t{\n\t\t\tdesc:         "PUT Query parameters malformed",\n\t\t\tmethod:       http.MethodPut,\n\t\t\texpectedCode: http.StatusBadRequest,\n\t\t\tcontentType:  "application/x-www-form-urlencoded",\n\t\t\tbody:         "level=%",\n\t\t},\n\t\t{\n\t\t\tdesc:         "PUT JSON unspecified",\n\t\t\tmethod:       http.MethodPut,\n\t\t\texpectedCode: http.StatusBadRequest,\n\t\t\tbody:         `{}`,\n\t\t},\n\t\t{\n\t\t\tdesc:         "PUT URL encoded unspecified",\n\t\t\tmethod:       http.MethodPut,\n\t\t\texpectedCode: http.StatusBadRequest,\n\t\t\tcontentType:  "application/x-www-form-urlencoded",\n\t\t\tbody:         "",\n\t\t},\n\t\t{\n\t\t\tdesc:         "POST JSON",\n\t\t\tmethod:       http.MethodPost,\n\t\t\texpectedCode: http.StatusMethodNotAllowed,\n\t\t\tbody:         `{"level":"warn"}`,\n\t\t},\n\t\t{\n\t\t\tdesc:         "POST URL",\n\t\t\tmethod:       http.MethodPost,\n\t\t\texpectedCode: http.StatusMethodNotAllowed,\n\t\t\tcontentType:  "application/x-www-form-urlencoded",\n\t\t\tbody:         "level=warn",\n\t\t},\n\t}\n\n\tfor _, tt := range tests {\n\t\tt.Run(tt.desc, func(t *testing.T) {\n\t\t\tlvl := zap.NewAtomicLevel()\n\t\t\tlvl.SetLevel(zapcore.InfoLevel)\n\n\t\t\tserver := httptest.NewServer(lvl)\n\t\t\tdefer server.Close()\n\n\t\t\treq, err := http.NewRequest(tt.method, server.URL+tt.query, strings.NewReader(tt.body))\n\t\t\trequire.NoError(t, err, "Error constructing %s request.", req.Method)\n\t\t\tif tt.contentType != "" {\n\t\t\t\treq.Header.Set("Content-Type", tt.contentType)\n\t\t\t}\n\n\t\t\tres, err := http.DefaultClient.Do(req)\n\t\t\trequire.NoError(t, err, "Error making %s request.", req.Method)\n\t\t\tdefer func() {\n\t\t\t\tassert.NoError(t, res.Body.Close(), "Error closing response body.")\n\t\t\t}()\n\n\t\t\trequire.Equal(t, tt.expectedCode, res.StatusCode, "Unexpected status code.")\n\t\t\tif tt.expectedCode != http.StatusOK {\n\t\t\t\t// Don\'t need to test exact error message, but one should be present.\n\t\t\t\tvar pld struct {\n\t\t\t\t\tError string `json:"error"`\n\t\t\t\t}\n\t\t\t\trequire.NoError(t, json.NewDecoder(res.Body).Decode(&pld), "Decoding response body")\n\t\t\t\tassert.NotEmpty(t, pld.Error, "Expected an error message")\n\t\t\t\treturn\n\t\t\t}\n\n\t\t\tvar pld struct {\n\t\t\t\tLevel zapcore.Level `json:"level"`\n\t\t\t}\n\t\t\trequire.NoError(t, json.NewDecoder(res.Body).Decode(&pld), "Decoding response body")\n\t\t\tassert.Equal(t, tt.expectedLevel, pld.Level, "Unexpected logging level returned")\n\t\t})\n\t}\n}\n\nfunc TestAtomicLevelServeHTTPBrokenWriter(t *testing.T) {\n\tt.Parallel()\n\n\tlvl := zap.NewAtomicLevel()\n\n\trequest, err := http.NewRequest(http.MethodGet, "http://localhost:1234/log/level", nil)\n\trequire.NoError(t, err, "Error constructing request.")\n\n\trecorder := httptest.NewRecorder()\n\tlvl.ServeHTTP(&brokenHTTPResponseWriter{\n\t\tResponseWriter: recorder,\n\t}, request)\n\n\tassert.Equal(t, http.StatusInternalServerError, recorder.Code, "Unexpected status code.")\n}\n\ntype brokenHTTPResponseWriter struct {\n\thttp.ResponseWriter\n}\n\nfunc (w *brokenHTTPResponseWriter) Write([]byte) (int, error) {\n\treturn 0, errors.New("great sadness")\n}\n',
        }
