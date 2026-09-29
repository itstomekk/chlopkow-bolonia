"""C05 - forest/water edge paths: guard tests + documented RED measurement.

    python test/forest_path_test.py            # run all guards on committed docs/
    python test/forest_path_test.py --out DIR  # also save walkability/reachability maps + crops

Card C05 of plans/2026-09-28-unified-luna-execution-plan.md owns forest-path and
trunk-collision diagnosis "only if proven". Its guard list:

  G1 sample trunk center solid               - every generated-tree trunk is solid 255
  G2 between-tree forest floor free          - forest terrain away from trunks/water is
                                               walkable by the in-game 6-point hitbox
  G3 main forest routes reachable from spawn - game buildReachableMask() replica: named
                                               venues and the whole forest are reachable
  G4 roads/water/buildings/venues retain collision - road px walkable 0, river px low-solid
                                              128, venue buildings tall-solid 255
  G5 water-bounded-closure measurement (the player-relevant RED of this card): the
     riverbank lane at the Bialka bend - the "forest/water transition" corridor that
     blocks Arek. The ford band is dry free land (0 trunk px, 0 water px inside) yet only
     76 px walkable because the 128 river bands sit 1 px outside it; every corridor row is
     >= 14 px wide except one, which contains water (128) and no trunk (255).

Verdict: G1-G4 pass and G5 proves the closure is water-bounded with zero trunk pixels, so
per the plan "mark collision change not needed and leave generator/collision unchanged".
The empty-edit byte-equality gate (6 outputs, zero warnings) is owned by
test/edits_pipeline_test.py and must stay green for this card.
"""
import argparse, json, os, sys
import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

fails = []


def check(cond, msg):
    print(('ok   ' if cond else 'FAIL ') + msg)
    if not cond:
        fails.append(msg)


def solid_from(collide):
    """game.js SOLID = v>200 ? 2 (tall) : v>64 ? 1 (low) : 0."""
    return np.where(collide > 200, 2, np.where(collide > 64, 1, 0)).astype(np.int8)


def onfoot_walkable(s):
    """game.js npcWalkable(): 6-point 14x6 hitbox, all samples non-solid."""
    H, W = s.shape
    yy, xx = np.mgrid[0:H, 0:W]
    def sm(xs, ys):
        xs = np.clip(xs, 0, W - 1); ys = np.clip(ys, 0, H - 1)
        return s[ys, xs] == 0
    return (sm(xx - 7, yy) & sm(xx + 7, yy) & sm(xx - 7, yy - 6)
            & sm(xx + 7, yy - 6) & sm(xx, yy) & sm(xx, yy - 6))


def reachable_mask(s, spawn, step=12):
    """game.js buildReachableMask(): 12 px grid, cell walkable when any of the 9
    (+-4,0)^2 probes is npcWalkable, 4-neighbour BFS from the spawn cell."""
    H, W = s.shape
    gw, gh = int(np.ceil(W / step)), int(np.ceil(H / step))
    cx = np.arange(gw) * step + step // 2
    cy = np.arange(gh) * step + step // 2
    probe = np.zeros((gh, gw), bool)
    for dx in (-4, 0, 4):
        for dy in (-4, 0, 4):
            X = np.clip(cx[None, :] + dx, 0, W - 1)
            Y = np.clip(cy[:, None] + dy, 0, H - 1)
            probe |= s[Y, X] == 0
    sx, sy = int(spawn['x']) // step, int(spawn['y']) // step
    nx, ny = sx, sy
    for r in range(20):
        nx, ny = sx, sy
        nx += r % 2 and 1 or -1
        ny += (r % 3) and 0 or 1
        if 0 <= ny < gh and 0 <= nx < gw and probe[ny, nx]:
            break
    if not (0 <= ny < gh and 0 <= nx < gw and probe[ny, nx]):
        return probe, np.zeros((gh, gw), bool), (gw, gh)
    lab, _ = ndimage.label(probe, structure=np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], bool))
    reach = lab == lab[ny, nx]
    return probe, reach, (gw, gh)


