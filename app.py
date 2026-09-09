"""
Dashboard for the Toronto DineSafe longitudinal inspection prediction project.

This only reads and displays the saved research outputs in outputs/.
It does not train anything, does not run any feature engineering, and does
not recompute any result.
"""

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="DineSafe Inspection Prediction", layout="centered")

OUT = "outputs"


def load_csv(name):
    return pd.read_csv(f"{OUT}/{name}")


st.title("Toronto DineSafe Longitudinal Inspection Prediction")
st.write("Predicting the next observed DineSafe inspection outcome from prior inspection history.")

st.header("Project")
st.write(
    "Research question: how much does longitudinal inspection history improve prediction of "
    "an establishment's next DineSafe inspection outcome, and how does the amount and recency "
    "of available history affect predictive performance?"
)
col1, col2 = st.columns(2)
with col1:
    st.metric("Current inspections", "77,475")
    st.metric("Establishments", "18,898")
with col2:
    st.metric("Target", "Pass vs Non-Pass")
    st.metric("Prediction period", "current period only")
st.write(
    "Data: the current DineSafe export plus a 2001-2023 historical archive, used only to build "
    "history features. Non-Pass = Conditional Pass or Closed. Targets are restricted to the "
    "current period because historical and current Non-Pass rates differ structurally."
)

st.header("Data and prediction setup")
split_table = pd.DataFrame([
    {"Split": "Train", "Date range": "2023-11-10 to 2025-11-05", "Rows": 45334},
    {"Split": "Validation", "Date range": "2025-11-06 to 2026-04-09", "Rows": 11740},
    {"Split": "Test", "Date range": "2026-04-10 to 2026-09-08", "Rows": 12692},
])
st.table(split_table.set_index("Split"))
st.write(
    "Inspections are ordered by date so the model is trained on earlier observations and "
    "evaluated on later ones. This is not a random split, and Non-Pass prevalence changes "
    "over time (about 5.5% in train, 6.4% in validation, 7.5% in test)."
)

st.header("Model experiments")
st.write("Test-set results for every model/feature combination tried, using the same strict temporal split.")

baseline = load_csv("baseline_logistic_strict_temporal_results.csv").iloc[0]
h365 = load_csv("logistic_365d_history_results.csv").iloc[0]
h730 = load_csv("logistic_730d_history_results.csv").iloc[0]
rf = load_csv("random_forest_730d_results.csv").iloc[0]
cb = load_csv("catboost_730d_results.csv").iloc[0]
eng = load_csv("logistic_engineered_results.csv").iloc[0]
tuned = load_csv("tuned_model_results.csv").iloc[0]
cat_corrected = load_csv("catboost_category_corrected_results.csv").iloc[1]

progression = pd.DataFrame([
    {"Feature set / model": "Previous inspection only (Logistic Regression)", "Test PR-AUC": baseline["test_pr_auc"], "Test ROC-AUC": baseline["test_roc_auc"], "Test F1": baseline["test_f1"]},
    {"Feature set / model": "+365-day history (Logistic Regression)", "Test PR-AUC": h365["test_pr_auc"], "Test ROC-AUC": h365["test_roc_auc"], "Test F1": h365["test_f1"]},
    {"Feature set / model": "+730-day history (Logistic Regression)", "Test PR-AUC": h730["test_pr_auc"], "Test ROC-AUC": h730["test_roc_auc"], "Test F1": h730["test_f1"]},
    {"Feature set / model": "Random Forest (15 features)", "Test PR-AUC": rf["test_pr_auc"], "Test ROC-AUC": rf["test_roc_auc"], "Test F1": rf["test_f1"]},
    {"Feature set / model": "CatBoost, default config (15 features)", "Test PR-AUC": cb["test_pr_auc"], "Test ROC-AUC": cb["test_roc_auc"], "Test F1": cb["test_f1"]},
    {"Feature set / model": "22-feature engineered (Logistic Regression)", "Test PR-AUC": eng["test_pr_auc"], "Test ROC-AUC": eng["test_roc_auc"], "Test F1": eng["test_f1"]},
    {"Feature set / model": "Tuned CatBoost (final model)", "Test PR-AUC": tuned["test_pr_auc"], "Test ROC-AUC": tuned["test_roc_auc"], "Test F1": tuned["test_f1"]},
    {"Feature set / model": "Corrected category model (45 features)", "Test PR-AUC": cat_corrected["test_pr_auc"], "Test ROC-AUC": cat_corrected["test_roc_auc"], "Test F1": cat_corrected["test_f1"]},
])
st.dataframe(progression.set_index("Feature set / model").round(4), use_container_width=True)

st.subheader("History depth: the central finding")
fig, ax = plt.subplots(figsize=(5, 3.5))
labels = ["Previous\ninspection only", "+365-day\nhistory", "+730-day\nhistory"]
values = [baseline["test_pr_auc"], h365["test_pr_auc"], h730["test_pr_auc"]]
ax.bar(labels, values, color="#4a6f8a")
ax.set_ylabel("Test PR-AUC")
st.pyplot(fig)
st.write("Most of the gain came from adding recent history; extending from one year to two years produced a smaller improvement.")

