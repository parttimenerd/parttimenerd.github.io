#!/usr/bin/env python3
"""
Usage: python fetch_releases.py --section femto|supportability

Reads  data/<section>/static.yaml
Writes data/<section>/releases.json  (only if any version changed)
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parent.parent
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")


def process_changelog(body: str) -> str:
    if not body:
        return ""
    lines = []
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if stripped.startswith(("- ", "* ")):
            lines.append(stripped[2:].strip())
    result = " · ".join(lines)
    if len(result) > 300:
        result = result[:297] + "…"
    return result


def fetch_latest_release(repo_id: str) -> dict | None:
    url = f"https://api.github.com/repos/parttimenerd/{repo_id}/releases/latest"
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    resp = requests.get(url, headers=headers, timeout=10)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    data = resp.json()
    version = data.get("tag_name", "").lstrip("v")
    date = (data.get("published_at") or "")[:10]
    changelog = process_changelog(data.get("body", ""))
    return {"version": version, "date": date, "changelog": changelog}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--section", required=True)
    args = parser.parse_args()

    section = args.section
    static_path = ROOT / "data" / section / "static.yaml"
    releases_path = ROOT / "data" / section / "releases.json"

    if not static_path.exists():
        print(f"ERROR: {static_path} not found", file=sys.stderr)
        sys.exit(1)

    entries = yaml.safe_load(static_path.read_text()) or []

    existing: dict = {}
    if releases_path.exists():
        existing = json.loads(releases_path.read_text()).get("entries", {})

    new_entries: dict = dict(existing)
    changed = False

    for entry in entries:
        tool_id = entry["id"]
        if entry.get("no_release"):
            continue
        result = fetch_latest_release(tool_id)
        if result is None:
            print(f"  {tool_id}: no release found, keeping existing")
            if tool_id not in new_entries:
                new_entries[tool_id] = {"version": "unreleased", "date": "", "changelog": ""}
            continue
        prev = existing.get(tool_id, {})
        if result["version"] != prev.get("version"):
            changed = True
            print(f"  {tool_id}: {prev.get('version', 'none')} → {result['version']}")
        new_entries[tool_id] = result

    if not changed:
        print("No versions changed — skipping write.")
        return

    releases_path.parent.mkdir(parents=True, exist_ok=True)
    releases_path.write_text(json.dumps({"entries": new_entries}, indent=2) + "\n")
    print(f"Written {releases_path}")


if __name__ == "__main__":
    main()
