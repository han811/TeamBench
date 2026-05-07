"""
Parameterized generator for GH692_flask_5903.

Source PR:    https://github.com/pallets/flask/pull/5903
Source Issue: N/A

Seed varies: renames 'config' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH692_flask_5903'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH692_flask_5903'
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
                files[fpath] = files[fpath].replace('config', 'config' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH692_flask_5903',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'pallets/flask',
                "pr_number": 5903,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/pallets/flask/pull/5903",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'docs/tutorial/factory.rst': '.. currentmodule:: flask\n\nApplication Setup\n=================\n\nA Flask application is an instance of the :class:`Flask` class.\nEverything about the application, such as configuration and URLs, will\nbe registered with this class.\n\nThe most straightforward way to create a Flask application is to create\na global :class:`Flask` instance directly at the top of your code, like\nhow the "Hello, World!" example did on the previous page. While this is\nsimple and useful in some cases, it can cause some tricky issues as the\nproject grows.\n\nInstead of creating a :class:`Flask` instance globally, you will create\nit inside a function. This function is known as the *application\nfactory*. Any configuration, registration, and other setup the\napplication needs will happen inside the function, then the application\nwill be returned.\n\n\nThe Application Factory\n-----------------------\n\nIt\'s time to start coding! Create the ``flaskr`` directory and add the\n``__init__.py`` file. The ``__init__.py`` serves double duty: it will\ncontain the application factory, and it tells Python that the ``flaskr``\ndirectory should be treated as a package.\n\n.. code-block:: none\n\n    $ mkdir flaskr\n\n.. code-block:: python\n    :caption: ``flaskr/__init__.py``\n\n    import os\n\n    from flask import Flask\n\n\n    def create_app(test_config=None):\n        # create and configure the app\n        app = Flask(__name__, instance_relative_config=True)\n        app.config.from_mapping(\n            SECRET_KEY=\'dev\',\n            DATABASE=os.path.join(app.instance_path, \'flaskr.sqlite\'),\n        )\n\n        if test_config is None:\n            # load the instance config, if it exists, when not testing\n            app.config.from_pyfile(\'config.py\', silent=True)\n        else:\n            # load the test config if passed in\n            app.config.from_mapping(test_config)\n\n        # ensure the instance folder exists\n        try:\n            os.makedirs(app.instance_path)\n        except OSError:\n            pass\n\n        # a simple page that says hello\n        @app.route(\'/hello\')\n        def hello():\n            return \'Hello, World!\'\n\n        return app\n\n``create_app`` is the application factory function. You\'ll add to it\nlater in the tutorial, but it already does a lot.\n\n#.  ``app = Flask(__name__, instance_relative_config=True)`` creates the\n    :class:`Flask` instance.\n\n    *   ``__name__`` is the name of the current Python module. The app\n        needs to know where it\'s located to set up some paths, and\n        ``__name__`` is a convenient way to tell it that.\n\n    *   ``instance_relative_config=True`` tells the app that\n        configuration files are relative to the\n        :ref:`instance folder <instance-folders>`. The instance folder\n        is located outside the ``flaskr`` package and can hold local\n        data that shouldn\'t be committed to version control, such as\n        configuration secrets and the database file.\n\n#.  :meth:`app.config.from_mapping() <Config.from_mapping>` sets\n    some default configuration that the app will use:\n\n    *   :data:`SECRET_KEY` is used by Flask and extensions to keep data\n        safe. It\'s set to ``\'dev\'`` to provide a convenient value\n        during development, but it should be overridden with a random\n        value when deploying.\n\n    *   ``DATABASE`` is the path where the SQLite database file will be\n        saved. It\'s under\n        :attr:`app.instance_path <Flask.instance_path>`, which is the\n        path that Flask has chosen for the instance folder. You\'ll learn\n        more about the database in the next section.\n\n#.  :meth:`app.config.from_pyfile() <Config.from_pyfile>` overrides\n    the default configuration with values taken from the ``config.py``\n    file in the instance folder if it exists. For example, when\n    deploying, this can be used to set a real ``SECRET_KEY``.\n\n    *   ``test_config`` can also be passed to the factory, and will be\n        used instead of the instance configuration. This is so the tests\n        you\'ll write later in the tutorial can be configured\n        independently of any development values you have configured.\n\n#.  :func:`os.makedirs` ensures that\n    :attr:`app.instance_path <Flask.instance_path>` exists. Flask\n    doesn\'t create the instance folder automatically, but it needs to be\n    created because your project will create the SQLite database file\n    there.\n\n#.  :meth:`@app.route() <Flask.route>` creates a simple route so you can\n    see the application working before getting into the rest of the\n    tutorial. It creates a connection between the URL ``/hello`` and a\n    function that returns a response, the string ``\'Hello, World!\'`` in\n    this case.\n\n\nRun The Application\n-------------------\n\nNow you can run your application using the ``flask`` command. From the\nterminal, tell Flask where to find your application, then run it in\ndebug mode. Remember, you should still be in the top-level\n``flask-tutorial`` directory, not the ``flaskr`` package.\n\nDebug mode shows an interactive debugger whenever a page raises an\nexception, and restarts the server whenever you make changes to the\ncode. You can leave it running and just reload the browser page as you\nfollow the tutorial.\n\n.. code-block:: text\n\n    $ flask --app flaskr run --debug\n\nYou\'ll see output similar to this:\n\n.. code-block:: text\n\n     * Serving Flask app "flaskr"\n     * Debug mode: on\n     * Running on http://127.0.0.1:5000/ (Press CTRL+C to quit)\n     * Restarting with stat\n     * Debugger is active!\n     * Debugger PIN: nnn-nnn-nnn\n\nVisit http://127.0.0.1:5000/hello in a browser and you should see the\n"Hello, World!" message. Congratulations, you\'re now running your Flask\nweb application!\n\nIf another program is already using port 5000, you\'ll see\n``OSError: [Errno 98]`` or ``OSError: [WinError 10013]`` when the\nserver tries to start. See :ref:`address-already-in-use` for how to\nhandle that.\n\nContinue to :doc:`database`.\n',
            'examples/tutorial/flaskr/__init__.py': 'import os\n\nfrom flask import Flask\n\n\ndef create_app(test_config=None):\n    """Create and configure an instance of the Flask application."""\n    app = Flask(__name__, instance_relative_config=True)\n    app.config.from_mapping(\n        # a default secret that should be overridden by instance config\n        SECRET_KEY="dev",\n        # store the database in the instance folder\n        DATABASE=os.path.join(app.instance_path, "flaskr.sqlite"),\n    )\n\n    if test_config is None:\n        # load the instance config, if it exists, when not testing\n        app.config.from_pyfile("config.py", silent=True)\n    else:\n        # load the test config if passed in\n        app.config.update(test_config)\n\n    # ensure the instance folder exists\n    try:\n        os.makedirs(app.instance_path)\n    except OSError:\n        pass\n\n    @app.route("/hello")\n    def hello():\n        return "Hello, World!"\n\n    # register the database commands\n    from . import db\n\n    db.init_app(app)\n\n    # apply the blueprints to the app\n    from . import auth\n    from . import blog\n\n    app.register_blueprint(auth.bp)\n    app.register_blueprint(blog.bp)\n\n    # make url_for(\'index\') == url_for(\'blog.index\')\n    # in another app, you might define a separate main index here with\n    # app.route, while giving the blog blueprint a url_prefix, but for\n    # the tutorial the blog will be the main index\n    app.add_url_rule("/", endpoint="index")\n\n    return app\n',
        }
