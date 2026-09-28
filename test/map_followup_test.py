"""Map follow-up checks for the relocated Sołtys, northern forest and football pitch."""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, "osm")
from geo import P, pre_expansion_i  # noqa: E402

URL = os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html")
MAP = json.load(open("docs/map.json", encoding="utf-8"))
ITEMS = json.load(open("docs/items.json", encoding="utf-8"))
COLLIDE = np.array(Image.open("docs/img/map_collide.png").convert("L"))


def geometry_mask(predicate, line_width=14):
    mask = Image.new("L", (MAP["w"], MAP["h"]), 0)
    draw = ImageDraw.Draw(mask)
    osm = json.load(open("osm/chlopkow.json", encoding="utf-8"))
    for element in osm["elements"]:
        tags = element.get("tags", {})
        if element.get("type") != "way" or "geometry" not in element or not predicate(tags):
            continue
        points = [P(g["lat"], g["lon"]) for g in element["geometry"]]
        if tags.get("waterway") in ("stream", "river", "ditch", "canal"):
            draw.line(points, fill=255, width=line_width, joint="curve")
        elif len(points) > 2:
            draw.polygon(points, fill=255)
    return np.array(mask) > 0


def northern_forest_point():
    forest = geometry_mask(lambda t: t.get("landuse") in ("forest", "wood") or t.get("natural") in ("forest", "wood"))
    yy, xx = np.indices(forest.shape)
    forest &= (yy >= 50) & (yy < MAP["h"] // 2) & (xx >= 40) & (xx < MAP["w"] - 40)   # the world border is solid by design
    # Pick a deep interior point, avoiding a boundary or a road crossing.
    from scipy import ndimage
    distance = ndimage.distance_transform_edt(forest)
    y, x = np.unravel_index(int(distance.argmax()), distance.shape)
    assert distance[y, x] >= 10, "no usable northern forest interior"
    return int(x), int(y)


def solid_water_point():
    water = geometry_mask(lambda t: t.get("natural") == "water" or t.get("waterway") in ("stream", "river", "ditch", "canal"))
    ys, xs = np.nonzero(water & (COLLIDE > 0))
    assert len(xs), "no colliding water sample"
    return int(xs[len(xs) // 2]), int(ys[len(ys) // 2])


soltys = next(n for n in ITEMS["npcs"] if n["id"] == "soltys")
boards = ITEMS["boards"]
target = pre_expansion_i(1887, 1237)
assert math.dist((soltys["x"], soltys["y"]), target) <= 180, (soltys, target)
assert all(math.dist((soltys["x"], soltys["y"]), (b["x"], b["y"])) > 45 for b in boards), soltys
assert any(p["key"] == "church" for p in MAP["pois"]), "church outdoor POI disappeared"

pitch_base = pre_expansion_i(2339, 1468)
pitch = MAP["football_pitch"]
assert (pitch["cx"], pitch["cy"], pitch["w"], pitch["h"]) == (*[pitch_base[0] + 200, pitch_base[1] + 200], 110, 190), pitch
pitch_landmark = next(l for l in MAP["landmarks"] if l["key"] == "football_pitch")
assert (pitch_landmark["x"], pitch_landmark["y"]) == (pitch["cx"], pitch["cy"]), pitch_landmark
pitch_item = next(l for l in ITEMS["landmarks"] if l["key"] == "football_pitch")

forest_point = northern_forest_point()
water_point = solid_water_point()

with sync_playwright() as playwright:
    browser = playwright.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 720})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(URL)
    page.wait_for_function("window.__game", timeout=30000)
    page.keyboard.press("Enter")
    page.wait_for_timeout(250)
    assert page.evaluate("p => !__game.blocked(p[0], p[1])", list(forest_point)), forest_point
    assert page.evaluate("p => __game.blocked(p[0], p[1])", list(water_point)), water_point
    assert page.evaluate("l => !__game.blocked(l.access.x, l.access.y)", pitch_item), pitch_item
    assert not errors, errors
    print("map follow-up OK", "soltys", soltys, "forest", forest_point, "water", water_point, "pitch", pitch)
    browser.close()
