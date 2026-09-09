# DineSafe Data Reconstruction & Historical Validation Report

Audit date: 2026-09-09
Scope: inspection-grain reconstruction, duplicate diagnostics, historical ZIP file-by-file audit, current/historical overlap validation, and `oldEstId`→`estId` identity analysis. No merging, no feature engineering, no modelling was performed. Source files (`Dinesafe.csv`, `Dinesafe Historical Data.zip`) were not modified.

Outputs produced:
- [outputs/data_quality/current_inspection_summary.csv](../outputs/data_quality/current_inspection_summary.csv) — one row per reconstructed `(estId, inspectionDate)` inspection.
- [outputs/data_quality/duplicate_inspection_groups.csv](../outputs/data_quality/duplicate_inspection_groups.csv) — suspicious wholesale-duplicated inspection groups.
- [outputs/data_quality/historical_file_audit.csv](../outputs/data_quality/historical_file_audit.csv) — per-year audit of the 23 historical files.
- [outputs/data_quality/overlap_validation.csv](../outputs/data_quality/overlap_validation.csv) — inspection-level comparison of current vs. historical-2023 for the Nov–Dec 2023 overlap window.
- [outputs/data_quality/oldEstId_identity_analysis.csv](../outputs/data_quality/oldEstId_identity_analysis.csv) — per-`oldEstId` classification of the 804 ambiguous legacy-ID cases.

---

## 1. Current data: true inspection grain

Verified again, on the full file: `inspectionStatus` is constant within every `(estId, inspectionDate)` group (0 of 77,475 groups have more than one distinct value). Grouping is therefore safe.

**The previous audit's status counts (Pass 96,854 / Conditional Pass 18,543 / Closed 500 / Temporarily Not Operating 2) were raw infraction-row counts, not inspection counts — confirmed by re-deriving them from the same file.** Rows are duplicated across an inspection whenever there is more than one infraction, which inflates every raw-row status count in exact proportion to how many infractions each inspection happened to have.

**TRUE inspection-level outcome distribution** (77,475 reconstructed inspections, 18,898 establishments):

| Outcome | Inspections | % of inspections |
|---|---|---|
| Pass | 72,788 | 93.950% |
| Conditional Pass | 4,606 | 5.945% |
| Closed | 80 | 0.103% |
| Temporarily Not Operating | 1 | 0.001% |

- **Non-Pass (Conditional Pass + Closed): 4,686 inspections, 6.048% of all inspections.**
- **Temporarily Not Operating: 1 inspection, 0.001%** — reported separately, not assigned to either class per instructions.

This resolves most of the "Closed 500 vs. 64" discrepancy flagged in the prior audit: the raw-row Closed count (500) was never a count of Closed *inspections* — the true inspection-level Closed count is **80**. This is much closer to (though still not identical to) the literature review's cited figure of 64. The remaining 80-vs-64 gap is consistent with the CSV being a live, rolling export that has grown since the literature review's audit was performed (see Section 6), not with a methodological error in either audit.

Additional structural facts confirmed during reconstruction:
- 42,379 of 77,475 inspections (54.7%) have a "blank infraction placeholder" row (no `typeDesc`/`deficiencyDesc`/`severity`) — i.e., a clean visit with zero recorded infractions.
- Raw rows per inspection: median 1, mean 1.50, max 24 (see Section 2 for why 24 is an outlier, not a genuine 24-infraction visit).

## 2. Systematic near-duplicate analysis

A content-based diagnostic key was built for every raw row using all columns **except** `_id`, `unique_id`, and a normalized version of `address` (lowercased, `Unit-`/`#`/punctuation stripped, whitespace collapsed) — i.e., exactly the fields that legitimately vary only because of row identity or address-formatting noise. A plain `drop_duplicates()` on the raw columns would miss these because the raw `address` strings differ by formatting even when everything else is identical.

