"""
Parameterized generator for GH385_consul_22798.

Source PR:    https://github.com/hashicorp/consul/pull/22798
Source Issue: N/A

Seed varies: renames 'binary' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH385_consul_22798'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH385_consul_22798'
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
                files[fpath] = files[fpath].replace('binary', 'binary' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH385_consul_22798',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'hashicorp/consul',
                "pr_number": 22798,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/hashicorp/consul/pull/22798",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            '.release/security-scan.hcl': '# Copyright (c) HashiCorp, Inc.\n# SPDX-License-Identifier: BUSL-1.1\n\n# These scan results are run as part of CRT workflows.\n\n# Un-triaged results will block release. See `security-scanner` docs for more\n# information on how to add `triage` config to unblock releases for specific results.\n# In most cases, we should not need to disable the entire scanner to unblock a release.\n\n# To run manually, install scanner and then from the repository root run\n# `SECURITY_SCANNER_CONFIG_FILE=.release/security-scan.hcl scan ...`\n# To scan a local container, add `local_daemon = true` to the `container` block below.\n# See `security-scanner` docs or run with `--help` for scan target syntax.\n\ncontainer {\n\tdependencies = true\n\tosv          = true\n\n\tsecrets {\n\t\tmatchers {\n\t\t\t// Use most of default list, minus Vault (`hashicorp`), which has experienced false positives.\n\t\t\t// See https://github.com/hashicorp/security-scanner/blob/v0.0.2/pkg/scanner/secrets.go#L130C2-L130C2\n\t\t\tknown = [\n\t\t\t\t// "hashicorp",\n\t\t\t\t"aws",\n\t\t\t\t"google",\n\t\t\t\t"slack",\n\t\t\t\t"github",\n\t\t\t\t"azure",\n\t\t\t\t"npm",\n\t\t\t]\n\t\t}\n\t}\n\n\t# Triage items that are _safe_ to ignore here. Note that this list should be\n\t# periodically cleaned up to remove items that are no longer found by the scanner.\n\ttriage {\n\t\tsuppress {\n\t\t\tvulnerabilities = [\n\t\t\t]\n\t\t\tpaths = [\n\t\t\t\t"internal/tools/proto-gen-rpc-glue/e2e/consul/*",\n\t\t\t\t"test/integration/connect/envoy/test-sds-server/*",\n\t\t\t\t"test/integration/consul-container/*",\n\t\t\t\t"testing/deployer/*",\n\t\t\t\t"test-integ/*",\n\t\t\t]\n\t\t}\n\t}\n}\n\nbinary {\n\tgo_modules   = true\n\tosv          = true\n\tgo_stdlib    = true\n\t# We can\'t enable npm for binary targets today because we don\'t yet embed the relevant file\n\t# (yarn.lock) in the Consul binary. This is something we may investigate in the future.\n\t\n\tsecrets {\n\t\tmatchers {\n\t\t\t// Use most of default list, minus Vault (`hashicorp`), which has experienced false positives.\n\t\t\t// See https://github.com/hashicorp/security-scanner/blob/v0.0.2/pkg/scanner/secrets.go#L130C2-L130C2\n\t\t\tknown = [\n\t\t\t\t// "hashicorp",\n\t\t\t\t"aws",\n\t\t\t\t"google",\n\t\t\t\t"slack",\n\t\t\t\t"github",\n\t\t\t\t"azure",\n\t\t\t\t"npm",\n\t\t\t]\n\t\t}\n\t}\n\n\t# Triage items that are _safe_ to ignore here. Note that this list should be\n\t# periodically cleaned up to remove items that are no longer found by the scanner.\n\ttriage {\n\t\tsuppress {\n\t\t\tvulnerabilities = [\n\t\t\t]\n\t\t\tpaths = [\n\t\t\t\t"internal/tools/proto-gen-rpc-glue/e2e/consul/*",\n\t\t\t\t"test/integration/connect/envoy/test-sds-server/*",\n\t\t\t\t"test/integration/consul-container/*",\n\t\t\t\t"testing/deployer/*",\n\t\t\t\t"test-integ/*",\n\t\t\t]\n\t\t}\n\t}\n}\n',
        }
