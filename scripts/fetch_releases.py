#!/usr/bin/env python3
"""
Usage: python fetch_releases.py --section femto|jvm-tools|experiments

Reads  data/<section>/static.yaml
Writes data/<section>/releases.json  (only if any version changed)

Version resolution order (first hit wins):
  1. crates.io    — if entry has cargo_crate: "<crate-name>"
  2. Maven Central — if entry has maven_coordinates: "groupId:artifactId"
  3. GitHub releases — parttimenerd/<id>/releases, skipping rolling tags
                       (tag names matching snapshot/nightly/latest/rc/alpha/beta
                        are skipped; the most recent stable release is used)
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

# Tag names (case-insensitive) treated as rolling/pre-release — skipped when
# looking for the latest stable release.
ROLLING_TAGS = re.compile(r"^(snapshot|nightly|latest|rc[\d.-]|alpha[\d.-]|beta[\d.-])", re.IGNORECASE)


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


def fetch_from_crates_io(crate_name: str) -> dict | None:
    """Fetch latest stable version from crates.io."""
    url = f"https://crates.io/api/v1/crates/{crate_name}"
    headers = {"User-Agent": "parttimenerd-site-builder/1.0 (https://parttimenerd.github.io)"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()
        crate = data.get("crate", {})
        version = crate.get("newest_version", "")
        updated = (crate.get("updated_at") or "")[:10]
        if not version:
            return None
        return {"version": version, "date": updated, "changelog": ""}
    except Exception as exc:
        print(f"  crates.io lookup failed for {crate_name}: {exc}", file=sys.stderr)
        return None


def fetch_from_maven_central(coordinates: str) -> dict | None:
    """Fetch latest version from Maven Central search API."""
    group_id, artifact_id = coordinates.split(":", 1)
    url = (
        "https://search.maven.org/solrsearch/select"
        f"?q=g:{group_id}+AND+a:{artifact_id}&rows=1&wt=json"
    )
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        docs = resp.json()["response"]["docs"]
        if not docs:
            return None
        version = docs[0].get("latestVersion", "")
        timestamp_ms = docs[0].get("timestamp", 0)
        date = ""
        if timestamp_ms:
            from datetime import datetime, timezone
            date = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        return {"version": version, "date": date, "changelog": ""}
    except Exception as exc:
        print(f"  Maven Central lookup failed for {coordinates}: {exc}", file=sys.stderr)
        return None


def fetch_from_github(repo_id: str) -> dict | None:
    """Fetch latest stable release from GitHub, skipping rolling tags."""
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    # First try /releases/latest — fastest path for repos with proper releases
    url_latest = f"https://api.github.com/repos/parttimenerd/{repo_id}/releases/latest"
    resp = requests.get(url_latest, headers=headers, timeout=10)
    if resp.status_code == 200:
        data = resp.json()
        tag = data.get("tag_name", "")
        if not ROLLING_TAGS.match(tag) and not data.get("prerelease") and not data.get("draft"):
            version = tag.lstrip("v")
            date = (data.get("published_at") or "")[:10]
            changelog = process_changelog(data.get("body", ""))
            return {"version": version, "date": date, "changelog": changelog}

    # /releases/latest returned a rolling tag or 404 — scan the list for the
    # most recent non-rolling, non-prerelease release
    url_list = f"https://api.github.com/repos/parttimenerd/{repo_id}/releases?per_page=20"
    resp2 = requests.get(url_list, headers=headers, timeout=10)
    if resp2.status_code != 200:
        return None
    releases = resp2.json()
    for rel in releases:
        if rel.get("prerelease") or rel.get("draft"):
            continue
        tag = rel.get("tag_name", "")
        if ROLLING_TAGS.match(tag):
            continue
        version = tag.lstrip("v")
        date = (rel.get("published_at") or "")[:10]
        changelog = process_changelog(rel.get("body", ""))
        return {"version": version, "date": date, "changelog": changelog}

    return None


def fetch_latest_release(entry: dict) -> dict | None:
    repo_id = entry["id"]

    cargo = entry.get("cargo_crate")
    if cargo:
        result = fetch_from_crates_io(cargo)
        if result:
            print(f"  {repo_id}: crates.io → {result['version']}")
            return result
        print(f"  {repo_id}: crates.io miss, falling back to GitHub")

    maven = entry.get("maven_coordinates")
    if maven:
        result = fetch_from_maven_central(maven)
        if result:
            print(f"  {repo_id}: Maven Central → {result['version']}")
            return result
        print(f"  {repo_id}: Maven Central miss, falling back to GitHub")

    return fetch_from_github(repo_id)


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
        result = fetch_latest_release(entry)
        if result is None:
            print(f"  {tool_id}: no release found, keeping existing")
            if tool_id not in new_entries:
                new_entries[tool_id] = {"version": "", "date": "", "changelog": ""}
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
