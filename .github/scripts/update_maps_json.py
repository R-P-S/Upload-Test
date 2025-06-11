#!/usr/bin/env python3
"""
Re-generate maps.json so it always lists every *.SC2Map in the repo.

For each map:
• If the map is new → add an entry with version "0.0.1"
• If the map already exists but its SHA-256 changed → bump patch part of its version.
• If unchanged → leave version alone.

If any map in a campaign bumps, bump the campaign's patch version too.
Assumes a single campaign block; extend logic if you add more campaigns.
"""

import hashlib, json, re
from pathlib import Path

ROOT        = Path(__file__).resolve().parents[2]   # repo root
MAPS_JSON   = ROOT / "maps.json"
TITLE       = "Azeroth Reborn"
ICON_NAME   = "WC3_AZRB2.png"                       # PNG in /assets
RAW_BASE    = f"https://raw.githubusercontent.com/{ROOT.parts[-1]}/main/"

SEMVER_RE   = re.compile(r"^(?P<maj>\d+)\.(?P<min>\d+)\.(?P<patch>\d+)$")

def next_patch(ver: str) -> str:
    m = SEMVER_RE.match(ver) or SEMVER_RE.match("0.0.0")
    maj, mini, pat = map(int, m.groups())
    return f"{maj}.{mini}.{pat+1}"

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb", buffering=1024 * 1024) as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

# -------- load current manifest (if any) ---------------------------
if MAPS_JSON.exists():
    data = json.loads(MAPS_JSON.read_text())
    if isinstance(data, list) and data:
        camp      = data[0]
        old_maps  = {m["name"]: m for m in camp["maps"]}
        camp_ver  = camp["version"]
    else:
        old_maps, camp_ver = {}, "0.0.0"
else:
    old_maps, camp_ver = {}, "0.0.0"

# -------- build dict of ALL maps currently in repo -----------------
repo_maps = {p.name: p for p in ROOT.rglob("*.SC2Map")}   # <-- restored line

updated_maps = []
bumped_any   = False

for map_path in repo_maps.values():                       # now uses repo_maps
    name   = map_path.name
    digest = sha256(map_path)
    entry  = old_maps.get(name, {"version": "0.0.0", "sha256": "", "name": name})
    if entry["sha256"] != digest:
        entry["version"] = next_patch(entry["version"] or "0.0.0")
        entry["sha256"]  = digest
        bumped_any       = True
    entry["url"] = RAW_BASE + name
    updated_maps.append(entry)

# keep entries for maps that were removed from repo (optional)
for missing in (set(old_maps) - set(repo_maps)):
    updated_maps.append(old_maps[missing])

# bump campaign version if any map bumped or added/removed
if bumped_any or len(updated_maps) != len(old_maps):
    camp_ver = next_patch(camp_ver)

manifest = [{
    "title": TITLE,
    "version": camp_ver,
    "asset": ICON_NAME,
    "maps": sorted(updated_maps, key=lambda m: m["name"])
}]

MAPS_JSON.write_text(json.dumps(manifest, indent=2))
print("maps.json updated")
