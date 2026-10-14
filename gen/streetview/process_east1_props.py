"""Cut reviewed east1 Codex prop atlases into transparent pixel sprites and a non-game preview.

The user labels in plans/yard-review-east1-v1-decisions.json remain authoritative; cells are asset proposals only.
Nothing in docs/ or the game is changed.
"""
import json
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "gen/yards/strip_east1"
sys.path.insert(0, str(ROOT / "gen"))
from build_walk_cycles import remove_magenta_background

FARM = [("cart", 0, 24), ("tractor_plough", 3, 30), ("well", 4, 14), ("hot_tub", 5, 15)]
HOME = [("kennel", 0, 14), ("orchard", 1, 42), ("mirabelle", 2, 20), ("opel_astra", 3, 28), ("white_car", 4, 27)]


def cell(path, index, width):
    sheet = Image.open(path).convert("RGBA")
    cw, ch = sheet.width // 3, sheet.height // 2
    x, y = index % 3, index // 3
    im = remove_magenta_background(sheet.crop((x*cw, y*ch, (x+1)*cw, (y+1)*ch)))
    alpha = np.asarray(im.getchannel("A")) > 0
    lab, n = ndimage.label(alpha, structure=np.ones((3, 3)))
    if not n: raise ValueError(f"Empty sprite cell {index} from {path}")
    sizes = np.bincount(lab.ravel()); sizes[0] = 0
    keep = np.zeros_like(alpha)
    for i in range(1, n+1):
        if sizes[i] >= max(5, sizes.max() * .008): keep |= lab == i
    a = np.asarray(im).copy(); a[~keep, 3] = 0; a[~keep, :3] = 0
    rgba = Image.fromarray(a); rgba = rgba.crop(rgba.getbbox())
    small = rgba.resize((width, max(4, round(rgba.height * width / rgba.width))), Image.Resampling.LANCZOS)
    arr = np.asarray(small).copy(); mask = arr[...,3] >= 128
    rgb = Image.fromarray(arr[...,:3]).quantize(colors=32, dither=Image.Dither.NONE).convert("RGB")
    result = np.asarray(rgb.convert("RGBA")).copy(); result[...,3] = np.where(mask,255,0); result[~mask,:3] = 0
    return Image.fromarray(result)


def standalone(path, width):
    im = remove_magenta_background(Image.open(path).convert("RGBA"))
    im = im.crop(im.getbbox())
    im = im.resize((width, max(4, round(im.height * width / im.width))), Image.Resampling.LANCZOS)
    arr = np.asarray(im).copy(); mask = arr[...,3] >= 128
    rgb = Image.fromarray(arr[...,:3]).quantize(colors=32, dither=Image.Dither.NONE).convert("RGB")
    result = np.asarray(rgb.convert("RGBA")).copy(); result[...,3] = np.where(mask,255,0); result[~mask,:3] = 0
    return Image.fromarray(result)