- **614 of 115,899 raw rows (0.53%) share their full diagnostic key with at least one other row.**
- Collapsing to the inspection level and checking whether an inspection's raw-row count is an exact whole-number multiple (≥2×) of its count of *distinct* infractions — i.e., every infraction in the inspection has an exact repeated twin elsewhere in the same inspection — identified **170 suspicious inspection groups**, all with ratio exactly **2.0** (meaning each of these inspections is recorded exactly twice, never three or more times).
- **Affected establishments: 36.** **Affected raw rows: 720** (0.62% of all rows).
- In every one of the 170 groups, the two copies of each infraction differ **only** in `_id`, `unique_id`, and an address-formatting variant (specifically, `"Unit-102D"`-style vs. `"102D"`-style unit notation — the same pattern the prior audit found for its one manually inspected example). `estName`, `inspectionStatus`, `typeDesc`, `deficiencyDesc`, `severity`, `OutcomeDate`, `OutcomeDesc`, `amountFined`, `phone`, `latitude`, `longitude`, and `estId`/`oldEstId` were identical between copies in every checked example.

**Examples** (full detail in `duplicate_inspection_groups.csv`):
- `estId 001Vo000013PoTqIAK`, `2025-06-13`: 1 distinct infraction, recorded as 2 rows; addresses `"4002 Sheppard Ave E Unit-102D M1S 4R5"` vs. `"4002 Sheppard Ave E 102D M1S 4R5"`.
- `estId 001Vo000013QE4dIAG`, `2024-08-06`: 3 distinct infractions, recorded as 6 rows (each infraction duplicated once); same address-formatting pattern.

**Classification: this is formatting duplication, not exact duplication and not two genuinely different inspections.** Every checked case has identical substantive content (same establishment, same date, same status, same infractions, same severities) and differs only in row-identity fields and a cosmetic address-unit-notation variant. This is consistent with the same inspection having been ingested twice from two slightly different export/formatting passes.

**Recommendation (evidence-based, not yet implemented):** before any feature engineering, deduplicate at the inspection level by collapsing each `(estId, inspectionDate)` group to its distinct-infraction set (ignore `_id`/`unique_id`/address-formatting variants) rather than by raw full-row `drop_duplicates()`. This affects a small but non-trivial number of establishments (36) and would otherwise double-count infractions and inflate "prior infraction count" features for those establishments if left unresolved. The 614-raw-row figure above is an upper bound; not all of it was traced to the wholesale-duplication pattern, so a residual set of individually-duplicated infraction rows (not full inspections) may still exist — this residual is UNVERIFIED and would need its own pass if pursued.

## 3. Historical ZIP: full file-by-file audit

All 23 yearly files (2001–2023) were parsed individually. Full detail in `historical_file_audit.csv`.

| Year | Rows | Encoding | Date format | Notes |
|---|---|---|---|---|
| 2001–2019 | 6,066 → 34,493 (growing) | UTF-8 | `YYYY-MM-DD` | Clean parse, 0 date failures |
| 2020 | 11,714 | UTF-8 | `YYYY-MM-DD` | **Corrupted, but fully recoverable — see below** |
| 2021 | 9,070 | UTF-8 | `YYYY-MM-DD` | **Corrupted, but fully recoverable — see below** |
| 2022 | 30,478 | UTF-8 | `YYYY-MM-DD` | **Corrupted, but fully recoverable — see below** |
| 2023 | 37,836 | **Latin-1** (not UTF-8) | **`MM/DD/YYYY`** (not ISO) | Clean parse once decoded as Latin-1 |

All 23 files share the same 16-column schema (`Rec #, Establishment ID, Inspection ID, Establishment Name, Establishment Type, Establishment Address, Latitude, Longitude, Establishment Status, Min. Inspections Per Year, Infraction Details, Inspection Date, Severity, Action, Outcome, Amount Fined`) once the 2020/2021/2022 corruption is corrected — the earlier apparent "no `Inspection Date` column" finding for those three years was an artifact of the corruption below, not a real schema difference.

**Root cause of the 2020/2021/2022 parsing failures — fully diagnosed, not a guess:**
1. The header line of each of these three files begins with a **duplicated leading quote character** (`""Rec #","Establishment ID",...` instead of `"Rec #","Establishment ID",...`). Under standard CSV quoting rules this is parsed as an escaped literal quote inside an opening quoted field that never closes, which corrupts quote-parity for every field that follows.
2. The **final data row** of each of these three files has one **extra trailing quote character** appended after its last (empty) field — confirmed by direct byte-level inspection of the file tails (e.g. 2020 ends `,"",""\"` instead of `,"",""`). This is what produced the earlier "EOF inside string" error, and it is why the error appeared to be near the last row of the file, not at some arbitrary internal row.
3. Both defects were present in **all three affected files** in the identical form, which is more consistent with a single shared export/packaging bug for these three years than with three independent, unrelated corruptions.

