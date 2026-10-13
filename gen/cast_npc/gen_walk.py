#!/usr/bin/env python3
"""Walk sheets for the NPC cast so they can be playable (Tomek, 2026-10-13: "all characters selectable").

Identity reference = the NPC's own in-game sprite (gen/npc_src, the same art packed into docs/img/npcs.png),
never private photos. Layout/style template = gen/bercik/bercik_walkcycle_raw.png (4x2 BERCIK grid on magenta).
Raw -> gen/cast_npc/<id>/<id>_walkcycle_raw.png, then gen/build_cast_walk.py builds the 130x170 sheet.

    python gen/cast_npc/gen_walk.py [id ...]          # generate missing raws (4 parallel) and build sheets
    python gen/cast_npc/gen_walk.py --force kasia     # regenerate
"""
from __future__ import annotations

import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = r"C:/Users/Lenovo/AppData/Local/hermes/hermes-agent/.venv/Scripts/python.exe"
TEMPLATE = ROOT / "gen/bercik/bercik_walkcycle_raw.png"
NPC_ATLAS_ORDER = ['kasia', 'marcin', 'damian', 'grandpa', 'irenka', 'kuba', 'michal', 'mateusz', 'patryk',
                   'zbyszek', 'wesoly_swiat', 'edytka', 'renik', 'soltys']   # gen/build_npcs.py ORDER

# game id -> (source sprite in gen/npc_src, short look description that keeps the outfit readable)
CAST = {
    'kasia': ('kasia', 'KASIA, a young woman from the village'),
    'grandpa': ('grandpa', 'DZIADEK ZDZISIEK, an elderly grandfather'),
    'halina': ('irenka', 'BABCIA IRENKA, an elderly grandmother'),
    'kuba': ('kuba', 'KUBA, a young man from the village'),
    'soltys': ('soltys_raw', 'the SOŁTYS (village head), a middle-aged man'),
    'michal': ('bukala', 'BUKAŁA, a man from the village'),
    'mateusz': ('mateusz', 'MATEUSZ, a young man from the village'),
    'patryk': ('patryk', 'PATRYK, a young man from the village'),
    'wesoly_swiat': ('wesoly_swiat', 'WESOŁYCH ŚWIĄT, a festive village character'),
}

PROMPT = ("Image 1 is the layout and style template: a 4x2 grid of eight chunky low-resolution pixel-art walking "
          "figures on a pure magenta background. Redraw the grid with exactly the same layout, order, scale, cell "
          "spacing, pixel size and art style, but replace the character with {who}, the character shown in image 2. "
          "Keep his or her look from image 2 exactly: face, hair, body shape, age, every piece of clothing, colours "
          "and accessories. Layout: row 1 = walk down A, walk down B, walk right A, walk right B; row 2 = walk up A, "
          "walk up B, walk left A, walk left B. Exactly eight isolated complete equal-scale figures with clear "
          "alternating steps, front/back/true side profiles; the back view shows the back of the same outfit. "
          "Chunky pixel art around 75px content height, 1px dark outline, compact proportions with a fairly large "
          "head like the template, 2-3 shading steps, 24-32 colours, upper-left light. Pure flat magenta background, "
          "no text, no ground, no shadows, no checkerboard, no overlapping cells.")


def reference(cid: str, src: str) -> Path:
    """Identity ref on a flat light background, about 1000 px tall (tiny pixel sprites scaled up with NEAREST)."""
    from PIL import Image
    im = Image.open(ROOT / f"gen/npc_src/{src}.png").convert("RGBA")
    if im.getchannel("A").getextrema()[0] < 255:
        im = im.crop(im.getchannel("A").getbbox())
    scale = 1000 / im.height
    im = im.resize((max(1, round(im.width * scale)), 1000), Image.NEAREST if im.height < 400 else Image.LANCZOS)
    canvas = Image.new("RGBA", (im.width + 160, 1160), (226, 224, 214, 255))
    canvas.alpha_composite(im, (80, 80))
    path = ROOT / f"gen/cast_npc/{cid}/{cid}_identity_ref.png"
    canvas.convert("RGB").save(path)
    return path


def generate(cid: str, force: bool) -> str:
    src, who = CAST[cid]
    out = ROOT / f"gen/cast_npc/{cid}"
    out.mkdir(parents=True, exist_ok=True)
    raw = out / f"{cid}_walkcycle_raw.png"
    if raw.exists() and not force:
        return f"{cid}: raw exists"
    ref = reference(cid, src)
    r = subprocess.run([PY, str(ROOT / "gen/codex_gen.py"), "--ref", str(TEMPLATE), "--ref", str(ref),
                        "--aspect", "landscape", "--prompt", PROMPT.format(who=who), "--out", str(raw)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    (out / "gen_log.json").write_text((r.stdout + r.stderr)[-2000:], encoding="utf-8")
    return f"{cid}: gen exit {r.returncode} {r.stdout.strip()[-160:]}"


def build(cid: str) -> str:
    out = ROOT / f"gen/cast_npc/{cid}"
    r = subprocess.run([sys.executable, str(ROOT / "gen/build_cast_walk.py"), "build", "--name", cid,
                        "--raw", str(out / f"{cid}_walkcycle_raw.png"), "--out", str(out), "--height", "75",
                        "--provider", f"openai-codex gpt-image-2-medium ({cid} walk from npc_src)"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=ROOT)
    return f"{cid}: build exit {r.returncode} {(r.stdout + r.stderr).strip()[-200:]}"


def main() -> None:
    args = sys.argv[1:]
    force = "--force" in args
    ids = [a for a in args if not a.startswith("--")] or list(CAST)
    with ThreadPoolExecutor(4) as pool:
        for line in pool.map(lambda c: generate(c, force), ids):
            print(line, flush=True)
    for cid in ids:
        if (ROOT / f"gen/cast_npc/{cid}/{cid}_walkcycle_raw.png").exists():
            print(build(cid), flush=True)


if __name__ == "__main__":
    main()
