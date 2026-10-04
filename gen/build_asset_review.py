"""Build a local, self-contained asset review sheet (roadmap task A0).

Reads ONLY shipped game images (docs/img/) and the landmark sources that
osm/render_map.py composites into the map (gen/lm_*.png). Never reads
references/ (private photos).

Output: asset-review/<date>/review.html (gitignored), one card per asset with
a stable ID and keep/adjust/regenerate/retire buttons.

    python gen/build_asset_review.py [YYYY-MM-DD]
"""
import base64
import datetime
import html
import io
import json
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(ROOT, 'docs', 'img')
DATE = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().isoformat()
OUT = os.path.join(ROOT, 'asset-review', DATE)

# NPC atlas slot order (docs/js/game.js NPC_IDX + gen/build_npcs.py ORDER)
NPC_SLOTS = ['kasia', 'marcin', 'damian', 'grandpa', 'irenka', 'kuba', 'michal', 'mateusz',
             'patryk', 'zbyszek', 'wesoly_swiat', 'edytka', 'renik', 'soltys']
CHAR_H = 40          # in-game character height, world px (game.js CHAR_H)
MAX_W = 360          # thumbnail width cap, CSS px

cards = []


def b64(im, scale=None, max_w=MAX_W, max_h=260, smooth=False):
    im = im.convert('RGBA')
    if scale is None:
        scale = min(max_w / im.width, max_h / im.height)
        if scale >= 1:
            scale = max(1, int(scale))   # integer upscale for pixel art
    w, h = max(1, round(im.width * scale)), max(1, round(im.height * scale))
    im = im.resize((w, h), Image.LANCZOS if (smooth or scale < 1) else Image.NEAREST)
    buf = io.BytesIO()
    im.save(buf, 'PNG', optimize=True)
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()


def card(aid, cat, title, im, path, kind, note='', scale=None):
    cards.append(dict(id=aid, cat=cat, title=title, src=b64(im, scale), path=path, kind=kind,
                      size=f'{im.width}x{im.height}', note=note))


def img(rel):
    return Image.open(os.path.join(ROOT, rel)).convert('RGBA')


# ---------------------------------------------------------------- characters
for name in ['arek_sheet_8dir', 'arek_sheet', 'marcin_sheet', 'damian_sheet', 'edytka_sheet', 'renik_sheet']:
    rel = f'docs/img/{name}.png'
    meta = json.load(open(os.path.join(IMG, f'{name}.json'), encoding='utf-8'))
    sheet = img(rel)
    fr = meta['anims']['walk_down']['frames'][0]
    frame = sheet.crop((fr['x'], fr['y'], fr['x'] + fr['w'], fr['y'] + fr['h']))
    pid = name.replace('_sheet', '')
    card(f'char.player.{pid}', 'Postacie (gracz)', f'{pid} - pojedyncza klatka', frame, rel,
         'packed sheet', f'{len(meta["anims"])} animacji, klatka {fr["w"]}x{fr["h"]}')
    card(f'char.player.{pid}.sheet', 'Postacie (gracz)', f'{pid} - cały arkusz', sheet, rel, 'packed sheet', scale=0.35)

npcs = img('docs/img/npcs.png')
for i, n in enumerate(NPC_SLOTS):
    cell = npcs.crop((i * 130, 0, i * 130 + 130, 170))
    if cell.getbbox():
        card(f'char.npc.{n}', 'Postacie (NPC)', n, cell, 'docs/img/npcs.png', 'packed atlas', f'slot {i}')
card('char.npc.soltys_church', 'Postacie (NPC)', 'Sołtys (kościół)', img('docs/img/church/soltys.png'),
     'docs/img/church/soltys.png', 'shipped file')