**Recovery verified:** stripping the duplicated leading quote from line 1 and the single extra trailing quote from the last line allows all three files to parse cleanly with the standard C parser, 0 date-parse failures, and plausible row counts (2020: 11,714 rows / 6,633 establishments; 2021: 9,070 rows / 5,431 establishments; 2022: 30,478 rows / 15,766 establishments). **This is not UNVERIFIED — the fix was applied and the resulting parse was checked end-to-end** (full row count, 0 date failures, sane date ranges within each year, no truncation). The fix is a two-line textual correction applied to an in-memory copy of the file content before parsing; the original ZIP was not modified.

**Historical `Establishment Status` values (all 23 files combined): only `Pass` (394,157 rows) and `Conditional Pass` (1,469 rows) appear — there is no `Closed` status anywhere in the historical archive.** This is a real structural difference from the current CSV (which has `Closed` and `Temporarily Not Operating` in addition to `Pass`/`Conditional Pass`) and must be accounted for if historical and current data are ever combined for target-label construction — a naive combined target definition would need to handle the fact that `Closed`/`Temporarily Not Operating` inspections simply cannot occur in the pre-2024 historical portion of any merged timeline (which is expected, and not itself an error, but is worth stating explicitly rather than assuming).

Total historical raw (infraction-level) rows across all 23 files, after the 2020/2021/2022 fix: **395,626**.

## 4. Current/historical overlap validation (Nov 10 – Dec 31, 2023)

Comparison used `current.oldEstId` ↔ `historical.Establishment ID` plus inspection date, restricted to the current CSV's earliest ~7 weeks (2023-11-10 to 2023-12-31), which is the only window both sources cover.

- Current-CSV inspections in this window (grouped, non-null `oldEstId`): **2,702**.
- Historical-2023 inspections in this window (grouped): **3,086**.
- **All 2,702 current-side inspections found an exact `(oldEstId, date)` match in the historical file** — i.e., every current inspection in the overlap window that has an `oldEstId` is also present in the historical 2023 export. (The historical file has 384 additional inspections in this window with no current-side match at the same `oldEstId`+date; these were not further investigated and are UNVERIFIED as to cause — e.g., possibly current-CSV rows missing an `oldEstId`, or dated slightly differently between systems.)

Of the 2,702 comparable inspection dates:

| Comparison | Result |
|---|---|
| Exact match (status + infraction count + severity counts all agree) | 2,499 (92.5%) |
| Status mismatch | 138 (5.1%) |
| Infraction-count mismatch | 71 (2.6%) |
| Severity-count mismatch | 67 (2.5%) |
| Establishment-name mismatch (case-insensitive) | 55 (2.0%) |

**The mismatches are strongly one-directional, not random noise:**
- Of 138 status mismatches, **132 are `current = Conditional Pass` vs. `historical = Pass`** for the identical inspection (only 6 go the other way).
- Of 71 infraction-count mismatches, **66 have `current > historical`** (more infractions recorded in the current export than the historical snapshot recorded for the same visit); only 5 go the other way.
- Most of the 55 name mismatches are minor spelling/punctuation/rebrand-string variants of the same business (e.g. `"ALEXANDRO'S TAKE OUT"` vs. `"ALEXANDROS TAKE OUT"`, `"SUBWAY SANDWICHES"` vs. `"SUBWAY"`), not evidence of a wrong join; a small number (e.g. `"AMBASSADOR CLUB"` vs. `"AMBASSADOR SAUNA"`, `"PAZARCIK KEBAB"` vs. `"KEBAB LAND"`) look like genuine rebrands/ownership changes at the same address and are flagged as **plausible inference, not confirmed**.

**Interpretation (plausible inference, not confirmed):** the consistent direction — current data shows *more* infractions and *stricter* status than the historical snapshot for the same physical inspection — is consistent with the live DineSafe system applying post-hoc administrative updates to inspection records (e.g., additional infractions logged after appeal/review, or a status escalation) that occurred **after** the historical yearly export was frozen. It is not consistent with random data corruption, since the direction is overwhelmingly one-sided.

**Conclusion: the two sources can reasonably represent one continuous historical timeline, with 92.5% exact agreement in the overlap window and the remaining disagreements following an explainable, one-directional pattern rather than random noise.** However, this means the current CSV and the historical ZIP are **not two independent, always-agreeing copies of the same truth** — where they disagree, the current CSV appears to be the more "final"/updated version. Any future merge should treat the current CSV as authoritative for the Nov–Dec 2023 overlap window rather than treating the two sources as equally reliable.

