"""
Parameterized generator for GH50_echo_2825.

Source PR:    https://github.com/labstack/echo/pull/2825
Source Issue: https://github.com/labstack/echo/issues/2794

Seed varies: renames 'back' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH50_echo_2825'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH50_echo_2825'
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
                files[fpath] = files[fpath].replace('back', 'back' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH50_echo_2825',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'labstack/echo',
                "pr_number": 2825,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/labstack/echo/pull/2825",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'middleware/basic_auth.go': '// SPDX-License-Identifier: MIT\n// SPDX-FileCopyrightText: © 2015 LabStack LLC and Echo contributors\n\npackage middleware\n\nimport (\n\t"encoding/base64"\n\t"net/http"\n\t"strconv"\n\t"strings"\n\n\t"github.com/labstack/echo/v4"\n)\n\n// BasicAuthConfig defines the config for BasicAuth middleware.\ntype BasicAuthConfig struct {\n\t// Skipper defines a function to skip middleware.\n\tSkipper Skipper\n\n\t// Validator is a function to validate BasicAuth credentials.\n\t// Required.\n\tValidator BasicAuthValidator\n\n\t// Realm is a string to define realm attribute of BasicAuth.\n\t// Default value "Restricted".\n\tRealm string\n}\n\n// BasicAuthValidator defines a function to validate BasicAuth credentials.\n// The function should return a boolean indicating whether the credentials are valid,\n// and an error if any error occurs during the validation process.\ntype BasicAuthValidator func(string, string, echo.Context) (bool, error)\n\nconst (\n\tbasic        = "basic"\n\tdefaultRealm = "Restricted"\n)\n\n// DefaultBasicAuthConfig is the default BasicAuth middleware config.\nvar DefaultBasicAuthConfig = BasicAuthConfig{\n\tSkipper: DefaultSkipper,\n\tRealm:   defaultRealm,\n}\n\n// BasicAuth returns an BasicAuth middleware.\n//\n// For valid credentials it calls the next handler.\n// For missing or invalid credentials, it sends "401 - Unauthorized" response.\nfunc BasicAuth(fn BasicAuthValidator) echo.MiddlewareFunc {\n\tc := DefaultBasicAuthConfig\n\tc.Validator = fn\n\treturn BasicAuthWithConfig(c)\n}\n\n// BasicAuthWithConfig returns an BasicAuth middleware with config.\n// See `BasicAuth()`.\nfunc BasicAuthWithConfig(config BasicAuthConfig) echo.MiddlewareFunc {\n\t// Defaults\n\tif config.Validator == nil {\n\t\tpanic("echo: basic-auth middleware requires a validator function")\n\t}\n\tif config.Skipper == nil {\n\t\tconfig.Skipper = DefaultBasicAuthConfig.Skipper\n\t}\n\tif config.Realm == "" {\n\t\tconfig.Realm = defaultRealm\n\t}\n\n\treturn func(next echo.HandlerFunc) echo.HandlerFunc {\n\t\treturn func(c echo.Context) error {\n\t\t\tif config.Skipper(c) {\n\t\t\t\treturn next(c)\n\t\t\t}\n\n\t\t\tauth := c.Request().Header.Get(echo.HeaderAuthorization)\n\t\t\tl := len(basic)\n\n\t\t\tif len(auth) > l+1 && strings.EqualFold(auth[:l], basic) {\n\t\t\t\t// Invalid base64 shouldn\'t be treated as error\n\t\t\t\t// instead should be treated as invalid client input\n\t\t\t\tb, err := base64.StdEncoding.DecodeString(auth[l+1:])\n\t\t\t\tif err != nil {\n\t\t\t\t\treturn echo.NewHTTPError(http.StatusBadRequest).SetInternal(err)\n\t\t\t\t}\n\n\t\t\t\tcred := string(b)\n\t\t\t\tfor i := 0; i < len(cred); i++ {\n\t\t\t\t\tif cred[i] == \':\' {\n\t\t\t\t\t\t// Verify credentials\n\t\t\t\t\t\tvalid, err := config.Validator(cred[:i], cred[i+1:], c)\n\t\t\t\t\t\tif err != nil {\n\t\t\t\t\t\t\treturn err\n\t\t\t\t\t\t} else if valid {\n\t\t\t\t\t\t\treturn next(c)\n\t\t\t\t\t\t}\n\t\t\t\t\t\tbreak\n\t\t\t\t\t}\n\t\t\t\t}\n\t\t\t}\n\n\t\t\trealm := defaultRealm\n\t\t\tif config.Realm != defaultRealm {\n\t\t\t\trealm = strconv.Quote(config.Realm)\n\t\t\t}\n\n\t\t\t// Need to return `401` for browsers to pop-up login box.\n\t\t\tc.Response().Header().Set(echo.HeaderWWWAuthenticate, basic+" realm="+realm)\n\t\t\treturn echo.ErrUnauthorized\n\t\t}\n\t}\n}\n',
            'middleware/basic_auth_test.go': '// SPDX-License-Identifier: MIT\n// SPDX-FileCopyrightText: © 2015 LabStack LLC and Echo contributors\n\npackage middleware\n\nimport (\n\t"encoding/base64"\n\t"errors"\n\t"net/http"\n\t"net/http/httptest"\n\t"strings"\n\t"testing"\n\n\t"github.com/labstack/echo/v4"\n\t"github.com/stretchr/testify/assert"\n)\n\nfunc TestBasicAuth(t *testing.T) {\n\te := echo.New()\n\n\tmockValidator := func(u, p string, c echo.Context) (bool, error) {\n\t\tif u == "joe" && p == "secret" {\n\t\t\treturn true, nil\n\t\t}\n\t\treturn false, nil\n\t}\n\n\ttests := []struct {\n\t\tname           string\n\t\tauthHeader     string\n\t\texpectedCode   int\n\t\texpectedAuth   string\n\t\tskipperResult  bool\n\t\texpectedErr    bool\n\t\texpectedErrMsg string\n\t}{\n\t\t{\n\t\t\tname:         "Valid credentials",\n\t\t\tauthHeader:   basic + " " + base64.StdEncoding.EncodeToString([]byte("joe:secret")),\n\t\t\texpectedCode: http.StatusOK,\n\t\t},\n\t\t{\n\t\t\tname:         "Case-insensitive header scheme",\n\t\t\tauthHeader:   strings.ToUpper(basic) + " " + base64.StdEncoding.EncodeToString([]byte("joe:secret")),\n\t\t\texpectedCode: http.StatusOK,\n\t\t},\n\t\t{\n\t\t\tname:           "Invalid credentials",\n\t\t\tauthHeader:     basic + " " + base64.StdEncoding.EncodeToString([]byte("joe:invalid-password")),\n\t\t\texpectedCode:   http.StatusUnauthorized,\n\t\t\texpectedAuth:   basic + ` realm="someRealm"`,\n\t\t\texpectedErr:    true,\n\t\t\texpectedErrMsg: "Unauthorized",\n\t\t},\n\t\t{\n\t\t\tname:           "Invalid base64 string",\n\t\t\tauthHeader:     basic + " invalidString",\n\t\t\texpectedCode:   http.StatusBadRequest,\n\t\t\texpectedErr:    true,\n\t\t\texpectedErrMsg: "Bad Request",\n\t\t},\n\t\t{\n\t\t\tname:           "Missing Authorization header",\n\t\t\texpectedCode:   http.StatusUnauthorized,\n\t\t\texpectedErr:    true,\n\t\t\texpectedErrMsg: "Unauthorized",\n\t\t},\n\t\t{\n\t\t\tname:           "Invalid Authorization header",\n\t\t\tauthHeader:     base64.StdEncoding.EncodeToString([]byte("invalid")),\n\t\t\texpectedCode:   http.StatusUnauthorized,\n\t\t\texpectedErr:    true,\n\t\t\texpectedErrMsg: "Unauthorized",\n\t\t},\n\t\t{\n\t\t\tname:          "Skipped Request",\n\t\t\tauthHeader:    basic + " " + base64.StdEncoding.EncodeToString([]byte("joe:skip")),\n\t\t\texpectedCode:  http.StatusOK,\n\t\t\tskipperResult: true,\n\t\t},\n\t}\n\n\tfor _, tt := range tests {\n\t\tt.Run(tt.name, func(t *testing.T) {\n\n\t\t\treq := httptest.NewRequest(http.MethodGet, "/", nil)\n\t\t\tres := httptest.NewRecorder()\n\t\t\tc := e.NewContext(req, res)\n\n\t\t\tif tt.authHeader != "" {\n\t\t\t\treq.Header.Set(echo.HeaderAuthorization, tt.authHeader)\n\t\t\t}\n\n\t\t\th := BasicAuthWithConfig(BasicAuthConfig{\n\t\t\t\tValidator: mockValidator,\n\t\t\t\tRealm:     "someRealm",\n\t\t\t\tSkipper: func(c echo.Context) bool {\n\t\t\t\t\treturn tt.skipperResult\n\t\t\t\t},\n\t\t\t})(func(c echo.Context) error {\n\t\t\t\treturn c.String(http.StatusOK, "test")\n\t\t\t})\n\n\t\t\terr := h(c)\n\n\t\t\tif tt.expectedErr {\n\t\t\t\tvar he *echo.HTTPError\n\t\t\t\terrors.As(err, &he)\n\t\t\t\tassert.Equal(t, tt.expectedCode, he.Code)\n\t\t\t\tif tt.expectedAuth != "" {\n\t\t\t\t\tassert.Equal(t, tt.expectedAuth, res.Header().Get(echo.HeaderWWWAuthenticate))\n\t\t\t\t}\n\t\t\t} else {\n\t\t\t\tassert.NoError(t, err)\n\t\t\t\tassert.Equal(t, tt.expectedCode, res.Code)\n\t\t\t}\n\t\t})\n\t}\n}\n',
        }
