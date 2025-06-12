#!/usr/bin/env python3
"""
Regenerate maps.json from campaigns/<Campaign>/ structure.

• New files (map or mod) start at version 1.0
• On SHA-256 change → bump minor (1.0 → 1.1 → 1.2)
• Removes deleted entries
• ‘launcher’ map always listed first
• Campaign minor version bumps if any entry changed
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
        url = subprocess.check_output(
            ["git", "config", "--get", "remote.origin.url"], text=True
        ).strip()
        m = re.search(r"[/:]([^/]+)/([^/]+?)(?:\.git)?$", url)
        if m:
            owner_repo = f"{m.group(1)}/{m.group(2)}"
    except Exception:
        pass
if not owner_repo or "/" not in owner_repo:
    raise SystemExit("Unable to determine <owner>/<repo>")

RAW_BASE = f"https://raw.githubusercontent.com/{owner_repo}/main/"

# -------- version helpers (major.minor) ---------------------
VER_RE = re.compile(r"^(?P<maj>\d+)\.(?P<min>\d+)$")
def bump_minor(ver: str) -> str:
    m = VER_RE.match(ver or "1.0") or VER_RE.match("1.0")
    maj, minor = map(int, m.groups())
    return f"{maj}.{minor+1}"

def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb", buffering=0) as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
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

    # --- collect *.SC2Map files in campaign root ------------------
    for map_path in camp_dir.glob("*.SC2Map"):
        updated_maps.append(map_path)

    # --- collect *.SC2Mod files under mods/ -----------------------
    for mod_path in (camp_dir / "mods").glob("*.SC2Mod"):
        updated_maps.append(mod_path)

    # --- build / update entries ----------------------------------
    new_entries = []
    for path in sorted(updated_maps, key=lambda p: p.name.lower()):
        name   = path.name
        digest = sha256(path)
        entry  = old_maps.get(name, {"version": "1.0",
                                     "sha256": "",
                                     "name":   name})

        if entry["sha256"] != digest:
            entry["version"] = bump_minor(entry["version"])
            entry["sha256"]  = digest
            bumped_any       = True

        rel = quote(path.relative_to(ROOT).as_posix())
        entry["url"] = RAW_BASE + rel
        new_entries.append(entry)

    # launcher first
    new_entries.sort(key=lambda m: (0 if "launcher" in m["name"].lower() else 1,
                                    m["name"].lower()))

    # bump campaign version if anything changed
    if bumped_any or len(new_entries) != len(old_maps):
        camp_ver = bump_minor(camp_ver)

    new_manifest.append({
        "title":   title,
        "version": camp_ver,
        "asset":   asset_png,
        "maps":    new_entries
    })

# -------- write manifest ------------------------------------------
MAPS_JSON.write_text(json.dumps(new_manifest, indent=2))
print("✅ maps.json regenerated with maps *and* mods")
