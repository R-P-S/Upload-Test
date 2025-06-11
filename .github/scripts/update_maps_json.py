#!/usr/bin/env python3
import json, hashlib, os, re, subprocess, sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[2]      # repo root
MAPS_JSON = ROOT / "maps.json"

SEMVER_RE = re.compile(r"^(?P<maj>\d+)\.(?P<min>\d+)\.(?P<patch>\d+)$")

def next_patch(ver: str) -> str:
    m = SEMVER_RE.match(ver) or SEMVER_RE.match("0.0.0")
    maj, min_, pat = map(int, m.groups())
    return f"{maj}.{min_}.{pat+1}"

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    data = json.loads(MAPS_JSON.read_text())
    repo_maps = {p.name: p for p in ROOT.rglob("*.SC2Map")}

    any_campaign_bumped = {}

    for camp in data:
        for m in camp["maps"]:
            path = repo_maps.get(m["name"])
            if not path:
                print("Warning: map not found in repo:", m["name"])
                continue
            digest = sha256(path)
            if m.get("sha256") != digest:
                # map changed → bump map version (patch)
                m["version"] = next_patch(m.get("version", "0.0.0"))
                m["sha256"]  = digest
                any_campaign_bumped[camp["title"]] = True
        # bump campaign if any map changed
        if any_campaign_bumped.get(camp["title"]):
            camp["version"] = next_patch(camp.get("version", "0.0.0"))

    MAPS_JSON.write_text(json.dumps(data, indent=2))
    print("maps.json updated")

if __name__ == "__main__":
    main()
