#!/usr/bin/env python3
"""
Strips empty/null/false boilerplate from static.yaml files and prepends a
schema reference comment block so the file is self-documenting.

Usage: python scripts/clean_static_yaml.py [--check]
  --check: dry-run — print what would change, exit 1 if any changes needed
"""

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

SCHEMA_HEADER = """\
# ─────────────────────────────────────────────────────────────────────────────
# ENTRY SCHEMA  (omit any optional field you don't need)
# ─────────────────────────────────────────────────────────────────────────────
#
# REQUIRED
#   id:               string  — slug, matches GitHub repo name (parttimenerd/<id>)
#   tag:              ready | experimental | poc | demo
#   tagline:          string  — 1–2 sentence description shown in detail view
#   tagline_short:    string  — ≤ 10 words shown on cards and in the nav tooltip
#
# OPTIONAL — source control
#   github_url:       string  — full URL; defaults to https://github.com/parttimenerd/<id>
#   github_pages:     string  — docs/web-app URL; shows "Docs" or "Web app" link in header
#
# OPTIONAL — release resolution (script tries these in order, falls back to GitHub)
#   maven_coordinates: "groupId:artifactId"  — used by fetch_releases.py
#   cargo_crate:       "crate-name"          — used by fetch_releases.py
#   static_version:    string  — hard-coded version when no release source exists
#   no_release:        true    — skip this entry in fetch_releases.py entirely
#
# OPTIONAL — card/detail content
#   group:            string  — section heading on the collection page
#   screenshot:       string  — URL; shown with lightbox in detail view
#   when_to_use:      list    — bullet points (shown green ✓)
#   when_not_to_use:  list    — bullet points (shown red ✗)
#   features:         list    — bullet points for demo/poc entries without when_to_use
#   vs:               object  — comparison table:
#                       name: "Other Lib"
#                       url:  "https://..."
#                       bottom_line: "One-liner picking guidance"
#                       comparison:
#                         - { feature: "JAR size", femto: "~50 KB", other: "~870 KB" }
#   related:          list    — { label: "name", url: "https://..." }
#   links:            list    — { label: "Blog post ↗", url: "https://..." }
#   install:          list    — code tabs:
#                         - label: Maven
#                           lang: xml
#                           code: |
#                             <dependency>...</dependency>
#                       VERSION is substituted with the resolved release version
#   usage:            list    — same structure as install; VERSION not substituted
#   note:             string  — shown as amber callout at the bottom of the detail section
# ─────────────────────────────────────────────────────────────────────────────
#
# COPY-PASTE TEMPLATE FOR A NEW ENTRY:
#
# - id: my-tool
#   tag: experimental
#   tagline: "One or two sentences. Use it when..."
#   tagline_short: "≤10 words"
#   when_to_use:
#     - You need X
#   when_not_to_use:
#     - You need Y
#   install:
#     - label: Maven
#       lang: xml
#       code: |
#         <dependency>
#           <groupId>me.bechberger</groupId>
#           <artifactId>my-tool</artifactId>
#           <version>VERSION</version>
#         </dependency>
#   usage:
#     - label: Example
#       lang: java
#       code: |
#         // example code here
# ─────────────────────────────────────────────────────────────────────────────

"""

# Fields omitted when their value is empty / null
OMIT_IF_EMPTY = {
    "screenshot", "static_version", "github_pages", "github_url",
    "note", "group", "vs", "related", "links", "install", "usage",
    "when_to_use", "when_not_to_use", "features",
    "maven_coordinates", "cargo_crate",
}
# Fields omitted when False
OMIT_IF_FALSE = {"no_release"}


class _LiteralStr(str):
    pass


def _literal_representer(dumper, data):
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")


def _build_dumper():
    class CleanDumper(yaml.Dumper):
        pass
    CleanDumper.add_representer(_LiteralStr, _literal_representer)
    return CleanDumper


def _wrap_literals(obj):
    """Recursively wrap multi-line strings as _LiteralStr so they dump with |."""
    if isinstance(obj, str):
        return _LiteralStr(obj) if "\n" in obj else obj
    if isinstance(obj, list):
        return [_wrap_literals(i) for i in obj]
    if isinstance(obj, dict):
        return {k: _wrap_literals(v) for k, v in obj.items()}
    return obj


def clean_entry(entry: dict) -> dict:
    result = {}
    for k, v in entry.items():
        if k in OMIT_IF_EMPTY and (v is None or v == "" or v == []):
            continue
        if k in OMIT_IF_FALSE and v is False:
            continue
        result[k] = v
    return result


def process(path: Path, check: bool) -> bool:
    """Returns True if the file was (or would be) changed."""
    raw = path.read_text()
    # Strip existing schema header if present
    if raw.startswith("# ─"):
        # Find end of header block (last line of dashes before first list item)
        lines = raw.splitlines(keepends=True)
        start = 0
        for i, line in enumerate(lines):
            if not line.startswith("#") and line.strip():
                start = i
                break
        raw = "".join(lines[start:])

    entries = yaml.safe_load(raw) or []
    cleaned = [clean_entry(e) for e in entries]
    wrapped = _wrap_literals(cleaned)

    dumper = _build_dumper()
    dumped = yaml.dump(
        wrapped,
        Dumper=dumper,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        width=100,
    )
    new_content = SCHEMA_HEADER + dumped

    if new_content == path.read_text():
        return False

    if check:
        print(f"  WOULD CHANGE: {path.relative_to(ROOT)}")
        return True

    path.write_text(new_content)
    print(f"  Updated: {path.relative_to(ROOT)}")
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    changed = False
    for section in ("femto", "jvm-tools", "experiments"):
        path = ROOT / "data" / section / "static.yaml"
        if path.exists():
            changed |= process(path, args.check)

    if args.check and changed:
        print("Run: python scripts/clean_static_yaml.py  to apply changes")
        sys.exit(1)


if __name__ == "__main__":
    main()
