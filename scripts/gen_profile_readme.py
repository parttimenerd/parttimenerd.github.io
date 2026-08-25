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

SOCIAL = [
    ("GitHub",    "https://github.com/parttimenerd"),
    ("Twitter/X", "https://twitter.com/parttimen3rd"),
    ("Mastodon",  "https://fosstodon.org/@parttimenerd"),
    ("LinkedIn",  "https://www.linkedin.com/in/johannes-bechberger"),
    ("Blog",      "https://mostlynerdless.de"),
    ("Website",   "https://parttimenerd.github.io/"),
]


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
    lines.append("> JVM Engineer · SapMachine team at SAP\n")

    # ── Social links ─────────────────────────────────────────────────────────
    social_md = " · ".join(f"[{label}]({url})" for label, url in SOCIAL)
    lines.append(social_md + "\n")

    # ── Bio ───────────────────────────────────────────────────────────────────
    lines.append("---\n")
    lines.append(bio + "\n")

    # ── Topics ────────────────────────────────────────────────────────────────
    tags = " ".join(f"`{t}`" for t in TOPICS)
    lines.append(tags + "\n")
    lines.append("🏆 Most Active Speaker 2024 · ☕ Java Champion 2026\n")

    # ── Upcoming talks ────────────────────────────────────────────────────────
    if talks:
        lines.append("---\n")
        lines.append("### 🎤 Upcoming talks\n")
        # Deduplicate: group by title, list conferences
        seen_conf: dict[str, list[str]] = {}
        for t in talks:
            title = t.get("title") or ""
            conf  = t.get("conference") or ""
            url   = t.get("conf_url") or ""
            entry = f"[{conf}]({url})" if url else conf
            seen_conf.setdefault(title, []).append(entry)
        for title, confs in seen_conf.items():
            confs_str = ", ".join(confs)
            lines.append(f"- **{title}** — {confs_str}\n")

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
