#!/usr/bin/env python3
"""
Regenerate maps.json to reflect every *.SC2Map located under campaigns/<Campaign>/

• If a map is new → version = "0.0.1"
• If hash changed  → bump patch (x.y.Z+1)
• If unchanged     → keep version
• If a map was deleted from repo → entry disappears

If any map in a campaign bumps, campaign.patch += 1.

Assumes each campaign has a PNG icon with the same folder name but spaces kept,
stored in /assets (e.g. campaigns/Azeroth Reborn/…  →  assets/Azeroth Reborn.png)
"""

import hashlib, json, re
from pathlib import Path

ROOT        = Path(__file__).resolve().parents[2]        # repo root
MAPS_DIR    = ROOT / "campaigns"
ASSETS_DIR  = ROOT / "assets"
MAPS_JSON   = ROOT / "maps.json"

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

# ------------- load current manifest (if exists) -------------------
if MAPS_JSON.exists():
    current = {c["title"]: c for c in json.loads(MAPS_JSON.read_text())}
else:
    current = {}

new_manifest = []

for camp_dir in sorted(p for p in MAPS_DIR.iterdir() if p.is_dir()):
    title = camp_dir.name
    old_block   = current.get(title, {})
    old_maps    = {m["name"]: m for m in old_block.get("maps", [])}
    camp_ver    = old_block.get("version", "0.0.0")
    asset_png   = f"{title}.png"                     # adjust if naming differs

    updated_maps = []
    bumped_any   = False

    # ---------- iterate *.SC2Map in this folder ---------------------
    for map_path in sorted(camp_dir.glob("*.SC2Map")):
        name   = map_path.name
        digest = sha256(map_path)
        entry  = old_maps.get(name, {"version": "0.0.0", "sha256": "", "name": name})

        if entry["sha256"] != digest:
            entry["version"] = next_patch(entry["version"])
            entry["sha256"]  = digest
            bumped_any       = True

        entry["url"] = f"https://raw.githubusercontent.com/{ROOT.parts[-1]}/main/{map_path.relative_to(ROOT).as_posix()}"
        updated_maps.append(entry)

    # ---------- launcher first (contains 'launcher') ---------------
    updated_maps.sort(key=lambda m: (0 if "launcher" in m["name"].lower() else 1, m["name"].lower()))

    # ---------- bump campaign version if any map bumped/added/removed
    if bumped_any or len(updated_maps) != len(old_maps):
        camp_ver = next_patch(camp_ver)

    new_manifest.append({
        "title":   title,
        "version": camp_ver,
        "asset":   asset_png,
        "maps":    updated_maps
    })

# write out
MAPS_JSON.write_text(json.dumps(new_manifest, indent=2))
print("maps.json regenerated")
