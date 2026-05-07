"""
Parameterized generator for GH813_quart_436.

Source PR:    https://github.com/pallets/quart/pull/436
Source Issue: N/A

Seed varies: renames 'align' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH813_quart_436'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH813_quart_436'
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
                files[fpath] = files[fpath].replace('align', 'align' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH813_quart_436',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'pallets/quart',
                "pr_number": 436,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/pallets/quart/pull/436",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'docs/conf.py': 'import importlib.metadata\nimport os\n\nfrom sphinx.ext import apidoc\n\n# Project --------------------------------------------------------------\n\nproject = "Quart"\ncopyright = "2017 Pallets"\nversion = release = importlib.metadata.version("quart").partition(".dev")[0]\n\n# General --------------------------------------------------------------\n\ndefault_role = "code"\nextensions = [\n    "sphinx.ext.autodoc",\n    "sphinx.ext.napoleon",\n    "myst_parser",\n]\nautodoc_member_order = "bysource"\nautodoc_typehints = "description"\nautodoc_preserve_defaults = True\nmyst_enable_extensions = [\n    "fieldlist",\n]\nmyst_heading_anchors = 2\n\n# HTML -----------------------------------------------------------------\n\nhtml_theme = "pydata_sphinx_theme"\nhtml_theme_options = {\n    "external_links": [\n        {"name": "Source code", "url": "https://github.com/pallets/quart"},\n        {"name": "Issues", "url": "https://github.com/pallets/quart/issues"},\n    ],\n    "icon_links": [\n        {\n            "name": "Github",\n            "url": "https://github.com/pallets/quart",\n            "icon": "fab fa-github",\n        },\n    ],\n}\nhtml_static_path = ["_static"]\nhtml_logo = "_static/logo_short.png"\n\n\ndef run_apidoc(_):\n    # generate API documentation via sphinx-apidoc\n    # https://www.sphinx-doc.org/en/master/man/sphinx-apidoc.html\n    base_path = os.path.abspath(os.path.dirname(__file__))\n    apidoc.main(\n        [\n            "-f",\n            "-e",\n            "-o",\n            f"{base_path}/reference/source",\n            f"{base_path}/../src/quart",\n            f"{base_path}/../src/quart/datastructures.py",\n        ]\n    )\n\n\ndef setup(app):\n    app.connect("builder-inited", run_apidoc)\n',
            'docs/index.rst': ":orphan:\n\n.. title:: Quart documentation\n\n.. image:: _static/logo.png\n   :width: 300px\n   :alt: Quart logo\n   :align: right\n\nQuart\n=====\n\nQuart is a Fast Python web microframework. Using Quart you can,\n\n * write JSON APIs e.g. :ref:`a RESTful API<api_tutorial>`,\n * render and serve HTML e.g. :ref:`a blog<blog_tutorial>`,\n * serve WebSockets e.g. :ref:`a simple chat<chat_tutorial>`,\n * stream responses e.g. :ref:`serve video<video_tutorial>`,\n * all of the above in a single app,\n * or do pretty much anything over the HTTP or WebSocket protocols.\n\nWith all of the above possible using asynchronous (asyncio)\nlibraries/code or :ref:`synchronous<sync_code>` libraries/code.\n\nIf you are,\n\n * new to Python then start by reading :ref:`installation` instructions,\n * new to Quart then try the :ref:`quickstart`,\n * new to asyncio see the :ref:`asyncio` guide,\n * migrating from Flask see :ref:`flask_migration`,\n * looking for a cheatsheet then look :ref:`here<cheatsheet>`.\n\nQuart is an asyncio reimplementation of the popular `Flask\n<https://flask.palletsprojects.com>`_ microframework API. This means that if you\nunderstand Flask you understand Quart. See :ref:`flask_evolution` to\nlearn more about how Quart builds on Flask.\n\nLike Flask Quart has an ecosystem of\n:ref:`extensions<quart_extensions>` for more specific needs. In\naddition a number of the Flask :ref:`extensions<flask_extensions>`\nwork with Quart.\n\nQuart is developed on `Github <https://github.com/pallets/quart>`_. If\nyou come across an issue, or have a feature request please open an\n`issue <https://github.com/pallets/quart/issues>`_.If you want to\ncontribute a fix or the feature-implementation please do (typo fixes\nwelcome), by proposing a `merge request\n<https://github.com/pallets/quart/merge_requests>`_. If you want to\nask for help try `on discord <https://discord.gg/pallets>`_.\n\n.. note::\n\n    If you can't find documentation for what you are looking for here,\n    remember that Quart is an implementation of the Flask API and\n    hence the `Flask documentation <https://flask.palletsprojects.com>`_ is\n    a great source of help. Quart is also built on the `Jinja\n    <https://flask.palletsprojects.com>`_ template engine and the `Werkzeug\n    <https://werkzeug.palletsprojects.com>`_ toolkit.\n\n    The Flask documentation is so good that you may be better placed\n    consulting it first then returning here to check how Quart\n    differs.\n\nTutorials\n---------\n\n.. toctree::\n   :maxdepth: 2\n\n   tutorials/index.rst\n\nHow to guides\n-------------\n\n.. toctree::\n   :maxdepth: 2\n\n   how_to_guides/index.rst\n\nDiscussion\n----------\n\n.. toctree::\n   :maxdepth: 2\n\n   discussion/index.rst\n\nReferences\n----------\n\n.. toctree::\n    :maxdepth: 2\n\n    reference/index\n    license\n    changes\n",
        }
