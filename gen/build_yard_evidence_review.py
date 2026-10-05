"""Build a self-contained, local-only J12 satellite uncertainty review. Never edits the game.

python gen/build_yard_evidence_review.py [--out PATH]
Source crops are real cached satellite images, not generated reconstructions.
"""
import argparse
import base64
import io
import json
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'gen/yards/j12'
REVIEW = 'yard-evidence-j12-v1'
# Pixel boxes are human-review regions, not verified physical object outlines.
REGIONS = [
    {'id': 'j12-15-vegetation', 'yard': '15', 'box': [558, 337, 699, 493],
     'title': 'Zieleń przy domu', 'confidence': 'Wysoka dla zieleni',
     'observation': 'Widoczna grupa roślin. Nie rozdzielam na pewno krzewów od koron małych drzew.',
     'proposal': 'Odtworzyć zieleń w tym miejscu, po sprawdzeniu obecnych drzew w grze.',
     'alternatives': ['krzewy', 'małe drzewa'], 'suggested': 'krzewy / małe drzewa'},
    {'id': 'j12-15-materials', 'yard': '15', 'box': [224, 548, 465, 704],
     'title': 'Podłużne pasy przy zabudowaniach', 'confidence': 'Niska',
     'observation': 'Jasne i ciemne pasy. Po powiększeniu nie da się potwierdzić stosu materiałów: mogą należeć do dachu, podłoża lub cienia.',
     'proposal': 'Nie dodawać jako materiały bez Twojego rozpoznania.',
     'alternatives': ['deski / składowane materiały?', 'dach lub cień?'], 'suggested': ''},
    {'id': 'j12-15-object', 'yard': '15', 'box': [440, 724, 521, 805],
     'title': 'Jasna plamka przy dolnym budynku', 'confidence': 'Niska',
     'observation': 'Nierozpoznana jasna plamka. Nie można nawet pewnie stwierdzić, czy to osobny przedmiot.',
     'proposal': 'Potrzebne rozpoznanie lokalne lub lepsze zdjęcie. Traktor i betoniarka nie są potwierdzone.',
     'alternatives': ['sprzęt lub zbiornik?', 'jasny fragment dachu / podłoża?'], 'suggested': ''},
    {'id': 'j12-18-vegetation', 'yard': '18', 'box': [758, 36, 1008, 324],
     'title': 'Pas zieleni przy drodze', 'confidence': 'Wysoka dla zieleni',
     'observation': 'Widoczne korony roślin przy drodze. Czy to żywopłot, krzewy czy drzewa, pozostaje do rozróżnienia.',
     'proposal': 'Odtworzyć pas zieleni, bez duplikowania istniejących drzew.',
     'alternatives': ['krzewy / żywopłot', 'drzewa'], 'suggested': 'krzewy / drzewa'},
    {'id': 'j12-18-ground', 'yard': '18', 'box': [356, 191, 639, 344],
     'title': 'Jasne i ciemne miejsca na ziemi', 'confidence': 'Niska',
     'observation': 'Plamy na odsłoniętym podłożu. Nie potwierdzono oddzielnej hałdy ani rodzaju materiału.',
     'proposal': 'Kupa piasku, żwiru lub ziemi tylko po Twoim potwierdzeniu. Alternatywnie zostawić gołe podłoże.',
     'alternatives': ['piasek / żwir / ziemia?', 'gołe podłoże / cień?'], 'suggested': ''},
    {'id': 'j12-18-object', 'yard': '18', 'box': [598, 425, 797, 693],
     'title': 'Nierozpoznane kształty między budynkami', 'confidence': 'Niska',
     'observation': 'Kilka ciemnych kształtów. Powiększenie nie potwierdza maszyn; możliwe cienie, podłoże albo fragmenty budynków.',
     'proposal': 'Nie przypisywać automatycznie traktora, betoniarki ani pojazdu.',
     'alternatives': ['sprzęt?', 'cień / dach / podłoże?'], 'suggested': ''},
]


def data_image(image):
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(buffer.getvalue()).decode('ascii')


