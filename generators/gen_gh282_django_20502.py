"""
Parameterized generator for GH282_django_20502.

Source PR:    https://github.com/django/django/pull/20502
Source Issue: N/A

Seed varies: renames 'added' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH282_django_20502'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH282_django_20502'
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
                files[fpath] = files[fpath].replace('added', 'added' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH282_django_20502',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'django/django',
                "pr_number": 20502,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/django/django/pull/20502",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'tests/field_defaults/tests.py': 'from datetime import datetime\nfrom decimal import Decimal\nfrom math import pi\n\nfrom django.core.exceptions import ValidationError\nfrom django.db import connection\nfrom django.db.models import Case, F, FloatField, Value, When\nfrom django.db.models.expressions import (\n    Expression,\n    ExpressionList,\n    ExpressionWrapper,\n    Func,\n    OrderByList,\n    RawSQL,\n)\nfrom django.db.models.functions import Collate\nfrom django.db.models.lookups import GreaterThan\nfrom django.test import SimpleTestCase, TestCase, override_settings, skipUnlessDBFeature\nfrom django.utils import timezone\n\nfrom .models import (\n    Article,\n    DBArticle,\n    DBDefaults,\n    DBDefaultsFK,\n    DBDefaultsFunction,\n    DBDefaultsPK,\n)\n\n\nclass DefaultTests(TestCase):\n    def test_field_defaults(self):\n        a = Article()\n        now = datetime.now()\n        a.save()\n\n        self.assertIsInstance(a.id, int)\n        self.assertEqual(a.headline, "Default headline")\n        self.assertLess((now - a.pub_date).seconds, 5)\n\n    @skipUnlessDBFeature("supports_expression_defaults")\n    def test_field_db_defaults_returning(self):\n        a = DBArticle()\n        a.save()\n        self.assertIsInstance(a.id, int)\n        expected_num_queries = (\n            0 if connection.features.can_return_columns_from_insert else 3\n        )\n        with self.assertNumQueries(expected_num_queries):\n            self.assertEqual(a.headline, "Default headline")\n            self.assertIsInstance(a.pub_date, datetime)\n            self.assertEqual(a.cost, Decimal("3.33"))\n\n    @skipUnlessDBFeature("supports_expression_defaults")\n    def test_field_db_defaults_refresh(self):\n        a = DBArticle()\n        a.save()\n        expected_num_queries = (\n            0 if connection.features.can_return_columns_from_insert else 3\n        )\n        self.assertIsInstance(a.id, int)\n        with self.assertNumQueries(expected_num_queries):\n            self.assertEqual(a.headline, "Default headline")\n            self.assertIsInstance(a.pub_date, datetime)\n            self.assertEqual(a.cost, Decimal("3.33"))\n\n    def test_null_db_default(self):\n        obj1 = DBDefaults.objects.create()\n        expected_num_queries = (\n            0 if connection.features.can_return_columns_from_insert else 1\n        )\n        with self.assertNumQueries(expected_num_queries):\n            self.assertEqual(obj1.null, 1.1)\n\n        obj2 = DBDefaults.objects.create(null=None)\n        with self.assertNumQueries(0):\n            self.assertIsNone(obj2.null)\n\n    @skipUnlessDBFeature("supports_expression_defaults")\n    @override_settings(USE_TZ=True)\n    def test_db_default_function(self):\n        m = DBDefaultsFunction.objects.create()\n        expected_num_queries = (\n            0 if connection.features.can_return_columns_from_insert else 4\n        )\n        with self.assertNumQueries(expected_num_queries):\n            self.assertAlmostEqual(m.number, pi)\n            self.assertEqual(m.year, timezone.now().year)\n            self.assertAlmostEqual(m.added, pi + 4.5)\n            self.assertEqual(m.multiple_subfunctions, 4.5)\n\n    @skipUnlessDBFeature("insert_test_table_with_defaults")\n    def test_both_default(self):\n        create_sql = connection.features.insert_test_table_with_defaults\n        with connection.cursor() as cursor:\n            cursor.execute(create_sql.format(DBDefaults._meta.db_table))\n        obj1 = DBDefaults.objects.get()\n        self.assertEqual(obj1.both, 2)\n\n        obj2 = DBDefaults.objects.create()\n        self.assertEqual(obj2.both, 1)\n\n    def test_pk_db_default(self):\n        obj1 = DBDefaultsPK.objects.create()\n        if not connection.features.can_return_columns_from_insert:\n            # refresh_from_db() cannot be used because that needs the pk to\n            # already be known to Django.\n            obj1 = DBDefaultsPK.objects.get(pk="en")\n        self.assertEqual(obj1.pk, "en")\n        self.assertEqual(obj1.language_code, "en")\n\n        obj2 = DBDefaultsPK.objects.create(language_code="de")\n        self.assertEqual(obj2.pk, "de")\n        self.assertEqual(obj2.language_code, "de")\n\n    def test_foreign_key_db_default(self):\n        parent1 = DBDefaultsPK.objects.create(language_code="fr")\n        child1 = DBDefaultsFK.objects.create()\n        if not connection.features.can_return_columns_from_insert:\n            child1.refresh_from_db()\n        self.assertEqual(child1.language_code, parent1)\n\n        parent2 = DBDefaultsPK.objects.create()\n        if not connection.features.can_return_columns_from_insert:\n            # refresh_from_db() cannot be used because that needs the pk to\n            # already be known to Django.\n            parent2 = DBDefaultsPK.objects.get(pk="en")\n        child2 = DBDefaultsFK.objects.create(language_code=parent2)\n        self.assertEqual(child2.language_code, parent2)\n\n    @skipUnlessDBFeature("supports_expression_defaults")\n    def test_case_when_db_default_returning(self):\n        m = DBDefaultsFunction.objects.create()\n        expected_num_queries = (\n            0 if connection.features.can_return_columns_from_insert else 1\n        )\n        with self.assertNumQueries(expected_num_queries):\n            self.assertEqual(m.case_when, 3)\n\n    @skipUnlessDBFeature("supports_expression_defaults")\n    def test_case_when_db_default_no_returning(self):\n        m = DBDefaultsFunction.objects.create()\n        m.refresh_from_db()\n        self.assertEqual(m.case_when, 3)\n\n    @skipUnlessDBFeature("supports_expression_defaults")\n    def test_bulk_create_all_db_defaults(self):\n        articles = [DBArticle(), DBArticle()]\n        DBArticle.objects.bulk_create(articles)\n\n        headlines = DBArticle.objects.values_list("headline", flat=True)\n        self.assertSequenceEqual(headlines, ["Default headline", "Default headline"])\n\n    @skipUnlessDBFeature("supports_expression_defaults")\n    def test_bulk_create_all_db_defaults_one_field(self):\n        pub_date = datetime.now()\n        articles = [DBArticle(pub_date=pub_date), DBArticle(pub_date=pub_date)]\n        DBArticle.objects.bulk_create(articles)\n\n        headlines = DBArticle.objects.values_list("headline", "pub_date", "cost")\n        self.assertSequenceEqual(\n            headlines,\n            [\n                ("Default headline", pub_date, Decimal("3.33")),\n                ("Default headline", pub_date, Decimal("3.33")),\n            ],\n        )\n\n    @skipUnlessDBFeature("supports_expression_defaults")\n    def test_bulk_create_mixed_db_defaults(self):\n        articles = [DBArticle(), DBArticle(headline="Something else")]\n        DBArticle.objects.bulk_create(articles)\n\n        headlines = DBArticle.objects.values_list("headline", flat=True)\n        self.assertCountEqual(headlines, ["Default headline", "Something else"])\n\n    @skipUnlessDBFeature("supports_expression_defaults")\n    @override_settings(USE_TZ=True)\n    def test_bulk_create_mixed_db_defaults_function(self):\n        instances = [DBDefaultsFunction(), DBDefaultsFunction(year=2000)]\n        DBDefaultsFunction.objects.bulk_create(instances)\n\n        years = DBDefaultsFunction.objects.values_list("year", flat=True)\n        self.assertCountEqual(years, [2000, timezone.now().year])\n\n    @skipUnlessDBFeature("supports_expression_defaults")\n    def test_full_clean(self):\n        obj = DBArticle()\n        obj.full_clean()\n        obj.save()\n        obj.refresh_from_db()\n        self.assertEqual(obj.headline, "Default headline")\n\n        obj = DBArticle(headline="Other title")\n        obj.full_clean()\n        obj.save()\n        obj.refresh_from_db()\n        self.assertEqual(obj.headline, "Other title")\n\n        obj = DBArticle(headline="")\n        with self.assertRaises(ValidationError):\n            obj.full_clean()\n\n\nclass AllowedDefaultTests(SimpleTestCase):\n    def test_allowed(self):\n        class Max(Func):\n            function = "MAX"\n\n        tests = [\n            Value(10),\n            Max(1, 2),\n            RawSQL("Now()", ()),\n            Value(10) + Value(7),  # Combined expression.\n            ExpressionList(Value(1), Value(2)),\n            ExpressionWrapper(Value(1), output_field=FloatField()),\n            Case(When(GreaterThan(2, 1), then=3), default=4),\n        ]\n        for expression in tests:\n            with self.subTest(expression=expression):\n                self.assertIs(expression.allowed_default, True)\n\n    def test_disallowed(self):\n        class Max(Func):\n            function = "MAX"\n\n        tests = [\n            Expression(),\n            F("field"),\n            Max(F("count"), 1),\n            Value(10) + F("count"),  # Combined expression.\n            ExpressionList(F("count"), Value(2)),\n            ExpressionWrapper(F("count"), output_field=FloatField()),\n            Collate(Value("John"), "nocase"),\n            OrderByList("field"),\n        ]\n        for expression in tests:\n            with self.subTest(expression=expression):\n                self.assertIs(expression.allowed_default, False)\n',
        }
