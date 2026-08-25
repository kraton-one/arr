#!/usr/bin/env python3
"""Merge missing series tags into Audiobookshelf books (idempotent).

Wave 2 / T3 of fix-audiobookshelf-series-metadata. For each entry in
SERIES_FIXES, look up the library item (ASIN first, title fallback), read its
current media.metadata.series array, append any mapping series whose name is
not already present, then PATCH /api/items/{id}/media with the FULL merged
array.

Why the full array: the PATCH endpoint REPLACES the series array wholesale;
sending only the new entries would silently delete every existing series. So
we always read the current array from GET /api/items/{id} and round-trip it.

Usage:
    python3 scripts/fix_series_metadata.py --dry-run   # show planned changes
    python3 scripts/fix_series_metadata.py             # apply changes
"""

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ABS_BASE = "http://10.40.40.25:13378"
LIBRARY_ID = "a31cede5-ac09-4dbc-9b49-4ed9de00ab7a"
LOG_PATH = Path("/tmp/series_fixes.json")
PAGE_SIZE = 500

# Mapping keyed by canonical ASIN. Lookup is ASIN-first, then falls back to
# substring matching on the item title (some ABS items have asin=null).
# Each entry lists series to ADD; existing series are always preserved.
SERIES_FIXES = {
    # The Lathe of Heaven (confirmed in library, asin matches)
    "B01M1N5CQ2": {
        "title_hint": "The Lathe of Heaven",
        "add": [{"name": "The Hainish Cycle", "sequence": "6"}],
    },
    # The Uplift War (in library as "99 - The Uplift War - David Brin - 1987",
    # asin is null — relies on title_hint fallback)
    "B002V8PNVE": {
        "title_hint": "The Uplift War",
        "add": [{"name": "Uplift Saga", "sequence": "3"}],
    },
    # Start with Why 15th Anniversary Edition (not currently in library —
    # script must log "book not found" and continue without error)
    "B07BD3V8BX": {
        "title_hint": "Start with Why",
        "add": [{"name": "Start with Why Series", "sequence": "1"}],
    },
}


def load_api_key(env_path: Path) -> str:
    """Read AUDIOBOOKSHELF_API_KEY from a .env file (KEY=VALUE lines)."""
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        if key.strip() == "AUDIOBOOKSHELF_API_KEY":
            return value.strip().strip('"').strip("'")
    raise SystemExit(f"AUDIOBOOKSHELF_API_KEY not found in {env_path}")


class ApiError(Exception):
    """HTTP error raised when ABS returns a non-2xx response."""


def make_client(api_key: str) -> urllib.request.OpenerDirector:
    """Build an urllib opener that always sends the Bearer auth header."""
    opener = urllib.request.build_opener()
    opener.addheaders = [("Authorization", f"Bearer {api_key}")]
    return opener


def http_json(opener: urllib.request.OpenerDirector, method: str, url: str,
              body: dict | None = None, timeout: int = 30):
    """Issue a JSON request and return (status_code, parsed_body).

    Raises ApiError on non-2xx so callers can catch one exception type. The
    parsed body is None when the response has no content (e.g., 200 with
    empty body from some PATCH calls)."""
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers,
                                 method=method)
    try:
        with opener.open(req, timeout=timeout) as resp:
            raw = resp.read()
            parsed = json.loads(raw) if raw else None
            return resp.status, parsed
    except urllib.error.HTTPError as e:
        body_text = e.read().decode(errors="replace")
        raise ApiError(f"{method} {url} -> {e.code}: {body_text[:300]}") from e


def iter_library_items(opener: urllib.request.OpenerDirector):
    """Yield every library item, paginating PAGE_SIZE at a time."""
    page = 0
    while True:
        params = urllib.parse.urlencode({"limit": PAGE_SIZE, "page": page})
        url = f"{ABS_BASE}/api/libraries/{LIBRARY_ID}/items?{params}"
        _, data = http_json(opener, "GET", url)
        results = data.get("results") or []
        if not results:
            return
        yield from results
        total = data.get("total", 0)
        page += 1
        if page * PAGE_SIZE >= total:
            return


