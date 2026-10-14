"""Four shelter variants in the selected Dom Muchy yard. Preview only.
Shelter ground position triangulated from three existing photo camera estimates.
Replace provisional B3 shed in previews, preserve accepted house/B1/B2 sources.
"""
import json,sys,hashlib,shutil
from pathlib import Path
from PIL import Image,ImageDraw
import numpy as np
from scipy import ndimage
P=Path(__file__).resolve().parent
YARD=P.parent; PILOT=YARD.parent; ROOT=PILOT.parents[1]
sys.path.insert(0,str(PILOT)); sys.path.insert(0,str(ROOT/'osm'))
import process_versions as pipeline
from geo import P as project
OUT=Path('C:/Users/Lenovo/Hermes/image-gen/2026-10-05-chlopkow-przystanek-warianty')
OLD=Path('C:/Users/Lenovo/Hermes/image-gen/2026-10-05-chlopkow-przystanek-dom-muchy')
BOX=(2070,4450,2390,4730)
SOURCES=[
 ('A','Previous',OLD/'shelter_raw.png','45a397de-262e-4ece-8b8f-36ce2c218a0e','medium'),
 ('B','Photo proportions',Path('C:/Users/Lenovo/AppData/Local/hermes/cache/generated/images/openai_codex_gpt-image-2-medium_20261005_075702_5c44f9fa.png'),'24a6efe7-0890-4ac1-8fd0-885614c45519','low'),
 ('C','More open front',Path('C:/Users/Lenovo/AppData/Local/hermes/cache/generated/images/openai_codex_gpt-image-2-medium_20261005_075706_ab06862e.png'),'73a84230-4193-4863-b3a6-9827be21eeec','low'),
 ('D','Chunkier',Path('C:/Users/Lenovo/AppData/Local/hermes/cache/generated/images/openai_codex_gpt-image-2-medium_20261005_075656_b1fe7179.png'),'a2117840-6268-40f9-8aa0-818dd3271864','low')]


