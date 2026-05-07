"""
Parameterized generator for GH523_testify_1782.

Source PR:    https://github.com/stretchr/testify/pull/1782
Source Issue: N/A

Seed varies: renames 'about' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH523_testify_1782'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH523_testify_1782'
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
                files[fpath] = files[fpath].replace('about', 'about' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH523_testify_1782',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'stretchr/testify',
                "pr_number": 1782,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/stretchr/testify/pull/1782",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            '_codegen/go.mod': 'module github.com/stretchr/testify/_codegen\n\ngo 1.11\n\nrequire github.com/ernesto-jimenez/gogen v0.0.0-20180125220232-d7d4131e6607\n',
            '_codegen/go.sum': 'github.com/ernesto-jimenez/gogen v0.0.0-20180125220232-d7d4131e6607 h1:cTavhURetDkezJCvxFggiyLeP40Mrk/TtVg2+ycw1Es=\ngithub.com/ernesto-jimenez/gogen v0.0.0-20180125220232-d7d4131e6607/go.mod h1:Cg4fM0vhYWOZdgM7RIOSTRNIc8/VT7CXClC3Ni86lu4=\n',
            '_codegen/main.go': '// This program reads all assertion functions from the assert package and\n// automatically generates the corresponding requires and forwarded assertions\n\npackage main\n\nimport (\n\t"bytes"\n\t"flag"\n\t"fmt"\n\t"go/ast"\n\t"go/build"\n\t"go/doc"\n\t"go/format"\n\t"go/importer"\n\t"go/parser"\n\t"go/token"\n\t"go/types"\n\t"io"\n\t"log"\n\t"os"\n\t"path"\n\t"regexp"\n\t"strings"\n\t"text/template"\n\n\t"github.com/ernesto-jimenez/gogen/imports"\n)\n\nvar (\n\tpkg       = flag.String("assert-path", "github.com/stretchr/testify/assert", "Path to the assert package")\n\tincludeF  = flag.Bool("include-format-funcs", false, "include format functions such as Errorf and Equalf")\n\toutputPkg = flag.String("output-package", "", "package for the resulting code")\n\ttmplFile  = flag.String("template", "", "What file to load the function template from")\n\tout       = flag.String("out", "", "What file to write the source code to")\n)\n\nfunc main() {\n\tflag.Parse()\n\n\tscope, docs, err := parsePackageSource(*pkg)\n\tif err != nil {\n\t\tlog.Fatal(err)\n\t}\n\n\timporter, funcs, err := analyzeCode(scope, docs)\n\tif err != nil {\n\t\tlog.Fatal(err)\n\t}\n\n\tif err := generateCode(importer, funcs); err != nil {\n\t\tlog.Fatal(err)\n\t}\n}\n\nfunc generateCode(importer imports.Importer, funcs []testFunc) error {\n\tbuff := bytes.NewBuffer(nil)\n\n\ttmplHead, tmplFunc, err := parseTemplates()\n\tif err != nil {\n\t\treturn err\n\t}\n\n\t// Generate header\n\tif err := tmplHead.Execute(buff, struct {\n\t\tName    string\n\t\tImports map[string]string\n\t}{\n\t\t*outputPkg,\n\t\timporter.Imports(),\n\t}); err != nil {\n\t\treturn err\n\t}\n\n\t// Generate funcs\n\tfor _, fn := range funcs {\n\t\tbuff.Write([]byte("\\n\\n"))\n\t\tif err := tmplFunc.Execute(buff, &fn); err != nil {\n\t\t\treturn err\n\t\t}\n\t}\n\n\tcode, err := format.Source(buff.Bytes())\n\tif err != nil {\n\t\treturn err\n\t}\n\n\t// Write file\n\toutput, err := outputFile()\n\tif err != nil {\n\t\treturn err\n\t}\n\tdefer output.Close()\n\t_, err = io.Copy(output, bytes.NewReader(code))\n\treturn err\n}\n\nfunc parseTemplates() (*template.Template, *template.Template, error) {\n\ttmplHead, err := template.New("header").Parse(headerTemplate)\n\tif err != nil {\n\t\treturn nil, nil, err\n\t}\n\tif *tmplFile != "" {\n\t\tf, err := os.ReadFile(*tmplFile)\n\t\tif err != nil {\n\t\t\treturn nil, nil, err\n\t\t}\n\t\tfuncTemplate = string(f)\n\t}\n\ttmpl, err := template.New("function").Funcs(template.FuncMap{\n\t\t"replace": strings.ReplaceAll,\n\t}).Parse(funcTemplate)\n\tif err != nil {\n\t\treturn nil, nil, err\n\t}\n\treturn tmplHead, tmpl, nil\n}\n\nfunc outputFile() (*os.File, error) {\n\tfilename := *out\n\tif filename == "-" || (filename == "" && *tmplFile == "") {\n\t\treturn os.Stdout, nil\n\t}\n\tif filename == "" {\n\t\tfilename = strings.TrimSuffix(strings.TrimSuffix(*tmplFile, ".tmpl"), ".go") + ".go"\n\t}\n\treturn os.Create(filename)\n}\n\n// analyzeCode takes the types scope and the docs and returns the import\n// information and information about all the assertion functions.\nfunc analyzeCode(scope *types.Scope, docs *doc.Package) (imports.Importer, []testFunc, error) {\n\ttestingT := scope.Lookup("TestingT").Type().Underlying().(*types.Interface)\n\n\timporter := imports.New(*outputPkg)\n\tvar funcs []testFunc\n\t// Go through all the top level functions\n\tfor _, fdocs := range docs.Funcs {\n\t\t// Find the function\n\t\tobj := scope.Lookup(fdocs.Name)\n\n\t\tfn, ok := obj.(*types.Func)\n\t\tif !ok {\n\t\t\tcontinue\n\t\t}\n\t\t// Check function signature has at least two arguments\n\t\tsig := fn.Type().(*types.Signature)\n\t\tif sig.Params().Len() < 2 {\n\t\t\tcontinue\n\t\t}\n\t\t// Check first argument is of type testingT\n\t\tfirst, ok := sig.Params().At(0).Type().(*types.Named)\n\t\tif !ok {\n\t\t\tcontinue\n\t\t}\n\t\tfirstType, ok := first.Underlying().(*types.Interface)\n\t\tif !ok {\n\t\t\tcontinue\n\t\t}\n\t\tif !types.Implements(firstType, testingT) {\n\t\t\tcontinue\n\t\t}\n\n\t\t// Skip functions ending with f\n\t\tif strings.HasSuffix(fdocs.Name, "f") && !*includeF {\n\t\t\tcontinue\n\t\t}\n\n\t\tfuncs = append(funcs, testFunc{*outputPkg, fdocs, fn})\n\t\timporter.AddImportsFrom(sig.Params())\n\t}\n\treturn importer, funcs, nil\n}\n\n// parsePackageSource returns the types scope and the package documentation from the package\nfunc parsePackageSource(pkg string) (*types.Scope, *doc.Package, error) {\n\tpd, err := build.Import(pkg, ".", 0)\n\tif err != nil {\n\t\treturn nil, nil, err\n\t}\n\n\tfset := token.NewFileSet()\n\tfiles := make(map[string]*ast.File)\n\tfileList := make([]*ast.File, len(pd.GoFiles))\n\tfor i, fname := range pd.GoFiles {\n\t\tsrc, err := os.ReadFile(path.Join(pd.Dir, fname))\n\t\tif err != nil {\n\t\t\treturn nil, nil, err\n\t\t}\n\t\tf, err := parser.ParseFile(fset, fname, src, parser.ParseComments|parser.AllErrors)\n\t\tif err != nil {\n\t\t\treturn nil, nil, err\n\t\t}\n\t\tfiles[fname] = f\n\t\tfileList[i] = f\n\t}\n\n\tcfg := types.Config{\n\t\tImporter: importer.For("source", nil),\n\t}\n\tinfo := types.Info{\n\t\tDefs: make(map[*ast.Ident]types.Object),\n\t}\n\ttp, err := cfg.Check(pkg, fset, fileList, &info)\n\tif err != nil {\n\t\treturn nil, nil, err\n\t}\n\n\tscope := tp.Scope()\n\n\tap, _ := ast.NewPackage(fset, files, nil, nil)\n\tdocs := doc.New(ap, pkg, 0)\n\n\treturn scope, docs, nil\n}\n\ntype testFunc struct {\n\tCurrentPkg string\n\tDocInfo    *doc.Func\n\tTypeInfo   *types.Func\n}\n\nfunc (f *testFunc) Qualifier(p *types.Package) string {\n\tif p == nil || p.Name() == f.CurrentPkg {\n\t\treturn ""\n\t}\n\treturn p.Name()\n}\n\nfunc (f *testFunc) Params() string {\n\tsig := f.TypeInfo.Type().(*types.Signature)\n\tparams := sig.Params()\n\tp := ""\n\tcomma := ""\n\tto := params.Len()\n\tvar i int\n\n\tif sig.Variadic() {\n\t\tto--\n\t}\n\tfor i = 1; i < to; i++ {\n\t\tparam := params.At(i)\n\t\tp += fmt.Sprintf("%s%s %s", comma, param.Name(), types.TypeString(param.Type(), f.Qualifier))\n\t\tcomma = ", "\n\t}\n\tif sig.Variadic() {\n\t\tparam := params.At(params.Len() - 1)\n\t\tp += fmt.Sprintf("%s%s ...%s", comma, param.Name(), types.TypeString(param.Type().(*types.Slice).Elem(), f.Qualifier))\n\t}\n\treturn p\n}\n\nfunc (f *testFunc) ForwardedParams() string {\n\tsig := f.TypeInfo.Type().(*types.Signature)\n\tparams := sig.Params()\n\tp := ""\n\tcomma := ""\n\tto := params.Len()\n\tvar i int\n\n\tif sig.Variadic() {\n\t\tto--\n\t}\n\tfor i = 1; i < to; i++ {\n\t\tparam := params.At(i)\n\t\tp += fmt.Sprintf("%s%s", comma, param.Name())\n\t\tcomma = ", "\n\t}\n\tif sig.Variadic() {\n\t\tparam := params.At(params.Len() - 1)\n\t\tp += fmt.Sprintf("%s%s...", comma, param.Name())\n\t}\n\treturn p\n}\n\nfunc (f *testFunc) ParamsFormat() string {\n\treturn strings.Replace(f.Params(), "msgAndArgs", "msg string, args", 1)\n}\n\nfunc (f *testFunc) ForwardedParamsFormat() string {\n\treturn strings.Replace(f.ForwardedParams(), "msgAndArgs", "append([]interface{}{msg}, args...)", 1)\n}\n\nfunc (f *testFunc) Comment() string {\n\treturn "// " + strings.Replace(strings.TrimSpace(f.DocInfo.Doc), "\\n", "\\n// ", -1)\n}\n\nfunc (f *testFunc) CommentFormat() string {\n\tsearch := fmt.Sprintf("%s", f.DocInfo.Name)\n\treplace := fmt.Sprintf("%sf", f.DocInfo.Name)\n\tcomment := strings.Replace(f.Comment(), search, replace, -1)\n\texp := regexp.MustCompile(replace + `\\(((\\(\\)|[^\\n])+)\\)`)\n\treturn exp.ReplaceAllString(comment, replace+`($1, "error message %s", "formatted")`)\n}\n\nfunc (f *testFunc) CommentWithoutT(receiver string) string {\n\tsearch := fmt.Sprintf("assert.%s(t, ", f.DocInfo.Name)\n\treplace := fmt.Sprintf("%s.%s(", receiver, f.DocInfo.Name)\n\treturn strings.Replace(f.Comment(), search, replace, -1)\n}\n\n// Standard header https://go.dev/s/generatedcode.\nvar headerTemplate = `// Code generated with github.com/stretchr/testify/_codegen; DO NOT EDIT.\n\npackage {{.Name}}\n\nimport (\n{{range $path, $name := .Imports}}\n\t{{$name}} "{{$path}}"{{end}}\n)\n`\n\nvar funcTemplate = `{{.Comment}}\nfunc (fwd *AssertionsForwarder) {{.DocInfo.Name}}({{.Params}}) bool {\n\treturn assert.{{.DocInfo.Name}}({{.ForwardedParams}})\n}`\n',
        }
