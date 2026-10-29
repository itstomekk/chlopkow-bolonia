"""Ground-layer palette step for osm/render_map.py (keeps the Wapnica change local to its region).

map_ground.png is a 256-colour palette image. A plain MEDIANCUT of the whole 36-megapixel map re-derives every
palette entry from the histogram, so changing a few thousand pixels around Wapnica would nudge colours all over the
map. Instead, when the released layout is reachable in git (BASE_REF), the new render is written like this:

  * outside REGION the released palette indices are kept bit for bit;
  * inside REGION the freshly rendered RGB goes through the released RGB -> index mapping (read back from the released
    image); colours that mapping has never seen (the Wapnica decal's 8 colours) are written exactly into palette slots
    the released image never used; anything still unmatched falls back to the nearest palette colour.

Without a baseline (shallow clone, no git, or BASE_REF unreachable) it falls back to the old global MEDIANCUT, so
the render still works, it just recolours the whole map slightly.

The next full re-render must keep this step (or re-baseline BASE_REF to the commit that contains the Wapnica map):
see "Wapnica" in DEVELOPMENT.md.
"""
import io, os, subprocess
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
BASE_REF = '40c9aa3'          # last commit before the Wapnica decal; its docs/img/map_ground.png is the palette baseline
BASE_PATH = 'docs/img/map_ground.png'


def baseline():
    try:
        raw = subprocess.run(['git', 'show', f'{BASE_REF}:{BASE_PATH}'], capture_output=True, check=True).stdout
        im = Image.open(io.BytesIO(raw)); im.load()
        return im if im.mode == 'P' else None
    except Exception as exc:
        print('quantize_ground: no baseline,', type(exc).__name__, exc)
        return None


def plain(ground):
    return ground.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)


def quantize(ground, region):
    """Return a 'P' image for `ground` (RGB). region = (x0, y0, x1, y1) in map px, exclusive end."""
    base = baseline() if region else None
    if base is None or base.size != ground.size:
        return plain(ground)
    rects = [region] if isinstance(region[0], int) else list(region)   # one rect, or a list of rects (Wapnica + forest sprites)
    R = np.zeros((ground.height, ground.width), bool)
    for x0, y0, x1, y1 in rects: R[y0:y1, x0:x1] = True
    idx = np.array(base)                                   # released indices
    pal = np.array(base.getpalette()[:768], np.int32).reshape(-1, 3)
    pal = np.concatenate([pal, np.zeros((256 - len(pal), 3), np.int32)])
    used = np.bincount(idx.ravel(), minlength=256) > 0
    free = [i for i in range(256) if not used[i]]
    arr = np.array(ground)                                 # H x W x 3 uint8
    # Pillow's MEDIANCUT maps every RGB value to one palette index. Read that mapping back from the released image:
    # (RGB outside the region, released index) pairs. A colour that maps to two indices would mean the ground outside
    # the region differs from the released one, so that is reported.
    pairs = set()
    for ys in range(0, ground.height, 512):
        c = arr[ys:ys + 512].astype(np.int64)
        k = (c[..., 0] << 16) | (c[..., 1] << 8) | c[..., 2]
        m = np.ones(k.shape, bool)
        m &= ~R[ys:ys + 512]
        pairs.update(np.unique((k[m] << 8) | idx[ys:ys + 512][m]).tolist())
    pairs = np.array(sorted(pairs), np.int64)
    pk, pi = pairs >> 8, (pairs & 255).astype(np.uint8)
    uniq, first = np.unique(pk, return_index=True)
    print(f'quantize_ground: {len(uniq)} colours known outside the region, {len(pk) - len(uniq)} of them with a second index')
    c = arr[R].astype(np.int64)
    key = (c[..., 0] << 16) | (c[..., 1] << 8) | c[..., 2]
    uk, inv, cnt = np.unique(key.ravel(), return_inverse=True, return_counts=True)
    pos = np.searchsorted(uniq, uk); pos[pos == len(uniq)] = 0
    known = uniq[pos] == uk
    lut = np.where(known, pi[first[pos]], 255).astype(np.int32)
    ucol = np.stack([uk >> 16, (uk >> 8) & 255, uk & 255], 1)
    new = np.nonzero(~known)[0]
    for j in new[np.argsort(-cnt[new])][:len(free)]:        # most frequent new colours (the decal) get an exact free slot
        slot = free.pop(0); pal[slot] = ucol[j]; used[slot] = True; lut[j] = slot; known[j] = True
    left = np.nonzero(~known)[0]
    cand = np.nonzero(used)[0]
    for j in left:
        lut[j] = cand[int(np.argmin(((pal[cand] - ucol[j]) ** 2).sum(1)))]
    print(f'quantize_ground: {len(rects)} region(s): {len(uk)} colours, {len(new)} new (exact slots: {len(new) - len(left)}, nearest: '
          f'{len(left)} = {int(cnt[left].sum()) if len(left) else 0} px)')
    idx[R] = lut[inv].reshape(key.shape).astype(np.uint8)
    out = Image.fromarray(idx, 'P'); out.putpalette(pal.astype(np.uint8).ravel().tolist())
    return out


def save(ground, path, region=None):
    if os.environ.get('ARK_DUMP_GROUND'):                  # dev only: keep the true-colour ground for palette experiments
        np.save(os.environ['ARK_DUMP_GROUND'], np.array(ground))
    quantize(ground, region).save(path, optimize=True)