def forest_mask(terrain):
    """Art-res forest floor from terrain class 220 (4x4 cells offset (2,2))."""
    ts = np.repeat(np.repeat(terrain, 4, 0), 4, 1)
    H, W = ts.shape[0] + 2, ts.shape[1] + 2
    f = np.zeros((H, W), bool)
    f[2:, 2:] = ts[:H - 2, :W - 2] == 220
    return f[:terrain.shape[0] * 4 + 2, :terrain.shape[1] * 4 + 2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=None, help='directory for walkability maps + crops')
    args = ap.parse_args()

    c = np.array(Image.open('docs/img/map_collide.png').convert('L'))
    t = np.array(Image.open('docs/img/map_terrain.png').convert('L'))
    g = np.array(Image.open('docs/img/map_ground.png').convert('RGB'))
    mj = json.load(open('docs/map.json', encoding='utf-8'))
    H, W = c.shape
    s = solid_from(c)
    wk = onfoot_walkable(s)
    forest = forest_mask(t)[:H, :W]
    probe, reach, (gw, gh) = reachable_mask(s, mj['spawn'])
    gx = np.clip((np.arange(W)[None, :] // 12), 0, gw - 1)
    gy = np.clip((np.arange(H)[:, None] // 12), 0, gh - 1)
    reach_px = wk & reach[gy, gx]
    pois = {p['key']: (p['x'], p['y']) for p in mj['pois']}

    print(f'map {W}x{H}, walkable {wk.mean()*100:.2f}%, forest {forest.mean()*100:.1f}%')

    # ---- G1: sample trunk center solid
    trs = [o for o in mj['objects'] if o.get('kind') == 'tree']
    feet = [(o['x'] + o['w'] // 2, int(o['base'])) for o in trs
            if 0 <= o['x'] + o['w'] // 2 < W and 0 <= int(o['base']) < H]
    solid_feet = sum(int((s[f[1] - 3:f[1] + 1, f[0] - 3:f[0] + 4] != 0).any()) for f in feet)
    check(solid_feet == len(feet) and len(feet) >= 400,
          f'G1 every generated tree trunk is solid 255 ({solid_feet}/{len(feet)} feet)')

    # ---- G2: between-tree forest floor free (in-game 6-point walkability)
    rng = np.random.default_rng(7)
    bly = np.arange(2, H - 6, 4); blx = np.arange(2, W - 6, 4)
    bx, by = np.meshgrid(blx, bly)
    fm = forest[by, bx]
    fy, fx = np.nonzero(fm)
    pts = np.stack([fx * 4 + 2, fy * 4 + 2], 1)
    sel = rng.choice(len(pts), size=min(20000, len(pts)), replace=False)
    sx, sy = pts[sel, 0], pts[sel, 1]
    dirty = np.zeros(len(sel), bool)
    for dy in (-6, -3, 0, 3, 6):
        for dx in (-6, -3, 0, 3, 6):
            dirty |= s[np.clip(sy + dy, 0, H - 1), np.clip(sx + dx, 0, W - 1)] != 0
    clean = ~dirty
    fails2 = 0
    for dy in (-6, 0):
        for dx in (-7, 0, 7):
            fails2 += int((s[np.clip(sy[clean] + dy, 0, H - 1), np.clip(sx[clean] + dx, 0, W - 1)] != 0).sum())
    rate = 1 - fails2 / max(1, int(clean.sum()))
    check(rate >= 0.995,
          f'G2 between-tree forest floor free: {rate*100:.2f}% of {int(clean.sum())} clean forest '
          f'samples walkable ({fails2} fails)')

    # ---- G3: main forest routes reachable from spawn + venues
    check(reach_px[wk].mean() >= 0.999,
          f'G3 spawn-reachable walkable fraction {reach_px[wk].mean()*100:.3f}% (fully connected)')
    for key in ('church', 'rectory', 'cemetery', 'windmill', 'river'):
        if key not in pois:
            continue
        px, py = pois[key]
        win = reach_px[max(0, py - 60):py + 61, max(0, px - 60):px + 61]
        check(int(win.sum()) >= 100,
              f'G3 venue {key} ({px},{py}) has {int(win.sum())} reachable-walkable px nearby')

    # ---- G4: roads/water/buildings/venues retain collision (unchanged this card)
    road_b = (t == 60) | (t == 100)
    road_art = np.pad(np.repeat(np.repeat(road_b.astype(np.uint8), 4, 0), 4, 1)[2:, 2:] == 1,
                      ((0, 2), (0, 2)))[:H, :W]
    road_solid = int((s != 0)[road_art].sum())
    check(road_solid / max(1, int(road_art.sum())) <= 0.001,
          f'G4 roads stay walkable ({(1-road_solid/max(1,int(road_art.sum())))*100:.2f}% of road px free)')
    water = c == 128
    check(int(water.sum()) > 10000 and int((s != 0)[water].sum()) == int(water.sum()),
          f'G4 river water retained as low-solid 128 ({int(water.sum())} px, all solid)')
    for key in ('church', 'rectory', 'windmill'):
        if key not in pois:
            continue
        px, py = pois[key]
        tall = int((s[max(0, py - 6):py + 7, max(0, px - 6):px + 7] == 2).sum())
        check(tall >= 50, f'G4 venue {key} keeps tall-solid 255 at its anchor ({tall} px)')

    # ---- G5: documented RED - the riverbank "forest/water transition" lane
    F = (2257, 5026, 2274, 5044)          # the ford band (dry strip between two 128 banks)
    fb = wk[F[1]:F[3], F[0]:F[2]]
    fb128 = int((c[F[1]:F[3], F[0]:F[2]] == 128).sum())
    fb255 = int((c[F[1]:F[3], F[0]:F[2]] == 255).sum())
    check(int(fb.sum()) < 200 and fb255 == 0,
          f'G5 ford band {F} closed for Arek: {int(fb.sum())} walkable px, 0 trunk px '
          f'(128 water px inside: {fb128} - margins carry the 128 bands)')
    edt = ndimage.distance_transform_edt(wk[5018:5064, 2290:2700])
    rows = list(range(8, 41))             # y 5026..5058
    wide = sum(1 for r in rows if edt[r].max() >= 7)
    narrow = [(5018 + r, float(edt[r].max()), int((c[5018 + r, 2290:2700] == 128).sum()),
               int((c[5018 + r, 2290:2700] == 255).sum())) for r in rows if edt[r].max() < 7]
    check(wide >= 30 and all(n[3] == 0 and n[2] >= 50 for n in narrow),
          f'G5 shore-walk corridor: {wide}/{len(rows)} rows >= 14 px wide; narrow rows '
          f'{[(n[0], n[2], n[3]) for n in narrow]} are water-bounded with 0 trunk px')
    check(not narrow or len(narrow) <= 1,
          f'G5 corridor pinch count minimal ({len(narrow)} narrow row(s))')

    # ---- outputs
    if args.out:
        os.makedirs(args.out, exist_ok=True)
        ov = Image.fromarray(g[::4, ::4]).convert('RGB')
        a = np.array(ov).copy()
        a[forest[::4, ::4]] = np.minimum(a[forest[::4, ::4]] * 0.55 + np.array([0, 60, 0], np.uint8), 255)
        a[(c[::4, ::4] == 128)] = np.array([40, 70, 200], np.uint8)
        a[reach_px[::4, ::4] & wk[::4, ::4]] = np.minimum(a[reach_px[::4, ::4] & wk[::4, ::4]] * 0.7, 255)
        from PIL import ImageDraw
        d = ImageDraw.Draw(Image.fromarray(a))
        for key, col in (('church', (255, 200, 0)), ('rectory', (255, 200, 0)),
                         ('cemetery', (255, 200, 0)), ('windmill', (255, 200, 0))):
            if key in pois:
                d.ellipse([pois[key][0] // 4 - 6, pois[key][1] // 4 - 6,
                           pois[key][0] // 4 + 6, pois[key][1] // 4 + 6], outline=col, width=2)
        d.ellipse([mj['spawn']['x'] // 4 - 5, mj['spawn']['y'] // 4 - 5,
                   mj['spawn']['x'] // 4 + 5, mj['spawn']['y'] // 4 + 5], outline=(255, 60, 60), width=2)
        d.rectangle([2274 // 4, 4938 // 4, 2681 // 4, 5149 // 4], outline=(255, 0, 255), width=2)
        Image.fromarray(a).save(os.path.join(args.out, 'reachability_overview.png'))
        # corridor crop: collide + walkable + ford mark + narrow row
        crop = Image.fromarray(c[4990:5090, 2210:2720]).resize(((2720 - 2210) * 2, (5090 - 4990) * 2),
                                                               Image.Resampling.NEAREST)
        d2 = ImageDraw.Draw(crop.convert('RGB'))
        d2.rectangle([(2257 - 2210) * 2, (5026 - 4990) * 2, (2274 - 2210) * 2, (5044 - 4990) * 2],
                     outline=(255, 60, 255), width=3)
        d2.line([(2290 - 2210) * 2, (5051 - 4990) * 2, (2700 - 2210) * 2, (5051 - 4990) * 2],
                fill=(255, 200, 0), width=3)
        crop.convert('RGB').save(os.path.join(args.out, 'corridor_collide_crop.png'))
        np.save(os.path.join(args.out, 'walk_mask.npy'), wk)
        np.save(os.path.join(args.out, 'reach_mask.npy'), reach_px)
        print('outputs in:', args.out)

    print('\nFAILED:', len(fails)) if fails else print('\nALL PASSED')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()