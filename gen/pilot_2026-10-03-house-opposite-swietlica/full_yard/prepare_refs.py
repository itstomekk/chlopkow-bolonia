"""Whole-property satellite source discovery only; no shared map edits."""
import sys,json,math,io,urllib.request
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'gen/streetview'))
from building_refs import merc
ids=[993157691,993157696,993157706]
es=json.loads((ROOT/'osm/chlopkow.json').read_text(encoding='utf-8'))['elements']
byid={e['id']:e for e in es if e.get('geometry')}
lat,lon=52.264154,22.8748966
z=20; half=600
cx,cy=merc(lat,lon,z); x0,y0=int(cx-half),int(cy-half)
canvas=Image.new('RGB',(half*2,half*2))
tiles=[(tx,ty) for tx in range(x0//256,(x0+half*2-1)//256+1) for ty in range(y0//256,(y0+half*2-1)//256+1)]
def fetch(pair):
 tx,ty=pair
 url=f'https://mt1.google.com/vt/lyrs=s&x={tx}&y={ty}&z={z}'
 req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
 with urllib.request.urlopen(req,timeout=45) as r: data=r.read()
 im=Image.open(io.BytesIO(data)).convert('RGB'); assert im.size==(256,256)
 return tx,ty,im
for tx,ty,tile in ThreadPoolExecutor(max_workers=6).map(fetch,tiles):
 canvas.paste(tile,(tx*256-x0,ty*256-y0))
canvas.save(OUT/'sat_clean.png')
marked=canvas.copy(); draw=ImageDraw.Draw(marked)
records=[]
for i,id in enumerate(ids):
 e=byid[id]; ring=e['geometry']
 points=[(merc(g['lat'],g['lon'],z)[0]-x0,merc(g['lat'],g['lon'],z)[1]-y0) for g in ring]
 colour=(255,40,170) if i==0 else (255,230,60)
 draw.line(points,fill=colour,width=3)
 x=sum(p[0] for p in points[:-1])/len(points[:-1]); y=sum(p[1] for p in points[:-1])/len(points[:-1])
 label='HOUSE' if i==0 else 'B'+str(i)
 draw.rectangle((x-30,y-12,x+35,y+12),fill=(0,0,0)); draw.text((x-25,y-8),label,fill=colour)
 records.append({'label':label,'osm_way':id,'polygon':points,'tags':e['tags']})
marked.save(OUT/'sat_marked.png')
manifest={'source':'Google satellite tiles','zoom':z,'origin_global_px':[x0,y0],'size':list(canvas.size),'centre_lat_lon':[lat,lon],'osm_buildings':records,'third_outbuilding':'not in nearby OSM, requires satellite evidence/user confirmation','gameChangesApplied':False}
(OUT/'references.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps(manifest,indent=2,ensure_ascii=False))
