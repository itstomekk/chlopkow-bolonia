"""Build a self-contained review sheet for one strip of real yards. Local only, never edits the game.

    python gen/build_yard_review.py --strip east1 [--out PATH]

Two parts, both decided by Tomek and exported as JSON back into the chat:
  1. Houses: satellite + Street View + the current sprite, decision ok / regenerate + note.
  2. Small yard elements: candidate boxes on the real satellite crop (gen/streetview/yard_props_detect.py, Codex Luna),
     Tomek says what each thing is and whether to add it. Boxes are review regions, not verified outlines.
Same flow as gen/build_yard_evidence_review.py (J12): decisions persist in localStorage, export/import JSON.
"""
import argparse
import base64
import io
import json
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
REFS = Path(r"C:\Users\Lenovo\Hermes\image-gen\2026-10-03-chlopkow-building-refs")
A = 2                      # map px per metre (yard_strip.A)
SHIFT = (5, 3)             # OSM -> satellite offset (yard_strip.SHIFT); map coords = satellite frame - SHIFT
YARD_NAMES = {"E1": "E1 (bez numeru, za 19)"}
# Duplicate crop detections across overlapping plots: retain the best/user-answered card once.
MERGED = {"east1-19-p1": ["east1-E1-p2"], "east1-19-p4": ["east1-20-p3"]}
REMOVED = {"east1-23-p1", "east1-23-p2", *(x for xs in MERGED.values() for x in xs)}


def data_image(im, fmt="JPEG", maxw=None):
    im = im.convert("RGB") if fmt == "JPEG" else im
    if maxw and im.width > maxw:
        im = im.resize((maxw, round(im.height * maxw / im.width)), Image.Resampling.LANCZOS)
    buf = io.BytesIO(); im.save(buf, format=fmt, **({"quality": 85} if fmt == "JPEG" else {}))
    return f"data:image/{fmt.lower()};base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def frame(plan, yard):
    """Same framing as yard_strip.gen(): returns (left, top, size) of the 1024 sat_clean crop in satellite-frame px."""
    pts = [p for b in plan if b["yard"] == yard for p in b["pts"]]
    xs, ys = zip(*pts)
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    half = (max(max(xs) - min(xs), max(ys) - min(ys)) / 2 / A + 8) * A
    return cx - half, cy - half, 2 * half