def main():
 OUT.mkdir(parents=True,exist_ok=True)
 protected=[ROOT/'docs/map.json',ROOT/'docs/img/map_ground.png',ROOT/'docs/img/map_objects.png',PILOT/'with_tree/4.png',YARD/'B1.png',YARD/'B2_3d_yaw32/B2.png',YARD/'B3_candidate.png',YARD/'manifest_selected.json',OLD/'shelter.png']
 hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
 m=json.loads((YARD/'manifest_selected.json').read_text())
 pos=json.loads((P/'shelter_position_estimate.json').read_text())
 cx,cy=project(pos['lat'],pos['lon'])
 ground=np.array(Image.open(protected[1]).convert('RGBA').crop(BOX))
 objects=np.array(Image.open(protected[2]).convert('RGBA').crop(BOX))
 old_ground=ground.copy(); old_objects=objects.copy()
 lab,_=ndimage.label(objects[:,:,3]>0)
 ks=[lab[y-BOX[1],x-BOX[0]] for x,y in [(2222,4595),(2163,4590)]]
 mask=np.isin(lab,ks); assert 0 not in ks and int(mask.sum())==4776
 objects[mask]=0; assert np.array_equal(objects[~mask],old_objects[~mask])
 lab,_=ndimage.label(np.all(ground[:,:,:3]==[58,84,40],axis=2))
 ks=[lab[y-BOX[1],x-BOX[0]] for x,y in [(2225,4623),(2170,4620),(2190,4665)]]
 shadows=np.isin(lab,ks); assert 0 not in ks and int(shadows.sum())==3308
 _,ix=ndimage.distance_transform_edt(shadows,return_indices=True)
 ground[shadows]=ground[ix[0][shadows],ix[1][shadows]]
 assert np.array_equal(ground[~shadows],old_ground[~shadows])
 entries=[]
 for v in m['outbuildings']:
  if v['id'].startswith('B3'): continue
  entries.append((v['id'],Image.open(v['sprite']).convert('RGBA'),*v['position']))
 hm=json.loads((PILOT/'with_tree/manifest.json').read_text()); h=next(v for v in hm['variants'] if v['id']=='4')
 entries.append(('Dom Muchy D',Image.open(PILOT/'with_tree/4.png').convert('RGBA'),h['position'][0]+2,h['position'][1]+12))
 def render(es):
  sc=Image.fromarray(ground)
  for name,sp,x,y in es:
   sh=Image.new('RGBA',sp.size,(58,84,40,255)); sh.putalpha(sp.getchannel('A'))
   dx,dy=(3,2) if name in ('A','B','C','D') else (5,3)
   foot=sh.crop((0,sp.height//2,sp.width,sp.height));sc.alpha_composite(foot,(x-BOX[0]+dx,y-BOX[1]+sp.height//2+dy))
  sc.alpha_composite(Image.fromarray(objects))
  for name,sp,x,y in sorted(es,key=lambda s:s[3]+s[1].height):
   sy,sx=y-BOX[1],x-BOX[0]
   assert np.sum((np.array(sp.getchannel('A'))>0)&(objects[sy:sy+sp.height,sx:sx+sp.width,3]>0))==0
   sc.alpha_composite(sp,(sx,sy))
  sc.alpha_composite(pipeline.arek(),(2289-BOX[0],4646-BOX[1]))
  return sc
 base=render(entries)
 pipeline.COLORS=24
 records=[]; panels=[]; sprites=[]
 for id,label,raw,req,quality in SOURCES:
  shutil.copy2(raw,OUT/f'{id}_raw.png')
  sp=Image.open(OLD/'shelter.png').convert('RGBA') if id=='A' else pipeline.pixelate(pipeline.clean(raw),18)
  sp.save(OUT/f'{id}.png')
  a=np.array(sp); assert set(np.unique(a[:,:,3]))=={0,255}; colours=len(np.unique(a[:,:,:3][a[:,:,3]>0],axis=0)); assert colours<=24
  assert not np.any((a[:,:,3]>0)&(a[:,:,0]>180)&(a[:,:,2]>150)&(a[:,:,1]<100))
  x,y=round(cx-sp.width/2),round(cy-sp.height*.85)
  scene=render(entries+[(id,sp,x,y)])
  diff=np.any(np.array(base)!=np.array(scene),axis=2); allowed=np.zeros(diff.shape,bool)
  allowed[y-BOX[1]:y-BOX[1]+sp.height+3,x-BOX[0]:x-BOX[0]+sp.width+4]=True
  assert not np.any(diff&~allowed)
  panel=scene.resize((960,840),Image.Resampling.NEAREST)
  panel.save(OUT/f'{id}_on_map.png')
  d=ImageDraw.Draw(panel); ax=(x-BOX[0])*3; ay=(y-BOX[1])*3
  d.rectangle((ax-3,ay-3,ax+sp.width*3+3,ay+sp.height*3+3),outline=(0,255,255),width=2)
  d.text((ax-10,ay-18),'BUS SHELTER',fill=(0,255,255))
  panels.append((id,label,panel));sprites.append((id,label,sp))
  rec={'id':id,'label':label,'raw':str(OUT/f'{id}_raw.png'),'sprite':str(OUT/f'{id}.png'),'native_size':list(sp.size),'position':[x,y],'ground_centre':[cx,cy],'colour_count':colours,'alpha_values':[0,255],'provider':'openai-codex','model':'gpt-image-2-medium','request_id':req,'reported_quality':quality}
  records.append(rec)
  (OUT/'manifest.json').write_text(json.dumps({'gameChangesApplied':False,'position':pos,'map_ground_centre':[cx,cy],'variants':records},indent=2),encoding='utf-8')
 assert len(records)==4 and len({v['id'] for v in records})==4
 sheet=Image.new('RGB',(1930,1770),(24,24,24));d=ImageDraw.Draw(sheet)
 for i,(id,label,panel) in enumerate(panels):
  x=(i%2)*970;y=(i//2)*885;d.text((x+8,y+9),f'{id} - {label}; position approximate (+/- 3m)',fill=(255,230,80));sheet.paste(panel.convert('RGB'),(x,y+34))
 sheet.save(OUT/'versions_on_map.png')
 close=Image.new('RGB',(960,330),(24,24,24));d=ImageDraw.Draw(close)
 for i,(id,label,sp) in enumerate(sprites):
  x=i*240+15;d.text((x,10),id+' - '+label,fill=(255,230,80))
  big=sp.resize((sp.width*10,sp.height*10),Image.Resampling.NEAREST)
  bg=Image.new('RGBA',big.size,(74,89,56,255));bg.alpha_composite(big);close.paste(bg.convert('RGB'),(x,45));d.text((x,290),f'{sp.width}x{sp.height}px',fill='white')
 close.save(OUT/'sprite_versions.png')
 assert hashes=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
 final={'gameChangesApplied':False,'variant_count':4,'new_GPT_generations':3,'variants':records,'position_estimate':pos,'map_ground_centre':[cx,cy],
        'old_provisional_B3_omitted_from_preview':True,'accepted_house_B1_B2_unchanged':True,'all_shared_game_files_unchanged':True,'unrelated_object_occlusion_pixels':0,
        'references':[str(P/'shelter_photo_crop.png'),str(P/'shelter_other_photo_crop.png')],'map_sheet':str(OUT/'versions_on_map.png')}
 (OUT/'manifest.json').write_text(json.dumps(final,indent=2),encoding='utf-8'); print(json.dumps(final,indent=2))

if __name__=='__main__':main()
