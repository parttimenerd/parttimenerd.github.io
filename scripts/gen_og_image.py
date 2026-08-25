#!/usr/bin/env python3
"""
Reads content/*/_index.md files with og_title/og_subtitle/og_out front matter.
Downloads Vollkorn Bold + Inter Regular from Google Fonts (cached in scripts/.font_cache/).
Embeds fonts as base64 in an SVG, renders to static/<og_out> at 1200x630 via cairosvg.
"""

import base64
import re
import sys
from pathlib import Path

import cairosvg
import requests
import yaml

ROOT = Path(__file__).resolve().parent.parent
FONT_CACHE = Path(__file__).resolve().parent / ".font_cache"
FONT_CACHE.mkdir(exist_ok=True)

WIDTH, HEIGHT = 1200, 630


def fetch_font_bytes(family: str, weight: int) -> bytes:
    """Download a font file from Google Fonts API, cache locally."""
    cache_key = f"{family.replace(' ', '_')}_{weight}.ttf"
    cache_path = FONT_CACHE / cache_key
    if cache_path.exists():
        return cache_path.read_bytes()

    headers = {"User-Agent": "Mozilla/5.0"}
    css_url = f"https://fonts.googleapis.com/css2?family={family.replace(' ', '+')}:wght@{weight}&display=swap"
    css = requests.get(css_url, headers=headers, timeout=10).text

    urls = re.findall(r"src:\s*url\(([^)]+)\)", css)
    font_url = None
    for u in urls:
        ctx = css[max(0, css.find(u) - 200):css.find(u) + 50]
        if "latin" in ctx or len(urls) == 1:
            font_url = u
            break
    if not font_url and urls:
        font_url = urls[0]
    if not font_url:
        raise RuntimeError(f"Could not find font URL for {family} {weight}")

    data = requests.get(font_url, timeout=10).content
    cache_path.write_bytes(data)
    return data


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


def make_svg(og_title: str, og_subtitle: str) -> str:
    vollkorn = fetch_font_bytes("Vollkorn", 700)
    inter = fetch_font_bytes("Inter", 400)

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="{WIDTH}" height="{HEIGHT}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <style>
      @font-face {{
        font-family: 'Vollkorn';
        font-weight: 700;
        src: url('data:font/truetype;base64,{b64(vollkorn)}') format('truetype');
      }}
      @font-face {{
        font-family: 'Inter';
        font-weight: 400;
        src: url('data:font/truetype;base64,{b64(inter)}') format('truetype');
      }}
    </style>
  </defs>
  <rect width="{WIDTH}" height="{HEIGHT}" fill="#ffffff"/>
  <text x="{WIDTH // 2}" y="{HEIGHT // 2 - 30}"
        font-family="Vollkorn" font-weight="700" font-size="96"
        fill="#1a1a1a" text-anchor="middle" dominant-baseline="middle">
    {og_title}
  </text>
  <text x="{WIDTH // 2}" y="{HEIGHT // 2 + 70}"
        font-family="Inter" font-weight="400" font-size="28"
        fill="#6b7280" text-anchor="middle" dominant-baseline="middle">
    {og_subtitle}
  </text>
</svg>"""


def parse_frontmatter(md_path: Path) -> dict:
    text = md_path.read_text()
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}
    return yaml.safe_load(m.group(1)) or {}


def main():
    content_dir = ROOT / "content"
    static_dir = ROOT / "static"
    static_dir.mkdir(exist_ok=True)

    pages = list(content_dir.glob("**/_index.md"))
    generated = 0

    for page in pages:
        fm = parse_frontmatter(page)
        og_title = fm.get("og_title")
        og_subtitle = fm.get("og_subtitle", "")
        og_out = fm.get("og_out")
        if not og_title or not og_out:
            continue

        out_path = static_dir / og_out
        print(f"  Generating {og_out} for '{og_title}'...")
        svg = make_svg(og_title, og_subtitle)
        cairosvg.svg2png(
            bytestring=svg.encode(),
            write_to=str(out_path),
            output_width=WIDTH,
            output_height=HEIGHT,
        )
        print(f"  → {out_path} ({out_path.stat().st_size // 1024} KB)")
        generated += 1

    print(f"Generated {generated} og-image(s).")


if __name__ == "__main__":
    main()
