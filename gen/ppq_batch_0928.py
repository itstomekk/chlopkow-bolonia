"""Batch PPQ gpt-image-2 generation for the Sept-28 content batch (NPCs, animals, trash, venues).
Run from gen/: python ppq_batch_0928.py [names...]   -> writes gen/raw0928/<name>.png, logs costs to raw0928/log.jsonl"""
import json, subprocess, sys, pathlib
HERE = pathlib.Path(__file__).parent
OUT = HERE / 'raw0928'; OUT.mkdir(exist_ok=True)
KEY = 'Solid flat pure magenta #FF00FF background everywhere around the sprites (chroma key), no shadows on the background, no text, no border, no frame.'
PIX = 'Crisp 16-bit SNES-era pixel art, clean dark outlines, limited palette, consistent soft top-left lighting, same pixel-art style as the reference image.'
NPC = ('Full-body single character sprite, standing facing the viewer, slight 3/4, whole figure visible head to shoes, centered, '
       'same proportions, head size and pixel-art style as the reference character. ' + PIX + ' ' + KEY)
JOBS = {
    'michal': ('npc_src/kuba_raw.png', 'portrait_4_3', 'Michał, a fictional Polish village man in his 30s who owns and runs a small rural shooting range: '
               'olive-khaki outdoor vest over a dark t-shirt, cargo trousers, sturdy boots, green baseball cap, yellow ear-protection earmuffs around his neck, '
               'short dark beard, confident friendly smile, arms crossed. No weapon. ' + NPC),
    'mateusz': ('npc_src/kuba_raw.png', 'portrait_4_3', 'Mateusz, a fictional young Polish village guy who organizes the village clean-up: fluorescent orange high-visibility vest over a grey hoodie, '
                'jeans, work gloves, holding a black trash bag in one hand and a litter picker in the other, short light-brown hair, cheerful. ' + NPC),
    'patryk': ('npc_src/kuba_raw.png', 'portrait_4_3', 'Patryk, a fictional Polish village musician who runs jazz nights in a barn: grey flat cap, white shirt with rolled sleeves, '
               'dark suspenders, brown trousers, holding a shiny golden saxophone, small moustache, relaxed smile. ' + NPC),
    'trash': (None, 'landscape_16_9', 'A sprite sheet of 5 separate small litter items in one horizontal row, evenly spaced with wide magenta gaps, each viewed from slightly above like '
              'top-down RPG pickup items: 1) crumpled clear-blue plastic water bottle, 2) crushed silver-green beer can, 3) tied black plastic trash bag, '
              '4) crumpled brown cardboard and paper litter, 5) old black car tyre lying flat. Each item the same size. ' + PIX + ' ' + KEY),
    'hen': ('dog_raw.png', 'landscape_16_9', 'Sprite sheet: one row of 4 animation frames of the same brown-red Polish farm hen (kura) seen from the side facing right, '
            'frames: walk step A, walk step B, pecking the ground with head down, standing alert. Same scale in each frame, evenly spaced. '
            'Match the pixel-art style, outline weight and shading of the reference dog sheet. ' + PIX + ' ' + KEY),
    'stray': ('dog_raw.png', 'landscape_16_9', 'Sprite sheet: one row of 4 animation frames of a scruffy black-and-white Polish village mutt dog seen from the side facing right, '
              'frames: trot A, trot B, sniffing ground, sitting and scratching ear. Same scale each frame, evenly spaced. Match the reference dog sheet style exactly. ' + PIX + ' ' + KEY),
    'bird': ('dog_raw.png', 'landscape_16_9', 'Sprite sheet: one row of 4 animation frames of a small brown house sparrow facing right: standing on ground, hopping, '
             'flying with wings up, flying with wings down. Same scale each frame, evenly spaced. Match the reference sheet style. ' + PIX + ' ' + KEY),
    'stork': ('dog_raw.png', 'landscape_16_9', 'Sprite sheet: one row of 4 animation frames of a white stork (bocian) with black wing tips and red beak and legs, side view facing right: '
              'walking step A, walking step B, standing on one leg, bending to catch a frog in the grass. Same scale, evenly spaced. Match the reference sheet style. ' + PIX + ' ' + KEY),
    'fox': ('dog_raw.png', 'landscape_16_9', 'Sprite sheet: one row of 4 animation frames of a red fox (lis) with white-tipped bushy tail, side view facing right: '
            'running gallop A, running gallop B, running gallop C, standing and looking back. Same scale, evenly spaced. Match the reference dog sheet style. ' + PIX + ' ' + KEY),
    'frodo_idle': ('frodo_sheet_raw.png', 'landscape_16_9', 'Sprite sheet of the SAME small dog as the reference (identical colours, markings, size and pixel style), '
                   'one row of 6 frames, all facing right: 1) sitting, 2) licking his own flank with head turned back and pink tongue out, 3) licking again with tongue further, '
                   '4) sitting and scratching his ear with a hind leg, 5) nose down sniffing the ground, 6) lying down relaxed. Evenly spaced, same scale. ' + PIX + ' ' + KEY),
    'barn': ('../docs/img/map_objects.png' if False else None, 'landscape_16_9', 'Top-down 3/4 view RPG map sprite (like Stardew Valley / Pokemon buildings) of a large old Polish wooden barn (stodoła) '
             'with dark weathered vertical planks, grey corrugated roof, big double doors wide open showing warm yellow light inside, a string of warm light bulbs over the entrance, '
             'a small hand-painted wooden sign above the doors, hay bales beside it, a couple of wooden benches in front. Single building, whole sprite visible. '
             + PIX + ' ' + KEY),
    'gravel': (None, 'landscape_16_9', 'Top-down 3/4 view RPG map sprite (like Stardew Valley) of a small rural gravel pit and village dump (żwirownia): a shallow excavation of pale sand and grey gravel '
               'with two conical gravel heaps, a rusty green open waste skip container with some rubbish, a small wooden sign post, a few tyre tracks, tufts of grass at the rim. '
               'Whole scene as one self-contained sprite. ' + PIX + ' ' + KEY),
}
names = sys.argv[1:] or list(JOBS)
for n in names:
    ref, aspect, prompt = JOBS[n]
    out = OUT / f'{n}.png'
    if out.exists(): print('skip', n); continue
    cmd = [sys.executable, str(HERE / 'ppq_gen.py'), '--prompt', prompt, '--out', str(out), '--aspect', aspect]
    if ref: cmd += ['--ref', str((HERE / ref).resolve())]
    r = subprocess.run(cmd, capture_output=True, text=True)
    line = (r.stdout.strip().splitlines() or [''])[-1]
    print(n, r.returncode, line[:300], r.stderr[-400:] if r.returncode else '')
    with open(OUT / 'log.jsonl', 'a', encoding='utf-8') as f: f.write(json.dumps(dict(name=n, rc=r.returncode, out=line[:500], err=r.stderr[-800:])) + '\n')
