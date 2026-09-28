"""Append procedural pixel-art wild-animal rows to the runtime critter atlas."""
import json
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
img_path = ROOT / "docs/img/critters.png"
meta_path = ROOT / "docs/img/critters.json"
CELL = 64


def frame(kind, phase):
    im = Image.new("RGBA", (CELL, CELL), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    bob = phase % 2
    if kind == "boar":
        d.rectangle((13, 31 + bob, 47, 48 + bob), fill="#493831")
        d.rectangle((37, 27 + bob, 55, 43 + bob), fill="#5f473a")
        d.rectangle((49, 37 + bob, 59, 44 + bob), fill="#30262a")
        d.rectangle((43, 25 + bob, 48, 31 + bob), fill="#684b3d")
        d.rectangle((47, 24 + bob, 52, 29 + bob), fill="#30262a")
        d.rectangle((26, 45 + bob, 31, 57), fill="#33282a")
        d.rectangle((40, 45 + bob, 45, 57), fill="#33282a")
        d.rectangle((55, 39 + bob, 58, 42 + bob), fill="#e5bea0")
        d.point((48, 33 + bob), fill="#f7e6c4")
    elif kind == "mouse":
        d.ellipse((14, 33 + bob, 43, 49 + bob), fill="#86746c")
        d.ellipse((35, 27 + bob, 51, 43 + bob), fill="#9b857b")
        d.ellipse((38, 24 + bob, 45, 31 + bob), fill="#d29c9b")
        d.rectangle((48, 35 + bob, 55, 39 + bob), fill="#27232a")
        d.line((16, 43 + bob, 5, 48 + bob, 1, 44 + bob), fill="#a68c82", width=2)
        d.point((48, 33 + bob), fill="#1e1b22")
    elif kind == "pig":
        d.rectangle((11, 33 + bob, 46, 49 + bob), fill="#d48691")
        d.rectangle((37, 27 + bob, 55, 44 + bob), fill="#e19aa2")
        d.rectangle((49, 36 + bob, 59, 43 + bob), fill="#b86270")
        d.rectangle((43, 25 + bob, 48, 31 + bob), fill="#e19aa2")
        d.rectangle((47, 24 + bob, 52, 29 + bob), fill="#c47783")
        d.rectangle((24, 46 + bob, 29, 57), fill="#a95f6c")
        d.rectangle((39, 46 + bob, 44, 57), fill="#a95f6c")
        d.rectangle((54, 38 + bob, 58, 42 + bob), fill="#5e3841")
        d.point((48, 33 + bob), fill="#5e3841")
    else:
        d.rectangle((14, 34 + bob, 43, 50 + bob), fill="#996947")
        d.rectangle((35, 28 + bob, 52, 44 + bob), fill="#b47b50")
        d.rectangle((39, 18 + bob, 44, 32 + bob), fill="#b47b50")
        d.rectangle((46, 16 + bob, 51, 32 + bob), fill="#b47b50")
        d.rectangle((49, 34 + bob, 55, 38 + bob), fill="#28232a")
        d.rectangle((19, 47 + bob, 24, 58), fill="#704c3c")
        d.rectangle((37, 47 + bob, 42, 58), fill="#704c3c")
        d.point((49, 32 + bob), fill="#1e1b22")
    return im


def main():
    old = Image.open(img_path).convert("RGBA")
    rows = ["boar", "mouse", "hare", "pig"]
    missing = [kind for kind in rows if kind not in meta_rows(meta_path)]
    out = Image.new("RGBA", (old.width, old.height + len(missing) * CELL), (0, 0, 0, 0))
    out.alpha_composite(old)
    for row, kind in enumerate(missing):
        for phase in range(4):
            out.alpha_composite(frame(kind, phase), (phase * CELL, old.height + row * CELL))
    out.save(img_path, optimize=True)
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    start = len(meta["rows"])
    for row, kind in enumerate(missing, start=start):
        meta["rows"][kind] = {"row": row, "frames": ["walk1", "walk2", "idle", "idle2"], "h": {"boar": 44, "mouse": 18, "hare": 28, "pig": 42}[kind]}
    meta_path.write_text(json.dumps(meta, indent=1) + "\n", encoding="utf-8")
    print(f"wild critters: {out.size[0]}x{out.size[1]}, rows={','.join(rows)}")


def meta_rows(path):
    return json.loads(path.read_text(encoding="utf-8"))["rows"]


if __name__ == "__main__":
    main()
