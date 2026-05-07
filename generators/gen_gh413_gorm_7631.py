"""
Parameterized generator for GH413_gorm_7631.

Source PR:    https://github.com/go-gorm/gorm/pull/7631
Source Issue: N/A

Seed varies: renames 'append' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH413_gorm_7631'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH413_gorm_7631'
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
                files[fpath] = files[fpath].replace('append', 'append' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH413_gorm_7631',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'go-gorm/gorm',
                "pr_number": 7631,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/go-gorm/gorm/pull/7631",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'schema/utils.go': 'package schema\n\nimport (\n\t"context"\n\t"fmt"\n\t"reflect"\n\t"regexp"\n\t"strings"\n\n\t"gorm.io/gorm/clause"\n\t"gorm.io/gorm/utils"\n)\n\nvar embeddedCacheKey = "embedded_cache_store"\n\nfunc ParseTagSetting(str string, sep string) map[string]string {\n\tsettings := map[string]string{}\n\tnames := strings.Split(str, sep)\n\n\tfor i := 0; i < len(names); i++ {\n\t\tj := i\n\t\tif len(names[j]) > 0 {\n\t\t\tfor {\n\t\t\t\tif names[j][len(names[j])-1] == \'\\\\\' {\n\t\t\t\t\ti++\n\t\t\t\t\tnames[j] = names[j][0:len(names[j])-1] + sep + names[i]\n\t\t\t\t\tnames[i] = ""\n\t\t\t\t} else {\n\t\t\t\t\tbreak\n\t\t\t\t}\n\t\t\t}\n\t\t}\n\n\t\tvalues := strings.Split(names[j], ":")\n\t\tk := strings.TrimSpace(strings.ToUpper(values[0]))\n\n\t\tif len(values) >= 2 {\n\t\t\tsettings[k] = strings.Join(values[1:], ":")\n\t\t} else if k != "" {\n\t\t\tsettings[k] = k\n\t\t}\n\t}\n\n\treturn settings\n}\n\nfunc toColumns(val string) (results []string) {\n\tif val != "" {\n\t\tfor _, v := range strings.Split(val, ",") {\n\t\t\tresults = append(results, strings.TrimSpace(v))\n\t\t}\n\t}\n\treturn\n}\n\nfunc removeSettingFromTag(tag reflect.StructTag, names ...string) reflect.StructTag {\n\tfor _, name := range names {\n\t\ttag = reflect.StructTag(regexp.MustCompile(`(?i)(gorm:.*?)(`+name+`(:.*?)?)(;|("))`).ReplaceAllString(string(tag), "${1}${5}"))\n\t}\n\treturn tag\n}\n\nfunc appendSettingFromTag(tag reflect.StructTag, value string) reflect.StructTag {\n\tt := tag.Get("gorm")\n\tif strings.Contains(t, value) {\n\t\treturn tag\n\t}\n\treturn reflect.StructTag(fmt.Sprintf(`gorm:"%s;%s"`, value, t))\n}\n\n// GetRelationsValues get relations\'s values from a reflect value\nfunc GetRelationsValues(ctx context.Context, reflectValue reflect.Value, rels []*Relationship) (reflectResults reflect.Value) {\n\tfor _, rel := range rels {\n\t\treflectResults = reflect.MakeSlice(reflect.SliceOf(reflect.PointerTo(rel.FieldSchema.ModelType)), 0, 1)\n\n\t\tappendToResults := func(value reflect.Value) {\n\t\t\tif _, isZero := rel.Field.ValueOf(ctx, value); !isZero {\n\t\t\t\tresult := reflect.Indirect(rel.Field.ReflectValueOf(ctx, value))\n\t\t\t\tswitch result.Kind() {\n\t\t\t\tcase reflect.Struct:\n\t\t\t\t\treflectResults = reflect.Append(reflectResults, result.Addr())\n\t\t\t\tcase reflect.Slice, reflect.Array:\n\t\t\t\t\tfor i := 0; i < result.Len(); i++ {\n\t\t\t\t\t\tif elem := result.Index(i); elem.Kind() == reflect.Ptr {\n\t\t\t\t\t\t\treflectResults = reflect.Append(reflectResults, elem)\n\t\t\t\t\t\t} else {\n\t\t\t\t\t\t\treflectResults = reflect.Append(reflectResults, elem.Addr())\n\t\t\t\t\t\t}\n\t\t\t\t\t}\n\t\t\t\t}\n\t\t\t}\n\t\t}\n\n\t\tswitch reflectValue.Kind() {\n\t\tcase reflect.Struct:\n\t\t\tappendToResults(reflectValue)\n\t\tcase reflect.Slice:\n\t\t\tfor i := 0; i < reflectValue.Len(); i++ {\n\t\t\t\tappendToResults(reflectValue.Index(i))\n\t\t\t}\n\t\t}\n\n\t\treflectValue = reflectResults\n\t}\n\n\treturn\n}\n\n// GetIdentityFieldValuesMap get identity map from fields\nfunc GetIdentityFieldValuesMap(ctx context.Context, reflectValue reflect.Value, fields []*Field) (map[string][]reflect.Value, [][]interface{}) {\n\tvar (\n\t\tresults       = [][]interface{}{}\n\t\tdataResults   = map[string][]reflect.Value{}\n\t\tloaded        = map[interface{}]bool{}\n\t\tnotZero, zero bool\n\t)\n\n\tif reflectValue.Kind() == reflect.Ptr ||\n\t\treflectValue.Kind() == reflect.Interface {\n\t\treflectValue = reflectValue.Elem()\n\t}\n\n\tswitch reflectValue.Kind() {\n\tcase reflect.Map:\n\t\tresults = [][]interface{}{make([]interface{}, len(fields))}\n\t\tfor idx, field := range fields {\n\t\t\tmapValue := reflectValue.MapIndex(reflect.ValueOf(field.DBName))\n\t\t\tif mapValue.IsZero() {\n\t\t\t\tmapValue = reflectValue.MapIndex(reflect.ValueOf(field.Name))\n\t\t\t}\n\t\t\tresults[0][idx] = mapValue.Interface()\n\t\t}\n\n\t\tdataResults[utils.ToStringKey(results[0]...)] = []reflect.Value{reflectValue}\n\tcase reflect.Struct:\n\t\tresults = [][]interface{}{make([]interface{}, len(fields))}\n\n\t\tfor idx, field := range fields {\n\t\t\tresults[0][idx], zero = field.ValueOf(ctx, reflectValue)\n\t\t\tnotZero = notZero || !zero\n\t\t}\n\n\t\tif !notZero {\n\t\t\treturn nil, nil\n\t\t}\n\n\t\tdataResults[utils.ToStringKey(results[0]...)] = []reflect.Value{reflectValue}\n\tcase reflect.Slice, reflect.Array:\n\t\tfor i := 0; i < reflectValue.Len(); i++ {\n\t\t\telem := reflectValue.Index(i)\n\t\t\telemKey := elem.Interface()\n\t\t\tif elem.Kind() != reflect.Ptr && elem.CanAddr() {\n\t\t\t\telemKey = elem.Addr().Interface()\n\t\t\t}\n\n\t\t\tif _, ok := loaded[elemKey]; ok {\n\t\t\t\tcontinue\n\t\t\t}\n\t\t\tloaded[elemKey] = true\n\n\t\t\tfieldValues := make([]interface{}, len(fields))\n\t\t\tnotZero = false\n\t\t\tfor idx, field := range fields {\n\t\t\t\tfieldValues[idx], zero = field.ValueOf(ctx, elem)\n\t\t\t\tnotZero = notZero || !zero\n\t\t\t}\n\n\t\t\tif notZero {\n\t\t\t\tdataKey := utils.ToStringKey(fieldValues...)\n\t\t\t\tif _, ok := dataResults[dataKey]; !ok {\n\t\t\t\t\tresults = append(results, fieldValues)\n\t\t\t\t\tdataResults[dataKey] = []reflect.Value{elem}\n\t\t\t\t} else {\n\t\t\t\t\tdataResults[dataKey] = append(dataResults[dataKey], elem)\n\t\t\t\t}\n\t\t\t}\n\t\t}\n\t}\n\n\treturn dataResults, results\n}\n\n// GetIdentityFieldValuesMapFromValues get identity map from fields\nfunc GetIdentityFieldValuesMapFromValues(ctx context.Context, values []interface{}, fields []*Field) (map[string][]reflect.Value, [][]interface{}) {\n\tresultsMap := map[string][]reflect.Value{}\n\tresults := [][]interface{}{}\n\n\tfor _, v := range values {\n\t\trm, rs := GetIdentityFieldValuesMap(ctx, reflect.Indirect(reflect.ValueOf(v)), fields)\n\t\tfor k, v := range rm {\n\t\t\tresultsMap[k] = append(resultsMap[k], v...)\n\t\t}\n\t\tresults = append(results, rs...)\n\t}\n\treturn resultsMap, results\n}\n\n// ToQueryValues to query values\nfunc ToQueryValues(table string, foreignKeys []string, foreignValues [][]interface{}) (interface{}, []interface{}) {\n\tqueryValues := make([]interface{}, len(foreignValues))\n\tif len(foreignKeys) == 1 {\n\t\tfor idx, r := range foreignValues {\n\t\t\tqueryValues[idx] = r[0]\n\t\t}\n\n\t\treturn clause.Column{Table: table, Name: foreignKeys[0]}, queryValues\n\t}\n\n\tcolumns := make([]clause.Column, len(foreignKeys))\n\tfor idx, key := range foreignKeys {\n\t\tcolumns[idx] = clause.Column{Table: table, Name: key}\n\t}\n\n\tfor idx, r := range foreignValues {\n\t\tqueryValues[idx] = r\n\t}\n\n\treturn columns, queryValues\n}\n\ntype embeddedNamer struct {\n\tTable string\n\tNamer\n}\n',
            'schema/utils_test.go': 'package schema\n\nimport (\n\t"reflect"\n\t"testing"\n)\n\nfunc TestRemoveSettingFromTag(t *testing.T) {\n\ttags := map[string]string{\n\t\t`gorm:"before:value;column:db;after:value" other:"before:value;column:db;after:value"`:  `gorm:"before:value;after:value" other:"before:value;column:db;after:value"`,\n\t\t`gorm:"before:value;column:db;" other:"before:value;column:db;after:value"`:             `gorm:"before:value;" other:"before:value;column:db;after:value"`,\n\t\t`gorm:"before:value;column:db" other:"before:value;column:db;after:value"`:              `gorm:"before:value;" other:"before:value;column:db;after:value"`,\n\t\t`gorm:"column:db" other:"before:value;column:db;after:value"`:                           `gorm:"" other:"before:value;column:db;after:value"`,\n\t\t`gorm:"before:value;column:db ;after:value" other:"before:value;column:db;after:value"`: `gorm:"before:value;after:value" other:"before:value;column:db;after:value"`,\n\t\t`gorm:"before:value;column:db; after:value" other:"before:value;column:db;after:value"`: `gorm:"before:value; after:value" other:"before:value;column:db;after:value"`,\n\t\t`gorm:"before:value;column; after:value" other:"before:value;column:db;after:value"`:    `gorm:"before:value; after:value" other:"before:value;column:db;after:value"`,\n\t}\n\n\tfor k, v := range tags {\n\t\tif string(removeSettingFromTag(reflect.StructTag(k), "column")) != v {\n\t\t\tt.Errorf("%v after removeSettingFromTag should equal %v, but got %v", k, v, removeSettingFromTag(reflect.StructTag(k), "column"))\n\t\t}\n\t}\n}\n',
        }