def main():
    assets = {}
    for filename, specs in [("props_atlas_farm_raw.png", FARM), ("props_atlas_home_raw.png", HOME)]:
        for name, index, width in specs:
            im = cell(OUT / filename, index, width)
            (OUT / "props").mkdir(exist_ok=True)
            im.save(OUT / "props" / f"{name}.png", optimize=True); assets[name] = im
    for name, raw_name, width in [("tin_shelter", "props_tinshelter_raw.png", 32), ("workshop", "props_workshop_raw.png", 34)]:
        im = standalone(OUT / raw_name, width)
        im.save(OUT / "props" / f"{name}.png", optimize=True); assets[name] = im
    assets["hedge"] = Image.open(ROOT / "docs/img/j12_prop_hedge.png").convert("RGBA")

    uses = [
        ("cart", "east1-19-p1", "wóz na słomę pusty"),
        ("tin_shelter", "east1-19-p2", "wiata blaszana"),
        ("workshop", "east1-19-p3", "warsztat"),
        ("hedge", "east1-19-p4", "żywopłot"),
        ("orchard", "east1-19-p5", "drzewka iglaste po prawej a po lewej czeresnie"),
        ("tractor_plough", "east1-19-p6", "maszyny gospodarcze, traktor, pług"),
        ("well", "east1-19-p7", "studnia"),
        ("opel_astra", "east1-20-p2", "opel astra"),
        ("hot_tub", "east1-20-p4", "balia do gorącej kąpieli"),
        ("well", "east1-20-p5", "studnia"),
        ("white_car", "east1-22-p1", "auto biale"),
        ("well", "east1-22-p3", "studnia"),
        ("mirabelle", "east1-22-p5", "drzewka z mirabelkami"),
        ("kennel", "east1-E1-p5", "kojec dla psa"),
    ]
    decision_path = ROOT / "plans/yard-review-east1-v1-decisions.json"
    raw = json.loads(decision_path.read_text(encoding="utf-8")); decisions = raw["decisions"]
    provenance = {p["id"]: p for p in raw["provenance"]}
    data = {"sourceReview": "yard-review-east1-v1", "gameChangesApplied": False,
            "identificationSource": "user-supplied review; literal values preserved", "assets": {}, "props": []}
    for name, im in assets.items():
        data["assets"][name] = {"file": f"gen/yards/strip_east1/props/{name}.png", "size": list(im.size),
                                "source": "Codex gpt-image-2-medium" if name != "hedge" else "reused reviewed J12 sprite"}
    for name, cid, label in uses:
        d = decisions[cid]
        if d["decision"] != "add" or d["identification"] != label:
            raise ValueError(f"Decision mismatch; do not normalize: {cid}: {d['identification']!r}")
        point = provenance[cid]["mapPointApprox"]
        if cid == "east1-19-p4":   # merge the same continuous hedge seen in the adjacent yard-20 crop
            other = provenance["east1-20-p3"]["mapPointApprox"]
            point = [round((a+b)/2) for a,b in zip(point, other)]
        data["props"].append({"id": f"{cid}:{name}", "candidate": cid, "kind": name,
                              "x": point[0], "y": point[1], "identification": label, "status": "preview-only"})
    (OUT / "props/placements_preview.json").write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    names = list(assets); tilew,tileh=220,190
    sheet=Image.new("RGB",(3*tilew,((len(names)+2)//3)*tileh),(36,42,42)); draw=ImageDraw.Draw(sheet)
    for i,name in enumerate(names):
        im=assets[name]; x=(i%3)*tilew; y=(i//3)*tileh
        bg=Image.new("RGBA",(tilew-12,tileh-34),(83,111,74,255)); s=im.copy()
        s.thumbnail((tilew-34,tileh-70),Image.Resampling.NEAREST)
        bg.alpha_composite(s,((bg.width-s.width)//2,(bg.height-s.height)//2)); sheet.paste(bg.convert("RGB"),(x+6,y+26))
        draw.text((x+8,y+7),name,fill="white")
    sheet.save(OUT / "props_sprites_preview.png")
    compare = Image.open(ROOT / "gen/pilot_2026-10-03-houses/compare_east1.png").convert("RGBA")
    box = (860, 3870, 1180, 4400); factor = 3
    panel_h = (box[3]-box[1])*factor; panel_top = 2*(panel_h+26)+26
    scene = compare.crop((0,panel_top,box[2]-box[0],panel_top+panel_h))
    d = ImageDraw.Draw(scene)
    for i,p in enumerate(sorted(data["props"],key=lambda p:(p["y"],p["x"])),1):
        sprite=assets[p["kind"]].resize((assets[p["kind"]].width*factor,assets[p["kind"]].height*factor),Image.Resampling.NEAREST)
        x=round((p["x"]-box[0])*factor-sprite.width/2); y=round((p["y"]-box[1])*factor-sprite.height)
        scene.alpha_composite(sprite,(x,y))
        cx=round((p["x"]-box[0])*factor); cy=round((p["y"]-box[1])*factor)
        d.rectangle((cx-9,cy-9,cx+9,cy+9),fill="#14201a",outline="#ffe078",width=2)
        d.text((cx-4,cy-6),str(i),fill="#ffe078")
    scene.convert("RGB").save(OUT / "props_map_mockup.png")
    print(json.dumps({"assets":{n:list(v.size) for n,v in assets.items()},"props":len(data["props"]),
                      "sprites_preview":str(OUT/"props_sprites_preview.png"),
                      "map_mockup":str(OUT/"props_map_mockup.png")},ensure_ascii=False,indent=2))

if __name__ == "__main__": main()
