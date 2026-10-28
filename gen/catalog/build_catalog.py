"""World-element catalog for review (Tomek 2026-10-27): every non-character visual with an ID, so comments can say 'T03 too big'.
Writes gen/catalog/out/<section>.png + catalog.json (id -> source). Re-run: python gen/catalog/build_catalog.py"""
import json, random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
ROOT = Path(__file__).resolve().parents[2]; D = ROOT / "docs" / "img"; OUT = Path(__file__).with_name("out"); OUT.mkdir(exist_ok=True)
F = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 15); FS = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 12); FH = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 26)
CELL = 190; BG = (226, 224, 214); CATALOG = {}
MAP = json.load(open(ROOT / "docs/map.json", encoding="utf-8")); OBJ = None


def trim(im):
    im = im.convert("RGBA"); b = im.getbbox(); return im.crop(b) if b else im


def sheet(name, title, tiles, cols=6):
    rows = (len(tiles) + cols - 1) // cols; S = Image.new("RGB", (cols * CELL, rows * (CELL + 38) + 50), BG); d = ImageDraw.Draw(S)
    d.text((10, 10), title, font=FH, fill=(0, 0, 0))
    for k, (tid, label, im, src) in enumerate(tiles):
        im = trim(im); x, y = (k % cols) * CELL, 50 + (k // cols) * (CELL + 38)
        z = max(1, min(6, (CELL - 20) // max(im.width, 1), (CELL - 20) // max(im.height, 1)))
        g = im.resize((im.width * z, im.height * z), Image.NEAREST)
        if g.width > CELL - 10 or g.height > CELL - 10:
            s = min((CELL - 10) / g.width, (CELL - 10) / g.height); g = g.resize((max(1, int(g.width * s)), max(1, int(g.height * s))), Image.NEAREST)
        S.paste(g, (x + (CELL - g.width) // 2, y + CELL - 8 - g.height), g)
        d.rectangle((x + 2, y + 2, x + CELL - 3, y + CELL + 34), outline=(190, 188, 176))
        d.text((x + 8, y + CELL - 4 + 0), f"{tid}", font=F, fill=(0, 0, 0)); d.text((x + 8, y + CELL + 14), f"{label} {im.width}x{im.height}", font=FS, fill=(70, 70, 70))
        CATALOG[tid] = dict(label=label, native=[im.width, im.height], zoom=z, source=src, sheet=f"{name}.png")
    S.save(OUT / f"{name}.png"); print(name, len(tiles), S.size)


def objcrop(o):
    global OBJ
    if OBJ is None: OBJ = Image.open(D / "map_objects.png").convert("RGBA")
    return OBJ.crop((o["x"], o["y"], o["x"] + o["w"], o["y"] + o["h"]))


def pick(lst, n, seed):
    lst = sorted(lst, key=lambda o: o["w"] * o["h"]); return [lst[int(i * (len(lst) - 1) / max(1, n - 1))] for i in range(n)] if len(lst) > n else lst


objs = MAP["objects"]
# 1 trees
dec = pick([o for o in objs if o.get("species") == "deciduous"], 12, 1); oak = pick([o for o in objs if o.get("species") == "oak"], 6, 2)
tiles = [(f"T{i+1:02d}", "drzewo liściaste", objcrop(o), f"map.json objects x={o['x']} y={o['y']}") for i, o in enumerate(dec)]
tiles += [(f"T{i+13:02d}", "dąb (zatwierdzony sprite)", objcrop(o), f"map.json objects x={o['x']} y={o['y']}") for i, o in enumerate(oak)]
terr = Image.open(D / "map_terrain.png").convert("L"); gnd = Image.open(D / "map_ground.png").convert("RGBA"); rnd = random.Random(7); got = 0; tries = 0
while got < 4 and tries < 4000:
    tries += 1; x, y = rnd.randrange(60, terr.width - 60), rnd.randrange(60, terr.height - 60)
    if all(terr.getpixel((x + dx, y + dy)) >= 200 for dx in (-30, 0, 30) for dy in (-30, 0, 30)):
        got += 1; X, Y = x * 4, y * 4; tiles.append((f"T{18+got:02d}", "las iglasty (wycinek tła)", gnd.crop((X - 70, Y - 70, X + 70, Y + 70)), f"map_ground.png @{X},{Y}"))
sheet("1_trees", "1. DRZEWA (T01-T22): liściaste, dęby, las", tiles)
# 2 buildings
yb = pick([o for o in objs if o.get("kind") == "yard_building"], 8, 3); gb = pick([o for o in objs if "kind" not in o and o["w"] >= 40 and o["h"] >= 30 and o["w"] <= 200], 10, 4)
tiles = [(f"B{i+1:02d}", "budynek z podwórka", objcrop(o), f"map.json yard_building way={o['way']}") for i, o in enumerate(yb)]
tiles += [(f"B{i+9:02d}", "budynek / obiekt mapy", objcrop(o), f"map.json objects x={o['x']} y={o['y']}") for i, o in enumerate(gb)]
for i, p in enumerate(sorted((ROOT / "gen").glob("lm_*.png"))):
    if any(s in p.stem for s in ("raw", "keyed", "v1", "v2")): continue
    tiles.append((f"B{len(tiles)+1:02d}", p.stem.replace("lm_", "punkt: "), Image.open(p), f"gen/{p.name}"))
sheet("2_buildings", "2. BUDYNKI i PUNKTY (B..): domy, stodoły, kościół, sklep, kapliczki", tiles)
# 3 props
tiles = []
PFX = "P"
def add(pid, label, im, src): tiles.append((f"{PFX}{len(tiles)+1:02d}", label, im, src))
add(0, "bela siana", Image.open(D / "hay_bale.png"), "img/hay_bale.png")
for n, l in (("bale", "bela (podwórko)"), ("hedge", "żywopłot"), ("shrub", "krzew"), ("silo", "silos"), ("truck", "ciężarówka")): add(0, l, Image.open(D / f"j12_prop_{n}.png"), f"img/j12_prop_{n}.png")
tr = Image.open(D / "trash.png"); names = json.load(open(D / "trash.json"))["names"]
for i, n in enumerate(names): add(0, f"śmieć: {n}", tr.crop((i * 32, 0, i * 32 + 32, 32)), "img/trash.png")
for p in sorted((D / "church").glob("*.png")): add(0, f"kościół: {p.stem}", Image.open(p), f"img/church/{p.name}")
for p in sorted((D / "memories").glob("*.png")): add(0, f"cmentarz: {p.stem}", Image.open(p), f"img/memories/{p.name}")
sheet("3_props", "3. REKWIZYTY (P..): bele, żywopłot, śmieci, kościół, cmentarz", tiles)
# 4 vehicles + animals
tiles = []; PFX = "V"
vj = json.load(open(D / "vehicles.json")); vi = Image.open(D / "vehicles.png").convert("RGBA"); c = vj["cell"]
for n, r in vj["rows"].items(): add(0, f"pojazd: {n}", vi.crop((0, r["row"] * c, c, r["row"] * c + c)), "img/vehicles.png")
add(0, "samochód czerwony", Image.open(D / "car_red.png"), "img/car_red.png")
cj = json.load(open(D / "critters.json")); ci = Image.open(D / "critters.png").convert("RGBA"); c = cj["cell"]
for n, r in cj["rows"].items(): add(0, f"zwierzę: {n}", ci.crop((0, r["row"] * c, c, r["row"] * c + c)), "img/critters.png")
an = Image.open(D / "animals.png").convert("RGBA")
add(0, "świnia", an.crop((0, 0, 110, 90)), "img/animals.png"); add(0, "pies (wiejski)", an.crop((0, 90, 110, 180)), "img/animals.png")
add(0, "żubr", Image.open(D / "bison.png").convert("RGBA").crop((0, 0, 96, 80)), "img/bison.png")
add(0, "Frodo (pies)", Image.open(D / "frodo.png").convert("RGBA").crop((0, 0, 32, 32)), "img/frodo.png"); add(0, "Wajper (pies)", Image.open(D / "wajper.png").convert("RGBA").crop((0, 0, 32, 32)), "img/wajper.png")
sheet("4_vehicles_animals", "4. POJAZDY i ZWIERZĘTA (V..): traktor, auta, zwierzęta, psy", tiles)
json.dump(CATALOG, open(OUT / "catalog.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
