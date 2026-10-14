"""Mobile-friendly web build of review round v3 (east1 + east2): optimised, lazy-loaded image tiles + a Polish decision form
that autosaves to the game server (Cloudflare Worker `chlopkow-api`, route /review/<id>).

    python gen/yards/reviews/2026-10-14-east1/build_v3_web.py --out OUT_DIR [--src SHEETS_DIR] [--api URL] [--review-id ID] [--seed-out FILE]

Output (static, no external requests except the API):  OUT_DIR/index.html (+ inline CSS/JS/data) and OUT_DIR/a/*.png|webp.
Each PNG sheet is cut into tiles along its empty gutters (rows, then columns inside tall rows). Tiles with few colours / blocky pixel art
stay lossless PNG (shown with image-rendering:pixelated when zoomed); photo tiles become WebP q88. Tiles load lazily; tapping a sheet opens a
zoom view at 1 image pixel per CSS pixel. The access key is NOT in the page: it comes from the URL fragment (#k=...) and is sent in a header.

--seed-out writes the initial server document (v1 answers seeded) so the review can be (re)set with fetch_review.py put.
Local only; never edits the game.
"""
import argparse
import io
import json
import re
import shutil
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
MAIN_SRC = Path("C:/Users/Lenovo/Hermes/projects/games/arek-w-chlopkowie/gen/yards/reviews/2026-10-14-east1")
DEC = json.loads((ROOT / "plans/yard-review-east1-v1-decisions.json").read_text(encoding="utf-8"))

SHEETS = {  # key: (file, accessible name)
    "overview": ("01_przeglad_pas.png", "Cały pas obu grup"),
    "19": ("02_dom_19.png", "Dom nr 19"), "20": ("03_dom_20.png", "Dom nr 20"), "23": ("04_dom_23.png", "Dom nr 23"),
    "22": ("05_dom_22.png", "Dom nr 22"), "E1": ("06_dom_E1.png", "Dom E1"),
    "E2": ("09_dom_E2.png", "Dom E2"), "E3": ("10_dom_E3.png", "Dom E3"), "E4": ("11_dom_E4.png", "Dom E4"),
    "E5": ("12_dom_E5.png", "Dom E5"), "E6": ("13_dom_E6.png", "Dom E6"),
    "p0": ("07_rekwizyty_przeglad.png", "Rekwizyty: przegląd"), "pa": ("07a_rekwizyty_zachod_20_22_23.png", "Rekwizyty: zachód 20, 22, 23"),
    "pb": ("07b_rekwizyty_wschod_19_E1.png", "Rekwizyty: wschód 19, E1"), "pc": ("07c_rekwizyty_E2_E3.png", "Rekwizyty: E2, E3"),
    "pd": ("07d_rekwizyty_E4_E5_E6.png", "Rekwizyty: E4, E5, E6"),
    "pending": ("08_do_rozpoznania.png", "Do rozpoznania (east1)"), "pending2": ("08b_do_rozpoznania_east2_E2_E3.png", "Do rozpoznania: E2, E3"),
    "pending3": ("08c_do_rozpoznania_east2_E4_E5_E6.png", "Do rozpoznania: E4, E5, E6"),
}
V1 = lambda a: [("v1", a)]  # noqa: E731
HOUSES = [  # key, way, title, group, options [(value, label)], farm (outbuildings decision?)
    ("19", 909988586, "Dom nr 19", "east1", V1("zostaw stary (v1)") + [("1", "1 – dwuspadowy, skręcony"), ("2", "2 – dwuspadowy, prosto"), ("3", "3 – czterospadowy, prosto")], False),
    ("20", 909989528, "Dom nr 20 (ruina)", "east1", V1("zostaw stary (v1)") + [("1", "1 – ściany do połowy"), ("2", "2 – dach zawalony do środka"), ("3", "3 – fundament i stos desek")], False),
    ("23", 909989530, "Dom nr 23", "east1", V1("zostaw kremowy (v1)") + [("1", "1 – jasnoszary"), ("2", "2 – średnioszary")], False),
    ("22", 909989529, "Dom nr 22", "east1", V1("ok (bez zmian)"), False),
    ("E1", 1095382357, "Dom bez numeru (E1)", "east1", V1("ok (bez zmian)"), False),
    ("E2", 1095382355, "Dom E2 (OSM 1095382355) — bez Street View", "east2", [("1", "1 – dwuspadowy, kalenica N-S"), ("2", "2 – czterospadowy"), ("regen", "przerysować (opisz w uwagach)"), ("none", "zostaw szare pudełko")], True),
    ("E3", 1095382338, "Dom E3 (OSM 1095382338)", "east2", [("1", "dodać do gry (ta wersja)"), ("regen", "przerysować (opisz w uwagach)"), ("none", "zostaw szare pudełko")], True),
    ("E4", 1095382337, "Dom E4 (OSM 1095382337) — drewniany", "east2", [("1", "dodać do gry (ta wersja)"), ("regen", "przerysować (opisz w uwagach)"), ("none", "zostaw szare pudełko")], True),
    ("E5", 1095382325, "Dom E5 (OSM 1095382325) — z bali", "east2", [("1", "dodać do gry (ta wersja)"), ("regen", "przerysować (opisz w uwagach)"), ("none", "zostaw szare pudełko")], True),
    ("E6", 1095382294, "Dom E6 (OSM 1095382294) — dwupiętrowy", "east2", [("1", "dodać do gry (ta wersja)"), ("regen", "przerysować (opisz w uwagach)"), ("none", "zostaw szare pudełko")], True),
]

