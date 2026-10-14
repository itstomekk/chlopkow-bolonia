"""B2-only GPT redraw clockwise. Preserve originals and all shared game assets."""
import argparse,hashlib,json,shutil,sys
from pathlib import Path
import numpy as np
from scipy import ndimage
from PIL import Image,ImageDraw
P=Path(__file__).resolve().parent
PILOT=P.parent
ROOT=P.parents[2]
sys.path.insert(0,str(PILOT))
from process_versions import clean,pixelate,arek
RAW=Path('C:/Users/Lenovo/AppData/Local/hermes/cache/generated/images/openai_codex_gpt-image-2-medium_20261004_202351_aa29e4f4.png')
D=P/'B2_clockwise15'
OUT=Path('C:/Users/Lenovo/Hermes/image-gen/2026-10-04-chlopkow-B2-clockwise')
BOX=(2070,4450,2390,4730)


def main():
    global RAW,D,OUT
    parser=argparse.ArgumentParser()
    parser.add_argument('--raw',type=Path,default=RAW)
    parser.add_argument('--variant',default='B2_clockwise15')
    parser.add_argument('--out',type=Path,default=OUT)
    parser.add_argument('--previous',type=Path)
    args=parser.parse_args()
    RAW=args.raw; D=P/args.variant; OUT=args.out
    D.mkdir(exist_ok=True); OUT.mkdir(parents=True,exist_ok=True)
    protected=[ROOT/'docs/map.json',ROOT/'docs/img/map_ground.png',ROOT/'docs/img/map_objects.png',P/'B1.png',P/'B2.png',P/'B3_candidate.png',PILOT/'with_tree/4.png',P/'manifest.json']
    if args.previous:
        assert args.previous.resolve()!=D.resolve(), 'Preserve previous accepted variant'
        protected += [args.previous/'B2.png',args.previous/'B2_raw.png',args.previous/'manifest.json']
    hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    shutil.copy2(RAW,D/'B2_raw.png')
    sp=pixelate(clean(RAW),55)
    sp.save(D/'B2.png')
    a=np.array(sp)
    assert set(np.unique(a[:,:,3])).issubset({0,255})
    assert len(np.unique(a[:,:,:3][a[:,:,3]>0],axis=0))<=28
    assert not np.any((a[:,:,3]>0)&(a[:,:,0]>180)&(a[:,:,2]>150)&(a[:,:,1]<100))
    m=json.loads((P/'manifest.json').read_text(encoding='utf-8'))
    b2=next(v for v in m['outbuildings'] if v['id']=='B2')
    previous_meta=None
    if args.previous:
        previous_meta=json.loads((args.previous/'manifest.json').read_text(encoding='utf-8'))
        b2=dict(b2,position=previous_meta['new_position'])
    cx,cy=b2['centre_map']
    new_x,new_y=round(cx-sp.width/2),round(cy-sp.height*.81)
    ground=np.array(Image.open(protected[1]).convert('RGBA').crop(BOX))
    objects=np.array(Image.open(protected[2]).convert('RGBA').crop(BOX))
    lab,_=ndimage.label(objects[:,:,3]>0)
    ks=[lab[y-BOX[1],x-BOX[0]] for x,y in [(2222,4595),(2163,4590)]]
    assert 0 not in ks and int(np.isin(lab,ks).sum())==4776
    keep=~np.isin(lab,ks); original=objects.copy(); objects[~keep]=0
    assert np.array_equal(objects[keep],original[keep])
    lab,_=ndimage.label(np.all(ground[:,:,:3]==[58,84,40],axis=2))
    ks=[lab[y-BOX[1],x-BOX[0]] for x,y in [(2225,4623),(2170,4620),(2190,4665)]]
    shadow=np.isin(lab,ks)
    assert 0 not in ks and int(shadow.sum())==3308
    _,ix=ndimage.distance_transform_edt(shadow,return_indices=True)
    ground[shadow]=ground[ix[0][shadow],ix[1][shadow]]
    unchanged=[]
    for v in m['outbuildings']:
        if v['id']=='B2': continue
        unchanged.append((v['id'],Image.open(v['sprite']).convert('RGBA'),*v['position']))
    house=Image.open(PILOT/'with_tree/4.png').convert('RGBA')
    hm=json.loads((PILOT/'with_tree/manifest.json').read_text(encoding='utf-8'))
    h=next(v for v in hm['variants'] if v['id']=='4')
    hx,hy=h['position']; unchanged.append(('HOUSE D',house,hx+2,hy+12))
    old=Image.open((args.previous/'B2.png') if args.previous else (P/'B2.png')).convert('RGBA')
    scenes=[]
    unrelated_overlaps=[]
    for replacement,x,y in [(old,*b2['position']),(sp,new_x,new_y)]:
        entries=unchanged+[('B2',replacement,x,y)]
        sc=Image.fromarray(ground)
        for name,s,xx,yy in entries:
            sh=Image.new('RGBA',s.size,(58,84,40,255)); sh.putalpha(s.getchannel('A'))
            foot=sh.crop((0,s.height//2,s.width,s.height))
            sc.alpha_composite(foot,(xx-BOX[0]+5,yy-BOX[1]+s.height//2+3))
        sc.alpha_composite(Image.fromarray(objects))
        overlaps=0
        for name,s,xx,yy in sorted(entries,key=lambda v:v[3]+v[1].height):
            row,col=yy-BOX[1],xx-BOX[0]
            overlaps+=int(np.sum((np.array(s.getchannel('A'))>0)&(objects[row:row+s.height,col:col+s.width,3]>0)))
            sc.alpha_composite(s,(col,row))
        unrelated_overlaps.append(overlaps)
        sc.alpha_composite(arek(),(2289-BOX[0],4646-BOX[1]))
        scenes.append(sc)
    assert unrelated_overlaps==[0,0]
    # Changes must remain exclusively in B2 plus its new/old shadow envelopes.
    allowed=np.zeros((BOX[3]-BOX[1],BOX[2]-BOX[0]),bool)
    for s,x,y in [(old,*b2['position']),(sp,new_x,new_y)]:
        allowed[y-BOX[1]:y-BOX[1]+s.height+3,x-BOX[0]:x-BOX[0]+s.width+5]=True
    diff=np.any(np.array(scenes[0])!=np.array(scenes[1]),axis=2)
    assert int(diff.sum())>0 and not np.any(diff&~allowed)
    zoomed=[s.resize((960,840),Image.Resampling.NEAREST) for s in scenes]
    zoomed[1].save(OUT/'B2_new_on_map.png')
    comparison=Image.new('RGB',(1932,872),(24,24,24)); draw=ImageDraw.Draw(comparison)
    titles=['B2 PREVIOUS','B2 NEW GPT REDRAW - another 15 deg CW' if args.previous else 'B2 NEW GPT REDRAW - clockwise / near east-west']
    for i,(title,im) in enumerate(zip(titles,zoomed)):
        x=i*972; draw.text((x+8,8),title,fill=(255,230,80)); comparison.paste(im.convert('RGB'),(x,32))
    comparison.save(OUT/'B2_map_compare.png')
    close=Image.new('RGB',(750,300),(24,24,24)); draw=ImageDraw.Draw(close)
    for i,(title,s) in enumerate([('PREVIOUS',old),('NEW - requested another +15 deg CW' if args.previous else 'NEW - requested +15 deg CW',sp)]):
        big=s.resize((s.width*6,s.height*6),Image.Resampling.NEAREST)
        bg=Image.new('RGBA',big.size,(74,89,56,255)); bg.alpha_composite(big)
        x=12+i*370; draw.text((x,12),title,fill=(255,230,80)); close.paste(bg.convert('RGB'),(x,42))
    close.save(OUT/'B2_sprite_compare.png')
    assert hashes=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    result={'preview_only':True,'gameChangesApplied':False,'changed_asset':'B2',
            'requested_delta_degrees_clockwise':15,'exact_angle_verified':False,'manual_rotation_or_shear':False,
            'requested_cumulative_delta_clockwise':15+(previous_meta.get('requested_cumulative_delta_clockwise',previous_meta['requested_delta_degrees_clockwise']) if previous_meta else 0),
            'previous_variant':str(args.previous) if args.previous else 'original',
            'source':str(RAW),'references':[str(args.previous/'B2_raw.png') if args.previous else 'B2_original_raw_crop.png','B2_sat_crop.png','../with_tree/4_raw.png'],
            'provider':'openai-codex','model':'gpt-image-2-medium','requested_quality':'medium','reported_quality':'low',
            'old_size':list(old.size),'new_size':list(sp.size),'ground_centre_map':b2['centre_map'],
            'old_position':b2['position'],'new_position':[new_x,new_y],
            'changed_map_pixels':int(diff.sum()),'non_B2_map_pixels_unchanged':True,
            'accepted_sources_and_shared_docs_unchanged':True,'unrelated_overlap_pixels':unrelated_overlaps,
            'delivery':str(OUT)}
    (D/'manifest.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__': main()
