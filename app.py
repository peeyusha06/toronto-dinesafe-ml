"""Dashboard for the Toronto DineSafe inspection prediction project. Reads saved results only."""

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="DineSafe Inspection Prediction", layout="centered")

OUT = "outputs"


def load_csv(name):
    return pd.read_csv(f"{OUT}/{name}")


st.title("Toronto DineSafe Longitudinal Inspection Prediction")
st.write(
    "How much does longitudinal inspection history improve prediction of an establishment's "
    "next DineSafe inspection outcome, and how does the amount and recency of available history "
    "affect predictive performance?"
)

# project scale, kept small rather than as large kpi cards
scale = st.columns(3)
scale[0].metric("Current inspections", "77,475", border=True)
scale[1].metric("Establishments", "18,898", border=True)
scale[2].metric("Inspection record", "2001-2026", border=True)
st.caption(
    "Prediction targets begin on 2023-11-10, the first date in the current export. Evaluation is "
    "strictly temporal, so the model is fitted on earlier inspections and scored on later ones."
)

st.write(
    "The target is the recorded inspection result, Pass against Non-Pass, where Non-Pass covers "
    "Conditional Pass and Closed. The 2001-2023 archive is used only to build history features, "
    "because Non-Pass was recorded far less often in that period than it is now. What gets "
    "predicted is the observed DineSafe outcome, not an establishment's underlying food safety."
)

st.header("Data and prediction setup")
split_table = pd.DataFrame([
    {"Split": "Train", "Date range": "2023-11-10 to 2025-11-05", "Rows": "45,334"},
    {"Split": "Validation", "Date range": "2025-11-06 to 2026-04-09", "Rows": "11,740"},
    {"Split": "Test", "Date range": "2026-04-10 to 2026-09-08", "Rows": "12,692"},
])
st.table(split_table.set_index("Split"))
st.write(
    "Inspections are ordered by date so the model is trained on earlier observations and "
    "evaluated on later ones. A random split would let a later inspection help predict an "
    "earlier one. Non-Pass prevalence also drifts upward across the three periods, from about "
    "5.5% in train to 6.4% in validation and 7.5% in test."
)

