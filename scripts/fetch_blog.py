#!/usr/bin/env python3
"""
Fetch the N most recent posts from the blog RSS feed.
Writes data/blog.json  (only if content changed).

Each entry:
  { "title": "...", "url": "...", "date": "2026-07-31", "date_display": "Jul 31" }
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree

import requests

ROOT = Path(__file__).resolve().parent.parent
OUT  = ROOT / "data" / "blog.json"

RSS_URL = "https://mostlynerdless.de/feed/"
N       = 3

MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def fetch_posts(n: int) -> list[dict]:
    resp = requests.get(RSS_URL, timeout=15)
    resp.raise_for_status()
    root = ElementTree.fromstring(resp.content)
    ns   = {"dc": "http://purl.org/dc/elements/1.1/"}
    posts = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        url   = (item.findtext("link")  or "").strip()
        pub   = (item.findtext("pubDate") or "").strip()
        # pubDate: "Fri, 31 Jul 2026 13:23:00 +0000"
        try:
            dt = datetime.strptime(pub, "%a, %d %b %Y %H:%M:%S %z")
            date_iso  = dt.strftime("%Y-%m-%d")
            date_disp = f"{MONTH_ABBR[dt.month - 1]} {dt.day}"
        except ValueError:
            date_iso  = ""
            date_disp = ""
        posts.append({"title": title, "url": url,
                      "date": date_iso, "date_display": date_disp})
        if len(posts) >= n:
            break
    return posts


def main():
    posts = fetch_posts(N)
    if not posts:
        print("No posts found", file=sys.stderr)
        sys.exit(1)

    new_json = json.dumps({"posts": posts}, indent=2) + "\n"

    if OUT.exists() and OUT.read_text() == new_json:
        print("No changes — skipping write.")
        return

    OUT.write_text(new_json)
    print(f"Written {OUT} ({len(posts)} posts)")


if __name__ == "__main__":
    main()
