#!/usr/bin/env python3
"""Redesign walk sheets (Tomek 2026-10-27): WESOŁYCH ŚWIĄT from a real photo (approved for Codex, never in git),
KASIA without the cowboy outfit (student), MATEUSZ as a student (no litter picking).

Refs: 1 = BERCIK 4x2 layout template, 2 = style canon (Arek/Iwona/Halina: line weight, chunkiness, head+hand size),
3 = identity (photo / old sprite for the face only / none).
    python gen/cast_npc/gen_redo.py <id> [<id> ...]      # 2 variants each -> gen/cast_npc/<id>/redo_<v>_raw.png
"""
from __future__ import annotations
import subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANON_ROOT = Path("C:/Users/Lenovo/Hermes/projects/games/arek-w-chlopkowie")   # references/ lives only in the canonical checkout
PY = r"C:/Users/Lenovo/AppData/Local/hermes/hermes-agent/.venv/Scripts/python.exe"
TEMPLATE = ROOT / "gen/bercik/bercik_walkcycle_raw.png"
CANON = ROOT / "gen/style_canon/canon_ref.png"

BASE = ("Image 1 is the layout template: a 4x2 grid of eight chunky low-resolution pixel-art walking figures on a pure magenta "
        "background. Image 2 is the STYLE CANON (Arek, Iwona, Halina): copy its bold dark outline weight, big chunky pixel blocks, "
        "flat 2-3 step shading and especially its generous head size and chunky hands: the head must be about one third of the body "
        "height, hands and feet clearly readable, never a thin or fine-pixelated figure. Redraw the Image 1 grid with exactly the "
        "same layout, order, scale, cell spacing and pixel size, but with {who}. {look} "
        "Layout: row 1 = walk down A, walk down B, walk right A, walk right B; row 2 = walk up A, walk up B, walk left A, walk left B. "
        "Exactly eight isolated complete equal-scale figures with clear alternating steps, front/back/true side profiles; the back view "
        "shows the back of the same outfit. Chunky pixel art around 75px content height, 24-32 colours, upper-left light. "
        "Pure flat magenta #FF00FF background, no text, no ground, no shadows, no checkerboard, no overlapping cells.")

CAST = {
    "wesoly_swiat": dict(
        ident=CANON_ROOT / "references/wesoly_swiat/wesoly_swiat_ref.png",
        who="WESOŁYCH ŚWIĄT, the older man shown in Image 3 (a photo)",
        looks=["Copy his face, age, weathered lined skin, short grey hair, green baseball cap with small emblem and the heavy plaid flannel overshirt in red, brown, cream and maroon from the photo; dark trousers, sturdy boots. Friendly, slightly stocky.",
               "Same man as the photo in Image 3: green cap, plaid red/brown/cream flannel overshirt, weathered face, short grey hair, dark work trousers and boots, hands in the pockets while walking."]),
    "kasia": dict(
        ident=ROOT / "gen/npc_src/kasia.png",
        who="KASIA, a young woman who is now a university student (Image 3 is her OLD sprite: keep ONLY her face and long brown hair)",
        looks=["Replace the whole outfit: NO cowboy hat, NO vest, NO skirt, NO boots, NO bag strap from the old sprite. New outfit: oversized cream knit sweater, light blue jeans, white sneakers, a canvas backpack on both shoulders, long brown hair loose.",
               "Replace the whole outfit: NO cowboy hat, NO pink, NO skirt, NO boots. New outfit: short denim jacket over a striped t-shirt, dark jeans, white sneakers, a tote bag with books on one shoulder, long brown hair in a ponytail."]),
    "mateusz": dict(
        ident=None,
        who="MATEUSZ, a young male university student",
        looks=["Short messy dark-brown hair, round glasses, grey zip hoodie, blue jeans, white sneakers, a green backpack on both shoulders, headphones around the neck. NO high-visibility vest, NO trash bag, NO litter grabber.",
               "Short messy dark-brown hair, no glasses, olive bomber jacket over a white t-shirt, black jeans, sneakers, a laptop bag across the chest, a notebook in one hand. NO high-visibility vest, NO trash bag, NO litter grabber."]),
}


def run(job):
    cid, v = job
    c = CAST[cid]; out = ROOT / f"gen/cast_npc/{cid}"; out.mkdir(parents=True, exist_ok=True)
    raw = out / f"redo_{v}_raw.png"
    if raw.exists():
        return f"{cid}/{v}: exists"
    cmd = [PY, str(ROOT / "gen/codex_gen.py"), "--ref", str(TEMPLATE), "--ref", str(CANON)]
    if c["ident"]:
        cmd += ["--ref", str(c["ident"])]
    cmd += ["--aspect", "landscape", "--out", str(raw), "--prompt", BASE.format(who=c["who"], look=c["looks"][v])]
    for _ in range(3):
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        (out / f"redo_{v}.log").write_text((r.stdout + r.stderr)[-1500:], encoding="utf-8")
        if r.returncode == 0 and raw.exists():
            return f"{cid}/{v}: ok"
    return f"{cid}/{v}: FAILED {(r.stdout + r.stderr)[-200:]}"


if __name__ == "__main__":
    ids = sys.argv[1:] or list(CAST)
    jobs = [(i, v) for i in ids for v in (0, 1)]
    with ThreadPoolExecutor(3) as ex:
        for line in ex.map(run, jobs):
            print(line, flush=True)
