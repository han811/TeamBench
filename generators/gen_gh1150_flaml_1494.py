"""
Parameterized generator for GH1150_FLAML_1494.

Source PR:    https://github.com/microsoft/FLAML/pull/1494
Source Issue: https://github.com/microsoft/FLAML/issues/1246

Seed varies: renames 'added' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH1150_FLAML_1494'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH1150_FLAML_1494'
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
            task_id='GH1150_FLAML_1494',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'microsoft/FLAML',
                "pr_number": 1494,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/microsoft/FLAML/pull/1494",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'flaml/tune/searcher/search_thread.py': '# !\n#  * Copyright (c) Microsoft Corporation. All rights reserved.\n#  * Licensed under the MIT License. See LICENSE file in the\n#  * project root for license information.\nfrom typing import Dict, Optional\n\nimport numpy as np\n\ntry:\n    from ray import __version__ as ray_version\n\n    assert ray_version >= "1.10.0"\n    if ray_version.startswith("1."):\n        from ray.tune.suggest import Searcher\n    else:\n        from ray.tune.search import Searcher\nexcept (ImportError, AssertionError):\n    from .suggestion import Searcher\nimport logging\n\nfrom ..result import TIME_TOTAL_S\nfrom ..space import add_cost_to_space, unflatten_hierarchical\nfrom .flow2 import FLOW2\n\nlogger = logging.getLogger(__name__)\n\n\nclass SearchThread:\n    """Class of global or local search thread."""\n\n    def __init__(\n        self,\n        mode: str = "min",\n        search_alg: Optional[Searcher] = None,\n        cost_attr: Optional[str] = TIME_TOTAL_S,\n        eps: Optional[float] = 1.0,\n    ):\n        """When search_alg is omitted, use local search FLOW2."""\n        self._search_alg = search_alg\n        self._is_ls = isinstance(search_alg, FLOW2)\n        self._mode = mode\n        self._metric_op = 1 if mode == "min" else -1\n        self.cost_best = self.cost_last = self.cost_total = self.cost_best1 = getattr(search_alg, "cost_incumbent", 0)\n        self._eps = eps\n        self.cost_best2 = 0\n        self.obj_best1 = self.obj_best2 = getattr(search_alg, "best_obj", np.inf)  # inherently minimize\n        self.best_result = None\n        # eci: estimated cost for improvement\n        self.eci = self.cost_best\n        self.priority = self.speed = 0\n        self._init_config = True\n        self.running = 0  # the number of running trials from the thread\n        self.cost_attr = cost_attr\n        if search_alg:\n            self.space = self._space = search_alg.space  # unflattened space\n            if self.space and not isinstance(search_alg, FLOW2) and isinstance(search_alg._space, dict):\n                # remember const config\n                self._const = add_cost_to_space(self.space, {}, {})\n\n    def suggest(self, trial_id: str) -> Optional[Dict]:\n        """Use the suggest() of the underlying search algorithm."""\n        if isinstance(self._search_alg, FLOW2):\n            config = self._search_alg.suggest(trial_id)\n        else:\n            try:\n                config = self._search_alg.suggest(trial_id)\n                if isinstance(self._search_alg._space, dict):\n                    config.update(self._const)\n                else:\n                    # define by run\n                    config, self.space = unflatten_hierarchical(config, self._space)\n            except FloatingPointError:\n                logger.warning("The global search method raises FloatingPointError. " "Ignoring for this iteration.")\n                config = None\n        if config is not None:\n            self.running += 1\n        return config\n\n    def update_priority(self, eci: Optional[float] = 0):\n        # optimistic projection\n        self.priority = eci * self.speed - self.obj_best1\n\n    def update_eci(self, metric_target: float, max_speed: Optional[float] = np.inf):\n        # calculate eci: estimated cost for improvement over metric_target\n        best_obj = metric_target * self._metric_op\n        if not self.speed:\n            self.speed = max_speed\n        self.eci = max(self.cost_total - self.cost_best1, self.cost_best1 - self.cost_best2)\n        if self.obj_best1 > best_obj and self.speed > 0:\n            self.eci = max(self.eci, 2 * (self.obj_best1 - best_obj) / self.speed)\n\n    def _update_speed(self):\n        # calculate speed; use 0 for invalid speed temporarily\n        if self.obj_best2 > self.obj_best1:\n            # discount the speed if there are unfinished trials\n            self.speed = (\n                (self.obj_best2 - self.obj_best1) / self.running / (max(self.cost_total - self.cost_best2, self._eps))\n            )\n        else:\n            self.speed = 0\n\n    def on_trial_complete(self, trial_id: str, result: Optional[Dict] = None, error: bool = False):\n        """Update the statistics of the thread."""\n        if not self._search_alg:\n            return\n        if not hasattr(self._search_alg, "_ot_trials") or (not error and trial_id in self._search_alg._ot_trials):\n            # optuna doesn\'t handle error\n            if self._is_ls or not self._init_config:\n                try:\n                    self._search_alg.on_trial_complete(trial_id, result, error)\n                except RuntimeError as e:\n                    # rs is used in place of optuna sometimes\n                    if not str(e).endswith("has already finished and can not be updated."):\n                        raise e\n            else:\n                # init config is not proposed by self._search_alg\n                # under this thread\n                self._init_config = False\n        if result:\n            self.cost_last = result.get(self.cost_attr, 1)\n            self.cost_total += self.cost_last\n            if self._search_alg.metric in result and (getattr(self._search_alg, "lexico_objectives", None) is None):\n                # TODO: Improve this behavior. When lexico_objectives is provided to CFO,\n                # related variables are not callable.\n                obj = result[self._search_alg.metric] * self._metric_op\n                if obj < self.obj_best1 or self.best_result is None:\n                    self.cost_best2 = self.cost_best1\n                    self.cost_best1 = self.cost_total\n                    self.obj_best2 = obj if np.isinf(self.obj_best1) else self.obj_best1\n                    self.obj_best1 = obj\n                    self.cost_best = self.cost_last\n                    self.best_result = result\n            if getattr(self._search_alg, "lexico_objectives", None) is None:\n                # TODO: Improve this behavior. When lexico_objectives is provided to CFO,\n                # related variables are not callable.\n                self._update_speed()\n        self.running -= 1\n        assert self.running >= 0\n\n    def on_trial_result(self, trial_id: str, result: Dict):\n        # TODO update the statistics of the thread with partial result?\n        if not self._search_alg:\n            return\n        if not hasattr(self._search_alg, "_ot_trials") or (trial_id in self._search_alg._ot_trials):\n            try:\n                self._search_alg.on_trial_result(trial_id, result)\n            except RuntimeError as e:\n                # rs is used in place of optuna sometimes\n                if not str(e).endswith("has already finished and can not be updated."):\n                    raise e\n        new_cost = result.get(self.cost_attr, 1)\n        if self.cost_last < new_cost:\n            self.cost_last = new_cost\n            # self._update_speed()\n\n    @property\n    def converged(self) -> bool:\n        return self._search_alg.converged\n\n    @property\n    def resource(self) -> float:\n        return self._search_alg.resource\n\n    def reach(self, thread) -> bool:\n        """Whether the incumbent can reach the incumbent of thread."""\n        return self._search_alg.reach(thread._search_alg)\n\n    @property\n    def can_suggest(self) -> bool:\n        """Whether the thread can suggest new configs."""\n        return self._search_alg.can_suggest\n',
            'test/tune/test_search_thread.py': '"""Tests for SearchThread nested dictionary update fix."""\n\nimport pytest\n\nfrom flaml.tune.searcher.search_thread import _recursive_dict_update\n\n\ndef test_recursive_dict_update_simple():\n    """Test simple non-nested dictionary update."""\n    target = {"a": 1, "b": 2}\n    source = {"c": 3}\n    _recursive_dict_update(target, source)\n    assert target == {"a": 1, "b": 2, "c": 3}\n\n\ndef test_recursive_dict_update_override():\n    """Test that source values override target values for non-dict values."""\n    target = {"a": 1, "b": 2}\n    source = {"b": 3}\n    _recursive_dict_update(target, source)\n    assert target == {"a": 1, "b": 3}\n\n\ndef test_recursive_dict_update_nested():\n    """Test nested dictionary merge (the main use case for XGBoost params)."""\n    target = {\n        "num_boost_round": 10,\n        "params": {\n            "max_depth": 12,\n            "eta": 0.020168455186106736,\n            "min_child_weight": 1.4504723523894132,\n            "scale_pos_weight": 3.794258636185337,\n            "gamma": 0.4985070123025904,\n        },\n    }\n    source = {\n        "params": {\n            "verbosity": 3,\n            "booster": "gbtree",\n            "eval_metric": "auc",\n            "tree_method": "hist",\n            "objective": "binary:logistic",\n        }\n    }\n    _recursive_dict_update(target, source)\n\n    # Check that sampled params are preserved\n    assert target["params"]["max_depth"] == 12\n    assert target["params"]["eta"] == 0.020168455186106736\n    assert target["params"]["min_child_weight"] == 1.4504723523894132\n    assert target["params"]["scale_pos_weight"] == 3.794258636185337\n    assert target["params"]["gamma"] == 0.4985070123025904\n\n    # Check that const params are added\n    assert target["params"]["verbosity"] == 3\n    assert target["params"]["booster"] == "gbtree"\n    assert target["params"]["eval_metric"] == "auc"\n    assert target["params"]["tree_method"] == "hist"\n    assert target["params"]["objective"] == "binary:logistic"\n\n    # Check top-level param is preserved\n    assert target["num_boost_round"] == 10\n\n\ndef test_recursive_dict_update_deeply_nested():\n    """Test deeply nested dictionary merge."""\n    target = {"a": {"b": {"c": 1, "d": 2}}}\n    source = {"a": {"b": {"e": 3}}}\n    _recursive_dict_update(target, source)\n    assert target == {"a": {"b": {"c": 1, "d": 2, "e": 3}}}\n\n\ndef test_recursive_dict_update_mixed_types():\n    """Test that non-dict values in source replace dict values in target."""\n    target = {"a": {"b": 1}}\n    source = {"a": 2}\n    _recursive_dict_update(target, source)\n    assert target == {"a": 2}\n\n\ndef test_recursive_dict_update_empty_dicts():\n    """Test with empty dictionaries."""\n    target = {}\n    source = {"a": 1}\n    _recursive_dict_update(target, source)\n    assert target == {"a": 1}\n\n    target = {"a": 1}\n    source = {}\n    _recursive_dict_update(target, source)\n    assert target == {"a": 1}\n\n\ndef test_recursive_dict_update_none_values():\n    """Test that None values are properly handled."""\n    target = {"a": 1, "b": None}\n    source = {"b": 2, "c": None}\n    _recursive_dict_update(target, source)\n    assert target == {"a": 1, "b": 2, "c": None}\n',
        }
