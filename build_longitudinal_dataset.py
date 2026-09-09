"""
Build a clean inspection-level dataset from Dinesafe.csv, and a longitudinal
version that adds pre-2024 history from the Historical Data ZIP.

No modelling, no features, no target column here - just a clean
(estId, inspectionDate) level table for later use.

Findings this script relies on come from docs/DATA_RECONSTRUCTION.md.
"""

import zipfile
import io
import pandas as pd
import numpy as np

CSV_PATH = "Dinesafe.csv"
ZIP_PATH = "Dinesafe Historical Data.zip"

pd.set_option("display.width", 140)

# ---------------------------------------------------------------------------
# 1. Load current data and remove wholesale-duplicated infractions
# ---------------------------------------------------------------------------

raw = pd.read_csv(CSV_PATH, dtype=str, low_memory=False)
print("Raw current rows loaded:", len(raw))

# The audit found ~170 inspections recorded twice, differing only in
# _id / unique_id / address formatting. Dedup on the fields that actually
# describe the infraction, ignoring row-identity and address formatting.
dedup_cols = ["estId", "inspectionDate", "typeDesc", "deficiencyDesc",
              "severity", "OutcomeDate", "OutcomeDesc", "amountFined"]

before = len(raw)
raw_clean = raw.drop_duplicates(subset=dedup_cols, keep="first").copy()
removed = before - len(raw_clean)
print(f"Rows removed as confirmed duplicates: {removed}")

# ---------------------------------------------------------------------------
# 2. Build the current inspection-level table
# ---------------------------------------------------------------------------

def summarize_inspection(g):
    sev = g["severity"].value_counts(dropna=True)
    n_minor = int(sev.get("M - Minor", 0))
    n_sig = int(sev.get("S - Significant", 0))
    n_crucial = int(sev.get("C - Crucial", 0))
    return pd.Series({
        "oldEstId": g["oldEstId"].iloc[0],
        "estName": g["estName"].iloc[0],
        "address": g["address"].iloc[0],
        "latitude": g["latitude"].iloc[0],
        "longitude": g["longitude"].iloc[0],
        "inspectionStatus": g["inspectionStatus"].iloc[0],
        "n_infractions": int(g["typeDesc"].notna().sum()),
        "n_minor": n_minor,
        "n_significant": n_sig,
        "n_crucial": n_crucial,
    })

current_insp = (
    raw_clean.groupby(["estId", "inspectionDate"], sort=False)
    .apply(summarize_inspection, include_groups=False)
    .reset_index()
)
current_insp["inspectionDate"] = pd.to_datetime(current_insp["inspectionDate"])
current_insp["source"] = "current"

print("\nCurrent inspection-level rows:", len(current_insp))
print(current_insp["inspectionStatus"].value_counts())

# sanity checks against the numbers in DATA_RECONSTRUCTION.md
assert len(current_insp) == 77475, "inspection count changed after dedup, check dedup logic"
status_counts = current_insp["inspectionStatus"].value_counts()
assert status_counts.get("Pass", 0) == 72788
assert status_counts.get("Conditional Pass", 0) == 4606
assert status_counts.get("Closed", 0) == 80
assert status_counts.get("Temporarily Not Operating", 0) == 1
assert current_insp.duplicated(subset=["estId", "inspectionDate"]).sum() == 0
print("Sanity checks passed: 77,475 inspections, status counts match the audit, no duplicate (estId, date) rows.")

current_insp = current_insp.sort_values(["estId", "inspectionDate"]).reset_index(drop=True)
current_insp.to_csv("outputs/inspection_level_current.csv", index=False)
print("Saved outputs/inspection_level_current.csv")

# ---------------------------------------------------------------------------
# 3. oldEstId -> estId mapping (unambiguous cases only)
# ---------------------------------------------------------------------------
# We keep estId as the entity key. oldEstId is only used to link historical
# records in. Where one oldEstId maps to more than one estId (804 cases,
# see DATA_RECONSTRUCTION.md section 5), we do not guess which estId the
# historical rows belong to, so those get no historical link.

old_to_new = raw_clean.dropna(subset=["oldEstId"]).groupby("oldEstId")["estId"].nunique()
unambiguous_old_ids = old_to_new[old_to_new == 1].index
old_to_new_map = (
    raw_clean[raw_clean["oldEstId"].isin(unambiguous_old_ids)]
    .drop_duplicates(subset=["oldEstId"])
    .set_index("oldEstId")["estId"]
    .to_dict()
)
print(f"\nUsable oldEstId -> estId links: {len(old_to_new_map)} (of {old_to_new.shape[0]} distinct oldEstId values)")

# ---------------------------------------------------------------------------
# 4. Load and fix historical files, build historical inspection-level table
# ---------------------------------------------------------------------------

CORRUPT_YEARS = {"2020", "2021", "2022"}

z = zipfile.ZipFile(ZIP_PATH)
names = sorted(n for n in z.namelist() if n.endswith(".csv"))

