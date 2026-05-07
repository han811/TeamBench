"""
Parameterized generator for GH600_psycopg_1269.

Source PR:    https://github.com/psycopg/psycopg/pull/1269
Source Issue: N/A

Seed varies: renames 'bytes' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH600_psycopg_1269'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH600_psycopg_1269'
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
                files[fpath] = files[fpath].replace('bytes', 'bytes' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH600_psycopg_1269',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'psycopg/psycopg',
                "pr_number": 1269,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/psycopg/psycopg/pull/1269",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'psycopg/psycopg/types/uuid.py': '"""\nAdapters for the UUID type.\n"""\n\n# Copyright (C) 2020 The Psycopg Team\n\nfrom __future__ import annotations\n\nfrom typing import TYPE_CHECKING\nfrom collections.abc import Callable\n\nfrom .. import _oids\nfrom ..pq import Format\nfrom ..abc import AdaptContext\nfrom ..adapt import Buffer, Dumper, Loader\n\nif TYPE_CHECKING:\n    import uuid\n\n# Importing the uuid module is slow, so import it only on request.\nUUID: Callable[..., uuid.UUID] = None  # type: ignore[assignment]\n\n\nclass UUIDDumper(Dumper):\n    oid = _oids.UUID_OID\n\n    def dump(self, obj: uuid.UUID) -> Buffer | None:\n        return obj.hex.encode()\n\n\nclass UUIDBinaryDumper(UUIDDumper):\n    format = Format.BINARY\n\n    def dump(self, obj: uuid.UUID) -> Buffer | None:\n        return obj.bytes\n\n\nclass UUIDLoader(Loader):\n    def __init__(self, oid: int, context: AdaptContext | None = None):\n        super().__init__(oid, context)\n        global UUID\n        if UUID is None:\n            from uuid import UUID\n\n    def load(self, data: Buffer) -> uuid.UUID:\n        if isinstance(data, memoryview):\n            data = bytes(data)\n        return UUID(data.decode())\n\n\nclass UUIDBinaryLoader(UUIDLoader):\n    format = Format.BINARY\n\n    def load(self, data: Buffer) -> uuid.UUID:\n        if isinstance(data, memoryview):\n            data = bytes(data)\n        return UUID(bytes=data)\n\n\ndef register_default_adapters(context: AdaptContext) -> None:\n    adapters = context.adapters\n    adapters.register_dumper("uuid.UUID", UUIDDumper)\n    adapters.register_dumper("uuid.UUID", UUIDBinaryDumper)\n    adapters.register_loader("uuid", UUIDLoader)\n    adapters.register_loader("uuid", UUIDBinaryLoader)\n',
        }