def build(out, decisions=None):
    plan = json.loads((SOURCE / 'plan.json').read_text(encoding='utf-8'))
    yards = {}
    for yard in ('15', '18'):
        im = Image.open(SOURCE / f'yard_{yard}/sat_clean.png').convert('RGB')
        assert im.size == (1024, 1024), 'Recalibrate review boxes if source size changed'
        pts = [p for b in plan if b['yard'] == yard for p in b['pts']]
        xs, ys = zip(*pts)
        cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        # Same source framing as yard_strip.gen(): A=2 world px per metre.
        half = max(max(xs) - min(xs), max(ys) - min(ys)) / 2 + 16
        marked = im.copy()
        draw = ImageDraw.Draw(marked)
        for index, item in enumerate((r for r in REGIONS if r['yard'] == yard), 1):
            box = item['box']
            item['source'] = f'gen/yards/j12/yard_{yard}/sat_clean.png'
            item['crop'] = data_image(im.crop(box))
            item['index'] = index
            x, y = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
            item['mapPointApprox'] = [round(cx - half + x / 1024 * half * 2),
                                      round(cy - half + y / 1024 * half * 2)]
            draw.rectangle(box, outline='#ffdf75', width=4)
            draw.rectangle((box[0], box[1], box[0] + 24, box[1] + 24), fill='#ffdf75')
            draw.text((box[0] + 7, box[1] + 5), str(index), fill='#182321')
        yards[yard] = {'full': data_image(im), 'marked': data_image(marked)}
    if decisions is not None:
        if decisions.get('review') != REVIEW or set(decisions.get('decisions', {})) != {c['id'] for c in REGIONS}:
            raise ValueError('Decision JSON does not match the six J12 candidate IDs')
        for d in decisions['decisions'].values():
            if d.get('decision') not in ('pending', 'add', 'skip', 'better-photo') or not all(isinstance(d.get(k), str) for k in ('identification', 'note')):
                raise ValueError('Invalid decision schema')
    data = {'review': REVIEW, 'candidates': REGIONS, 'yards': yards, 'initialDecisions': decisions,
            'policy': {'denseFarmyards': 'Prefer chickens and dogs around dense farmyard clusters; animals are gameplay dressing, not identified from satellite imagery.'}}
    template = TEMPLATE.replace('__DATA__', json.dumps(data, ensure_ascii=False).replace('</', '<\\/'))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(template, encoding='utf-8')
    print(f'6 review candidates, 2 real satellite sources -> {out}')


