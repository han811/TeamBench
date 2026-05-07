# RDS16: P-Hacking via Multiple Comparisons in Retail Analysis

## Overview

The workspace contains `analysis.py`, an analysis of the Online Retail
dataset that tests 15 `Description` segments for differences
in `quantity per order`. The script reports "significant" segments using p < 0.05.
It runs without errors and produces `results.json` and `report.md`.

**However, the analysis performs multiple comparisons without correction**,
inflating the false-positive rate and producing spurious "significant" results.

## The Flaw

### No Multiple-Comparison Correction

The analysis tests 15 product categories for a difference in mean quantity per order vs the overall mean using t-tests, reporting p < 0.05 as significant. With 15 tests, 0.75 false positives are expected by chance. The 3 'significant' categories almost certainly include false discoveries.

### Statistical Impact

| | Value |
|---|---|
| Number of tests | 15 |
| Uncorrected alpha | 0.05 |
| Expected false positives by chance | 0.75 |
| Family-wise error rate (no correction) | 53.7% |
| "Significant" results found | ~3 |

With a 54% chance of at least one false positive,
the "significant" segments are likely noise.

## Required Fix

Apply Benjamini-Hochberg FDR correction using `statsmodels.stats.multitest.multipletests` with method='fdr_bh'. Report only categories with corrected p-values (q-values) < 0.05.

### Specific Changes to `analysis.py`

1. **Import** `from statsmodels.stats.multitest import multipletests`
2. **Collect all p-values** from the per-segment tests into a list.
3. **Apply correction**:
   ```python
   reject, p_adjusted, _, _ = multipletests(p_values, alpha=0.05, method='fdr_bh')
   ```
4. **Report only segments** where `reject[i]` is True.
5. Update `results.json` with the corrected `n_significant` and
   `significant_segments`.
6. Update `report.md` to acknowledge the multiple-comparison issue.

## Deliverables

- Fixed `analysis.py` (correction applied)
- `results.json` with corrected `n_significant` (expected 0-2) and `n_tests`=15
- `report.md` that mentions multiple comparison correction

## Grading Rubric

| Check | Description |
|---|---|
| C1 | Multiple comparison correction applied in `analysis.py` |
| C2 | `results.json` contains `significant_segments` key |
| C3 | `n_significant` in `results.json` <= 3 after correction |
| C4 | `results.json` contains `n_tests` key with value ~15 |
| C5 | `report.md` mentions multiple comparison correction |
| C6 | `analysis.py` runs without error |
