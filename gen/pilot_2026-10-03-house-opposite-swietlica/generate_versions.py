"""Chlopkow 3 (house opposite the swietlica) - multiple generation approaches.

Each job = one distinct approach. Same projection/angle contract everywhere
(oblique 3/4 like anchor 27A_road, light from the west, magenta bg, no ground
shadow). Only the treatment differs, so Tomek can pick the approach.

    python gen/pilot_2026-10-03-house-opposite-swietlica/generate_versions.py [job ...]
"""
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
D = Path(__file__).resolve().parent
SHRINE = ROOT / "gen/pilot_2026-10-02/ref_shrine_stone.png"
ANCHOR = ROOT / "gen/pilot_2026-10-03-houses/anchor_27A_road_x8.png"
CODEX_PY = r"C:\Users\Lenovo\AppData\Local\hermes\hermes-agent\.venv\Scripts\python.exe"

STYLE = ("Style: genuine low-resolution game pixel art, chunky crisp square pixels, large flat colour clusters, "
         "1 pixel dark outline, 2-3 step shading, about 20 flat colours, no anti-aliasing, no gradients, no noise, "
         "no photorealism, no text. Plain perfectly flat solid magenta #FF00FF background, no ground, no shadow.")
PROJ = ("Use EXACTLY the same projection as image 4: the game's oblique top-down 3/4 view, roof seen mostly from "
        "above, the front wall visible below it with real depth, same camera height, same 3D look. Light from the "
        "left (west). Ridge runs almost vertical (north-south).")


def sheet():
    out = D / "sv_sheet.jpg"
    if out.exists():
        return out
    frames = sorted(D.glob("sv_*.jpg"))
    assert frames, "no sv frames; run building_refs.py first"
    ims = [Image.open(f).convert("RGB") for f in frames]
    w = max(i.width for i in ims); h = max(i.height for i in ims)
    grid = Image.new("RGB", (w * 2, h * 2), (0, 0, 0))
    for k, im in enumerate(ims):
        im = im.resize((w, h))
        grid.paste(im, ((k % 2) * w, (k // 2) * h))
    grid.save(out, quality=90)
    return out


SV = sheet()
SAT = D / "sat.png"

JOBS = {
    "photo": dict(
        refs=[SV, SAT, SHRINE, ANCHOR],
        prompt=("Image 1: street photos of one detached house in the Polish village Chlopkow (address 3, opposite "
                "the community hall). Image 2: north-up satellite view with the house footprint outlined. Image 3: "
                "style reference. Image 4: another house of the same game, already made (the projection + style to "
                "copy). Draw THIS house as one sprite, faithful to the photo: same wall colour, same roof colour and "
                "shape, the windows and door as in the photos, the road-facing wall shown as the front. "
                + PROJ + " Fits about 65x58 pixels. " + STYLE)),
    "cheerful": dict(
        refs=[SV, SAT, SHRINE, ANCHOR],
        prompt=("Image 1: street photos of one detached house in the Polish village Chlopkow (address 3). Image 2: "
                "north-up satellite. Image 3: style reference. Image 4: another house of the same game (projection + "
                "style to copy). Draw THIS house as one sprite, but MORE COLOURFUL and cheerful than the photos while "
                "staying in the same colour family: warmer roof, brighter plaster, a touch more contrast on the "
                "windows. Same layout as the photos. " + PROJ + " Fits about 65x58 pixels. " + STYLE)),
    "plain": dict(
        refs=[SAT, D / "sat_wide.png", SHRINE, ANCHOR],
        prompt=("Images 1-2: north-up satellite views (close, wide) of ONE house in Chlopkow; there are no street "
                "photos. Image 3: style reference. Image 4: another house of the same game. Draw this house as one "
                "sprite, drawing ONLY what the satellite shows: roof shape, ridge, roof colour, chimneys, annexes. "
                "Plain neutral light-plaster walls with NO windows, NO doors, NO plants. "
                + PROJ + " Fits about 65x58 pixels. " + STYLE)),
    "warm": dict(
        refs=[SV, SAT, SHRINE, ANCHOR],
        prompt=("Image 1: street photos of one detached house in Chlopkow (address 3). Image 2: north-up satellite. "
                "Image 3: style reference. Image 4: another house of the same game (projection + style to copy). Draw "
                "THIS house as one sprite in a warm afternoon light: strong light from the west, clear warm highlights "
                "on the western wall and roof, soft but visible 2-3 step shading, richer warm palette. Same layout as "
                "the photos. " + PROJ + " Fits about 65x58 pixels. " + STYLE)),
}


def main():
    for name in sys.argv[1:] or list(JOBS):
        out = D / f"{name}_raw.png"
        if out.exists():
            print(name, "raw exists, skip"); continue
        j = JOBS[name]
        args = [CODEX_PY, str(ROOT / "gen/codex_gen.py"), "--aspect", "square",
                "--prompt", j["prompt"], "--out", str(out)]
        for x in j["refs"]:
            args += ["--ref", str(x)]
        res = subprocess.run(args, cwd=ROOT, capture_output=True, text=True).stdout.strip()
        print(name, "->", res[-140:])


if __name__ == "__main__":
    main()