def build(strip, out):
    sdir = ROOT / ("gen/yards/strip" if strip == "west" else f"gen/yards/strip_{strip}")
    plan = json.loads((sdir / "plan.json").read_text(encoding="utf-8"))
    plc = sdir / "placements_with_east1.json" if strip == "east1" else ROOT / "gen/yards/final/placements.json"
    sprites = {q["id"]: q["png"] for q in json.loads(plc.read_text(encoding="utf-8"))}
    houses, props, yards = [], [], {}
    placement_data = json.loads(plc.read_text(encoding="utf-8"))
    place_by_id = {q["id"]: q for q in placement_data}
    map_sheet_path = ROOT / "gen/pilot_2026-10-03-houses" / f"compare{('9' if strip == 'west' else '_' + strip)}.png"
    map_sheet = Image.open(map_sheet_path).convert("RGB") if map_sheet_path.exists() else None
    # yard_strip compares four vertically stacked panels, each 3x the selected map BOX.
    map_box = (860, 3870, 1180, 4400) if strip == "east1" else None
    panel_h = (map_box[3] - map_box[1]) * 3 if map_box else 0
    new_map_panel_y = 2 * (panel_h + 26) + 26
    for b in sorted((b for b in plan if b["house"]), key=lambda b: b["c"][0]):
        ref = REFS / f"w{b['id']}"
        spr = Image.open(ROOT / sprites[b["id"]]).convert("RGBA")
        bg = Image.new("RGBA", spr.size, (92, 120, 70, 255)); bg.alpha_composite(spr)
        q = place_by_id[b["id"]]
        map_preview = None
        if map_sheet is not None and map_box:
            cx = round((q["x"] + spr.width / 2 - map_box[0]) * 3)
            by = round(new_map_panel_y + (q["y"] + spr.height - map_box[1]) * 3)
            r = 90 * 3; up = 95 * 3; down = 35 * 3
            crop = map_sheet.crop((max(0, cx-r), max(new_map_panel_y, by-up), min(map_sheet.width, cx+r), min(new_map_panel_y+panel_h, by+down)))
            mark = ImageDraw.Draw(crop)
            # Footprint centroid in the actual map coordinate frame, with a subtle crosshair.
            tx = round((b["c"][0] - SHIFT[0] - map_box[0]) * 3) - max(0, cx-r)
            ty = round(new_map_panel_y + (b["c"][1] - SHIFT[1] - map_box[1]) * 3) - max(new_map_panel_y, by-up)
            mark.ellipse((tx-9, ty-9, tx+9, ty+9), outline="#ffe078", width=3)
            mark.line((tx-15, ty, tx+15, ty), fill="#ffe078", width=2); mark.line((tx, ty-15, tx, ty+15), fill="#ffe078", width=2)
            mark.rectangle((5, 5, 78, 27), fill="#182321"); mark.text((10, 9), "PÓŁNOC ↑", fill="#ffe078")
            map_preview = data_image(crop, maxw=600)
        houses.append({"id": f"house-{b['id']}", "way": b["id"], "yard": b["yard"],
                       "sat": data_image(Image.open(ref / "sat.png"), maxw=420),
                       "sv": data_image(Image.open(ref / "sv_sheet.jpg"), maxw=900),
                       "sprite": data_image(bg.resize((spr.width * 4, spr.height * 4), Image.Resampling.NEAREST), "PNG"),
                       "map": map_preview, "mapXY": [round(b["c"][0]-SHIFT[0]), round(b["c"][1]-SHIFT[1])]})
    for yard in sorted({b["yard"] for b in plan if b["yard"]}):
        d = sdir / f"yard_{yard}"
        if not (d / "props_luna.json").exists(): continue
        im = Image.open(d / "sat_clean.png").convert("RGB")
        left, top, size = frame(plan, yard); k = size / im.width
        marked = im.copy(); dr = ImageDraw.Draw(marked)
        candidates = json.loads((d / "props_luna.json").read_text(encoding="utf-8"))
        for i, c in enumerate(candidates, 1):
            cid = f"{strip}-{yard}-p{i}"
            if strip == "east1" and cid in REMOVED:
                continue
            x0, y0, x1, y1 = [max(0, min(1024, int(v))) for v in c["box"]]
            if x1 - x0 < 8 or y1 - y0 < 8: continue
            m = 40   # show context around the box
            crop = im.crop((max(0, x0 - m), max(0, y0 - m), min(1024, x1 + m), min(1024, y1 + m))).copy()
            ImageDraw.Draw(crop).rectangle((x0 - max(0, x0 - m), y0 - max(0, y0 - m), x1 - max(0, x0 - m), y1 - max(0, y0 - m)), outline="#ffdf75", width=2)
            dr.rectangle((x0, y0, x1, y1), outline="#ffdf75", width=4)
            dr.rectangle((x0, y0, x0 + 26, y0 + 24), fill="#ffdf75"); dr.text((x0 + 7, y0 + 5), str(i), fill="#182321")
            mx, my = left + (x0 + x1) / 2 * k - SHIFT[0], top + (y0 + y1) / 2 * k - SHIFT[1]
            props.append({"id": cid, "yard": yard, "index": i, "box": [x0, y0, x1, y1],
                          "mergedFrom": MERGED.get(cid, []), "title": c.get("title", "?"), "observation": c.get("observation", ""),
                          "alternatives": c.get("alternatives", []), "confidence": c.get("confidence", "Niska"),
                          "sizeM": [round((x1 - x0) * k / A, 1), round((y1 - y0) * k / A, 1)],
                          "mapPointApprox": [round(mx), round(my)], "suggested": "",
                          "source": str((d / "sat_clean.png").relative_to(ROOT)).replace("\\", "/"),
                          "crop": data_image(crop.resize((crop.width * 2, crop.height * 2), Image.Resampling.LANCZOS) if crop.width < 300 else crop, maxw=640)})
        yards[yard] = {"name": YARD_NAMES.get(yard, yard), "marked": data_image(marked), "full": data_image(im)}
    review = f"yard-review-{strip}-v3"
    decisions_file = ROOT / "plans/yard-review-east1-v1-decisions.json" if strip == "east1" else None
    old = json.loads(decisions_file.read_text(encoding="utf-8")) if decisions_file and decisions_file.exists() else {}
    valid_ids = {f"house-{b['id']}" for b in plan if b["house"]} | {p["id"] for p in props}
    seed = {key: value for key, value in old.get("decisions", {}).items() if key in valid_ids}
    data = {"review": review, "strip": strip, "houses": houses, "candidates": props, "yards": yards, "seed": seed,
            "dedupeNote": "Po scaleniu wykrytych powtórek zostało jedno pytanie na jeden obiekt: auto i plac (20/23), wóz (19/E1) i żywopłot (19/20). Zachowałem Twoje odpowiedzi z v1."}
    html = TEMPLATE.replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/")).replace("__STRIP__", strip)
    out.parent.mkdir(parents=True, exist_ok=True); out.write_text(html, encoding="utf-8")
    print(f"{len(houses)} houses, {len(props)} candidates in {len(yards)} yards -> {out}")


