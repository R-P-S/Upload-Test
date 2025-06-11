#!/usr/bin/env python3
"""
Regenerate maps.json from campaigns/<Campaign> folders.

• Adds new maps (version 0.0.1)
• Bumps patch when SHA-256 changes
• Removes deleted maps
• Puts any map whose filename contains “launcher” first
• Bumps campaign patch if any map in it changed
"""

import hashlib, json, os, re, subprocess
from urllib.parse import quote
from pathlib import Path

# ------------------------------------------------------------
# Paths
# ------------------------------------------------------------
ROOT       = Path(__file__).resolve().parents[2]    # repo root
MAPS_DIR   = ROOT / "campaigns"
MAPS_JSON  = ROOT / "maps.json"

# ------------------------------------------------------------
# Derive <owner>/<repo> automatically
# ------------------------------------------------------------
owner_repo = os.getenv("GITHUB_REPOSITORY")         # e.g. "R-P-S/Upload-Test"
if not owner_repo or "/" not in owner_repo:
    try:
        remote_url = subprocess.check_output(
            ["git", "config", "--get", "remote.origin.url"],
            text=True
        ).strip()
        m = re.search(r"[/:]([^/]+)/([^/]+?)(?:\.git)?$", remote_url)
        if m:
            owner_repo = f"{m.group(1)}/{m.group(2)}"
    except Exception:
        pass

if not owner_repo or "/" not in owner_repo:
    raise SystemExit("❌ Unable to determine GitHub owner/repo. "
                     "Set GITHUB_REPOSITORY env-var or configure a git remote.")

RAW_BASE = f"https://raw.githubusercontent.com/{owner_repo}/main/"

# ------------------------------------------------------------
# SemVer helpers
# ------------------------------------------------------------
SEMVER_RE = re.compile(r"^(?P<maj>\d+)\.(?P<min>\d+)\.(?P<patch>\d+)$")

def next_patch(ver: str) -> str:
    m = SEMVER_RE.match(ver or "0.0.0")
    maj, mini, pat = map(int, m.groups())
    return f"{maj}.{mini}.{pat+1}"

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

# ------------------------------------------------------------
# Load existing manifest (if any)
# ------------------------------------------------------------
current = {c["title"]: c for c in json.loads(MAPS_JSON.read_text())} \
          if MAPS_JSON.exists() else {}

new_manifest = []

# ------------------------------------------------------------
# Walk every campaign folder
# ------------------------------------------------------------
for camp_dir in sorted(p for p in MAPS_DIR.iterdir() if p.is_dir()):
    title     = camp_dir.name                   # human-readable title (with spaces)
    asset_png = f"{title}.png"
    old_block = current.get(title, {})
    old_maps  = {m["name"]: m for m in old_block.get("maps", [])}
    camp_ver  = old_block.get("version", "0.0.0")

    updated_maps = []
    bumped_any   = False

    for map_path in sorted(camp_dir.glob("*.SC2Map")):
        name   = map_path.name
        digest = sha256(map_path)
        entry  = old_maps.get(name, {"version": "0.0.0", "sha256": "", "name": name})

        if entry["sha256"] != digest:
            entry["version"] = next_patch(entry["version"])
            entry["sha256"]  = digest
            bumped_any       = True

        # URL-encode relative path (spaces → %20)
        rel_path = quote(map_path.relative_to(ROOT).as_posix())
        entry["url"] = RAW_BASE + rel_path
        updated_maps.append(entry)

    # put launcher first
    updated_maps.sort(key=lambda m: (0 if "launcher" in m["name"].lower() else 1,
                                     m["name"].lower()))

    # bump campaign if anything changed
    if bumped_any or len(updated_maps) != len(old_maps):
        camp_ver = next_patch(camp_ver)

    new_manifest.append({
        "title":   title,
        "version": camp_ver,
        "asset":   asset_png,
        "maps":    updated_maps
    })

# ------------------------------------------------------------
# Write maps.json
# ------------------------------------------------------------
MAPS_JSON.write_text(json.dumps(new_manifest, indent=2))
print("✅ maps.json regenerated")
