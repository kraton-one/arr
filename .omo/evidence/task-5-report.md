# Task 5 Evidence — Audiobook Gap Report

## Artifacts

- **Script:** `/home/mwdavisii/code/arr/scripts/generate_gap_report.py`
- **Report:** `/home/mwdavisii/Documents/audiobook_gap_report.md`

## Counts (verified against API)

- **total_series_count:** 74 — matches `total: 74` from
  `GET /api/libraries/a31cede5-ac09-4dbc-9b49-4ed9de00ab7a/series` (single page,
  limit=100)
- **total_missing_count:** 10 — cross-checked by an independent inline
  recalculation against the raw API response (same sequence-parsing rule),
  also 10
- **total_owned_books:** 146 (parsed + unparsable)

## Top 5 series with most gaps

| Series | Missing |
|--------|---------|
| The Dresden Files | 9 |
| Magic 2.0 | 1 |
| Who Moved My Cheese? | 0 |
| Unfu*k Yourself | 0 |
| Raven's Shadow | 0 |

(Only 2 of 74 series have any gaps; the remaining top-5 slots are 0-gap
series shown for completeness.)

## No fabricated titles

Confirmed: MISSING entries are emitted strictly as
`- <Series Name> #N — MISSING` (series name + book number only). A regex
check (`^- .+ #\d+ — MISSING$`) over the generated report found
**0 malformed MISSING lines** — no missing entry carries a title, and the
script contains no hardcoded book lists.

## Notes / gotchas

- Duplicate library items surface as duplicate owned rows (A Song of Ice and
  Fire shows *A Storm of Swords* twice, same ASIN B0036NQ9Z8) — these are two
  real ABS items, not report duplication. The gap math dedupes by integer
  sequence via a set, so duplicates do not affect missing counts.
- Fractional sequences (12.5 *Side Jobs*, 14.5 *Shadowed Souls* in Dresden)
  parse as floats and are excluded from the integer gap range while still
  listed as owned — no false MISSING entries between 12 and 13.
- 2 of 146 books have UNPARSABLE sequences (seriesName present but no `#N`
  suffix, or null). They are listed in Owned with an `UNPARSABLE` marker and
  excluded from range calculation.
- Pagination: library fits in one page (74 < limit=100), but the script loops
  on `len(results) < total` so it scales if the library grows.