# ---------------------------------------------------------------- image tiling
GAP, TALL, MIN_COL = 4, 100, 80


def bg_colors(a):
    edge = np.concatenate([a[:, 0], a[:, -1], a[0], a[-1]])
    u, c = np.unique(edge.reshape(-1, 3), axis=0, return_counts=True)
    return [tuple(int(x) for x in u[i]) for i in np.argsort(-c)[:3] if c[i] > 50]


def runs(mask, gap):
    out, i, n = [], 0, len(mask)
    while i < n:
        if mask[i]:
            j = i
            while j < n and mask[j]:
                j += 1
            if j - i >= gap:
                out.append((i, j))
            i = j
        else:
            i += 1
    return out


def content_segments(rs, n):
    out, prev = [], 0
    for s, e in rs:
        if s > prev:
            out.append((prev, s))
        prev = e
    if prev < n:
        out.append((prev, n))
    return out


def tile_boxes(im):
    """Return [(x0, y0, x1, y1)] tiles that exactly tile the image."""
    a = np.asarray(im)
    h, w, _ = a.shape
    bg = bg_colors(a)
    m = np.zeros((h, w), bool)
    for c in bg:
        m |= (a == np.array(c)).all(axis=2)
    segs = content_segments(runs(m.all(axis=1), GAP), h)
    if not segs:
        return [(0, 0, w, h)]
    groups, cur = [], []  # consecutive short segments are one text block; tall segments stand alone
    for s in segs:
        if s[1] - s[0] >= TALL:
            if cur:
                groups.append(cur)
                cur = []
            groups.append([s])
        else:
            cur.append(s)
    if cur:
        groups.append(cur)
    # y ranges tile the sheet: cut at the middle of the gap between neighbouring groups
    spans = [(g[0][0], g[-1][1]) for g in groups]
    cuts = [0] + [(spans[i][1] + spans[i + 1][0]) // 2 for i in range(len(spans) - 1)] + [h]
    boxes = []
    for gi, g in enumerate(groups):
        y0, y1 = cuts[gi], cuts[gi + 1]
        if len(g) == 1 and g[0][1] - g[0][0] >= TALL:
            cs = content_segments(runs(m[g[0][0]:g[0][1]].all(axis=0), GAP), w)
            cs = [c for c in cs]
            xs = [0] + [(cs[i][1] + cs[i + 1][0]) // 2 for i in range(len(cs) - 1)] + [w]
            parts = [[xs[i], xs[i + 1]] for i in range(len(cs))]
            merged = []
            for p in parts:  # too narrow tiles join their neighbour
                if merged and (p[1] - p[0] < MIN_COL or merged[-1][1] - merged[-1][0] < MIN_COL):
                    merged[-1][1] = p[1]
                else:
                    merged.append(p)
            for x0, x1 in merged:
                boxes.append((x0, y0, x1, y1))
        else:
            boxes.append((0, y0, w, y1))
    return boxes


def encode(tile):
    """Choose PNG (lossless: graphics, text, pixel art) or WebP (photos). Returns (ext, bytes)."""
    a = np.asarray(tile).reshape(-1, 3).astype(np.uint32)
    uniq = len(np.unique((a[:, 0] << 16) | (a[:, 1] << 8) | a[:, 2]))
    arr = np.asarray(tile).astype(np.int16)
    blocky = float((arr[:, 1:] == arr[:, :-1]).all(axis=2).mean())
    src = tile
    if uniq <= 256:
        src = tile.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    b = io.BytesIO()
    src.save(b, "PNG", optimize=True)
    png = b.getvalue()
    w = io.BytesIO()
    tile.save(w, "WEBP", quality=88, method=4)
    webp = w.getvalue()
    if uniq <= 6000 and len(png) <= max(3 * len(webp), 300_000):
        return "png", png
    if blocky >= 0.80 and len(png) <= 900_000:
        return "png", png
    return ("png", png) if len(png) <= len(webp) else ("webp", webp)


def build_sheets(src, assets):
    out, total = {}, 0
    for key, (fn, _) in SHEETS.items():
        im = Image.open(src / fn).convert("RGB")
        w, h = im.size
        a = np.asarray(im)
        bg = bg_colors(a)[0] if bg_colors(a) else (24, 35, 33)
        tiles = []
        for i, (x0, y0, x1, y1) in enumerate(tile_boxes(im)):
            cx1, cy1 = min(x1 + 1, w), min(y1 + 1, h)  # 1 px overlap: no hairline seams
            ext, data = encode(im.crop((x0, y0, cx1, cy1)))
            name = f"{key}-{i}.{ext}"
            (assets / name).write_bytes(data)
            total += len(data)
            tiles.append([x0, y0, cx1 - x0, cy1 - y0, name])
        out[key] = {"w": w, "h": h, "bg": "#%02x%02x%02x" % bg, "alt": SHEETS[key][1], "tiles": tiles}
        print(f"  {key:9s} {w}x{h}  {len(tiles):2d} tiles  {sum((assets / t[4]).stat().st_size for t in tiles) // 1024:5d} KB")
    return out, total


# ---------------------------------------------------------------- data + page
def seed_state(props, houses):
    seed = {}
    for p in props:
        old = DEC["decisions"].get(p["id"], {})
        seed[p["id"]] = {"decision": old.get("decision", "pending"), "identification": old.get("identification", ""), "note": old.get("note", "")}
    st = {"houses": {}, "farms": {}, "props": seed}
    for h in houses:
        st["houses"][h["key"]] = {"option": "v1" if h["group"] == "east1" else "", "note": (h["seed"] or {}).get("note", "")}
        if h["farm"]:
            st["farms"][h["key"]] = {"decision": "", "note": ""}
    return st


def export_doc(review, houses, props, st):
    return {"review": review, "strips": ["east1", "east2"], "gameChangesApplied": False,
            "houses": {f"house-{h['way']}": {"yard": h["key"], "group": h["group"], "option": st["houses"][h["key"]]["option"], "note": st["houses"][h["key"]]["note"]} for h in houses},
            "outbuildings": {f"yard-{h['key']}": {"decision": st["farms"][h["key"]]["decision"], "note": st["farms"][h["key"]]["note"]} for h in houses if h["farm"]},
            "props": {p["id"]: {"n": p["n"], **st["props"][p["id"]]} for p in props}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--src", default=None, help="folder with the PNG sheets and props_v3.json (default: next to this script, else the main checkout)")
    ap.add_argument("--api", default="https://chlopkow-api.kolotom.workers.dev")
    ap.add_argument("--review-id", default="yard-east-v3")
    ap.add_argument("--seed-out", default=None)
    args = ap.parse_args()
    src = Path(args.src) if args.src else (HERE if (HERE / "props_v3.json").exists() else MAIN_SRC)
    out = Path(args.out)
    assets = out / "a"
    if out.exists():
        shutil.rmtree(out)
    assets.mkdir(parents=True)
    props_full = json.loads((src / "props_v3.json").read_text(encoding="utf-8"))
    props = [{"n": p["n"], "id": p["id"], "name": p["name"], "pending": bool(p["pending"])} for p in props_full]
    houses = [{"key": k, "way": w, "title": t, "group": g, "options": o, "farm": f, "seed": DEC["decisions"].get(f"house-{w}", {})} for k, w, t, g, o, f in HOUSES]
    print("tiling sheets from", src)
    sheets, total = build_sheets(src, assets)
    review = "yard-review-east1-v3"
    st = seed_state(props, houses)
    data = {"review": review, "houses": houses, "props": props, "seed": st, "sheets": sheets}
    cfg = {"api": args.api.rstrip("/"), "rid": args.review_id}
    html = (TEMPLATE.replace("__CFG__", json.dumps(cfg)).replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
            .replace("__API__", cfg["api"]))
    (out / "index.html").write_text(html, encoding="utf-8")
    if args.seed_out:
        Path(args.seed_out).write_text(json.dumps({"review": review, "client": "seed-v1", "state": st, "export": export_doc(review, houses, props, st)}, ensure_ascii=False, indent=1), encoding="utf-8")
    files = sum(1 for _ in assets.iterdir())
    print(f"OK {out}  index.html {len(html) // 1024} KB, {files} images, images total {total / 1e6:.1f} MB (lazy-loaded)")


TEMPLATE = r'''<!doctype html>
<html lang="pl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow,noarchive">
<meta name="referrer" content="no-referrer">
<meta name="theme-color" content="#151c1b">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src 'self' data:; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src __API__; base-uri 'none'; form-action 'none'">
<link rel="icon" href="data:,">
<title>Chłopków · podwórka east1 + east2 · przegląd v3</title>
<style>
:root{color-scheme:dark;--bg:#151c1b;--card:#1f2926;--text:#eeeade;--muted:#b6b9a8;--line:#425048;--accent:#eed392}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}body{margin:0;background:var(--bg);color:var(--text);font:16px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1500px;margin:auto;padding:16px 16px 80px}h1{font-size:clamp(24px,5vw,34px);line-height:1.2;margin:8px 0}h2{margin:30px 0 10px;color:var(--accent);font-size:clamp(20px,4vw,26px)}h3{margin:0 0 8px;font-size:20px}
.tools{position:sticky;top:0;z-index:5;display:flex;gap:8px 12px;flex-wrap:wrap;align-items:center;padding:8px 0;background:var(--bg);border-bottom:1px solid var(--line)}
.tools strong{font-size:14px;font-weight:600}
button,select,input,textarea,.il{font:inherit;color:var(--text);background:#26352e;border:1px solid var(--line);border-radius:8px;padding:8px 12px}
button,.il{cursor:pointer;min-height:40px;display:inline-flex;align-items:center}#copy{background:var(--accent);color:#19251d;font-weight:700}.il input{display:none}
#save{font-size:14px;font-weight:700;margin-left:auto}#save.ok{color:#8fe388}#save.warn{color:#ffb454}#save.err{color:#ff8a80}
#banner{display:none;margin:10px 0;padding:12px;border:1px solid #ffb454;border-radius:8px;background:#3a2f1a}#banner button{margin:6px 8px 0 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px;margin:14px 0}
.sheet{position:relative;width:100%;overflow:hidden;border-radius:6px;cursor:zoom-in;-webkit-tap-highlight-color:transparent}.sheet img{position:absolute;display:block;max-width:none}
.hint{font-size:13px;color:var(--muted);margin:2px 0 8px}
.opts{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0}
.opts label{display:flex;align-items:center;gap:10px;min-height:44px;padding:6px 14px 6px 10px;border:1px solid var(--line);border-radius:10px;background:#222e29;font-size:17px;cursor:pointer}
.opts input{width:22px;height:22px;margin:0;accent-color:var(--accent);flex:none}.opts label:has(input:checked){border-color:var(--accent);background:#33402f}
textarea{width:100%;min-height:60px}table{width:100%;border-collapse:collapse}td,th{padding:6px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
.n{display:inline-block;min-width:34px;text-align:center;border-radius:20px;color:#19251d;font-weight:800;padding:2px 8px}.g{background:#78dc6e}.o{background:#ff9628}
.tag{display:inline-block;border-radius:6px;padding:1px 8px;font-size:13px;font-weight:700;color:#19251d;background:#8ab4ff;margin-left:8px;vertical-align:middle}.tag.e1{background:#ff8a80}
.muted{color:var(--muted)}.sub{margin:10px 0 2px;font-weight:700}
#lb{position:fixed;inset:0;z-index:20;background:#000;display:none;flex-direction:column}#lb.on{display:flex}
#lbbar{display:flex;gap:8px;align-items:center;padding:6px 8px;background:#111;flex:none}#lbbar span{color:var(--muted);font-size:14px;margin-left:auto;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#lbs{flex:1;overflow:auto;-webkit-overflow-scrolling:touch}#lbin{margin:0 auto}#lbin .sheet{cursor:default}#lb.px .sheet img.png{image-rendering:pixelated}
@media (max-width:700px){main{padding:10px 10px 70px}.card{padding:10px;border-radius:8px}.opts label{flex:1 1 100%;font-size:16px}
 table,thead,tbody,tr,td{display:block}thead{display:none}tr{padding:10px 0;border-bottom:1px solid var(--line)}td{border:0;padding:3px 0}td[data-l]::before{content:attr(data-l) ": ";color:var(--muted);font-size:13px}
 td select,td input{width:100%;min-height:44px}
 .tools{gap:4px 6px;padding:6px 0}.tools strong{flex:1 1 100%;font-size:12px}.tools button,.tools .il{min-height:36px;padding:4px 10px;font-size:14px}#save{flex:1 1 auto;margin-left:0;font-size:13px;text-align:right}#copy,#dl{flex:none}}
</style></head><body><main>
<h1>Przegląd v3: podwórka east1 + east2 NA MAPIE</h1>
<p class="muted">Wszystko pokazane na prawdziwej mapie gry (live, origin/main) obok satelity. Turkusowy czworokąt = prawdziwy obrys domu (OSM), biały = budynki gospodarcze. Dwie grupy: <b>east1</b> (19, 20, 22, 23, E1; runda v2, Twoje odpowiedzi z v1 są wstawione) i <b>east2</b> (E2–E6, nowe: 5 domów + 8 budynków gospodarczych). Wybierasz i piszesz — <b>zapisuje się samo</b> na serwerze gry (zobacz „Zapisano ✓” u góry) i w tej przeglądarce. Obrazki: dotknij, żeby powiększyć. Nic nie zmienia gry.</p>
<div class="tools"><strong id="progress"></strong><button id="copy">Kopiuj JSON</button><button id="dl">Pobierz JSON</button>
<label class="il">Wczytaj JSON<input type="file" id="imp" accept=".json,application/json"></label><span id="save" role="status" aria-live="polite"></span></div>
<div id="banner" role="alert"></div>
<span id="notice" class="muted"></span>
<h2>0. Cały pas (obie grupy)</h2><div class="card" data-sheet="overview"></div>
<h2>1. Domy east1 (runda v2)</h2><div id="houses1"></div>
<h2>2. Domy east2 (NOWE: E2–E6, z budynkami gospodarczymi)</h2><div id="houses2"></div>
<h2>3. Rekwizyty (east1: do dodania + do rozpoznania; east2: nowi kandydaci 20+)</h2>
<div class="card" data-sheet="p0"></div><div class="card" data-sheet="pa"></div><div class="card" data-sheet="pb"></div><div class="card" data-sheet="pc"></div><div class="card" data-sheet="pd"></div>
<div class="card"><table id="props"><thead><tr><th>Nr</th><th>ID</th><th>Co to (model)</th><th>Decyzja</th><th>Co to jest (Twoje słowa)</th></tr></thead><tbody></tbody></table></div>
<h2>4. Jeszcze nierozpoznane</h2><div class="card" data-sheet="pending"></div><div class="card" data-sheet="pending2"></div><div class="card" data-sheet="pending3"></div>
</main>
<div id="lb" role="dialog" aria-modal="true" aria-label="Powiększenie"><div id="lbbar"><button id="lbx" aria-label="Zamknij">✕ Zamknij</button><button id="lbm" aria-label="Pomniejsz">−</button><button id="lbp" aria-label="Powiększ">+</button><button id="lbf">Dopasuj</button><button id="lb1">100%</button><span id="lbt"></span></div><div id="lbs"><div id="lbin"></div></div></div>
<script>
const CFG=__CFG__, D=__DATA__, KEY='yard-review-east1-v3', META=KEY+':meta', KEYSTORE='yard-review-key:'+CFG.rid;
const $=s=>document.querySelector(s), esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const lsGet=k=>{try{return localStorage.getItem(k)}catch(e){return null}}, lsSet=(k,v)=>{try{localStorage.setItem(k,v)}catch(e){}};
/* ---------- access key: URL fragment (#k=...) never goes to a server log or referrer; kept in localStorage for plain reloads ---------- */
let key=null;{const m=/[#&]k=([A-Za-z0-9_-]{8,128})/.exec(location.hash);if(m){key=m[1];lsSet(KEYSTORE,key)}else key=lsGet(KEYSTORE)}
/* ---------- state ---------- */
const clone=o=>JSON.parse(JSON.stringify(o));
function norm(s){s=s&&typeof s==='object'?s:{};const r=clone(D.seed);
 for(const k of Object.keys(r.houses))if(s.houses&&s.houses[k])r.houses[k]={option:s.houses[k].option||'',note:s.houses[k].note||''};
 for(const k of Object.keys(r.farms))if(s.farms&&s.farms[k])r.farms[k]={decision:s.farms[k].decision||'',note:s.farms[k].note||''};
 for(const k of Object.keys(r.props))if(s.props&&s.props[k])r.props[k]={decision:s.props[k].decision||'pending',identification:s.props[k].identification||'',note:s.props[k].note||''};
 return r}
let S;{let o=null;try{o=JSON.parse(lsGet(KEY)||'null')}catch(e){}
 if(!o){try{const v2=JSON.parse(lsGet('yard-review-east1-v2')||'null');if(v2){o=clone(D.seed);Object.assign(o.houses,v2.houses||{});for(const [k,v] of Object.entries(v2.props||{}))if(o.props[k])o.props[k]=v}}catch(e){}}
 S=norm(o)}
let M={rev:null,dirty:false};try{Object.assign(M,JSON.parse(lsGet(META)||'{}'))}catch(e){}
/* ---------- sheets: lazy tiles, tap to zoom ---------- */
function sheetEl(k,lazy){const s=D.sheets[k],d=document.createElement('div');d.className='sheet';d.dataset.k=k;d.style.aspectRatio=s.w+'/'+s.h;d.style.background=s.bg;d.setAttribute('role','button');d.tabIndex=0;d.setAttribute('aria-label','Powiększ: '+s.alt);
 for(const [x,y,w,h,f] of s.tiles){const i=new Image();if(lazy)i.loading='lazy';i.decoding='async';i.alt='';i.className=f.endsWith('.png')?'png':'';i.width=w;i.height=h;
  i.style.cssText=`left:${x/s.w*100}%;top:${y/s.h*100}%;width:${w/s.w*100}%;height:${h/s.h*100}%`;i.src='a/'+f;d.append(i)}
 return d}
document.querySelectorAll('[data-sheet]').forEach(c=>{c.append(sheetEl(c.dataset.sheet,true))});
/* ---------- houses + props ---------- */
const hn={},fn={},hr={},fr={},pr={};
for(const h of D.houses){const box=$(h.group==='east1'?'#houses1':'#houses2'),c=document.createElement('div');c.className='card';
 c.innerHTML=`<h3>${esc(h.title)}<span class="tag ${h.group==='east1'?'e1':''}">${h.group}</span></h3><div class="hint">Dotknij obrazka, żeby go powiększyć.</div><div data-sheet-slot></div><div class="sub">Dom</div><div class="opts">`+h.options.map(([v,l])=>`<label><input type="radio" name="h${h.key}" value="${esc(v)}"> ${esc(l)}</label>`).join('')+`</div><textarea class="hn" placeholder="Uwagi do domu (opcjonalnie)"></textarea>`+
 (h.farm?`<div class="sub">Budynki gospodarcze tego podwórka (E?-1, E?-2…)</div><div class="opts"><label><input type="radio" name="f${h.key}" value="add"> dodać do gry</label><label><input type="radio" name="f${h.key}" value="regen"> przerysować (opisz)</label><label><input type="radio" name="f${h.key}" value="none"> zostawić szare pudełka</label></div><textarea class="fn" placeholder="Uwagi do budynków gospodarczych (np. czy E?-1 to na pewno stodoła, przypisanie do podwórka)"></textarea>`:'');
 c.querySelector('[data-sheet-slot]').replaceWith(sheetEl(h.key,true));box.append(c);
 hr[h.key]=[...c.querySelectorAll('input[name="h'+h.key+'"]')];hr[h.key].forEach(i=>i.onchange=()=>{S.houses[h.key].option=i.value;save()});
 hn[h.key]=c.querySelector('.hn');hn[h.key].oninput=()=>{S.houses[h.key].note=hn[h.key].value;save()};
 if(h.farm){fr[h.key]=[...c.querySelectorAll('input[name="f'+h.key+'"]')];fr[h.key].forEach(i=>i.onchange=()=>{S.farms[h.key].decision=i.value;save()});
  fn[h.key]=c.querySelector('.fn');fn[h.key].oninput=()=>{S.farms[h.key].note=fn[h.key].value;save()}}}
const tb=$('#props tbody');
for(const p of D.props){const r=document.createElement('tr');
 r.innerHTML=`<td data-l="Nr"><span class="n ${p.pending?'o':'g'}">${p.n}</span></td><td data-l="ID">${esc(p.id.replace('east1-',''))}</td><td data-l="Co to (model)">${esc(p.name)}</td><td data-l="Decyzja"><select aria-label="Decyzja: ${p.n}"><option value="add">dodać</option><option value="skip">pominąć</option><option value="pending">nie wiem</option></select></td><td data-l="Co to jest (Twoje słowa)"><input aria-label="Co to jest: ${p.n}" style="width:100%"></td>`;
 tb.append(r);const sel=r.querySelector('select'),inp=r.querySelector('input');pr[p.id]=[sel,inp];
 sel.onchange=()=>{S.props[p.id].decision=sel.value;save()};inp.oninput=()=>{S.props[p.id].identification=inp.value;save()}}
function applyState(){
 for(const h of D.houses){const o=S.houses[h.key];hr[h.key].forEach(i=>i.checked=o.option===i.value);if(document.activeElement!==hn[h.key])hn[h.key].value=o.note||'';
  if(h.farm){const f=S.farms[h.key];fr[h.key].forEach(i=>i.checked=f.decision===i.value);if(document.activeElement!==fn[h.key])fn[h.key].value=f.note||''}}
 for(const p of D.props){const s=S.props[p.id],[sel,inp]=pr[p.id];sel.value=s.decision;if(document.activeElement!==inp)inp.value=s.identification||''}
 prog()}
function prog(){const open=Object.values(S.props).filter(x=>x.decision==='pending').length,hs=D.houses.filter(h=>h.group==='east2'&&!S.houses[h.key].option).length;
 $('#progress').textContent=`Nierozstrzygnięte: rekwizyty ${open}, domy east2 ${hs}`}
function out(){return JSON.stringify(exportObj(),null,2)}
function exportObj(){return {review:D.review,strips:['east1','east2'],gameChangesApplied:false,
 houses:Object.fromEntries(D.houses.map(h=>[`house-${h.way}`,{yard:h.key,group:h.group,option:S.houses[h.key].option,note:S.houses[h.key].note}])),
 outbuildings:Object.fromEntries(D.houses.filter(h=>h.farm).map(h=>[`yard-${h.key}`,{decision:S.farms[h.key].decision,note:S.farms[h.key].note}])),
 props:Object.fromEntries(D.props.map(p=>[p.id,{n:p.n,...S.props[p.id]}]))}}
/* ---------- autosave to the game server (debounced), localStorage as the fallback ---------- */
const hhmm=t=>new Date(t||Date.now()).toLocaleTimeString('pl-PL',{hour:'2-digit',minute:'2-digit'});
function status(cls,txt){const e=$('#save');e.className=cls;e.textContent=txt}
let ver=0,inflight=false,again=false,timer=null,retry=null,conflict=false;
const persist=()=>{lsSet(KEY,JSON.stringify(S));lsSet(META,JSON.stringify(M))};
function save(){ver++;M.dirty=true;persist();prog();if(!key){status('warn','Brak klucza w linku — zapisane tylko lokalnie');return}
 status('warn','Zapisywanie…');clearTimeout(timer);timer=setTimeout(push,700)}
const hdr=()=>({'X-Review-Key':key});
function tfetch(u,o){const c=new AbortController(),t=setTimeout(()=>c.abort(),10000);return fetch(u,{...o,signal:c.signal}).finally(()=>clearTimeout(t))}
function body(){return JSON.stringify({review:D.review,client:'web-v3',savedAt:new Date().toISOString(),state:S,export:exportObj()})}
async function push(opts){
 if(!key||conflict)return;if(inflight){again=true;return}
 inflight=true;clearTimeout(retry);const myVer=ver,h={...hdr(),'Content-Type':'application/json'};if(M.rev!==null)h['X-Base-Rev']=String(M.rev);
 try{const b=body(),r=await tfetch(CFG.api+'/review/'+CFG.rid,{method:'PUT',headers:h,body:b,keepalive:!!(opts&&opts.keepalive)&&b.length<60000});
  if(r.status===401){status('err','Zły klucz w linku — zapisane lokalnie');return}
  if(r.status===409){const j=await r.json();conflict=true;showConflict(j);return}
  if(!r.ok)throw new Error('http '+r.status);
  const j=await r.json();M.rev=j.rev;if(ver===myVer)M.dirty=false;persist();
  if(ver!==myVer||again){again=false;status('warn','Zapisywanie…');setTimeout(push,50)}else status('ok','Zapisano ✓ '+hhmm())}
 catch(e){status('warn','Brak połączenia — zapisane lokalnie');retry=setTimeout(push,20000)}
 finally{inflight=false}}
async function pull(){
 if(!key)return status('warn','Brak klucza w linku — zapisane tylko lokalnie');
 try{const r=await tfetch(CFG.api+'/review/'+CFG.rid,{headers:hdr()});
  if(r.status===401)return status('err','Zły klucz w linku — zapisane lokalnie');
  if(!r.ok)throw new Error('http '+r.status);
  const j=await r.json(),d=j.doc||{};
  if(!d.state){if(M.dirty||j.rev===0){M.rev=j.rev;persist();return push()}return status('ok','Zapisano ✓ '+hhmm(j.updated_at))}
  if(M.dirty&&M.rev!==j.rev){conflict=true;return showConflict(j)}
  if(M.dirty)return push();
  if(M.rev!==j.rev||JSON.stringify(norm(d.state))!==JSON.stringify(S)){S=norm(d.state);M.rev=j.rev;M.dirty=false;persist();applyState()}
  M.rev=j.rev;persist();status('ok','Zapisano ✓ '+hhmm(j.updated_at))}
 catch(e){status('warn','Brak połączenia — zapisane lokalnie');retry=setTimeout(()=>M.dirty?push():pull(),20000)}}
function showConflict(j){const b=$('#banner');b.style.display='block';status('err','Konflikt — inna wersja na serwerze');
 b.innerHTML=`Na serwerze jest nowsza wersja (zapisana ${hhmm(j.updated_at)}, pewnie z innego urządzenia). <br><button id="cs">Wczytaj z serwera</button><button id="cm">Zachowaj moje i zapisz</button>`;
 $('#cs').onclick=async()=>{b.style.display='none';conflict=false;M.dirty=false;const r=await fetch(CFG.api+'/review/'+CFG.rid,{headers:hdr()});const x=await r.json();if(x.doc&&x.doc.state){S=norm(x.doc.state)}M.rev=x.rev;persist();applyState();status('ok','Zapisano ✓ '+hhmm(x.updated_at))};
 $('#cm').onclick=()=>{b.style.display='none';conflict=false;M.rev=j.rev;persist();push()}}
addEventListener('online',()=>M.dirty?push():pull());
document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='hidden'){if(M.dirty&&key&&!conflict){clearTimeout(timer);push({keepalive:true})}}else if(!M.dirty&&key&&!conflict&&!inflight)pull()});
/* ---------- backup: copy / download / import JSON ---------- */
$('#copy').onclick=async()=>{try{await navigator.clipboard.writeText(out());$('#notice').textContent='Skopiowano JSON.'}catch(e){window.prompt('Skopiuj (Ctrl+C):',out())}};
$('#dl').onclick=()=>{const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([out()],{type:'application/json'}));a.download='yard-review-east1-v3-decisions.json';a.click()};
$('#imp').onchange=async e=>{try{const j=JSON.parse(await e.target.files[0].text());
 for(const h of D.houses){const x=j.houses&&j.houses[`house-${h.way}`];if(x)S.houses[h.key]={option:x.option||(h.group==='east1'?'v1':''),note:x.note||''};const y=j.outbuildings&&j.outbuildings[`yard-${h.key}`];if(y)S.farms[h.key]={decision:y.decision||'',note:y.note||''}}
 for(const p of D.props){const x=j.props&&j.props[p.id];if(x)S.props[p.id]={decision:x.decision||'pending',identification:x.identification||'',note:x.note||''}}
 applyState();save();$('#notice').textContent='Wczytano JSON.'}catch(err){$('#notice').textContent='Nie udało się wczytać pliku.'}e.target.value=''};
/* ---------- zoom view: 1 image pixel = 1 CSS pixel by default; pixel art stays crisp ---------- */
let lbK=null,lbZ=1;
function lbSet(z){const s=D.sheets[lbK],vw=$('#lbs').clientWidth;lbZ=Math.max(.15,Math.min(4,z));$('#lbin').style.width=Math.round(s.w*lbZ)+'px';$('#lb').classList.toggle('px',lbZ*(devicePixelRatio||1)>1.4);$('#lbt').textContent=s.alt+' · '+Math.round(lbZ*100)+'%'}
function lbOpen(k){lbK=k;const s=D.sheets[k],inn=$('#lbin');inn.replaceChildren(sheetEl(k,false));$('#lb').classList.add('on');document.body.style.overflow='hidden';
 const fit=Math.min(1,($('#lbs').clientWidth-2)/s.w);lbSet(innerWidth<=900?1:fit);$('#lbs').scrollTo(0,0);$('#lbx').focus()}
function lbClose(){$('#lb').classList.remove('on');document.body.style.overflow=''}
document.addEventListener('click',e=>{const s=e.target.closest('main .sheet');if(s)lbOpen(s.dataset.k)});
document.addEventListener('keydown',e=>{if(e.key==='Escape')lbClose();if((e.key==='Enter'||e.key===' ')&&e.target.matches&&e.target.matches('main .sheet')){e.preventDefault();lbOpen(e.target.dataset.k)}});
$('#lbx').onclick=lbClose;$('#lbp').onclick=()=>lbSet(lbZ*1.4);$('#lbm').onclick=()=>lbSet(lbZ/1.4);$('#lb1').onclick=()=>lbSet(1);
$('#lbf').onclick=()=>lbSet(Math.min(1,($('#lbs').clientWidth-2)/D.sheets[lbK].w));
applyState();persist();pull();
</script></body></html>'''

if __name__ == "__main__":
    main()