def extract_metadata(item: dict) -> dict:
    """List endpoint may nest metadata under media.metadata or expose it flat."""
    media = item.get("media") or {}
    return media.get("metadata") or item.get("metadata") or {}


def find_item(opener: urllib.request.OpenerDirector, asin: str,
              title_hint: str):
    """Locate a library item by ASIN, falling back to title substring match."""
    title_hint_lower = title_hint.lower()
    title_fallback = None
    for item in iter_library_items(opener):
        meta = extract_metadata(item)
        item_asin = meta.get("asin") or item.get("asin")
        if item_asin and item_asin == asin:
            return item
        title = (meta.get("title") or "").lower()
        if title_fallback is None and title_hint_lower in title:
            title_fallback = item
    return title_fallback


def merge_series(existing: list, additions: list) -> tuple[list, bool]:
    """Append additions whose name is not already in existing.

    Every existing series object (including its id and sequence) is preserved
    verbatim. Returns (merged_array, changed?). Because PATCH replaces the
    whole array, the merged array — not just the additions — is what we send.
    """
    merged = list(existing or [])
    existing_names = {s.get("name") for s in merged}
    changed = False
    for new in additions:
        if new["name"] not in existing_names:
            merged.append({"name": new["name"], "sequence": new["sequence"]})
            existing_names.add(new["name"])
            changed = True
    return merged, changed


def process_book(opener: urllib.request.OpenerDirector, asin: str,
                 spec: dict, dry_run: bool, log_entries: list) -> None:
    item = find_item(opener, asin, spec["title_hint"])
    if item is None:
        msg = f"book not found: ASIN={asin} title_hint={spec['title_hint']!r}"
        print(f"SKIP  {msg}")
        log_entries.append({"asin": asin, "status": "not_found"})
        return

    item_id = item["id"]
    _, detail = http_json(opener, "GET", f"{ABS_BASE}/api/items/{item_id}")
    meta = (detail.get("media") or {}).get("metadata") or {}
    title = meta.get("title", "<untitled>")
    current_series = meta.get("series") or []

    merged, changed = merge_series(current_series, spec["add"])

    print(f"ITEM  {title} (id={item_id}, asin={meta.get('asin')!r})")
    print(f"  current series: {json.dumps(current_series)}")
    print(f"  merged  series: {json.dumps(merged)}")

    if not changed:
        print("  no changes needed (already up to date)")
        log_entries.append({
            "asin": asin, "item_id": item_id, "title": title,
            "status": "no_change",
        })
        return

    if dry_run:
        print("  [dry-run] would PATCH /api/items/"
              f"{item_id}/media with metadata.series above")
        log_entries.append({
            "asin": asin, "item_id": item_id, "title": title,
            "status": "dry_run", "merged_series": merged,
        })
        return

    status, body = http_json(opener, "PATCH",
                             f"{ABS_BASE}/api/items/{item_id}/media",
                             body={"metadata": {"series": merged}})
    body_preview = json.dumps(body)[:500] if body is not None else ""
    print(f"  PATCH status={status} body={body_preview}")
    log_entries.append({
        "asin": asin, "item_id": item_id, "title": title,
        "status": "patched", "http_status": status,
        "response_body": body_preview,
    })


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run", action="store_true",
        help="print planned series merges without PATCHing",
    )
    parser.add_argument(
        "--env-file", default=str(Path(__file__).resolve().parent.parent / ".env"),
        help="path to .env containing AUDIOBOOKSHELF_API_KEY",
    )
    args = parser.parse_args()

    api_key = load_api_key(Path(args.env_file))
    opener = make_client(api_key)

    log_entries: list = []
    for asin, spec in SERIES_FIXES.items():
        try:
            process_book(opener, asin, spec, args.dry_run, log_entries)
        except (ApiError, urllib.error.URLError) as e:
            print(f"ERROR processing ASIN={asin}: {e}")
            log_entries.append({"asin": asin, "status": "error",
                                "error": str(e)})

    LOG_PATH.write_text(json.dumps(log_entries, indent=2))
    print(f"\nWrote log to {LOG_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
