"""A2 pilot (2026-10-02): generate one oak tree and one wild boar candidate from Tomek's approved anchors.

Anchors (shipped game art, no private photos): shrine_stone, cross_iron (map crops), critter bird row, Renik frame.
Run from repo root: python gen/pilot_2026-10-02/generate.py [oak] [boar]
Generation uses Codex GPT Image via gen/codex_gen.py (ChatGPT quota, no per-image API charge).
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D = Path(__file__).resolve().parent
CODEX_PY = r"C:\Users\Lenovo\AppData\Local\hermes\hermes-agent\.venv\Scripts\python.exe"
STYLE = (
    "Match exactly the art style of the reference images: genuine low-resolution game pixel art with chunky crisp "
    "square pixels, large flat color clusters, a 1 pixel dark outline, simple 2-3 step shading lit from the upper left, "
    "muted earthy village palette like the stone shrine and iron cross references. About 20 flat colors total, "
    "no anti-aliasing, no smooth gradients, no fine noise, no painted texture, no photorealism. "
    "Plain perfectly flat solid magenta #FF00FF background for removal, no ground, no cast shadow, no text."
)
JOBS = {
    "oak": dict(aspect="square", prompt=(
        "Create one single oak tree sprite for a cozy Polish village pixel-art game seen in slight top-down 3/4 view, "
        "like the shrine references. Broad rounded lobed crown made of 5-7 big leaf clumps, short thick brown trunk with "
        "small root flare, a couple of branches visible between clumps, readable silhouette at 56x52 pixels. "
        "Draw it on an approximately 56x56 pixel grid, centered, whole tree visible. " + STYLE)),
    "boar": dict(aspect="landscape", prompt=(
        "Create a sprite strip of one wild boar (European dzik) for the same pixel-art village game, side view facing right, "
        "exactly 4 frames in one horizontal row with equal spacing: walk step 1, walk step 2, standing idle, idle sniffing "
        "with snout lowered. Dark brown-grey bristly coat, lighter snout, small tusks, short legs, all frames the same size "
        "with feet on the same baseline. Each frame drawn on an approximately 48x32 pixel grid. " + STYLE)),
}
REFS = [D / "ref_shrine_stone.png", D / "ref_cross_iron.png", D / "ref_bird.png", D / "ref_renik.png"]

for name in sys.argv[1:] or list(JOBS):
    job = JOBS[name]
    args = [CODEX_PY, str(ROOT / "gen/codex_gen.py"), "--aspect", job["aspect"], "--prompt", job["prompt"],
            "--out", str(D / f"{name}_raw.png")]
    for r in REFS:
        args += ["--ref", str(r)]
    subprocess.run(args, cwd=ROOT, check=True)
