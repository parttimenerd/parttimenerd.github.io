#!/usr/bin/env python3
"""
Generate a GitHub profile README from the homepage data sources.

Reads:
  content/_index.md        — bio paragraph (markdown body, front-matter stripped)
  data/talks.json          — upcoming talks
  data/blog.json           — recent blog posts

Writes:
  docs/profile-README.md   — committed to this repo (for review / diffing)

The caller (GitHub Actions) pushes that file to parttimenerd/parttimenerd
as README.md.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT  = ROOT / "docs" / "profile-README.md"

TOPICS = ["Profiling", "OpenJDK", "Java", "Java Performance", "Debugging", "eBPF"]


def read_bio() -> str:
    raw = (ROOT / "content" / "_index.md").read_text()
    # Strip YAML front-matter
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        body = parts[2].strip() if len(parts) >= 3 else ""
    else:
        body = raw.strip()
    return body


def read_talks() -> list[dict]:
    path = ROOT / "data" / "talks.json"
    if not path.exists():
        return []
    return json.loads(path.read_text()).get("talks", [])


def read_posts() -> list[dict]:
    path = ROOT / "data" / "blog.json"
    if not path.exists():
        return []
    return json.loads(path.read_text()).get("posts", [])


def render(bio: str, talks: list[dict], posts: list[dict]) -> str:
    lines = []

    # ── Header ───────────────────────────────────────────────────────────────
    lines.append("## Johannes Bechberger (@parttimenerd)\n")

    # ── Bio ───────────────────────────────────────────────────────────────────
    lines.append(bio + "\n")

    # ── Topics ────────────────────────────────────────────────────────────────
    tags = " ".join(f"`{t}`" for t in TOPICS)
    lines.append(tags + "\n")
    lines.append("🏆 Most Active Speaker 2024 · ☕ Java MVP 2026\n")

    # ── Upcoming talks ────────────────────────────────────────────────────────
    if talks:
        lines.append("---\n")
        lines.append("### 🎤 Upcoming talks\n")
        for t in talks:
            date  = t.get("date_display") or t.get("date") or ""
            # Trim year from display date: "Sep 8 - 9, 2026" → "Sep 8"
            date_short = date.split(" - ")[0].split(",")[0].strip()
            title = t.get("title") or ""
            conf  = t.get("conference") or ""
            conf_url   = t.get("conf_url") or ""
            location   = t.get("location") or ""
            co_speaker = t.get("co_speaker") or ""
            link_text  = t.get("link_text") or ""
            link_url   = t.get("link_url") or ""

            conf_md = f"[{conf}]({conf_url})" if conf_url else conf
            parts = [f"**{date_short}**", title, conf_md]
            if location:
                parts.append(location)
            if co_speaker:
                parts.append(f"w/ {co_speaker}")
            if link_text and link_url:
                parts.append(f"[{link_text}]({link_url})")
            lines.append("- " + " · ".join(parts) + "\n")

    # ── Recent posts ──────────────────────────────────────────────────────────
    if posts:
        lines.append("---\n")
        lines.append("### 📝 Recent posts\n")
        for p in posts:
            date  = p.get("date_display") or p.get("date") or ""
            title = p.get("title") or ""
            url   = p.get("url") or ""
            if url:
                lines.append(f"- {date} — [{title}]({url})\n")
            else:
                lines.append(f"- {date} — {title}\n")
        lines.append(
            "\n→ [All posts at Mostly Nerdless](https://mostlynerdless.de)\n"
        )

    # ── Footer ────────────────────────────────────────────────────────────────
    lines.append("---\n")
    lines.append(
        "<sub>Auto-generated from "
        "[parttimenerd.github.io](https://github.com/parttimenerd/parttimenerd.github.io)"
        "</sub>\n"
    )

    return "\n".join(lines)


def main():
    bio   = read_bio()
    talks = read_talks()
    posts = read_posts()

    readme = render(bio, talks, posts)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    if OUT.exists() and OUT.read_text() == readme:
        print("No changes.")
        return
    OUT.write_text(readme)
    print(f"Written {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
