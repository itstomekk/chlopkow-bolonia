"""Reference-based house+tree candidates, separately generated; map previews only.
Do not rotate/shear any drawing. Scale against HOUSE width, not whole tree+house.
"""
import hashlib,json,shutil
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from scipy import ndimage
from process_versions import clean, pixelate, arek

ROOT=Path(__file__).resolve().parents[2]
D=Path(__file__).resolve().parent/'with_tree'; D.mkdir(exist_ok=True)
OUT=Path('C:/Users/Lenovo/Hermes/image-gen/2026-10-04-chlopkow-house-tree'); OUT.mkdir(parents=True,exist_ok=True)
CACHE=Path('C:/Users/Lenovo/AppData/Local/hermes/cache/generated/images')
SOURCES=[('1','Natural','openai_codex_gpt-image-2-medium_20261004_195313_52801e73.png'),
('2','Fuller tree','openai_codex_gpt-image-2-medium_20261004_195320_c10e4032.png'),
('3','Cheerful warm','openai_codex_gpt-image-2-medium_20261004_195320_0618a00d.png'),
('4','Chunky','openai_codex_gpt-image-2-medium_20261004_195321_b6abc896.png')]
BOX=(2070,4450,2390,4730); CX,BASE=2224,4621

def main():
 protected=[ROOT/'docs/map.json',ROOT/'docs/img/map_ground.png',ROOT/'docs/img/map_objects.png']
 hashes=[hashlib.sha256(p.read_bytes()).hexdigest() for p in protected]
 meta=json.loads(protected[0].read_text(encoding='utf-8'))
 assert any(o['x']==2208 and o['y']==4580 and o['w']==31 and o['h']==44 for o in meta['objects'])
 g=np.array(Image.open(protected[1]).convert('RGBA').crop(BOX))
 o=np.array(Image.open(protected[2]).convert('RGBA').crop(BOX))
 lab,_=ndimage.label(o[:,:,3]>0); k=lab[4595-BOX[1],2222-BOX[0]]; mask=lab==k
 assert k>0 and int(mask.sum())==641
 old=o.copy(); o[mask]=0; assert np.array_equal(old[~mask],o[~mask])
 lab,_=ndimage.label(np.all(g[:,:,:3]==[58,84,40],axis=2)); k=lab[4623-BOX[1],2225-BOX[0]]; mask=lab==k
 assert k>0 and int(mask.sum())==396
 _,ix=ndimage.distance_transform_edt(mask,return_indices=True); g[mask]=g[ix[0][mask],ix[1][mask]]
 panels=[]; close=[]; rec=[]
 for n,title,filename in SOURCES:
  raw=D/f'{n}_raw.png'; shutil.copy2(CACHE/filename,raw)
  im=clean(raw); a=np.array(im).astype(float)
  # Locate the largest red/orange architectural component, excluding magenta/green foliage.
  warm=(a[:,:,3]>0)&(a[:,:,0]>1.13*a[:,:,1])&(a[:,:,1]>1.10*a[:,:,2])&(a[:,:,0]>70)
  lab,num=ndimage.label(warm); sizes=np.bincount(lab.ravel()); sizes[0]=0
  assert num>0
  yy,xx=np.where(lab==sizes.argmax()); left,right=int(xx.min()),int(xx.max())+1
  assert right-left>im.width*.25
  # Wall-colour pixels below the roof determine house grounding (tree trunk excluded by x range).
  wall=(a[:,:,3]>0)&(a[:,:,0]>1.06*a[:,:,1])&(a[:,:,1]>1.1*a[:,:,2])
  wall[:,:left]=False; wall[:,right:]=False
  sy,sx=np.where(wall); bottom=int(sy.max())+1
  scale=58/(right-left)
  width=max(1,round(im.width*scale)); sp=pixelate(im,width); sp.save(D/f'{n}.png')
  # Our cropped raw is tightly alpha-bound so pixelate will not introduce margin shifts.
  x=CX-round((left+right)/2*scale); y=BASE-round(bottom*scale)
  sc=Image.fromarray(g); sh=Image.new('RGBA',sp.size,(58,84,40,255)); sh.putalpha(sp.getchannel('A'))
  foot=sh.crop((0,sp.height//2,sp.width,sp.height))
  sc.alpha_composite(foot,(x-BOX[0]+5,y-BOX[1]+sp.height//2+3))
  sc.alpha_composite(Image.fromarray(o)); sc.alpha_composite(sp,(x-BOX[0],y-BOX[1]))
  player=arek(); sc.alpha_composite(player,(CX+65-BOX[0],BASE+65-40-BOX[1]))
  view=sc.resize((sc.width*3,sc.height*3),Image.Resampling.NEAREST)
  view.save(OUT/f'{n}_map.png'); panels.append((n,title,view))
  bg=Image.new('RGBA',sp.size,(74,89,56,255)); bg.alpha_composite(sp)
  close.append((n,title,bg.resize((bg.width*5,bg.height*5),Image.Resampling.NEAREST)))
  rec.append({'id':n,'title':title,'raw':str(raw),'separate_generation':True,'manual_rotation':False,
              'house_width_target':58,'compound_sprite_size':list(sp.size),'position':[x,y]})
 pw,ph=panels[0][2].size
 sheet=Image.new('RGB',(pw*2+12,(ph+32)*2+12),(24,24,24)); dr=ImageDraw.Draw(sheet)
 for i,(n,title,im) in enumerate(panels):
  x=(i%2)*(pw+12); y=(i//2)*(ph+44)
  dr.text((x+8,y+8),f'{n} - {title}',fill=(255,230,80)); sheet.paste(im.convert('RGB'),(x,y+32))
 sheet.save(OUT/'four_tree_versions_map.png')
 cw=max(im.width for _,_,im in close)+24; ch=max(im.height for _,_,im in close)+36
 sheet=Image.new('RGB',(cw*2+12,ch*2+12),(24,24,24)); dr=ImageDraw.Draw(sheet)
 for i,(n,title,im) in enumerate(close):
  x=(i%2)*(cw+12); y=(i//2)*(ch+12)
  dr.text((x+8,y+6),f'{n} - {title}',fill=(255,230,80)); sheet.paste(im.convert('RGB'),(x+12,y+32))
 sheet.save(OUT/'four_tree_versions_closeup.png')
 assert hashes==[hashlib.sha256(p.read_bytes()).hexdigest() for p in protected]
 data={'count':len(rec),'reference_files':['sv_sheet.jpg','sat.png','angles/D_raw.png','cheerful_raw.png'],
       'preview_only':True,'docs_unchanged':True,'variants':rec}
 (D/'manifest.json').write_text(json.dumps(data,indent=2),encoding='utf-8'); print(json.dumps(data,indent=2))

if __name__=='__main__':main()
