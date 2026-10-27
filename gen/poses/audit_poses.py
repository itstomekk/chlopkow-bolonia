"""Audit gen/poses/<id>/out: per-pose empty/edge-touching/duplicate/odd-scale checks + contact sheets (contact_N.png, ignored).
Run: python gen/poses/audit_poses.py"""
import json, os
from pathlib import Path
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ids = sorted(p.parent.parent.name for p in HERE.glob("*/out/review.png"))
print(len(ids), "characters")
bad = 0
for cid in ids:
    j = json.load(open(HERE / cid / "out" / f"{cid}_poses.json"))
    im = np.asarray(Image.open(HERE / cid / "out" / f"{cid}_poses.png"))
    W, H = j["cell"]
    issues, hs = [], {}
    for i, n in enumerate(j["poses"]):
        c = im[:, i * W:(i + 1) * W, 3] > 0
        ys, xs = np.nonzero(c)
        if len(ys) == 0:
            issues.append(n + ":empty"); continue
        if xs.min() == 0 or xs.max() == W - 1 or ys.min() == 0:
            issues.append(n + ":edge")
        hs[n] = int(ys.max() - ys.min() + 1)
        if i and (im[:, i * W:(i + 1) * W] == im[:, (i - 1) * W:i * W]).all():
            issues.append(n + ":dup")
    st = hs.get("stand", 1)
    odd = [n for n in ("talk1", "run1", "cheer1", "dig1", "laugh1", "point") if n in hs and not 0.7 < hs[n] / st < 1.5]
    portrait = (HERE / cid / "out" / f"{cid}_portrait.png").exists()
    if issues or odd or not portrait or len(j["poses"]) != 41:
        bad += 1
    print(cid, len(j["poses"]), "stand_h", st, issues, "odd", odd, "portrait", portrait)
print("flagged:", bad)
for k in range(0, len(ids), 4):
    ims = [Image.open(HERE / c / "out" / "review.png") for c in ids[k:k + 4]]
    w, h = ims[0].size
    s = Image.new("RGB", (w * 2, h * 3))
    for i, m in enumerate(ims):
        s.paste(m, ((i % 2) * w, (i // 2) * h))
    s.resize((s.width * 3 // 5, s.height * 3 // 5), Image.NEAREST).save(HERE / f"contact_{k // 4}.png")
    print(k // 4, ids[k:k + 4])
