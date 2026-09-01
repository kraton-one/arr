# Task 5 Evidence — Audiobook Gap Report

## Artifacts

- **Script:** `/home/mwdavisii/code/arr/scripts/generate_gap_report.py`
- **Report:** `/home/mwdavisii/Documents/audiobook_gap_report.md`

## Counts (verified against API) — **UPDATED 2026-08-25 after T4b Twelve Months fix**

- **total_series_count:** 74 — unchanged
- **total_missing_count:** **5** (was 10 before task 4b)
- **total_owned_books:** 146 — unchanged

Note on the count drop: when the script wrote this report the first time,
Twelve Months was mis-sequenced at Dresden Files #23, which made the gap
range [1, 23] and flagged 9 Dresden entries (#2–#5 + #18–#22). After task 4b
fixed the sequence to #18, the range narrowed to [1, 18] and MISSING shrank
to #2–#5 (4 entries). #19–#22 fall outside [min, max] of owned integers so
they no longer surface as MISSING — this is by design in the script's
range-based gap detection. The remaining gap is 1 entry in Magic 2.0 (#4),
giving 4 + 1 = 5 total.

## Current actual MISSING lines (regenerated report)

```
- Magic 2.0 #4 — MISSING
- The Dresden Files #2 — MISSING
- The Dresden Files #3 — MISSING
- The Dresden Files #4 — MISSING
- The Dresden Files #5 — MISSING
```

## Top 5 series with most gaps (current)

| Series | Missing |
|--------|---------|
| The Dresden Files | 4 |
| Magic 2.0 | 1 |
| Who Moved My Cheese? | 0 |
| Unfu*k Yourself | 0 |
| Raven's Shadow | 0 |

(Only 2 of 74 series have any gaps.)

## No fabricated titles

Confirmed: MISSING entries are emitted strictly as
`- <Series Name> #N — MISSING` (series name + book number only). The
script contains no hardcoded book lists and no title invention.

## Notes / gotchas

- **Range-based gap detection has a known edge case:** if a series has
  future/unreleased books past the max owned sequence (e.g., Dresden
  #19–#22, none yet published), they are NOT reported as missing. This
  matches user intent (don't list books that don't exist), but it means the
  report can undercount "all planned books in a series."
- The Cosmere sequence metadata for Stormlight Archive titles is UNPARSABLE
  on the series endpoint (no `#N` in seriesName for them), so the Cosmere
  bucket does not produce MISSING entries for the Stormlight novels. This
  is fine — the Stormlight Archive series section correctly shows 6 owned
  and 0 missing.
- Duplicate library items surface as duplicate owned rows (A Song of Ice
  and Fire shows *A Storm of Swords* twice). The gap math dedupes by int
  seq via a set, so duplicates do not affect missing counts.
- Pagination: library fits in one page (74 < limit=100).
