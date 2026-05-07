"""
Parameterized generator for GH669_deno_32853.

Source PR:    https://github.com/denoland/deno/pull/32853
Source Issue: N/A

Seed varies: renames 'about' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH669_deno_32853'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH669_deno_32853'
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
            task_id='GH669_deno_32853',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'denoland/deno',
                "pr_number": 32853,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/denoland/deno/pull/32853",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'tests/integration/pm_tests.rs': '// Copyright 2018-2026 the Deno authors. MIT license.\n\nuse serde_json::json;\nuse test_util::TestContextBuilder;\nuse test_util::assert_contains;\nuse test_util::env_vars_for_jsr_npm_tests;\nuse test_util::pty::Pty;\nuse test_util::test;\n\n#[test]\nfn add_basic() {\n  let starting_deno_json = json!({\n    "name": "@foo/bar",\n    "version": "1.0.0",\n    "exports": "./mod.ts",\n  });\n  let context = pm_context_builder().build();\n  let temp_dir = context.temp_dir().path();\n  temp_dir.join("deno.json").write_json(&starting_deno_json);\n\n  let output = context.new_command().args("add jsr:@denotest/add").run();\n  output.assert_exit_code(0);\n  let output = output.combined_output();\n  assert_contains!(output, "Add jsr:@denotest/add");\n  temp_dir.join("deno.json").assert_matches_json(json!({\n    "name": "@foo/bar",\n    "version": "1.0.0",\n    "exports": "./mod.ts",\n    "imports": {\n      "@denotest/add": "jsr:@denotest/add@^1.0.0"\n    }\n  }));\n}\n\n#[test]\nfn add_basic_no_deno_json() {\n  let context = pm_context_builder().build();\n  let temp_dir = context.temp_dir().path();\n\n  let output = context.new_command().args("add jsr:@denotest/add").run();\n  output.assert_exit_code(0);\n  let output = output.combined_output();\n  assert_contains!(output, "Add jsr:@denotest/add");\n  // Don\'t use `assert_matches_json` to ensure the file is properly formatted.\n  let expected = r#"{\n  "imports": {\n    "@denotest/add": "jsr:@denotest/add@^1.0.0"\n  }\n}\n"#;\n  temp_dir.join("deno.json").assert_matches_text(expected);\n}\n\n#[test]\nfn add_basic_with_empty_deno_json() {\n  let context = pm_context_builder().build();\n  let temp_dir = context.temp_dir();\n  temp_dir.write("deno.json", "");\n\n  let output = context.new_command().args("add jsr:@denotest/add").run();\n  output.assert_exit_code(0);\n  let output = output.combined_output();\n  assert_contains!(output, "Add jsr:@denotest/add");\n  temp_dir\n    .path()\n    .join("deno.json")\n    .assert_matches_json(json!({\n      "imports": {\n        "@denotest/add": "jsr:@denotest/add@^1.0.0"\n      }\n    }));\n}\n\n#[test]\nfn add_version_contraint() {\n  let context = pm_context_builder().build();\n  let temp_dir = context.temp_dir().path();\n\n  let output = context.new_command().args("add jsr:@denotest/add@1").run();\n  output.assert_exit_code(0);\n  let output = output.combined_output();\n  assert_contains!(output, "Add jsr:@denotest/add");\n  temp_dir.join("deno.json").assert_matches_json(json!({\n    "imports": {\n      "@denotest/add": "jsr:@denotest/add@^1.0.0"\n    }\n  }));\n}\n\n#[test]\nfn add_tilde() {\n  let context = pm_context_builder().build();\n  let temp_dir = context.temp_dir().path();\n\n  let output = context.new_command().args("add jsr:@denotest/add@~1").run();\n  output.assert_exit_code(0);\n  let output = output.combined_output();\n  assert_contains!(output, "Add jsr:@denotest/add");\n  temp_dir.join("deno.json").assert_matches_json(json!({\n    "imports": {\n      "@denotest/add": "jsr:@denotest/add@~1.0.0"\n    }\n  }));\n}\n\n#[test]\nfn add_save_exact() {\n  let context = pm_context_builder().build();\n  let temp_dir = context.temp_dir().path();\n\n  let output = context\n    .new_command()\n    .args("add jsr:@denotest/add --save-exact")\n    .run();\n  output.assert_exit_code(0);\n  let output = output.combined_output();\n  assert_contains!(output, "Add jsr:@denotest/add");\n  temp_dir.join("deno.json").assert_matches_json(json!({\n    "imports": {\n      "@denotest/add": "jsr:@denotest/add@1.0.0"\n    }\n  }));\n}\n\n#[test]\nfn add_exact_alias() {\n  let context = pm_context_builder().build();\n  let temp_dir = context.temp_dir().path();\n\n  let output = context\n    .new_command()\n    .args("add jsr:@denotest/add --exact")\n    .run();\n  output.assert_exit_code(0);\n  let output = output.combined_output();\n  assert_contains!(output, "Add jsr:@denotest/add");\n  temp_dir.join("deno.json").assert_matches_json(json!({\n    "imports": {\n      "@denotest/add": "jsr:@denotest/add@1.0.0"\n    }\n  }));\n}\n\n#[test]\nfn add_multiple() {\n  let starting_deno_json = json!({\n    "name": "@foo/bar",\n    "version": "1.0.0",\n    "exports": "./mod.ts",\n  });\n  let context = pm_context_builder().build();\n  let temp_dir = context.temp_dir().path();\n  temp_dir.join("deno.json").write_json(&starting_deno_json);\n\n  let output = context\n    .new_command()\n    .args("add jsr:@denotest/add jsr:@denotest/subset-type-graph")\n    .run();\n  output.assert_exit_code(0);\n  let output = output.combined_output();\n  assert_contains!(output, "Add jsr:@denotest/add");\n  temp_dir.join("deno.json").assert_matches_json(json!({\n    "name": "@foo/bar",\n    "version": "1.0.0",\n    "exports": "./mod.ts",\n    "imports": {\n      "@denotest/add": "jsr:@denotest/add@^1.0.0",\n      "@denotest/subset-type-graph": "jsr:@denotest/subset-type-graph@^0.1.0"\n    }\n  }));\n}\n\n#[test]\nfn add_npm() {\n  let context = pm_context_builder().build();\n  let temp_dir = context.temp_dir().path();\n\n  let output = context.new_command().args("add npm:chalk@4.1").run();\n  output.assert_exit_code(0);\n  let output = output.combined_output();\n  assert_contains!(output, "Add npm:chalk");\n  temp_dir.join("deno.json").assert_matches_json(json!({\n    "imports": {\n      "chalk": "npm:chalk@^4.1.2"\n    }\n  }));\n}\n\nfn pm_context_builder() -> TestContextBuilder {\n  TestContextBuilder::new()\n    .use_http_server()\n    .envs(env_vars_for_jsr_npm_tests())\n    .use_temp_cwd()\n}\n\n#[test(flaky)]\nfn approve_scripts_basic() {\n  if !Pty::is_supported() {\n    return;\n  }\n  let context = pm_context_builder().build();\n  context\n    .temp_dir()\n    .write("deno.json", r#"{"nodeModulesDir": "manual"}"#);\n  context\n    .new_command()\n    .args("install npm:@denotest/node-lifecycle-scripts@1.0.0")\n    .run()\n    .skip_output_check();\n  context\n    .new_command()\n    .args("approve-scripts")\n    .with_pty(|mut pty| {\n      pty.expect("Select which packages to approve lifecycle scripts for");\n      pty.expect("@denotest/node-lifecycle-scripts@1.0.0");\n      pty.write_line(" ");\n      pty.write_line("\\r\\n");\n      pty.expect("Approved npm:@denotest/node-lifecycle-scripts@1.0.0");\n      pty.expect("Ran build script npm:@denotest/node-lifecycle-scripts@1.0.0");\n    });\n  context\n    .temp_dir()\n    .path()\n    .join("deno.json")\n    .assert_matches_json(json!({\n      "nodeModulesDir": "manual",\n      "imports": {\n        "@denotest/node-lifecycle-scripts": "npm:@denotest/node-lifecycle-scripts@1.0.0"\n      },\n      "allowScripts": ["npm:@denotest/node-lifecycle-scripts@1.0.0"],\n    }));\n  context\n    .temp_dir()\n    .path()\n    .join("install.txt")\n    .assert_matches_text("Installed by @denotest/node-lifecycle-scripts!");\n}\n\n#[test(flaky)]\nfn approve_scripts_deny_some() {\n  if !Pty::is_supported() {\n    return;\n  }\n  let context = pm_context_builder().build();\n  context\n    .temp_dir()\n    .write("deno.json", r#"{"nodeModulesDir": "manual"}"#);\n  context\n    .new_command()\n    .args("install npm:@denotest/node-lifecycle-scripts@1.0.0 npm:@denotest/print-npm-user-agent@1.0.0")\n    .run()\n    .skip_output_check();\n  context\n    .new_command()\n    .args("approve-scripts")\n    .with_pty(|mut pty| {\n      pty.expect("Select which packages to approve lifecycle scripts for");\n      pty.expect("@denotest/node-lifecycle-scripts@1.0.0");\n      pty.expect("@denotest/print-npm-user-agent@1.0.0");\n      pty.write_line(" ");\n      pty.write_line("\\r\\n");\n      pty.expect("Denied npm:@denotest/print-npm-user-agent@1.0.0");\n      pty.expect("Approved npm:@denotest/node-lifecycle-scripts@1.0.0");\n      pty.expect("Ran build script npm:@denotest/node-lifecycle-scripts@1.0.0");\n    });\n  context.temp_dir().path().join("deno.json").assert_matches_json(json!({\n    "nodeModulesDir": "manual",\n    "imports": {\n      "@denotest/node-lifecycle-scripts": "npm:@denotest/node-lifecycle-scripts@1.0.0",\n      "@denotest/print-npm-user-agent": "npm:@denotest/print-npm-user-agent@1.0.0"\n    },\n    "allowScripts": {\n      "allow": ["npm:@denotest/node-lifecycle-scripts@1.0.0"],\n      "deny": ["npm:@denotest/print-npm-user-agent@1.0.0"]\n    },\n  }));\n  context\n    .temp_dir()\n    .path()\n    .join("install.txt")\n    .assert_matches_text("Installed by @denotest/node-lifecycle-scripts!");\n}\n',
        }
