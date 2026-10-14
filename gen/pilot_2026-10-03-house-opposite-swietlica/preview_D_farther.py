"""Translate selected fourth house+tree away from the diagonal road. Preview only.
Keep sprite byte-for-byte unchanged; preserve all shared docs files.
"""
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy import ndimage
from PIL import Image, ImageDraw
from process_versions import arek

ROOT=Path(__file__).resolve().parents[2]
P=Path(__file__).resolve().parent
OUT=Path('C:/Users/Lenovo/Hermes/image-gen/2026-10-04-chlopkow-house-tree')
BOX=(2070,4450,2390,4730)


def main():
    manifest=json.loads((P/'with_tree/manifest.json').read_text(encoding='utf-8'))
    entry=next(v for v in manifest['variants'] if v['id']=='4')
    sprite_path=P/'with_tree/4.png'
    protected=[ROOT/'docs/map.json',ROOT/'docs/img/map_ground.png',ROOT/'docs/img/map_objects.png',sprite_path]
    hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    ground=np.array(Image.open(protected[1]).convert('RGBA').crop(BOX))
    objects=np.array(Image.open(protected[2]).convert('RGBA').crop(BOX))
    original_objects=objects.copy()
    lab,_=ndimage.label(objects[:,:,3]>0)
    k=lab[4595-BOX[1],2222-BOX[0]]
    target=lab==k
    assert k>0 and int(target.sum())==641, 'Original house layer changed; inspect before previewing'
    objects[target]=0
    assert np.array_equal(objects[~target],original_objects[~target])
    lab,_=ndimage.label(np.all(ground[:,:,:3]==[58,84,40],axis=2))
    k=lab[4623-BOX[1],2225-BOX[0]]
    shadow=lab==k
    assert k>0 and int(shadow.sum())==396
    _,ix=ndimage.distance_transform_edt(shadow,return_indices=True)
    ground[shadow]=ground[ix[0][shadow],ix[1][shadow]]
    sprite=Image.open(sprite_path).convert('RGBA')
    assert list(sprite.size)==entry['compound_sprite_size']
    x,y=entry['position']
    dx,dy=2,12
    frames=[]
    overlaps=[]
    for label,offset in [('D - before',0),('D - farther from road',dy)]:
        px=x+(dx if offset else 0)
        sc=Image.fromarray(ground)
        sh=Image.new('RGBA',sprite.size,(58,84,40,255))
        sh.putalpha(sprite.getchannel('A'))
        foot=sh.crop((0,sprite.height//2,sprite.width,sprite.height))
        sc.alpha_composite(foot,(px-BOX[0]+5,y+offset-BOX[1]+sprite.height//2+3))
        sc.alpha_composite(Image.fromarray(objects))
        alpha=np.zeros(objects.shape[:2],bool)
        sy,sx=y+offset-BOX[1],px-BOX[0]
        alpha[sy:sy+sprite.height,sx:sx+sprite.width]=np.array(sprite.getchannel('A'))>0
        overlaps.append(int(np.sum(alpha & (objects[:,:,3]>0))))
        sc.alpha_composite(sprite,(sx,sy))
        player=arek()
        sc.alpha_composite(player,(2224+65-BOX[0],4621+65-40-BOX[1]))
        zoom=sc.resize((sc.width*3,sc.height*3),Image.Resampling.NEAREST)
        frames.append((label,zoom))
    # No new occlusion of neighbouring object layer.
    assert overlaps[1]<=overlaps[0], overlaps
    w,h=frames[0][1].size
    comparison=Image.new('RGB',(w*2+12,h+32),(24,24,24))
    draw=ImageDraw.Draw(comparison)
    for i,(label,im) in enumerate(frames):
        draw.text((i*(w+12)+8,8),label,fill=(255,230,80))
        comparison.paste(im.convert('RGB'),(i*(w+12),32))
    comparison.save(OUT/'D_farther_comparison.png')
    frames[1][1].save(OUT/'D_farther_map.png')
    assert hashes=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    result={'preview_only':True,'selected_variant':'4/Chunky','translation':[dx,dy],
            'previous_position':[x,y],'new_position':[x+dx,y+dy],
            'neighbour_overlap_pixels':overlaps,'docs_unchanged':True,'sprite_unchanged':True,
            'comparison':str(OUT/'D_farther_comparison.png'),'after':str(OUT/'D_farther_map.png')}
    (OUT/'D_farther_manifest.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    main()