TEMPLATE = r'''<!doctype html>
<html lang="pl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Chłopków Bolonia · J12 · niepewności z satelity</title>
<style>
:root{color-scheme:dark;--bg:#151c1b;--card:#1f2926;--text:#eeeade;--muted:#b6b9a8;--line:#425048;--accent:#eed392}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:16px/1.5 system-ui,sans-serif}main{max-width:1280px;margin:auto;padding:28px}h1{font-size:clamp(28px,4vw,44px);line-height:1.1;margin:12px 0}h2{margin:0 0 12px}p{margin:8px 0}small,.muted{color:var(--muted)}.eyebrow{letter-spacing:.14em;text-transform:uppercase;color:var(--accent);font-size:12px}.intro{max-width:850px}.policy{border-left:3px solid var(--accent);padding:10px 16px;background:var(--card);margin:18px 0}.tools{position:sticky;top:0;z-index:2;display:flex;align-items:center;gap:12px;flex-wrap:wrap;padding:14px 0;background:var(--bg);border-bottom:1px solid var(--line)}button,select,input,textarea,.import-label{font:inherit;color:var(--text);background:#26352e;border:1px solid var(--line);border-radius:6px;padding:8px 10px}button,.import-label{cursor:pointer}#export{background:var(--accent);color:#19251d;border-color:var(--accent);font-weight:700}.import-label input{display:none}#notice{font-size:14px;color:var(--accent)}.yard{margin-top:34px}.overview{display:flex;gap:18px;align-items:flex-start;background:var(--card);padding:16px;border-radius:10px}.overview img{width:300px;max-width:100%;height:auto;cursor:zoom-in}.overview div{max-width:600px}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin-top:18px}.candidate{background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}.candidate[data-state="add"]{border-color:#96b87b}.candidate[data-state="skip"]{border-color:#8c8e89}.candidate[hidden]{display:none}.crop-wrap{background:#111817;height:220px;display:flex;align-items:center;justify-content:center}.crop{width:100%;height:100%;object-fit:contain;cursor:zoom-in;image-rendering:auto}.body{padding:18px}.confidence{font-size:12px;color:var(--accent);text-transform:uppercase}.candidate h3{font-size:20px;line-height:1.25;margin:9px 0}.candidate p{font-size:14px}.body label{display:block;font-size:13px;color:var(--muted);margin-top:14px}.body select,.body input,.body textarea{display:block;width:100%;margin-top:5px}.body textarea{min-height:78px;resize:vertical}.coords{font:12px ui-monospace,monospace;color:var(--muted);margin-top:12px}dialog{max-width:95vw;max-height:95vh;background:var(--bg);color:var(--text);border:1px solid var(--line);padding:12px;border-radius:8px}dialog::backdrop{background:#000c}dialog img{display:block;max-width:88vw;max-height:78vh;object-fit:contain}dialog button{float:right;margin-bottom:10px}.foot{margin:30px 0;color:var(--muted);font-size:13px}@media(max-width:900px){.grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:620px){main{padding:16px}.grid{grid-template-columns:1fr}.overview{display:block}.overview img{width:100%}.tools{position:static}}
</style></head><body><main>
<div class="eyebrow">Chłopków Bolonia / rekonstrukcja satelitarna / J12</div>
<h1>Co naprawdę widać na podwórkach?</h1>
<div class="intro"><p>Sześć miejsc do rozstrzygnięcia. To prawdziwe wycinki zdjęć, nie wygenerowane propozycje. Zieleń jest widoczna, ale traktor, betoniarka ani kupa piasku nie są tu potwierdzone.</p>
<p class="muted">Kliknij zdjęcie, żeby powiększyć. Zaznaczenia na podglądzie wskazują obszar pytania, nie pewny obrys przedmiotu. Możesz rozpoznać go z pamięci albo zaproponować dekorację, ale wpisz wtedy, że to swobodny dodatek.</p></div>
<div class="policy"><strong>Zasada dla następnych sektorów:</strong> przy gęstej zabudowie gospodarczej częściej umieszczamy kury i psy, ewentualnie inne pasujące zwierzęta. To ożywienie gry, nie odczyt zwierząt ze zdjęcia satelitarnego. Niepewne rekwizyty najpierw trafiają do takiego arkusza.</div>
<div class="tools"><strong id="progress"></strong><select id="filter" aria-label="Filtr"><option value="all">Wszystkie</option><option value="pending">Nierozstrzygnięte</option><option value="done">Rozstrzygnięte</option></select><button id="copy">Kopiuj JSON</button><button id="export">Pobierz decyzje JSON</button><label class="import-label">Wczytaj decyzje<input type="file" id="import" accept=".json,application/json"></label></div>
<textarea id="copy-json" aria-label="JSON do ręcznego skopiowania" hidden readonly style="width:100%;min-height:200px"></textarea>
<p id="notice" role="status">Decyzje zapisują się w tej przeglądarce. Na końcu pobierz JSON i wrzuć go do rozmowy. Ten HTML sam nie zmienia gry.</p>
<div id="yards"></div><p class="foot">Źródło: lokalnie zapisane zdjęcia satelitarne użyte do J12. Data wykonania zdjęć nie jest znana. Koordynaty przy kartach są przybliżonym środkiem wycinka, nie miejscem zaakceptowanego rekwizytu. Samodzielny HTML działa bez internetu; przenosząc go, zabierz także wyeksportowane decyzje.</p>
</main><dialog id="zoom"><button id="close">Zamknij</button><img alt="Powiększenie zdjęcia satelitarnego"></dialog>
<script>
'use strict';
const DATA=__DATA__;
const seedKey=DATA.initialDecisions?'-seed-'+Array.from(JSON.stringify(DATA.initialDecisions.decisions)).reduce((h,c)=>Math.imul(h^c.charCodeAt(0),16777619)>>>0,2166136261):'';
const KEY='bolonia-'+DATA.review+seedKey;
const ACTIONS=new Set(['pending','add','skip','better-photo']);
const defaults=()=>Object.fromEntries(DATA.candidates.map(c=>[c.id,{decision:'pending',identification:c.suggested,note:''}]));
let decisions=defaults();
function validate(payload){
  if(!payload||payload.review!==DATA.review||!payload.decisions||typeof payload.decisions!=='object')throw Error('To nie jest arkusz J12 w tej wersji.');
  const fresh=defaults();
  for(const c of DATA.candidates){const d=payload.decisions[c.id];if(!d)continue;
    if(!ACTIONS.has(d.decision)||typeof d.identification!=='string'||typeof d.note!=='string')throw Error('Nieprawidłowa decyzja dla '+c.id);
    fresh[c.id]={decision:d.decision,identification:d.identification,note:d.note};}
  return fresh;
}
function payload(){return {review:DATA.review,gameChangesApplied:false,policy:DATA.policy,decisions,
  provenance:DATA.candidates.map(({id,yard,source,box,mapPointApprox})=>({id,yard,source,box,mapPointApprox}))};}
if(DATA.initialDecisions)decisions=validate(DATA.initialDecisions);
// Seed-specific storage avoids stale pending choices while preserving later edits.
try{const saved=localStorage.getItem(KEY);if(saved)decisions=validate(JSON.parse(saved));}catch(e){}
function save(){try{localStorage.setItem(KEY,JSON.stringify(payload()));}catch(e){document.querySelector('#notice').textContent='Przeglądarka nie pozwala zapisać lokalnie. Pobierz JSON przed zamknięciem.';}refresh();}
function refresh(){const n=DATA.candidates.filter(c=>decisions[c.id].decision!=='pending').length;document.querySelector('#progress').textContent=n+' / '+DATA.candidates.length+' rozstrzygniętych';
  const filter=document.querySelector('#filter').value;document.querySelectorAll('.candidate').forEach(card=>{const done=decisions[card.dataset.id].decision!=='pending';card.dataset.state=decisions[card.dataset.id].decision;card.hidden=filter==='pending'?done:filter==='done'?!done:false;});}
function zoom(src){document.querySelector('#zoom img').src=src;document.querySelector('#zoom').showModal();}
function render(){const root=document.querySelector('#yards');root.replaceChildren();
for(const yard of ['15','18']){const section=document.createElement('section');section.className='yard';section.innerHTML='<h2>Podwórko '+yard+'</h2><div class="overview"><img alt="Podwórko '+yard+' z zaznaczonymi obszarami"><div><p>Żółte ramki 1–3 odpowiadają kartom poniżej.</p><p class="muted">Zobacz też pełne zdjęcie bez ramek. Rozpoznanie szerokiej kategorii nie dowodzi konkretnego rodzaju sprzętu lub materiału.</p><button class="clean">Pełne zdjęcie bez zaznaczeń</button></div></div><div class="grid"></div>';
section.querySelector('.overview img').src=DATA.yards[yard].marked;section.querySelector('.overview img').onclick=()=>zoom(DATA.yards[yard].marked);section.querySelector('.clean').onclick=()=>zoom(DATA.yards[yard].full);
for(const c of DATA.candidates.filter(c=>c.yard===yard)){const card=document.createElement('article');card.className='candidate';card.dataset.id=c.id;
card.innerHTML='<div class="crop-wrap"><img class="crop" alt="Wycinek satelity"></div><div class="body"><span class="confidence"></span><h3></h3><p class="observation"></p><p class="muted alternatives"></p><p class="proposal"></p><label>Decyzja<select class="decision"><option value="pending">Jeszcze nie wiem</option><option value="add">Dodaj po moim rozpoznaniu / jako świadomy dodatek</option><option value="skip">Pomiń</option><option value="better-photo">Potrzebne lepsze zdjęcie / pytanie</option></select></label><label>Co to jest / co dodać<input class="identification" placeholder="np. betoniarka; wiem z pamięci"></label><label>Uwagi<textarea class="note" placeholder="Co zmienić, skąd pewność, czy to swobodna dekoracja?"></textarea></label><div class="coords"></div></div>';
card.querySelector('.crop').src=c.crop;card.querySelector('.crop').onclick=()=>zoom(c.crop);card.querySelector('.confidence').textContent=c.confidence;card.querySelector('h3').textContent=c.index+'. '+c.title;card.querySelector('.observation').textContent=c.observation;card.querySelector('.alternatives').textContent='Możliwości: '+c.alternatives.join(' / ');card.querySelector('.proposal').textContent=c.proposal;card.querySelector('.coords').textContent='J12 · x,y ≈ '+c.mapPointApprox.join(',')+' · '+c.id;
for(const [selector,key] of [['.decision','decision'],['.identification','identification'],['.note','note']]){const el=card.querySelector(selector);el.value=decisions[c.id][key];el.addEventListener(key==='decision'?'change':'input',()=>{decisions[c.id][key]=el.value;save();});}
section.querySelector('.grid').append(card);}root.append(section);}refresh();}
document.querySelector('#filter').onchange=refresh;
document.querySelector('#close').onclick=()=>document.querySelector('#zoom').close();
document.querySelector('#copy').onclick=async()=>{
  const text=JSON.stringify(payload(),null,2), area=document.querySelector('#copy-json'), notice=document.querySelector('#notice');
  area.hidden=true;
  try{if(!navigator.clipboard?.writeText)throw Error('Clipboard unavailable');await navigator.clipboard.writeText(text);notice.textContent='Skopiowano JSON.';}
  catch(error){area.value=text;area.hidden=false;area.focus();area.select();let copied=false;try{copied=document.execCommand('copy');}catch(e){}
    if(copied){area.hidden=true;notice.textContent='Skopiowano JSON.';}else notice.textContent='Schowek niedostępny. JSON jest zaznaczony poniżej: Ctrl+C.';}
};
document.querySelector('#export').onclick=()=>{const url=URL.createObjectURL(new Blob([JSON.stringify(payload(),null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='yard-evidence-j12-decisions.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
document.querySelector('#import').onchange=async e=>{try{const file=e.target.files[0];if(!file)return;const parsed=JSON.parse(await file.text());const fresh=validate(parsed);decisions=fresh;save();render();document.querySelector('#notice').textContent='Wczytano decyzje. Gry nie zmieniono.';}catch(error){document.querySelector('#notice').textContent='Nie wczytano: '+error.message;}finally{e.target.value='';}};
render();
</script></body></html>'''

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / 'asset-review/yard-evidence-j12/review.html')
    parser.add_argument('--decisions', type=Path, help='Preload an explicitly supplied decision JSON')
    args = parser.parse_args()
    build(args.out, json.loads(args.decisions.read_text(encoding='utf-8')) if args.decisions else None)
