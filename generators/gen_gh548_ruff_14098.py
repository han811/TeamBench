"""
Parameterized generator for GH548_ruff_14098.

Source PR:    https://github.com/astral-sh/ruff/pull/14098
Source Issue: https://github.com/astral-sh/ruff/issues/13807

Seed varies: renames 'argument' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH548_ruff_14098'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH548_ruff_14098'
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
                files[fpath] = files[fpath].replace('argument', 'argument' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH548_ruff_14098',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'astral-sh/ruff',
                "pr_number": 14098,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/astral-sh/ruff/pull/14098",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'crates/ruff_linter/resources/test/fixtures/refurb/FURB157.py': 'import decimal\nfrom decimal import Decimal\n\n# Errors\nDecimal("0")\nDecimal("-42")\nDecimal(float("Infinity"))\nDecimal(float("-Infinity"))\nDecimal(float("inf"))\nDecimal(float("-inf"))\nDecimal(float("nan"))\ndecimal.Decimal("0")\n\n# OK\nDecimal(0)\nDecimal("Infinity")\ndecimal.Decimal(0)\n',
            'crates/ruff_linter/src/rules/refurb/rules/verbose_decimal_constructor.rs': 'use ruff_diagnostics::{Diagnostic, Edit, Fix, FixAvailability, Violation};\nuse ruff_macros::{derive_message_formats, violation};\nuse ruff_python_ast::{self as ast, Expr};\nuse ruff_python_trivia::PythonWhitespace;\nuse ruff_text_size::Ranged;\n\nuse crate::checkers::ast::Checker;\n\n/// ## What it does\n/// Checks for unnecessary string literal or float casts in `Decimal`\n/// constructors.\n///\n/// ## Why is this bad?\n/// The `Decimal` constructor accepts a variety of arguments, including\n/// integers, floats, and strings. However, it\'s not necessary to cast\n/// integer literals to strings when passing them to the `Decimal`.\n///\n/// Similarly, `Decimal` accepts `inf`, `-inf`, and `nan` as string literals,\n/// so there\'s no need to wrap those values in a `float` call when passing\n/// them to the `Decimal` constructor.\n///\n/// Prefer the more concise form of argument passing for `Decimal`\n/// constructors, as it\'s more readable and idiomatic.\n///\n/// ## Example\n/// ```python\n/// Decimal("0")\n/// Decimal(float("Infinity"))\n/// ```\n///\n/// Use instead:\n/// ```python\n/// Decimal(0)\n/// Decimal("Infinity")\n/// ```\n///\n/// ## References\n/// - [Python documentation: `decimal`](https://docs.python.org/3/library/decimal.html)\n#[violation]\npub struct VerboseDecimalConstructor {\n    replacement: String,\n}\n\nimpl Violation for VerboseDecimalConstructor {\n    const FIX_AVAILABILITY: FixAvailability = FixAvailability::Always;\n\n    #[derive_message_formats]\n    fn message(&self) -> String {\n        "Verbose expression in `Decimal` constructor".to_string()\n    }\n\n    fn fix_title(&self) -> Option<String> {\n        let VerboseDecimalConstructor { replacement } = self;\n        Some(format!("Replace with `{replacement}`"))\n    }\n}\n\n/// FURB157\npub(crate) fn verbose_decimal_constructor(checker: &mut Checker, call: &ast::ExprCall) {\n    if !checker\n        .semantic()\n        .resolve_qualified_name(&call.func)\n        .is_some_and(|qualified_name| matches!(qualified_name.segments(), ["decimal", "Decimal"]))\n    {\n        return;\n    }\n\n    // Decimal accepts arguments of the form: `Decimal(value=\'0\', context=None)`\n    let Some(value) = call.arguments.find_argument("value", 0) else {\n        return;\n    };\n\n    let diagnostic = match value {\n        Expr::StringLiteral(ast::ExprStringLiteral {\n            value: str_literal, ..\n        }) => {\n            // Parse the inner string as an integer.\n            let trimmed = str_literal.to_str().trim_whitespace();\n\n            // Extract the unary sign, if any.\n            let (unary, rest) = if let Some(trimmed) = trimmed.strip_prefix(\'+\') {\n                ("+", trimmed)\n            } else if let Some(trimmed) = trimmed.strip_prefix(\'-\') {\n                ("-", trimmed)\n            } else {\n                ("", trimmed)\n            };\n\n            // Skip leading zeros.\n            let rest = rest.trim_start_matches(\'0\');\n\n            // Verify that the rest of the string is a valid integer.\n            if !rest.chars().all(|c| c.is_ascii_digit()) {\n                return;\n            };\n\n            // If all the characters are zeros, then the value is zero.\n            let rest = if rest.is_empty() { "0" } else { rest };\n\n            let replacement = format!("{unary}{rest}");\n            let mut diagnostic = Diagnostic::new(\n                VerboseDecimalConstructor {\n                    replacement: replacement.clone(),\n                },\n                value.range(),\n            );\n\n            diagnostic.set_fix(Fix::safe_edit(Edit::range_replacement(\n                replacement,\n                value.range(),\n            )));\n\n            diagnostic\n        }\n        Expr::Call(ast::ExprCall {\n            func, arguments, ..\n        }) => {\n            // Must be a call to the `float` builtin.\n            if !checker.semantic().match_builtin_expr(func, "float") {\n                return;\n            };\n\n            // Must have exactly one argument, which is a string literal.\n            if arguments.keywords.len() != 0 {\n                return;\n            };\n            let [float] = arguments.args.as_ref() else {\n                return;\n            };\n            let Some(float) = float.as_string_literal_expr() else {\n                return;\n            };\n            if !matches!(\n                float.value.to_str().to_lowercase().as_str(),\n                "inf" | "-inf" | "infinity" | "-infinity" | "nan"\n            ) {\n                return;\n            }\n\n            let replacement = checker.locator().slice(float).to_string();\n            let mut diagnostic = Diagnostic::new(\n                VerboseDecimalConstructor {\n                    replacement: replacement.clone(),\n                },\n                value.range(),\n            );\n\n            diagnostic.set_fix(Fix::safe_edit(Edit::range_replacement(\n                replacement,\n                value.range(),\n            )));\n\n            diagnostic\n        }\n        _ => {\n            return;\n        }\n    };\n\n    checker.diagnostics.push(diagnostic);\n}\n',
            'crates/ruff_linter/src/rules/refurb/snapshots/ruff_linter__rules__refurb__tests__FURB157_FURB157.py.snap': '---\nsource: crates/ruff_linter/src/rules/refurb/mod.rs\n---\nFURB157.py:5:9: FURB157 [*] Verbose expression in `Decimal` constructor\n  |\n4 | # Errors\n5 | Decimal("0")\n  |         ^^^ FURB157\n6 | Decimal("-42")\n7 | Decimal(float("Infinity"))\n  |\n  = help: Replace with `0`\n\nℹ Safe fix\n2 2 | from decimal import Decimal\n3 3 | \n4 4 | # Errors\n5   |-Decimal("0")\n  5 |+Decimal(0)\n6 6 | Decimal("-42")\n7 7 | Decimal(float("Infinity"))\n8 8 | Decimal(float("-Infinity"))\n\nFURB157.py:6:9: FURB157 [*] Verbose expression in `Decimal` constructor\n  |\n4 | # Errors\n5 | Decimal("0")\n6 | Decimal("-42")\n  |         ^^^^^ FURB157\n7 | Decimal(float("Infinity"))\n8 | Decimal(float("-Infinity"))\n  |\n  = help: Replace with `-42`\n\nℹ Safe fix\n3 3 | \n4 4 | # Errors\n5 5 | Decimal("0")\n6   |-Decimal("-42")\n  6 |+Decimal(-42)\n7 7 | Decimal(float("Infinity"))\n8 8 | Decimal(float("-Infinity"))\n9 9 | Decimal(float("inf"))\n\nFURB157.py:7:9: FURB157 [*] Verbose expression in `Decimal` constructor\n  |\n5 | Decimal("0")\n6 | Decimal("-42")\n7 | Decimal(float("Infinity"))\n  |         ^^^^^^^^^^^^^^^^^ FURB157\n8 | Decimal(float("-Infinity"))\n9 | Decimal(float("inf"))\n  |\n  = help: Replace with `"Infinity"`\n\nℹ Safe fix\n4 4 | # Errors\n5 5 | Decimal("0")\n6 6 | Decimal("-42")\n7   |-Decimal(float("Infinity"))\n  7 |+Decimal("Infinity")\n8 8 | Decimal(float("-Infinity"))\n9 9 | Decimal(float("inf"))\n10 10 | Decimal(float("-inf"))\n\nFURB157.py:8:9: FURB157 [*] Verbose expression in `Decimal` constructor\n   |\n 6 | Decimal("-42")\n 7 | Decimal(float("Infinity"))\n 8 | Decimal(float("-Infinity"))\n   |         ^^^^^^^^^^^^^^^^^^ FURB157\n 9 | Decimal(float("inf"))\n10 | Decimal(float("-inf"))\n   |\n   = help: Replace with `"-Infinity"`\n\nℹ Safe fix\n5 5 | Decimal("0")\n6 6 | Decimal("-42")\n7 7 | Decimal(float("Infinity"))\n8   |-Decimal(float("-Infinity"))\n  8 |+Decimal("-Infinity")\n9 9 | Decimal(float("inf"))\n10 10 | Decimal(float("-inf"))\n11 11 | Decimal(float("nan"))\n\nFURB157.py:9:9: FURB157 [*] Verbose expression in `Decimal` constructor\n   |\n 7 | Decimal(float("Infinity"))\n 8 | Decimal(float("-Infinity"))\n 9 | Decimal(float("inf"))\n   |         ^^^^^^^^^^^^ FURB157\n10 | Decimal(float("-inf"))\n11 | Decimal(float("nan"))\n   |\n   = help: Replace with `"inf"`\n\nℹ Safe fix\n6  6  | Decimal("-42")\n7  7  | Decimal(float("Infinity"))\n8  8  | Decimal(float("-Infinity"))\n9     |-Decimal(float("inf"))\n   9  |+Decimal("inf")\n10 10 | Decimal(float("-inf"))\n11 11 | Decimal(float("nan"))\n12 12 | decimal.Decimal("0")\n\nFURB157.py:10:9: FURB157 [*] Verbose expression in `Decimal` constructor\n   |\n 8 | Decimal(float("-Infinity"))\n 9 | Decimal(float("inf"))\n10 | Decimal(float("-inf"))\n   |         ^^^^^^^^^^^^^ FURB157\n11 | Decimal(float("nan"))\n12 | decimal.Decimal("0")\n   |\n   = help: Replace with `"-inf"`\n\nℹ Safe fix\n7  7  | Decimal(float("Infinity"))\n8  8  | Decimal(float("-Infinity"))\n9  9  | Decimal(float("inf"))\n10    |-Decimal(float("-inf"))\n   10 |+Decimal("-inf")\n11 11 | Decimal(float("nan"))\n12 12 | decimal.Decimal("0")\n13 13 | \n\nFURB157.py:11:9: FURB157 [*] Verbose expression in `Decimal` constructor\n   |\n 9 | Decimal(float("inf"))\n10 | Decimal(float("-inf"))\n11 | Decimal(float("nan"))\n   |         ^^^^^^^^^^^^ FURB157\n12 | decimal.Decimal("0")\n   |\n   = help: Replace with `"nan"`\n\nℹ Safe fix\n8  8  | Decimal(float("-Infinity"))\n9  9  | Decimal(float("inf"))\n10 10 | Decimal(float("-inf"))\n11    |-Decimal(float("nan"))\n   11 |+Decimal("nan")\n12 12 | decimal.Decimal("0")\n13 13 | \n14 14 | # OK\n\nFURB157.py:12:17: FURB157 [*] Verbose expression in `Decimal` constructor\n   |\n10 | Decimal(float("-inf"))\n11 | Decimal(float("nan"))\n12 | decimal.Decimal("0")\n   |                 ^^^ FURB157\n13 | \n14 | # OK\n   |\n   = help: Replace with `0`\n\nℹ Safe fix\n9  9  | Decimal(float("inf"))\n10 10 | Decimal(float("-inf"))\n11 11 | Decimal(float("nan"))\n12    |-decimal.Decimal("0")\n   12 |+decimal.Decimal(0)\n13 13 | \n14 14 | # OK\n15 15 | Decimal(0)\n',
        }