hist_frames = []
for name in names:
    year = name.split("_")[-1].replace(".csv", "")
    encoding = "latin-1" if year == "2023" else "utf-8"
    text = z.read(name).decode(encoding)

    if year in CORRUPT_YEARS:
        # known bug: doubled leading quote on the header line, and one
        # extra trailing quote on the last data row (see DATA_RECONSTRUCTION.md)
        if text.startswith('""'):
            text = '"' + text[2:]
        text = text.rstrip("\r\n")
        if text.endswith('"""'):
            text = text[:-1]

    df = pd.read_csv(io.StringIO(text), dtype=str)
    date_fmt = "%m/%d/%Y" if year == "2023" else "%Y-%m-%d"
    df["Inspection Date"] = pd.to_datetime(df["Inspection Date"], format=date_fmt)
    hist_frames.append(df)

hist_raw = pd.concat(hist_frames, ignore_index=True)
print("\nHistorical raw rows (2001-2023, all years, after known fixes):", len(hist_raw))

def summarize_hist_inspection(g):
    sev = g["Severity"].value_counts(dropna=True)
    return pd.Series({
        "estName": g["Establishment Name"].iloc[0],
        "address": g["Establishment Address"].iloc[0],
        "latitude": g["Latitude"].iloc[0],
        "longitude": g["Longitude"].iloc[0],
        "inspectionStatus": g["Establishment Status"].iloc[0],
        "n_infractions": int(g["Infraction Details"].notna().sum()),
        "n_minor": int(sev.get("M - Minor", 0)),
        "n_significant": int(sev.get("S - Significant", 0)),
        "n_crucial": int(sev.get("C - Crucial", 0)),
    })

hist_insp = (
    hist_raw.groupby(["Establishment ID", "Inspection Date"], sort=False)
    .apply(summarize_hist_inspection, include_groups=False)
    .reset_index()
    .rename(columns={"Establishment ID": "oldEstId", "Inspection Date": "inspectionDate"})
)
print("Historical inspection-level rows:", len(hist_insp))

# link to current estId via the unambiguous oldEstId map
hist_insp["estId"] = hist_insp["oldEstId"].map(old_to_new_map)

n_linked = hist_insp["estId"].notna().sum()
n_unlinked = hist_insp["estId"].isna().sum()
print(f"Historical inspections linked to a current estId: {n_linked}")
print(f"Historical inspections with no link (no matching oldEstId, or oldEstId ambiguous): {n_unlinked}")

hist_linked = hist_insp[hist_insp["estId"].notna()].copy()
hist_linked["source"] = "historical"

# ---------------------------------------------------------------------------
# 5. Combine current + historical, current wins on overlap
# ---------------------------------------------------------------------------

current_keys = set(zip(current_insp["estId"], current_insp["inspectionDate"]))
overlap_mask = hist_linked.apply(lambda r: (r["estId"], r["inspectionDate"]) in current_keys, axis=1)

n_overlap_dropped = overlap_mask.sum()
print(f"\nHistorical inspections dropped because current already has that (estId, date): {n_overlap_dropped}")

hist_kept = hist_linked[~overlap_mask].copy()

longitudinal = pd.concat([hist_kept, current_insp], ignore_index=True, sort=False)
longitudinal = longitudinal.sort_values(["estId", "inspectionDate"]).reset_index(drop=True)

# keep a consistent column order
cols = ["estId", "oldEstId", "estName", "address", "latitude", "longitude",
        "inspectionDate", "inspectionStatus", "n_infractions", "n_minor",
        "n_significant", "n_crucial", "source"]
longitudinal = longitudinal[cols]

print("\nFinal longitudinal inspection count:", len(longitudinal))
print("Distinct establishments (estId):", longitudinal["estId"].nunique())
print("Date range:", longitudinal["inspectionDate"].min(), "to", longitudinal["inspectionDate"].max())

assert longitudinal.duplicated(subset=["estId", "inspectionDate"]).sum() == 0, "duplicate (estId, date) in longitudinal table"

longitudinal.to_csv("outputs/inspection_level_longitudinal.csv", index=False)
print("Saved outputs/inspection_level_longitudinal.csv")

# ---------------------------------------------------------------------------
# 6. Verification summary
# ---------------------------------------------------------------------------

overlap_start = pd.Timestamp("2023-11-10")
overlap_end = pd.Timestamp("2023-12-31")
current_in_overlap = current_insp[
    (current_insp["inspectionDate"] >= overlap_start) & (current_insp["inspectionDate"] <= overlap_end)
]

print("\n--- Verification summary ---")
print("Final current inspection count:", len(current_insp))
print("Final longitudinal inspection count:", len(longitudinal))
print("Establishments represented (longitudinal):", longitudinal["estId"].nunique())
print("Earliest date:", longitudinal["inspectionDate"].min())
print("Latest date:", longitudinal["inspectionDate"].max())
print("Historical inspections with a linked estId:", n_linked)
print("Historical inspections with no link:", n_unlinked)
print("Current inspections in the Nov-Dec 2023 overlap window:", len(current_in_overlap))
print("Raw current rows removed due to confirmed duplication:", removed)
