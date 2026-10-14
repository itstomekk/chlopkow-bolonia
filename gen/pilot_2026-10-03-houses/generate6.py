"""Iteration 6 (2026-10-03): complete yard of Chłopków 28 + Chłopków 29 redone in the natural game projection.

Tomek, iteration 5: the shear trick looks flat/unnatural. Rotation must be drawn by GPT in the same projection as
the other houses (anchor 27A_road); the angle is chosen relative to the building's road / house.
  yard_28_L : 909988358, L-shaped outbuilding south of house 28, satellite 92 deg = same as house 28
              -> same orientation as house 28 = road angle, like anchor 27A_road
  29_v3     : satellite walls 11/101 deg; its access road runs N-S, so the house is almost square to its road:
              a light clockwise turn, about half of the anchor's, same projection; satellite-only, plain walls

    python gen/pilot_2026-10-03-houses/generate6.py [job ...]
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D = Path(__file__).resolve().parent
REF = Path(r"C:\Users\Lenovo\Hermes\image-gen\2026-10-03-chlopkow-building-refs")
CODEX_PY = r"C:\Users\Lenovo\AppData\Local\hermes\hermes-agent\.venv\Scripts\python.exe"
STYLE = ("Style: genuine low-resolution game pixel art, chunky crisp square pixels, large flat colour clusters, 1 pixel "
         "dark outline, 2-3 step shading, cheerful colours, about 20 flat colours, no anti-aliasing, no gradients, no "
         "noise, no photorealism, no text. Plain perfectly flat solid magenta #FF00FF background, no ground, no shadow.")
PROJ = ("Use EXACTLY the same projection as image 4: the game's oblique top-down 3/4 view, roof seen mostly from above, "
        "the front wall visible below it with real depth, the same camera height and the same 3D look. Light from the "
        "left (west).")
ANCHOR = D / "anchor_27A_road_x8.png"
SHRINE = ROOT / "gen/pilot_2026-10-02/ref_shrine_stone.png"

JOBS = {
    "yard28_L": dict(
        refs=[REF / "w909988358/sv_sheet.jpg", REF / "w909988358/sat.png", SHRINE, ANCHOR],
        prompt=("Image 1: street photos towards a farm yard in the Polish village Chlopkow (the outbuilding is behind "
                "the house, mostly hidden). Image 2: north-up satellite view; the farm building at the centre (magenta "
                "outline) is L-shaped, about 13 m long and 8 m deep with a shorter wing, single storey. Image 3: style "
                "reference. Image 4: the main house of the same yard, already made for the game.\nDraw this L-shaped "
                "farm building (barn / cowshed / storage) as one sprite: roof shape and colour as on the satellite, plain "
                "farm walls, one or two wide wooden doors. It stands at the SAME orientation as the house in image 4 "
                "(ridge running upper-left to lower-right, right end lower). " + PROJ + " Fits about 64x52 pixels. "
                + STYLE)),
    "29_v3": dict(
        refs=[REF / "w909988194/sat.png", REF / "w909988194/sat_wide.png", SHRINE, ANCHOR],
        prompt=("Images 1-2: north-up satellite views (close, wide) of ONE house in the Polish village Chlopkow; there "
                "are no street photos. Image 3: style reference. Image 4: another house of the same game.\nDraw this "
                "house as one sprite. Draw ONLY what the satellite shows: roof shape and ridge, roof colour, chimneys, "
                "annexes and their size. The walls are plain neutral light plaster with NO windows, NO doors, NO stairs, "
                "NO balcony, NO plants. Single storey. Orientation: only slightly turned clockwise, about HALF as much "
                "as the house in image 4 (ridge almost horizontal, right end a little lower). " + PROJ +
                " Fits about 89x78 pixels. " + STYLE)),
}


def main():
    for name in sys.argv[1:] or list(JOBS):
        out = D / f"{name}_raw.png"
        if out.exists():
            print(name, "raw exists, skip"); continue
        j = JOBS[name]
        args = [CODEX_PY, str(ROOT / "gen/codex_gen.py"), "--aspect", "square", "--prompt", j["prompt"], "--out", str(out)]
        for x in j["refs"]:
            args += ["--ref", str(x)]
        for attempt in range(2):
            res = subprocess.run(args, cwd=ROOT, capture_output=True, text=True).stdout.strip()
            if '"ok": true' in res: break
        print(name, res[-110:])


if __name__ == "__main__":
    main()
