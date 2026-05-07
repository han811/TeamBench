"""
Parameterized generator for GH690_diesel_4956.

Source PR:    https://github.com/diesel-rs/diesel/pull/4956
Source Issue: N/A

Seed varies: renames 'above' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH690_diesel_4956'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH690_diesel_4956'
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
                files[fpath] = files[fpath].replace('above', 'above' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH690_diesel_4956',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'diesel-rs/diesel',
                "pr_number": 4956,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/diesel-rs/diesel/pull/4956",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'README.md': '[![diesel logo](https://diesel.rs/assets/images/diesel_logo_stacked_black.png)](https://diesel.rs)\n\n# A safe, extensible ORM and Query Builder for Rust\n\n[![Build Status](https://github.com/diesel-rs/diesel/workflows/CI%20Tests/badge.svg)](https://github.com/diesel-rs/diesel/actions?query=workflow%3A%22CI+Tests%22+branch%3Amaster)\n[![Crates.io](https://img.shields.io/crates/v/diesel.svg)](https://crates.io/crates/diesel)\n\nAPI Documentation: [latest release](https://docs.rs/diesel) – [master branch](https://docs.diesel.rs/master/diesel/index.html)\n\n[Homepage](https://diesel.rs)\n\nDiesel gets rid of the boilerplate for database interaction and eliminates\nruntime errors without sacrificing performance. It takes full advantage of\nRust\'s type system to create a low overhead query builder that "feels like\nRust."\n\nSupported databases:\n1. [PostgreSQL](https://docs.diesel.rs/master/diesel/pg/index.html)\n2. [MySQL](https://docs.diesel.rs/master/diesel/mysql/index.html)\n3. [SQLite](https://docs.diesel.rs/master/diesel/sqlite/index.html)\n\nYou can configure the database backend in `Cargo.toml`:\n\n```toml\n[dependencies]\ndiesel = { version = "<version>", features = ["<postgres|mysql|sqlite>"] }\n```\n\n## Getting Started\n\nFind our extensive Getting Started tutorial at\n[https://diesel.rs/guides/getting-started](https://diesel.rs/guides/getting-started).\nGuides on more specific features are coming soon.\n\n## Getting help\n\nIf you run into problems, you can come ask for help at in our [GitHub Discussions](https://github.com/diesel-rs/diesel/discussions) forum. \nThis is also the right place to propose new features or show your applications.\n\n## Usage\n\n### Simple queries\n\nSimple queries are a complete breeze. Loading all users from a database:\n\n```rust\nusers::table.load(&mut connection)\n```\n\nExecuted SQL:\n\n```sql\nSELECT * FROM users;\n```\n\nLoading all the posts for a user:\n\n``` rust\nPost::belonging_to(user).load(&mut connection)\n```\n\nExecuted SQL:\n\n```sql\nSELECT * FROM posts WHERE user_id = 1;\n```\n\n### Complex queries\n\nDiesel\'s powerful query builder helps you construct queries as simple or complex as\nyou need, at zero cost.\n\n```rust\nlet versions = Version::belonging_to(krate)\n  .select(id)\n  .order(num.desc())\n  .limit(5);\nlet downloads = version_downloads\n  .filter(date.gt(now - 90.days()))\n  .filter(version_id.eq_any(versions))\n  .order(date)\n  .load::<Download>(&mut conn)?;\n```\n\nExecuted SQL:\n\n```sql\nSELECT version_downloads.* FROM version_downloads\n  WHERE date > (NOW() - \'90 days\')\n    AND version_id = ANY(\n      SELECT id FROM versions\n        WHERE crate_id = 1\n        ORDER BY num DESC\n        LIMIT 5\n    )\n  ORDER BY date\n```\n\n### Less boilerplate\n\nDiesel codegen generates boilerplate for you. It lets you focus on your business logic, not mapping to and from SQL rows.\n\nThat means you can write this:\n\n```rust\n#[derive(Queryable, Selectable)]\n#[diesel(table_name = downloads)]\npub struct Download {\n    id: i32,\n    version_id: i32,\n    downloads: i32,\n    counted: i32,\n    date: SystemTime,\n}\n```\n\nInstead of this without Diesel:\n\n```rust\npub struct Download {\n    id: i32,\n    version_id: i32,\n    downloads: i32,\n    counted: i32,\n    date: SystemTime,\n}\n\nimpl Download {\n    fn from_row(row: &Row) -> Download {\n        Download {\n            id: row.get("id"),\n            version_id: row.get("version_id"),\n            downloads: row.get("downloads"),\n            counted: row.get("counted"),\n            date: row.get("date"),\n        }\n    }\n}\n```\n\n### Inserting data\n\nIt\'s not just about reading data. Diesel makes it easy to use structs for new records.\n\n```rust\n#[derive(Insertable)]\n#[diesel(table_name = users)]\nstruct NewUser<\'a> {\n    name: &\'a str,\n    hair_color: Option<&\'a str>,\n}\n\nlet new_users = vec![\n    NewUser { name: "Sean", hair_color: Some("Black") },\n    NewUser { name: "Gordon", hair_color: None },\n];\n\ninsert_into(users)\n    .values(&new_users)\n    .execute(&mut connection);\n```\n\nExecuted SQL:\n\n```sql\nINSERT INTO users (name, hair_color) VALUES\n  (\'Sean\', \'Black\'),\n  (\'Gordon\', DEFAULT)\n```\n\nIf you need data from the rows you inserted, just change `execute` to `get_result` or `get_results`. Diesel will take care of the rest.\n\n```rust\nlet new_users = vec![\n    NewUser { name: "Sean", hair_color: Some("Black") },\n    NewUser { name: "Gordon", hair_color: None },\n];\n\nlet inserted_users = insert_into(users)\n    .values(&new_users)\n    .get_results::<User>(&mut connection);\n```\n\nExecuted SQL:\n\n```sql\nINSERT INTO users (name, hair_color) VALUES\n  (\'Sean\', \'Black\'),\n  (\'Gordon\', DEFAULT)\n  RETURNING *\n```\n\n### Updating data\n\nDiesel\'s codegen can generate several ways to update a row, letting you encapsulate your logic in the way that makes sense for your app.\n\nModifying a struct:\n\n```rust\npost.published = true;\npost.save_changes(&mut connection);\n```\n\nOne-off batch changes:\n\n```rust\nupdate(users.filter(email.like("%@spammer.com")))\n    .set(banned.eq(true))\n    .execute(&mut connection)\n```\n\nUsing a struct for encapsulation:\n\n```rust\nupdate(Settings::belonging_to(current_user))\n    .set(&settings_form)\n    .execute(&mut connection)\n```\n\n### Raw SQL\n\nThere will always be certain queries that are just easier to write as raw SQL, or can\'t be expressed with the query builder. Even in these cases, Diesel provides an easy to use API for writing raw SQL.\n\n```rust\n#[derive(QueryableByName)]\n#[diesel(table_name = users)]\nstruct User {\n    id: i32,\n    name: String,\n    organization_id: i32,\n}\n\n// Using `include_str!` allows us to keep the SQL in a\n// separate file, where our editor can give us SQL specific\n// syntax highlighting.\nsql_query(include_str!("complex_users_by_organization.sql"))\n    .bind::<Integer, _>(organization_id)\n    .bind::<BigInt, _>(offset)\n    .bind::<BigInt, _>(limit)\n    .load::<User>(&mut conn)?;\n```\n\n## Code of conduct\n\nAnyone who interacts with Diesel in any space, including but not limited to\nthis GitHub repository, must follow our [code of conduct](https://github.com/diesel-rs/diesel/blob/master/code_of_conduct.md).\n\n## License\n\nLicensed under either of these:\n\n * Apache License, Version 2.0, ([LICENSE-APACHE](LICENSE-APACHE) or\n   https://www.apache.org/licenses/LICENSE-2.0)\n * MIT license ([LICENSE-MIT](LICENSE-MIT) or\n   https://opensource.org/licenses/MIT)\n\n### Contributing\n\nBefore contributing, please read the [contributors guide](https://github.com/diesel-rs/diesel/blob/master/CONTRIBUTING.md)\nfor useful information about setting up Diesel locally, coding style and common abbreviations.\n\nUnless you explicitly state otherwise, any contribution you intentionally submit\nfor inclusion in the work, as defined in the Apache-2.0 license, shall be\ndual-licensed as above, without any additional terms or conditions.\n\n### Notable Sponsors and Supporters\n\nWe would like to thank all of the sponsors supporting the work on Diesel. Notable large sponsors are:\n\n\n<p align="center">\n    <a href="https://nlnet.nl/project/Diesel/">\n        <img src="https://diesel.rs/assets/images/nl_net_foundation_logo.svg" width="50%"/>\n        <br/>\n        NLNet Foundation\n    </a>\n</p>\n\n<p align="center">\n    <a href="https://nlnet.nl/project/Diesel/">\n        <img src="https://diesel.rs/assets/images/NGI0Core_tag.svg" width="50%"/>\n        <br/>\n        NGI Zero Core\n    </a>\n</p>\n\n<p align="center">\n    <a href="https://www.prototypefund.de/projects/diesel-databaseviews">\n        <img src="https://diesel.rs/assets/images/PrototypeFund_logo_dark.png" width="50%"/>\n        <br/>\n        Prototype Fund\n    </a>\n</p>\n\n<p align="center">\n    <a href="https://www.prototypefund.de/projects/diesel-databaseviews">\n        <img src="https://diesel.rs/assets/images/bmbf_logo.jpg" width="50%"/>\n        <br/>\n        Federal Ministry of Research, Technology and Space (Germany)\n    </a>\n</p>\n\n<p align="center">\n    <a href="https://github.blog/open-source/maintainers/securing-the-supply-chain-at-scale-starting-with-71-important-open-source-projects/">\n        <img src="https://diesel.rs/assets/images/GitHub_Logo.png" width="50%"/>\n        GitHub Secure Open Source Fund\n    </a>\n</p>\n\n<p align="center">\n    <a href="https://giga-infosystems.com/">\n        <img src="https://diesel.rs/assets/images/logo_giga.svg" width="35%"/>\n        <br/>\n        GiGa Infosystems GmbH\n    </a>\n</p>\n\nAdditionally we would like to thank all persons sponsoring the project on [GitHub](https://github.com/sponsors/weiznich#sponsors). Without them developing Diesel wouldn\'t be possible.\n',
        }
