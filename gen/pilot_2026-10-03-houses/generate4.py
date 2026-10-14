"""Iteration 4 (2026-10-03): thicker 28/26, first farm buildings, first satellite-only house.

Rules applied (plans/asset-style-guide.md, Real buildings 11-14):
  angle   every building of a roadside plot takes the road angle (anchor 27A_road), farm buildings keep their
          real orientation relative to the house
  size    W = length along the road x 7.5 px/m;  H = depth x 7.5 x 1.1 x 0.75 + 12 + 6 per extra storey
          (1.1 = real roofs are deeper than the OSM template outline). The raw is fitted into (W, H) exactly.
  refs    Street View sheet + satellite + shrine anchor + 27A_road anchor; satellite-only: sat + sat_wide + anchors

    python gen/pilot_2026-10-03-houses/generate4.py [job ...]     # skips jobs whose raw exists
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D = Path(__file__).resolve().parent
REF = Path(r"C:\Users\Lenovo\Hermes\image-gen\2026-10-03-chlopkow-building-refs")
CODEX_PY = r"C:\Users\Lenovo\AppData\Local\hermes\hermes-agent\.venv\Scripts\python.exe"
ANCHOR = D / "anchor_27A_road_x8.png"
PXM = 7.5


def size(length, depth, storeys=1):
    return round(length * PXM), round(depth * PXM * 1.1 * 0.75 + 12 + 6 * (storeys - 1))


# name: (ref dir, osm way, length along road m, depth m, storeys, kind, extra)
JOBS = {
    "28_v2": ("chlopkow-28", 909988191, 11.5, 10.2, 1, "house",
              "These photos show the house's street side (it faces north to the road); draw THAT side as the front wall."),
    "26_v2": ("chlopkow-26", 909988213, 9.6, 8.5, 1, "house", ""),
    "farm_behind28": ("w909988763", 909988763, 6.9, 17.2, 1, "farm", ""),
    "farm_behind27A": ("w909989345", 909989345, 11.5, 5.7, 1, "farm", ""),
    "farm_behind27": ("w909988457", 909988457, 4.2, 20.0, 1, "farm", ""),
    "29_sat": ("w909988194", 909988194, 11.9, 11.2, 1, "satellite", ""),
}


def prompt(name, job):
    _, _, length, depth, storeys, kind, extra = job
    w, h = size(length, depth, storeys)
    deep = "long side along the road" if length >= depth else "long side perpendicular to the road"
    if kind == "satellite":
        intro = ("Images 1 and 2 are north-up satellite top views (close and wide) of ONE house in the Polish village "
                 "Chlopkow; its footprint is outlined in magenta. There are no street photos: take the roof shape, "
                 "ridge, roof colour and footprint from the satellite and invent plausible simple walls, windows and "
                 "a door typical for a rural Polish house of that size.")
    else:
        what = "farm building (barn / shed / garage)" if kind == "farm" else "house"
        intro = (f"Image 1 is a sheet of real street photos of the plot of ONE {what} in the Polish village Chlopkow "
                 "(it may be partly hidden behind trees or the house in front of it). Image 2 is a north-up satellite "
                 "top view of it, footprint outlined in magenta. Copy the real building: roof shape, ridge, roof and "
                 "wall colours, doors, windows, extensions, as far as visible. Ignore trees, fences, cars. " + extra)
    if length >= depth:
        view = ("turned to stand parallel to the diagonal road at EXACTLY the angle of the house in image 4: ridge and "
                "front wall run from upper-left to lower-right, right end lower, front wall facing the viewer as a "
                "slanted band")
    else:
        view = ("a long narrow building whose long axis is PERPENDICULAR to the diagonal road of image 4: we see its "
                "short gable end as the front wall facing the viewer, and its long roof recedes away from the viewer, "
                "leaning slightly to the right, rotated consistently with image 4")
    return (
        intro + " Image 3 is an art-style reference; image 4 is a house already made for the same game: copy its "
        "camera angle, pixel size, outline, shading and colourfulness exactly.\n"
        f"Camera: the game's fixed oblique view from the south, looking down at about 45 degrees. The building is "
        f"{view} ({deep}). The roof is DEEP as on the satellite: the real roof is nearly as deep as it is long "
        f"(length {length} m, depth {depth} m), do not flatten it. Light from the left (west). No cast shadow.\n"
        "Style: genuine low-resolution game pixel art, chunky crisp square pixels, large flat colour clusters, "
        "1 pixel dark outline, 2-3 step shading, cheerful and more colourful than the photos but in the real colour "
        "family, about 24 flat colours, no anti-aliasing, no gradients, no noise, no photorealism, no text. "
        f"The whole sprite fits a box of about {w}x{h} pixels (width x height), centered, whole building visible. "
        "Plain perfectly flat solid magenta #FF00FF background, no ground."
    )


def main():
    for name in sys.argv[1:] or list(JOBS):
        out = D / f"{name}_raw.png"
        if out.exists():
            print(name, "raw exists, skip"); continue
        job = JOBS[name]; r = REF / job[0]
        refs = ([r / "sat.png", r / "sat_wide.png"] if job[5] == "satellite" else [r / "sv_sheet.jpg", r / "sat.png"])
        refs += [ROOT / "gen/pilot_2026-10-02/ref_shrine_stone.png", ANCHOR]
        args = [CODEX_PY, str(ROOT / "gen/codex_gen.py"), "--aspect", "square", "--prompt", prompt(name, job),
                "--out", str(out)]
        for x in refs:
            args += ["--ref", str(x)]
        print(name, size(*job[2:5]), subprocess.run(args, cwd=ROOT, capture_output=True, text=True).stdout.strip()[-120:])


if __name__ == "__main__":
    main()
