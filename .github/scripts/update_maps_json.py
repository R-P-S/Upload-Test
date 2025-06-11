#!/usr/bin/env python3
"""
Regenerate maps.json from campaigns/<Campaign> folders.

• New maps start at version 1.0
• When SHA-256 changes → bump minor (1.0 → 1.1 → 1.2)
• Removes deleted maps
• Puts any filename containing "launcher" first
• Bumps campaign minor if any map in it changed
"""

import hashlib, json, os, re, subprocess
from urllib.parse import quote
from pathlib import Path

# ------------------------------------------------------------
ROOT      = Path(__file__).resolve().parents[2]
MAPS_DIR  = ROOT / "campaigns"
MAPS_JSON = ROOT / "maps.json"

# -------- derive owner/repo for raw URLs --------------------
owner_repo = os.getenv("GITHUB_REPOSITORY")
if not owner_repo or "/" not in owner_repo:
    try:
        remote_url = subprocess.check_output(
            ["git", "config", "--get", "remote.origin.url"], text=True
        ).strip()
        m = re.search(r"[/:]([^/]+)/([^/]+?)(?:\.git)?$", remote_url)
        if m:
            owner_repo = f"{m.group(1)}/{m.group(2)}"
    except Exception:
        pass
if not owner_repo or "/" not in owner_repo:
    raise SystemExit("Unable to determine GitHub owner/repo")
RAW_BASE = f"https://raw.githubusercontent.com/{owner_repo}/main/"

# -------- version helpers (major.minor) ---------------------
VER_RE = re.compile(r"^(?P<maj>\d+)\.(?P<min>\d+)$")
def bump_minor(ver: str) -> str:
    m = VER_RE.match(ver or "1.0") or VER_RE.match("1.0")
    maj, minor = map(int, m.groups())
    return f"{maj}.{minor+1}"

def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda:f.read(1<<20), b""):
            h.update(chunk)
    return h.hexdigest()

# -------- load current manifest -----------------------------------
current = {c["title"]: c for c in json.loads(MAPS_JSON.read_text())} \
          if MAPS_JSON.exists() else {}
new_manifest = []

# -------- iterate campaigns ---------------------------------------
for camp_dir in sorted(p for p in MAPS_DIR.iterdir() if p.is_dir()):
    title      = camp_dir.name
    asset_png  = f"{title}.png"
    old_block  = current.get(title, {})
    old_maps   = {m["name"]: m for m in old_block.get("maps", [])}
    camp_ver   = old_block.get("version", "1.0")

    updated_maps = []
    bumped_any   = False

    for map_path in sorted(camp_dir.glob("*.SC2Map")):
        name   = map_path.name
        digest = sha256(map_path)
        entry  = old_maps.get(name,
                 {"version": "1.0", "sha256": "", "name": name})

        if entry["sha256"] != digest:
            entry["version"] = bump_minor(entry["version"])
            entry["sha256"]  = digest
            bumped_any       = True

        rel = quote(map_path.relative_to(ROOT).as_posix())
        entry["url"] = RAW_BASE + rel
        updated_maps.append(entry)

    # launcher first
    updated_maps.sort(key=lambda m: (0 if "launcher" in m["name"].lower() else 1,
                                     m["name"].lower()))

    # bump campaign if maps changed / added / removed
    if bumped_any or len(updated_maps) != len(old_maps):
        camp_ver = bump_minor(camp_ver)

    new_manifest.append({
        "title":   title,
        "version": camp_ver,
        "asset":   asset_png,
        "maps":    updated_maps
    })

# -------- write file ----------------------------------------------
MAPS_JSON.write_text(json.dumps(new_manifest, indent=2))
print("✅ maps.json regenerated")