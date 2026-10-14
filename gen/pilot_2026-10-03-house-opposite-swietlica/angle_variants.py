"""Four gentle GPT yaw edits of accepted Warm house; preview only.
Angles below are requested yaw changes, NOT measured/exact output angles.
No shared map files are changed. Preserve accepted Warm source and neighbours.
"""
import hashlib
import json
import shutil
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
from process_versions import clean, pixelate, arek

ROOT=Path(__file__).resolve().parents[2]
D=Path(__file__).resolve().parent/'angles'
DELIVERY=Path('C:/Users/Lenovo/Hermes/image-gen/2026-10-04-chlopkow-house-angles')
SOURCES=[
 ('A',10,'CW','openai_codex_gpt-image-2-medium_20261004_194026_6499090d.png'),
 ('B',15,'CW','openai_codex_gpt-image-2-medium_20261004_194025_65622518.png'),
 ('C',20,'CW','openai_codex_gpt-image-2-medium_20261004_194028_2dfdfa86.png'),
 ('D',15,'CCW','openai_codex_gpt-image-2-medium_20261004_194029_7814aee4.png')]
CACHE=Path('C:/Users/Lenovo/AppData/Local/hermes/cache/generated/images')
BOX=(2104,4486,2344,4696)
CX,BASE=2224,4621


def main():
 D.mkdir(exist_ok=True); DELIVERY.mkdir(parents=True,exist_ok=True)
 protected=[ROOT/'docs/map.json',ROOT/'docs/img/map_ground.png',ROOT/'docs/img/map_objects.png']
 hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
 meta=json.loads(protected[0].read_text(encoding='utf-8'))
 assert any(o['x']==2208 and o['y']==4580 and o['w']==31 and o['h']==44 for o in meta['objects'])
 ground=np.array(Image.open(protected[1]).convert('RGBA').crop(BOX))
 obj=np.array(Image.open(protected[2]).convert('RGBA').crop(BOX))
 lab,_=ndimage.label(obj[:,:,3]>0)
 k=lab[4595-BOX[1],2222-BOX[0]]
 mask=lab==k; assert k>0 and int(mask.sum())==641
 old=obj.copy(); obj[mask]=0
 assert np.array_equal(old[~mask],obj[~mask])
 lab,_=ndimage.label(np.all(ground[:,:,:3]==[58,84,40],axis=2))
 k=lab[4623-BOX[1],2225-BOX[0]]; mask=lab==k
 assert k>0 and int(mask.sum())==396
 _,ix=ndimage.distance_transform_edt(mask,return_indices=True)
 ground[mask]=ground[ix[0][mask],ix[1][mask]]
 panels=[]; records=[]; sprites=[]
 for letter,angle,direction,source in SOURCES:
  raw=D/f'{letter}_raw.png'; shutil.copy2(CACHE/source,raw)
  keyed=clean(raw)
  scale=min(58/keyed.width,55/keyed.height)
  width=max(1,round(keyed.width*scale))
  sp=pixelate(keyed,width)
  assert sp.width<=58 and sp.height<=56
  pixels=np.array(sp); assert set(np.unique(pixels[:,:,3])).issubset({0,255})
  sp.save(D/f'{letter}.png')
  sprites.append((letter,sp))
  x,y=CX-sp.width//2,BASE-sp.height
  sc=Image.fromarray(ground)
  sh=Image.new('RGBA',sp.size,(58,84,40,255)); sh.putalpha(sp.getchannel('A'))
  foot=sh.crop((0,sp.height//2,sp.width,sp.height))
  sc.alpha_composite(foot,(x-BOX[0]+5,y-BOX[1]+sp.height//2+3))
  sc.alpha_composite(Image.fromarray(obj)); sc.alpha_composite(sp,(x-BOX[0],y-BOX[1]))
  player=arek(); sc.alpha_composite(player,(CX+65-BOX[0],BASE+65-40-BOX[1]))
  sc=sc.resize((sc.width*3,sc.height*3),Image.Resampling.NEAREST)
  sc.save(DELIVERY/f'{letter}_map.png')
  panels.append((letter,angle,direction,sc))
  records.append({'variant':letter,'requested_delta_degrees':angle,'direction':direction,
                  'exact_angle_verified':False,'source':str(CACHE/source),'sprite_size':list(sp.size),
                  'placement':{'center_x':CX,'base':BASE,'x':x,'y':y}})
 pw,ph=panels[0][3].size
 out=Image.new('RGB',(pw*2+12,(ph+30)*2+12),(24,24,24)); draw=ImageDraw.Draw(out)
 for i,(letter,angle,direction,sc) in enumerate(panels):
  x=(i%2)*(pw+12); y=(i//2)*(ph+42)
  draw.text((x+8,y+8),f'{letter} - requested {angle} deg {direction} | same position and size envelope',fill=(255,230,80))
  out.paste(sc.convert('RGB'),(x,y+30))
 out.save(DELIVERY/'four_angles_on_map.png')
 sheet=Image.new('RGB',(4*380,510),(30,30,32)); draw=ImageDraw.Draw(sheet)
 for i,(letter,sp) in enumerate(sprites):
  big=sp.resize((sp.width*6,sp.height*6),Image.Resampling.NEAREST)
  bg=Image.new('RGBA',big.size,(74,89,56,255)); bg.alpha_composite(big)
  draw.text((i*380+15,18),letter,fill=(255,230,80))
  sheet.paste(bg.convert('RGB'),(i*380+(380-big.width)//2,70))
 sheet.save(DELIVERY/'four_angles_closeup.png')
 assert hashes=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
 result={'preview_only':True,'count':len(records),'variants':records,'docs_unchanged':True,
         'neighbours_unchanged':True,'original_warm_preserved':True,'delivery':str(DELIVERY)}
 (D/'manifest.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
 print(json.dumps(result,indent=2))

if __name__=='__main__': main()