## 5. `oldEstId` → `estId` identity analysis

All 804 ambiguous `oldEstId` values (each mapping to exactly 2 distinct `estId` values in every case checked) were analyzed using normalized address matching (case/punctuation/postal-code-tolerant) and a ~100m latitude/longitude tolerance, after discovering that a naive exact-string address comparison was itself producing false "different address" results due to formatting noise (e.g. `"2500 Sheppard Ave E"` vs. `"2500 SHEPPARD AVE E"` — same address, different case only).

**Findings, with confidence level stated for each:**

- **SUPPORTED (100% of cases, 804/804):** every ambiguous `oldEstId` case has both `estId`s at the *same physical premises* (identical address once normalized, or within ~100m) — there is no case of a legacy ID being reused for a genuinely different physical location.
- **SUPPORTED (759/804, 94.4%):** the two `estId`s also share the same establishment name (normalized) — i.e., it looks like the same business, at the same address, simply recorded under two different modern `estId`s.
- **SUPPORTED (801/804, 99.6%):** the two `estId`s' inspection date ranges **overlap in time** rather than being sequential — i.e., both IDs have inspections recorded as active in the *same period*, not one ID's history ending before the other begins. This is the opposite of what a clean "business closed, re-registered under a new ID" pattern would look like (which would show non-overlapping, sequential date ranges — only 3 of 804 cases show that pattern).
- **PLAUSIBLE INFERENCE (45/804, 5.6%):** a normalized name difference alongside the same address (e.g. `"AMEY'S"` vs. `"KO FRUIT MARKET"` at the same address) — these are more consistent with an ownership/rebrand change, though this cannot be confirmed from the data alone (no explicit "closed"/"reopened" flag exists to verify it).
- **UNRESOLVED:** the dominant pattern — same premises, same name, concurrent (overlapping) `estId` date ranges for 94% of cases — is **not** explained by ownership change (no evidence of sequential succession) and looks more consistent with a **duplicate administrative record** (e.g., two `Account`-style records created for the same establishment, possibly triggered by an address-formatting mismatch during an internal entity-resolution step) than with two genuinely distinct real-world businesses. This explanation is plausible given the evidence but was not independently confirmed (e.g., no system log or documentation was available to verify *why* two IDs exist), so it is labeled **plausible inference**, not certain.

**Materiality:** this issue affects 1,608 of 18,898 `estId` values (8.5%) and 7,615 of 115,899 raw rows (6.6%) — a modest but non-trivial share of the dataset. Of the affected `estId`s, 164 have only a single inspection under that `estId` — for these, the ambiguity means a chunk of their "true" longitudinal history may be sitting under the other `estId` sharing the same `oldEstId`, invisible to a per-`estId` history feature.

**Decision input for modelling (not a decision made here):** given that the dominant pattern (94%) looks like a duplicate-record artifact rather than a real ownership change, the conservative "keep `estId` as canonical entity" approach recommended in the literature review is **defensible as a first-pass choice** (it will not silently merge two genuinely different businesses), but it likely **under-counts and fragments** the true longitudinal history for roughly 8% of establishments. This should be documented as an explicit, acknowledged limitation of any first modelling version, rather than silently ignored — but implementing a merge rule is out of scope for this reconstruction phase per instructions.

## 6. Snapshot / data versioning

| File | Local modification time | Notes |
|---|---|---|
| `Dinesafe.csv` | 2026-09-09 20:50:45 | |
| `Dinesafe Historical Data.zip` | 2026-09-09 22:52:00 | |
| `DineSafe_Literature_Review_IEEE.docx` | 2026-09-09 22:43:54 | |

