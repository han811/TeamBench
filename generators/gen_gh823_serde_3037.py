"""
Parameterized generator for GH823_serde_3037.

Source PR:    https://github.com/serde-rs/serde/pull/3037
Source Issue: N/A

Seed varies: renames 'attr' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH823_serde_3037'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH823_serde_3037'
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
                files[fpath] = files[fpath].replace('attr', 'attr' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH823_serde_3037',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'serde-rs/serde',
                "pr_number": 3037,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/serde-rs/serde/pull/3037",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'serde_derive/src/internals/ast.rs': '//! A Serde ast, parsed from the Syn ast and ready to generate Rust code.\n\nuse crate::internals::{attr, check, Ctxt, Derive};\nuse proc_macro2::Ident;\nuse syn::punctuated::Punctuated;\nuse syn::Token;\n\n/// A source data structure annotated with `#[derive(Serialize)]` and/or `#[derive(Deserialize)]`,\n/// parsed into an internal representation.\npub struct Container<\'a> {\n    /// The struct or enum name (without generics).\n    pub ident: syn::Ident,\n    /// Attributes on the structure, parsed for Serde.\n    pub attrs: attr::Container,\n    /// The contents of the struct or enum.\n    pub data: Data<\'a>,\n    /// Any generics on the struct or enum.\n    pub generics: &\'a syn::Generics,\n    /// Original input.\n    pub original: &\'a syn::DeriveInput,\n}\n\n/// The fields of a struct or enum.\n///\n/// Analogous to `syn::Data`.\npub enum Data<\'a> {\n    Enum(Vec<Variant<\'a>>),\n    Struct(Style, Vec<Field<\'a>>),\n}\n\n/// A variant of an enum.\npub struct Variant<\'a> {\n    pub ident: syn::Ident,\n    pub attrs: attr::Variant,\n    pub style: Style,\n    pub fields: Vec<Field<\'a>>,\n    pub original: &\'a syn::Variant,\n}\n\n/// A field of a struct.\npub struct Field<\'a> {\n    pub member: syn::Member,\n    pub attrs: attr::Field,\n    pub ty: &\'a syn::Type,\n    pub original: &\'a syn::Field,\n}\n\n#[derive(Copy, Clone)]\npub enum Style {\n    /// Named fields.\n    Struct,\n    /// Many unnamed fields.\n    Tuple,\n    /// One unnamed field.\n    Newtype,\n    /// No fields.\n    Unit,\n}\n\nimpl<\'a> Container<\'a> {\n    /// Convert the raw Syn ast into a parsed container object, collecting errors in `cx`.\n    pub fn from_ast(\n        cx: &Ctxt,\n        item: &\'a syn::DeriveInput,\n        derive: Derive,\n        private: &Ident,\n    ) -> Option<Container<\'a>> {\n        let attrs = attr::Container::from_ast(cx, item);\n\n        let mut data = match &item.data {\n            syn::Data::Enum(data) => {\n                Data::Enum(enum_from_ast(cx, &data.variants, attrs.default(), private))\n            }\n            syn::Data::Struct(data) => {\n                let (style, fields) =\n                    struct_from_ast(cx, &data.fields, None, attrs.default(), private);\n                Data::Struct(style, fields)\n            }\n            syn::Data::Union(_) => {\n                cx.error_spanned_by(item, "Serde does not support derive for unions");\n                return None;\n            }\n        };\n\n        match &mut data {\n            Data::Enum(variants) => {\n                for variant in variants {\n                    variant.attrs.rename_by_rules(attrs.rename_all_rules());\n                    for field in &mut variant.fields {\n                        field.attrs.rename_by_rules(\n                            variant\n                                .attrs\n                                .rename_all_rules()\n                                .or(attrs.rename_all_fields_rules()),\n                        );\n                    }\n                }\n            }\n            Data::Struct(_, fields) => {\n                for field in fields {\n                    field.attrs.rename_by_rules(attrs.rename_all_rules());\n                }\n            }\n        }\n\n        let mut item = Container {\n            ident: item.ident.clone(),\n            attrs,\n            data,\n            generics: &item.generics,\n            original: item,\n        };\n        check::check(cx, &mut item, derive);\n        Some(item)\n    }\n}\n\nimpl<\'a> Data<\'a> {\n    pub fn all_fields(&\'a self) -> Box<dyn Iterator<Item = &\'a Field<\'a>> + \'a> {\n        match self {\n            Data::Enum(variants) => {\n                Box::new(variants.iter().flat_map(|variant| variant.fields.iter()))\n            }\n            Data::Struct(_, fields) => Box::new(fields.iter()),\n        }\n    }\n\n    pub fn has_getter(&self) -> bool {\n        self.all_fields().any(|f| f.attrs.getter().is_some())\n    }\n}\n\nfn enum_from_ast<\'a>(\n    cx: &Ctxt,\n    variants: &\'a Punctuated<syn::Variant, Token![,]>,\n    container_default: &attr::Default,\n    private: &Ident,\n) -> Vec<Variant<\'a>> {\n    let variants: Vec<Variant> = variants\n        .iter()\n        .map(|variant| {\n            let attrs = attr::Variant::from_ast(cx, variant);\n            let (style, fields) = struct_from_ast(\n                cx,\n                &variant.fields,\n                Some(&attrs),\n                container_default,\n                private,\n            );\n            Variant {\n                ident: variant.ident.clone(),\n                attrs,\n                style,\n                fields,\n                original: variant,\n            }\n        })\n        .collect();\n\n    let index_of_last_tagged_variant = variants\n        .iter()\n        .rposition(|variant| !variant.attrs.untagged());\n    if let Some(index_of_last_tagged_variant) = index_of_last_tagged_variant {\n        for variant in &variants[..index_of_last_tagged_variant] {\n            if variant.attrs.untagged() {\n                cx.error_spanned_by(&variant.ident, "all variants with the #[serde(untagged)] attribute must be placed at the end of the enum");\n            }\n        }\n    }\n\n    variants\n}\n\nfn struct_from_ast<\'a>(\n    cx: &Ctxt,\n    fields: &\'a syn::Fields,\n    attrs: Option<&attr::Variant>,\n    container_default: &attr::Default,\n    private: &Ident,\n) -> (Style, Vec<Field<\'a>>) {\n    match fields {\n        syn::Fields::Named(fields) => (\n            Style::Struct,\n            fields_from_ast(cx, &fields.named, attrs, container_default, private),\n        ),\n        syn::Fields::Unnamed(fields) if fields.unnamed.len() == 1 => (\n            Style::Newtype,\n            fields_from_ast(cx, &fields.unnamed, attrs, container_default, private),\n        ),\n        syn::Fields::Unnamed(fields) => (\n            Style::Tuple,\n            fields_from_ast(cx, &fields.unnamed, attrs, container_default, private),\n        ),\n        syn::Fields::Unit => (Style::Unit, Vec::new()),\n    }\n}\n\nfn fields_from_ast<\'a>(\n    cx: &Ctxt,\n    fields: &\'a Punctuated<syn::Field, Token![,]>,\n    attrs: Option<&attr::Variant>,\n    container_default: &attr::Default,\n    private: &Ident,\n) -> Vec<Field<\'a>> {\n    fields\n        .iter()\n        .enumerate()\n        .map(|(i, field)| Field {\n            member: match &field.ident {\n                Some(ident) => syn::Member::Named(ident.clone()),\n                None => syn::Member::Unnamed(i.into()),\n            },\n            attrs: attr::Field::from_ast(cx, i, field, attrs, container_default, private),\n            ty: &field.ty,\n            original: field,\n        })\n        .collect()\n}\n',
        }
