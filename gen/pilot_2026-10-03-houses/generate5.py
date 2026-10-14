"""Iteration 5 (2026-10-03): farm behind 27A at its satellite angle, Chłopków 29 conservative + satellite angle.

Angles are measured on the satellite (edge histogram + guide-line overlay, angle_check_farm27A_29.png), not taken
from OSM: the OSM footprints here are axis-aligned import templates.
  farm behind 27A: long wall at 117 deg (27 deg clockwise from east-west), about the road angle -> 27A_road anchor
  Chłopków 29: walls at 11 / 101 deg -> drawn front-on here, the exact 11 deg tilt is applied afterwards by a
               vertical shear (process5.py), which GPT cannot hit reliably for small angles

    python gen/pilot_2026-10-03-houses/generate5.py [job ...]
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
CAM = ("Camera: the game's fixed oblique view from the south, looking down at about 45 degrees; roof seen mostly from "
       "above, the front wall below it. Light from the left (west).")

JOBS = {
    "farm_behind27A_v2": dict(
        refs=[REF / "w909989345/sv_sheet.jpg", REF / "w909989345/sat.png",
              ROOT / "gen/pilot_2026-10-02/ref_shrine_stone.png", D / "anchor_27A_road_x8.png"],
        prompt=("Image 1: street photos of a farm yard in the Polish village Chlopkow (the outbuilding may be hidden). "
                "Image 2: north-up satellite view; the outbuilding at the centre is a simple rectangle about 11.5 m long "
                "and 5.7 m deep, its long side running at 117 degrees, i.e. turned clockwise like the house in image 4. "
                "Image 3: style reference. Image 4: a house from the same game; copy its camera, rotation angle, pixel "
                "size and shading EXACTLY.\nDraw this outbuilding (shed/garage) as one sprite: low single storey, simple "
                "gable roof in the roof colour seen on the satellite, plain walls, one wide shed door. The building runs "
                "from upper-left to lower-right at exactly the same angle as image 4, right end lower. Fits about "
                "86x50 pixels. " + CAM + " " + STYLE)),
    "29_sat_v2": dict(
        refs=[REF / "w909988194/sat.png", REF / "w909988194/sat_wide.png",
              ROOT / "gen/pilot_2026-10-02/ref_shrine_stone.png", ROOT / "gen/pilot_2026-10-03-houses/anchor_27A_x8.png"],
        prompt=("Images 1-2: north-up satellite views (close, wide) of ONE house in the Polish village Chlopkow; there "
                "are no street photos. Image 3: style reference. Image 4: a house from the same game drawn front-on; "
                "copy its camera, pixel size, outline and shading.\nDraw this house FRONT-ON, not rotated (the rotation "
                "is added later). Draw ONLY what the satellite shows: the roof shape and ridge, roof colour, chimneys, "
                "roof extensions or annexes and their size. Below the roof show a plain wall band of a neutral light "
                "plaster colour with NO windows, NO doors, NO stairs, NO balcony, NO plants or flower boxes, NO details "
                "that cannot be seen from above. Single storey. Fits about 89x75 pixels. " + CAM + " " + STYLE)),
    "farm_behind27A_front": dict(
        refs=[REF / "w909989345/sv_sheet.jpg", REF / "w909989345/sat.png",
              ROOT / "gen/pilot_2026-10-02/ref_shrine_stone.png", ROOT / "gen/pilot_2026-10-03-houses/anchor_27A_x8.png"],
        prompt=("Image 1: street photos of a farm yard in the Polish village Chlopkow (the outbuilding may be hidden). "
                "Image 2: north-up satellite view; the outbuilding at the centre is a simple rectangle about 11.5 m long "
                "and 5.7 m deep. Image 3: style reference. Image 4: a house from the same game drawn front-on; copy its "
                "camera, pixel size, outline and shading. Draw this outbuilding FRONT-ON, not rotated (the rotation is "
                "added later): low single storey, simple gable roof in the roof colour seen on the satellite, plain walls, "
                "one wide shed door. Fits about 86x45 pixels. " + CAM + " " + STYLE)),
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
        print(name, subprocess.run(args, cwd=ROOT, capture_output=True, text=True).stdout.strip()[-110:])


if __name__ == "__main__":
    main()
