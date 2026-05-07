"""
Parameterized generator for GH49_gorm_7717.

Source PR:    https://github.com/go-gorm/gorm/pull/7717
Source Issue: https://github.com/go-gorm/gorm/issues/7715

Seed varies: renames 'after' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH49_gorm_7717'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH49_gorm_7717'
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
                files[fpath] = files[fpath].replace('after', 'after' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH49_gorm_7717',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'go-gorm/gorm',
                "pr_number": 7717,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/go-gorm/gorm/pull/7717",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'utils/utils.go': 'package utils\n\nimport (\n\t"database/sql/driver"\n\t"fmt"\n\t"path/filepath"\n\t"reflect"\n\t"runtime"\n\t"strconv"\n\t"strings"\n\t"unicode"\n)\n\nvar gormSourceDir string\n\nfunc init() {\n\t_, file, _, _ := runtime.Caller(0)\n\t// compatible solution to get gorm source directory with various operating systems\n\tgormSourceDir = sourceDir(file)\n}\n\nfunc sourceDir(file string) string {\n\tdir := filepath.Dir(file)\n\tdir = filepath.Dir(dir)\n\n\ts := filepath.Dir(dir)\n\tif filepath.Base(s) != "gorm.io" {\n\t\ts = dir\n\t}\n\treturn filepath.ToSlash(s) + "/"\n}\n\n// CallerFrame retrieves the first relevant stack frame outside of GORM\'s internal implementation files.\n// It skips:\n//   - GORM\'s core source files (identified by gormSourceDir prefix)\n//   - Exclude test files (*_test.go)\n//   - go-gorm/gen\'s Generated files (*.gen.go)\nfunc CallerFrame() runtime.Frame {\n\tpcs := [13]uintptr{}\n\t// the third caller usually from gorm internal\n\tlen := runtime.Callers(3, pcs[:])\n\tframes := runtime.CallersFrames(pcs[:len])\n\tfor i := 0; i < len; i++ {\n\t\t// second return value is "more", not "ok"\n\t\tframe, _ := frames.Next()\n\t\tif (!strings.HasPrefix(frame.File, gormSourceDir) ||\n\t\t\tstrings.HasSuffix(frame.File, "_test.go")) && !strings.HasSuffix(frame.File, ".gen.go") {\n\t\t\treturn frame\n\t\t}\n\t}\n\n\treturn runtime.Frame{}\n}\n\n// FileWithLineNum return the file name and line number of the current file\nfunc FileWithLineNum() string {\n\tframe := CallerFrame()\n\tif frame.PC != 0 {\n\t\treturn string(strconv.AppendInt(append([]byte(frame.File), \':\'), int64(frame.Line), 10))\n\t}\n\n\treturn ""\n}\n\nfunc IsInvalidDBNameChar(c rune) bool {\n\treturn !unicode.IsLetter(c) && !unicode.IsNumber(c) && c != \'.\' && c != \'*\' && c != \'_\' && c != \'$\' && c != \'@\'\n}\n\n// CheckTruth check string true or not\nfunc CheckTruth(vals ...string) bool {\n\tfor _, val := range vals {\n\t\tif val != "" && !strings.EqualFold(val, "false") {\n\t\t\treturn true\n\t\t}\n\t}\n\treturn false\n}\n\nfunc ToStringKey(values ...interface{}) string {\n\tresults := make([]string, len(values))\n\n\tfor idx, value := range values {\n\t\tif valuer, ok := value.(driver.Valuer); ok {\n\t\t\tvalue, _ = valuer.Value()\n\t\t}\n\n\t\tswitch v := value.(type) {\n\t\tcase string:\n\t\t\tresults[idx] = v\n\t\tcase []byte:\n\t\t\tresults[idx] = string(v)\n\t\tcase uint:\n\t\t\tresults[idx] = strconv.FormatUint(uint64(v), 10)\n\t\tdefault:\n\t\t\tresults[idx] = "nil"\n\t\t\tvv := reflect.ValueOf(v)\n\t\t\tif vv.IsValid() && !vv.IsZero() {\n\t\t\t\tresults[idx] = fmt.Sprint(reflect.Indirect(vv).Interface())\n\t\t\t}\n\t\t}\n\t}\n\n\treturn strings.Join(results, "_")\n}\n\nfunc Contains(elems []string, elem string) bool {\n\tfor _, e := range elems {\n\t\tif elem == e {\n\t\t\treturn true\n\t\t}\n\t}\n\treturn false\n}\n\nfunc AssertEqual(x, y interface{}) bool {\n\tif reflect.DeepEqual(x, y) {\n\t\treturn true\n\t}\n\tif x == nil || y == nil {\n\t\treturn false\n\t}\n\n\txval := reflect.ValueOf(x)\n\tyval := reflect.ValueOf(y)\n\tif xval.Kind() == reflect.Ptr && xval.IsNil() ||\n\t\tyval.Kind() == reflect.Ptr && yval.IsNil() {\n\t\treturn false\n\t}\n\n\tif valuer, ok := x.(driver.Valuer); ok {\n\t\tx, _ = valuer.Value()\n\t}\n\tif valuer, ok := y.(driver.Valuer); ok {\n\t\ty, _ = valuer.Value()\n\t}\n\treturn reflect.DeepEqual(x, y)\n}\n\nfunc ToString(value interface{}) string {\n\tswitch v := value.(type) {\n\tcase string:\n\t\treturn v\n\tcase int:\n\t\treturn strconv.FormatInt(int64(v), 10)\n\tcase int8:\n\t\treturn strconv.FormatInt(int64(v), 10)\n\tcase int16:\n\t\treturn strconv.FormatInt(int64(v), 10)\n\tcase int32:\n\t\treturn strconv.FormatInt(int64(v), 10)\n\tcase int64:\n\t\treturn strconv.FormatInt(v, 10)\n\tcase uint:\n\t\treturn strconv.FormatUint(uint64(v), 10)\n\tcase uint8:\n\t\treturn strconv.FormatUint(uint64(v), 10)\n\tcase uint16:\n\t\treturn strconv.FormatUint(uint64(v), 10)\n\tcase uint32:\n\t\treturn strconv.FormatUint(uint64(v), 10)\n\tcase uint64:\n\t\treturn strconv.FormatUint(v, 10)\n\t}\n\treturn ""\n}\n\nconst nestedRelationSplit = "__"\n\n// NestedRelationName nested relationships like `Manager__Company`\nfunc NestedRelationName(prefix, name string) string {\n\treturn prefix + nestedRelationSplit + name\n}\n\n// SplitNestedRelationName Split nested relationships to `[]string{"Manager","Company"}`\nfunc SplitNestedRelationName(name string) []string {\n\treturn strings.Split(name, nestedRelationSplit)\n}\n\n// JoinNestedRelationNames nested relationships like `Manager__Company`\nfunc JoinNestedRelationNames(relationNames []string) string {\n\treturn strings.Join(relationNames, nestedRelationSplit)\n}\n\n// RTrimSlice Right trims the given slice by given length\nfunc RTrimSlice[T any](v []T, trimLen int) []T {\n\tif trimLen >= len(v) { // trimLen greater than slice len means fully sliced\n\t\treturn v[:0]\n\t}\n\tif trimLen < 0 { // negative trimLen is ignored\n\t\treturn v[:]\n\t}\n\treturn v[:len(v)-trimLen]\n}\n',
            'utils/utils_test.go': 'package utils\n\nimport (\n\t"database/sql"\n\t"database/sql/driver"\n\t"errors"\n\t"math"\n\t"strings"\n\t"testing"\n\t"time"\n)\n\nfunc TestIsInvalidDBNameChar(t *testing.T) {\n\tfor _, db := range []string{"db", "dbName", "db_name", "db1", "1dbname", "db$name"} {\n\t\tif fields := strings.FieldsFunc(db, IsInvalidDBNameChar); len(fields) != 1 {\n\t\t\tt.Fatalf("failed to parse db name %v", db)\n\t\t}\n\t}\n}\n\nfunc TestCheckTruth(t *testing.T) {\n\tcheckTruthTests := []struct {\n\t\tv   string\n\t\tout bool\n\t}{\n\t\t{"123", true},\n\t\t{"true", true},\n\t\t{"", false},\n\t\t{"false", false},\n\t\t{"False", false},\n\t\t{"FALSE", false},\n\t\t{"\\u0046alse", false},\n\t}\n\n\tfor _, test := range checkTruthTests {\n\t\tt.Run(test.v, func(t *testing.T) {\n\t\t\tif out := CheckTruth(test.v); out != test.out {\n\t\t\t\tt.Errorf("CheckTruth(%s) want: %t, got: %t", test.v, test.out, out)\n\t\t\t}\n\t\t})\n\t}\n}\n\nfunc TestToStringKey(t *testing.T) {\n\tcases := []struct {\n\t\tvalues []interface{}\n\t\tkey    string\n\t}{\n\t\t{[]interface{}{"a"}, "a"},\n\t\t{[]interface{}{1, 2, 3}, "1_2_3"},\n\t\t{[]interface{}{1, nil, 3}, "1_nil_3"},\n\t\t{[]interface{}{[]interface{}{1, 2, 3}}, "[1 2 3]"},\n\t\t{[]interface{}{[]interface{}{"1", "2", "3"}}, "[1 2 3]"},\n\t\t{[]interface{}{[]interface{}{"1", nil, "3"}}, "[1 <nil> 3]"},\n\t}\n\tfor _, c := range cases {\n\t\tif key := ToStringKey(c.values...); key != c.key {\n\t\t\tt.Errorf("%v: expected %v, got %v", c.values, c.key, key)\n\t\t}\n\t}\n}\n\nfunc TestContains(t *testing.T) {\n\tcontainsTests := []struct {\n\t\tname  string\n\t\telems []string\n\t\telem  string\n\t\tout   bool\n\t}{\n\t\t{"exists", []string{"1", "2", "3"}, "1", true},\n\t\t{"not exists", []string{"1", "2", "3"}, "4", false},\n\t}\n\tfor _, test := range containsTests {\n\t\tt.Run(test.name, func(t *testing.T) {\n\t\t\tif out := Contains(test.elems, test.elem); test.out != out {\n\t\t\t\tt.Errorf("Contains(%v, %s) want: %t, got: %t", test.elems, test.elem, test.out, out)\n\t\t\t}\n\t\t})\n\t}\n}\n\ntype ModifyAt sql.NullTime\n\n// Value return a Unix time.\nfunc (n ModifyAt) Value() (driver.Value, error) {\n\tif !n.Valid {\n\t\treturn nil, nil\n\t}\n\treturn n.Time.Unix(), nil\n}\n\nfunc TestAssertEqual(t *testing.T) {\n\tnow := time.Now()\n\tassertEqualTests := []struct {\n\t\tname     string\n\t\tsrc, dst interface{}\n\t\tout      bool\n\t}{\n\t\t{"error equal", errors.New("1"), errors.New("1"), true},\n\t\t{"error not equal", errors.New("1"), errors.New("2"), false},\n\t\t{"driver.Valuer equal", ModifyAt{Time: now, Valid: true}, ModifyAt{Time: now, Valid: true}, true},\n\t\t{"driver.Valuer not equal", ModifyAt{Time: now, Valid: true}, ModifyAt{Time: now.Add(time.Second), Valid: true}, false},\n\t\t{"driver.Valuer equal (ptr to nil ptr)", (*ModifyAt)(nil), &ModifyAt{}, false},\n\t}\n\tfor _, test := range assertEqualTests {\n\t\tt.Run(test.name, func(t *testing.T) {\n\t\t\tif out := AssertEqual(test.src, test.dst); test.out != out {\n\t\t\t\tt.Errorf("AssertEqual(%v, %v) want: %t, got: %t", test.src, test.dst, test.out, out)\n\t\t\t}\n\t\t})\n\t}\n}\n\nfunc TestToString(t *testing.T) {\n\ttests := []struct {\n\t\tname string\n\t\tin   interface{}\n\t\tout  string\n\t}{\n\t\t{"int", math.MaxInt64, "9223372036854775807"},\n\t\t{"int8", int8(math.MaxInt8), "127"},\n\t\t{"int16", int16(math.MaxInt16), "32767"},\n\t\t{"int32", int32(math.MaxInt32), "2147483647"},\n\t\t{"int64", int64(math.MaxInt64), "9223372036854775807"},\n\t\t{"uint", uint(math.MaxUint64), "18446744073709551615"},\n\t\t{"uint8", uint8(math.MaxUint8), "255"},\n\t\t{"uint16", uint16(math.MaxUint16), "65535"},\n\t\t{"uint32", uint32(math.MaxUint32), "4294967295"},\n\t\t{"uint64", uint64(math.MaxUint64), "18446744073709551615"},\n\t\t{"string", "abc", "abc"},\n\t\t{"other", true, ""},\n\t}\n\tfor _, test := range tests {\n\t\tt.Run(test.name, func(t *testing.T) {\n\t\t\tif out := ToString(test.in); test.out != out {\n\t\t\t\tt.Fatalf("ToString(%v) want: %s, got: %s", test.in, test.out, out)\n\t\t\t}\n\t\t})\n\t}\n}\n\nfunc TestRTrimSlice(t *testing.T) {\n\ttests := []struct {\n\t\tname     string\n\t\tinput    []int\n\t\ttrimLen  int\n\t\texpected []int\n\t}{\n\t\t{\n\t\t\tname:     "Trim two elements from end",\n\t\t\tinput:    []int{1, 2, 3, 4, 5},\n\t\t\ttrimLen:  2,\n\t\t\texpected: []int{1, 2, 3},\n\t\t},\n\t\t{\n\t\t\tname:     "Trim entire slice",\n\t\t\tinput:    []int{1, 2, 3},\n\t\t\ttrimLen:  3,\n\t\t\texpected: []int{},\n\t\t},\n\t\t{\n\t\t\tname:     "Trim length greater than slice length",\n\t\t\tinput:    []int{1, 2, 3},\n\t\t\ttrimLen:  5,\n\t\t\texpected: []int{},\n\t\t},\n\t\t{\n\t\t\tname:     "Zero trim length",\n\t\t\tinput:    []int{1, 2, 3},\n\t\t\ttrimLen:  0,\n\t\t\texpected: []int{1, 2, 3},\n\t\t},\n\t\t{\n\t\t\tname:     "Trim one element from end",\n\t\t\tinput:    []int{1, 2, 3},\n\t\t\ttrimLen:  1,\n\t\t\texpected: []int{1, 2},\n\t\t},\n\t\t{\n\t\t\tname:     "Empty slice",\n\t\t\tinput:    []int{},\n\t\t\ttrimLen:  2,\n\t\t\texpected: []int{},\n\t\t},\n\t\t{\n\t\t\tname:     "Negative trim length (should be treated as zero)",\n\t\t\tinput:    []int{1, 2, 3},\n\t\t\ttrimLen:  -1,\n\t\t\texpected: []int{1, 2, 3},\n\t\t},\n\t}\n\n\tfor _, testcase := range tests {\n\t\tt.Run(testcase.name, func(t *testing.T) {\n\t\t\tresult := RTrimSlice(testcase.input, testcase.trimLen)\n\t\t\tif !AssertEqual(result, testcase.expected) {\n\t\t\t\tt.Errorf("RTrimSlice(%v, %d) = %v; want %v", testcase.input, testcase.trimLen, result, testcase.expected)\n\t\t\t}\n\t\t})\n\t}\n}\n',
        }
