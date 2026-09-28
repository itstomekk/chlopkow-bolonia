"""Local server for the Chłopków Bolonia map editor.

    python editor/server.py            # http://127.0.0.1:8770/
    python editor/server.py --port 8771

Serves the editor UI, the game's generated map read-only (/game/* -> docs/*), and a small
JSON API. Binds to 127.0.0.1 only. Uses the Python standard library (+ numpy/Pillow that the
map generator already needs).

API
  GET  /api/geo                 map geometry (bbox, size, scale) from osm/geo.py
  GET  /api/edits               osm/edits.json (empty document when missing)
  PUT  /api/edits               validate + atomic write; previous version kept in editor/history/
  GET  /api/basemap/<z>/<tx>/<ty>.jpg   satellite tile in map-pixel space (cached in editor/basemap/)
  POST /api/rebuild             run osm/render_map.py + osm/place_items.py (only with --allow-rebuild)
"""
import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import threading
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EDITOR = os.path.join(ROOT, 'editor')
DOCS = os.path.join(ROOT, 'docs')
BASEMAP = os.path.join(EDITOR, 'basemap')
HISTORY = os.path.join(EDITOR, 'history')
sys.path.insert(0, os.path.join(ROOT, 'osm'))
import edits  # noqa: E402
import geo  # noqa: E402

TILE = 512                       # tile size in map art pixels at z=0 (1 art px = 0.5 m)
KEEP_HISTORY = 30
MIME = {'.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8',
        '.json': 'application/json; charset=utf-8', '.png': 'image/png', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml',
        '.ico': 'image/x-icon', '.woff2': 'font/woff2', '.md': 'text/plain; charset=utf-8'}
SOURCES = {
    # ArcGIS REST export in EPSG:4326 matches the map's equirectangular projection closely at village scale.
    'esri': ('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/export'
             '?bbox={lon0},{lat0},{lon1},{lat1}&bboxSR=4326&imageSR=4326&size={w},{h}&format=jpg&f=image',
             'Imagery © Esri, Maxar, Earthstar Geographics, and the GIS User Community'),
    # Polish national orthophoto (WMS 1.3.0, EPSG:4326 axis order lat,lon). Often unreachable from abroad.
    'geoportal': ('https://mapy.geoportal.gov.pl/wss/service/PZGIK/ORTO/WMS/StandardResolution?SERVICE=WMS&VERSION=1.3.0'
                  '&REQUEST=GetMap&LAYERS=Raster&STYLES=&CRS=EPSG:4326&BBOX={lat0},{lon0},{lat1},{lon1}'
                  '&WIDTH={w}&HEIGHT={h}&FORMAT=image/jpeg',
                  'Ortofotomapa © GUGiK (geoportal.gov.pl)'),
}
rebuild_lock = threading.Lock()
save_lock = threading.Lock()
ALLOW_REBUILD = False
EDITS_PATH = edits.DEFAULT_PATH


def geo_info():
    return dict(bbox=list(geo.BBOX), w=geo.W, h=geo.H, a=geo.A, mx=geo.MX, my=geo.MY, tile=TILE,
                sources={k: v[1] for k, v in SOURCES.items()}, allowRebuild=ALLOW_REBUILD,
                zoneKinds=list(edits.ZONE_KINDS), layers=list(edits.LAYERS))


def safe_join(base, rel):
    rel = urllib.parse.unquote(rel).replace('\\', '/').lstrip('/')
    p = os.path.realpath(os.path.join(base, rel))
    if p != os.path.realpath(base) and not p.startswith(os.path.realpath(base) + os.sep):
        return None
    return p


_BUILDINGS = None


