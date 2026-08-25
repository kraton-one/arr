# Learnings — fix-audiobookshelf-series-metadata

Conventions, patterns, and successful approaches discovered during work on this plan.

_Auto-scaffolded by /start-work. Append new entries below - never overwrite._

---

## Task 3 (2026-08-25) — ASIN / series lookup gotchas

- Library list endpoint `GET /api/libraries/{id}/items?limit=500&page=N` returns
  `results[]` with `media.metadata.{title,asin,seriesName,...}`. `asin` may be
  `null` on BOTH list and item responses for items matched only via folder scans
  (e.g., "99 - The Uplift War - David Brin - 1987" has `asin: null`). Always
  fall back to a title substring match; never rely on ASIN alone.
- ASIN appears at `media.metadata.asin` in the list response and at
  `media.metadata.asin` on the item detail response — same shape both ways.
- `media.metadata.series` on an item detail is an array of
  `{id, name, sequence}` objects. `id` is a per-item-series membership UUID
  assigned by ABS — do NOT set it when appending new entries; omit `id` and
  ABS assigns one on PATCH.
- List response also exposes `seriesName` as a pre-formatted string like
  `"Uplift Saga #2"` — read-only convenience; do not parse it for merging.
- PATCH `/api/items/{id}/media` with `{"metadata":{"series":[...]}}` REPLACES
  the entire series array. Round-trip every existing object (including `id`)
  to avoid silent deletion.
- Library search endpoint is `GET /api/libraries/{id}/search?q=...`
  (NOT `/api/search/library` — that 404s).

## Task 5 (2026-08-25) — Gap report generation gotchas

- `GET /api/libraries/{id}/series?limit=100&page=N` returns
  `{results, total, limit, page}`; `results[].books[]` are full library items
  carrying `media.metadata.{title,asin,seriesName}`. Whole library (74
  series) fit in one page at limit=100; loop until `len(collected) >= total`.
- Fractional sequences exist in the wild (`The Dresden Files #12.5`,
  `#14.5`). Parse with `#(\d+(?:\.\d+)?)$` as float, but compute gaps over
  INTEGER sequences only — otherwise 12→13 would false-positive as missing.
- Duplicate ABS items (same ASIN, two library items) show up twice in
  `books[]`. Dedupe sequences with a set before computing the missing range.
- Some books in a series have `seriesName` with no `#N` for that series (or
  null) — report them as UNPARSABLE, don't drop them silently.
- MISSING entries must be series-name + number only; never invent titles.
