#!/usr/bin/env python3
"""
Usage: python fetch_releases.py --section femto|jvm-tools|experiments [--dry-run]

Reads  data/<section>/static.yaml
Writes data/<section>/releases.json  (only if any version changed)

Version resolution order (first hit wins):
  1. cargo CLI  — if entry has cargo_crate: "<crate-name>"
     Falls back to crates.io REST if cargo is unavailable.
  2. Maven Central metadata XML — if entry has maven_coordinates: "groupId:artifactId"
     Falls back to Maven Central search API if metadata unavailable.
  3. GitHub releases — parttimenerd/<id>/releases, skipping rolling tags
                       (tag names matching snapshot/nightly/latest/rc/alpha/beta
                        are skipped; the most recent stable release is used)

Exit codes:
  0 — success (even if nothing changed)
  1 — one or more entries failed to resolve AND had no prior cached version
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parent.parent
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

# Tag names (case-insensitive) treated as rolling/pre-release — skipped when
# looking for the latest stable release.
ROLLING_TAGS = re.compile(r"^(snapshot|nightly|latest|rc[\d.-]|alpha[\d.-]|beta[\d.-])", re.IGNORECASE)

# Maximum changelog bullet points to keep.
CHANGELOG_MAX_LINES = 8


def _run(cmd: list[str], timeout: int = 30) -> str | None:
    """Run a subprocess, return stdout or None on failure."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        if result.returncode == 0:
            return result.stdout
        return None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def _get(url: str, headers: dict | None = None, timeout: int = 10, retries: int = 3) -> requests.Response:
    """GET with exponential backoff on 429 / 5xx."""
    headers = headers or {}
    delay = 2.0
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            if resp.status_code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                retry_after = float(resp.headers.get("Retry-After", delay))
                time.sleep(min(retry_after, 60))
                delay *= 2
                continue
            return resp
        except requests.exceptions.Timeout:
            if attempt < retries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            raise
    raise RuntimeError(f"GET {url} failed after {retries} attempts")


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
            if len(lines) >= CHANGELOG_MAX_LINES:
                break
    result = " · ".join(lines)
    if len(result) > 600:
        result = result[:597] + "…"
    return result


# ---------------------------------------------------------------------------
# Cargo / crates.io
# ---------------------------------------------------------------------------

def fetch_from_cargo_cli(crate_name: str) -> dict | None:
    """Use `cargo search` to get latest version from crates.io."""
    out = _run(["cargo", "search", "--limit", "1", crate_name])
    if out is None:
        return None
    m = re.match(rf'^{re.escape(crate_name)}\s*=\s*"([^"]+)"', out.strip())
    if m:
        return {"version": m.group(1), "date": "", "changelog": ""}
    return None


def fetch_from_crates_io(crate_name: str) -> dict | None:
    """Fetch latest stable version from crates.io REST API."""
    url = f"https://crates.io/api/v1/crates/{crate_name}"
    headers = {"User-Agent": "parttimenerd-site-builder/1.0 (https://parttimenerd.github.io)"}
    try:
        resp = _get(url, headers=headers)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()
        crate = data.get("crate", {})
        version = crate.get("newest_version", "")
        if not version:
            return None
        # Get date from the specific version entry (not crate-level updated_at)
        date = ""
        for v in data.get("versions", []):
            if v.get("num") == version:
                date = (v.get("created_at") or "")[:10]
                break
        return {"version": version, "date": date, "changelog": ""}
    except Exception as exc:
        print(f"  crates.io lookup failed for {crate_name}: {exc}", file=sys.stderr)
        return None


def fetch_cargo(crate_name: str) -> dict | None:
    """Try cargo CLI first, fall back to crates.io REST."""
    result = fetch_from_cargo_cli(crate_name)
    if result:
        return result
    return fetch_from_crates_io(crate_name)


# ---------------------------------------------------------------------------
# Maven / Maven Central
# ---------------------------------------------------------------------------

def fetch_from_maven_central_metadata(coordinates: str) -> dict | None:
    """
    Fetch latest release version via repo1.maven.org maven-metadata.xml.
    This is the most reliable method — the search API lags and the mvn CLI
    echoes 'RELEASE' instead of the resolved version.
    """
    group_id, artifact_id = coordinates.split(":", 1)
    group_path = group_id.replace(".", "/")
    url = f"https://repo1.maven.org/maven2/{group_path}/{artifact_id}/maven-metadata.xml"
    try:
        resp = _get(url)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        xml = resp.text
        # Prefer <release> over <latest> (release = non-snapshot stable)
        m = re.search(r"<release>([^<]+)</release>", xml)
        if not m:
            m = re.search(r"<latest>([^<]+)</latest>", xml)
        if not m:
            return None
        version = m.group(1).strip()
        # Use Last-Modified header from the versioned POM for the date
        pom_url = (
            f"https://repo1.maven.org/maven2/{group_path}/{artifact_id}"
            f"/{version}/{artifact_id}-{version}.pom"
        )
        date = ""
        try:
            head = requests.head(pom_url, timeout=10)
            lm = head.headers.get("last-modified", "")
            if lm:
                from email.utils import parsedate_to_datetime
                date = parsedate_to_datetime(lm).strftime("%Y-%m-%d")
        except Exception:
            pass
        return {"version": version, "date": date, "changelog": ""}
    except Exception as exc:
        print(f"  Maven Central metadata lookup failed for {coordinates}: {exc}", file=sys.stderr)
        return None


