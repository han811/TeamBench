"""
Parameterized generator for GH136_mitmproxy_8054.

Source PR:    https://github.com/mitmproxy/mitmproxy/pull/8054
Source Issue: https://github.com/mitmproxy/mitmproxy/issues/8051

Seed varies: renames 'application' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH136_mitmproxy_8054'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH136_mitmproxy_8054'
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
                files[fpath] = files[fpath].replace('application', 'application' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH136_mitmproxy_8054',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'mitmproxy/mitmproxy',
                "pr_number": 8054,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/mitmproxy/mitmproxy/pull/8054",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'mitmproxy/contentviews/__init__.py': '"""\nmitmproxy includes a set of content views which can be used to\nformat/decode/highlight/reencode data. While they are mostly used for HTTP message\nbodies, the may be used in other contexts, e.g. to decode WebSocket messages.\n\nSee "Custom Contentviews" in the mitmproxy documentation for examples.\n"""\n\nimport logging\nimport sys\nimport traceback\nimport warnings\nfrom dataclasses import dataclass\n\nfrom ..addonmanager import cut_traceback\nfrom ._api import Contentview\nfrom ._api import InteractiveContentview\nfrom ._api import Metadata\nfrom ._api import SyntaxHighlight\nfrom ._compat import get  # noqa: F401\nfrom ._compat import LegacyContentview\nfrom ._compat import remove  # noqa: F401\nfrom ._registry import ContentviewRegistry\nfrom ._utils import ContentviewMessage\nfrom ._utils import get_data\nfrom ._utils import make_metadata\nfrom ._view_css import css\nfrom ._view_dns import dns\nfrom ._view_graphql import graphql\nfrom ._view_http3 import http3\nfrom ._view_image import image\nfrom ._view_javascript import javascript\nfrom ._view_json import json_view\nfrom ._view_mqtt import mqtt\nfrom ._view_multipart import multipart\nfrom ._view_query import query\nfrom ._view_raw import raw\nfrom ._view_socketio import socket_io\nfrom ._view_urlencoded import urlencoded\nfrom ._view_wbxml import wbxml\nfrom ._view_xml_html import xml_html\nfrom .base import View\nimport mitmproxy_rs.contentviews\nfrom mitmproxy import flow\nfrom mitmproxy.utils import strutils\n\nlogger = logging.getLogger(__name__)\n\n\n@dataclass\nclass ContentviewResult:\n    text: str\n    syntax_highlight: SyntaxHighlight\n    view_name: str | None\n    description: str\n\n\nregistry = ContentviewRegistry()\n\n\ndef prettify_message(\n    message: ContentviewMessage,\n    flow: flow.Flow,\n    view_name: str = "auto",\n    registry: ContentviewRegistry = registry,\n) -> ContentviewResult:\n    data, enc = get_data(message)\n    if data is None:\n        return ContentviewResult(\n            text="Content is missing.",\n            syntax_highlight="error",\n            description="",\n            view_name=None,\n        )\n\n    # Determine the correct view\n    metadata = make_metadata(message, flow)\n    view = registry.get_view(data, metadata, view_name)\n\n    # Finally, we can pretty-print!\n    try:\n        ret = ContentviewResult(\n            text=view.prettify(data, metadata),\n            syntax_highlight=view.syntax_highlight,\n            view_name=view.name,\n            description=enc,\n        )\n    except Exception as e:\n        logger.debug(f"Contentview {view.name!r} failed: {e}", exc_info=True)\n        if view_name == "auto":\n            # If the contentview was chosen as the best matching one, fall back to raw.\n            ret = ContentviewResult(\n                text=raw.prettify(data, metadata),\n                syntax_highlight=raw.syntax_highlight,\n                view_name=raw.name,\n                description=f"{enc}[failed to parse as {view.name}]",\n            )\n        else:\n            # Cut the exception traceback for display.\n            exc, value, tb = sys.exc_info()\n            tb_cut = cut_traceback(tb, "prettify_message")\n            if (\n                tb_cut == tb\n            ):  # If there are no extra frames, just skip displaying the traceback.\n                tb_cut = None\n            # If the contentview has been set explicitly, we display a hard error.\n            err = "".join(traceback.format_exception(exc, value=value, tb=tb_cut))\n            ret = ContentviewResult(\n                text=f"Couldn\'t parse as {view.name}:\\n{err}",\n                syntax_highlight="error",\n                view_name=view.name,\n                description=enc,\n            )\n\n    ret.text = strutils.escape_control_characters(ret.text)\n    return ret\n\n\ndef reencode_message(\n    prettified: str,\n    message: ContentviewMessage,\n    flow: flow.Flow,\n    view_name: str,\n) -> bytes:\n    metadata = make_metadata(message, flow)\n    view = registry[view_name.lower()]\n    if not isinstance(view, InteractiveContentview):\n        raise ValueError(f"Contentview {view.name} is not interactive.")\n    return view.reencode(prettified, metadata)\n\n\n_views: list[Contentview] = [\n    css,\n    dns,\n    graphql,\n    http3,\n    image,\n    javascript,\n    json_view,\n    mqtt,\n    multipart,\n    query,\n    raw,\n    socket_io,\n    urlencoded,\n    wbxml,\n    xml_html,\n]\nfor view in _views:\n    registry.register(view)\nfor name in mitmproxy_rs.contentviews.__all__:\n    if name.startswith("_"):\n        continue\n    cv = getattr(mitmproxy_rs.contentviews, name)\n    if isinstance(cv, Contentview) and not isinstance(cv, type):\n        registry.register(cv)\n\n\ndef add(contentview: Contentview | type[Contentview]) -> None:\n    """\n    Register a contentview for use in mitmproxy.\n\n    You may pass a `Contentview` instance or the class itself.\n    When passing the class, its constructor will be invoked with no arguments.\n    """\n    if isinstance(contentview, View):\n        warnings.warn(\n            f"`mitmproxy.contentviews.View` is deprecated since mitmproxy 12, "\n            f"migrate {contentview.__class__.__name__} to `mitmproxy.contentviews.Contentview` instead.",\n            stacklevel=2,\n        )\n        contentview = LegacyContentview(contentview)\n    registry.register(contentview)\n\n\n# hack: docstring where pdoc finds it.\nSyntaxHighlight = SyntaxHighlight\n"""\nSyntax highlighting formats currently supported by mitmproxy.\nNote that YAML is a superset of JSON; so if you\'d like to highlight JSON, pick the YAML highlighter.\n\n*If you have a concrete use case for additional formats, please open an issue.*\n"""\n\n\n__all__ = [\n    # Public Contentview API\n    "Contentview",\n    "InteractiveContentview",\n    "SyntaxHighlight",\n    "add",\n    "Metadata",\n]\n',
            'test/mitmproxy/contentviews/test__view_zip.py': 'import io\nimport zipfile\n\nfrom mitmproxy import http\nfrom mitmproxy.contentviews import Metadata\nfrom mitmproxy.contentviews._view_zip import zip\n\n\ndef meta(content_type: str) -> Metadata:\n    return Metadata(\n        content_type=content_type.split(";")[0],\n        http_message=http.Request.make(\n            "POST", "https://example.com/", headers={"content-type": content_type}\n        ),\n    )\n\n\ndef test_view_zip():\n    buffer = io.BytesIO()\n    with zipfile.ZipFile(buffer, "w") as zf:\n        for name in [\n            "normal.txt",\n            "with spaces.txt",\n            "dir/nested.txt",\n            "file\\nwith\\nnewlines.txt",\n            "unicode_文件.txt",\n            "café.txt",\n        ]:\n            zf.writestr(name, b"content")\n    result = zip.prettify(buffer.getvalue(), meta("application/zip"))\n    for name in [\n        "normal.txt",\n        "with spaces.txt",\n        "dir/nested.txt",\n        "newlines",\n        "文件",\n        "café",\n    ]:\n        assert name in result\n    assert zip.syntax_highlight == "yaml"\n\n\ndef test_view_zip_empty():\n    buffer = io.BytesIO()\n    with zipfile.ZipFile(buffer, "w"):\n        pass\n    assert (\n        zip.prettify(buffer.getvalue(), meta("application/zip")) == "(empty zip file)"\n    )\n\n\ndef test_render_priority():\n    assert zip.render_priority(b"data", Metadata(content_type="application/zip")) == 1.0\n    assert zip.render_priority(b"data", Metadata(content_type="text/plain")) == 0\n    assert zip.render_priority(b"", Metadata(content_type="application/zip")) == 0\n',
        }
