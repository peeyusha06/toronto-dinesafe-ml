# Notebook Guide

One sentence per notebook, in the order the research was actually done.

- **01_prediction_events** — builds the first version of the prediction-event dataset (features from history before a target inspection, target = that inspection's outcome), using the full 2001-2026 pooled data.
- **02_temporal_distribution_check** — finds that historical and current periods have very different Non-Pass rates, motivating restricting prediction targets to the current period.
- **03_modern_target_dataset** — rebuilds the prediction-event dataset with targets restricted to the current period (2023-11-10 onward), history still drawn from the full longitudinal record.
- **04_baseline_logistic_regression** — first model: Logistic Regression using only the immediately previous inspection's features.
- **05_logistic_with_365d_history** — adds 365-day rolling history features; corrects the train/validation/test split to be strictly date-based; shows a real improvement over the previous-inspection-only baseline.
- **06_logistic_with_730d_history** — adds 730-day rolling history features on top of 365-day; shows a further, smaller improvement.
- **07_random_forest_730d_history** — same 15 features, untuned Random Forest; performs clearly worse than Logistic Regression.
- **08_catboost_730d_history** — same 15 features, untuned CatBoost; competitive with but does not beat Logistic Regression.
- **09_catboost_shap_interpretation** — SHAP analysis of the untuned CatBoost model; finds accumulated infractions and inspection timing dominate.
- **10_logistic_engineered_features** — tests seven engineered recency/rate/trend features; finds no meaningful improvement over the 15-feature representation.
- **11_model_tuning** — controlled hyperparameter search for Logistic Regression (C) and CatBoost (depth/iterations/learning rate); selects a shallower CatBoost configuration as the final tuned model.
- **12_history_depth_analysis** — stratifies test performance by how much pre-2023 history each establishment had; finds a non-monotonic pattern, not "more history = better."
- **13_catboost_infraction_categories** — first attempt at adding infraction-type history features (7 categories); finds no meaningful improvement.
- **14_catboost_infraction_categories_corrected** — corrected rerun using the full 15-category allowance (93% coverage instead of 76%); confirms the same essentially-flat result.
- **15_top_k_evaluation** — evaluates the final model as a capacity-constrained ranking tool; finds meaningful concentration of Non-Pass cases in the highest-risk-ranked inspections.
- **16_calibration_analysis** — checks whether the final model's predicted probabilities are trustworthy as probabilities; finds systematic overprediction, concluding the model is a ranking tool rather than a calibrated probability model.
