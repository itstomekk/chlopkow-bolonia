"""Preview-only east1 prop assets: 14 user-approved unique placements, no game data writes."""
import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "gen/yards/strip_east1"
data = json.loads((OUT / "props/placements_preview.json").read_text(encoding="utf-8"))
source = json.loads((ROOT / "plans/yard-review-east1-v1-decisions.json").read_text(encoding="utf-8"))
assert data["gameChangesApplied"] is False
assert len(data["props"]) == 14
assert len({p["id"] for p in data["props"]}) == 14
assert "east1-E1-p2" not in {p["candidate"] for p in data["props"]}  # same cart as 19-p1
assert "east1-20-p3" not in {p["candidate"] for p in data["props"]}  # hedge merged with 19-p4
assert not ({"east1-23-p1", "east1-23-p2"} & {p["candidate"] for p in data["props"]})
for p in data["props"]:
    d = source["decisions"][p["candidate"]]
    assert d["decision"] == "add" and d["identification"] == p["identification"]
for name, asset in data["assets"].items():
    im = Image.open(ROOT / asset["file"])
    assert im.mode == "RGBA" and im.size == tuple(asset["size"])
    assert im.getchannel("A").getbbox() is not None, name
assert Image.open(OUT / "props_map_mockup.png").size == (960, 1590)
assert (OUT / "props_sprites_preview.png").is_file()
assert not data.get("gameFilesChanged", False)
print("east1 props preview: PASS — 14 unique reviewed placements, all RGBA assets, mockup only")
