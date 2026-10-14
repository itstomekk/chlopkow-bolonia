"""Preview only: replace the exact procedural house with selected Warm art.
Never writes docs/ or rebuilds the shared map. Preserve all neighbouring pixels.
"""
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[2]
D = Path(__file__).resolve().parent
OLD = dict(x=2208, y=4580, w=31, h=44)
BOX = (2070, 4450, 2450, 4770)
ZOOM = 3

def main():
    meta = json.loads((ROOT/'docs/map.json').read_text(encoding='utf-8'))
    matches = [o for o in meta['objects'] if all(o.get(k)==v for k,v in OLD.items())]
    assert len(matches)==1, 'Target building changed; inspect again rather than guess'
    obj = matches[0]
    ground = np.array(Image.open(ROOT/'docs/img/map_ground.png').convert('RGBA').crop(BOX))
    layer = np.array(Image.open(ROOT/'docs/img/map_objects.png').convert('RGBA').crop(BOX))
    before = Image.fromarray(ground); before.alpha_composite(Image.fromarray(layer))
    # Remove only the isolated alpha component containing the target house roof.
    labels, _ = ndimage.label(layer[:,:,3]>0)
    component = int(labels[4595-BOX[1], 2222-BOX[0]])
    assert component>0
    old_mask = labels==component
    ys,xs = np.where(old_mask)
    assert xs.min()+BOX[0]>=OLD['x'] and xs.max()+BOX[0]<OLD['x']+OLD['w']
    assert ys.min()+BOX[1]>=OLD['y'] and ys.max()+BOX[1]<OLD['y']+OLD['h']
    original = layer.copy()
    layer[old_mask]=0
    assert np.array_equal(layer[~old_mask],original[~old_mask]), 'Neighbour changed'
    # Remove only the target's connected flat procedural shadow, not neighbouring shadows.
    shadows, _ = ndimage.label(np.all(ground[:,:,:3]==[58,84,40],axis=2))
    shadow_id = int(shadows[4623-BOX[1],2225-BOX[0]])
    assert shadow_id>0
    shadow_mask = shadows==shadow_id
    sy,sx=np.where(shadow_mask)
    assert sx.max()-sx.min()<40 and sy.max()-sy.min()<40
    _, nearest = ndimage.distance_transform_edt(shadow_mask,return_indices=True)
    ground[shadow_mask]=ground[nearest[0][shadow_mask],nearest[1][shadow_mask]]
    sprite = Image.open(D/'warm.png').convert('RGBA')
    assert sprite.size==(58,55), 'Keep selected smaller Warm sprite'
    cx=round(obj['x']+obj['w']/2)
    base=round(obj['base'])
    x,y=cx-sprite.width//2,base-sprite.height
    after=Image.fromarray(ground)
    sh=Image.new('RGBA',sprite.size,(58,84,40,255)); sh.putalpha(sprite.getchannel('A'))
    foot=sh.crop((0,sprite.height//2,sprite.width,sprite.height))
    after.alpha_composite(foot,(x-BOX[0]+5,y-BOX[1]+sprite.height//2+3))
    after.alpha_composite(Image.fromarray(layer))
    after.alpha_composite(sprite,(x-BOX[0],y-BOX[1]))
    # Draw the player south of the house for scale, without obscuring it.
    player=Image.open(ROOT/'docs/img/arek_sheet_8dir.png').convert('RGBA').crop((0,0,130,170))
    player=player.crop(player.getbbox())
    player=player.resize((round(player.width*40/player.height),40),Image.Resampling.NEAREST)
    for panel in (before,after):
        panel.alpha_composite(player,(cx+65-BOX[0],base+65-40-BOX[1]))
    before=before.resize((before.width*ZOOM,before.height*ZOOM),Image.Resampling.NEAREST)
    after=after.resize((after.width*ZOOM,after.height*ZOOM),Image.Resampling.NEAREST)
    after.save(D/'warm_placed.png')
    w,h=before.size
    comparison=Image.new('RGB',(w*2+12,h+32),(24,24,24))
    draw=ImageDraw.Draw(comparison)
    draw.text((8,8),'BEFORE: procedural house',fill=(255,230,80))
    draw.text((w+20,8),'AFTER: Warm replaces that house, same ground anchor',fill=(255,230,80))
    comparison.paste(before.convert('RGB'),(0,32))
    comparison.paste(after.convert('RGB'),(w+12,32))
    comparison.save(D/'warm_replacement_compare.png')
    info={'preview_only':True,'osm_way':993157691,'variant':'warm','size':list(sprite.size),
          'old_object':obj,'placement':{'x':x,'y':y,'center_x':cx,'base':base},
          'removed_old_house_pixels':int(old_mask.sum()),'removed_old_shadow_pixels':int(shadow_mask.sum()),
          'neighbour_layer_unchanged':True}
    (D/'warm_placement.json').write_text(json.dumps(info,indent=2),encoding='utf-8')
    print(json.dumps(info))
    print('Saved',D/'warm_replacement_compare.png')

if __name__=='__main__':
    main()
