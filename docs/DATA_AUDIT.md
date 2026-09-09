# DineSafe Data Audit Report

Audit date: 2026-09-09
Scope: inspection of existing project files only. No modelling, no feature engineering, no merging, no modification of source files.

## A. Project files discovered

The project directory contains exactly three files (no README, no code, no local API documentation):

| File | Size | Type |
|---|---|---|
| `Dinesafe.csv` | 43,253,408 bytes (~41.3 MB) | Current DineSafe export (Toronto Open Data) |
| `Dinesafe Historical Data.zip` | 11,490,618 bytes (~11.0 MB) | ZIP archive of 23 yearly historical CSVs (2001–2023) |
| `DineSafe_Literature_Review_IEEE.docx` | 52,552 bytes | Literature review / research-design memo (IEEE-style) |

No `README`, no metadata file, no existing analysis/modelling code, and **no local API documentation** were found. Per instructions, the CKAN API was not queried, since no local API documentation exists to justify or scope such a request.

## B. Current CSV structure (`Dinesafe.csv`)

- Rows: 115,899 (data rows; 115,902 lines including header, minus 3 for the header line and pandas' handling)
- Columns: 18
- Columns: `_id, unique_id, estId, oldEstId, estName, address, inspectionStatus, phone, inspectionDate, observation, typeDesc, deficiencyDesc, severity, OutcomeDate, OutcomeDesc, amountFined, latitude, longitude`
- All columns load as strings; `inspectionDate` and `OutcomeDate` are date-like strings (`YYYY-MM-DD`) and require explicit parsing — they are not native dates in the raw file.

**Missing-value counts:**

| Column | Missing | % |
|---|---|---|
| `oldEstId` | 4,662 | 4.0% |
| `phone` | 10,942 | 9.4% |
| `typeDesc` | 42,435 | 36.6% |
| `deficiencyDesc` | 42,435 | 36.6% |
| `severity` | 47,673 | 41.1% |
| `OutcomeDate` | 115,657 | 99.8% |
| `OutcomeDesc` | 115,457 | 99.6% |
| `amountFined` | 115,658 | 99.8% |
| all other columns | 0 | 0% |

`typeDesc`/`deficiencyDesc`/`severity` are missing together on rows that represent an inspection with no recorded infraction (i.e., a clean pass visit) — consistent with the infraction-level grain described in section C.

**Unique-value counts for key columns:**

| Column | Unique values |
|---|---|
| `estId` | 18,898 |
| `oldEstId` | 15,944 |
| `estName` | 14,398 |
| `address` | 16,406 |
| `inspectionDate` | 833 distinct dates |
| `inspectionStatus` | 4 |
| `typeDesc` | 359 |
| `deficiencyDesc` | 36 |
| `severity` | 3 |
| `OutcomeDesc` | 6 |

**`inspectionStatus` value counts:**

| Value | Count | % |
|---|---|---|
| Pass | 96,854 | 83.6% |
| Conditional Pass | 18,543 | 16.0% |
| Closed | 500 | 0.43% |
| Temporarily Not Operating | 2 | ~0% |

**`severity` value counts (of non-missing):** M - Minor 42,021; S - Significant 22,965; C - Crucial 3,240.

**Date columns and ranges:**
- `inspectionDate`: 2023-11-10 to 2026-09-08 (0 missing). The current CSV covers roughly a 34-month rolling window, not the full DineSafe history.
- `OutcomeDate`: 2023-12-11 to 2026-08-12, but populated for only 242 of 115,899 rows (0.2%) — this field only fires for a small number of legal/enforcement outcomes (`OutcomeDesc` values: Pending, Conviction - Fined, Conviction: Fined, Cancelled, Charges Withdrawn, Charges Quashed), not for ordinary inspections.

**Likely identifier columns:**
- `estId` — Salesforce-style alphanumeric ID (e.g. `001Vo000013QjdPIAS`), 18,898 distinct values. This is the modern, primary establishment identifier used by the current system.
- `oldEstId` — purely numeric legacy ID (e.g. `10752656`), 15,944 distinct values, 4,662 missing. This matches the `Establishment ID` format used in the Historical Data ZIP (see D).
- `_id` / `unique_id` — both unique per row (115,899 distinct each); these identify the raw row/infraction record, not the establishment or the inspection.

**Likely inspection identifier/date column:** `inspectionDate` combined with `estId` is the practical inspection key — there is no single "inspection ID" column in the current CSV (unlike the historical files, which do have `Inspection ID`).

**Outcome/status columns:** `inspectionStatus` (Pass / Conditional Pass / Closed / Temporarily Not Operating) is the inspection-level outcome. `OutcomeDesc` + `OutcomeDate` + `amountFined` describe rare downstream legal/enforcement outcomes, not the inspection result itself.

**Infraction/severity-related columns:** `typeDesc` (infraction type, free text, 359 distinct), `deficiencyDesc` (36 distinct higher-level deficiency categories), `severity` (Minor/Significant/Crucial), `observation` (5 distinct boilerplate sentences describing the inspection regulation basis).

## C. Actual row grain (verified from data, not column names)

**The current CSV is at infraction-row grain, not inspection grain and not establishment grain.** This was verified directly:

- 115,899 total rows but only 77,475 distinct `(estId, inspectionDate)` combinations — so many rows share the same establishment+date.
- Within a shared `(estId, inspectionDate)` group, `inspectionStatus` is always constant (0 of 77,475 groups have more than one distinct status), confirming that the outcome is recorded at the inspection level, while `typeDesc`/`deficiencyDesc`/`severity` vary row-to-row within that group — i.e., each row is one infraction (or one "no infraction" placeholder row) tied to a single inspection visit.
- The maximum number of rows sharing one `(estId, inspectionDate)` pair is 24 (one heavily-cited inspection had 12 distinct infractions, apparently listed twice — see finding I-1 below).
- 42,435 rows (36.6%) have no `typeDesc`/`deficiencyDesc`/`severity` at all — these are the "clean" rows representing an inspection with zero infractions.

**Conclusion:** one row = one infraction observed during an inspection, or (if no infractions were found) one placeholder row for that inspection. The inspection-level entity must be reconstructed by grouping on `(estId, inspectionDate)`.

## D. Historical Data ZIP contents (`Dinesafe Historical Data.zip`)

Contents (not modified, not extracted to disk permanently — read in-memory only):

- A single top-level folder `Dinesafe Historical data/` containing 23 files: `dinesafe_hist_2001.csv` through `dinesafe_hist_2023.csv` (one file per calendar year).
- Total uncompressed size: ~83.0 MB; total historical rows across all 23 files: roughly 340,000+ infraction-level rows (sum of per-file row counts, e.g. 2001: 6,066 rows, 2010: 14,920 rows, 2019: 34,493 rows, 2023: 37,838 rows).
- Historical schema (identical across at least the 2001, 2012, and 2023 files checked): `Rec #, Establishment ID, Inspection ID, Establishment Name, Establishment Type, Establishment Address, Latitude, Longitude, Establishment Status, Min. Inspections Per Year, Infraction Details, Inspection Date, Severity, Action, Outcome, Amount Fined`.
- This schema is **not identical** to the current CSV's schema: it has an explicit `Inspection ID` (the current CSV has none), an `Establishment Type` column (absent from the current CSV), and an `Action` column (absent from the current CSV); it lacks the current CSV's `phone`, `unique_id`, and `oldEstId`/`estId` split.
- Date format differs: historical `Inspection Date` is `MM/DD/YYYY` in the 2023 file and `YYYY-MM-DD` in the 2001 file — **the date format is not consistent across years and must be checked file-by-file before any parsing.**
- Encoding: the 2023 file (and likely others) contains non-UTF-8 bytes (`UnicodeDecodeError` on strict UTF-8 read); it parses successfully as Latin-1. This must be handled explicitly.
- The 2022 file failed to parse with the standard C parser (`EOF inside string`, error near row 30,478) even under Latin-1 decoding — there appears to be a malformed/unescaped quoted field somewhere in that file. This was not fully root-caused and is flagged as UNVERIFIED pending a dedicated parsing pass (e.g. Python's `csv` module with `on_bad_lines` handling, or manual inspection around the reported line).
- **Identifier compatibility:** the historical `Establishment ID` field is numeric (e.g. `10586847`, `9013060`) and matches the format of the current CSV's `oldEstId` column (also numeric, e.g. `10752656`), not the current CSV's `estId` (Salesforce-style alphanumeric). This was confirmed by direct set overlap: of 15,944 distinct `oldEstId` values in the current CSV, 11,223 also appear as `Establishment ID` in the 2023 historical file alone. This confirms the historical ZIP **can** extend longitudinal history for a large majority of current establishments, joined via `oldEstId` ↔ `Establishment ID` — **not** via `estId`.
- Because `oldEstId` is missing for 4,662 of 115,899 current rows, a portion of current establishments (those without an `oldEstId`) cannot be joined to historical data by this key and would need a fallback (e.g. name+address matching), which is unverified and out of scope for this audit.
- Date coverage: historical files span 2001-02 through 2023-12 (2023 file's inspection dates run 01/03/2023–12/29/2023). The current CSV starts 2023-11-10. **There is a ~1.5 month overlap window (Nov–Dec 2023) between the historical 2023 file and the current CSV**, which could be used to validate that the two sources agree during the overlap, before treating them as a single continuous timeline.
- The historical ZIP does **not** appear to contain a newer version of the current dataset — it stops at the end of 2023, while the current CSV covers Nov 2023–Sep 2026. They are complementary, not duplicative, for the vast majority of their respective date ranges.

## E. Date coverage summary

| Source | Earliest | Latest |
|---|---|---|
| Current CSV (`inspectionDate`) | 2023-11-10 | 2026-09-08 |
| Historical ZIP (aggregate, per-year files) | 2001-02 (2001 file) | 2023-12-29 (2023 file) |

Combined, and pending the overlap-validation and identifier-join work noted above, the two sources could in principle provide inspection history from 2001 through 2026 — over two decades longer than the current CSV alone.

## F. Identifier structure

- `estId` (current, Salesforce-style) is the canonical modern establishment key in the current CSV; 18,898 distinct values.
- `oldEstId` (current, numeric) is a legacy key, 1:1 with `estId` in the current file (0 of 18,898 `estId` groups map to more than one `oldEstId`), but **804 of 15,944 distinct `oldEstId` values map to more than one `estId`** — verified directly. This means the legacy→modern mapping is not always one-to-one, and naive joining on `oldEstId` alone could conflate multiple current establishments that once shared (or were recorded under) the same legacy ID.
- No single "inspection ID" exists in the current CSV; the historical files do have `Inspection ID`, which is not present in the current file and cannot be cross-checked without the join described above.

## G. Inspection outcome structure

- Inspection-level outcome lives in `inspectionStatus`, constant within each `(estId, inspectionDate)` group: Pass (83.6%), Conditional Pass (16.0%), Closed (0.43%), Temporarily Not Operating (~0%).
- The planned binary target (Pass=0, Non-Pass=1 where Non-Pass = Conditional Pass ∪ Closed) is directly constructible from `inspectionStatus` at the inspection grain (after grouping infraction rows).
- 15,731 of 18,898 establishments (83%) have 2 or more distinct inspection dates; 58,577 previous→next inspection pairs exist at the current data's inspection grain. 3,167 establishments have only a single inspection in the current window (no "previous inspection" feature possible without historical data).
- Median gap between consecutive inspections for the same establishment: 141 days.

## H. Relevant data-quality findings

1. **Near-duplicate infraction rows.** At least one `(estId, inspectionDate)` group (estId `001Vo000013QoD5IAK`, 2025-07-09) has its entire 12-infraction inspection listed twice (24 rows total), with the two copies differing only in a formatting variant of the `address` field ("Unit-7" vs "7"). These are not exact duplicate rows (so a naive full-row `drop_duplicates` would not catch them), but they are functionally the same inspection/infraction repeated. This was confirmed by direct cell-by-cell comparison. The prevalence of this pattern across the full file is UNVERIFIED — only one case was manually inspected in depth; a systematic near-duplicate check (grouping on all columns except address/`_id`/`unique_id`) is a recommended next step.
2. **Discrepancy vs. the literature review's cited audit numbers.** The literature review document (Section 1) cites a prior audit of "the current DineSafe CSV" reporting 18,898 establishments, 115,899 rows, 77,475 inspections, 15,731 establishments with ≥2 inspections, 58,577 prev→next pairs, a 141-day median gap, and 804 `oldEstId`→multiple-`estId` cases — **all of which matched exactly** on re-verification here. However, the literature review cites **64 Closed cases**, while the current file has **500 Closed cases**. All other numbers matching exactly but this one differing suggests the current `Dinesafe.csv` file has been refreshed/updated since the literature review's audit was performed (this is plausible since the current CSV is a live, rolling export whose "Closed" count would grow over time), not that the current re-verification is wrong. This means Non-Pass volume (Conditional Pass + Closed) is now 19,043 rather than 18,607, and any prior assumption that "Closed is extremely rare, so three-class modelling is fragile" should be re-checked against the live file, though the qualitative conclusion (Closed still <1% of inspections) is very likely unchanged.
3. **Historical ZIP encoding is not pure UTF-8.** At least the 2023 file contains non-UTF-8 bytes; must be read with an explicit fallback encoding (e.g. Latin-1) or errors="replace".
4. **Historical ZIP date format is inconsistent across years** (`YYYY-MM-DD` in 2001, `MM/DD/YYYY` in 2023 — the exact file(s) where the format changes is UNVERIFIED and needs a full per-year check before any parsing pipeline is built).
5. **The 2022 historical file has a CSV parsing error** (malformed/unescaped field near row 30,478) under the standard C parser even with Latin-1 decoding. Root cause UNVERIFIED; needs a dedicated, tolerant parse.
6. **`oldEstId` is not always unique to one `estId`** (804 legacy IDs map to multiple current IDs) — this directly affects any attempt to join historical data onto current establishments and is explicitly called out as an unresolved identity-resolution issue in the literature review as well.
7. **4,662 current rows (4.0%) have no `oldEstId` at all**, so a numeric-ID join to the historical ZIP cannot recover history for those rows/establishments without a fallback matching strategy (not attempted here).

## I. Potential temporal/leakage concerns identified from the raw structure

- The current CSV's row grain is infraction-level, not inspection-level. Any feature engineering must first collapse to `(estId, inspectionDate)` before defining "previous inspection" features — using raw infraction rows directly as independent observations would leak same-inspection infraction information into what should be a purely historical feature set, and would also let information about the *outcome* inspection's own infractions leak into its own feature row if not handled carefully.
- `OutcomeDate`/`OutcomeDesc`/`amountFined` are populated after (and because of) certain inspection outcomes (legal/enforcement actions) — these must never be used as of-inspection-time features for the inspection they are attached to, since they can post-date the inspection itself and are only known once the outcome has already occurred.
- The near-duplicate inspection rows (H-1) could inflate historical infraction counts (e.g., "prior infraction count" features) for affected establishments if not deduplicated at the inspection-reconstruction step.
- If the historical ZIP is later joined in, the `oldEstId`→multiple-`estId` ambiguity (804 cases) creates a risk of merging two genuinely different current establishments' histories together under a shared legacy ID, artificially extending or contaminating one establishment's longitudinal history with another's.
- The current CSV's date range (Nov 2023–Sep 2026) already includes "future" dates relative to typical analysis; no evidence of look-ahead was found, but any pipeline must confirm system clock/extraction date vs. `inspectionDate` max before treating today's date as a safe cutoff.

## J. What is still unknown (explicitly UNVERIFIED)

- UNVERIFIED: whether near-duplicate infraction-row pairs (H-1) occur elsewhere in the file beyond the one manually inspected case, and at what overall rate.
- UNVERIFIED: the exact file(s) within the historical ZIP where the `Inspection Date` format changes from `YYYY-MM-DD` to `MM/DD/YYYY`.
- UNVERIFIED: the root cause and extent of the 2022 historical file's CSV parsing error, and whether other yearly files have similar issues (only 2001, 2012, 2022, and 2023 were directly inspected).
- UNVERIFIED: whether the discrepancy in Closed-case counts (64 vs. 500, finding H-2) is fully explained by a dataset refresh, or reflects some other definitional change — the literature review's other cited figures all matched exactly, which supports the refresh explanation but does not confirm it with a timestamped snapshot of the file used for the original audit.
- UNVERIFIED: whether establishments lacking `oldEstId` (4,662 rows) can be reliably matched to historical records via name/address, and how much longitudinal history that would recover.
- UNVERIFIED: whether the CKAN API (mentioned in the DineSafe developer documentation quoted by the user, but not present locally as a file) offers any additional fields, a true inspection-level grain, or additional history not present in either the current CSV or the historical ZIP — no API request was made, per instructions, since no local documentation exists to scope one.
- No local README, schema dictionary, or Toronto Open Data data-dictionary file was found in the project, so all column semantics above are inferred from data inspection and the (separately trustworthy) literature review, not from an official field-level data dictionary.

## K. Recommended next investigation before feature engineering

1. Reconstruct the inspection-level table from the current CSV by grouping infraction rows on `(estId, inspectionDate)`, and validate that `inspectionStatus` is constant within every group (already confirmed at 100% for the current file) before relying on it going forward.
2. Systematically check for near-duplicate inspection groups across the full file (not just the one case found), using a similarity-tolerant comparison (e.g., ignore `address` formatting) to decide whether deduplication is needed before counting infractions.
3. Resolve, or explicitly document as unresolved, the 804 `oldEstId`→multiple-`estId` cases before attempting any join to the historical ZIP.
4. Parse each of the 23 historical yearly files individually (correct encoding, correct date format per file, tolerant CSV parsing for the 2022 file), and validate the current-CSV/historical overlap window (Nov–Dec 2023) by comparing establishment status and infraction counts for the same `(oldEstId, date)` in both sources, to confirm the two datasets can be treated as one continuous timeline.
5. Re-derive the literature review's cited dataset statistics (especially the Closed-case count) against whatever CSV snapshot is actually used for modelling, and note the snapshot date, since the current file already differs from the literature review's cited figures on this one dimension.
6. Only after 1–4 above are resolved, decide whether/how to merge historical and current data into a single longitudinal source — do not merge before establishment-identity and schema-alignment issues are settled.