# ---------------------------------------------------------------- animals / vehicles / items
card('animal.frodo.walk', 'Zwierzęta', 'Frodo - chód', img('docs/img/frodo.png'), 'docs/img/frodo.png', 'packed sheet')
card('animal.frodo.idle', 'Zwierzęta', 'Frodo - pozy', img('docs/img/frodo_idle.png'), 'docs/img/frodo_idle.png', 'packed sheet')
crit = img('docs/img/critters.png')
cmeta = json.load(open(os.path.join(IMG, 'critters.json'), encoding='utf-8'))
cell = cmeta['cell']
for k, r in cmeta['rows'].items():
    row = crit.crop((0, r['row'] * cell, 4 * cell, (r['row'] + 1) * cell))
    card(f'animal.critter.{k}', 'Zwierzęta', k, row, 'docs/img/critters.png', 'packed atlas', 'klatki: ' + ', '.join(r['frames']))
card('animal.minigame_sheet', 'Zwierzęta', 'zwierzęta minigier (świnia, psy...)', img('docs/img/animals.png'),
     'docs/img/animals.png', 'packed sheet', 'rysowane z wygładzaniem (rozmyte) - minigames.js:335')

veh = img('docs/img/vehicles.png')
vmeta = json.load(open(os.path.join(IMG, 'vehicles.json'), encoding='utf-8'))
for k, r in vmeta['rows'].items():
    row = veh.crop((0, r['row'] * vmeta['cell'], 4 * vmeta['cell'], (r['row'] + 1) * vmeta['cell']))
    card(f'vehicle.{k}', 'Pojazdy i przedmioty', k, row, 'docs/img/vehicles.png', 'packed atlas')
card('vehicle.car_red', 'Pojazdy i przedmioty', 'czerwone auto', img('docs/img/car_red.png'), 'docs/img/car_red.png', 'shipped file')
card('item.trash', 'Pojazdy i przedmioty', 'śmieci', img('docs/img/trash.png'), 'docs/img/trash.png', 'packed sheet')

# ---------------------------------------------------------------- landmark sources
for k in ['church', 'windmill', 'shop', 'barn', 'house_generic', 'shrine_stone', 'shrine_white',
          'shrine_fenced', 'cross_iron', 'village_sign']:
    rel = f'gen/lm_{k}.png'
    if os.path.exists(os.path.join(ROOT, rel)):
        card(f'landmark.{k}', 'Budynki i obiekty (źródła)', k, img(rel), rel, 'source image',
             'wklejany do mapy przez osm/render_map.py (skalowany LANCZOS)')

# ---------------------------------------------------------------- map crops
MAP = json.load(open(os.path.join(ROOT, 'docs', 'map.json'), encoding='utf-8'))
ground = Image.open(os.path.join(IMG, 'map_ground.png')).convert('RGBA')
objs = Image.open(os.path.join(IMG, 'map_objects.png')).convert('RGBA')
world = ground.copy()
world.alpha_composite(objs)
del ground, objs


def crop(cx, cy, w=320, h=200):
    x0 = max(0, min(MAP['w'] - w, int(cx - w / 2)))
    y0 = max(0, min(MAP['h'] - h, int(cy - h / 2)))
    return world.crop((x0, y0, x0 + w, y0 + h)), x0, y0


# scale context: Arek at real game size on the spawn crop
sp = MAP['spawn']
c, x0, y0 = crop(sp['x'], sp['y'])
a = img('docs/img/arek_sheet_8dir.png').crop((0, 0, 130, 170))
k = CHAR_H / (170 - 6 - 14)
a = a.resize((round(130 * k), round(170 * k)), Image.NEAREST)
c.alpha_composite(a, (int(sp['x'] - x0 - a.width / 2), int(sp['y'] - y0 - a.height + 6 * k)))
card('map.context.spawn', 'Mapa - kontekst', 'start + Arek w skali gry', c, 'docs/img/map_ground.png + map_objects.png',
     'procedural', 'tak to wygląda w grze (2x)', scale=2)

for lm in MAP['landmarks']:
    c, _, _ = crop(lm['x'], lm['y'])
    card(f'map.place.{lm["key"]}', 'Mapa - miejsca', lm['name'], c, 'map_ground + map_objects', 'procedural / composited', scale=2)
