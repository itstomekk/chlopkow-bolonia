"""Build complete Frodo poses while preserving original walk and its palette.

Reuse WAJPER's verified background/component tools, never its identity or scale.
No per-frame fitting: one standing anchor per sheet, fixed scale for the sheet.
Palette derives exclusively from the approved Frodo walk, not the dark old lick.
"""
from pathlib import Path
import importlib.util
import json
import shutil

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
from generate_poses import JOBS

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / 'out'
spec = importlib.util.spec_from_file_location('dog_tools', ROOT / 'gen/wajper/build_wajper.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def fixed_palette(walk):
    a = np.asarray(walk)
    rgb = a[a[..., 3] > 0][:, :3]
    sample = Image.fromarray(rgb.reshape(1, -1, 3))
    q = sample.quantize(24, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    coat = np.array(q.getpalette(), dtype=np.int32).reshape(-1, 3)[:24]
    # Rare but identity-critical collar/tongue colours get explicit slots: frequency
    # quantisation of the small walk atlas otherwise discards them into dark brown.
    return np.vstack([coat, [180,45,48], [220,135,150], [245,232,204]])


def palette_map(im, palette):
    a = np.asarray(im).copy()
    flat = a[..., :3].astype(np.int32).reshape(-1, 3)
    distance = ((flat[:, None, :] - palette[None, :, :]) ** 2).sum(2)
    a[..., :3] = palette[np.argmin(distance, axis=1)].reshape(a.shape[:2] + (3,))
    a[a[..., 3] == 0, :3] = 0
    return Image.fromarray(a)


def native(fr, scale):
    dims = tuple(max(1, round(n * scale)) for n in fr.size)
    im = fr.resize(dims, Image.Resampling.BOX)
    a = np.asarray(im).copy()
    a[..., 3] = np.where(a[..., 3] >= 128, 255, 0)
    lab, n = ndimage.label(a[..., 3] > 0, structure=np.ones((3, 3)))
    sizes = np.bincount(lab.ravel())
    for i in range(1, n + 1):
        if sizes[i] <= 2:
            a[lab == i, 3] = 0
    return Image.fromarray(a)


def previews(strip, meta, walk):
    names, anims = meta['poses'], meta['anims']
    z, cols, cw, ch = 6, 8, 210, 215
    rows = (len(names) + cols - 1) // cols
    canvas = Image.new('RGBA', (cols * cw, 260 + rows * ch + 140), '#48533e')
    d = ImageDraw.Draw(canvas)
    d.text((12, 10), 'FRODO | 49 poses | fixed approved walk palette | original walk unchanged | x6', fill='white')
    canvas.alpha_composite(walk.resize((384, 192 * 4), Image.Resampling.NEAREST).crop((0, 384, 384, 576)), (10, 35))
    d.text((410, 80), 'Original walk, right view (identity and colour reference)', fill='white')
    for i, name in enumerate(names):
        x, y = i % cols * cw + 8, 260 + i // cols * ch
        canvas.alpha_composite(strip.crop((i * 32, 0, i * 32 + 32, 32)).resize((192, 192), Image.Resampling.NEAREST), (x, y))
        d.text((x, y + 192), f'{i+1}. {name}', fill='white')
    y = 260 + rows * ch
    d.text((10, y), 'Same game scale x3: walk | pant | yawn | tilt | lick | lickpaw | sleep | shake', fill='white')
    cells = [walk.crop((0, 64, 32, 96))]
    cells += [strip.crop((names.index(n)*32, 0, names.index(n)*32+32, 32)) for n in ['pant1','yawn3','tilt2','lick1','lickpaw1','sleep1','shake1']]
    for i, c in enumerate(cells):
        canvas.alpha_composite(c.resize((96,96), Image.Resampling.NEAREST), (10+i*110,y+20))
    canvas.convert('RGB').save(OUT / 'frodo_review.png')
    show = list(anims)
    cols = 8
    frames = []
    for t in range(24):
        f = Image.new('RGB', (cols*128, ((len(show)+cols-1)//cols)*148), '#48533e')
        d = ImageDraw.Draw(f)
        for j, action in enumerate(show):
            seq = anims[action]
            idx = names.index(seq[t % len(seq)])
            c = strip.crop((idx*32,0,idx*32+32,32)).resize((128,128), Image.Resampling.NEAREST)
            x,y=j%cols*128,j//cols*148
            f.paste(c,(x,y),c)
            d.text((x+4,y+130), action, fill='white')
        frames.append(f)
    frames[0].save(OUT/'frodo_behaviours.gif',save_all=True,append_images=frames[1:],loop=0,duration=180,disposal=2)


def main():
    OUT.mkdir(exist_ok=True)
    walk = Image.open(ROOT/'docs/img/frodo.png').convert('RGBA')
    palette = fixed_palette(walk)
    names, cells, scales = [], [], {}
    # Neutral standing frame (unchanged existing art).
    cells.append(palette_map(walk.crop((0,64,32,96)), palette)); names.append('stand')
    for sheet, nms in JOBS.items():
        rows = helper.figures(helper.key(Image.open(HERE/'raw'/f'{sheet}.png')), [1,4,4])
        anchor = rows[0][0]
        scale = 20 / anchor.height  # original side dog 26x20 px
        poses = rows[1]+rows[2]
        scale = min(scale, 28/max(max(p.size) for p in poses))
        scales[sheet] = round(scale,6)
        for name, fr in zip(nms, poses):
            fr = native(fr,scale)
            # shared feet baseline; translate, never independently resize a frame
            cell = Image.new('RGBA',(32,32))
            x = min(max(round(16-helper.body_cx(fr)),0),32-fr.width)
            cell.alpha_composite(fr,(x,29-fr.height))
            names.append(name); cells.append(palette_map(cell,palette))
    strip = Image.new('RGBA',(len(cells)*32,32))
    for i,c in enumerate(cells): strip.alpha_composite(c,(i*32,0))
    anims = dict(helper.ANIMS)
    anims['sit'] = ['yawn1']
    meta={'cell':32,'facing':'right','poses':names,'anims':anims}
    strip.save(OUT/'frodo_poses.png')
    (OUT/'frodo_poses.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
    report={'poses':len(names),'scales':scales,'palette':palette.tolist(),'frames':{}}
    for name,cell in zip(names,cells):
        a=np.asarray(cell).astype(np.int32); op=a[...,3]>0; rgb=a[op,:3]
        assert op.any(),name
        assert set(np.unique(a[...,3])) <= {0,255}
        assert not ((rgb[:,0]>160)&(rgb[:,2]>160)&(rgb[:,1]<100)).any()
        tan=(rgb[:,0]>rgb[:,2]+35)&(rgb[:,0]>130)&(rgb[:,1]>70)
        collar=(rgb[:,0]>70)&(rgb[:,0]>rgb[:,1]*1.7)&(rgb[:,1]<100)&(rgb[:,2]<100)
        report['frames'][name]={'bbox':cell.getchannel('A').getbbox(),'tan_pixels':int(tan.sum()),'red_pixels':int(collar.sum())}
        # Licking must keep tan markings, not become an all-black silhouette.
        if name.startswith(('lick','pant','yawn','tilt')):
            assert tan.sum()>=12,(name,'lost tan coat',tan.sum())
            assert collar.sum()>=1,(name,'lost red collar')
    previews(strip,meta,walk)
    (OUT/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'poses':len(names),'lick_tan':{n:r['tan_pixels'] for n,r in report['frames'].items() if n.startswith('lick')},'output':str(OUT)}))

if __name__=='__main__': main()