TEMPLATE = r'''<!doctype html>
<html lang="pl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Chłopków · podwórka __STRIP__ · przegląd</title>
<style>
:root{color-scheme:dark;--bg:#151c1b;--card:#1f2926;--text:#eeeade;--muted:#b6b9a8;--line:#425048;--accent:#eed392}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:16px/1.5 system-ui,sans-serif}
main{max-width:1280px;margin:auto;padding:28px}h1{font-size:clamp(28px,4vw,42px);line-height:1.1;margin:12px 0}h2{margin:36px 0 12px}
p{margin:8px 0}.muted{color:var(--muted)}.eyebrow{letter-spacing:.14em;text-transform:uppercase;color:var(--accent);font-size:12px}
.tools{position:sticky;top:0;z-index:2;display:flex;align-items:center;gap:12px;flex-wrap:wrap;padding:14px 0;background:var(--bg);border-bottom:1px solid var(--line)}
button,select,input,textarea,.import-label{font:inherit;color:var(--text);background:#26352e;border:1px solid var(--line);border-radius:6px;padding:8px 10px}
button,.import-label{cursor:pointer}#export{background:var(--accent);color:#19251d;border-color:var(--accent);font-weight:700}.import-label input{display:none}
#notice{font-size:14px;color:var(--accent)}label{display:block;margin-top:10px;font-size:14px;color:var(--muted)}label input,label select,label textarea{display:block;width:100%;margin-top:4px}
textarea{min-height:60px}.card{background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}
.card[data-state="ok"],.card[data-state="add"]{border-color:#96b87b}.card[data-state="regen"]{border-color:#e0a050}.card[data-state="skip"]{border-color:#8c8e89}.card[hidden]{display:none}
.house{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:0;margin-top:16px}.house img{width:100%;height:250px;object-fit:contain;display:block;cursor:zoom-in}.house .sv{background:#111817}.house .map{background:#111817}.house .spr{background:#111817;display:flex;align-items:center;justify-content:center}.house .spr img{width:auto;max-width:100%;image-rendering:pixelated}.house .body{grid-column:1/-1;padding:16px;display:grid;grid-template-columns:1fr 2fr;gap:16px}
.overview{display:flex;gap:18px;align-items:flex-start;background:var(--card);padding:16px;border-radius:10px}.overview img{width:320px;max-width:100%;cursor:zoom-in}
.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin-top:16px}.crop-wrap{background:#111817;height:240px;display:flex;align-items:center;justify-content:center}
.crop{width:100%;height:100%;object-fit:contain;cursor:zoom-in}.body{padding:16px}.confidence{font-size:12px;color:var(--accent);text-transform:uppercase}
.card h3{font-size:19px;margin:4px 0}.coords{font-size:12px;color:var(--muted);margin-top:8px}
dialog{max-width:96vw;max-height:96vh;background:#000;border:0;padding:0}dialog img{max-width:94vw;max-height:90vh;display:block}#close{position:absolute;right:8px;top:8px}
@media(max-width:900px){.grid{grid-template-columns:1fr}.house{grid-template-columns:repeat(2,minmax(0,1fr))}.house .body{grid-template-columns:1fr}}@media(max-width:540px){.house{grid-template-columns:1fr}}
</style></head><body><main>
<div class="eyebrow">Chłopków Bolonia / prawdziwe podwórka / __STRIP__</div>
<h1>Przegląd: domy i drobne rzeczy na podwórkach</h1>
<p>Część 1: pięć domów. Satelita, Street View, obecny rysunek z gry (×4) ORAZ mały wycinek mapy z domem ustawionym w jego rzeczywistym kierunku. Żółty krzyż pokazuje środek obrysu.</p>
<p>Część 2: miejsca na podwórkach, które wyglądają na drobne rzeczy (to prawdziwe wycinki satelity, ramki wskazał model, nie są pewne). Napisz, co to jest, i czy dodać to do gry. W v3 scaliłem powtarzające się pytania między nakładającymi się zdjęciami (auto/plac 20–23, wóz 19–E1, żywopłot 19–20); Twoje odpowiedzi zostały przeniesione.</p>
<div class="tools"><strong id="progress"></strong><select id="filter"><option value="all">Wszystkie</option><option value="pending">Nierozstrzygnięte</option><option value="done">Rozstrzygnięte</option></select>
<button id="copy">Kopiuj JSON</button><button id="export">Pobierz JSON</button><label class="import-label" style="margin:0;color:var(--text)">Wczytaj JSON<input type="file" id="import" accept=".json,application/json"></label></div>
<p id="notice" role="status">Decyzje zapisują się lokalnie. Skopiuj JSON przyciskiem albo pobierz plik. Ten arkusz nie zmienia gry.</p><textarea id="copyFallback" hidden aria-label="JSON do ręcznego skopiowania" style="width:100%;min-height:260px"></textarea>
<h2>1. Domy</h2><div id="houses"></div>
<h2>2. Drobne rzeczy na podwórkach</h2><div id="yards"></div>
<p class="muted">Koordynaty x,y to przybliżony środek ramki na mapie gry. Wymiary w metrach są przybliżone.</p>
</main><dialog id="zoom"><button id="close">Zamknij</button><img alt="Powiększenie"></dialog>
<script>
'use strict';
const DATA=__DATA__;
const KEY='bolonia-'+DATA.review;
const ITEMS=[...DATA.houses.map(h=>({id:h.id,kind:'house'})),...DATA.candidates.map(c=>({id:c.id,kind:'prop'}))];
const ACTIONS={house:new Set(['pending','ok','regen']),prop:new Set(['pending','add','skip','better-photo'])};
const defaults=()=>Object.fromEntries(ITEMS.map(i=>[i.id,{decision:'pending',identification:'',note:''}]));
let decisions={...defaults(),...DATA.seed};
function validate(p){if(!p||p.review!==DATA.review||!p.decisions)throw Error('To nie jest ten arkusz.');const f=defaults();
  for(const i of ITEMS){const d=p.decisions[i.id];if(!d)continue;if(!ACTIONS[i.kind].has(d.decision)||typeof d.note!=='string')throw Error('Zła decyzja dla '+i.id);
  f[i.id]={decision:d.decision,identification:String(d.identification||''),note:d.note};}return f;}
function payload(){return {review:DATA.review,strip:DATA.strip,gameChangesApplied:false,decisions,
  provenance:DATA.candidates.map(({id,yard,source,box,mapPointApprox,sizeM,title,mergedFrom})=>({id,yard,source,box,mapPointApprox,sizeM,guess:title,mergedFrom})),
  houses:DATA.houses.map(({id,way,yard})=>({id,way,yard}))};}
try{const s=localStorage.getItem(KEY);if(s)decisions=validate(JSON.parse(s));}catch(e){}
function save(){try{localStorage.setItem(KEY,JSON.stringify(payload()));}catch(e){document.querySelector('#notice').textContent='Nie da się zapisać lokalnie. Pobierz JSON przed zamknięciem.';}refresh();}
function refresh(){const n=ITEMS.filter(i=>decisions[i.id].decision!=='pending').length;document.querySelector('#progress').textContent=n+' / '+ITEMS.length+' rozstrzygniętych';
  const f=document.querySelector('#filter').value;document.querySelectorAll('.card').forEach(c=>{const done=decisions[c.dataset.id].decision!=='pending';c.dataset.state=decisions[c.dataset.id].decision;c.hidden=f==='pending'?done:f==='done'?!done:false;});}
function zoom(src){document.querySelector('#zoom img').src=src;document.querySelector('#zoom').showModal();}
function bind(card,id){for(const [sel,key] of [['.decision','decision'],['.identification','identification'],['.note','note']]){const el=card.querySelector(sel);if(!el)continue;el.value=decisions[id][key];
  el.addEventListener(key==='decision'?'change':'input',()=>{decisions[id][key]=el.value;save();});}card.querySelectorAll('img').forEach(i=>i.onclick=()=>zoom(i.src));}
function render(){const H=document.querySelector('#houses');H.replaceChildren();
 for(const h of DATA.houses){const c=document.createElement('article');c.className='card house';c.dataset.id=h.id;
  c.innerHTML='<img class="sat" alt="satelita"><div class="sv"><img alt="Street View"></div><div class="map"><img alt="dom na mapie north-up"></div><div class="spr"><img alt="rysunek w grze"></div><div class="body"><div><h3></h3><p class="muted">satelita · Street View · mapa z orientacją · rysunek (×4)</p><div class="coords"></div></div><div><label>Decyzja<select class="decision"><option value="pending">Jeszcze nie wiem</option><option value="ok">OK, zostaje</option><option value="regen">Narysować od nowa</option></select></label><label>Co się nie zgadza / co zmienić<textarea class="note" placeholder="np. za niski, dach powinien być czerwony, brak ganku, za duży"></textarea></label></div></div>';
  c.querySelector('.sat').src=h.sat;c.querySelector('.sv img').src=h.sv;c.querySelector('.map img').src=h.map;c.querySelector('.spr img').src=h.sprite;c.querySelector('h3').textContent='Dom '+h.yard+' · OSM '+h.way;c.querySelector('.coords').textContent='na mapie · x,y ≈ '+h.mapXY.join(',')+' · północ u góry';bind(c,h.id);H.append(c);}
 const Y=document.querySelector('#yards');Y.replaceChildren();
 for(const [yard,info] of Object.entries(DATA.yards)){const s=document.createElement('section');
  s.innerHTML='<h3>Podwórko '+info.name+'</h3><div class="overview"><img class="m" alt="zaznaczenia"><div><p>Żółte ramki odpowiadają kartom poniżej.</p><button class="clean">Zdjęcie bez ramek</button></div></div><div class="grid"></div>';
  s.querySelector('.m').src=info.marked;s.querySelector('.m').onclick=()=>zoom(info.marked);s.querySelector('.clean').onclick=()=>zoom(info.full);
  for(const p of DATA.candidates.filter(p=>p.yard===yard)){const c=document.createElement('article');c.className='card';c.dataset.id=p.id;
   c.innerHTML='<div class="crop-wrap"><img class="crop" alt="wycinek"></div><div class="body"><span class="confidence"></span><h3></h3><p class="obs"></p><p class="muted alt"></p><p class="merged muted"></p><label>Decyzja<select class="decision"><option value="pending">Jeszcze nie wiem</option><option value="add">Dodaj do gry</option><option value="skip">Pomiń</option><option value="better-photo">Nie wiem, co to jest</option></select></label><label>Co to jest<input class="identification" placeholder="np. kupa drewna, przyczepa, tunel foliowy"></label><label>Uwagi<textarea class="note" placeholder="kolor, wielkość, czy coś obok"></textarea></label><div class="coords"></div></div>';
   c.querySelector('.crop').src=p.crop;c.querySelector('.confidence').textContent='pewność: '+p.confidence;c.querySelector('h3').textContent=p.index+'. '+p.title+' (zgadywanie)';
   c.querySelector('.obs').textContent=p.observation;c.querySelector('.alt').textContent='Może: '+p.alternatives.join(' / ');c.querySelector('.merged').textContent=p.mergedFrom?.length?'To samo miejsce/scalony kadr: '+p.mergedFrom.join(', '):'';
      c.querySelector('.coords').textContent='x,y ≈ '+p.mapPointApprox.join(',')+' · ok. '+p.sizeM.join('×')+' m · '+p.id;bind(c,p.id);s.querySelector('.grid').append(c);}
  Y.append(s);}refresh();}
document.querySelector('#filter').onchange=refresh;document.querySelector('#close').onclick=()=>document.querySelector('#zoom').close();
document.querySelector('#copy').onclick=async()=>{const text=JSON.stringify(payload(),null,2),box=document.querySelector('#copyFallback'),notice=document.querySelector('#notice');
  try{if(!navigator.clipboard?.writeText)throw Error('clipboard unavailable');await navigator.clipboard.writeText(text);box.hidden=true;notice.textContent='JSON skopiowany do schowka.';}
  catch{box.hidden=false;box.value=text;box.focus();box.select();const ok=document.execCommand('copy');notice.textContent=ok?'JSON skopiowany. Jeśli nie, zaznaczyłem go poniżej: Ctrl+C.':'Schowek zablokowany. JSON jest zaznaczony poniżej: Ctrl+C.';}};
document.querySelector('#export').onclick=()=>{const u=URL.createObjectURL(new Blob([JSON.stringify(payload(),null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=u;a.download=DATA.review+'-decisions.json';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);};
document.querySelector('#import').onchange=async e=>{try{const f=e.target.files[0];if(!f)return;decisions=validate(JSON.parse(await f.text()));save();render();document.querySelector('#notice').textContent='Wczytano decyzje.';}catch(err){document.querySelector('#notice').textContent='Nie wczytano: '+err.message;}finally{e.target.value='';}};
render();
</script></body></html>'''

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--strip", default="east1")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    build(a.strip, a.out or ROOT / f"asset-review/yard-review-{a.strip}/review.html")
