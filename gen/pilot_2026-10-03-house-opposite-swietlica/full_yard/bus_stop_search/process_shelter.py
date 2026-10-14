"""Prepare standalone shelter pilot, not integrated or placed at unverified coordinates."""
from pathlib import Path
import sys,json,hashlib,shutil
from PIL import Image,ImageDraw
import numpy as np
P=Path(__file__).resolve().parent
PILOT=P.parents[1]
ROOT=PILOT.parents[1]
sys.path.insert(0,str(PILOT))
import process_versions as pipeline
RAW=Path('C:/Users/Lenovo/AppData/Local/hermes/cache/generated/images/openai_codex_gpt-image-2-medium_20261005_074717_ca074b17.png')
OUT=Path('C:/Users/Lenovo/Hermes/image-gen/2026-10-05-chlopkow-przystanek-dom-muchy')
PROTECTED=[ROOT/'docs/map.json',ROOT/'docs/img/map_objects.png',ROOT/'docs/img/map_ground.png',PILOT/'with_tree/4.png',P.parent/'manifest_selected.json',P.parent/'B3_candidate.png']


def main():
    hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in PROTECTED}
    OUT.mkdir(parents=True,exist_ok=True)
    shutil.copy2(RAW,OUT/'shelter_raw.png')
    clean=pipeline.clean(OUT/'shelter_raw.png')
    pipeline.COLORS=24
    sprite=pipeline.pixelate(clean,18)
    sprite.save(OUT/'shelter.png')
    a=np.array(sprite); alpha=a[:,:,3]
    colours=len(np.unique(a[:,:,:3][alpha>0],axis=0))
    assert set(np.unique(alpha))=={0,255}
    assert colours<=24
    assert not np.any((alpha>0)&(a[:,:,0]>180)&(a[:,:,2]>150)&(a[:,:,1]<100))
    assert sprite.width==18 and 12<=sprite.height<=30
    assert np.all(a[:,:,:3][alpha==0]==0)
    zoom=10
    big=sprite.resize((sprite.width*zoom,sprite.height*zoom),Image.Resampling.NEAREST)
    review=Image.new('RGB',(760,370),(24,24,24)); d=ImageDraw.Draw(review)
    d.text((18,12),'REAL STREET VIEW REFERENCE',fill=(255,230,80))
    source=Image.open(P/'shelter_photo_crop.png').convert('RGB')
    source.thumbnail((320,290)); review.paste(source,(18,42))
    for label,bg,x in [('SPRITE x10',(74,89,56,255),365),('ALPHA CHECK',(255,0,255,255),565)]:
        d.text((x,12),label,fill=(255,230,80))
        panel=Image.new('RGBA',big.size,bg); panel.alpha_composite(big)
        review.paste(panel.convert('RGB'),(x,42))
    d.text((365,340),f'{sprite.width}x{sprite.height} px / {colours} colours / hard alpha',fill='white')
    review.save(OUT/'shelter_review.png')
    green=Image.new('RGBA',(big.width+80,big.height+80),(74,89,56,255))
    green.alpha_composite(big,(40,40)); green.convert('RGB').save(OUT/'shelter_preview.png')
    assert hashes=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in PROTECTED}
    result={'asset_id':'dom_muchy_bus_shelter','human_identification':'small bus-stop shelter north of Dom Muchy',
        'original_asset_unchanged':'B3_candidate.png','source_reference_files':[str(P/'shelter_near_close.jpg'),str(P/'shelter_photo_crop.png'),str(PILOT/'with_tree/4_raw.png')],
        'source_generation':str(RAW),'generator':'GPT Image via Codex OAuth','model':'gpt-image-2-medium','requested_quality':'medium','reported_quality':'medium',
        'request_id':'45a397de-262e-4ece-8b8f-36ce2c218a0e','native_size':list(sprite.size),'opaque_colour_count':colours,
        'alpha_values':[0,255],'magenta_halo_pixels':0,'placement':None,'placement_note':'No precise satellite match established; do not reuse guessed B3 coordinates.',
        'gameChangesApplied':False,'accepted_pilot_and_shared_game_files_unchanged':True,
        'delivered_sprite':str(OUT/'shelter.png'),'review':str(OUT/'shelter_review.png')}
    (OUT/'manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    (P/'shelter_generation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
