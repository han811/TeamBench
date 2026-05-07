"""
Parameterized generator for GH842_rust-clippy_16636.

Source PR:    https://github.com/rust-lang/rust-clippy/pull/16636
Source Issue: N/A

Seed varies: renames 'as_local' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH842_rust-clippy_16636'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH842_rust-clippy_16636'
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
                files[fpath] = files[fpath].replace('as_local', 'as_local' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH842_rust-clippy_16636',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'rust-lang/rust-clippy',
                "pr_number": 16636,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/rust-lang/rust-clippy/pull/16636",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'clippy_utils/src/mir/mod.rs': "use rustc_hir::{Expr, HirId};\nuse rustc_index::bit_set::DenseBitSet;\nuse rustc_middle::mir::visit::{MutatingUseContext, NonMutatingUseContext, PlaceContext, Visitor};\nuse rustc_middle::mir::{\n    BasicBlock, Body, InlineAsmOperand, Local, Location, Place, START_BLOCK, StatementKind, TerminatorKind, traversal,\n};\nuse rustc_middle::ty::TyCtxt;\n\nmod possible_borrower;\npub use possible_borrower::PossibleBorrowerMap;\n\nmod possible_origin;\n\nmod transitive_relation;\n\n#[derive(Clone, Debug, Default)]\npub struct LocalUsage {\n    /// The locations where the local is used, if any.\n    pub local_use_locs: Vec<Location>,\n    /// The locations where the local is consumed or mutated, if any.\n    pub local_consume_or_mutate_locs: Vec<Location>,\n}\n\npub fn visit_local_usage(locals: &[Local], mir: &Body<'_>, location: Location) -> Option<Vec<LocalUsage>> {\n    let init = vec![\n        LocalUsage {\n            local_use_locs: Vec::new(),\n            local_consume_or_mutate_locs: Vec::new(),\n        };\n        locals.len()\n    ];\n\n    traversal::Postorder::new(&mir.basic_blocks, location.block, None)\n        .collect::<Vec<_>>()\n        .into_iter()\n        .rev()\n        .try_fold(init, |usage, tbb| {\n            let tdata = &mir.basic_blocks[tbb];\n\n            // Give up on loops\n            if tdata.terminator().successors().any(|s| s == location.block) {\n                return None;\n            }\n\n            let mut v = V {\n                locals,\n                location,\n                results: usage,\n            };\n            v.visit_basic_block_data(tbb, tdata);\n            Some(v.results)\n        })\n}\n\nstruct V<'a> {\n    locals: &'a [Local],\n    location: Location,\n    results: Vec<LocalUsage>,\n}\n\nimpl<'tcx> Visitor<'tcx> for V<'_> {\n    fn visit_place(&mut self, place: &Place<'tcx>, ctx: PlaceContext, loc: Location) {\n        if loc.block == self.location.block && loc.statement_index <= self.location.statement_index {\n            return;\n        }\n\n        let local = place.local;\n\n        for (i, self_local) in self.locals.iter().enumerate() {\n            if local == *self_local {\n                if !matches!(\n                    ctx,\n                    PlaceContext::MutatingUse(MutatingUseContext::Drop) | PlaceContext::NonUse(_)\n                ) {\n                    self.results[i].local_use_locs.push(loc);\n                }\n                if matches!(\n                    ctx,\n                    PlaceContext::NonMutatingUse(NonMutatingUseContext::Move | NonMutatingUseContext::Inspect)\n                        | PlaceContext::MutatingUse(MutatingUseContext::Borrow)\n                ) {\n                    self.results[i].local_consume_or_mutate_locs.push(loc);\n                }\n            }\n        }\n    }\n}\n\n/// Checks if the block is part of a cycle\npub fn block_in_cycle(body: &Body<'_>, block: BasicBlock) -> bool {\n    let mut seen = DenseBitSet::new_empty(body.basic_blocks.len());\n    let mut to_visit = Vec::with_capacity(body.basic_blocks.len() / 2);\n\n    seen.insert(block);\n    let mut next = block;\n    loop {\n        for succ in body.basic_blocks[next].terminator().successors() {\n            if seen.insert(succ) {\n                to_visit.push(succ);\n            } else if succ == block {\n                return true;\n            }\n        }\n\n        if let Some(x) = to_visit.pop() {\n            next = x;\n        } else {\n            return false;\n        }\n    }\n}\n\n/// Convenience wrapper around `visit_local_usage`.\npub fn used_exactly_once(mir: &Body<'_>, local: Local) -> Option<bool> {\n    visit_local_usage(\n        &[local],\n        mir,\n        Location {\n            block: START_BLOCK,\n            statement_index: 0,\n        },\n    )\n    .map(|mut vec| {\n        let LocalUsage { local_use_locs, .. } = vec.remove(0);\n        let mut locations = local_use_locs\n            .into_iter()\n            .filter(|&location| !is_local_assignment(mir, local, location));\n        if let Some(location) = locations.next() {\n            locations.next().is_none() && !block_in_cycle(mir, location.block)\n        } else {\n            false\n        }\n    })\n}\n\n/// Returns the `mir::Body` containing the node associated with `hir_id`.\n#[expect(clippy::module_name_repetitions)]\npub fn enclosing_mir(tcx: TyCtxt<'_>, hir_id: HirId) -> Option<&Body<'_>> {\n    let body_owner_local_def_id = tcx.hir_enclosing_body_owner(hir_id);\n    if tcx.hir_body_owner_kind(body_owner_local_def_id).is_fn_or_closure() {\n        Some(tcx.optimized_mir(body_owner_local_def_id.to_def_id()))\n    } else {\n        None\n    }\n}\n\n/// Tries to determine the `Local` corresponding to `expr`, if any.\n/// This function is expensive and should be used sparingly.\npub fn expr_local(tcx: TyCtxt<'_>, expr: &Expr<'_>) -> Option<Local> {\n    enclosing_mir(tcx, expr.hir_id).and_then(|mir| {\n        mir.local_decls.iter_enumerated().find_map(|(local, local_decl)| {\n            if local_decl.source_info.span == expr.span {\n                Some(local)\n            } else {\n                None\n            }\n        })\n    })\n}\n\n/// Returns a vector of `mir::Location` where `local` is assigned.\npub fn local_assignments(mir: &Body<'_>, local: Local) -> Vec<Location> {\n    let mut locations = Vec::new();\n    for (block, data) in mir.basic_blocks.iter_enumerated() {\n        for statement_index in 0..=data.statements.len() {\n            let location = Location { block, statement_index };\n            if is_local_assignment(mir, local, location) {\n                locations.push(location);\n            }\n        }\n    }\n    locations\n}\n\n// `is_local_assignment` is based on `is_place_assignment`:\n// https://github.com/rust-lang/rust/blob/b7413511dc85ec01ef4b91785f86614589ac6103/compiler/rustc_middle/src/mir/visit.rs#L1350\nfn is_local_assignment(mir: &Body<'_>, local: Local, location: Location) -> bool {\n    let Location { block, statement_index } = location;\n    let basic_block = &mir.basic_blocks[block];\n    if statement_index < basic_block.statements.len() {\n        let statement = &basic_block.statements[statement_index];\n        if let StatementKind::Assign(box (place, _)) = statement.kind {\n            place.as_local() == Some(local)\n        } else {\n            false\n        }\n    } else {\n        let terminator = basic_block.terminator();\n        match &terminator.kind {\n            TerminatorKind::Call { destination, .. } => destination.as_local() == Some(local),\n            TerminatorKind::InlineAsm { operands, .. } => operands.iter().any(|operand| {\n                if let InlineAsmOperand::Out { place: Some(place), .. } = operand {\n                    place.as_local() == Some(local)\n                } else {\n                    false\n                }\n            }),\n            _ => false,\n        }\n    }\n}\n",
        }
