"""Generate complete Frodo behaviours from his approved walk identity, never the dark old lick sheet."""
import concurrent.futures
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
RAW = HERE / 'raw'
JOBS = {
    'idle': ['pant1', 'pant2', 'pant3', 'pant4', 'scratch1', 'scratch2', 'sniff1', 'sniff2'],
    'yawn': ['yawn1', 'yawn2', 'yawn3', 'yawn4', 'tilt1', 'tilt2', 'tilt3', 'tilt4'],
    'fun': ['shake1', 'shake2', 'shake3', 'shake4', 'bark1', 'bark2', 'howl1', 'howl2'],
    'dig': ['dig1', 'dig2', 'dig3', 'dig4', 'playbow', 'lie', 'belly1', 'belly2'],
    'run': ['run1', 'run2', 'run3', 'run4', 'jump', 'beg', 'wag1', 'wag2'],
    'sleep': ['sleep1', 'sleep2', 'stretch1', 'stretch2', 'lick1', 'lick2', 'lickpaw1', 'lickpaw2'],
}
ACTIONS = {
    'idle': 'Row 2 four sitting panting frames: tongue out/in, small ear motion. Row 3: two scratching-behind-ear frames (hind foot up/down), two nose-to-ground sniffing frames.',
    'yawn': 'Row 2 four sitting YAWN frames: mouth closed, half-open, VERY WIDE OPEN pink tongue eyes squeezed shut, closing. Row 3 four sitting HEAD TILT frames: neutral, head visibly tilted left, neutral, tilted right. Keep torso and paws identical; head rotates, NEVER zooms.',
    'fun': 'Row 2 four WET-DOG SHAKE frames: body twists left/right, ears flap, a few drops. Row 3 two barking frames mouth closed/open, two sitting howling frames nose pointed skywards mouth closed/open.',
    'dig': 'Row 2 four DIG frames: front paws scraping soil backwards in alternating strokes. Row 3: play bow (front low, rump high), lying belly down head on front paws, two belly-up rolling frames paws waving.',
    'run': 'Row 2 four RUN gallop frames: gathered legs, extended legs airborne, gathered other phase, extended other phase. Row 3: happy jump all paws airborne, begging sitting upright front paws lifted, two tail-wag frames (tail swings opposite sides).',
    'sleep': 'Row 2: two curled-up sleeping breathing frames nose tucked into tail, front stretch with rump raised, hind-leg stretch. Row 3 FOUR sitting grooming frames: tongue out licking flank, tongue further out, raised front paw being licked, second paw-lick frame. IMPORTANT the tan muzzle, eyebrow markings, chest and tan legs stay bright GOLDEN TAN in ALL grooming poses, never turn black.',
}
IDENTITY = ('FRODO from Image 1, same exact approved dog, NOT Wajper. Sleek short-coated BLACK AND GOLDEN-TAN dog, lean medium build, '
            'upright pointed triangular ears (black backs, tan inner ears), bright warm golden-tan eyebrows, cheeks, muzzle sides, chest patch, '
            'belly edge and lower legs/paws. Near-black crown, saddle/back, upper legs and raised hook-shaped tail. '
            'Thin bright RED COLLAR visible in EVERY pose. Pink tongue. Preserve the bright tan regions in grooming and sleeping, '
            'never replace tan face/chest with black. Do not add shaggy fur, silver coat, drooping ears or a different breed.')
STYLE = ('Exact chunky pixel-art outline and flat colours of Image 1. Same top-down 3/4 camera. '
         'Uniform flat daylight, absolutely no pose-specific darkness/shadow/lighting/filter. '
         'Bold clean black silhouette, only about 16 colours; same dog scale, same body proportions in every cell. '
         'Solid flat #FF00FF background, NO ground, NO cast shadows, NO text, NO labels, NO grids. '
         'Each complete dog isolated with a generous gap from every cell edge; no overlapping figures.')

def generate(name):
    RAW.mkdir(parents=True, exist_ok=True)
    prompt = (f'A 4-column by 3-row sprite sheet of {IDENTITY} {STYLE} '
              'Row 1 has exactly ONE dog, in the FIRST cell: neutral standing side profile facing RIGHT, '
              'an exact duplicate of Image 1 side-view dog as size and colour anchor. Leave remaining 3 cells of row 1 empty MAGENTA. '
              f'{ACTIONS[name]} All poses face RIGHT (except belly-up); exactly 9 dogs total: 1 + 4 + 4. '
              'Each animation is drawn at constant scale; keep planted feet on a common baseline within the row.')
    (RAW / f'{name}.prompt.txt').write_text(prompt, encoding='utf-8')
    command = [sys.executable, str(ROOT / 'gen/codex_gen.py'), '--ref', str(ROOT / 'gen/frodo_sheet_raw.png'),
               '--aspect', 'landscape', '--prompt', prompt, '--out', str(RAW / f'{name}.png')]
    result = subprocess.run(command, capture_output=True, text=True, timeout=300)
    (RAW / f'{name}.log').write_text(result.stdout + result.stderr, encoding='utf-8')
    if result.returncode:
        raise RuntimeError(f'{name}: {result.stdout[-1000:]} {result.stderr[-1000:]}')
    print(name, result.stdout.strip(), flush=True)

if __name__ == '__main__':
    names = sys.argv[1:] or list(JOBS)
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(generate, names))
