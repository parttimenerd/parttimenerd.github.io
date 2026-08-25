#!/usr/bin/env python3
"""
Fetch upcoming talks from the SapMachine wiki Presentations page.
Writes data/talks.json  (list of upcoming talks sorted by date ascending).

Each entry:
  { "date": "2026-09-08", "date_display": "Sep 8 - 9, 2026",
    "conference": "JavaZone", "conf_url": "https://...",
    "location": "Oslo, Norway",
    "title": "My Talk Title",
    "co_speaker": "Jane Smith",   # optional
    "link_text": "Schedule", "link_url": "https://..." }

Talk title is taken from the nearest preceding H2/H3 heading or bold paragraph
that acts as a section title (lines like "### Title" or "**Title**\n------").
Co-speaker is parsed from the links column when it contains plain text like
"joint talk with Name" alongside any markdown links.
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


def parse_co_speaker(link_raw: str) -> str:
    """Extract co-speaker from text like 'joint talk with Jake Hillion'."""
    # Remove all markdown links first
    plain = re.sub(r"\[([^\]]+)\]\([^)]+\)", "", link_raw).strip()
    # Strip trailing/leading punctuation left by link removal
    plain = re.sub(r"^[,\s]+|[,\s]+$", "", plain)
    m = re.search(r"(?:joint talk with|w/)\s+(.+)", plain, re.IGNORECASE)
    if m:
        return m.group(1).strip().rstrip(".")
    return ""


def parse_tables(md: str) -> list[dict]:
    """
    Parse all GFM tables whose header contains 'Date' and 'Event'.
    Attach the nearest preceding section title to each table's rows.
    Returns rows as dicts with keys: date_raw, conf_raw, loc_raw, link_raw, title.
    """
    rows = []
    lines = md.splitlines()
    current_title = ""

    i = 0
    while i < len(lines):
        line = lines[i]

        # Track section title: ATX heading (## / ###) or setext underline (-----)
        atx = re.match(r"^#{2,3}\s+(.+)$", line)
        if atx:
            t = atx.group(1).strip()
            # Ignore structural headings like "Non-Java Presentations"
            if not re.search(r"Presentation|Speaker|Schedule|Upcoming|Past", t, re.I):
                current_title = t
            i += 1
            continue

        setext = (i + 1 < len(lines) and re.match(r"^-{3,}$", lines[i + 1].strip()))
        if setext and line.strip() and not re.match(r"^[-|]", line):
            t = line.strip()
            if not re.search(r"Presentation|Speaker|Schedule|Upcoming|Past|Date\s*\|", t, re.I):
                current_title = t
            i += 2
            continue

        # Detect header row
        if re.search(r"Date\s*\|.*Event", line):
            if i + 1 < len(lines) and re.match(r"^[-| ]+$", lines[i + 1]):
                i += 2  # skip header + separator
                while i < len(lines) and lines[i].strip() and "|" in lines[i]:
                    cols = [c.strip() for c in lines[i].split("|")]
                    cols = [c.replace("\xa0", " ").strip() for c in cols]
                    if len(cols) >= 2:
                        rows.append({
                            "date_raw": cols[0],
                            "conf_raw": cols[1] if len(cols) > 1 else "",
                            "loc_raw":  cols[2] if len(cols) > 2 else "",
                            "link_raw": cols[3] if len(cols) > 3 else "",
                            "title":    current_title,
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
        co_speaker = parse_co_speaker(row["link_raw"])

        key = (d.isoformat(), conf_name)
        if key in seen:
            continue
        seen.add(key)

        entry: dict = {
            "date":         d.isoformat(),
            "date_display": row["date_raw"],
            "conference":   conf_name,
            "conf_url":     conf_url,
            "location":     row["loc_raw"],
            "title":        row["title"],
            "link_text":    link_label,
            "link_url":     link_url,
        }
        if co_speaker:
            entry["co_speaker"] = co_speaker

        upcoming.append(entry)

    upcoming.sort(key=lambda t: t["date"])
    return upcoming


def main() -> None:
    talks = fetch()
    OUT.write_text(json.dumps({"talks": talks}, indent=2) + "\n")
    print(f"Wrote {len(talks)} upcoming talks to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
