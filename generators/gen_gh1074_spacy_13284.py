"""
Parameterized generator for GH1074_spaCy_13284.

Source PR:    https://github.com/explosion/spaCy/pull/13284
Source Issue: N/A

Seed varies: renames 'default' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH1074_spaCy_13284'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH1074_spaCy_13284'
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
                files[fpath] = files[fpath].replace('default', 'default' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH1074_spaCy_13284',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'explosion/spaCy',
                "pr_number": 13284,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/explosion/spaCy/pull/13284",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'spacy/tests/serialize/test_serialize_extension_attrs.py': 'import pytest\n\nfrom spacy.tokens import Doc, Token\nfrom spacy.vocab import Vocab\n\n\n@pytest.fixture\ndef doc_w_attrs(en_tokenizer):\n    Doc.set_extension("_test_attr", default=False)\n    Doc.set_extension("_test_prop", getter=lambda doc: len(doc.text))\n    Doc.set_extension("_test_method", method=lambda doc, arg: f"{len(doc.text)}{arg}")\n    doc = en_tokenizer("This is a test.")\n    doc._._test_attr = "test"\n\n    Token.set_extension("_test_token", default="t0")\n    doc[1]._._test_token = "t1"\n\n    return doc\n\n\ndef test_serialize_ext_attrs_from_bytes(doc_w_attrs):\n    doc_b = doc_w_attrs.to_bytes()\n    doc = Doc(Vocab()).from_bytes(doc_b)\n    assert doc._.has("_test_attr")\n    assert doc._._test_attr == "test"\n    assert doc._._test_prop == len(doc.text)\n    assert doc._._test_method("test") == f"{len(doc.text)}test"\n    assert doc[0]._._test_token == "t0"\n    assert doc[1]._._test_token == "t1"\n    assert doc[2]._._test_token == "t0"\n',
        }
