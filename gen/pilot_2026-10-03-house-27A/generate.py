"""House pilot (2026-10-03): Chłopków 27A (OSM way 909988193) from real references.

References passed straight to GPT Image (max 4 images per call):
  1. refs_streetview.jpg  all 4 aimed Street View frames of the house (south facade, July 2024), one sheet
  2. sat.png              north-up satellite crop, magenta = OSM footprint
  3-4. style anchors      gen/pilot_2026-10-02/ref_shrine_stone.png, ref_cross_iron.png
Source frames: C:/Users/Lenovo/Hermes/image-gen/2026-10-03-chlopkow-building-refs/chlopkow-27A/
(made by gen/streetview/building_refs.py 909988193 <dir>).

Camera/light contract copied from osm/render_map.py (procedural houses): north up, viewed from the south,
roof seen mostly from above, only the south wall is visible below it, light from the west (left walls/slopes
brighter), ground shadow falls to the south-east and is drawn by the map, not the sprite.

    python gen/pilot_2026-10-03-house-27A/generate.py      # generates raw only if missing
"""
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
D = Path(__file__).resolve().parent
REF = Path(r"C:\Users\Lenovo\Hermes\image-gen\2026-10-03-chlopkow-building-refs\chlopkow-27A")
PILOT = ROOT / "gen/pilot_2026-10-02"
CODEX_PY = r"C:\Users\Lenovo\AppData\Local\hermes\hermes-agent\.venv\Scripts\python.exe"

PROMPT = (
    "Image 1 is a sheet of four real street photos of ONE house in the Polish village Chlopkow, all showing its "
    "south (front) side from the road. Image 2 is a north-up satellite top view of the same house, its footprint "
    "outlined in magenta. Images 3 and 4 are the art-style references.\n"
    "Create one map-object sprite of THIS house for a cozy pixel-art village game. Copy the real house: its "
    "storeys, roof shape and ridge direction from the satellite, wall colour, window and balcony layout, the lower "
    "extension with solar panels, as seen in the photos. Ignore the trees, fences and cars in the photos.\n"
    "Camera: the game's fixed oblique view from the south, the same for every building: we look down at about "
    "45 degrees, the roof is seen mostly from above and the south front wall is visible below it, front-on and "
    "not rotated; east and west side walls are NOT visible. Light comes from the left (west): left-facing parts "
    "brighter, right parts darker. No cast shadow.\n"
    "Style: match images 3 and 4 exactly: genuine low-resolution game pixel art, chunky crisp square pixels, large "
    "flat colour clusters, 1 pixel dark outline, 2-3 step shading. Make it cheerful and more colourful than the "
    "photos: saturated warm roof, clean bright walls, colourful flower boxes, but keep the real colour family. "
    "About 24 flat colours, no anti-aliasing, no gradients, no noise, no photorealism, no text. "
    "Draw it on an approximately 64x64 pixel grid, centered, whole house visible. "
    "Plain perfectly flat solid magenta #FF00FF background, no ground."
)


def sheet():
    fs = sorted(REF.glob("sv_*.jpg"))
    s = Image.new("RGB", (1200, 800), (0, 0, 0))
    for i, f in enumerate(fs[:4]):
        s.paste(Image.open(f).convert("RGB").resize((600, 400)), ((i % 2) * 600, (i // 2) * 400))
    ImageDraw.Draw(s).line([(600, 0), (600, 800)], fill=(255, 255, 255), width=3)
    ImageDraw.Draw(s).line([(0, 400), (1200, 400)], fill=(255, 255, 255), width=3)
    s.save(D / "refs_streetview.jpg", quality=90)
    return D / "refs_streetview.jpg"


def main():
    if (D / "house_raw.png").exists():
        print("raw exists, skip generation"); return
    refs = [sheet(), REF / "sat.png", PILOT / "ref_shrine_stone.png", PILOT / "ref_cross_iron.png"]
    args = [CODEX_PY, str(ROOT / "gen/codex_gen.py"), "--aspect", "square", "--prompt", PROMPT,
            "--out", str(D / "house_raw.png")]
    for r in refs:
        args += ["--ref", str(r)]
    subprocess.run(args, cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