def osm_buildings():
    """OSM building footprints as oriented rectangles, same fit as render_map.py (PCA axes, metres).
    The game draws them 1.25-2.3x larger; the editor shows the real OSM footprint."""
    global _BUILDINGS
    if _BUILDINGS is not None:
        return _BUILDINGS
    import math
    import numpy as np
    d = json.load(open(os.path.join(ROOT, 'osm', 'chlopkow.json'), encoding='utf-8'))
    out = []
    for e in d.get('elements', []):
        tg = e.get('tags', {})
        if e.get('type') != 'way' or 'building' not in tg or len(e.get('geometry', [])) < 3:
            continue
        g = e['geometry']
        ll = [(p['lat'], p['lon']) for p in g]
        if ll[0] == ll[-1]:
            ll = ll[:-1]
        arr = np.array([geo.P(la, lo) for la, lo in ll])
        c = arr.mean(0)
        _, _, vt = np.linalg.svd(arr - c)
        ax, nx = vt[0], vt[1]
        pl, pn = (arr - c) @ ax, (arr - c) @ nx
        # centre of the oriented bounding box (not the vertex mean)
        cc = c + ax * (pl.max() + pl.min()) / 2 + nx * (pn.max() + pn.min()) / 2
        lat, lon = geo.to_latlon(*cc)
        kind = tg['building']
        out.append(dict(id=e['id'], lat=float(lat), lon=float(lon), len=round(float(pl.max() - pl.min()) / geo.A, 2),
                        wid=round(float(pn.max() - pn.min()) / geo.A, 2), angle=round(math.degrees(math.atan2(ax[1], ax[0])), 2),
                        kind='house' if kind in ('house', 'detached', 'bungalow', 'yes', 'residential') else 'farm',
                        osmKind=kind, name=tg.get('name', ''),
                        landmark=kind == 'church' or tg.get('amenity') == 'place_of_worship'))
    _BUILDINGS = out
    return out


def bbox_key():
    """Tiles are cut in map-pixel space, so a bbox change (map extension) needs a fresh tile set."""
    return 'bbox_' + '_'.join(f'{v:.5f}' for v in geo.BBOX).replace('.', 'p')


def fetch_tile(src, z, tx, ty):
    """Tile (tx, ty) at zoom level z covers TILE*2**z art pixels and is TILE px wide."""
    span = TILE * (2 ** z)
    x0, y0 = tx * span, ty * span
    if tx < 0 or ty < 0 or x0 >= geo.W or y0 >= geo.H or z < 0 or z > 4:
        return None, 'tile outside map'
    path = os.path.join(BASEMAP, src, bbox_key(), str(z), f'{tx}_{ty}.jpg')
    if os.path.exists(path):
        return path, None
    lat1, lon0 = geo.to_latlon(x0, y0)
    lat0, lon1 = geo.to_latlon(x0 + span, y0 + span)
    # ArcGIS keeps square *degree* pixels and silently widens the extent otherwise, so ask for an
    # image whose pixel aspect matches the degree aspect, then resample to a square map-pixel tile.
    rw = TILE * 2
    rh = max(1, round(rw * (lat1 - lat0) / (lon1 - lon0)))
    url = SOURCES[src][0].format(lat0=lat0, lon0=lon0, lat1=lat1, lon1=lon1, w=rw, h=rh)
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'chlopkow-bolonia-map-editor/1'})
        data = urllib.request.urlopen(req, timeout=40).read()
    except Exception as e:  # offline, blocked, timeout
        return None, f'{src} unavailable: {e}'
    if not data.startswith(b'\xff\xd8'):
        return None, f'{src} returned a non-JPEG response'
    from PIL import Image
    import io
    im = Image.open(io.BytesIO(data)).convert('RGB').resize((TILE, TILE), Image.LANCZOS)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.part'
    im.save(tmp, 'JPEG', quality=88)
    os.replace(tmp, path)
    return path, None


