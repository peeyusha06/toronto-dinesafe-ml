# DineSafe Longitudinal Inspection Prediction

## Research question

How much does longitudinal inspection history improve prediction of an establishment's next DineSafe inspection outcome, and how does the amount and recency of available history affect predictive performance?

This is not framed as "can machine learning predict restaurant safety" or as an attempt to build a highly accurate food-safety classifier. It is a disciplined empirical study of longitudinal inspection history as a predictor of the next *observed* DineSafe outcome, under a strict future-oriented evaluation.

## Data and prediction target

The current DineSafe export (`Dinesafe.csv`) is infraction-row level, not inspection level. It was audited and reconstructed to an inspection-level table: 77,475 current inspections across 18,898 establishments (`docs/DATA_AUDIT.md`, `docs/DATA_RECONSTRUCTION.md`). A historical archive (2001-2023) was linked in via legacy `oldEstId` matching to extend each establishment's longitudinal record where that linkage is available (`docs/LONGITUDINAL_DATASET.md`).

An early temporal check (`docs/TEMPORAL_DISTRIBUTION_CHECK.md`) found a large outcome-regime difference between the historical archive and the modern export: Non-Pass rates were far lower and structurally different (no "Closed" status at all) before the current export period. Because of this, prediction *targets* are restricted to the modern/current period; historical inspections are used only to build longitudinal history features, never as targets.

Target definition:

- 0 = Pass
- 1 = Non-Pass (Conditional Pass + Closed)
- Temporarily Not Operating is excluded from the target entirely (only one such inspection exists in the data)

The model predicts the observed DineSafe inspection outcome as recorded by the inspection process. It does not predict an establishment's true underlying food safety, which is not observed.

## Temporal methodology

Prediction events are evaluated with a strict, date-ordered split, not a random train/test split:

| Split | Rows | Date range |
|---|---|---|
| Train | 45,334 | 2023-11-10 to 2025-11-05 |
| Validation | 11,740 | 2025-11-06 to 2026-04-09 |
| Test | 12,692 | 2026-04-10 to 2026-09-08 |

Train contains the earliest target inspections, validation contains later inspections used for model and threshold decisions, and test contains the latest inspections, used once for final evaluation. The same establishment can legitimately appear in more than one split, since the task is forecasting a *later* inspection for an *existing* establishment using only information available before it, not classifying disjoint establishments.

The test set is not an independent sample from an identical distribution: Non-Pass prevalence drifts across the splits (roughly 5.5% in train, 6.4% in validation, 7.5% in test), a genuine feature of this forecasting setup, not an artifact.

## Feature representation

The stable, final feature representation used across the model comparison is 15 longitudinal features, built only from an establishment's own inspection history strictly before the target date:

```
days_since_previous_inspection, prev_non_pass, prev_total_infractions, prev_minor,
prev_significant, prev_crucial, n_inspections_seen_so_far,
prior_365d_n_inspections, prior_365d_n_non_pass, prior_365d_total_infractions, prior_365d_crucial_infractions,
prior_730d_n_inspections, prior_730d_n_non_pass, prior_730d_total_infractions, prior_730d_crucial_infractions
```

This representation was arrived at incrementally, not designed upfront:

- Previous-inspection-only features: test PR-AUC ≈ 0.127
- Adding 365-day history: test PR-AUC ≈ 0.162
- Adding 730-day history: test PR-AUC ≈ 0.173

The largest single gain came from adding one year of recent history. A second year of history added only a small further improvement. This is one of the strongest findings of the project: recency matters much more than sheer accumulation of history.

## Experiments

The work proceeded in this order, each step building on and testing the previous one:

1. Data audit and inspection-level reconstruction
2. Longitudinal dataset (historical + current linkage)
3. Modern-target prediction-event dataset
4. Temporal distribution check (motivated restricting targets to the modern period)
5. Previous-inspection-only Logistic Regression baseline
6. +365-day history
7. +730-day history
8. Model comparison: Logistic Regression, Random Forest, CatBoost (same 15 features, same split)
9. SHAP interpretation of the fixed CatBoost model
10. Seven engineered recency/rate/trend features (controlled negative result)
11. Controlled hyperparameter tuning (Logistic Regression and CatBoost only)
12. History-depth subgroup analysis
13. Infraction-category history features (later corrected to use 15 categories instead of 7)
14. Top-K capacity-constrained evaluation
15. Calibration analysis

## Model comparison

Using the identical 15-feature representation and identical strict split, before any tuning:

| Model | Test PR-AUC | Test ROC-AUC |
|---|---|---|
| Logistic Regression | 0.173 | 0.720 |
| Random Forest | 0.115 | 0.652 |
| CatBoost (default depth/iterations) | 0.159 | 0.717 |

