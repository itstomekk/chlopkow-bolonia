"""Key, slice, scale and pack gen/poses/<id>/raw/*.png into pose atlases (candidates in gen/poses/<id>/out/).

Output: <id>_poses.png (strip of 130x190 cells, facing right), <id>_poses.json {cell, facing, poses, anims}, <id>_portrait.png, review.png.
Scale: every sheet's standing anchor is scaled to the height of the shipped walk_right frame, so all poses share one size.
Run: python gen/poses/build_poses.py <id> [<id> ...]
"""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import pose_lib as bm
CW, CH, BOTTOM, MAXW, MAXH = 130, 190, 7, 126, 180

SHEETS = {
    "talk": [["stand", "talk1", "talk2", "talk3", "talk4"], ["wave1", "wave2", "wave3", "wave4"]],
    "emote": [["_a", "laugh1", "laugh2", "laugh3", "laugh4"], ["think", "surprised", "sad", "angry"]],
    "act": [["_a", "point", "pointup", "cheer1", "cheer2"], ["sit1", "sit2", "sleep1", "sleep2"]],
    "move": [["_a", "run1", "run2", "run3", "run4"], ["jump", "hurt1", "hurt2", "ko"]],
    "work": [["_a", "dig1", "dig2", "dig3", "dig4"], ["crouch", "pickup", "throw1", "throw2"]],
}
ANIMS = {"stand": ["stand"], "talk": ["talk1", "talk2", "talk3", "talk2"], "wave": ["wave1", "wave2", "wave3", "wave4", "wave3", "wave2"],
         "laugh": ["laugh1", "laugh2", "laugh3", "laugh4"], "think": ["think"], "surprised": ["surprised"], "sad": ["sad"], "angry": ["angry"],
         "point": ["point"], "pointup": ["pointup"], "cheer": ["cheer1", "cheer2"], "sit": ["sit1", "sit2"], "sleep": ["sleep1", "sleep1", "sleep2", "sleep2"],
         "run": ["run1", "run2", "run3", "run4"], "jump": ["jump"], "hurt": ["hurt1", "hurt2"], "ko": ["ko"],
         "dig": ["dig1", "dig2", "dig3", "dig4"], "crouch": ["crouch"], "pickup": ["pickup"], "throw": ["throw1", "throw2"]}


def walk_height(cid):
    d = ROOT / "docs" / "img"
    base = f"{cid}_sheet_8dir" if (d / f"{cid}_sheet_8dir.png").exists() else f"{cid}_sheet"
    im = Image.open(d / f"{base}.png").convert("RGBA")
    jj = json.load(open(d / f"{base}.json", encoding="utf-8"))
    f = jj["anims"]["walk_right"]["frames"][0]
    a = np.asarray(im)[f["y"]:f["y"] + f["h"], f["x"]:f["x"] + f["w"], 3] > 0
    ys = np.nonzero(a.any(1))[0]
    return int(ys.max() - ys.min() + 1)


def place(fr):
    c = Image.new("RGBA", (CW, CH))
    fr = fr.crop(fr.getbbox())
    if fr.width > MAXW or fr.height > MAXH:
        s = min(MAXW / fr.width, MAXH / fr.height)
        fr = fr.resize((max(1, int(fr.width * s)), max(1, int(fr.height * s))), Image.Resampling.NEAREST)
    c.alpha_composite(fr, ((CW - fr.width) // 2, CH - BOTTOM - fr.height))
    return c


def main(cid):
    raw = HERE / cid / "raw"
    out = HERE / cid / "out"
    out.mkdir(exist_ok=True)
    stand_h = walk_height(cid)
    report = {"stand_h": stand_h}
    names, cells = [], []
    for sheet, rows in SHEETS.items():
        f = raw / f"{sheet}.png"
        if not f.exists():
            report[sheet] = "missing"
            continue
        figs = bm.figures(bm.key(Image.open(f)), [len(r) for r in rows])
        sc = stand_h / figs[0][0].height
        report[f"{sheet}_scale"] = round(sc, 3)
        for rn, rf in zip(rows, figs):
            for n, fr in zip(rn, rf):
                if n.startswith("_"):
                    continue
                names.append(n)
                cells.append(place(bm.shrink(fr, sc)))
    pal = bm.quantise(cells)
    strip = Image.new("RGBA", (CW * len(pal), CH))
    for i, c in enumerate(pal):
        strip.alpha_composite(c, (i * CW, 0))
    strip.save(out / f"{cid}_poses.png")
    anims = {k: v for k, v in ANIMS.items() if all(n in names for n in v)}
    json.dump({"cell": [CW, CH], "facing": "right", "poses": names, "anims": anims}, open(out / f"{cid}_poses.json", "w"), indent=1)
    p = raw / "portrait.png"
    if p.exists():
        pf = bm.figures(bm.key(Image.open(p)), [1])[0][0]
        pf = pf.crop(pf.getbbox())
        pf.thumbnail((124, 172), Image.Resampling.NEAREST)
        pc = Image.new("RGBA", (128, 176))
        pc.alpha_composite(pf, ((128 - pf.width) // 2, 176 - 2 - pf.height))
        pc.save(out / f"{cid}_portrait.png")
    cols = 8
    rws = (len(pal) + cols - 1) // cols
    rv = Image.new("RGBA", (cols * CW, rws * CH), (90, 110, 90, 255))
    for i, c in enumerate(pal):
        rv.alpha_composite(c, ((i % cols) * CW, (i // cols) * CH))
    rv.convert("RGB").save(out / "review.png")
    json.dump(report, open(out / "report.json", "w"), indent=1)
    print(cid, len(names), "poses", report)


if __name__ == "__main__":
    for cid in sys.argv[1:]:
        main(cid)
