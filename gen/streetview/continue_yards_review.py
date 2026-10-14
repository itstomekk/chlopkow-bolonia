"""Continue east1 yard previews using the existing real-reference GPT library.
Never execute the shared renderer's final export; isolate all render writes in a review folder.
Reuse owner's house-20 ruin and house-19 cuboid revisions and accepted dressing labels.
"""
from pathlib import Path
import sys,os,json,inspect,shutil,hashlib
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'gen/yards/strip_east1'
OUT=ROOT/'gen/yards/reviews/2026-10-05-next'
DELIVERY=Path('C:/Users/Lenovo/Hermes/image-gen/2026-10-05-chlopkow-next-yards')
TARGETS=['23','22','20','19']

def main():
 os.environ['STRIP']='east1';sys.path.insert(0,str(ROOT/'gen/streetview'))
 import yard_strip as ys
 guard=[ROOT/'docs/map.json',ROOT/'docs/img/map_objects.png',ROOT/'docs/img/map_ground.png',ROOT/'gen/yards/final/placements.json',ROOT/'plans/yard-review-east1-v1-decisions.json']
 guard.extend((ROOT/'gen/yards/final').glob('*.png'))
 original={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in guard}
 OUT.mkdir(parents=True,exist_ok=True);DELIVERY.mkdir(parents=True,exist_ok=True)
 plan=json.loads((SOURCE/'plan.json').read_text()); shutil.copy2(SOURCE/'plan.json',OUT/'plan.json')
 for b in plan:
  if b['yard'] and not b['house']:
   d=OUT/str(b['id']);d.mkdir(exist_ok=True);shutil.copy2(SOURCE/str(b['id'])/'raw.png',d/'raw.png')
 ys.OUT=OUT;ys.HOUSES_DIR=OUT
 # Match old procedural boxes globally one-to-one. Small containing boxes can otherwise
 # be selected twice when two roofs overlap, leaving the real tall barn underneath.
 from scipy.optimize import linear_sum_assignment
 old_objects=json.loads((ROOT/'docs/map.json').read_text())['objects']
 targets=[b for b in plan if b['house'] or b['yard']]
 candidates=[o for o in old_objects if o.get('kind')!='tree' and ys.BOX[0]-40<o['x']+o['w']/2<ys.BOX[2]+40 and ys.BOX[1]<o['base']<ys.BOX[3]]
 centres=np.array([[b['c'][0]-ys.SHIFT[0],b['c'][1]-ys.SHIFT[1]] for b in targets])
 old_centres=np.array([[o['x']+o['w']/2,o['base']-o['h']*.225] for o in candidates])
 cost=np.linalg.norm(centres[:,None,:]-old_centres[None,:,:],axis=2)
 rows,cols=linear_sum_assignment(cost);assert len(rows)==len(targets)
 matched={targets[i]['id']:candidates[j] for i,j in zip(rows,cols)}
 assert max(cost[i,j] for i,j in zip(rows,cols))<40
 def old_match(cx,cy,objects,taken):
  i=int(np.argmin(np.linalg.norm(centres-[cx,cy],axis=1))); ob=matched[targets[i]['id']]
  # The map JSON is loaded again in the renderer; return that exact dict for identity-based clearing.
  hits=[q for q in objects if q['x']==ob['x'] and q['y']==ob['y'] and q['w']==ob['w'] and q['h']==ob['h']]
  assert len(hits)==1 and id(hits[0]) not in taken
  return hits
 ys.OLD_OBJECTS=old_match
 ys.HOUSES[909989528]=('20',SOURCE/'revisions/house20_ruins_raw.png',1.0)
 ys.HOUSES[909988586]=('19',SOURCE/'revisions/house19_cuboid_raw.png',1.0)
 # All renderer-generated sprites/placements go to this isolated review, never gen/yards/final.
 text=inspect.getsource(ys.render)
 old='fin = ROOT / "gen/yards/final"; fin.mkdir(parents=True, exist_ok=True)'
 assert text.count(old)==1
 text=text.replace(old,'fin = OUT / "sprites"; fin.mkdir(parents=True, exist_ok=True)')
 # Re-grid source art at a smaller size only when necessary, never translate the ground anchor.
 house_branch='''        if b["house"]:
            r = put(b, *home(b), None)'''
 corrected='''        if b["house"]:
            raw = HOUSES[b["id"]][1]
            source = clean(raw)
            full_width = b["sprite"].width
            for factor in (1.0, .95, .9, .85, .8, .75, .7, .6):
                width = round(full_width * factor)
                b["sprite"] = pixelate(source, width)
                r = put(b, *home(b), occ)
                if r:
                    b["review_scale"] = factor
                    break
            if r is None:
                raise AssertionError("No safe house placement: " + str(b["id"]))'''
 assert text.count(house_branch)==1
 text=text.replace(house_branch,corrected)
 text=text.replace('for scale in (1.0, 0.9, 0.8, 0.7, 0.6):','for scale in (1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3):')
 text=text.replace('key=lambda b: (not b["house"], abs(b["v"]))','key=lambda b: (not b["house"], b["yard"] == "E1", abs(b["v"]))')
 text=text.replace('gg.alpha_composite(a, (215, 245 - a.height))','gg.alpha_composite(a, (285, 410 - a.height))')
 ns=dict(ys.__dict__);exec(text,ns);ns['render']()
 from process import clean,pixelate
 import process3 as p3
 placements=json.loads((OUT/'sprites/placements.json').read_text())
 assert len({p['id'] for p in placements})==len(placements)
 byid={b['id']:b for b in plan}
 for p in placements:
  s=Image.open(OUT/'sprites'/f"{p['id']}.png").convert('RGBA');a=np.array(s)
  assert set(np.unique(a[:,:,3])).issubset({0,255})
  assert not np.any((a[:,:,3]>0)&(a[:,:,0]>180)&(a[:,:,2]>150)&(a[:,:,1]<100))
  foot=p3.collision(s); yy,xx=np.nonzero(foot)
  b=byid[p['id']];centre=(b['c'][0]-ys.SHIFT[0],b['c'][1]-ys.SHIFT[1])
  error=np.hypot(xx.mean()+p['x']-centre[0],yy.mean()+p['y']-centre[1]);assert error<0.8,error
 # Ground-occupancy test for every exported building pair: no silently accepted overlaps.
 occupants={p['id']:{(int(x+p['x']),int(y+p['y'])) for y,x in zip(*np.nonzero(p3.collision(Image.open(OUT/'sprites'/f"{p['id']}.png").convert('RGBA'))))} for p in placements}
 pairs=[]
 for i,p in enumerate(placements):
  for q in placements[i+1:]:
   count=len(occupants[p['id']]&occupants[q['id']])
   if count:pairs.append([p['id'],q['id'],count])
 assert not pairs,pairs
 box=ys.BOX;pw=(box[2]-box[0])*3;ph=(box[3]-box[1])*3
 compare=Image.open(OUT/'compare_east1.png').convert('RGBA')
 base=compare.crop((0,2*(ph+26)+26,pw,2*(ph+26)+26+ph)).resize((pw//3,ph//3),Image.Resampling.NEAREST)
 assert base.size==(box[2]-box[0],box[3]-box[1])
 # Build user-labelled small props from existing raws without overwriting the source atlas cuts.
 import process_east1_props as props
 assets={}
 for rawname,specs in [('props_atlas_farm_raw.png',props.FARM),('props_atlas_home_raw.png',props.HOME)]:
  for name,idx,width in specs:assets[name]=props.cell(SOURCE/rawname,idx,width)
 for name,raw,width in [('tin_shelter','props_tinshelter_raw.png',32),('workshop','props_workshop_raw.png',34)]:assets[name]=props.standalone(SOURCE/raw,width)
 assets['hedge']=Image.open(ROOT/'docs/img/j12_prop_hedge.png').convert('RGBA')
 pd=json.loads((SOURCE/'props/placements_preview.json').read_text())
 wanted=[p for p in pd['props'] if any(p['candidate'].startswith(f'east1-{yard}-') for yard in TARGETS)]
 decisions=json.loads((ROOT/'plans/yard-review-east1-v1-decisions.json').read_text())['decisions']
 for p in wanted:
  decision=decisions[p['candidate']];assert decision['decision']=='add' and decision['identification']==p['identification']
 # Keep props off enlarged sprite pixels. Approximate candidate positions may snap locally to clear ground.
 building_alpha=np.zeros((base.height,base.width),bool)
 for p in placements:
  s=Image.open(OUT/'sprites'/f"{p['id']}.png").convert('RGBA');a=np.array(s.getchannel('A'))>0
  x,y=p['x']-box[0],p['y']-box[1]
  building_alpha[y:y+s.height,x:x+s.width]|=a
 blocked=building_alpha.copy();prop_placements=[]
 for p in sorted(wanted,key=lambda v:(v['y'],v['x'])):
  s=assets[p['kind']];a=np.array(s.getchannel('A'))>0
  x=round(p['x']-s.width/2)-box[0];y=round(p['y']-s.height)-box[1]
  offsets=sorted([(dx,dy) for dy in range(-18,19,2) for dx in range(-18,19,2)],key=lambda v:v[0]**2+v[1]**2)
  found=None
  for dx,dy in offsets:
   xx,yy=x+dx,y+dy
   if xx<0 or yy<0 or xx+s.width>base.width or yy+s.height>base.height:continue
   if np.any(blocked[yy:yy+s.height,xx:xx+s.width]&a):continue
   found=(xx,yy,dx,dy);break
  if found is None:
   prop_placements.append(dict(p,status='not placed: no clear ground within local preview tolerance'));continue
  xx,yy,dx,dy=found;blocked[yy:yy+s.height,xx:xx+s.width]|=a;base.alpha_composite(s,(xx,yy))
  s.save(OUT/(p['kind']+'.png'))
  prop_placements.append(dict(p,status='placed',sprite_position=[xx+box[0],yy+box[1]],offset=[dx,dy]))
 base.resize((pw,ph),Image.Resampling.NEAREST).save(DELIVERY/'four_yards_on_map.png')
 grid=Image.new('RGB',(1540,1360),(24,24,24));dr=ImageDraw.Draw(grid)
 counts={}
 for i,yard in enumerate(TARGETS):
  group=[p for p in placements if p['yard']==yard];counts[yard]=len(group)
  bld=[byid[p['id']] for p in group];xmin=min(b['c'][0] for b in bld)-65;xmax=max(b['c'][0] for b in bld)+65;ymin=min(b['c'][1] for b in bld)-80;ymax=max(b['c'][1] for b in bld)+50
  width=250;height=205;cx=(xmin+xmax)/2;cy=(ymin+ymax)/2
  region=(round(cx-width/2),round(cy-height/2),round(cx+width/2),round(cy+height/2))
  crop=base.crop((region[0]-box[0],region[1]-box[1],region[2]-box[0],region[3]-box[1])).resize((width*3,height*3),Image.Resampling.NEAREST)
  label=yard+(' - ruins, not an intact house' if yard=='20' else '')
  mark=ImageDraw.Draw(crop)
  for item in group:
   sprite=Image.open(OUT/'sprites'/f"{item['id']}.png")
   xx=(item['x']-region[0])*3;yy=(item['y']-region[1])*3
   mark.rectangle((xx-2,yy-2,xx+sprite.width*3+2,yy+sprite.height*3+2),outline=(255,225,100),width=2)
   tag=yard if item['house'] else yard+' G'
   mark.rectangle((xx,yy-17,xx+45,yy-3),fill=(24,24,24));mark.text((xx+3,yy-16),tag,fill=(255,225,100))
  px=(i%2)*770;py=(i//2)*680;dr.text((px+10,py+12),f'YARD {label} / {len(group)} OSM buildings',fill=(255,230,80));grid.paste(crop.convert('RGB'),(px+10,py+40))
  crop.save(DELIVERY/f'yard_{yard}_on_map.png')
 grid.save(DELIVERY/'four_yards_detail.png')
 assert set(counts)==set(TARGETS) and all(counts[y]>1 for y in TARGETS)
 assert original=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in guard}
 result={'preview_only':True,'gameChangesApplied':False,'yards':TARGETS,'building_count_per_yard':counts,'target_building_total':sum(counts.values()),
 'source':'Existing GPT Image source library, repixelated at current game scale; no new generation claimed.',
 'house_revisions':{'20':'Owner-corrected wooden ruin','19':'Owner-corrected rectangular cuboid'},'small_props':prop_placements,
 'ground_pair_overlap_pixels':0,'ground_centroid_error_max_px':0.8,'protected_shared_files_unchanged':True,'delivery':str(DELIVERY)}
 (OUT/'manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
