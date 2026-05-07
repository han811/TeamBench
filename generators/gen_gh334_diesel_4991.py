"""
Parameterized generator for GH334_diesel_4991.

Source PR:    https://github.com/diesel-rs/diesel/pull/4991
Source Issue: N/A

Seed varies: renames 'able' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH334_diesel_4991'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH334_diesel_4991'
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
                files[fpath] = files[fpath].replace('able', 'able' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH334_diesel_4991',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'diesel-rs/diesel',
                "pr_number": 4991,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/diesel-rs/diesel/pull/4991",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            '.github/ISSUE_TEMPLATE/config.yml': "blank_issues_enabled: false\ncontact_links:\n  - name: Compiler error while compiling diesel\n    url: https://github.com/diesel-rs/diesel/issues?q=is%3Aissue+ld+returned+1+exit+status+\n    about: Failed to compile diesel? Have a look at existing issues. You've likely miss some required dependency.\n  - name: Questions\n    url: https://github.com/diesel-rs/diesel/discussions/categories/q-a\n    about: Do you have questions? Ask in our forum.\n  - name: Feature Requests\n    url: https://github.com/diesel-rs/diesel/discussions/categories/ideas\n    about: If you want to suggest a new feature please create a new topic in our discussions forum\n",
            'CONTRIBUTING.md': '# Contributing\n\nThanks for your interest in contributing to Diesel! We very much look forward to\nyour suggestions, bug reports, and pull requests.\n\nWe run an active [discussion forum](https://github.com/diesel-rs/diesel/discussions) where you can ask Diesel-related questions and\nget help. Feel free to ask there before opening a GitHub issue or\npull request.\n\n*Note:* Anyone who interacts with Diesel in any space, including but not\nlimited to this GitHub repository, must follow our [code of\nconduct](https://github.com/diesel-rs/diesel/blob/master/code_of_conduct.md).\n\n## Submitting bug reports\n\nHave a look at our [issue tracker]. If you can\'t find an issue (open or closed)\ndescribing your problem (or a very similar one) there, please open a new issue with\nthe following details:\n\n- Which versions of Rust and Diesel are you using?\n- Which feature flags are you using?\n- What are you trying to accomplish?\n- What is the full error you are seeing?\n- How can we reproduce this?\n  - Please quote as much of your code as needed to reproduce (best link to a\n    public repository or [Gist])\n  - Please post as much of your database schema as is relevant to your error\n\n[issue tracker]: https://github.com/diesel-rs/diesel/issues\n[Gist]: https://gist.github.com\n\nThank you! We\'ll try to respond as quickly as possible.\n\n\n## Submitting feature requests\n\nDiesel\'s issue tracker is meant to represent our current roadmap. An open issue represents either a bug, or a new feature that a member of the Diesel team is actively working on.\n\nThis means that you should not submit a feature request to our issue tracker, unless you were asked to do so by a member of the Diesel team. Feature requests should instead be posted in\nour [discussion forum](https://github.com/diesel-rs/diesel/discussions/categories/ideas).\n\nIf you can\'t find thread describing your idea on our forum, create a new one. Adding answers to the following questions in your description is +1:\n\n-   What do you want to do, and how do you expect Diesel to support you with that?\n-   How might this be added to Diesel?\n-   What are possible alternatives?\n-   Are there any disadvantages?\n\nThank you! We\'ll try to respond as quickly as possible.\n\n## Improve the documentation\n\nWe are welcoming contributions that improve the documentation, examples or the guides provided on the web page. \nThese contribution are as valuable as any code contribution. So if you notice something that could be documented\nin a better way or that is missing an example do not hesitate to open a PR to improve the documentation for all users.\n\n## Triaging issues & Reviewing changes\n\nThe Diesel project receives a significant number of bug reports and pull requests. Any help reviewing and classifying these reports are highly welcome. For PR\'s you can just leave review comments. Otherwise you are welcome to join the [Diesel Reviewer team](https://github.com/orgs/diesel-rs/teams/reviewers) by requesting access [in this issue](https://github.com/diesel-rs/diesel/issues/1186). Members of this team get pinged on PR\'s that need a review and do have the right to triage issues. Especially PR reviews are a good place to become more familiar with certain Rust idioms and Diesel internals as they are a good place to ask questions about how something works.\n\n## Contribute code to Diesel\n\nWe try to keep a number of issues [marked as good first issue](https://github.com/diesel-rs/diesel/issues?q=is%3Aissue%20state%3Aopen%20label%3A%22good%20first%20issue%22%20label%3A%22help%20wanted%22%20label%3A%22mentoring%20available%22) in our issue tracker. These are usually a good starting point if you are new to contribute to Diesel. We also keep a project to [plan](https://github.com/orgs/diesel-rs/projects/1) features for the next Diesel release. Feel free to grab any open issue in our tracker or project tracking by leaving a comment there. Also do not hesitate to ask for help if you are stuck trying to resolve a specific issue. Other contributors usually can help you around most problems.\n\n### Setting up Diesel locally\n\n1. Install Rust using [rustup], which allows you to easily switch between Rust\n   versions. Diesel currently supports Rust Stable, Nightly, Rust Beta.\n\n2. Install the system libraries needed to interface with the database systems\n   you wish to use.\n\n   These are the same as when compiling Diesel. It\'s generally a good idea\n   to install _all_ drivers so you can run all tests locally.\n\n   *Shortcut:* On macOS, you don\'t need to install anything to work with SQLite.\n   For PostgreSQL, you\'ll only need the server (`libpq` is installed by\n   default). To get started, `brew install postgresql@17 mysql` and follow the\n   instructions shown to set up the database servers. Other versions of\n   PostgreSQL should work as well.\n3. Clone this repository and open it in your favorite editor.\n4. Create a `.env` file in this directory, and add the connection details for\n   your databases.\n\n   *Additional note:* The MySQL tests currently fail when running on MySQL 5.6\n   or lower. If you have 5.6 or lower installed locally and cannot upgrade for\n   some reason, you may want to consider setting up Docker as mentioned below.\n\n   See [.env.sample](.env.sample) for an example that works with a trivial\n   local setup.\n\n   *Note:* If you didn\'t specify the MySQL user to be one with elevated\n   permissions, you\'ll want to run a command like ```mysql -c "GRANT ALL ON\n   `diesel_%`.* TO \'\'@\'localhost\';" -uroot```, or something similar for the\n   user that you\'ve specified.\n\n   If you have [Docker](https://www.docker.com/), the following snippet might help you\n   to get Postgres and MySQL running (with the above `.env` file):\n\n   ```bash\n   #!/usr/bin/env sh\n   set -e\n   docker run -d --name diesel.mysql -p 3306:3306 -e MYSQL_ALLOW_EMPTY_PASSWORD=true mysql\n   while\n     sleep 1;\n     ! echo \'CREATE DATABASE diesel_test; CREATE DATABASE diesel_unit_test;\' | docker exec -i diesel.mysql mysql\n   do sleep 1; done\n\n   docker run -d --name diesel.postgres -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres\n   while\n     sleep 1;\n     ! echo \'CREATE DATABASE diesel_test;\' | docker exec -i diesel.postgres psql -U postgres\n   do :; done\n   ```\n\n   If you want to use docker-compose, you can execute docker-compose command like this.\n\n    ```bash\n    $ docker-compose up\n    ```\n    \n5. Install [cargo-nextest](https://nexte.st/) via `cargo install cargo-nextest`\n\n6. Now, try running the test suite to confirm everything works for you locally\n   by executing `cargo xtask run-tests`. (Initially, this will take a while to compile\n   everything.) In addition, if you want to compile and test a crate separately, \n   you can refer to the commands printed and executed by `cargo xtask run-tests`. Additionally you \n   can check `cargo xtask run-tests --help` on how to further configure which tests are executed.\n\n[rustup]: https://rustup.rs/\n\n### Coding Style\n\nWe follow the [Rust Style Guide](https://github.com/rust-dev-tools/fmt-rfcs/blob/master/guide/guide.md), enforced using [rustfmt](https://github.com/rust-lang/rustfmt).\nTo run rustfmt tests locally:\n\n1. Use rustup to set rust toolchain to the version specified in the\n   [rust-toolchain file](./rust-toolchain).\n\n2. Install the rustfmt and clippy by running\n   ```\n   rustup component add rustfmt\n   rustup component add clippy\n   ```\n\n3. Install [typos](https://github.com/crate-ci/typos) via `cargo install typos-cli`\n\n4. Use `cargo xtask tidy` to check if your changes follow the expected code style.\n   This will run `cargo fmt --check`, `typos` and `cargo clippy` internally. See `cargo xtask tidy --help`\n   for additional options.\n\nYou can also use rustfmt to make corrections or highlight issues in your editor.\nCheck out [their README](https://github.com/rust-lang/rustfmt) for details.\n\n### Usage of LLMs and AI agents\n\nThe Diesel project doesn\'t completely disallow to usage of LLMs and AI agents for contributions. There are still a number of restrictions and rules you as a PR author are asked to follow.\n\nMost importantly you as the author of the PR are responsible for carefully reviewing the generated code to make sure that:\n\n* It is correct to your best knowledge\n* It does not contain any copyrighted code that is incompatible with the license used by Diesel\n\nFurthermore you are asked to disclose the usage of any such tools in your PR description. \n\n### Common Abbreviations\n\n`ST`: Sql Type. Basically always has the `NativeSqlType` constraint\n\n`DB`: Database. Basically always has the `Backend` constraint.\n\n`QS`: Query Source. Usually doesn\'t have a constraint, but sometimes will have `QuerySource` attached\n\n`PK`: Primary Key\n\n`Lhs`: Left Hand Side\n\n`Rhs`: Right Hand Side\n\n`Conn`: Connection\n\nGenerally, we prefer to give our types meaningful names. `Lhs` and `Rhs` vs `T` and `U` for a binary expression, for example.\n\n### Compile Tests\n\nDiesel has an extensive suite of compile tests in the `diesel_compile_tests` crate. These test work by having a small test program for each test case and then verifying that the compilation of those tests fail with a specific error message. For that we use the [`ui_test`](https://docs.rs/ui_test/latest/ui_test/) also used by rustc.  \nRunning these tests can done by simply running `cargo test` in the `diesel_compile_tests` directory. Adding new tests simply requires adding a new file to `diesel_compile_tests/tests/fail/` containing the source code you want to test.\nYou can run these tests with the environment variable `BLESS` set to `1` to update the expected stderr output. You also need to update the inline error annotations in the source code to match on the error message. See the documentation of `ui_test` for how to do that. \n\n### Snapshot tests\n\nDiesel\'s test suite is using [insta](https://docs.rs/insta/latest/insta/) for snapshot tests in various places. If you get an error in the test suite that some output of such a test changed you can use [cargo-insta](https://docs.rs/insta/latest/insta/) to review and accept these changes. You need to commit these changes as part of your changeset.\n\nSuch snapshot tests are used by the following tests:\n\n* Expanded code tests in `diesel_derives`\n* Print-schema tests in `diesel_cli`\n* Generate-migration tests in `diesel_cli`\n',
        }