Logistic Regression had the best PR-AUC of the three before any tuning. CatBoost was not the best model at this stage — it only became competitive, and then only marginally ahead, after its own hyperparameter search found that the original configuration (depth=6, 500 iterations) was overfitting relative to a shallower one.

Controlled tuning results:

- Logistic Regression: varying `C` over [0.01, 0.1, 1.0, 10.0, 100.0] had almost no effect on validation PR-AUC (0.1625 to 0.1632).
- CatBoost: shallower, shorter configurations consistently outperformed deeper, longer ones on validation. The best configuration found was `iterations=300, depth=4, learning_rate=0.05`.

The seven engineered recency/rate/trend features (`days_since_previous_non_pass`, `consecutive_passes`, `prior_365d_non_pass_rate`, `prior_730d_non_pass_rate`, `prior_365d_infractions_per_inspection`, `prior_730d_infractions_per_inspection`, `infraction_change_365_vs_730`) produced essentially no improvement over the 15-feature Logistic Regression (test PR-AUC 0.1732 with 15 features vs. 0.1726 with all 22). This is reported as a controlled negative result, not a failed implementation — the features were built and validated correctly; they simply did not add incremental signal.

## Final model

The final selected model is the tuned CatBoost configuration:

```python
CatBoostClassifier(
    iterations=300, depth=4, learning_rate=0.05,
    loss_function="Logloss", auto_class_weights="Balanced",
    random_seed=42, verbose=False
)
```

Final test results (threshold locked at 0.70, chosen on validation before touching test):

| Metric | Value |
|---|---|
| PR-AUC | 0.1742 |
| ROC-AUC | 0.7337 |
| Precision | 0.2098 |
| Recall | 0.3019 |
| F1 | 0.2475 |
| Accuracy | 0.8620 |

Confusion matrix: `[[10653, 1085], [666, 288]]`.

This is a small improvement over the untuned Logistic Regression's 0.173 PR-AUC, not a dramatic one. SHAP interpretation of this model (fixed 2,000-row test sample) found the largest contributors, by mean absolute SHAP value, to be `prior_730d_total_infractions`, `days_since_previous_inspection`, `prior_365d_total_infractions`, `n_inspections_seen_so_far`, and `prev_non_pass` — the model relies heavily on accumulated historical infractions, timing since the last inspection, and how much inspection history exists. Several of these features overlap conceptually (different windows over similar counts), which makes individual attribution difficult to interpret independently; no causal claim is made about any of them.

A subgroup analysis by pre-cutoff (pre-2023-11-10) history depth found a non-monotonic pattern: the "1 to 4 history" group scored the highest test PR-AUC (≈0.204), followed by "no history" (≈0.175), with the "5+ history" group scoring lowest (≈0.166). More history did not monotonically improve performance. Non-Pass prevalence also differed across these groups, so the PR-AUC differences are reported descriptively rather than attributed to a single cause.

A corrected infraction-category experiment (15 `deficiencyDesc` categories, 30 new history features, 92.9% coverage of pre-test infraction rows, validated with 0 mismatches on a 300-row brute-force check) found essentially flat results relative to the 15-feature baseline: test PR-AUC 0.1756 vs. 0.1742, test ROC-AUC 0.7325 vs. 0.7337. Knowing the *type* of prior infraction did not materially improve prediction beyond knowing counts and severity.

## Top-K ranking results

Using the final model's predicted probabilities to rank the 12,692 test inspections (954 actual Non-Pass, prevalence ≈7.52%):

| Capacity | Precision@K | Recall@K | Lift@K |
|---|---|---|---|
| Top 1% | 25.2% | 3.4% | 3.35× |
| Top 5% | 24.6% | 16.4% | 3.27× |
| Top 10% | 21.0% | 28.0% | 2.80× |
| Top 20% | 17.5% | 46.5% | 2.33× |
| Top 25% | 16.4% | 54.5% | 2.18× |

The top 10% of model-ranked inspections contains 28% of all observed Non-Pass inspections in the test set, about 2.8 times the density that random prioritization would achieve. This is a genuine, consistent concentration effect across every capacity level checked, and it is one of the more practically interpretable results in the project: a modest overall PR-AUC still corresponds to real, usable ranking value at the top of the distribution.

This is retrospective ranking evidence on already-observed outcomes. It does not show that using this ranking to prioritize inspections would prevent future problems or improve real-world food safety.

## Calibration

