#!/usr/bin/env python3
"""Build a numbered KOSTEK concept review sheet from raw GPT Image outputs.

Each raw image holds three standing views (front, side, back) on magenta.
The three largest magenta-keyed components are cropped, regridded with BOX to
75 px content height, hard-alpha'd and upscaled 2x NEAREST (the BERCIK recipe),
then shown next to BERCIK's front frame for in-game scale.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[2]
CHARACTERS = {
    "kostek": ("KOSTEK", [
        ("1", "kostek_v1_hoodie_vest.png", "Hoodie + bezrękawnik, jeansy, telefon"),
        ("2", "kostek_v2_summer_tank.png", "Lato: kremowy tank z czerwonym lamowaniem"),
        ("3", "kostek_v3_black_tee.png", "Twardziel: czarny t-shirt, ciemne jeansy"),
        ("4", "kostek_v4_farm_work.png", "Gospodarz: bezrękawnik, kalosze, rękawice"),
    ]),
    "pawel": ("PAWEŁ", [
        ("1", "pawel_v1_gingham_shirt.png", "Koszula w kratkę, pasek, ciemne spodnie"),
        ("2", "pawel_v2_jacket_teal_tee.png", "Brązowa kurtka + morski t-shirt, zarost"),
        ("3", "pawel_v3_olive_sweater.png", "Zima: oliwkowy sweter, ręce skrzyżowane"),
        ("4", "pawel_v4_farm_bucket.png", "Gospodarz: sweter, kalosze, wiadro"),
    ]),
    "kostek-r2": ("KOSTEK runda 2 (twarz z 3, bez zarostu, łagodniejszy)", [
        ("5", "kostek_v5_overalls_white_tee.png", "Zielone ogrodniczki + biały t-shirt"),
        ("6", "kostek_v6_overalls_flannel.png", "Ciemnozielone ogrodniczki + flanela, kalosze"),
        ("3", "kostek_v3_black_tee.png", "(dla porównania) opcja 3: Twardziel"),
    ]),
    "darek": ("DAREK (170 cm: 70 px zamiast 75)", [
        ("5", "darek_v5_slim_suit.png", "Szczupły, żel: kremowy garnitur, fioletowy krawat"),
        ("6", "darek_v6_slim_white_shirt.png", "Szczupły, żel: biała koszula, chinosy"),
        ("7", "darek_v7_slim_painter.png", "Szczupły, żel: lakiernik, kombinezon, pistolet"),
        ("8", "darek_v8_slim_pink.png", "Szczupły, żel: różowa koszula, aviatory"),
    ]),
    "darek-r1": ("DAREK runda 1 (odrzucona: za tęgi)", [
        ("1", "darek_v1_cream_suit.png", "Elegancko: kremowy garnitur, fioletowy krawat"),
        ("2", "darek_v2_white_shirt.png", "Smart casual: biała koszula, chinosy, mokasyny"),
        ("3", "darek_v3_painter_coverall.png", "Lakiernik: biały kombinezon, pistolet lakierniczy"),
        ("4", "darek_v4_pink_aviators.png", "Wakacje: różowa koszula, aviatory, czapka tyłem"),
    ]),
}
FOLDERS = {"kostek-r2": "kostek", "darek-r1": "darek"}
HEIGHTS = {"darek": 70, "darek-r1": 70}
CHARACTER = sys.argv[1] if len(sys.argv) > 1 else "kostek"
TITLE, VARIANTS = CHARACTERS[CHARACTER]
CONCEPTS = ROOT / f"gen/{FOLDERS.get(CHARACTER, CHARACTER)}/concepts"
CONTENT_H = HEIGHTS.get(CHARACTER, 75)


def key_figures(path: Path) -> list[Image.Image]:
    rgba = np.asarray(Image.open(path).convert("RGBA"), dtype=np.uint8).copy()
    r, g, b = (rgba[..., i].astype(np.int32) for i in range(3))
    magenta = (r > 150) & (b > 130) & (g < 130) & (np.abs(r - b) < 110)
    fringe = (r > 105) & (b > 90) & (g < r - 35) & (g < b - 30)
    bg = ndimage.binary_propagation(
        np.pad(np.zeros((rgba.shape[0] - 2, rgba.shape[1] - 2), bool), 1, constant_values=True) & magenta,
        structure=np.ones((3, 3), bool), mask=magenta)
    bg |= ndimage.binary_dilation(bg, iterations=3) & fringe
    # Magenta enclosed between an arm and the body is not border-connected.
    holes, hole_count = ndimage.label(magenta & ~bg, structure=np.ones((3, 3), bool))
    if hole_count:
        hole_sizes = np.bincount(holes.ravel())
        big = np.flatnonzero(hole_sizes >= 40)
        bg |= np.isin(holes, big[big != 0])
        bg |= ndimage.binary_dilation(bg, iterations=2) & fringe
    rgba[bg, 3] = 0
    mask = rgba[..., 3] > 0
    labels, count = ndimage.label(mask, structure=np.ones((3, 3), bool))
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0
    slices = ndimage.find_objects(labels)
    biggest = sorted((int(lab) for lab in np.argsort(sizes)[::-1][:3]), key=lambda lab: slices[lab - 1][1].start)
    figures = []
    for lab in biggest:
        main = labels == lab
        near = ndimage.binary_dilation(main, iterations=6)
        keep = main.copy()
        for other in range(1, count + 1):
            if other not in biggest and sizes[other] >= 8 and np.any((labels == other) & near):
                keep |= labels == other
        arr = rgba.copy()
        arr[~keep, 3] = 0
        img = Image.fromarray(arr, "RGBA")
        img = img.crop(img.getchannel("A").getbbox())
        w = max(1, round(img.width * CONTENT_H / img.height))
        small = np.asarray(img.resize((w, CONTENT_H), Image.Resampling.BOX)).copy()
        small[..., 3] = np.where(small[..., 3] >= 128, 255, 0)
        small[small[..., 3] == 0, :3] = 0
        figures.append(Image.fromarray(small, "RGBA").resize((w * 2, CONTENT_H * 2), Image.Resampling.NEAREST))
    return figures


def main() -> None:
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 20)
    small_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 14)
    bercik = Image.open(ROOT / "docs/img/bercik_sheet.png").crop((0, 0, 130, 170))
    bb = bercik.getchannel("A").getbbox()
    bercik = bercik.crop(bb)
    row_h, raw_w = 330, 520
    sheet = Image.new("RGBA", (raw_w + 4 * 170 + 60, 40 + row_h * len(VARIANTS)), (226, 224, 214, 255))
    draw = ImageDraw.Draw(sheet)
    draw.text((16, 10), f"{TITLE} - koncepty (raw | front / bok / tył w skali gry 2x | BERCIK dla skali)", fill=(20, 20, 20), font=font)
    report = {}
    for i, (num, name, label) in enumerate(VARIANTS):
        y0 = 40 + i * row_h
        draw.rectangle((6, y0 + 4, sheet.width - 7, y0 + row_h - 4), outline=(90, 90, 84), fill=(238, 236, 228))
        raw = Image.open(CONCEPTS / name).convert("RGBA")
        thumb = raw.copy()
        thumb.thumbnail((raw_w - 30, row_h - 60))
        sheet.alpha_composite(thumb, (20, y0 + 44))
        draw.text((20, y0 + 12), f"{num}. {label}", fill=(160, 20, 20), font=font)
        figs = key_figures(CONCEPTS / name)
        x = raw_w + 10
        base = y0 + row_h - 24
        for fig in figs + [bercik]:
            sheet.alpha_composite(fig, (x + (160 - fig.width) // 2, base - fig.height))
            x += 170
        draw.text((raw_w + 10 + 3 * 170 + 40, base + 2), "BERCIK", fill=(60, 60, 60), font=small_font)
        report[num] = {"raw": name, "raw_size": list(raw.size), "figures": [list(f.size) for f in figs]}
    out = CONCEPTS / f"{CHARACTER}_concepts_review.png"
    sheet.convert("RGB").save(out, optimize=True)
    print(json.dumps(report, indent=2), out)


if __name__ == "__main__":
    main()
