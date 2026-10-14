"""Ask Codex Luna to list small non-building things on each yard's satellite crop (review candidates, not facts).

    STRIP=east1 python gen/streetview/yard_props_detect.py [yard ...]
Writes gen/yards/strip_<STRIP>/yard_<y>/props_luna.json: [{box:[x0,y0,x1,y1] in the 1024 sat_clean frame, title,
observation, alternatives, confidence}]. Tomek identifies them in the review sheet (gen/build_yard_review.py).
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STRIP = os.environ.get("STRIP", "east1")
OUT = ROOT / ("gen/yards/strip" if STRIP == "west" else f"gen/yards/strip_{STRIP}")
PY = Path(os.environ["LOCALAPPDATA"]) / "hermes/hermes-agent/.venv/Scripts/python.exe"
LUNA = ROOT / "gen/streetview/luna_vision.py"

Q = """Image 1: north-up satellite photo (1024x1024 px) of one farm yard in a Polish village. Image 2: the same photo with the known buildings outlined (magenta = house, cyan = farm buildings).
Task: find SMALL things on the yard that are NOT those outlined buildings and could be drawn in a pixel-art game as
small props: e.g. sheds smaller than the outlined ones, garden/greenhouse/foil tunnel, wood pile, hay or straw bales,
manure heap, sand/gravel heap, silage under foil, vehicles or machines, trailers, containers, tanks, wells,
paved/concrete yard surface, beehives, playground items, pools, chicken runs, fences/gates, single trees or bushes,
vegetable garden beds. Do NOT list the outlined buildings, the road, or open lawn/fields.
Only list things you can actually see. If unsure what something is, still list it with low confidence and say so.
Return ONLY a JSON array (max 10 items), each: {"box":[x0,y0,x1,y1] pixel box in image 1 (tight, at least 30 px),
"title":"short Polish name of the guess", "observation":"one Polish sentence what is visible",
"alternatives":["polish guess 1","polish guess 2"], "confidence":"Wysoka|Średnia|Niska"}"""


def detect(yard):
    d = OUT / f"yard_{yard}"
    out = d / "props_luna.txt"
    r = subprocess.run([str(PY), str(LUNA), str(out), Q, str(d / "sat_clean.png"), str(d / "sat_labelled.png")],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode or not out.exists():
        raise RuntimeError(f"luna failed for {yard}: {r.stderr[-800:]}")
    txt = out.read_text(encoding="utf-8")
    m = re.search(r"\[.*\]", txt, re.S)
    items = json.loads(m.group(0)) if m else []
    items = [i for i in items if len(i.get("box", [])) == 4]
    (d / "props_luna.json").write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    print(yard, len(items), "candidates:", "; ".join(i["title"] for i in items))


if __name__ == "__main__":
    yards = sys.argv[1:] or sorted(p.name[5:] for p in OUT.glob("yard_*") if (p / "sat_clean.png").exists())
    for y in yards:
        detect(y)