class Handler(BaseHTTPRequestHandler):
    server_version = 'ArkMapEditor/1'

    def log_message(self, fmt, *args):
        if '/api/' in (args[0] if args else ''):
            sys.stderr.write('%s\n' % (fmt % args))

    def send_json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path, cache='no-cache'):
        if not path or not os.path.isfile(path):
            return self.send_json({'error': 'not found'}, 404)
        with open(path, 'rb') as f:
            body = f.read()
        self.send_response(200)
        self.send_header('Content-Type', MIME.get(os.path.splitext(path)[1].lower(), 'application/octet-stream'))
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', cache)
        self.end_headers()
        self.wfile.write(body)

    def body_json(self):
        n = int(self.headers.get('Content-Length') or 0)
        if n > 20_000_000:
            raise ValueError('body too large')
        return json.loads(self.rfile.read(n).decode('utf-8'))

    # ---------------------------------------------------------------- GET
    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        p = u.path
        if p in ('/', '/index.html'):
            return self.send_file(os.path.join(EDITOR, 'index.html'))
        if p == '/api/geo':
            return self.send_json(geo_info())
        if p == '/api/buildings':
            return self.send_json({'buildings': osm_buildings()})
        if p == '/api/edits':
            try:
                return self.send_json(edits.load(EDITS_PATH))
            except ValueError as e:
                return self.send_json({'error': str(e)}, 500)
        if p == '/api/history':
            files = sorted(os.listdir(HISTORY), reverse=True) if os.path.isdir(HISTORY) else []
            return self.send_json({'files': files})
        if p.startswith('/api/basemap/'):
            parts = p[len('/api/basemap/'):].split('/')
            q = urllib.parse.parse_qs(u.query)
            src = (q.get('src') or ['esri'])[0]
            if src not in SOURCES or len(parts) != 3 or not parts[2].endswith('.jpg'):
                return self.send_json({'error': 'bad tile request'}, 400)
            try:
                z, tx, ty = int(parts[0]), int(parts[1]), int(parts[2][:-4])
            except ValueError:
                return self.send_json({'error': 'bad tile request'}, 400)
            path, err = fetch_tile(src, z, tx, ty)
            if err:
                return self.send_json({'error': err}, 404 if 'outside' in err else 502)
            return self.send_file(path, cache='max-age=86400')
        if p.startswith('/game/'):
            return self.send_file(safe_join(DOCS, p[len('/game/'):]))
        return self.send_file(safe_join(EDITOR, p))

    # ---------------------------------------------------------------- PUT / POST
    def do_PUT(self):
        if urllib.parse.urlparse(self.path).path != '/api/edits':
            return self.send_json({'error': 'not found'}, 404)
        try:
            data = edits.migrate(self.body_json())
        except Exception as e:
            return self.send_json({'error': f'invalid JSON: {e}'}, 400)
        errs = edits.validate(data)
        if errs:
            return self.send_json({'error': 'invalid edits', 'details': errs}, 400)
        data.setdefault('meta', {})['updated'] = dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        with save_lock:
            if os.path.exists(EDITS_PATH):
                os.makedirs(HISTORY, exist_ok=True)
                stamp = dt.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
                shutil.copy2(EDITS_PATH, os.path.join(HISTORY, f'edits-{stamp}.json'))
                old = sorted(os.listdir(HISTORY))
                for f in old[:-KEEP_HISTORY]:
                    os.remove(os.path.join(HISTORY, f))
            edits.save(data, EDITS_PATH)
        return self.send_json({'ok': True, 'updated': data['meta']['updated']})

    def do_POST(self):
        if urllib.parse.urlparse(self.path).path != '/api/rebuild':
            return self.send_json({'error': 'not found'}, 404)
        if not ALLOW_REBUILD:
            return self.send_json({'error': 'rebuild disabled; start the server with --allow-rebuild '
                                            '(it rewrites docs/map.json, docs/items.json and docs/img/map_*.png)'}, 403)
        if not rebuild_lock.acquire(blocking=False):
            return self.send_json({'error': 'a rebuild is already running'}, 409)
        try:
            log, code = [], 0
            for script in ('osm/render_map.py', 'osm/place_items.py'):
                r = subprocess.run([sys.executable, script], cwd=ROOT, capture_output=True, text=True,
                                   encoding='utf-8', errors='replace', env=dict(os.environ, ARK_EDITS=EDITS_PATH))
                log.append(f'$ python {script}\n{r.stdout}{r.stderr}')
                code = r.returncode
                if code:
                    break
            return self.send_json({'ok': code == 0, 'code': code, 'log': '\n'.join(log)[-8000:]}, 200 if code == 0 else 500)
        finally:
            rebuild_lock.release()


def make_server(port=8770, edits_path=None, allow_rebuild=False):
    global EDITS_PATH, ALLOW_REBUILD
    EDITS_PATH = edits_path or edits.DEFAULT_PATH
    ALLOW_REBUILD = allow_rebuild
    return ThreadingHTTPServer(('127.0.0.1', port), Handler)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--port', type=int, default=8770)
    ap.add_argument('--edits', default=None, help='edits file (default osm/edits.json)')
    ap.add_argument('--allow-rebuild', action='store_true', help='enable the Rebuild button (rewrites generated map files)')
    a = ap.parse_args()
    srv = make_server(a.port, a.edits, a.allow_rebuild)
    print(f'Map editor: http://127.0.0.1:{a.port}/   (edits: {os.path.relpath(EDITS_PATH, ROOT)}, '
          f'rebuild {"ON" if a.allow_rebuild else "off"})', flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
