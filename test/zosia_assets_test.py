from pathlib import Path
import hashlib
import subprocess
import sys
import json
import numpy as np
from PIL import Image

root = Path(__file__).resolve().parents[1]
png = root / 'docs/img/zosia_sheet.png'
meta_path = root / 'docs/img/zosia_sheet.json'
before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (png, meta_path)}
subprocess.run([sys.executable, 'gen/zosia/build_sheet.py'], cwd=root, check=True)
assert before == {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (png, meta_path)}, 'non-reproducible atlas build'
a = np.asarray(Image.open(png).convert('RGBA'))
assert a.shape == (680, 640, 4)
assert set(np.unique(a[..., 3])) == {0, 255}
rgb = a[..., :3].astype(np.int32)
key = (rgb[..., 0] > 165) & (rgb[..., 2] > 145) & (rgb[..., 1] < 125) & (a[..., 3] > 0)
assert np.count_nonzero(key) == 0
meta = json.loads(meta_path.read_text())
for name, anim in meta['anims'].items():
    frames = []
    for f in anim['frames']:
        assert f['w'] == 160 and f['h'] == 170
        im = Image.open(png).crop((f['x'], f['y'], f['x'] + f['w'], f['y'] + f['h']))
        box = im.getchannel('A').getbbox()
        assert box and 0 < box[0] < box[2] < 160 and 0 < box[1] < box[3] == 164
        frames.append(np.asarray(im))
    assert np.array_equal(frames[0], frames[2]) and np.array_equal(frames[1], frames[3])
    assert np.count_nonzero(frames[0][100:] != frames[1][100:]) > 0, name
print('PASS ZOSIA assets: reproducible atlas, 640x680, 160x170 cells, baseline 164, hard alpha, zero magenta, distinct lower-body A/B frames in every direction')
