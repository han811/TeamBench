"""
Parameterized generator for GH63_werkzeug_3102.

Source PR:    https://github.com/pallets/werkzeug/pull/3102
Source Issue: https://github.com/pallets/werkzeug/issues/2924

Seed varies: renames 'adapter' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH63_werkzeug_3102'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH63_werkzeug_3102'
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
                files[fpath] = files[fpath].replace('adapter', 'adapter' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH63_werkzeug_3102',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'pallets/werkzeug',
                "pr_number": 3102,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/pallets/werkzeug/pull/3102",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'docs/routing.rst': '===========\nURL Routing\n===========\n\n.. module:: werkzeug.routing\n\nWhen it comes to combining multiple controller or view functions (however\nyou want to call them), you need a dispatcher.  A simple way would be\napplying regular expression tests on ``PATH_INFO`` and call registered\ncallback functions that return the value.\n\nWerkzeug provides a much more powerful system, similar to `Routes`_.  All the\nobjects mentioned on this page must be imported from :mod:`werkzeug.routing`, not\nfrom :mod:`werkzeug`!\n\n.. _Routes: https://routes.readthedocs.io/en/latest/\n\n\nQuickstart\n==========\n\nHere is a simple example which could be the URL definition for a blog::\n\n    from werkzeug.routing import Map, Rule, NotFound, RequestRedirect\n\n    url_map = Map([\n        Rule(\'/\', endpoint=\'blog/index\'),\n        Rule(\'/<int:year>/\', endpoint=\'blog/archive\'),\n        Rule(\'/<int:year>/<int:month>/\', endpoint=\'blog/archive\'),\n        Rule(\'/<int:year>/<int:month>/<int:day>/\', endpoint=\'blog/archive\'),\n        Rule(\'/<int:year>/<int:month>/<int:day>/<slug>\',\n             endpoint=\'blog/show_post\'),\n        Rule(\'/about\', endpoint=\'blog/about_me\'),\n        Rule(\'/feeds/\', endpoint=\'blog/feeds\'),\n        Rule(\'/feeds/<feed_name>.rss\', endpoint=\'blog/show_feed\')\n    ])\n\n    def application(environ, start_response):\n        urls = url_map.bind_to_environ(environ)\n        try:\n            endpoint, args = urls.match()\n        except HTTPException as e:\n            return e(environ, start_response)\n        start_response(\'200 OK\', [(\'Content-Type\', \'text/plain\')])\n        return [f\'Rule points to {endpoint!r} with arguments {args!r}\'.encode()]\n\nSo what does that do?  First of all we create a new :class:`Map` which stores\na bunch of URL rules.  Then we pass it a list of :class:`Rule` objects.\n\nEach :class:`Rule` object is instantiated with a string that represents a rule\nand an endpoint which will be the alias for what view the rule represents.\nMultiple rules can have the same endpoint, but should have different arguments\nto allow URL construction.\n\nThe format for the URL rules is straightforward, but explained in detail below.\n\nInside the WSGI application we bind the url_map to the current request which will\nreturn a new :class:`MapAdapter`.  This url_map adapter can then be used to match\nor build domains for the current request.\n\nThe :meth:`MapAdapter.match` method can then either return a tuple in the form\n``(endpoint, args)`` or raise one of the three exceptions\n:exc:`~werkzeug.exceptions.NotFound`, :exc:`~werkzeug.exceptions.MethodNotAllowed`,\nor :exc:`~werkzeug.exceptions.RequestRedirect`.  For more details about those\nexceptions have a look at the documentation of the :meth:`MapAdapter.match` method.\n\n\nRule Format\n===========\n\nRule strings are URL paths with placeholders for variable parts in the\nformat ``<converter(arguments):name>``. ``converter`` and ``arguments``\n(with parentheses) are optional. If no converter is given, the\n``default`` converter is used (``string`` by default). The available\nconverters are discussed below.\n\nRules that end with a slash are "branches", others are "leaves". If\n``strict_slashes`` is enabled (the default), visiting a branch URL\nwithout a trailing slash will redirect to the URL with a slash appended.\n\nMany HTTP servers merge consecutive slashes into one when receiving\nrequests. If ``merge_slashes`` is enabled (the default), rules will\nmerge slashes in non-variable parts when matching and building. Visiting\na URL with consecutive slashes will redirect to the URL with slashes\nmerged. If you want to disable ``merge_slashes`` for a :class:`Rule` or\n:class:`Map`, you\'ll also need to configure your web server\nappropriately.\n\n\nBuilt-in Converters\n===================\n\nConverters for common types of URL variables are built-in. The available\nconverters can be overridden or extended through :attr:`Map.converters`.\n\n.. autoclass:: UnicodeConverter\n\n.. autoclass:: PathConverter\n\n.. autoclass:: AnyConverter\n\n.. autoclass:: IntegerConverter\n\n.. autoclass:: FloatConverter\n\n.. autoclass:: UUIDConverter\n\n\nMaps, Rules and Adapters\n========================\n\n.. autoclass:: Map\n   :members:\n\n   .. attribute:: converters\n\n      The dictionary of converters.  This can be modified after the class\n      was created, but will only affect rules added after the\n      modification.  If the rules are defined with the list passed to the\n      class, the `converters` parameter to the constructor has to be used\n      instead.\n\n.. autoclass:: MapAdapter\n   :members:\n\n.. autoclass:: Rule\n   :members: empty\n\n\nMatchers\n========\n\n.. autoclass:: StateMachineMatcher\n   :members:\n\n\nRule Factories\n==============\n\n.. autoclass:: RuleFactory\n   :members: get_rules\n\n.. autoclass:: Subdomain\n\n.. autoclass:: Submount\n\n.. autoclass:: EndpointPrefix\n\n\nRule Templates\n==============\n\n.. autoclass:: RuleTemplate\n\n\nCustom Converters\n=================\n\nYou can add custom converters that add behaviors not provided by the\nbuilt-in converters. To make a custom converter, subclass\n:class:`BaseConverter` then pass the new class to the :class:`Map`\n``converters`` parameter, or add it to\n:attr:`url_map.converters <Map.converters>`.\n\nThe converter should have a ``regex`` attribute with a regular\nexpression to match with. If the converter can take arguments in a URL\nrule, it should accept them in its ``__init__`` method. The entire\nregex expression will be matched as a group and used as the value for\nconversion.\n\nIf a custom converter can match a forward slash, ``/``, it should have\nthe attribute ``part_isolating`` set to ``False``. This will ensure\nthat rules using the custom converter are correctly matched.\n\nIt can implement a ``to_python`` method to convert the matched string to\nsome other object. This can also do extra validation that wasn\'t\npossible with the ``regex`` attribute, and should raise a\n:exc:`werkzeug.routing.ValidationError` in that case. Raising any other\nerrors will cause a 500 error.\n\nIt can implement a ``to_url`` method to convert a Python object to a\nstring when building a URL. Any error raised here will be converted to a\n:exc:`werkzeug.routing.BuildError` and eventually cause a 500 error.\n\nThis example implements a ``BooleanConverter`` that will match the\nstrings ``"yes"``, ``"no"``, and ``"maybe"``, returning a random value\nfor ``"maybe"``. ::\n\n    from random import randrange\n    from werkzeug.routing import BaseConverter, ValidationError\n\n    class BooleanConverter(BaseConverter):\n        regex = r"(?:yes|no|maybe)"\n\n        def __init__(self, url_map, maybe=False):\n            super().__init__(url_map)\n            self.maybe = maybe\n\n        def to_python(self, value):\n            if value == "maybe":\n                if self.maybe:\n                    return not randrange(2)\n                raise ValidationError\n            return value == \'yes\'\n\n        def to_url(self, value):\n            return "yes" if value else "no"\n\n    from werkzeug.routing import Map, Rule\n\n    url_map = Map([\n        Rule("/vote/<bool:werkzeug_rocks>", endpoint="vote"),\n        Rule("/guess/<bool(maybe=True):foo>", endpoint="guess")\n    ], converters={\'bool\': BooleanConverter})\n\nIf you want to change the default converter, assign a different\nconverter to the ``"default"`` key.\n\n\nHost Matching\n=============\n\n.. versionadded:: 0.7\n\nStarting with Werkzeug 0.7 it\'s also possible to do matching on the whole\nhost names instead of just the subdomain.  To enable this feature you need\nto pass ``host_matching=True`` to the :class:`Map` constructor and provide\nthe `host` argument to all routes::\n\n    url_map = Map([\n        Rule(\'/\', endpoint=\'www_index\', host=\'www.example.com\'),\n        Rule(\'/\', endpoint=\'help_index\', host=\'help.example.com\')\n    ], host_matching=True)\n\nVariable parts are of course also possible in the host section::\n\n    url_map = Map([\n        Rule(\'/\', endpoint=\'www_index\', host=\'www.example.com\'),\n        Rule(\'/\', endpoint=\'user_index\', host=\'<user>.example.com\')\n    ], host_matching=True)\n\n\nWebSockets\n==========\n\n.. versionadded:: 1.0\n\nIf a :class:`Rule` is created with ``websocket=True``, it will only\nmatch if the :class:`Map` is bound to a request with a ``url_scheme`` of\n``ws`` or ``wss``.\n\n.. note::\n\n   Werkzeug has no further WebSocket support beyond routing. This\n   functionality is mostly of use to ASGI projects.\n\n.. code-block:: python\n\n    url_map = Map([\n        Rule("/ws", endpoint="comm", websocket=True),\n    ])\n    adapter = map.bind("example.org", "/ws", url_scheme="ws")\n    assert adapter.match() == ("comm", {})\n\nIf the only match is a WebSocket rule and the bind is HTTP (or the\nonly match is HTTP and the bind is WebSocket) a\n:exc:`WebsocketMismatch` (derives from\n:exc:`~werkzeug.exceptions.BadRequest`) exception is raised.\n\nAs WebSocket URLs have a different scheme, rules are always built with a\nscheme and host, ``force_external=True`` is implied.\n\n.. code-block:: python\n\n    url = adapter.build("comm")\n    assert url == "ws://example.org/ws"\n\n\nState Machine Matching\n======================\n\nThe default matching algorithm uses a state machine that transitions\nbetween parts of the request path to find a match. To understand how\nthis works consider this rule::\n\n    /resource/<id>\n\nFirstly this rule is decomposed into two ``RulePart``. The first is a\nstatic part with a content equal to ``resource``, the second is\ndynamic and requires a regex match to ``[^/]+``.\n\nA state machine is then created with an initial state that represents\nthe rule\'s first ``/``. This initial state has a single, static\ntransition to the next state which represents the rule\'s second\n``/``. This second state has a single dynamic transition to the final\nstate which includes the rule.\n\nTo match a path the matcher starts and the initial state and follows\ntransitions that work. Clearly a trial path of ``/resource/2`` has the\nparts ``""``, ``resource``, and ``2`` which match the transitions and\nhence a rule will match. Whereas ``/other/2`` will not match as there\nis no transition for the ``other`` part from the initial state.\n\nThe only diversion from this rule is if a ``RulePart`` is not\npart-isolating i.e. it will match ``/``. In this case the ``RulePart``\nis considered final and represents a transition that must include all\nthe subsequent parts of the trial path.\n',
        }
