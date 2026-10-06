"""Run every play-test and print a summary.

    python test/run_all.py                 # local server (python -m http.server 8765 --directory docs)
    python test/run_all.py <URL>           # e.g. the live GitHub Pages site

Each test reads the target from the ARK_URL environment variable. jump_test needs a river column
without a riverside tree; it is found automatically from docs/img/map_collide.png, so rebuilding the
map never breaks it.
"""
import os, subprocess, sys, time
import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
url = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8765/index.html'
env = dict(os.environ, ARK_URL=url, PYTHONIOENCODING='utf-8')


def river_column():
    c = np.array(Image.open('docs/img/map_collide.png').convert('L'))
    H, W = c.shape
    for x in range(200, W - 200, 20):
        col = c[:, x - 8:x + 8]
        low = np.nonzero((col == 128).any(1))[0]
        low = low[(low > 200) & (low < H - 200)]
        if len(low) < 8: continue
        y0, y1 = low.min(), low.max()
        if y1 - y0 < 30 and not (c[y0 - 80:y1 + 60, x - 9:x + 9] == 255).any():
            return x, y1
    raise SystemExit('no clear river column found')


jx, jy = river_column()
TESTS = [['music_test.py'], ['quest_test.py'], ['jump_test.py', str(jx), str(jy)], ['features_test.py'], ['quiz_expansion_test.py'], ['minigames_test.py'],
         ['church_test.py'], ['frodo_test.py'], ['soltys_surprise_test.py'], ['cemetery_memories_test.py'],
         ['village_sign_test.py'], ['edytka_test.py'], ['mushroom_test.py'], ['play_test.py'],
         ['character_selection_test.py'], ['arrival_log_test.py'], ['bercik_test.py'], ['eight_direction_test.py'], ['latest_world_requests_test.py'], ['sprite_background_test.py'],
         ['map_venues_test.py'], ['sept28_batch_test.py'], ['soltys_chat_test.py'], ['animals_test.py'], ['trees_test.py'], ['bukala_test.py'],
         ['forest_path_test.py'], ['duck_score_test.py'], ['mission_data_test.py'], ['mission_runtime_test.py'],
         ['mission_pilot_test.py'], ['save_migration_test.py'], ['local_competition_test.py'], ['local_competition_race_test.py'],
         ['save_name_test.py'], ['bison_test.py'], ['forest_styles_test.py'], ['forest_shade_test.py'], ['hud_corners_test.py'],
         ['branding_flow_test.py'], ['site_metadata_test.py'], ['splash_loading_test.py'], ['splash_timing_test.py']]
results = []
for t in TESTS:
    t0 = time.time()
    # Game entry now publishes an arrival: isolate all regression browsers from public relays.
    p = subprocess.run([sys.executable, os.path.join('test', 'isolated_browser_runner.py'), os.path.join('test', t[0]), *t[1:]], env=env, capture_output=True, text=True, encoding='utf-8', errors='replace')
    out = (p.stdout + p.stderr).strip().splitlines()
    bad = p.returncode != 0 or any('errors [' in l and 'errors []' not in l for l in out) or any(l.startswith('FAIL ') for l in out)
    results.append((t[0], not bad, time.time() - t0, out[-1] if out else ''))
    print(f"{'PASS' if not bad else 'FAIL'}  {t[0]:<28} {time.time() - t0:5.1f}s  {out[-1][:90] if out else ''}", flush=True)
    if bad: print('\n'.join('      ' + l for l in out[-15:]))
print(f"\n{sum(r[1] for r in results)}/{len(results)} passed against {url}")
sys.exit(0 if all(r[1] for r in results) else 1)