def fetch_from_maven_central_search(coordinates: str) -> dict | None:
    """Fallback: fetch latest version from Maven Central search API (lags ~hours)."""
    group_id, artifact_id = coordinates.split(":", 1)
    url = (
        "https://search.maven.org/solrsearch/select"
        f"?q=g:{group_id}+AND+a:{artifact_id}&rows=1&wt=json"
    )
    try:
        resp = _get(url)
        resp.raise_for_status()
        docs = resp.json()["response"]["docs"]
        if not docs:
            return None
        version = docs[0].get("latestVersion", "")
        if not version:
            return None
        timestamp_ms = docs[0].get("timestamp", 0)
        date = ""
        if timestamp_ms:
            from datetime import datetime, timezone
            date = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        return {"version": version, "date": date, "changelog": ""}
    except Exception as exc:
        print(f"  Maven Central search failed for {coordinates}: {exc}", file=sys.stderr)
        return None


def fetch_maven(coordinates: str) -> dict | None:
    """Fetch from Maven Central metadata XML, fall back to search API."""
    result = fetch_from_maven_central_metadata(coordinates)
    if result:
        return result
    return fetch_from_maven_central_search(coordinates)


# ---------------------------------------------------------------------------
# GitHub
# ---------------------------------------------------------------------------

def fetch_from_github(repo_id: str, github_url: str = "") -> dict | None:
    """Fetch latest stable release from GitHub, skipping rolling tags."""
    if github_url:
        parts = github_url.rstrip("/").split("/")
        repo_path = f"{parts[-2]}/{parts[-1]}"
    else:
        repo_path = f"parttimenerd/{repo_id}"

    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    # First try /releases/latest — fastest path for repos with proper releases
    try:
        resp = _get(f"https://api.github.com/repos/{repo_path}/releases/latest", headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            tag = data.get("tag_name", "")
            if not ROLLING_TAGS.match(tag) and not data.get("prerelease") and not data.get("draft"):
                return {
                    "version": tag.lstrip("v"),
                    "date": (data.get("published_at") or "")[:10],
                    "changelog": process_changelog(data.get("body", "")),
                }
    except Exception as exc:
        print(f"  GitHub /releases/latest failed for {repo_path}: {exc}", file=sys.stderr)
        return None

    # /releases/latest returned a rolling tag or 404 — scan the list
    try:
        resp2 = _get(
            f"https://api.github.com/repos/{repo_path}/releases?per_page=20",
            headers=headers,
        )
        if resp2.status_code != 200:
            return None
        for rel in resp2.json():
            if rel.get("prerelease") or rel.get("draft"):
                continue
            tag = rel.get("tag_name", "")
            if ROLLING_TAGS.match(tag):
                continue
            return {
                "version": tag.lstrip("v"),
                "date": (rel.get("published_at") or "")[:10],
                "changelog": process_changelog(rel.get("body", "")),
            }
    except Exception as exc:
        print(f"  GitHub releases list failed for {repo_path}: {exc}", file=sys.stderr)

    return None


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

def fetch_latest_release(entry: dict) -> dict | None:
    repo_id = entry["id"]

    cargo = entry.get("cargo_crate")
    if cargo:
        result = fetch_cargo(cargo)
        if result:
            return result
        print(f"  {repo_id}: cargo/crates.io miss, falling back to GitHub", file=sys.stderr)

    maven = entry.get("maven_coordinates")
    if maven:
        result = fetch_maven(maven)
        if result:
            return result
        print(f"  {repo_id}: Maven Central miss, falling back to GitHub", file=sys.stderr)

    return fetch_from_github(repo_id, entry.get("github_url", ""))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--section", required=True,
                        help="Data section name: femto, jvm-tools, or experiments")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would change without writing releases.json")
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
    n_updated = 0
    n_unchanged = 0
    n_failed = 0

    for entry in entries:
        tool_id = entry["id"]
        if entry.get("no_release"):
            continue
        result = fetch_latest_release(entry)
        if result is None:
            prev = existing.get(tool_id)
            if prev:
                print(f"  {tool_id}: fetch failed — keeping cached {prev['version']}")
                n_unchanged += 1
            else:
                print(f"  {tool_id}: fetch failed — no cached version", file=sys.stderr)
                n_failed += 1
                new_entries.setdefault(tool_id, {"version": "", "date": "", "changelog": ""})
            continue

        prev = existing.get(tool_id, {})
        if result["version"] != prev.get("version"):
            print(f"  {tool_id}: {prev.get('version', 'none')} → {result['version']}")
            n_updated += 1
        else:
            print(f"  {tool_id}: {result['version']} (unchanged)")
            n_unchanged += 1
        new_entries[tool_id] = result

    print(f"\n  Summary: {n_updated} updated, {n_unchanged} unchanged, {n_failed} failed")

    if n_updated == 0:
        print("  No versions changed — skipping write.")
        if n_failed > 0:
            sys.exit(1)
        return

    if args.dry_run:
        print("  (dry-run: not writing)")
        return

    releases_path.parent.mkdir(parents=True, exist_ok=True)
    releases_path.write_text(json.dumps({"entries": new_entries}, indent=2) + "\n")
    print(f"  Written {releases_path.relative_to(ROOT)}")

    if n_failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
