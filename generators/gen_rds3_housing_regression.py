"""
Parameterized generator for RDS3: Ames Housing Regression (Open-Ended, Archetype 3).

Three seed variants with different research focuses:
  Seed 0 — "prediction":        Build best predictive model for SalePrice. Compare ≥2 model types.
  Seed 1 — "feature_importance": Which features most influence price? ≥2 importance methods.
  Seed 2 — "assumptions":       Is linear regression appropriate? Test normality, homoscedasticity,
                                  linearity. Propose corrections.

Each variant:
  - spec_md:        Full requirements with focus-specific criteria, 8 grading criteria.
  - brief_md:       Vague — "Analyze Ames Housing dataset for housing price insights".
  - workspace_files: data/ames_housing.csv (seed-varied feature subset), requirements.txt,
                     check_solution.py.

Rubric checks (8):
  C1  script_runs         — analysis script executes without error
  C2  output_contains     — EDA present (describe/hist/scatter/boxplot/distribution/summary/corr)
  C3  output_contains     — missing-value handling present
  C4  output_contains     — uncertainty metric reported (rmse/r2/ci/score/mse/mae)
  C5  output_contains     — focus-specific criteria (patterns differ per seed)
  C6  output_contains     — random seed set (random_state/seed/np.random.seed)
  C7  output_contains     — outlier handling documented
  C8  file_exists         — report.md present
"""
from __future__ import annotations

import textwrap

from generators.base import GeneratedTask
from generators.primitives import SeededRandom
from generators.real_data_base import OpenEndedGenerator

# ── Column catalogue ──────────────────────────────────────────────────────────

# Always-present core columns (anchor columns + target)
_CORE_COLUMNS = [
    "SalePrice", "GrLivArea", "OverallQual", "YearBuilt",
    "TotalBsmtSF", "GarageCars",
]

# Pool of additional columns to sample from (must exist in the synthetic CSV)
_EXTRA_POOL = [
    "LotArea", "OverallCond", "YearRemodAdd", "FullBath", "HalfBath",
    "BedroomAbvGr", "GarageArea", "Fireplaces", "TotRmsAbvGrd",
    "PoolArea", "MoSold", "YrSold", "MSSubClass", "LotFrontage",
    "TotalBsmtSF",  # already in core but harmless; select_columns deduplicates
    "HeatingQC", "KitchenQual", "ExterQual",
]

# Deduplicated, order-preserving
_EXTRA_POOL_UNIQUE = list(dict.fromkeys(c for c in _EXTRA_POOL if c not in _CORE_COLUMNS))

# ── Focus definitions ─────────────────────────────────────────────────────────

_FOCUSES = ["prediction", "feature_importance", "assumptions"]

_FOCUS_SPEC: dict[str, dict] = {
    "prediction": {
        "title": "Predictive Modeling for SalePrice",
        "goal": (
            "Build the best predictive model you can for `SalePrice`. "
            "Evaluate on a held-out test set."
        ),
        "requirements": textwrap.dedent("""\
            1. **EDA**: Examine distributions, correlations, and missing values.
            2. **Preprocessing**: Handle missing values; encode or drop categoricals as needed.
            3. **Modelling**: Train **at least two different model types** (e.g., linear regression,
               random forest, gradient boosting, ridge, lasso, …).
            4. **Evaluation**: Report RMSE and R² on a held-out 20 % test split (`random_state=42`).
            5. **Comparison**: State which model performs best and why.
            6. **Outliers**: Document any outlier removal or winsorisation steps in `report.md`.
            7. **Random seed**: Set `random_state=42` (or equivalent) for all stochastic steps.
            8. **Deliverables**: `analysis.py` (runnable script), `results.json` (RMSE and R² for
               each model), `report.md` (narrative discussion ≥ 200 words).
        """),
        "extra_criteria": [
            "rmse", "r2", "random_forest|gradient_boosting|GradientBoosting|RandomForest"
            "|ridge|lasso|LinearRegression|linear_regression",
        ],
        "c5_patterns": ["rmse", "r2"],
        "c5_description": "Results file contains RMSE and R² metrics",
        "c5_path": "results.json",
    },
    "feature_importance": {
        "title": "Feature Importance Analysis for SalePrice",
        "goal": (
            "Identify which features most influence `SalePrice` using at least two "
            "different importance methods."
        ),
        "requirements": textwrap.dedent("""\
            1. **EDA**: Examine distributions, correlations, and missing values.
            2. **Preprocessing**: Handle missing values; encode or drop categoricals as needed.
            3. **Importance methods**: Apply **at least two** methods, e.g.:
               - Pearson / Spearman correlation ranking
               - Random Forest feature importances
               - Permutation importance
               - SHAP values
               - Lasso / ElasticNet coefficients (standardised)
            4. **Multicollinearity**: Discuss any high correlations between top features
               (VIF or pairwise correlation matrix).
            5. **Outliers**: Document any outlier removal in `report.md`.
            6. **Random seed**: Set `random_state=42` (or equivalent) for all stochastic steps.
            7. **Deliverables**: `analysis.py` (runnable script), `results.json` (ranked feature
               list from at least one method), `report.md` (narrative ≥ 200 words discussing
               multicollinearity and top features).
        """),
        "c5_patterns": ["feature_importance|permutation|shap|correlation|importances"],
        "c5_description": "Analysis uses at least one quantitative importance method",
        "c5_path": "report.md",
    },
    "assumptions": {
        "title": "Linear Regression Assumption Testing for SalePrice",
        "goal": (
            "Assess whether linear regression is appropriate for `SalePrice` prediction "
            "by formally testing its core assumptions."
        ),
        "requirements": textwrap.dedent("""\
            1. **EDA**: Examine distributions, correlations, and missing values.
            2. **Preprocessing**: Handle missing values; encode or drop categoricals as needed.
            3. **Fit a baseline linear regression** (`random_state=42`) on the provided features.
            4. **Test assumptions**:
               - *Normality of residuals*: Shapiro-Wilk test or Q-Q plot.
               - *Homoscedasticity*: Breusch-Pagan test or residuals-vs-fitted plot.
               - *Linearity*: Partial regression plots or RESET test.
            5. **Propose corrections**: Based on findings, propose at least one remediation
               (e.g., log-transform target, Box-Cox, polynomial features, robust regression).
            6. **Outliers**: Document influential observations (Cook's distance or leverage)
               in `report.md`.
            7. **Random seed**: Set `random_state=42` for all stochastic steps.
            8. **Deliverables**: `analysis.py` (runnable script), `results.json` (p-values or
               test statistics for each assumption test), `report.md` (narrative ≥ 200 words
               discussing findings and corrections).
        """),
        "c5_patterns": ["shapiro|breusch|normality|homoscedasticity|qqplot|q-q|residual"],
        "c5_description": "Report documents at least one formal assumption test",
        "c5_path": "report.md",
    },
}


