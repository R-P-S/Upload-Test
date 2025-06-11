#!/usr/bin/env python3
"""
Re-generate maps.json so it always lists every *.SC2Map in the repo.

For each map:
• If the map is new → add an entry with version   "0.0.1"
• If the map already exists but its SHA-256 changed → bump patch part of its version.
• If unchanged → leave version alone.

If **any** map in a campaign bumps, bump the campaign's patch version too.

Assumes a single campaign block; extend `CAMPAIGNS` dict if you want more.
"""

import hashlib, json, os, re
from pathlib import Path

ROOT       = Path(__file__).resolve().parents[2]        # repo root
MAPS_JSON  = ROOT / "maps.json"
CAMPAIGN_TITLE = "Azeroth Reborn"
CAMPAIGN_ICON  = "WC3_AZRB2.png"                        # adjust if needed
RAW_BASE   = "https://raw.githubusercontent.com/{repo}/main/".format(
                repo=ROOT.parts[-1])

SEMVER_RE  = re.compile(r"^(?P<maj>\d+)\.(?P<min>\d+)\.(?P<patch>\d+)$")

def next_patch(ver: str) -> str:
    m = SEMVER_RE.match(ver) or SEMVER_RE.match("0.0.0")
    maj, mini, pat = map(int, m.groups())
    return f"{maj}.{mini}.{pat+1}"

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

# ------------------ load existing maps.json -----------------------
if MAPS_JSON.exists():
    data = json.loads(MAPS_JSON.read_text())
    if isinstance(data, list) and data:
        camp = data[0]
        old_maps = {m["name"]: m for m in camp["maps"]}
        camp_ver = camp["version"]
    else:
        camp, old_maps, camp_ver = {}, {}, "0.0.0"
else:
    camp, old_maps, camp_ver = {}, {}, "0.0.0"

updated_maps = []
bumped_any   = False

for map_path in ROOT.glob("*.SC2Map"):
    name   = map_path.name
    digest = sha256(map_path)
    entry  = old_maps.get(name,
                          {"version": "0.0.0", "sha256": "", "name": name})
    if entry["sha256"] != digest:
        entry["version"] = next_patch(entry["version"])
        entry["sha256"]  = digest
        bumped_any       = True
    entry["url"] = RAW_BASE + name
    updated_maps.append(entry)

# bump campaign if any map bumped or a new map added
if bumped_any or len(updated_maps) != len(old_maps):
    camp_ver = next_patch(camp_ver)

manifest = [{
    "title" : CAMPAIGN_TITLE,
    "version": camp_ver,
    "asset" : CAMPAIGN_ICON,
    "maps"  : sorted(updated_maps, key=lambda x: x["name"])
}]

MAPS_JSON.write_text(json.dumps(manifest, indent=2))
print("maps.json updated")
