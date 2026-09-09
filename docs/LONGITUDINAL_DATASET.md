# Longitudinal Inspection Dataset

This describes what `build_longitudinal_dataset.py` produces. No features, no target column, no modelling here yet.

## What one row represents

One row is one inspection: a distinct `(estId, inspectionDate)` pair. Infraction-level detail from the raw files is collapsed into counts (total infractions, and counts by severity), so the grain matches an actual inspection visit rather than an individual violation.

## Duplicate inspections

The audit in `DATA_RECONSTRUCTION.md` found ~170 inspections in `Dinesafe.csv` that were recorded twice, with the two copies differing only in `_id`, `unique_id`, and address formatting (e.g. "Unit-102D" vs "102D"). These are dropped before building the inspection table, by removing rows that match on establishment, date, and every field that actually describes the infraction (`typeDesc`, `deficiencyDesc`, `severity`, `OutcomeDate`, `OutcomeDesc`, `amountFined`). This removed 360 raw rows. After dedup, the inspection count and the Pass/Conditional Pass/Closed/TNO counts match the audit exactly (77,475 inspections; 72,788 / 4,606 / 80 / 1).

## Establishment key

`estId` is used as the entity key for now. It is not merged with other `estId`s even when they share an `oldEstId`. The audit found 804 `oldEstId` values that map to more than one `estId`, and in most of those cases it looks like a duplicate record rather than a real ownership change, but we can't tell for sure from the data, so nothing is merged. This is a deliberate conservative choice:

- it avoids wrongly combining two records that might actually be different
- but it means the true history for those ~1,600 affected `estId`s (about 8% of establishments) may be split across two IDs and this dataset won't see all of it

## Connecting current and historical data

`oldEstId` is the bridge to the historical files, which use the old numeric `Establishment ID`. The link only works one way and only where it's unambiguous:

historical `Establishment ID` -> current `oldEstId` -> current `estId`

If an `oldEstId` maps to more than one `estId` (the 804 cases above), or if a historical `Establishment ID` doesn't appear as an `oldEstId` in the current file at all, that historical inspection is left unlinked and dropped from the longitudinal table. No name/address matching was used to try to recover these. Out of 257,676 historical inspections, 187,643 linked to a current `estId` and 70,033 did not.

## Current vs historical precedence

The 2020-2022 historical files needed a small fix before they would parse (a doubled quote at the start of the header line, and one extra quote at the end of the last row - both explained in `DATA_RECONSTRUCTION.md`). This fix is applied to the file content in memory only; the original ZIP is never touched.

The current CSV and the 2023 historical file both cover Nov-Dec 2023. The overlap check in `DATA_RECONSTRUCTION.md` showed the current export usually has the same or more infractions and stricter status for the same inspection, consistent with the current system updating some records after the historical snapshot was taken. So for any `(estId, date)` that exists in both sources, the current version is kept and the historical version is dropped. This isn't a claim that the current data is "correct" - just that it looks like the more complete/updated version where the two disagree. 2,571 historical inspections were dropped for this reason.

## Temporarily Not Operating

There is exactly one "Temporarily Not Operating" inspection in the current data. It is kept in this dataset. It will be excluded from the Pass vs Non-Pass model later since one example isn't enough to say anything useful about it - that decision is not made in this script, just noted here.

## What's in the dataset

Each row has: `estId`, `oldEstId`, establishment name, address, latitude, longitude, inspection date, inspection status, total infraction count, and infraction counts by severity (minor/significant/crucial), plus a `source` column (`current` or `historical`).

Legal/enforcement fields (`OutcomeDate`, `OutcomeDesc`, `amountFined`) are left out on purpose - they mostly get filled in after the fact and shouldn't be used as pre-inspection information later.

## Output files

- `outputs/inspection_level_current.csv` - current data only, 77,475 inspections
- `outputs/inspection_level_longitudinal.csv` - current + linked historical data, 262,547 inspections, 18,898 establishments, 2001-01-03 to 2026-09-08

## Limitations

- The 804 ambiguous `oldEstId` cases get no historical link, and their current-side history is possibly split across two `estId`s. Not resolved.
- 70,033 historical inspections (about 27% of the historical file) have no link into the current data, either because the establishment closed before ~2024 and never got a current `estId`, or because of the ambiguous-ID issue above.
- The 2020-2022 fix is a manual correction based on inspecting the files by hand. It worked cleanly for all three files but hasn't been checked against any external source of truth for those years.
- Historical files never have a "Closed" or "Temporarily Not Operating" status - only Pass and Conditional Pass. This is expected (not a bug) but means the class balance of any future target will look different depending on how much historical data before 2024 is included.