class Generator(OpenEndedGenerator):
    task_id = "RDS3_housing_regression"
    domain = "data_science"
    difficulty = "hard"
    languages = ["python"]

    dataset_name = "ames_housing"
    dataset_license = "CC0"
    dataset_source = "Kaggle/OpenML (synthetic placeholder)"

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        focus_name = _FOCUSES[seed % len(_FOCUSES)]
        focus = _FOCUS_SPEC[focus_name]

        # ── Feature selection ──────────────────────────────────────────────
        n_extra = rng.randint(8, 15)
        extra_cols = rng.sample(_EXTRA_POOL_UNIQUE, min(n_extra, len(_EXTRA_POOL_UNIQUE)))
        # Core columns first, then extras — deduplicated
        selected_cols = list(dict.fromkeys(_CORE_COLUMNS + extra_cols))

        # ── Load and slice dataset ─────────────────────────────────────────
        all_rows = self.load_dataset()
        subset_rows = self.select_columns(all_rows, selected_cols)
        dataset_csv = self.rows_to_csv(subset_rows, selected_cols)

        # ── Grading checks ─────────────────────────────────────────────────
        eda_patterns = [
            "describe|hist|scatter|boxplot|distribution|summary|corr|head|info|value_counts"
        ]
        missing_patterns = [
            "fillna|impute|dropna|missing|isnull|isna|SimpleImputer|KNNImputer"
        ]
        uncertainty_patterns = [
            "rmse|r2|r2_score|mean_squared_error|mean_absolute_error|score|mse|mae"
        ]
        seed_patterns = [
            "random_state|np.random.seed|random.seed|torch.manual_seed|set_seed"
        ]
        outlier_patterns = [
            "outlier|extreme|influential|leverage|clip|winsoriz|cook|zscore|z-score|IQR|iqr"
        ]

        checks = [
            {
                "id": "C1",
                "description": "analysis.py runs without error",
                "type": "script_runs",
                "path": "analysis.py",
                "timeout": 120,
            },
            {
                "id": "C2",
                "description": "EDA present in analysis.py (describe/hist/scatter/corr/etc.)",
                "type": "output_contains",
                "path": "analysis.py",
                "patterns": eda_patterns,
            },
            {
                "id": "C3",
                "description": "Missing-value handling present in analysis.py",
                "type": "output_contains",
                "path": "analysis.py",
                "patterns": missing_patterns,
            },
            {
                "id": "C4",
                "description": "Uncertainty metric reported in results.json or report.md",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib, re
                    ws = pathlib.Path(workspace_dir)
                    text = ""
                    for fname in ("results.json", "report.md"):
                        p = ws / fname
                        if p.exists():
                            text += p.read_text(encoding="utf-8", errors="ignore")
                    patterns = {uncertainty_patterns}
                    passed = bool(re.search("|".join(patterns), text, re.IGNORECASE))
                    detail = "uncertainty metric found" if passed else "no uncertainty metric found in results.json or report.md"
                """).format(uncertainty_patterns=repr(
                    ["rmse", "r2", "r2_score", "mean_squared_error",
                     "mean_absolute_error", "score", "mse", "mae"]
                )),
            },
            {
                "id": "C5",
                "description": focus["c5_description"],
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib, re
                    ws = pathlib.Path(workspace_dir)
                    text = ""
                    for fname in ("analysis.py", "results.json", "report.md"):
                        p = ws / fname
                        if p.exists():
                            text += p.read_text(encoding="utf-8", errors="ignore")
                    patterns = {c5_patterns}
                    passed = bool(re.search("|".join(patterns), text, re.IGNORECASE))
                    detail = "focus criteria found" if passed else "focus-specific criteria not found in analysis.py / results.json / report.md"
                """).format(c5_patterns=repr(focus["c5_patterns"])),
            },
            {
                "id": "C6",
                "description": "Random seed set in analysis.py",
                "type": "output_contains",
                "path": "analysis.py",
                "patterns": seed_patterns,
            },
            {
                "id": "C7",
                "description": "Outlier handling documented in report.md",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib, re
                    ws = pathlib.Path(workspace_dir)
                    p = ws / "report.md"
                    text = p.read_text(encoding="utf-8", errors="ignore") if p.exists() else ""
                    patterns = {outlier_patterns}
                    passed = bool(re.search("|".join(patterns), text, re.IGNORECASE))
                    detail = "outlier documentation found" if passed else "no outlier documentation in report.md"
                """).format(outlier_patterns=repr(
                    ["outlier", "extreme", "influential", "leverage",
                     "clip", "winsoriz", "cook", "zscore", "z-score", "IQR", "iqr"]
                )),
            },
            {
                "id": "C8",
                "description": "report.md exists",
                "type": "file_exists",
                "path": "report.md",
            },
        ]

        check_solution_py = self.make_check_solution(checks)
        requirements_txt = self.make_requirements_txt([
            "pandas>=1.5",
            "numpy>=1.23",
            "scipy>=1.9",
            "scikit-learn>=1.1",
            "matplotlib>=3.5",
            "statsmodels>=0.13",
        ])

        workspace_files = {
            "data/ames_housing.csv": dataset_csv,
            "check_solution.py": check_solution_py,
            "requirements.txt": requirements_txt,
        }

        spec_md = self._build_spec(focus_name, focus, selected_cols)
        brief_md = self._build_brief()

        expected = {
            "focus": focus_name,
            "selected_columns": selected_cols,
            "n_rows": len(subset_rows),
            "core_columns": _CORE_COLUMNS,
            "extra_columns": extra_cols,
        }

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )

    # ── Document builders ──────────────────────────────────────────────────────

    def _build_spec(
        self,
        focus_name: str,
        focus: dict,
        selected_cols: list[str],
    ) -> str:
        cols_str = ", ".join(f"`{c}`" for c in selected_cols)
        return textwrap.dedent(f"""\
            # RDS3: Ames Housing Regression — {focus["title"]}

            ## Dataset
            **File**: `data/ames_housing.csv`
            **Source**: Ames Housing dataset (Kaggle/OpenML, CC0)
            **Rows**: ~2,930 residential property sales in Ames, Iowa
            **Target variable**: `SalePrice` (continuous, USD)

            **Available columns** ({len(selected_cols)} total):
            {cols_str}

            ## Goal
            {focus["goal"]}

            ## Requirements
            {focus["requirements"]}

            ## Grading Rubric (8 criteria)

            | ID | Criterion | How to satisfy |
            |----|-----------|----------------|
            | C1 | Script runs | `analysis.py` executes end-to-end without uncaught exceptions |
            | C2 | EDA present | `analysis.py` contains at least one EDA operation (describe, histogram, scatter, correlation, etc.) |
            | C3 | Missing values handled | `analysis.py` explicitly addresses missing/null values (fillna, dropna, imputer, etc.) |
            | C4 | Uncertainty reported | `results.json` or `report.md` includes a numeric metric (RMSE, R², MAE, MSE, CI, etc.) |
            | C5 | Focus criteria met | See focus-specific requirement above |
            | C6 | Random seed set | `analysis.py` sets `random_state=42` or equivalent |
            | C7 | Outlier handling documented | `report.md` mentions outlier/leverage/influential observation strategy |
            | C8 | Report exists | `report.md` file is present |

            ## Deliverables
            - `analysis.py` — single runnable Python script
            - `results.json` — machine-readable metrics/findings
            - `report.md` — narrative write-up (≥ 200 words)

            ## Notes
            - The grading script is `check_solution.py`; run it to self-assess.
            - Do **not** modify `data/ames_housing.csv` or `check_solution.py`.
            - All stochastic operations must use `random_state=42`.
        """)

    def _build_brief(self) -> str:
        return textwrap.dedent("""\
            # RDS3: Ames Housing Regression

            Analyze the Ames Housing dataset for housing price insights.

            The dataset is in `data/ames_housing.csv`. The target variable is `SalePrice`.

            Produce:
            - `analysis.py` — a runnable Python analysis script
            - `results.json` — key numerical findings
            - `report.md` — a narrative summary of your findings

            Run `check_solution.py` to evaluate your solution.
        """)