st.header("How the study progressed")
st.write("Each step changed one thing and was scored on the same split.")
with st.container(border=True):
    st.markdown(
        "1. **Previous inspection only.** Seven features, the simplest useful starting point.\n"
        "2. **Plus 365-day history.** The largest single gain in the whole study.\n"
        "3. **Plus 730-day history.** A smaller further gain, which fixed the 15-feature set.\n"
        "4. **Model comparison.** Logistic Regression, Random Forest and CatBoost on those "
        "same features.\n"
        "5. **Feature engineering.** Seven rate and recency features added, then dropped.\n"
        "6. **Tuning.** A small validation-only search over Logistic Regression and CatBoost "
        "settings.\n"
        "7. **History depth.** Test rows grouped by how much pre-2023 history each "
        "establishment had.\n"
        "8. **Category experiment.** Infraction type added as history features, in two "
        "versions.\n"
        "9. **Top-K.** How well the final ranking concentrates observed Non-Pass cases.\n"
        "10. **Calibration.** Whether the predicted scores can be read as probabilities."
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
st.dataframe(progression.set_index("Feature set / model").round(4), width="stretch")

st.subheader("Recency vs. longer history")
fig, ax = plt.subplots(figsize=(5, 3.5))
labels = ["Previous\ninspection only", "+365-day\nhistory", "+730-day\nhistory"]
values = [baseline["test_pr_auc"], h365["test_pr_auc"], h730["test_pr_auc"]]
ax.bar(labels, values, color="#4a6f8a")
ax.set_ylabel("Test PR-AUC")
st.pyplot(fig)
st.write("Most of the gain came from adding recent history. Going from one year to two produced a smaller improvement.")

st.header("Final model")
with st.container(border=True):
    st.markdown(
        "**CatBoost**, tuned on the validation period only.\n\n"
        "300 iterations, depth 4, learning rate 0.05, 15 longitudinal features, threshold 0.70."
    )

# pr-auc and roc-auc are threshold free, so they lead
headline = st.columns(2)
headline[0].metric("Test PR-AUC", f"{tuned['test_pr_auc']:.4f}", border=True)
headline[1].metric("Test ROC-AUC", f"{tuned['test_roc_auc']:.4f}", border=True)

threshold_table = pd.DataFrame([
    {"Metric": "Precision", "Value": f"{tuned['test_precision']:.4f}"},
    {"Metric": "Recall", "Value": f"{tuned['test_recall']:.4f}"},
    {"Metric": "F1", "Value": f"{tuned['test_f1']:.4f}"},
    {"Metric": "Accuracy", "Value": f"{tuned['test_accuracy']:.4f}"},
])
st.table(threshold_table.set_index("Metric"))
st.caption("Measured at the 0.70 threshold, which was locked on validation before the test set was scored.")

st.markdown(
    "- PR-AUC is the number to read first. Non-Pass is about 7.5% of the test period, so "
    "accuracy stays high even for a model that flags nothing.\n"
    "- The output is more useful for ranking establishments by risk than for stating how likely "
    "a Non-Pass result is.\n"
    "- The raw probabilities are poorly calibrated, so a score of 0.70 does not mean a 70% chance "
    "of Non-Pass."
)

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
st.dataframe(topk_display.round(3).set_index("Top K"), width="stretch")

top10 = topk[topk["k_percent"] == 10].iloc[0]
st.write(
    f"**Top 10% of the test ranking contains about {top10['recall_at_k']*100:.0f}% of observed "
    f"Non-Pass cases**, roughly {top10['lift_at_k']:.1f} times the rate of picking inspections at random."
)
st.image(f"{OUT}/figures/top_k_recall_curve.png")
st.write(
    "The ranking is measured on inspections that already happened, so it shows concentration "
    "rather than any effect of acting on the ranking."
)

st.header("Calibration")
st.write("Are the predicted probabilities themselves trustworthy, or just the ranking?")
calib = load_csv("calibration_results.csv").iloc[0]
st.image(f"{OUT}/figures/catboost_calibration_curve.png")
col3, col4 = st.columns(2)
with col3:
    st.metric("Brier score", round(calib["test_brier_score"], 4))
with col4:
    st.metric("Log loss", round(calib["test_log_loss"], 4))
bins = load_csv("calibration_bins.csv")
highest_bin = bins.iloc[-1]
st.write(
    f"The curve sits well below the diagonal, so the predicted values run high everywhere. In the "
    f"highest decile the mean predicted value is {highest_bin['mean_predicted_probability']:.3f} "
    f"while the observed Non-Pass rate is {highest_bin['observed_non_pass_rate']:.3f}. The scores "
    f"order establishments sensibly, but they should not be quoted as probabilities."
)

st.header("What the model relies on")
shap_imp = load_csv("catboost_shap_importance.csv").head(5)
fig2, ax2 = plt.subplots(figsize=(5, 3))
ax2.barh(shap_imp["feature"][::-1], shap_imp["mean_abs_shap"][::-1], color="#4a6f8a")
ax2.set_xlabel("mean |SHAP value|")
st.pyplot(fig2)
st.write("These values describe what the model leans on. They are not causal effects.")

st.header("What did not improve the model")
st.write(
    "Several reasonable ideas were tested and kept in the write-up even though they did not help."
)
negative_results = pd.DataFrame([
    {"Attempt": "Seven engineered rate and recency features",
     "Result": "PR-AUC 0.1732 to 0.1726, no meaningful gain"},
    {"Attempt": "Infraction-category history, 15 categories",
     "Result": "PR-AUC 0.1742 to 0.1756, essentially flat"},
    {"Attempt": "Random Forest on the same 15 features",
     "Result": "PR-AUC 0.1154, weaker than both other models"},
    {"Attempt": "Second year of history, 365 to 730 days",
     "Result": "PR-AUC 0.1624 to 0.1732, a real but diminishing gain"},
    {"Attempt": "Deeper and longer CatBoost settings",
     "Result": "lower validation PR-AUC than the shallow model"},
    {"Attempt": "Using the raw scores as probabilities",
     "Result": "poorly calibrated, overconfident across the range"},
])
st.table(negative_results.set_index("Attempt"))

st.header("Limitations")
st.markdown(
    "- Predicts the *observed* DineSafe outcome, not an establishment's true food safety\n"
    "- Non-Pass is a minority class (roughly 6-8% depending on the period)\n"
    "- Non-Pass prevalence drifts over time, so train, validation and test are not identically distributed\n"
    "- Historical-to-current establishment linkage relies on a legacy ID field with documented ambiguity\n"
    "- Raw predicted probabilities are poorly calibrated\n"
    "- All results come from one fixed future test period"
)
