"""Building pilot (2026-10-03): generate one swietlica (community hall) sprite
from the Street View front photo + satellite top view + approved style anchors.

Generate -> key magenta -> drop debris -> BOX downscale -> quantize -> hard alpha
-> compare.html (photo / satellite / raw / pixel / anchors).

Run: python gen/pilot_2026-10-03-swietlica/generate.py
"""
import base64
import io
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[2]
D = Path(__file__).resolve().parent
D.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "gen"))
from build_walk_cycles import remove_magenta_background  # noqa: E402

CODEX_PY = r"C:\Users\Lenovo\AppData\Local\hermes\hermes-agent\.venv\Scripts\python.exe"
PILOT = ROOT / "gen/pilot_2026-10-02"
PHOTOS = r"C:\Users\Lenovo\Hermes\image-gen\2026-10-02-chlopkow-streetview"

STYLE = (
    "Match exactly the art style of the reference images: genuine low-resolution game pixel art with chunky crisp "
    "square pixels, large flat color clusters, a 1 pixel dark outline, simple 2-3 step shading lit from the upper left, "
    "muted earthy village palette like the stone shrine and iron cross references. About 20 flat colors total, "
    "no anti-aliasing, no smooth gradients, no fine noise, no painted texture, no photorealism. "
    "Plain perfectly flat solid magenta #FF00FF background for removal, no ground, no cast shadow, no text."
)
PROMPT = (
    "Create one single building sprite for the same cozy Polish village pixel-art game: a village community hall "
    "(swietlica wiejska) in slight top-down 3/4 view, oriented NORTH-SOUTH so its long axis runs VERTICALLY up the "
    "sprite and the sprite is TALLER than wide. Show one short gable end facing the viewer with a plain entrance, "
    "the long side wall receding upward, and the flat roof on top. Light beige plaster walls, flat dark roof, a row "
    "of evenly spaced white-framed windows along the long side wall, one small chimney. Do NOT make it wide or "
    "horizontal. Keep the simple proportions and look of the real building in the reference photo. "
    "Draw it on an approximately 60x100 pixel grid, centered, whole building visible, taller than wide. " + STYLE
)

REFS = [
    PILOT / "ref_shrine_stone.png",
    PILOT / "ref_cross_iron.png",
    PILOT / "ref_bird.png",
    PILOT / "ref_renik.png",
    Path(PHOTOS) / "landmarks/swietlica_2_d14m_yaw97.jpg",
]

W_WORLD = 43   # target width in world px (native re-pixelation, never fractional upscale)
COLORS = 24


def run_codex():
    args = [CODEX_PY, str(ROOT / "gen/codex_gen.py"), "--aspect", "portrait",
            "--prompt", PROMPT, "--out", str(D / "swietlica_raw.png")]
    for r in REFS:
        args += ["--ref", str(r)]
    print("running codex_gen ...")
    r = subprocess.run(args, cwd=ROOT)
    if r.returncode != 0:
        raise SystemExit("codex_gen failed")


def clean(raw):
    arr = np.array(remove_magenta_background(Image.open(raw)), dtype=np.uint8)
    lab, n = ndimage.label(arr[..., 3] > 0, structure=np.ones((3, 3), bool))
    if n:
        sizes = np.bincount(lab.ravel()); sizes[0] = 0
        arr[(lab > 0) & (sizes[lab] < max(60, sizes.max() * 0.01)), 3] = 0
    arr[arr[..., 3] == 0, :3] = 0
    return Image.fromarray(arr)


def pixelate(im, size, colors=COLORS):
    small = im.resize(size, Image.Resampling.BOX)
    a = np.array(small.getchannel("A")) >= 128
    rgb = small.convert("RGB").quantize(colors=colors, dither=Image.Dither.NONE).convert("RGB")
    out = np.dstack([np.array(rgb), np.where(a, 255, 0).astype(np.uint8)])
    out[~a, :3] = 0
    return Image.fromarray(out)


def b64(im, z=1):
    if z != 1:
        im = im.resize((im.width * z, im.height * z), Image.Resampling.NEAREST)
    buf = io.BytesIO(); im.convert("RGBA").save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def main():
    if not (D / "swietlica_raw.png").exists():
        run_codex()
    im = clean(D / "swietlica_raw.png")
    im = im.crop(im.getbbox())
    h = round(im.height * W_WORLD / im.width)
    out = pixelate(im, (W_WORLD, h))
    out = out.crop(out.getbbox())
    out.save(D / "swietlica.png")
    print("pixel sprite", out.size, "->", D / "swietlica.png")

    rows = [
        ("Zdjęcie referencyjne (Street View, lipiec 2024)",
         b64(Image.open(Path(PHOTOS) / "landmarks/swietlica_2_d14m_yaw97.jpg").convert("RGB"))),
        ("Widok z góry (satelita)",
         b64(Image.open(Path(PHOTOS) / "top_52.26411_22.87549_z19.png").convert("RGB"))),
        ("Surowy wynik GPT Image", b64(Image.open(D / "swietlica_raw.png").convert("RGB"))),
        ("Pixel (1 px = 1 px mapy), x4", b64(out, 4)),
        ("Wzory stylu (kapliczka, krzyż)",
         "".join(f'<img src="{b64(Image.open(PILOT / f"ref_{k}.png"))}" style="width:220px">'
                 for k in ("shrine_stone", "cross_iron"))),
    ]
    body = "".join(f"<h3>{t}</h3><img src='{s}' style='image-rendering:pixelated;max-width:100%;border:1px solid #ccc'>"
                   for t, s in rows)
    (D / "compare.html").write_text(
        "<!doctype html><meta charset=utf-8><style>body{padding:8px;background:#111;color:#eee}h3{font-size:14px;"
        "margin:16px 0 4px}</style><h2>Pilot budynku: świetlica</h2>" + body, encoding="utf-8")
    print("compare ->", D / "compare.html")


if __name__ == "__main__":
    main()
