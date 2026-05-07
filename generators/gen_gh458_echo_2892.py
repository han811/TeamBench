"""
Parameterized generator for GH458_echo_2892.

Source PR:    https://github.com/labstack/echo/pull/2892
Source Issue: N/A

Seed varies: renames 'code' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH458_echo_2892'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH458_echo_2892'
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
                files[fpath] = files[fpath].replace('code', 'code' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH458_echo_2892',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'labstack/echo',
                "pr_number": 2892,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/labstack/echo/pull/2892",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'httperror.go': '// SPDX-License-Identifier: MIT\n// SPDX-FileCopyrightText: © 2015 LabStack LLC and Echo contributors\n\npackage echo\n\nimport (\n\t"errors"\n\t"fmt"\n\t"net/http"\n)\n\n// HTTPStatusCoder is interface that errors can implement to produce status code for HTTP response\ntype HTTPStatusCoder interface {\n\tStatusCode() int\n}\n\n// Following errors can produce HTTP status code by implementing HTTPStatusCoder interface\nvar (\n\tErrBadRequest                  = &httpError{http.StatusBadRequest}            // 400\n\tErrUnauthorized                = &httpError{http.StatusUnauthorized}          // 401\n\tErrForbidden                   = &httpError{http.StatusForbidden}             // 403\n\tErrNotFound                    = &httpError{http.StatusNotFound}              // 404\n\tErrMethodNotAllowed            = &httpError{http.StatusMethodNotAllowed}      // 405\n\tErrRequestTimeout              = &httpError{http.StatusRequestTimeout}        // 408\n\tErrStatusRequestEntityTooLarge = &httpError{http.StatusRequestEntityTooLarge} // 413\n\tErrUnsupportedMediaType        = &httpError{http.StatusUnsupportedMediaType}  // 415\n\tErrTooManyRequests             = &httpError{http.StatusTooManyRequests}       // 429\n\tErrInternalServerError         = &httpError{http.StatusInternalServerError}   // 500\n\tErrBadGateway                  = &httpError{http.StatusBadGateway}            // 502\n\tErrServiceUnavailable          = &httpError{http.StatusServiceUnavailable}    // 503\n)\n\n// Following errors fall into 500 (InternalServerError) category\nvar (\n\tErrValidatorNotRegistered = errors.New("validator not registered")\n\tErrRendererNotRegistered  = errors.New("renderer not registered")\n\tErrInvalidRedirectCode    = errors.New("invalid redirect status code")\n\tErrCookieNotFound         = errors.New("cookie not found")\n\tErrInvalidCertOrKeyType   = errors.New("invalid cert or key type, must be string or []byte")\n\tErrInvalidListenerNetwork = errors.New("invalid listener network")\n)\n\n// NewHTTPError creates new instance of HTTPError\nfunc NewHTTPError(code int, message string) *HTTPError {\n\treturn &HTTPError{\n\t\tCode:    code,\n\t\tMessage: message,\n\t}\n}\n\n// HTTPError represents an error that occurred while handling a request.\ntype HTTPError struct {\n\t// Code is status code for HTTP response\n\tCode    int    `json:"-"`\n\tMessage string `json:"message"`\n\terr     error\n}\n\n// StatusCode returns status code for HTTP response\nfunc (he *HTTPError) StatusCode() int {\n\treturn he.Code\n}\n\n// Error makes it compatible with `error` interface.\nfunc (he *HTTPError) Error() string {\n\tmsg := he.Message\n\tif msg == "" {\n\t\tmsg = http.StatusText(he.Code)\n\t}\n\tif he.err == nil {\n\t\treturn fmt.Sprintf("code=%d, message=%v", he.Code, msg)\n\t}\n\treturn fmt.Sprintf("code=%d, message=%v, err=%v", he.Code, msg, he.err.Error())\n}\n\n// Wrap eturns new HTTPError with given errors wrapped inside\nfunc (he HTTPError) Wrap(err error) error {\n\treturn &HTTPError{\n\t\tCode:    he.Code,\n\t\tMessage: he.Message,\n\t\terr:     err,\n\t}\n}\n\nfunc (he *HTTPError) Unwrap() error {\n\treturn he.err\n}\n\ntype httpError struct {\n\tcode int\n}\n\nfunc (he httpError) StatusCode() int {\n\treturn he.code\n}\n\nfunc (he httpError) Error() string {\n\treturn http.StatusText(he.code) // does not include status code\n}\n\nfunc (he httpError) Wrap(err error) error {\n\treturn &HTTPError{\n\t\tCode:    he.code,\n\t\tMessage: http.StatusText(he.code),\n\t\terr:     err,\n\t}\n}\n',
            'httperror_test.go': '// SPDX-License-Identifier: MIT\n// SPDX-FileCopyrightText: © 2015 LabStack LLC and Echo contributors\n\npackage echo\n\nimport (\n\t"errors"\n\t"github.com/stretchr/testify/assert"\n\t"net/http"\n\t"testing"\n)\n\nfunc TestHTTPError_StatusCode(t *testing.T) {\n\tvar err error = &HTTPError{Code: http.StatusBadRequest, Message: "my error message"}\n\n\tcode := 0\n\tvar sc HTTPStatusCoder\n\tif errors.As(err, &sc) {\n\t\tcode = sc.StatusCode()\n\t}\n\tassert.Equal(t, http.StatusBadRequest, code)\n}\n\nfunc TestHTTPError_Error(t *testing.T) {\n\tvar testCases = []struct {\n\t\tname   string\n\t\terror  error\n\t\texpect string\n\t}{\n\t\t{\n\t\t\tname:   "ok, without message",\n\t\t\terror:  &HTTPError{Code: http.StatusBadRequest},\n\t\t\texpect: "code=400, message=Bad Request",\n\t\t},\n\t\t{\n\t\t\tname:   "ok, with message",\n\t\t\terror:  &HTTPError{Code: http.StatusBadRequest, Message: "my error message"},\n\t\t\texpect: "code=400, message=my error message",\n\t\t},\n\t}\n\tfor _, tc := range testCases {\n\t\tt.Run(tc.name, func(t *testing.T) {\n\t\t\tassert.Equal(t, tc.expect, tc.error.Error())\n\t\t})\n\t}\n}\n\nfunc TestHTTPError_WrapUnwrap(t *testing.T) {\n\terr := &HTTPError{Code: http.StatusBadRequest, Message: "bad"}\n\twrapped := err.Wrap(errors.New("my_error")).(*HTTPError)\n\n\terr.Code = http.StatusOK\n\terr.Message = "changed"\n\n\tassert.Equal(t, http.StatusBadRequest, wrapped.Code)\n\tassert.Equal(t, "bad", wrapped.Message)\n\n\tassert.Equal(t, errors.New("my_error"), wrapped.Unwrap())\n\tassert.Equal(t, "code=400, message=bad, err=my_error", wrapped.Error())\n}\n\nfunc TestNewHTTPError(t *testing.T) {\n\terr := NewHTTPError(http.StatusBadRequest, "bad")\n\terr2 := &HTTPError{Code: http.StatusBadRequest, Message: "bad"}\n\n\tassert.Equal(t, err2, err)\n}\n',
        }
