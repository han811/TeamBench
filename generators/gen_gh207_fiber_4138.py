"""
Parameterized generator for GH207_fiber_4138.

Source PR:    https://github.com/gofiber/fiber/pull/4138
Source Issue: N/A

Seed varies: renames 'aamm' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH207_fiber_4138'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH207_fiber_4138'
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
                files[fpath] = files[fpath].replace('aamm', 'aamm' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH207_fiber_4138',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'gofiber/fiber',
                "pr_number": 4138,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/gofiber/fiber/pull/4138",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'go.mod': 'module github.com/gofiber/fiber/v3\n\ngo 1.25.0\n\nrequire (\n\tgithub.com/gofiber/schema v1.7.0\n\tgithub.com/gofiber/utils/v2 v2.0.2\n\tgithub.com/google/uuid v1.6.0\n\tgithub.com/mattn/go-colorable v0.1.14\n\tgithub.com/mattn/go-isatty v0.0.20\n\tgithub.com/shamaton/msgpack/v3 v3.1.0\n\tgithub.com/stretchr/testify v1.11.1\n\tgithub.com/tinylib/msgp v1.6.3\n\tgithub.com/valyala/bytebufferpool v1.0.0\n\tgithub.com/valyala/fasthttp v1.69.0\n\tgolang.org/x/crypto v0.48.0\n)\n\nrequire (\n\tgithub.com/andybalholm/brotli v1.2.0 // indirect\n\tgithub.com/davecgh/go-spew v1.1.1 // indirect\n\tgithub.com/fxamacker/cbor/v2 v2.9.0 // direct\n\tgithub.com/klauspost/compress v1.18.4 // indirect\n\tgithub.com/philhofer/fwd v1.2.0 // indirect\n\tgithub.com/pmezard/go-difflib v1.0.0 // indirect\n\tgithub.com/x448/float16 v0.8.4 // indirect\n\tgolang.org/x/net v0.51.0\n\tgolang.org/x/sys v0.42.0 // indirect\n\tgolang.org/x/text v0.34.0\n\tgopkg.in/yaml.v3 v3.0.1 // indirect\n)\n',
            'go.sum': 'github.com/andybalholm/brotli v1.2.0 h1:ukwgCxwYrmACq68yiUqwIWnGY0cTPox/M94sVwToPjQ=\ngithub.com/andybalholm/brotli v1.2.0/go.mod h1:rzTDkvFWvIrjDXZHkuS16NPggd91W3kUSvPlQ1pLaKY=\ngithub.com/davecgh/go-spew v1.1.1 h1:vj9j/u1bqnvCEfJOwUhtlOARqs3+rkHYY13jYWTU97c=\ngithub.com/davecgh/go-spew v1.1.1/go.mod h1:J7Y8YcW2NihsgmVo/mv3lAwl/skON4iLHjSsI+c5H38=\ngithub.com/fxamacker/cbor/v2 v2.9.0 h1:NpKPmjDBgUfBms6tr6JZkTHtfFGcMKsw3eGcmD/sapM=\ngithub.com/fxamacker/cbor/v2 v2.9.0/go.mod h1:vM4b+DJCtHn+zz7h3FFp/hDAI9WNWCsZj23V5ytsSxQ=\ngithub.com/gofiber/schema v1.7.0 h1:yNM+FNRZjyYEli9Ey0AXRBrAY9jTnb+kmGs3lJGPvKg=\ngithub.com/gofiber/schema v1.7.0/go.mod h1:A/X5Ffyru4p9eBdp99qu+nzviHzQiZ7odLT+TwxWhbk=\ngithub.com/gofiber/utils/v2 v2.0.2 h1:ShRRssz0F3AhTlAQcuEj54OEDtWF7+HJDwEi/aa6QLI=\ngithub.com/gofiber/utils/v2 v2.0.2/go.mod h1:+9Ub4NqQ+IaJoTliq5LfdmOJAA/Hzwf4pXOxOa3RrJ0=\ngithub.com/google/uuid v1.6.0 h1:NIvaJDMOsjHA8n1jAhLSgzrAzy1Hgr+hNrb57e+94F0=\ngithub.com/google/uuid v1.6.0/go.mod h1:TIyPZe4MgqvfeYDBFedMoGGpEw/LqOeaOT+nhxU+yHo=\ngithub.com/klauspost/compress v1.18.4 h1:RPhnKRAQ4Fh8zU2FY/6ZFDwTVTxgJ/EMydqSTzE9a2c=\ngithub.com/klauspost/compress v1.18.4/go.mod h1:R0h/fSBs8DE4ENlcrlib3PsXS61voFxhIs2DeRhCvJ4=\ngithub.com/mattn/go-colorable v0.1.14 h1:9A9LHSqF/7dyVVX6g0U9cwm9pG3kP9gSzcuIPHPsaIE=\ngithub.com/mattn/go-colorable v0.1.14/go.mod h1:6LmQG8QLFO4G5z1gPvYEzlUgJ2wF+stgPZH1UqBm1s8=\ngithub.com/mattn/go-isatty v0.0.20 h1:xfD0iDuEKnDkl03q4limB+vH+GxLEtL/jb4xVJSWWEY=\ngithub.com/mattn/go-isatty v0.0.20/go.mod h1:W+V8PltTTMOvKvAeJH7IuucS94S2C6jfK/D7dTCTo3Y=\ngithub.com/philhofer/fwd v1.2.0 h1:e6DnBTl7vGY+Gz322/ASL4Gyp1FspeMvx1RNDoToZuM=\ngithub.com/philhofer/fwd v1.2.0/go.mod h1:RqIHx9QI14HlwKwm98g9Re5prTQ6LdeRQn+gXJFxsJM=\ngithub.com/pmezard/go-difflib v1.0.0 h1:4DBwDE0NGyQoBHbLQYPwSUPoCMWR5BEzIk/f1lZbAQM=\ngithub.com/pmezard/go-difflib v1.0.0/go.mod h1:iKH77koFhYxTK1pcRnkKkqfTogsbg7gZNVY4sRDYZ/4=\ngithub.com/shamaton/msgpack/v3 v3.1.0 h1:jsk0vEAqVvvS9+fTZ5/EcQ9tz860c9pWxJ4Iwecz8gU=\ngithub.com/shamaton/msgpack/v3 v3.1.0/go.mod h1:DcQG8jrdrQCIxr3HlMYkiXdMhK+KfN2CitkyzsQV4uc=\ngithub.com/stretchr/testify v1.11.1 h1:7s2iGBzp5EwR7/aIZr8ao5+dra3wiQyKjjFuvgVKu7U=\ngithub.com/stretchr/testify v1.11.1/go.mod h1:wZwfW3scLgRK+23gO65QZefKpKQRnfz6sD981Nm4B6U=\ngithub.com/tinylib/msgp v1.6.3 h1:bCSxiTz386UTgyT1i0MSCvdbWjVW+8sG3PjkGsZQt4s=\ngithub.com/tinylib/msgp v1.6.3/go.mod h1:RSp0LW9oSxFut3KzESt5Voq4GVWyS+PSulT77roAqEA=\ngithub.com/valyala/bytebufferpool v1.0.0 h1:GqA5TC/0021Y/b9FG4Oi9Mr3q7XYx6KllzawFIhcdPw=\ngithub.com/valyala/bytebufferpool v1.0.0/go.mod h1:6bBcMArwyJ5K/AmCkWv1jt77kVWyCJ6HpOuEn7z0Csc=\ngithub.com/valyala/fasthttp v1.69.0 h1:fNLLESD2SooWeh2cidsuFtOcrEi4uB4m1mPrkJMZyVI=\ngithub.com/valyala/fasthttp v1.69.0/go.mod h1:4wA4PfAraPlAsJ5jMSqCE2ug5tqUPwKXxVj8oNECGcw=\ngithub.com/x448/float16 v0.8.4 h1:qLwI1I70+NjRFUR3zs1JPUCgaCXSh3SW62uAKT1mSBM=\ngithub.com/x448/float16 v0.8.4/go.mod h1:14CWIYCyZA/cWjXOioeEpHeN/83MdbZDRQHoFcYsOfg=\ngithub.com/xyproto/randomstring v1.0.5 h1:YtlWPoRdgMu3NZtP45drfy1GKoojuR7hmRcnhZqKjWU=\ngithub.com/xyproto/randomstring v1.0.5/go.mod h1:rgmS5DeNXLivK7YprL0pY+lTuhNQW3iGxZ18UQApw/E=\ngolang.org/x/crypto v0.48.0 h1:/VRzVqiRSggnhY7gNRxPauEQ5Drw9haKdM0jqfcCFts=\ngolang.org/x/crypto v0.48.0/go.mod h1:r0kV5h3qnFPlQnBSrULhlsRfryS2pmewsg+XfMgkVos=\ngolang.org/x/net v0.51.0 h1:94R/GTO7mt3/4wIKpcR5gkGmRLOuE/2hNGeWq/GBIFo=\ngolang.org/x/net v0.51.0/go.mod h1:aamm+2QF5ogm02fjy5Bb7CQ0WMt1/WVM7FtyaTLlA9Y=\ngolang.org/x/sys v0.6.0/go.mod h1:oPkhp1MJrh7nUepCBck5+mAzfO9JrbApNNgaTdGDITg=\ngolang.org/x/sys v0.42.0 h1:omrd2nAlyT5ESRdCLYdm3+fMfNFE/+Rf4bDIQImRJeo=\ngolang.org/x/sys v0.42.0/go.mod h1:4GL1E5IUh+htKOUEOaiffhrAeqysfVGipDYzABqnCmw=\ngolang.org/x/text v0.34.0 h1:oL/Qq0Kdaqxa1KbNeMKwQq0reLCCaFtqu2eNuSeNHbk=\ngolang.org/x/text v0.34.0/go.mod h1:homfLqTYRFyVYemLBFl5GgL/DWEiH5wcsQ5gSh1yziA=\ngopkg.in/check.v1 v0.0.0-20161208181325-20d25e280405 h1:yhCVgyC4o1eVCa2tZl7eS0r+SDo693bJlVdllGtEeKM=\ngopkg.in/check.v1 v0.0.0-20161208181325-20d25e280405/go.mod h1:Co6ibVJAznAaIkqp8huTwlJQCZ016jof/cbN4VW5Yz0=\ngopkg.in/yaml.v3 v3.0.1 h1:fxVm/GzAzEWqLHuvctI91KS9hhNmmWOoWu0XTYJS7CA=\ngopkg.in/yaml.v3 v3.0.1/go.mod h1:K4uyk7z7BCEPqu6E+C64Yfv1cQ7kz7rIZviUmN+EgEM=\n',
        }
