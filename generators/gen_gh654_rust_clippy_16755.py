"""
Parameterized generator for GH654_rust-clippy_16755.

Source PR:    https://github.com/rust-lang/rust-clippy/pull/16755
Source Issue: N/A

Seed varies: renames 'check_expr' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH654_rust-clippy_16755'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH654_rust-clippy_16755'
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
                files[fpath] = files[fpath].replace('check_expr', 'check_expr' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH654_rust-clippy_16755',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'rust-lang/rust-clippy',
                "pr_number": 16755,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/rust-lang/rust-clippy/pull/16755",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'clippy_lints/src/manual_is_ascii_check.rs': 'use clippy_config::Conf;\nuse clippy_utils::diagnostics::span_lint_and_then;\nuse clippy_utils::macros::matching_root_macro_call;\nuse clippy_utils::msrvs::{self, Msrv};\nuse clippy_utils::res::MaybeResPath;\nuse clippy_utils::sugg::Sugg;\nuse clippy_utils::{higher, is_in_const_context, peel_ref_operators, sym};\nuse rustc_ast::LitKind::{Byte, Char};\nuse rustc_ast::ast::RangeLimits;\nuse rustc_errors::Applicability;\nuse rustc_hir::{Expr, ExprKind, Lit, Node, Param, PatExpr, PatExprKind, PatKind, RangeEnd};\nuse rustc_lint::{LateContext, LateLintPass};\nuse rustc_middle::ty::{self, Ty};\nuse rustc_session::impl_lint_pass;\nuse rustc_span::Span;\n\ndeclare_clippy_lint! {\n    /// ### What it does\n    /// Suggests to use dedicated built-in methods,\n    /// `is_ascii_(lowercase|uppercase|digit|hexdigit)` for checking on corresponding\n    /// ascii range\n    ///\n    /// ### Why is this bad?\n    /// Using the built-in functions is more readable and makes it\n    /// clear that it\'s not a specific subset of characters, but all\n    /// ASCII (lowercase|uppercase|digit|hexdigit) characters.\n    /// ### Example\n    /// ```no_run\n    /// fn main() {\n    ///     assert!(matches!(\'x\', \'a\'..=\'z\'));\n    ///     assert!(matches!(b\'X\', b\'A\'..=b\'Z\'));\n    ///     assert!(matches!(\'2\', \'0\'..=\'9\'));\n    ///     assert!(matches!(\'x\', \'A\'..=\'Z\' | \'a\'..=\'z\'));\n    ///     assert!(matches!(\'C\', \'0\'..=\'9\' | \'a\'..=\'f\' | \'A\'..=\'F\'));\n    ///\n    ///     (\'0\'..=\'9\').contains(&\'0\');\n    ///     (\'a\'..=\'z\').contains(&\'a\');\n    ///     (\'A\'..=\'Z\').contains(&\'A\');\n    /// }\n    /// ```\n    /// Use instead:\n    /// ```no_run\n    /// fn main() {\n    ///     assert!(\'x\'.is_ascii_lowercase());\n    ///     assert!(b\'X\'.is_ascii_uppercase());\n    ///     assert!(\'2\'.is_ascii_digit());\n    ///     assert!(\'x\'.is_ascii_alphabetic());\n    ///     assert!(\'C\'.is_ascii_hexdigit());\n    ///\n    ///     \'0\'.is_ascii_digit();\n    ///     \'a\'.is_ascii_lowercase();\n    ///     \'A\'.is_ascii_uppercase();\n    /// }\n    /// ```\n    #[clippy::version = "1.67.0"]\n    pub MANUAL_IS_ASCII_CHECK,\n    style,\n    "use dedicated method to check ascii range"\n}\n\nimpl_lint_pass!(ManualIsAsciiCheck => [MANUAL_IS_ASCII_CHECK]);\n\npub struct ManualIsAsciiCheck {\n    msrv: Msrv,\n}\n\nimpl ManualIsAsciiCheck {\n    pub fn new(conf: &\'static Conf) -> Self {\n        Self { msrv: conf.msrv }\n    }\n}\n\n#[derive(Debug, PartialEq)]\nenum CharRange {\n    /// \'a\'..=\'z\' | b\'a\'..=b\'z\'\n    LowerChar,\n    /// \'A\'..=\'Z\' | b\'A\'..=b\'Z\'\n    UpperChar,\n    /// `AsciiLower` | `AsciiUpper`\n    FullChar,\n    /// \'0..=9\'\n    Digit,\n    /// \'a..=f\'\n    LowerHexLetter,\n    /// \'A..=F\'\n    UpperHexLetter,\n    /// \'0..=9\' | \'a..=f\' | \'A..=F\'\n    HexDigit,\n    Otherwise,\n}\n\nimpl<\'tcx> LateLintPass<\'tcx> for ManualIsAsciiCheck {\n    fn check_expr(&mut self, cx: &LateContext<\'tcx>, expr: &\'tcx Expr<\'_>) {\n        if !self.msrv.meets(cx, msrvs::IS_ASCII_DIGIT) {\n            return;\n        }\n\n        if is_in_const_context(cx) && !self.msrv.meets(cx, msrvs::IS_ASCII_DIGIT_CONST) {\n            return;\n        }\n\n        let (arg, span, range) = if let Some(macro_call) = matching_root_macro_call(cx, expr.span, sym::matches_macro)\n            && let ExprKind::Match(recv, [arm, ..], _) = expr.kind\n        {\n            let recv = peel_ref_operators(cx, recv);\n            let range = check_pat(&arm.pat.kind);\n            (recv, macro_call.span, range)\n        } else if let ExprKind::MethodCall(path, receiver, [arg], ..) = expr.kind\n            && path.ident.name == sym::contains\n            && let Some(higher::Range {\n                start: Some(start),\n                end: Some(end),\n                limits: RangeLimits::Closed,\n                span: _,\n            }) = higher::Range::hir(cx, receiver)\n            && !matches!(cx.typeck_results().expr_ty(arg).peel_refs().kind(), ty::Param(_))\n        {\n            let arg = peel_ref_operators(cx, arg);\n            let range = check_expr_range(start, end);\n            (arg, expr.span, range)\n        } else {\n            return;\n        };\n\n        let ty_sugg = get_ty_sugg(cx, arg);\n        check_is_ascii(cx, span, arg, &range, ty_sugg);\n    }\n}\n\nfn get_ty_sugg<\'tcx>(cx: &LateContext<\'tcx>, arg: &Expr<\'_>) -> Option<(Span, Ty<\'tcx>)> {\n    let local_hid = arg.res_local_id()?;\n    if let Node::Param(Param { ty_span, span, .. }) = cx.tcx.parent_hir_node(local_hid)\n        // `ty_span` and `span` are the same for inferred type, thus a type suggestion must be given\n        && ty_span == span\n    {\n        let arg_type = cx.typeck_results().expr_ty(arg);\n        return Some((*ty_span, arg_type));\n    }\n    None\n}\n\nfn check_is_ascii(\n    cx: &LateContext<\'_>,\n    span: Span,\n    recv: &Expr<\'_>,\n    range: &CharRange,\n    ty_sugg: Option<(Span, Ty<\'_>)>,\n) {\n    let sugg = match range {\n        CharRange::UpperChar => "is_ascii_uppercase",\n        CharRange::LowerChar => "is_ascii_lowercase",\n        CharRange::FullChar => "is_ascii_alphabetic",\n        CharRange::Digit => "is_ascii_digit",\n        CharRange::HexDigit => "is_ascii_hexdigit",\n        CharRange::Otherwise | CharRange::LowerHexLetter | CharRange::UpperHexLetter => return,\n    };\n    let mut app = Applicability::MachineApplicable;\n    let recv = Sugg::hir_with_context(cx, recv, span.ctxt(), "_", &mut app).maybe_paren();\n    let mut suggestion = vec![(span, format!("{recv}.{sugg}()"))];\n    if let Some((ty_span, ty)) = ty_sugg {\n        suggestion.push((ty_span, format!("{recv}: {ty}")));\n    }\n\n    span_lint_and_then(\n        cx,\n        MANUAL_IS_ASCII_CHECK,\n        span,\n        "manual check for common ascii range",\n        |diag| {\n            diag.multipart_suggestion("try", suggestion, app);\n        },\n    );\n}\n\nfn check_pat(pat_kind: &PatKind<\'_>) -> CharRange {\n    match pat_kind {\n        PatKind::Or(pats) => {\n            let ranges = pats.iter().map(|p| check_pat(&p.kind)).collect::<Vec<_>>();\n\n            if ranges.len() == 2 && ranges.contains(&CharRange::UpperChar) && ranges.contains(&CharRange::LowerChar) {\n                CharRange::FullChar\n            } else if ranges.len() == 3\n                && ranges.contains(&CharRange::Digit)\n                && ranges.contains(&CharRange::LowerHexLetter)\n                && ranges.contains(&CharRange::UpperHexLetter)\n            {\n                CharRange::HexDigit\n            } else {\n                CharRange::Otherwise\n            }\n        },\n        PatKind::Range(Some(start), Some(end), RangeEnd::Included) => check_range(start, end),\n        _ => CharRange::Otherwise,\n    }\n}\n\nfn check_expr_range(start: &Expr<\'_>, end: &Expr<\'_>) -> CharRange {\n    if let ExprKind::Lit(start_lit) = &start.kind\n        && let ExprKind::Lit(end_lit) = &end.kind\n    {\n        check_lit_range(start_lit, end_lit)\n    } else {\n        CharRange::Otherwise\n    }\n}\n\nfn check_range(start: &PatExpr<\'_>, end: &PatExpr<\'_>) -> CharRange {\n    if let PatExprKind::Lit {\n        lit: start_lit,\n        negated: false,\n    } = &start.kind\n        && let PatExprKind::Lit {\n            lit: end_lit,\n            negated: false,\n        } = &end.kind\n    {\n        check_lit_range(start_lit, end_lit)\n    } else {\n        CharRange::Otherwise\n    }\n}\n\nfn check_lit_range(start_lit: &Lit, end_lit: &Lit) -> CharRange {\n    match (&start_lit.node, &end_lit.node) {\n        (Char(\'a\'), Char(\'z\')) | (Byte(b\'a\'), Byte(b\'z\')) => CharRange::LowerChar,\n        (Char(\'A\'), Char(\'Z\')) | (Byte(b\'A\'), Byte(b\'Z\')) => CharRange::UpperChar,\n        (Char(\'a\'), Char(\'f\')) | (Byte(b\'a\'), Byte(b\'f\')) => CharRange::LowerHexLetter,\n        (Char(\'A\'), Char(\'F\')) | (Byte(b\'A\'), Byte(b\'F\')) => CharRange::UpperHexLetter,\n        (Char(\'0\'), Char(\'9\')) | (Byte(b\'0\'), Byte(b\'9\')) => CharRange::Digit,\n        _ => CharRange::Otherwise,\n    }\n}\n',
        }
