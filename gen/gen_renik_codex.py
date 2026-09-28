"""Generate DJ Renik's NPC portrait and 4-direction walk cycle with Codex GPT Image.

Reference photos live in gitignored references/renik/ and are never committed.
Run from the repo root with Hermes' venv python:
  C:/Users/Lenovo/AppData/Local/hermes/hermes-agent/.venv/Scripts/python.exe gen/gen_renik_codex.py [npc|walk]
Outputs: gen/npc_src/renik_raw.png, gen/npc_src/renik_walkcycle_raw.png
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable
REF = lambda *p: os.path.join(ROOT, *p)
DESC = ("a stocky, heavyset bearded village DJ in his thirties: full reddish-brown beard and mustache, round friendly face, "
        "tan/khaki baseball cap worn BACKWARDS with black over-ear DJ headphones resting on top of the cap, black crew-neck "
        "t-shirt with a small colorful space-themed graphic on the chest, light-blue denim jeans, dark sneakers, black "
        "crossbody strap, big warm smile")

JOBS = {
    'npc': dict(
        refs=[REF('references', 'renik', 'renik_5.png'), REF('references', 'renik', 'renik_4.png'),
              REF('references', 'renik', 'renik_1.png'), REF('gen', 'npc_src', 'patryk.png')],
        aspect='portrait', out=REF('gen', 'npc_src', 'renik_raw.png'),
        prompt=(f"Full-body 16-bit pixel-art NPC sprite of {DESC}. Use the photos only for his look (beard, build, "
                "backwards cap, headphones, black tee). Match the chunky pixel-art style, dark outline and proportions of "
                "the last reference sprite. Front-facing 3/4 standing pose, one hand raised doing a cheerful DJ hype "
                "gesture. Single character, centered, full body head to feet, on a plain flat magenta #FF00FF background, "
                "no text, no ground shadow.")),
    'walk': dict(
        refs=[REF('references', 'renik', 'renik_5.png'), REF('references', 'renik', 'renik_1.png'),
              REF('docs', 'img', 'damian_sheet.png')],
        aspect='landscape', out=REF('gen', 'npc_src', 'renik_walkcycle_raw.png'),
        prompt=(f"8-bit/16-bit pixel art walk-cycle sprite sheet of {DESC}. Exactly 8 figures in a 4 columns x 2 rows "
                "grid, evenly spaced, same scale, all full-body head to feet, the same character in every cell. "
                "Row 1: [walking DOWN toward camera, frame A] [walking DOWN, frame B] [walking RIGHT side view, frame A] "
                "[walking RIGHT, frame B]. Row 2: [walking UP, back view, frame A] [walking UP, frame B] "
                "[walking LEFT side view, frame A] [walking LEFT, frame B]. Match the style, outline and proportions of "
                "the reference sprite sheet. Plain flat magenta #FF00FF background, no grid lines, no labels, no text.")),
}

for name in (sys.argv[1:] or list(JOBS)):
    j = JOBS[name]
    cmd = [PY, REF('gen', 'codex_gen.py'), '--aspect', j['aspect'], '--prompt', j['prompt'], '--out', j['out']]
    for r in j['refs']:
        cmd += ['--ref', r]
    p = subprocess.run(cmd, capture_output=True, text=True)
    print(name, p.stdout.strip() or p.stderr.strip()[-800:])
