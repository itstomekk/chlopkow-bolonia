"""Whole-yard pilot. Accepted house/tree retained; three generated shed candidates.
Preview only. B3 is explicitly an unconfirmed satellite hypothesis.
"""
import sys,json,math,hashlib,shutil
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from scipy import ndimage
P=Path(__file__).resolve().parent
PILOT=P.parent
ROOT=P.parents[2]
sys.path.insert(0,str(PILOT))
sys.path.insert(0,str(ROOT/'osm'))
from process_versions import pixelate,arek
from build_walk_cycles import remove_magenta_background
from geo import P as game_point
RAW=Path('C:/Users/Lenovo/AppData/Local/hermes/cache/generated/images/openai_codex_gpt-image-2-medium_20261004_201355_56f2c386.png')
OUT=Path('C:/Users/Lenovo/Hermes/image-gen/2026-10-04-chlopkow-full-yard')
BOX=(2070,4450,2390,4730)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    protected=[ROOT/'docs/map.json',ROOT/'docs/img/map_ground.png',ROOT/'docs/img/map_objects.png',PILOT/'with_tree/4.png']
    hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    shutil.copy2(RAW,P/'outbuildings_raw.png')
    arr=np.array(remove_magenta_background(Image.open(RAW)))
    lab,n=ndimage.label(arr[:,:,3]>0,structure=np.ones((3,3),bool))
    sizes=np.bincount(lab.ravel()); sizes[0]=0
    ks=[int(k) for k in range(1,n+1) if sizes[k]>sizes.max()*.02]
    assert len(ks)==3, f'Expected 3 isolated buildings, got {len(ks)}'
    bounds=[]
    for k in ks:
        yy,xx=np.where(lab==k)
        box=(int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1)
        bounds.append((k,box))
    lower=max(bounds,key=lambda v:v[1][1])
    upper=sorted([v for v in bounds if v!=lower],key=lambda v:v[1][0])
    mapping={'B1':upper[0],'B2':lower,'B3?':upper[1]}
    references=json.loads((P/'references.json').read_text(encoding='utf-8'))
    gx,gy=references['origin_global_px']
    world=256*2**references['zoom']
    # Third candidate is an uncertain satellite rectangle, not an invented OSM id.
    px,py=gx+397.5,gy+522
    lon=px/world*360-180
    lat=math.degrees(math.atan(math.sinh(math.pi*(1-2*py/world))))
    b3centre=game_point(lat,lon)
    es=json.loads((ROOT/'osm/chlopkow.json').read_text(encoding='utf-8'))['elements']
    es={e['id']:e for e in es if e.get('geometry')}
    centres={}
    for name,id in [('B1',993157696),('B2',993157706)]:
        ring=es[id]['geometry'][:-1]
        centres[name]=game_point(sum(g['lat'] for g in ring)/len(ring),sum(g['lon'] for g in ring)/len(ring))
    centres['B3?']=b3centre
    targets={'B1':36,'B2':55,'B3?':17}
    records=[]
    sprites=[]
    for name,(k,box) in mapping.items():
        one=arr.copy(); one[lab!=k]=0
        raw=Image.fromarray(one).crop(box)
        sp=pixelate(raw,targets[name])
        a=np.array(sp); assert set(np.unique(a[:,:,3])).issubset({0,255})
        assert not np.any((a[:,:,3]>0)&(a[:,:,0]>180)&(a[:,:,2]>150)&(a[:,:,1]<100))
        path=P/(name.replace('?','_candidate')+'.png'); sp.save(path)
        # Roof points up; visible wall ground band is bottom 38%. Ground centroid is 81% of height.
        cx,cy=centres[name]
        x=round(cx-sp.width/2); y=round(cy-sp.height*.81)
        sprites.append((name,sp,x,y,y+sp.height))
        records.append({'id':name,'osm_way':{'B1':993157696,'B2':993157706}.get(name),
                        'status':'unconfirmed satellite hypothesis' if '?' in name else 'OSM roof corroborated by satellite',
                        'centre_map':list(centres[name]),'sprite_size':list(sp.size),'position':[x,y],
                        'raw_component_box':list(box),'sprite':str(path)})
    assert len(records)==3
    house=Image.open(protected[3]).convert('RGBA')
    hm=json.loads((PILOT/'with_tree/manifest.json').read_text(encoding='utf-8'))
    h=next(v for v in hm['variants'] if v['id']=='4')
    hx,hy=h['position']; hx+=2; hy+=12
    sprites.append(('HOUSE D',house,hx,hy,hy+house.height))
    ground=np.array(Image.open(protected[1]).convert('RGBA').crop(BOX))
    objects=np.array(Image.open(protected[2]).convert('RGBA').crop(BOX))
    original_objects=objects.copy(); original_ground=ground.copy()
    lab,_=ndimage.label(objects[:,:,3]>0)
    k_house=lab[4595-BOX[1],2222-BOX[0]]
    k_barns=lab[4590-BOX[1],2163-BOX[0]]
    assert k_barns==lab[4635-BOX[1],2190-BOX[0]]
    assert int((lab==k_house).sum())==641 and int((lab==k_barns).sum())==4135
    removed=(lab==k_house)|(lab==k_barns)
    objects[removed]=0
    assert np.array_equal(objects[~removed],original_objects[~removed])
    lab,_=ndimage.label(np.all(ground[:,:,:3]==[58,84,40],axis=2))
    shadow_ids=[lab[y-BOX[1],x-BOX[0]] for x,y in [(2225,4623),(2170,4620),(2190,4665)]]
    shadow=np.isin(lab,shadow_ids)
    assert 0 not in shadow_ids and int(shadow.sum())==3308
    _,ix=ndimage.distance_transform_edt(shadow,return_indices=True)
    ground[shadow]=ground[ix[0][shadow],ix[1][shadow]]
    assert np.array_equal(ground[~shadow],original_ground[~shadow])
    before=Image.fromarray(original_ground); before.alpha_composite(Image.fromarray(original_objects))
    scene=Image.fromarray(ground)
    for name,sp,x,y,base in sprites:
        sh=Image.new('RGBA',sp.size,(58,84,40,255)); sh.putalpha(sp.getchannel('A'))
        foot=sh.crop((0,sp.height//2,sp.width,sp.height))
        scene.alpha_composite(foot,(x-BOX[0]+5,y-BOX[1]+sp.height//2+3))
    scene.alpha_composite(Image.fromarray(objects))
    # Report whether proposed pixels hide any unrelated objects; do not silently accept overlap.
    unrelated_overlap=0
    for name,sp,x,y,base in sorted(sprites,key=lambda s:s[4]):
        sy,sx=y-BOX[1],x-BOX[0]
        unrelated_overlap+=int(np.sum((np.array(sp.getchannel('A'))>0)&(objects[sy:sy+sp.height,sx:sx+sp.width,3]>0)))
        scene.alpha_composite(sp,(sx,sy))
    assert unrelated_overlap==0, f'Unrelated scenery occlusion: {unrelated_overlap}'
    player=arek()
    for im in [before,scene]: im.alpha_composite(player,(2289-BOX[0],4646-BOX[1]))
    before=before.resize((960,840),Image.Resampling.NEAREST)
    after=scene.resize((960,840),Image.Resampling.NEAREST)
    after.save(OUT/'whole_yard_map.png')
    comparison=Image.new('RGB',(1932,872),(24,24,24)); d=ImageDraw.Draw(comparison)
    d.text((8,8),'CURRENT PROCEDURAL YARD',fill=(255,230,80))
    d.text((980,8),'WHOLE YARD PILOT - B3 is provisional',fill=(255,230,80))
    comparison.paste(before.convert('RGB'),(0,32)); comparison.paste(after.convert('RGB'),(972,32))
    comparison.save(OUT/'whole_yard_compare.png')
    review=after.convert('RGB'); d=ImageDraw.Draw(review)
    for name,sp,x,y,base in sprites:
        xx=(x-BOX[0])*3; yy=(y-BOX[1])*3-20
        label=name if '?' not in name else 'B3? confirm'
        d.rectangle((xx,yy,xx+100,yy+16),fill=(0,0,0))
        d.text((xx+3,yy+2),label,fill=(0,255,255) if '?' in name else (255,230,80))
    review.save(OUT/'whole_yard_labelled.png')
    close=Image.new('RGB',(1040,460),(24,24,24)); d=ImageDraw.Draw(close)
    for i,(name,sp,x,y,base) in enumerate(sprites[:3]):
        big=sp.resize((sp.width*6,sp.height*6),Image.Resampling.NEAREST)
        bg=Image.new('RGBA',big.size,(74,89,56,255)); bg.alpha_composite(big)
        xx=10+i*340
        d.text((xx,12),name if '?' not in name else 'B3? provisional',fill=(255,230,80))
        close.paste(bg.convert('RGB'),(xx,42))
    close.save(OUT/'outbuildings_closeup.png')
    shutil.copy2(P/'sat_candidates.png',OUT/'sat_candidates.png')
    assert hashes=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    result={'preview_only':True,'gameChangesApplied':False,'outbuilding_candidates_count':len(records),
            'confirmed_osm_outbuildings':2,'uncertain_candidate_count':1,'generation_source':str(RAW),
            'provider':'openai-codex','model':'gpt-image-2-medium','requested_quality':'medium','reported_quality':'low',
            'house_unchanged':True,'house_translation':[2,12],'docs_unchanged':True,
            'non_target_layer_pixels_unchanged':True,'unrelated_scenery_occlusion_pixels':unrelated_overlap,
            'outbuildings':records,'delivery':str(OUT)}
    (P/'manifest.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__': main()