The final model's raw predicted probabilities are poorly calibrated. Test Brier score ≈0.205, log loss ≈0.598. The reliability curve sits well below the perfect-calibration diagonal at every probability level, and the gap widens at higher predicted probabilities (e.g., the highest decile has a mean predicted probability of 0.776 but an observed Non-Pass rate of only 21.0%). A plausible, but not independently tested, explanation is that `auto_class_weights="Balanced"` shifts predicted probabilities away from the true ~7.5% base rate.

The model is better understood as a ranking/risk-score model than as a calibrated probability model. A predicted value of "0.70" should not be read as "a 70% chance of Non-Pass."

## Main findings

1. Longitudinal inspection history contains genuine predictive signal beyond the immediately previous inspection.
2. Recent history is far more valuable than simply accumulating more history — most of the gain came from the first year.
3. Going from one year to two years of history produces diminishing, modest returns.
4. Simple engineered rate/recency/trend transformations of the same information did not materially improve the representation.
5. More complex tree models (Random Forest, default-configuration CatBoost) did not clearly outperform the simple linear model on the same features.
6. Controlled hyperparameter tuning produced only a small final gain, and mainly by correcting an overfit CatBoost configuration rather than discovering new signal.
7. A more complete infraction-category representation (15 categories, 93% coverage) also added little incremental signal beyond counts and severity.
8. The final model has real, usable ranking concentration at the top of the risk ranking (Top-K results), even though its overall PR-AUC is modest.
9. The model's raw predicted probabilities are not well calibrated and should not be read as literal probabilities.
10. Taken together, this evidence suggests the current structured DineSafe inspection information is approaching a predictive ceiling for this specific next-inspection prediction task under this feature representation — not that the dataset is useless, but that it contains useful, bounded predictive information for this task.

## Limitations

- The target reflects the observed, recorded DineSafe inspection outcome, not an unobserved "true" food-safety state.
- Non-Pass is a strongly imbalanced minority class (≈6-8% depending on the period), which constrains what any classification metric can show and motivated using PR-AUC as the primary metric.
- Non-Pass prevalence drifts across the train/validation/test periods; the test set is not drawn from an identical distribution to training.
- Establishment identity linkage between the historical archive and the current export relies on a legacy `oldEstId` field with documented ambiguity (some legacy IDs map to more than one current `estId`); this linkage was resolved conservatively, not perfectly.
- Historical and current data are not perfectly interchangeable: the historical files lack a "Closed" status entirely, and outcome rates differ structurally between the two periods, which is exactly why targets were restricted to the current period.
- The current feature representation is built almost entirely from structured inspection-history counts and severities; no unstructured infraction-category modeling beyond compact count features, and no external context, was used.
- Raw predicted probabilities from the final model are poorly calibrated.
- The Top-K ranking result is retrospective evidence about historical concentration, not proof of operational benefit if used to prioritize real inspections.
- All final results come from one fixed future test period (2026-04-10 to 2026-09-08); performance in a different future period was not evaluated.
- The same establishment can legitimately appear across train, validation, and test, since the task is forecasting a future inspection for an existing establishment, not classifying disjoint establishments — this is by design, not leakage, but it does mean the splits are not establishment-independent.
- The history-depth subgroup analysis is descriptive; subgroup prevalence differed, so PR-AUC differences between groups should not be read as a clean causal comparison.
- No external context (e.g., neighborhood socioeconomic variables, business type, or other data outside DineSafe) was used in any experiment.

## Relation to prior work

The literature review (`DineSafe_Literature_Review_IEEE.docx`) already establishes that "can machine learning predict food-inspection outcomes" is not a novel question — this has been demonstrated in Chicago, in England and Wales, and in more recent restaurant/food-inspection ML work, including recent explainable transformer and Bayesian approaches. Toronto-specific DineSafe scholarship exists but is descriptive/statistical, not a predictive next-inspection model.

This project does not claim algorithmic novelty or a first-ever restaurant-inspection prediction system. The defensible contribution is Toronto-specific empirical evidence under a leakage-safe, strictly future-oriented temporal evaluation, together with a controlled set of ablations that show specifically where additional information helps (recent history, especially the first year) and where it does not (a second year of history, engineered rate features, a fuller infraction-category representation, and switching to more complex model families).

## Final conclusion

Under this feature representation, this temporal evaluation, and the present analysis, longitudinal DineSafe inspection history contains real but bounded predictive value for an establishment's next inspection outcome. The value is concentrated in recent history rather than in accumulating a long record, is not meaningfully increased by simple feature engineering, more complex models, tuning, or a fuller infraction-category representation, and translates into a model that is genuinely useful for risk-ranking (Top-K) but not for producing calibrated probabilities. This is a complete, defensible empirical answer to the research question as posed — it is not a claim that DineSafe data cannot support prediction at all, only that this project has mapped where the readily available predictive signal in the current structured data lies, and where it appears to run out.
