# Toronto DineSafe Longitudinal Inspection Prediction

## What this project asks

How much does longitudinal inspection history improve prediction of an establishment's next DineSafe inspection outcome, and how does the amount and recency of available history affect predictive performance?

## Data

Toronto's public DineSafe export (`Dinesafe.csv`, infraction-row level) plus a historical archive (`Dinesafe Historical Data.zip`, 2001-2023). Both were audited and reconstructed to a clean inspection-level table before any modelling — see `docs/DATA_AUDIT.md` and `docs/DATA_RECONSTRUCTION.md`. Neither source file was ever modified.

## Prediction target

Binary: Pass (0) vs. Non-Pass (1, meaning Conditional Pass or Closed). The model predicts the *observed* DineSafe outcome, not an establishment's actual food safety. Only current-period inspections (2023-11-10 onward) are used as prediction targets; the historical archive is used only to build history features, because historical and current outcome rates differ structurally (see `docs/TEMPORAL_DISTRIBUTION_CHECK.md`).

## How the temporal split works

Strict, date-ordered, not random: train on the earliest target inspections (2023-11-10 to 2025-11-05), validate on later ones (2025-11-06 to 2026-04-09), test once on the latest ones (2026-04-10 to 2026-09-08). The same establishment can appear in more than one split, since the task is forecasting a later inspection using only information known before it.

## Main result

A 15-feature longitudinal representation (previous inspection + 365-day + 730-day rolling history) with a tuned CatBoost model reaches test PR-AUC ≈0.174, ROC-AUC ≈0.734. Most of the value comes from the most recent year of history; a second year, engineered rate features, more complex models, and a fuller infraction-category representation all added little beyond that. The model shows real ranking value (top 10% of risk-ranked inspections captures 28% of actual Non-Pass cases), but its raw probabilities are not well calibrated.

## Main limitation

The current structured DineSafe representation appears to be approaching a predictive ceiling for this task — several independent attempts to add information (more history, engineered features, model family, tuning, infraction category) each produced little to no improvement. See `docs/FINAL_RESEARCH_SUMMARY.md` for the full limitations list.

## Dashboard

Run `streamlit run app.py` to view the project dashboard. It presents the research question, the temporal split, the model comparison, the final model, the Top-K ranking result, calibration, and the limitations, all read directly from the saved files in `outputs/`. The dashboard only reads existing results, it doesn't retrain anything.

To run it locally: `pip install -r requirements.txt` then `streamlit run app.py`. It can also be deployed directly from this repo on Streamlit Community Cloud, pointing at `app.py`.

## What's in the repo and what isn't

The raw DineSafe export and the historical ZIP archive are not included in this repo (they're too large and are public data anyway, downloadable from the [Toronto Open Data DineSafe page](https://open.toronto.ca/dataset/dinesafe/)). A few of the larger intermediate files built from them (the full inspection-level and prediction-event tables) are also left out for the same reason. Everything the dashboard actually needs — the small result CSVs and figures in `outputs/` — is included, along with all 16 research notebooks (their saved outputs are visible directly on GitHub without rerunning anything).

This means the notebooks can't actually be re-run straight from a clean clone of this repo — every notebook reads one of those excluded intermediate files (and notebooks 13/14 read `Dinesafe.csv` directly). To reproduce the full pipeline from scratch: download `Dinesafe.csv` and the historical ZIP from Toronto Open Data, put them in the project root, run `build_longitudinal_dataset.py` to rebuild the intermediate tables, then run the notebooks in order. The saved CSVs and figures in `outputs/` are included specifically so the results can be inspected without doing any of that.

## Where things are

- `docs/FINAL_RESEARCH_SUMMARY.md` — full write-up
- `docs/FINAL_RESULTS_TABLE.md` — compact results table
- `docs/NOTEBOOK_GUIDE.md` — one-line summary of each notebook
- `notebooks/` — the research notebooks, in the order the work was done
- `outputs/` — saved result CSVs and figures referenced throughout the docs