- Current CSV `inspectionDate` range: **2023-11-10 to 2026-09-08**. Today's audit date is 2026-09-09, one day after the file's latest inspection date — consistent with a live, rolling export rather than a fixed archival snapshot.
- The file's local modification timestamp (2026-09-09 20:50) predates this session's later files, consistent with it having been downloaded once and not altered since.
- **UNVERIFIED:** no official Toronto Open Data version/release identifier is present in the file itself (no metadata header, no accompanying data dictionary or version file was found locally). The exact CKAN dataset revision this file corresponds to cannot be confirmed without querying the API, which was not done here per the standing instruction not to query the API without local documentation to scope the request.
- **The Closed-count discrepancy (500 raw-row / 80 true-inspection vs. the literature review's cited 64) remains only partially resolved.** Section 1 shows the correct comparison is 80 (inspection-level) vs. 64 (literature review), not 500 vs. 64 as it first appeared. The remaining 80-vs-64 gap (16 additional Closed inspections) is consistent with — but not proven to be — organic growth in a live rolling export between the literature review's audit and this one. No timestamped snapshot of the file used for the original literature-review audit was available to confirm this directly, so it is recorded here as an **unresolved snapshot difference**, per instructions, rather than assumed.

---

## Answers to the eight closing questions

**1. TRUE current inspection-level outcome distribution:**
Pass 72,788 (93.950%), Conditional Pass 4,606 (5.945%), Closed 80 (0.103%), Temporarily Not Operating 1 (0.001%), out of 77,475 total inspections across 18,898 establishments. Non-Pass (Conditional Pass + Closed) = 4,686 (6.048%).

**2. Duplicate findings:**
170 inspection groups (36 establishments, 720 raw rows, 0.62% of all rows) are wholesale-duplicated — each inspection recorded exactly twice, differing only in `_id`/`unique_id`/address-unit-formatting. Classified as **formatting duplication**, not exact duplication and not genuinely different inspections. Not yet deduplicated; recommendation given but not implemented.

**3. Historical-file findings:**
All 23 files (2001–2023) now parse cleanly. 2020/2021/2022 had a shared, fully-diagnosed corruption (duplicated leading quote in the header + one extra trailing quote on the last row) that is reliably fixable with a two-line textual correction; verified end-to-end after the fix. 2023 requires Latin-1 decoding and uses `MM/DD/YYYY` dates, unlike all other years (`YYYY-MM-DD`). Historical `Establishment Status` only ever contains `Pass`/`Conditional Pass` — never `Closed` — across all 23 years.

**4. Overlap validation result:**
2,702 comparable inspections in the Nov–Dec 2023 overlap window; 92.5% exact agreement. Remaining disagreements are one-directional (current data shows more infractions / stricter status than the historical snapshot for the same visit), consistent with post-hoc record updates in the live system rather than random error. The two sources can reasonably represent one continuous timeline, but the current CSV should be treated as authoritative where they disagree.

**5. `oldEstId` identity findings:**
All 804 ambiguous cases are at the same physical premises (100%); 94% also share the same name and have *overlapping*, not sequential, inspection date ranges — inconsistent with simple ownership succession and more consistent with a duplicate administrative record (plausible inference, not confirmed). Affects 8.5% of establishments and 6.6% of raw rows.

**6. Is historical data safe to integrate yet?**
Not yet, but the remaining blockers are now well-defined and mostly resolved at the diagnostic level: (a) apply the verified 2020/2021/2022 corruption fix, (b) normalize date formats per file, (c) decide and document how to handle the `Closed`/`Temporarily Not Operating` statuses that don't exist pre-2024, (d) decide how to treat the current-CSV-vs-historical disagreement in the overlap window (recommend: current CSV wins on conflict), and (e) decide how to handle the 804 ambiguous `oldEstId` cases before using `oldEstId` as a join/entity key for merged history. None of these are open research questions anymore — they are now implementation decisions.

**7. Remaining blockers before feature engineering:**
- Decide and document a deduplication rule for the 170 formatting-duplicated inspection groups.
- Decide whether/how to consolidate the 804 ambiguous `oldEstId`→multiple-`estId` cases (or explicitly accept the fragmentation as a documented limitation).
- Decide the precedence rule for current-vs-historical conflicts before any merge.
- Confirm whether the 384 historical-side-only inspections in the overlap window (with no current-side match) matter for the intended modelling window (they precede the earliest current-only establishments' full history and may simply be out of scope).
- No official data dictionary/version identifier exists locally; establishing one API-based version check is recommended before finalizing any "as of" date for the modelling snapshot, but was not performed here.

**8. The single most important next step:**
Decide and document the entity-key and deduplication policy (which establishment ID to key on, how to treat the 804 ambiguous `oldEstId` cases, and how to deduplicate the 170 formatting-duplicated inspections) — every downstream feature (prior inspection count, non-pass rate, time since last inspection) depends directly on getting the entity and inspection grain right first.
