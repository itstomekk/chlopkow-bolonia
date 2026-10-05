"""Find real tree positions outside mapped forests -> osm/real_trees.json.

Two independent sources must agree, so a tree is only kept where both see one:
  * Meta & WRI High Resolution Canopy Height Maps (1 m, CC BY 4.0), read from the public
    AWS bucket: canopy >= 4 m gives the candidate crowns (one per ~7 m, tallest first).
  * Esri World Imagery (GeoEye-1, May 2021, ~0.5 m): the crown must also look like canopy
    (dark vegetation within ~4 m), which drops felled trees and canopy-model noise.

Needs rasterio + mercantile + scipy (not used by the game build itself):
    uv venv .venv-trees && uv pip install --python .venv-trees/Scripts/python.exe rasterio mercantile scipy numpy pillow
    .venv-trees/Scripts/python.exe osm/fetch_trees.py [cache_dir]

render_map.py reads osm/real_trees.json; without it, it falls back to random garden trees.
"""
import json, math, os, sys, time, urllib.request

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import geo  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
W, H = geo.W, geo.H
CACHE = sys.argv[1] if len(sys.argv) > 1 else os.path.join('editor', 'cache', 'trees')
OUT = os.path.join('osm', 'real_trees.json')
CHM_URL = 'https://dataforgood-fb-data.s3.amazonaws.com/forests/v1/alsgedi_global_v6_float/chm/'
ESRI = ('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/export'
        '?bbox={lo0},{la0},{lo1},{la1}&bboxSR=4326&imageSR=4326&size={w},{h}&format=jpg&f=image')
MIN_H, SPACING, DARK = 4, 14, 62      # canopy metres, crown spacing in art px (7 m), Esri brightness


def canopy_height():
    """Canopy height in metres on the game pixel grid (bilinear from the 1.2 m source)."""
    path = os.path.join(CACHE, 'chm.npy')
    if os.path.exists(path):
        return np.load(path)
    import mercantile, rasterio
    from rasterio.transform import from_bounds
    from rasterio.warp import reproject, transform_bounds, Resampling
    from rasterio.windows import from_bounds as window_from_bounds
    s, w, n, e = geo.BBOX
    dst = np.zeros((H, W), np.float32)
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR', AWS_NO_SIGN_REQUEST='YES'):
        for t in mercantile.tiles(w, s, e, n, 9):
            with rasterio.open('/vsicurl/' + CHM_URL + mercantile.quadkey(t) + '.tif') as src:
                b = transform_bounds('EPSG:4326', src.crs, w - .002, s - .002, e + .002, n + .002)
                win = window_from_bounds(*b, transform=src.transform).round_offsets().round_lengths()
                tmp = np.zeros((H, W), np.float32)
                reproject(src.read(1, window=win), tmp, src_transform=src.window_transform(win), src_crs=src.crs,
                          dst_transform=from_bounds(w, s, e, n, W, H), dst_crs='EPSG:4326', resampling=Resampling.bilinear)
                dst = np.maximum(dst, tmp)
    np.save(path, dst)
    return dst


def esri_mosaic(n=4):
    """Esri World Imagery on the game pixel grid (EPSG:4326 export is linear in lat/lon, like geo.P)."""
    path = os.path.join(CACHE, 'esri_full.png')
    if os.path.exists(path):
        return Image.open(path).convert('RGB')
    mos = Image.new('RGB', (W, H))
    xs = [round(i * W / n) for i in range(n + 1)]; ys = [round(j * H / n) for j in range(n + 1)]
    for j in range(n):
        for i in range(n):
            x0, x1, y0, y1 = xs[i], xs[i + 1], ys[j], ys[j + 1]
            la1, lo0 = geo.to_latlon(x0, y0); la0, lo1 = geo.to_latlon(x1, y1)
            url = ESRI.format(lo0=lo0, la0=la0, lo1=lo1, la1=la1, w=x1 - x0, h=y1 - y0)
            for attempt in range(3):
                try:
                    data = urllib.request.urlopen(url, timeout=120).read(); break
                except Exception:
                    if attempt == 2: raise
                    time.sleep(3)
            tile = Image.open(__import__('io').BytesIO(data)).convert('RGB').resize((x1 - x0, y1 - y0))
            mos.paste(tile, (x0, y0))
    mos.save(path)
    return mos


def forest_mask():
    d = json.load(open(os.path.join('osm', 'chlopkow.json'), encoding='utf-8'))
    m = Image.new('L', (W, H), 0); dr = ImageDraw.Draw(m)
    for e in d['elements']:
        t = e.get('tags', {})
        if e['type'] == 'way' and e.get('geometry') and (t.get('landuse') == 'forest' or t.get('natural') == 'wood'):
            dr.polygon([geo.P(p['lat'], p['lon']) for p in e['geometry']], fill=255)
    return np.array(m) > 0


def main():
    os.makedirs(CACHE, exist_ok=True)
    chm = canopy_height()
    rgb = np.array(esri_mosaic()).astype(np.float32)
    dark = ndimage.minimum_filter(ndimage.uniform_filter(rgb.mean(2), 7), size=17)   # darkest canopy within ~4 m
    can = (chm >= MIN_H) & ~forest_mask()
    lab, n = ndimage.label(can)
    big = np.zeros(n + 1, bool); big[1:] = ndimage.sum(can, lab, range(1, n + 1)) >= 24   # >= 6 m2 of crown
    can = big[lab]
    sm = ndimage.gaussian_filter(np.where(can, chm, 0).astype(np.float32), 2)
    peaks = (sm == ndimage.maximum_filter(sm, size=13)) & can & (sm > 2.5)
    ys, xs = np.nonzero(peaks)
    hs = sm[ys, xs]
    taken = {}
    trees = []
    for i in np.argsort(-hs):
        x, y = int(xs[i]), int(ys[i])
        gx, gy = x // SPACING, y // SPACING
        if any((px - x) ** 2 + (py - y) ** 2 < SPACING ** 2
               for ax in (gx - 1, gx, gx + 1) for ay in (gy - 1, gy, gy + 1) for px, py in taken.get((ax, ay), ())):
            continue
        taken.setdefault((gx, gy), []).append((x, y))
        if dark[y, x] >= DARK:
            continue                              # canopy model says tree, 2021 photo says open ground
        lat, lon = geo.to_latlon(x, y)
        trees.append(dict(lat=round(lat, 7), lon=round(lon, 7), h=round(float(chm[y, x]), 1)))
    json.dump(dict(source='Meta & WRI High Resolution Canopy Height Maps (CC BY 4.0) checked against '
                          'Esri World Imagery (GeoEye-1, 2021-05-13); trees outside OSM forests only.',
                   trees=trees), open(OUT, 'w', encoding='utf-8'), indent=0)
    print(len(trees), 'trees ->', OUT)


if __name__ == '__main__':
    main()
