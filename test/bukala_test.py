"""Verify Bukała display-name and sprite-atlas integration without external services."""
import json
import re
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
failures = []

def check(ok, message):
    if not ok:
        failures.append(message)


game = (ROOT / "docs/js/game.js").read_text(encoding="utf-8")
mini = (ROOT / "docs/js/minigames.js").read_text(encoding="utf-8")
items = json.loads((ROOT / "docs/items.json").read_text(encoding="utf-8"))
npcs = items.get("npcs", [])
check("michal" in [npc.get("id") for npc in npcs], "stable internal range NPC id is missing")
check(game.count("michal: 'BUKAŁA'") == 2, "Polish/English display names should both be BUKAŁA")
check("Michał:" not in mini and "Bukała:" in mini, "range dialogue still uses the old name")

atlas = Image.open(ROOT / "docs/img/npcs.png").convert("RGBA")
source = Image.open(ROOT / "gen/npc_src/bukala.png").convert("RGBA")
check(atlas.size == (14 * 130, 170), f"unexpected NPC atlas dimensions: {atlas.size}")
check(source.size == (130, 170), f"Bukała source should be one atlas cell, got {source.size}")
cell = atlas.crop((6 * 130, 0, 7 * 130, 170))
check(cell.getbbox() is not None, "Bukała atlas cell (index 6) is empty")
# Reproduce build_npcs.py's fit-and-place logic, then require exact equality with the atlas cell.
sprite = source.crop(source.getbbox())
scale = 150 / sprite.height
sprite = sprite.resize((round(sprite.width * scale), 150), Image.Resampling.LANCZOS)
if sprite.width > 130:
    sprite = sprite.resize((130, round(sprite.height * 130 / sprite.width)), Image.Resampling.LANCZOS)
expected = Image.new("RGBA", (130, 170), (0, 0, 0, 0))
expected.alpha_composite(sprite, ((130 - sprite.width) // 2, 170 - 6 - sprite.height))
check(list(cell.getdata()) == list(expected.getdata()), "atlas Bukała cell differs from the committed Bukała source")

if failures:
    print("Bukała: FAIL")
    for failure in failures:
        print(" -", failure)
    raise SystemExit(1)
print("Bukała: PASS (display name, range dialogue, source and atlas cell)")
