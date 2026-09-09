# Temporal Distribution Check

Short analysis, done in `notebooks/02_temporal_distribution_check.ipynb`, to understand the gap between historical (0.26% Non-Pass) and current (6.05% Non-Pass) targets in `prediction_events_v1.csv` before deciding how to define the modelling target period. This is analysis only, no output datasets were changed.

## 1. Non-Pass rate over time

Non-Pass rate stays under 1% for every single year from 2001 to 2022, ticks up slightly in 2023 (0.9%, a mix of historical Jan-Oct and current Nov-Dec), then jumps to 5.3% in 2024, 6.0% in 2025, 7.0% in 2026. This is a sharp break around 2023-2024, not a gradual drift.

By broad period:

| Period | Rows | Establishments | Non-Pass rate |
|---|---|---|---|
| 2001-2019 | 135,486 | 7,281 | 0.24% |
| 2020-2023 | 40,792 | 10,530 | 0.62% |
| 2024-2026 | 67,371 | 16,704 | 6.09% |

The low rate is consistent across the whole historical archive, not concentrated in a few odd years.

## 2. Historical vs current targets

| Source | Rows | Establishments | Non-Pass rate | Date range |
|---|---|---|---|---|
| historical | 173,883 | 10,412 | 0.26% | 2001-01-09 to 2023-12-22 |
| current | 69,766 | 16,779 | 6.05% | 2023-11-10 to 2026-09-08 |

Historical files also never record a "Closed" status, only Pass and Conditional Pass, which is a further reason the two target definitions aren't fully comparable.

## 3. How much history do current establishments have

Of the 18,898 establishments in the current CSV:

- 7,709 have no linked historical inspection
- 11,189 have 1 or more
- 9,517 have 3 or more
- 7,871 have 5 or more

For establishments with any historical link, the gap between their first historical inspection and first current-period inspection is often large (median about 7.5 years), so the archive reaches well beyond what current data alone covers.

Restricting to current-period prediction targets specifically: 73.8% of them get at least one extra prior inspection from the historical link, with a median of 12 extra prior inspections where a link exists. About 30% of current-period establishments (5,590 of 16,779) get no historical boost at all, either because they're new or their `oldEstId` link doesn't resolve.

## 4. Is the historical archive useful for modern prediction?

Yes, as history. It measurably deepens the prior-inspection record for most current establishments. It's the target label that's the problem, not the history itself.

## 5. Design A vs Design B

**Design A** (full 2001-2026 span as targets): more rows and longer histories for older establishments, but the target means something different depending on the period, and the historical portion has no Closed status at all. Pooling these risks a model that partly just learns "old record vs new record."

**Design B** (historical archive for history features only, targets restricted to the current period): every target comes from one consistent recording system, and establishments still benefit from historical depth as features. Fewer target rows (69,766 vs 243,649), and about 30% of current establishments won't get a historical boost, but that's a known, already-documented limitation rather than a new problem.

**Recommendation: Design B.** The break between historical and current Non-Pass rates is sharp, not gradual, and lines up exactly with the current CSV's start date rather than with any real-world trend. Treating both periods as one target pool would make the target itself period-dependent.

## 6. Unresolved issue

Design B needs an explicit cutoff date for what counts as a "current period" target. The natural choice is the current CSV's own start date (2023-11-10), consistent with the current-vs-historical precedence rule already documented in `LONGITUDINAL_DATASET.md`, but this should be decided and applied explicitly in the next step rather than assumed here.
