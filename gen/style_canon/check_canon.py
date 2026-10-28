"""Quick canon check for a shipped/candidate walk sheet: height 150, <=40 colours, hard alpha, head width.
python gen/style_canon/check_canon.py <id> [<id> ...]   (reads docs/img/<id>_sheet.png)"""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image
D = Path(__file__).resolve().parents[2] / "docs" / "img"
bad = 0
for cid in sys.argv[1:]:
    p = D / (f"{cid}_sheet_8dir.png" if (D / f"{cid}_sheet_8dir.png").exists() else f"{cid}_sheet.png")
    im = Image.open(p).convert("RGBA"); m = json.load(open(p.with_suffix(".json")))
    f = m["anims"]["walk_down"]["frames"][0]
    c = im.crop((f["x"], f["y"], f["x"] + f["w"], f["y"] + f["h"])); c = c.crop(c.getbbox()); a = np.array(c); al = a[..., 3]
    cols = len(np.unique(a[al > 0][:, :3], axis=0)); soft = int(((al > 0) & (al < 255)).sum()); H = c.height
    head = int((al[:H // 4] > 0).sum(1).max())
    flags = [x for x, ok in (("height", 125 <= H <= 165), ("colours>40", cols <= 40), ("soft alpha", soft == 0), ("head<50px", head >= 50)) if not ok]
    bad += bool(flags); print(f"{cid}: h={H} colours={cols} soft_alpha={soft} head_w={head}", "OK" if not flags else "FLAGS " + ",".join(flags))
sys.exit(1 if bad else 0)
