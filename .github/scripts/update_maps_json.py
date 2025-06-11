#!/usr/bin/env python3
"""
Regenerate maps.json from campaigns/<Campaign> folders.

• Adds new maps (version 0.0.1)
• Bumps patch when SHA-256 changes
• Removes deleted maps
• Puts any map whose filename contains “launcher” first
• Bumps campaign patch if any map in it changed
"""

import hashlib, json, re
from urllib.parse import quote          # ← NEW import
from pathlib import Path

ROOT        = Path(__file__).resolve().parents[2]
MAPS_DIR    = ROOT / "campaigns"
MAPS_JSON   = ROOT / "maps.json"

USER        = "R-P-S"                   # your GitHub username
REPO_NAME   = ROOT.parts[-1]
RAW_BASE    = f"https://raw.githubusercontent.com/{USER}/{REPO_NAME}/main/"

SEMVER_RE   = re.compile(r"^(?P<maj>\d+)\.(?P<min>\d+)\.(?P<patch>\d+)$")

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

# load existing manifest (if any)
current = {c["title"]: c for c in json.loads(MAPS_JSON.read_text())} if MAPS_JSON.exists() else {}
new_manifest = []

for camp_dir in sorted(p for p in MAPS_DIR.iterdir() if p.is_dir()):
    title      = camp_dir.name            # display title keeps spaces
    asset_png  = f"{title}.png"
    old_block  = current.get(title, {})
    old_maps   = {m["name"]: m for m in old_block.get("maps", [])}
    camp_ver   = old_block.get("version", "0.0.0")

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

        # ---------- URL now URL-encoded (spaces → %20) -------------
        entry["url"] = RAW_BASE + quote(map_path.relative_to(ROOT).as_posix())

        updated_maps.append(entry)

    # launcher first
    updated_maps.sort(
        key=lambda m: (0 if "launcher" in m["name"].lower() else 1, m["name"].lower())
    )

    # bump campaign version if any map added/removed/changed
    if bumped_any or len(updated_maps) != len(old_maps):
        camp_ver = next_patch(camp_ver)

    new_manifest.append({
        "title":   title,
        "version": camp_ver,
        "asset":   asset_png,
        "maps":    updated_maps
    })

MAPS_JSON.write_text(json.dumps(new_manifest, indent=2))
print("maps.json regenerated")