for s in MAP['shrines']:
    c, _, _ = crop(s['x'], s['y'], 200, 140)
    card(f'map.shrine.{s["spot"]}', 'Mapa - miejsca', f'kapliczka/krzyż: {s["kind"]}', c, 'map_objects', 'composited', scale=2)

# procedural trees: one example per species (village + forest)
seen = set()
for o in MAP['objects']:
    key = (o.get('kind'), o.get('species'))
    if 'species' in o and key not in seen:
        seen.add(key)
        pad = 12
        c = world.crop((o['x'] - pad, o['y'] - pad, o['x'] + o['w'] + pad, o['y'] + o['h'] + pad))
        card(f'tree.{o.get("kind")}.{o["species"]}', 'Drzewa (proceduralne)', f'{o["species"]} ({o.get("kind")})', c,
             'osm/render_map.py tree()', 'procedural', scale=3)

# procedural houses: spread of sizes
houses = sorted([o for o in MAP['objects'] if 'species' not in o], key=lambda o: o['w'] * o['h'])
pick = [houses[int(i * (len(houses) - 1) / 7)] for i in range(8)]
for i, o in enumerate(pick):
    pad = 16
    c = world.crop((o['x'] - pad, o['y'] - pad, o['x'] + o['w'] + pad, o['y'] + o['h'] + pad))
    card(f'house.procedural.{i + 1}', 'Domy (proceduralne)', f'dom #{i + 1} ({o["w"]}x{o["h"]})', c,
         'osm/render_map.py (budynki z OSM)', 'procedural', scale=3)
# a dense street-level crop
c, _, _ = crop(2150, 4300, 420, 260)
card('map.context.street', 'Mapa - kontekst', 'ulica - zabudowa', c, 'map_ground + map_objects', 'procedural', scale=1.5)
del world

# ---------------------------------------------------------------- church / memories / UI
for k in json.load(open(os.path.join(IMG, 'church', 'manifest.json'), encoding='utf-8')):
    if k == 'soltys':
        continue
    rel = f'docs/img/church/{k}.png'
    card(f'church.{k}', 'Kościół (wnętrze)', k, img(rel), rel, 'shipped file')
for k in ['procession', 'memorial', 'wooden_cross']:
    rel = f'docs/img/memories/{k}.png'
    card(f'memory.{k}', 'Wspomnienia (cmentarz)', k, img(rel), rel, 'shipped file')
card('ui.splash', 'UI / ekran tytułowy', 'splash', img('docs/img/splash.png'), 'docs/img/splash.png', 'shipped file')
card('ui.sokol_watermark', 'UI / ekran tytułowy', 'Sokół watermark', img('docs/img/sokol_watermark.png'),
     'docs/img/sokol_watermark.png', 'shipped file')