st.header("Final model")
st.write("CatBoost, tuned on validation only:")
st.code("iterations=300, depth=4, learning_rate=0.05, auto_class_weights='Balanced'", language="text")
st.write("Features: 15 longitudinal features (previous inspection + 365-day and 730-day rolling history). Threshold: 0.70.")
final_table = pd.DataFrame([
    {"Metric": "PR-AUC", "Value": round(tuned["test_pr_auc"], 4)},
    {"Metric": "ROC-AUC", "Value": round(tuned["test_roc_auc"], 4)},
    {"Metric": "Precision", "Value": round(tuned["test_precision"], 4)},
    {"Metric": "Recall", "Value": round(tuned["test_recall"], 4)},
    {"Metric": "F1", "Value": round(tuned["test_f1"], 4)},
    {"Metric": "Accuracy", "Value": round(tuned["test_accuracy"], 4)},
])
st.table(final_table.set_index("Metric"))

st.header("Risk ranking (Top-K)")
st.write(
    "PR-AUC and F1 describe overall performance at one threshold. Top-K asks a more practical "
    "question: if only a limited fraction of inspections could be prioritized, how many actual "
    "Non-Pass inspections would fall inside that fraction?"
)
topk = load_csv("top_k_results.csv")
topk_display = topk[topk["k_percent"] != 100].copy()
topk_display["k_percent"] = topk_display["k_percent"].astype(str) + "%"
topk_display = topk_display.rename(columns={
    "k_percent": "Top K", "precision_at_k": "Precision@K", "recall_at_k": "Recall@K", "lift_at_k": "Lift@K",
})[["Top K", "Precision@K", "Recall@K", "Lift@K"]]
st.dataframe(topk_display.round(3).set_index("Top K"), use_container_width=True)

top10 = topk[topk["k_percent"] == 10].iloc[0]
st.write(f"**Top 10% of ranked inspections contains {top10['recall_at_k']*100:.0f}% of observed Non-Pass inspections.**")
st.write(f"Lift = {top10['lift_at_k']:.2f}x compared with random prioritization.")
st.image(f"{OUT}/figures/top_k_recall_curve.png")
st.write("The model is more useful as a ranking tool than as a literal probability model.")

st.header("Calibration")
st.write("Are the predicted probabilities themselves trustworthy, or just the ranking?")
calib = load_csv("calibration_results.csv").iloc[0]
st.image(f"{OUT}/figures/catboost_calibration_curve.png")
col3, col4 = st.columns(2)
with col3:
    st.metric("Brier score", round(calib["test_brier_score"], 4))
with col4:
    st.metric("Log loss", round(calib["test_log_loss"], 4))
st.warning("The raw model probabilities are substantially overconfident.")
bins = load_csv("calibration_bins.csv")
highest_bin = bins.iloc[-1]
st.write(
    f"Highest probability decile: mean predicted probability {highest_bin['mean_predicted_probability']:.3f} "
    f"vs observed Non-Pass rate {highest_bin['observed_non_pass_rate']:.3f}."
)

st.header("What the model relies on")
shap_imp = load_csv("catboost_shap_importance.csv").head(5)
fig2, ax2 = plt.subplots(figsize=(5, 3))
ax2.barh(shap_imp["feature"][::-1], shap_imp["mean_abs_shap"][::-1], color="#4a6f8a")
ax2.set_xlabel("mean |SHAP value|")
st.pyplot(fig2)
st.write("These values describe what the model uses; they are not causal effects.")

st.header("What did not improve the model?")
negative_results = pd.DataFrame([
    {"Attempt": "7 engineered rate/recency/trend features", "Result": "essentially no change (PR-AUC 0.1732 to 0.1726)"},
    {"Attempt": "Random Forest (same 15 features)", "Result": "clearly worse (PR-AUC 0.115 vs 0.173)"},
    {"Attempt": "Infraction-category history (15 categories, 45 features)", "Result": "essentially no change (PR-AUC 0.1742 to 0.1756)"},
    {"Attempt": "Deeper/longer CatBoost (depth 6-8, 500-800 iterations)", "Result": "worse validation PR-AUC than a shallower, shorter model"},
])
st.table(negative_results.set_index("Attempt"))

st.header("Limitations")
st.markdown(
    "- Predicts the *observed* DineSafe outcome, not an establishment's true food safety\n"
    "- Non-Pass is a minority class (roughly 6-8% depending on the period)\n"
    "- Non-Pass prevalence drifts over time; train, validation, and test are not identically distributed\n"
    "- Historical-to-current establishment linkage relies on a legacy ID field with documented ambiguity\n"
    "- Raw predicted probabilities are poorly calibrated\n"
    "- All results come from one fixed future test period"
)

st.caption("See docs/FINAL_RESEARCH_SUMMARY.md for the full write-up.")
