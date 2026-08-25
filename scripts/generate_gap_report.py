#!/usr/bin/env python3
"""Generate an audiobook series gap report from Audiobookshelf.

Wave 4 / T5 of fix-audiobookshelf-series-metadata. Paginates
GET /api/libraries/{id}/series, extracts each book's sequence for the current
series from media.metadata.seriesName (comma-separated for multi-series
books), infers the expected integer range [min_seq, max_seq], and marks every
integer in that range with no owned book as MISSING.

Missing entries are reported as series name + book number ONLY — titles are
never fabricated, since we have no data source for what a missing book is.

Usage:
    python3 scripts/generate_gap_report.py
"""

import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ABS_BASE = "http://10.40.40.25:13378"
LIBRARY_ID = "a31cede5-ac09-4dbc-9b49-4ed9de00ab7a"
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
REPORT_PATH = Path("/home/mwdavisii/Documents/audiobook_gap_report.md")
PAGE_SIZE = 100

SEQ_RE = re.compile(r"#(\d+(?:\.\d+)?)$")


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


def api_get(path: str, api_key: str, params: dict | None = None) -> dict:
    """GET a JSON endpoint with bearer auth; raise on HTTP/network errors."""
    url = ABS_BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {api_key}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"HTTP {exc.code} from {url}: {exc.read()[:200]!r}")
    except urllib.error.URLError as exc:
        raise SystemExit(f"Request to {url} failed: {exc}")


def fetch_all_series(api_key: str) -> list[dict]:
    """Paginate GET /api/libraries/{id}/series until all pages are read."""
    series: list[dict] = []
    page = 0
    total = None
    while True:
        payload = api_get(
            f"/api/libraries/{LIBRARY_ID}/series",
            api_key,
            {"limit": PAGE_SIZE, "page": page},
        )
        results = payload.get("results", [])
        if total is None:
            total = payload.get("total")
        series.extend(results)
        page += 1
        if not results or (total is not None and len(series) >= total):
            break
    return series


def parse_sequence(series_name: str, series_name_field: str | None):
    """Extract this book's sequence within `series_name` from seriesName.

    seriesName is a comma-separated string like "The Stormlight Archive #2,
    The Cosmere". Find the entry starting with the series name, then pull the
    trailing #N (int or float). Returns None when no entry parses.
    """
    if not series_name_field:
        return None
    for entry in series_name_field.split(","):
        entry = entry.strip()
        if not entry.startswith(series_name):
            continue
        match = SEQ_RE.search(entry)
        if match:
            return float(match.group(1))
    return None


def seq_label(seq: float) -> str:
    """Render a sequence as an int when whole (2.0 -> '2')."""
    return str(int(seq)) if seq == int(seq) else str(seq)


def analyze_series(series: dict) -> dict:
    """Build owned/missing/unparsable lists for one series."""
    name = series["name"]
    owned = []
    unparsable = []
    for book in series.get("books", []):
        metadata = book.get("media", {}).get("metadata", {})
        title = metadata.get("title", "(untitled)")
        asin = metadata.get("asin")
        seq = parse_sequence(name, metadata.get("seriesName"))
        if seq is None:
            unparsable.append({"title": title, "asin": asin})
        else:
            owned.append({"seq": seq, "title": title, "asin": asin})

    owned.sort(key=lambda b: b["seq"])
    owned_ints = {int(b["seq"]) for b in owned}
    missing = []
    if owned_ints:
        for n in range(min(owned_ints), max(owned_ints) + 1):
            if n not in owned_ints:
                missing.append(n)

    return {
        "name": name,
        "owned": owned,
        "missing": missing,
        "unparsable": unparsable,
    }


def render_report(analyses: list[dict]) -> str:
    """Render the full Markdown gap report."""
    total_series = len(analyses)
    total_owned = sum(len(a["owned"]) + len(a["unparsable"]) for a in analyses)
    total_missing = sum(len(a["missing"]) for a in analyses)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    lines = [
        "# Audiobook Series Gap Report",
        "",
        f"_Generated {timestamp} from Audiobookshelf at {ABS_BASE}_",
        "",
        "## Summary",
        "",
        f"- **Total series:** {total_series}",
        f"- **Total owned books:** {total_owned}",
        f"- **Total missing books:** {total_missing}",
        "",
    ]

    for analysis in sorted(analyses, key=lambda a: a["name"].lower()):
        lines.append(f"## {analysis['name']}")
        lines.append("")
        lines.append(
            f"Owned: {len(analysis['owned']) + len(analysis['unparsable'])}"
            f" — Missing: {len(analysis['missing'])}"
        )
        lines.append("")

        lines.append("### Owned")
        lines.append("")
        if analysis["owned"] or analysis["unparsable"]:
            for book in analysis["owned"]:
                asin = book["asin"] or "no-ASIN"
                lines.append(
                    f"- {seq_label(book['seq'])} — {book['title']} — {asin}"
                )
            for book in analysis["unparsable"]:
                asin = book["asin"] or "no-ASIN"
                lines.append(
                    f"- UNPARSABLE — {book['title']} — {asin}"
                )
        else:
            lines.append("- _(none)_")
        lines.append("")

        if analysis["missing"]:
            lines.append("### Missing")
            lines.append("")
            for seq in analysis["missing"]:
                # Series name + number only — never fabricate a title.
                lines.append(f"- {analysis['name']} #{seq} — MISSING")
            lines.append("")

    return "\n".join(lines) + "\n"


def main() -> None:
    api_key = load_api_key(ENV_PATH)
    series = fetch_all_series(api_key)
    analyses = [analyze_series(s) for s in series]
    report = render_report(analyses)
    REPORT_PATH.write_text(report, encoding="utf-8")

    total_missing = sum(len(a["missing"]) for a in analyses)
    print(f"Wrote {REPORT_PATH}")
    print(f"series={len(analyses)} missing={total_missing}")
    top = sorted(analyses, key=lambda a: len(a["missing"]), reverse=True)[:5]
    print("top_gaps=" + json.dumps(
        [{"name": a["name"], "missing": len(a["missing"])} for a in top]
    ))


if __name__ == "__main__":
    sys.exit(main())
