"""
Parameterized generator for GH935_spaCy_7026.

Source PR:    https://github.com/explosion/spaCy/pull/7026
Source Issue: N/A

Seed varies: renames 'aligns' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH935_spaCy_7026'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH935_spaCy_7026'
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
                files[fpath] = files[fpath].replace('aligns', 'aligns' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH935_spaCy_7026',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'explosion/spaCy',
                "pr_number": 7026,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/explosion/spaCy/pull/7026",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'spacy/cli/evaluate.py': 'from typing import Optional, List, Dict\nfrom wasabi import Printer\nfrom pathlib import Path\nimport re\nimport srsly\nfrom thinc.api import fix_random_seed\n\nfrom ..training import Corpus\nfrom ..tokens import Doc\nfrom ._util import app, Arg, Opt, setup_gpu, import_code\nfrom ..scorer import Scorer\nfrom .. import util\nfrom .. import displacy\n\n\n@app.command("evaluate")\ndef evaluate_cli(\n    # fmt: off\n    model: str = Arg(..., help="Model name or path"),\n    data_path: Path = Arg(..., help="Location of binary evaluation data in .spacy format", exists=True),\n    output: Optional[Path] = Opt(None, "--output", "-o", help="Output JSON file for metrics", dir_okay=False),\n    code_path: Optional[Path] = Opt(None, "--code", "-c", help="Path to Python file with additional code (registered functions) to be imported"),\n    use_gpu: int = Opt(-1, "--gpu-id", "-g", help="GPU ID or -1 for CPU"),\n    gold_preproc: bool = Opt(False, "--gold-preproc", "-G", help="Use gold preprocessing"),\n    displacy_path: Optional[Path] = Opt(None, "--displacy-path", "-dp", help="Directory to output rendered parses as HTML", exists=True, file_okay=False),\n    displacy_limit: int = Opt(25, "--displacy-limit", "-dl", help="Limit of parses to render as HTML"),\n    # fmt: on\n):\n    """\n    Evaluate a trained pipeline. Expects a loadable spaCy pipeline and evaluation\n    data in the binary .spacy format. The --gold-preproc option sets up the\n    evaluation examples with gold-standard sentences and tokens for the\n    predictions. Gold preprocessing helps the annotations align to the\n    tokenization, and may result in sequences of more consistent length. However,\n    it may reduce runtime accuracy due to train/test skew. To render a sample of\n    dependency parses in a HTML file, set as output directory as the\n    displacy_path argument.\n\n    DOCS: https://spacy.io/api/cli#evaluate\n    """\n    import_code(code_path)\n    evaluate(\n        model,\n        data_path,\n        output=output,\n        use_gpu=use_gpu,\n        gold_preproc=gold_preproc,\n        displacy_path=displacy_path,\n        displacy_limit=displacy_limit,\n        silent=False,\n    )\n\n\ndef evaluate(\n    model: str,\n    data_path: Path,\n    output: Optional[Path] = None,\n    use_gpu: int = -1,\n    gold_preproc: bool = False,\n    displacy_path: Optional[Path] = None,\n    displacy_limit: int = 25,\n    silent: bool = True,\n) -> Scorer:\n    msg = Printer(no_print=silent, pretty=not silent)\n    fix_random_seed()\n    setup_gpu(use_gpu)\n    data_path = util.ensure_path(data_path)\n    output_path = util.ensure_path(output)\n    displacy_path = util.ensure_path(displacy_path)\n    if not data_path.exists():\n        msg.fail("Evaluation data not found", data_path, exits=1)\n    if displacy_path and not displacy_path.exists():\n        msg.fail("Visualization output directory not found", displacy_path, exits=1)\n    corpus = Corpus(data_path, gold_preproc=gold_preproc)\n    nlp = util.load_model(model)\n    dev_dataset = list(corpus(nlp))\n    scores = nlp.evaluate(dev_dataset)\n    metrics = {\n        "TOK": "token_acc",\n        "TAG": "tag_acc",\n        "POS": "pos_acc",\n        "MORPH": "morph_acc",\n        "LEMMA": "lemma_acc",\n        "UAS": "dep_uas",\n        "LAS": "dep_las",\n        "NER P": "ents_p",\n        "NER R": "ents_r",\n        "NER F": "ents_f",\n        "TEXTCAT": "cats_score",\n        "SENT P": "sents_p",\n        "SENT R": "sents_r",\n        "SENT F": "sents_f",\n        "SPEED": "speed",\n    }\n    results = {}\n    data = {}\n    for metric, key in metrics.items():\n        if key in scores:\n            if key == "cats_score":\n                metric = metric + " (" + scores.get("cats_score_desc", "unk") + ")"\n            if isinstance(scores[key], (int, float)):\n                if key == "speed":\n                    results[metric] = f"{scores[key]:.0f}"\n                else:\n                    results[metric] = f"{scores[key]*100:.2f}"\n            else:\n                results[metric] = "-"\n            data[re.sub(r"[\\s/]", "_", key.lower())] = scores[key]\n\n    msg.table(results, title="Results")\n\n    if "morph_per_feat" in scores:\n        if scores["morph_per_feat"]:\n            print_prf_per_type(msg, scores["morph_per_feat"], "MORPH", "feat")\n            data["morph_per_feat"] = scores["morph_per_feat"]\n    if "dep_las_per_type" in scores:\n        if scores["dep_las_per_type"]:\n            print_prf_per_type(msg, scores["dep_las_per_type"], "LAS", "type")\n            data["dep_las_per_type"] = scores["dep_las_per_type"]\n    if "ents_per_type" in scores:\n        if scores["ents_per_type"]:\n            print_prf_per_type(msg, scores["ents_per_type"], "NER", "type")\n            data["ents_per_type"] = scores["ents_per_type"]\n    if "cats_f_per_type" in scores:\n        if scores["cats_f_per_type"]:\n            print_prf_per_type(msg, scores["cats_f_per_type"], "Textcat F", "label")\n            data["cats_f_per_type"] = scores["cats_f_per_type"]\n    if "cats_auc_per_type" in scores:\n        if scores["cats_auc_per_type"]:\n            print_textcats_auc_per_cat(msg, scores["cats_auc_per_type"])\n            data["cats_auc_per_type"] = scores["cats_auc_per_type"]\n\n    if displacy_path:\n        factory_names = [nlp.get_pipe_meta(pipe).factory for pipe in nlp.pipe_names]\n        docs = [ex.predicted for ex in dev_dataset]\n        render_deps = "parser" in factory_names\n        render_ents = "ner" in factory_names\n        render_parses(\n            docs,\n            displacy_path,\n            model_name=model,\n            limit=displacy_limit,\n            deps=render_deps,\n            ents=render_ents,\n        )\n        msg.good(f"Generated {displacy_limit} parses as HTML", displacy_path)\n\n    if output_path is not None:\n        srsly.write_json(output_path, data)\n        msg.good(f"Saved results to {output_path}")\n    return data\n\n\ndef render_parses(\n    docs: List[Doc],\n    output_path: Path,\n    model_name: str = "",\n    limit: int = 250,\n    deps: bool = True,\n    ents: bool = True,\n):\n    docs[0].user_data["title"] = model_name\n    if ents:\n        html = displacy.render(docs[:limit], style="ent", page=True)\n        with (output_path / "entities.html").open("w", encoding="utf8") as file_:\n            file_.write(html)\n    if deps:\n        html = displacy.render(\n            docs[:limit], style="dep", page=True, options={"compact": True}\n        )\n        with (output_path / "parses.html").open("w", encoding="utf8") as file_:\n            file_.write(html)\n\n\ndef print_prf_per_type(\n    msg: Printer, scores: Dict[str, Dict[str, float]], name: str, type: str\n) -> None:\n    data = [\n        (k, f"{v[\'p\']*100:.2f}", f"{v[\'r\']*100:.2f}", f"{v[\'f\']*100:.2f}")\n        for k, v in scores.items()\n    ]\n    msg.table(\n        data,\n        header=("", "P", "R", "F"),\n        aligns=("l", "r", "r", "r"),\n        title=f"{name} (per {type})",\n    )\n\n\ndef print_textcats_auc_per_cat(\n    msg: Printer, scores: Dict[str, Dict[str, float]]\n) -> None:\n    msg.table(\n        [(k, f"{v:.2f}") for k, v in scores.items()],\n        header=("", "ROC AUC"),\n        aligns=("l", "r"),\n        title="Textcat ROC AUC (per label)",\n    )\n',
            'spacy/tests/regression/test_issue7019.py': 'from spacy.cli.evaluate import print_textcats_auc_per_cat, print_prf_per_type\nfrom wasabi import msg\n\n\ndef test_issue7019():\n    scores = {"LABEL_A": 0.39829102, "LABEL_B": 0.938298329382, "LABEL_C": None}\n    print_textcats_auc_per_cat(msg, scores)\n    scores = {\n        "LABEL_A": {"p": 0.3420302, "r": 0.3929020, "f": 0.49823928932},\n        "LABEL_B": {"p": None, "r": None, "f": None},\n    }\n    print_prf_per_type(msg, scores, name="foo", type="bar")\n',
        }
