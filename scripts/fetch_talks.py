#!/usr/bin/env python3
"""
Fetch upcoming talks from the SapMachine wiki Presentations page.
Writes data/talks.json  (list of upcoming talks sorted by date ascending).

Each entry:
  { "date": "2026-09-08", "date_display": "Sep 8 - 9, 2026",
    "conference": "JavaZone", "conf_url": "https://...",
    "location": "Oslo, Norway", "link_text": "Schedule", "link_url": "https://..." }
"""

import json
import re
from datetime import date
from pathlib import Path

import requests

ROOT     = Path(__file__).resolve().parent.parent
OUT      = ROOT / "data" / "talks.json"
WIKI_RAW = "https://raw.githubusercontent.com/wiki/SAP/SapMachine/Presentations.md"

MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,  "may": 5,  "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def parse_date(cell: str) -> date | None:
    """Parse 'Sep 8 - 9, 2026' or 'Feb 2, 2026' → date of first day."""
    m = re.match(r"([A-Za-z]+)\s+(\d+).*?(\d{4})", cell.strip())
    if not m:
        return None
    month = MONTH_MAP.get(m.group(1).lower()[:3])
    if not month:
        return None
    try:
        return date(int(m.group(3)), month, int(m.group(2)))
    except ValueError:
        return None


def first_md_link(text: str) -> tuple[str, str]:
    """Return (label, url) of the first markdown link in text, or ('', '')."""
    m = re.search(r"\[([^\]]+)\]\(([^)]+)\)", text)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return "", ""


def parse_tables(md: str) -> list[dict]:
    """
    Parse all GFM tables whose header contains 'Date' and 'Event'.
    Returns rows as dicts with keys: date_raw, conf_raw, loc_raw, link_raw.
    """
    rows = []
    lines = md.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        # Detect header row
        if re.search(r"Date\s*\|.*Event", line):
            # Next line must be a separator (only dashes, pipes, spaces)
            if i + 1 < len(lines) and re.match(r"^[-| ]+$", lines[i + 1]):
                i += 2  # skip header + separator
                while i < len(lines) and lines[i].strip() and "|" in lines[i]:
                    cols = [c.strip() for c in lines[i].split("|")]
                    # Strip \xa0 (non-breaking space)
                    cols = [c.replace("\xa0", " ").strip() for c in cols]
                    if len(cols) >= 2:
                        rows.append({
                            "date_raw": cols[0],
                            "conf_raw": cols[1] if len(cols) > 1 else "",
                            "loc_raw":  cols[2] if len(cols) > 2 else "",
                            "link_raw": cols[3] if len(cols) > 3 else "",
                        })
                    i += 1
                continue
        i += 1
    return rows


def fetch() -> list[dict]:
    resp = requests.get(WIKI_RAW, timeout=15)
    resp.raise_for_status()
    md = resp.text

    today = date.today()
    upcoming = []
    seen: set[tuple[str, str]] = set()

    for row in parse_tables(md):
        d = parse_date(row["date_raw"])
        if d is None or d < today:
            continue

        conf_name, conf_url = first_md_link(row["conf_raw"])
        if not conf_name:
            conf_name = row["conf_raw"]

        link_label, link_url = first_md_link(row["link_raw"])

        key = (d.isoformat(), conf_name)
        if key in seen:
            continue
        seen.add(key)

        upcoming.append({
            "date":         d.isoformat(),
            "date_display": row["date_raw"],
            "conference":   conf_name,
            "conf_url":     conf_url,
            "location":     row["loc_raw"],
            "link_text":    link_label,
            "link_url":     link_url,
        })

    upcoming.sort(key=lambda t: t["date"])
    return upcoming


def main() -> None:
    talks = fetch()
    OUT.write_text(json.dumps({"talks": talks}, indent=2) + "\n")
    print(f"Wrote {len(talks)} upcoming talks to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
