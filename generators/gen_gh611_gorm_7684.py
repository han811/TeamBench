"""
Parameterized generator for GH611_gorm_7684.

Source PR:    https://github.com/go-gorm/gorm/pull/7684
Source Issue: N/A

Seed varies: renames 'accounts' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH611_gorm_7684'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH611_gorm_7684'
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
                files[fpath] = files[fpath].replace('accounts', 'accounts' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH611_gorm_7684',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'go-gorm/gorm',
                "pr_number": 7684,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/go-gorm/gorm/pull/7684",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'tests/chainable_api_test.go': 'package tests\n\nimport (\n\t"context"\n\t"testing"\n\n\t"gorm.io/gorm"\n\t"gorm.io/gorm/clause"\n\t"gorm.io/gorm/schema"\n)\n\n// testDialector is a minimal Dialector implementation used only for unit tests in-memory.\ntype testDialector struct{}\n\nfunc (d testDialector) Name() string                                   { return "test" }\nfunc (d testDialector) Initialize(*gorm.DB) error                      { return nil }\nfunc (d testDialector) Migrator(db *gorm.DB) gorm.Migrator             { return nil }\nfunc (d testDialector) DataTypeOf(*schema.Field) string                { return "" }\nfunc (d testDialector) DefaultValueOf(*schema.Field) clause.Expression { return clause.Expr{} }\nfunc (d testDialector) BindVarTo(writer clause.Writer, stmt *gorm.Statement, v interface{}) {\n\t// write a simple placeholder\n\twriter.WriteByte(\'?\')\n}\nfunc (d testDialector) QuoteTo(writer clause.Writer, s string)         { writer.WriteString(s) }\nfunc (d testDialector) Explain(sql string, vars ...interface{}) string { return sql }\n\n// newTestDB returns a minimal *DB with an initialized Statement suitable for unit tests\nfunc newTestDB() *gorm.DB {\n\td := testDialector{}\n\tcfg := &gorm.Config{Dialector: d}\n\tdb := &gorm.DB{Config: cfg}\n\tstmt := &gorm.Statement{\n\t\tDB:       db,\n\t\tClauses:  map[string]clause.Clause{},\n\t\tPreloads: map[string][]interface{}{},\n\t\tContext:  context.Background(),\n\t\tVars:     make([]interface{}, 0),\n\t}\n\tdb.Statement = stmt\n\treturn db\n}\n\nfunc TestChainableAPI(t *testing.T) {\n\tdb := newTestDB()\n\n\t// Model\n\tm := &struct{ ID int }{}\n\ttx := db.Model(m)\n\tif tx.Statement.Model != m {\n\t\tt.Fatalf("Model not set, got %v", tx.Statement.Model)\n\t}\n\n\t// Table\n\ttx = tx.Table("users")\n\tif tx.Statement.Table != "users" {\n\t\tt.Fatalf("Table not set, got %v", tx.Statement.Table)\n\t}\n\tif tx.Statement.TableExpr == nil {\n\t\tt.Fatalf("TableExpr expected to be set")\n\t}\n\n\t// Distinct + Select\n\ttx = tx.Distinct("name", "age")\n\tif !tx.Statement.Distinct {\n\t\tt.Fatalf("Distinct expected true")\n\t}\n\tif len(tx.Statement.Selects) != 2 || tx.Statement.Selects[0] != "name" {\n\t\tt.Fatalf("Selects expected [name age], got %v", tx.Statement.Selects)\n\t}\n\n\t// Where\n\ttx = tx.Where("age = ?", 20)\n\tc, ok := tx.Statement.Clauses["WHERE"]\n\tif !ok {\n\t\tt.Fatalf("WHERE clause expected")\n\t}\n\tif where, ok := c.Expression.(clause.Where); !ok || len(where.Exprs) == 0 {\n\t\tt.Fatalf("WHERE expressions expected, got %v", c.Expression)\n\t}\n\n\t// Order\n\ttx = tx.Order("name DESC")\n\tif _, ok := tx.Statement.Clauses["ORDER BY"]; !ok {\n\t\tt.Fatalf("ORDER BY clause expected")\n\t}\n\n\t// Limit / Offset\n\ttx = tx.Limit(10).Offset(5)\n\tif cl, ok := tx.Statement.Clauses["LIMIT"]; !ok {\n\t\tt.Fatalf("LIMIT clause expected")\n\t} else {\n\t\tif limit, ok := cl.Expression.(clause.Limit); !ok || limit.Limit == nil || *limit.Limit != 10 || limit.Offset != 5 {\n\t\t\tt.Fatalf("LIMIT/Offset values unexpected: %v", cl.Expression)\n\t\t}\n\t}\n\n\t// Joins\n\ttx = tx.Joins("JOIN accounts ON accounts.user_id = users.id")\n\tif len(tx.Statement.Joins) == 0 {\n\t\tt.Fatalf("Joins expected")\n\t}\n\tif tx.Statement.Joins[0].Name != "JOIN accounts ON accounts.user_id = users.id" {\n\t\tt.Fatalf("Join name mismatch: %v", tx.Statement.Joins[0].Name)\n\t}\n\n\t// Preload\n\ttx = tx.Preload("Orders", "state != ?", "cancelled")\n\targs, ok := tx.Statement.Preloads["Orders"]\n\tif !ok || len(args) != 2 {\n\t\tt.Fatalf("Preload expected with args, got %v", tx.Statement.Preloads)\n\t}\n\n\t// Scopes: just ensure calling Scopes doesn\'t panic and returns a DB\n\ttx = tx.Scopes(func(d *gorm.DB) *gorm.DB { return d.Where("status = ?", "ok") })\n\tif tx == nil {\n\t\tt.Fatalf("Scopes returned nil")\n\t}\n\n\t// Unscoped\n\ttx = tx.Unscoped()\n\tif !tx.Statement.Unscoped {\n\t\tt.Fatalf("Unscoped expected to be true")\n\t}\n\n\t// Raw\n\ttx = tx.Raw("SELECT ? as x", 1)\n\tif tx.Statement.SQL.Len() == 0 {\n\t\tt.Fatalf("Raw SQL expected to be built")\n\t}\n\tif len(tx.Statement.Vars) != 1 || tx.Statement.Vars[0] != 1 {\n\t\tt.Fatalf("Raw Vars expected to contain 1, got %v", tx.Statement.Vars)\n\t}\n}\n',
        }
