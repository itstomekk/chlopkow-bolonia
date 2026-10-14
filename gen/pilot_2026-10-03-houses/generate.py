"""Houses iteration 2 (2026-10-03): 27A rotated to the road + two more real houses (Chłopków 27, 26).

Reference packs (gen/streetview/building_refs.py) in
C:/Users/Lenovo/Hermes/image-gen/2026-10-03-chlopkow-building-refs/<name>/ : sv_sheet.jpg (all aimed Street View
frames), sat.png (north-up, OSM footprint in magenta). Per call (Codex max 4 images): SV sheet, satellite,
stone shrine anchor, and the iteration-1 27A sprite as the house camera/style anchor.

Measured orientation (OSM footprint, checked against satellite, see orientation_check.png): the road runs at
113 deg (upper-left to lower-right on the map); 27A long wall 92 deg, 27 95 deg, 26 front wall 106 deg.

    python gen/pilot_2026-10-03-houses/generate.py [job ...]   # skips jobs whose raw exists
"""
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
D = Path(__file__).resolve().parent
REF = Path(r"C:\Users\Lenovo\Hermes\image-gen\2026-10-03-chlopkow-building-refs")
CODEX_PY = r"C:\Users\Lenovo\AppData\Local\hermes\hermes-agent\.venv\Scripts\python.exe"
HOUSE_ANCHOR = D / "anchor_27A_x8.png"

FRONT = ("front-on: the south front wall is a horizontal band facing the viewer, the roof seen mostly from above "
         "behind it, east and west side walls NOT visible")
TILT = ("turned clockwise by about {deg} degrees in the top view, so the whole house (roof outline and front wall) "
        "runs diagonally from upper-left to lower-right, the right end lower, like a house standing parallel to a "
        "diagonal road. The front wall is still the one facing the viewer (south-west); it becomes a slanted band, "
        "and only a thin sliver of the west side wall may show. Keep pixel lines clean, using regular 2:1 / 3:1 "
        "pixel steps for the slanted edges")


ROAD_ANCHOR = D / "anchor_27A_road_x8.png"
ROAD = ("turned to stand parallel to the diagonal road at EXACTLY the same angle, camera and pixel treatment as the "
        "house in image 4: the roof ridge and the front wall run from upper-left to lower-right, right end lower, "
        "the front wall faces the viewer as a slanted band. Same angle for every house in this game")


def prompt(view, extra=""):
    return (
        "Image 1 is a sheet of real street photos of ONE house in the Polish village Chlopkow, showing its south "
        "(front) side from the road. Image 2 is a north-up satellite top view of the same house (footprint outlined "
        "in magenta). Image 3 is an art-style reference; image 4 is another house already made for the same game: "
        "copy its camera angle, pixel size, outline, shading and colourfulness exactly.\n"
        "Create one map-object sprite of THIS house from images 1-2: copy its storeys, roof shape and ridge, wall "
        "colour, windows, doors, porch, extensions and other features from the photos. Ignore trees, fences, cars. "
        + extra +
        "\nCamera: the game's fixed oblique view from the south, looking down at about 45 degrees. The house is "
        f"{view}. Light from the left (west): left-facing parts brighter, right parts darker. No cast shadow.\n"
        "Style: genuine low-resolution game pixel art, chunky crisp square pixels, large flat colour clusters, "
        "1 pixel dark outline, 2-3 step shading, cheerful and more colourful than the photos but in the real colour "
        "family, about 24 flat colours, no anti-aliasing, no gradients, no noise, no photorealism, no text. "
        "Draw it on an approximately 72x72 pixel grid, centered, whole house visible. "
        "Plain perfectly flat solid magenta #FF00FF background, no ground."
    )


JOBS = {
    "27A_road": dict(ref="chlopkow-27A", prompt=prompt(TILT.format(deg=21),
                     "Image 4 IS this house drawn front-on; redraw the same house, same details and colours, but "
                     "rotated as described below.")),
    "27": dict(ref="chlopkow-27", prompt=prompt(FRONT + " (the real house is within 5 degrees of east-west)")),
    "26": dict(ref="chlopkow-26", prompt=prompt(TILT.format(deg=16))),
    # iteration 3 (Tomek: variant B wins, every house along the road gets the road angle of 27A_road)
    "27_road": dict(ref="chlopkow-27", anchor=ROAD_ANCHOR, prompt=prompt(ROAD)),
    "26_road": dict(ref="chlopkow-26", anchor=ROAD_ANCHOR, prompt=prompt(ROAD)),
    "28_road": dict(ref="chlopkow-28", anchor=ROAD_ANCHOR, prompt=prompt(ROAD,
                    "These photos show the house's street side (it faces north to the road). In the game draw THAT "
                    "street side as the visible front wall, keeping its left-right layout as in the photos.")),
}


def main():
    if not HOUSE_ANCHOR.exists():
        a = Image.open(ROOT / "gen/pilot_2026-10-03-house-27A/house_82.png")
        a.resize((a.width * 8, a.height * 8), Image.Resampling.NEAREST).save(HOUSE_ANCHOR)
    if not ROAD_ANCHOR.exists() and (D / "27A_road.png").exists():
        a = Image.open(D / "27A_road.png")
        a.resize((a.width * 8, a.height * 8), Image.Resampling.NEAREST).save(ROAD_ANCHOR)
    for name in sys.argv[1:] or list(JOBS):
        out = D / f"{name}_raw.png"
        if out.exists():
            print(name, "raw exists, skip"); continue
        j = JOBS[name]; r = REF / j["ref"]
        refs = [r / "sv_sheet.jpg", r / "sat.png", ROOT / "gen/pilot_2026-10-02/ref_shrine_stone.png",
                j.get("anchor", HOUSE_ANCHOR)]
        args = [CODEX_PY, str(ROOT / "gen/codex_gen.py"), "--aspect", "square", "--prompt", j["prompt"], "--out", str(out)]
        for x in refs:
            args += ["--ref", str(x)]
        print(name, subprocess.run(args, cwd=ROOT, capture_output=True, text=True).stdout.strip())


if __name__ == "__main__":
    main()
