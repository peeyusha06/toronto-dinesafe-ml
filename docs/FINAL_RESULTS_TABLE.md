# Final Results Table

All rows use the same strict temporal split (train 45,334 / validation 11,740 / test 12,692; test period 2026-04-10 to 2026-09-08) unless noted. Source CSVs are in `outputs/`.

## Main experiment progression

| Experiment | Model | Features | Test PR-AUC | Test ROC-AUC | Test F1 | Source file |
|---|---|---|---:|---:|---:|---|
| Previous inspection only | Logistic Regression | 7 | 0.1274 | 0.6440 | 0.1815 | `baseline_logistic_strict_temporal_results.csv` |
| +365-day history | Logistic Regression | 11 | 0.1624 | 0.7041 | 0.2439 | `logistic_365d_history_results.csv` |
| +730-day history | Logistic Regression | 15 | 0.1732 | 0.7202 | 0.2468 | `logistic_730d_history_results.csv` |
| Model comparison | Random Forest | 15 | 0.1154 | 0.6523 | 0.1695 | `random_forest_730d_results.csv` |
| Model comparison | CatBoost (default depth/iterations) | 15 | 0.1590 | 0.7169 | 0.2476 | `catboost_730d_results.csv` |
| 22-feature engineered | Logistic Regression | 22 | 0.1726 | 0.7170 | 0.2402 | `logistic_engineered_results.csv` |
| Tuned final model | CatBoost (iterations=300, depth=4, lr=0.05) | 15 | 0.1742 | 0.7337 | 0.2475 | `tuned_model_results.csv` |
| Corrected category-augmented model | CatBoost (same tuned config) | 45 (15 + 30 category) | 0.1756 | 0.7325 | 0.2382 | `catboost_category_corrected_results.csv` |

## History-depth subgroup (test set, tuned final model)

| Group | Test rows | Non-Pass prevalence | Test PR-AUC | Test ROC-AUC | Source file |
|---|---:|---:|---:|---:|---|
| No pre-cutoff history | 4,532 | 8.58% | 0.1751 | 0.7208 | `history_depth_test_results.csv` |
| 1-4 pre-cutoff inspections | 2,191 | 7.53% | 0.2044 | 0.7569 | `history_depth_test_results.csv` |
| 5+ pre-cutoff inspections | 5,969 | 6.70% | 0.1663 | 0.7329 | `history_depth_test_results.csv` |

Non-monotonic: performance does not simply increase with history depth. Prevalence differs across groups, so these PR-AUC values are descriptive, not causally attributable to history depth alone.

## Top-K ranking (tuned final model, test set)

12,692 test inspections, 954 actual Non-Pass, overall prevalence ≈7.52%. Source: `top_k_results.csv`.

| Capacity | Inspections selected | Actual Non-Pass selected | Precision@K | Recall@K | Lift@K |
|---|---:|---:|---:|---:|---:|
| Top 1% | 127 | 32 | 25.2% | 3.4% | 3.35× |
| Top 5% | 635 | 156 | 24.6% | 16.4% | 3.27× |
| Top 10% | 1,269 | 267 | 21.0% | 28.0% | 2.80× |
| Top 20% | 2,538 | 444 | 17.5% | 46.5% | 2.33× |
| Top 25% | 3,173 | 520 | 16.4% | 54.5% | 2.18× |
| Top 100% | 12,692 | 954 | 7.5% | 100% | 1.00× |

## Calibration (tuned final model, test set)

Source: `calibration_results.csv`, `calibration_bins.csv`.

| Metric | Value |
|---|---|
| Brier score | 0.2052 |
| Log loss | 0.5982 |

Reliability curve is consistently below the perfect-calibration diagonal (systematic overprediction), widening at higher predicted probabilities — e.g. highest decile: mean predicted probability 0.776 vs. observed rate 0.210.
