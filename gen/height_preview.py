#!/usr/bin/env python3
"""Before/after preview of per-character real heights (height_cm) on the real map.

Before: every sheet drawn at CHAR_H=40 world px (current game.js rule).
After:  draw height = CHAR_H * height_cm / 180 (AREK 180 cm keeps today's size).
Frames use the same source rectangle and scale rule as game.js
(scale = h / (f.h - foot - 14)), feet on one ground line, over a real map crop.
Heights marked "?" are placeholders until Tomek confirms them.
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
CHAR_H = 40
FONT = "C:/Windows/Fonts/arial.ttf"

# (label, sheet json, height_cm, confirmed)
CAST = [
    ("AREK", "docs/img/arek_sheet.json", 180, True),
    ("MARCIN", "docs/img/marcin_sheet.json", 180, False),
    ("DAMIAN", "docs/img/damian_sheet.json", 180, False),
    ("EDYTKA", "docs/img/edytka_sheet.json", 165, False),
    ("RENIK", "docs/img/renik_sheet.json", 180, False),
    ("WIESIO", "docs/img/wiesio_sheet.json", 180, False),
    ("BERCIK", "docs/img/bercik_sheet.json", 170, False),
    ("KOSTEK", "gen/kostek/walk/kostek_sheet.json", 181, False),
    ("PAWEŁ", "gen/pawel/walk_face_a/pawel_sheet.json", 181, False),
    ("DAREK", "gen/darek/walk_face_h/darek_sheet.json", 170, True),
]
PIXEL = {"BERCIK", "WIESIO", "KOSTEK", "PAWEŁ", "DAREK"}


def front_frame(json_path: Path) -> tuple[Image.Image, dict, dict]:
    meta = json.loads(json_path.read_text(encoding="utf-8"))
    sheet = Image.open(json_path.parent / meta["image"]).convert("RGBA")
    anims = meta["anims"]
    key = next(k for k in anims if k.endswith("down")) if any(k.endswith("down") for k in anims) else next(iter(anims))
    frame = anims[key]["frames"][0]
    cell = sheet.crop((frame["x"], frame["y"], frame["x"] + frame["w"], frame["y"] + frame["h"]))
    return cell, frame, meta


def draw_row(world: Image.Image, ground_y: int, heights: list[int]) -> Image.Image:
    out = world.copy()
    x = 22
    for (label, path, _, _), height in zip(CAST, heights):
        cell, frame, meta = front_frame(ROOT / path)
        h = CHAR_H * height / 180
        scale = h / (frame["h"] - meta.get("foot", 0) - 14)
        w, hh = max(1, round(frame["w"] * scale)), max(1, round(frame["h"] * scale))
        resample = Image.Resampling.NEAREST if label in PIXEL else Image.Resampling.LANCZOS
        sprite = cell.resize((w, hh), resample)
        foot = round(meta.get("foot", 0) * scale)
        out.alpha_composite(sprite, (x - w // 2, ground_y + foot - hh))
        x += 34
    return out


def main() -> None:
    ground = Image.open(ROOT / "docs/img/map_ground.png").convert("RGBA")
    objects = Image.open(ROOT / "docs/img/map_objects.png").convert("RGBA")
    box = (4760, 5800, 5130, 5940)  # sector J12 near BERCIK's NPC spot, with a yard
    world = ground.crop(box)
    world.alpha_composite(objects.crop(box))
    ground_y = 112
    before = draw_row(world, ground_y, [180] * len(CAST))
    after = draw_row(world, ground_y, [c[2] for c in CAST])

    zoom = 3
    W, H = world.width * zoom, world.height * zoom
    canvas = Image.new("RGBA", (W + 40, 2 * H + 150), (226, 224, 214, 255))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(FONT, 22)
    small = ImageFont.truetype(FONT, 15)
    for i, (title, img) in enumerate((("TERAZ: wszyscy 40 px mapy", before), ("PO: wzrost w cm (AREK 180 cm = dzisiejszy rozmiar)", after))):
        y0 = 10 + i * (H + 70)
        draw.text((20, y0), title, fill=(150, 20, 20) if i else (20, 20, 20), font=font)
        canvas.alpha_composite(img.resize((W, H), Image.Resampling.NEAREST), (20, y0 + 32))
        for j, (label, _, cm, ok) in enumerate(CAST):
            cx = 20 + (22 + j * 34) * zoom
            text = label if i == 0 else f"{label} {cm}{'' if ok else '?'}"
            draw.text((cx - 28, y0 + 32 + H + 2), text, fill=(20, 20, 20), font=small)
    out = ROOT / "gen/cast_review/2026-10-12_height_cm_before_after.png"
    canvas.convert("RGB").save(out, optimize=True)
    print(out, canvas.size)


if __name__ == "__main__":
    main()