# ---------------------------------------------------------------- html
os.makedirs(OUT, exist_ok=True)
json.dump([{k: v for k, v in c.items() if k != 'src'} for c in cards],
          open(os.path.join(OUT, 'assets.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

groups = {}
for c in cards:
    groups.setdefault(c['cat'], []).append(c)

LABELS = [('anchor', 'wzór stylu'), ('keep', 'zostaw'), ('adjust', 'popraw'), ('regen', 'od nowa'), ('retire', 'usuń')]
parts = []
for cat, items in groups.items():
    parts.append(f'<h2>{html.escape(cat)} <span class=n>{len(items)}</span></h2><div class=grid>')
    for c in items:
        btns = ''.join(f'<button data-v="{v}">{t}</button>' for v, t in LABELS)
        parts.append(
            f'<div class=card data-id="{c["id"]}"><div class=pic><img src="{c["src"]}"></div>'
            f'<b>{html.escape(c["title"])}</b><code>{c["id"]}</code>'
            f'<small>{html.escape(c["path"])} · {c["size"]} · {c["kind"]}</small>'
            + (f'<small class=note>{html.escape(c["note"])}</small>' if c['note'] else '') +
            f'<div class=btns>{btns}</div><input placeholder="uwaga (opcjonalnie)"></div>')
    parts.append('</div>')

page = f"""<!doctype html><meta charset=utf-8><title>Bolonia - przegląd assetów {DATE}</title>
<style>
body{{margin:0;padding:8px}} h1{{font-size:18px;margin:4px 0}} h2{{font-size:15px;margin:18px 0 6px}}
.n{{color:var(--muted-foreground,#888);font-weight:normal}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:8px}}
.card{{border:1px solid var(--border,#ccc);border-radius:6px;padding:6px;display:flex;flex-direction:column;gap:3px;background:var(--card,transparent)}}
.pic{{background:repeating-conic-gradient(#8883 0 25%,#0000 0 50%) 0 0/12px 12px;display:flex;justify-content:center;align-items:center;min-height:120px;max-height:260px;overflow:auto}}
.pic img{{image-rendering:pixelated;max-width:100%}}
code{{font-size:11px}} small{{font-size:11px;color:var(--muted-foreground,#777)}} .note{{color:var(--accent,#b60)}}
.btns{{display:flex;flex-wrap:wrap;gap:3px}} button{{font:inherit;font-size:11px;padding:2px 6px;border:1px solid var(--border,#aaa);border-radius:4px;background:none;color:inherit;cursor:pointer}}
button.on[data-v=anchor]{{background:#2a7}} button.on[data-v=keep]{{background:#6a6}} button.on[data-v=adjust]{{background:#c90}}
button.on[data-v=regen]{{background:#c55}} button.on[data-v=retire]{{background:#777}} button.on{{color:#fff}}
input{{font:inherit;font-size:11px;padding:2px 4px;border:1px solid var(--border,#aaa);border-radius:4px;background:none;color:inherit}}
#bar{{position:sticky;top:0;z-index:2;padding:6px 0;background:var(--card,#fff);display:flex;gap:8px;align-items:center}}
#send{{font-size:13px;padding:4px 10px}}
</style>
<h1>Chłopków Bolonia - przegląd assetów ({len(cards)}) · {DATE}</h1>
<div id=bar><button id=send>Wyślij oceny</button><button id=copy>Kopiuj JSON</button><span id=cnt></span></div>
<p><small>Oceń te, które masz w głowie - nie trzeba wszystkich. "wzór stylu" = to ma definiować styl całej gry.</small></p>
{''.join(parts)}
<script>
const S={{}};
document.querySelectorAll('.card').forEach(c=>{{
  const id=c.dataset.id;
  c.querySelectorAll('button').forEach(b=>b.onclick=()=>{{
    const on=b.classList.contains('on'); c.querySelectorAll('button').forEach(x=>x.classList.remove('on'));
    if(on) delete S[id]; else {{b.classList.add('on'); S[id]=Object.assign(S[id]||{{}},{{label:b.dataset.v}});}} upd();}});
  c.querySelector('input').oninput=e=>{{S[id]=Object.assign(S[id]||{{}},{{note:e.target.value}}); upd();}};
}});
function upd(){{document.getElementById('cnt').textContent=Object.keys(S).length+' ocenionych';}}
function out(){{return JSON.stringify(S);}}
document.getElementById('send').onclick=()=>{{
  const msg='Oceny assetów Bolonia (A0): '+out();
  try{{localStorage.setItem('bolonia-asset-labels',out());}}catch(e){{}}
  navigator.clipboard.writeText(out()).catch(()=>{{}});
  if(window.hermes&&window.hermes.send) window.hermes.send(msg);
  document.getElementById('cnt').textContent=Object.keys(S).length+' ocenionych - wysłane i skopiowane';}};
document.getElementById('copy').onclick=()=>navigator.clipboard.writeText(out());
</script>"""
with open(os.path.join(OUT, 'review.html'), 'w', encoding='utf-8') as f:
    f.write(page)
print(len(cards), 'cards ->', os.path.join(OUT, 'review.html'), round(len(page) / 1e6, 1), 'MB')
