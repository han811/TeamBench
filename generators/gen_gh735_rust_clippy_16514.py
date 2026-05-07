"""
Parameterized generator for GH735_rust-clippy_16514.

Source PR:    https://github.com/rust-lang/rust-clippy/pull/16514
Source Issue: N/A

Seed varies: renames 'aborting' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH735_rust-clippy_16514'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH735_rust-clippy_16514'
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
                files[fpath] = files[fpath].replace('aborting', 'aborting' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH735_rust-clippy_16514',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'rust-lang/rust-clippy',
                "pr_number": 16514,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/rust-lang/rust-clippy/pull/16514",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'clippy_lints/src/doc/doc_paragraphs_missing_punctuation.rs': 'use rustc_errors::Applicability;\nuse rustc_lint::LateContext;\nuse rustc_resolve::rustdoc::main_body_opts;\n\nuse rustc_resolve::rustdoc::pulldown_cmark::{Event, Options, Parser, Tag, TagEnd};\n\nuse super::{DOC_PARAGRAPHS_MISSING_PUNCTUATION, Fragments};\n\nconst MSG: &str = "doc paragraphs should end with a terminal punctuation mark";\nconst PUNCTUATION_SUGGESTION: char = \'.\';\n\npub fn check(cx: &LateContext<\'_>, doc: &str, fragments: Fragments<\'_>) {\n    for missing_punctuation in is_missing_punctuation(doc) {\n        match missing_punctuation {\n            MissingPunctuation::Fixable(offset) => {\n                // This ignores `#[doc]` attributes, which we do not handle.\n                if let Some(span) = fragments.span(cx, offset..offset) {\n                    clippy_utils::diagnostics::span_lint_and_sugg(\n                        cx,\n                        DOC_PARAGRAPHS_MISSING_PUNCTUATION,\n                        span,\n                        MSG,\n                        "end the paragraph with some punctuation",\n                        PUNCTUATION_SUGGESTION.to_string(),\n                        Applicability::MaybeIncorrect,\n                    );\n                }\n            },\n            MissingPunctuation::Unfixable(offset) => {\n                // This ignores `#[doc]` attributes, which we do not handle.\n                if let Some(span) = fragments.span(cx, offset..offset) {\n                    clippy_utils::diagnostics::span_lint_and_help(\n                        cx,\n                        DOC_PARAGRAPHS_MISSING_PUNCTUATION,\n                        span,\n                        MSG,\n                        None,\n                        "end the paragraph with some punctuation",\n                    );\n                }\n            },\n        }\n    }\n}\n\n#[must_use]\n/// If punctuation is missing, returns the offset where new punctuation should be inserted.\nfn is_missing_punctuation(doc_string: &str) -> Vec<MissingPunctuation> {\n    // The colon is not exactly a terminal punctuation mark, but this is required for paragraphs that\n    // introduce a table or a list for example.\n    const TERMINAL_PUNCTUATION_MARKS: &[char] = &[\'.\', \'?\', \'!\', \'…\', \':\'];\n\n    let mut no_report_depth = 0;\n    let mut missing_punctuation = Vec::new();\n    let mut current_paragraph = None;\n    let mut current_event_is_missing_punctuation = false;\n\n    for (event, offset) in\n        Parser::new_ext(doc_string, main_body_opts() - Options::ENABLE_SMART_PUNCTUATION).into_offset_iter()\n    {\n        let last_event_was_missing_punctuation = current_event_is_missing_punctuation;\n        current_event_is_missing_punctuation = false;\n\n        match event {\n            Event::Start(Tag::FootnoteDefinition(_) | Tag::Heading { .. } | Tag::HtmlBlock | Tag::Table(_)) => {\n                no_report_depth += 1;\n            },\n            Event::Start(Tag::CodeBlock(..) | Tag::List(..)) => {\n                no_report_depth += 1;\n                if last_event_was_missing_punctuation {\n                    // Remove the error from the previous paragraph as it is followed by a code\n                    // block or a list.\n                    missing_punctuation.pop();\n                }\n            },\n            Event::End(TagEnd::FootnoteDefinition) => {\n                no_report_depth -= 1;\n            },\n            Event::End(\n                TagEnd::CodeBlock | TagEnd::Heading(_) | TagEnd::HtmlBlock | TagEnd::List(_) | TagEnd::Table,\n            ) => {\n                no_report_depth -= 1;\n                current_paragraph = None;\n            },\n            Event::InlineHtml(_) | Event::Start(Tag::Image { .. }) | Event::End(TagEnd::Image) => {\n                current_paragraph = None;\n            },\n            Event::End(TagEnd::Paragraph) => {\n                if let Some(mp) = current_paragraph {\n                    missing_punctuation.push(mp);\n                    current_event_is_missing_punctuation = true;\n                }\n            },\n            Event::Code(..) | Event::Start(Tag::Link { .. }) | Event::End(TagEnd::Link)\n                if no_report_depth == 0 && !offset.is_empty() =>\n            {\n                if doc_string[..offset.end]\n                    .trim_end()\n                    .ends_with(TERMINAL_PUNCTUATION_MARKS)\n                {\n                    current_paragraph = None;\n                } else {\n                    current_paragraph = Some(MissingPunctuation::Fixable(offset.end));\n                }\n            },\n            Event::Text(..) if no_report_depth == 0 && !offset.is_empty() => {\n                let trimmed = doc_string[..offset.end].trim_end();\n                if trimmed.ends_with(TERMINAL_PUNCTUATION_MARKS) {\n                    current_paragraph = None;\n                } else if let Some(t) = trimmed.strip_suffix(|c| c == \')\' || c == \'"\') {\n                    if t.ends_with(TERMINAL_PUNCTUATION_MARKS) {\n                        // Avoid false positives.\n                        current_paragraph = None;\n                    } else {\n                        current_paragraph = Some(MissingPunctuation::Unfixable(offset.end));\n                    }\n                } else {\n                    current_paragraph = Some(MissingPunctuation::Fixable(offset.end));\n                }\n            },\n            _ => {},\n        }\n    }\n\n    missing_punctuation\n}\n\n#[derive(Debug, Copy, Clone, PartialEq, Eq)]\nenum MissingPunctuation {\n    Fixable(usize),\n    Unfixable(usize),\n}\n',
            'tests/ui/doc/doc_paragraphs_missing_punctuation_emoji.rs': '#![feature(custom_inner_attributes)]\n#![rustfmt::skip]\n#![warn(clippy::doc_paragraphs_missing_punctuation)]\n//@no-rustfix\n\nenum EmojiTrailers {\n    /// Sometimes the doc comment ends with an emoji! 😅\n    ExistingPunctuationBeforeEmoji,\n    /// But it may still be missing punctuation 😢\n    //~^ doc_paragraphs_missing_punctuation\n    MissingPunctuationBeforeEmoji,\n}\n',
            'tests/ui/doc/doc_paragraphs_missing_punctuation_emoji.stderr': 'error: doc paragraphs should end with a terminal punctuation mark\n  --> tests/ui/doc/doc_paragraphs_missing_punctuation_emoji.rs:9:50\n   |\nLL |     /// But it may still be missing punctuation 😢\n   |                                                   ^ help: end the paragraph with some punctuation: `.`\n   |\n   = note: `-D clippy::doc-paragraphs-missing-punctuation` implied by `-D warnings`\n   = help: to override `-D warnings` add `#[allow(clippy::doc_paragraphs_missing_punctuation)]`\n\nerror: aborting due to 1 previous error\n\n',
        }
