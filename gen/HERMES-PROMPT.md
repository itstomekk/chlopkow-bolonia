# Prompt for Hermes: generate the church art for "Arek w Chłopkowie"

Copy everything below the line into Hermes.

---

You are working on Tomek's browser game **Arek w Chłopkowie**, a top-down pixel-art adventure set in the real village of Chłopków.
Your job: generate AI pixel-art sprites for the **church interior** and the **Sołtys** (village head) with GPT Image,
drop them into the game, check them in the browser, and deploy.

## 0. Where things are
- Project folder: `C:\Users\Lenovo\Hermes\projects\games\arek-w-chlopkowie\`
- Repo: https://github.com/itstomekk/arek-w-chlopkowie. The work is on branch **`claude/determined-mccarthy-b9096e`**, which is not merged yet.
- Live game: https://itstomekk.github.io/arek-w-chlopkowie/. GitHub Pages serves `main:/docs`, so every push to `main` redeploys.
- Read `HANDOFF.md` first, then `gen/PROMPTS-church.md`.

```
cd C:\Users\Lenovo\Hermes\projects\games\arek-w-chlopkowie
git fetch origin
git checkout claude/determined-mccarthy-b9096e
git pull
```

## 1. Reference photos (never commit them)
Tomek sent these photos in chat. Save them into `references\` (gitignored). **Never `git add` that folder.**
If a file is missing, ask Tomek for it.

| File | Shows |
|---|---|
| `references\church_front.jpg` | white church facade, tower, arched door, steps, red paving |
| `references\church_altar.jpg` | altar with white lace cloth, 4 gold candles, Sacred Heart painting, stained glass, murals, marble ambo, red bishop banner |
| `references\church_mary.jpg` | Lourdes Mary in a marble niche, flowers, a harvest wreath, big leaded window, pews, flags |
| `references\church_nave.jpg` | light-pine pews, big arched leaded window, Stations of the Cross plaques, wooden confessional |
| `references\church_100.jpg` | altar and marble ambo from the side, the gold "100" in flowers (100 years of the parish) |
| `references\soltys.jpg` | the Sołtys: grey hair, glasses, brown pinstripe suit, grey tie, holding the harvest bread on a lace cloth (he agreed to be in the game) |

## 2. How to generate
- **First choice: Codex GPT Image.** Local reference files are sent directly and nothing gets uploaded publicly:
  `C:/Users/Lenovo/AppData/Local/hermes/hermes-agent/.venv/Scripts/python.exe gen/codex_gen.py --ref <ref> [--ref <ref2>] --aspect square --prompt "<prompt>" --out gen/raw/<name>.png`
- If Codex returns HTTP 429 (quota), wait and retry later. If the login has expired, re-authenticate Codex in Hermes the usual way.
- **Fallback: PPQ** (`gen/ppq_gen.py`, about $0.0115/image). Use it **only for objects**, with text prompts or the style reference `gen/lm_church.png`.
  **Never send photos of people through PPQ**: not `soltys.jpg`, and not photos with parishioners in them.
- Always add the style reference **`gen/lm_church.png`**, the existing church sprite. The new art must match it.
- Every object prompt starts with this style line:
  `Pixel-art game sprite in the exact style of the reference church sprite: crisp 16-bit pixels, clean dark outlines, soft shading, top-down 3/4 view from slightly above and in front. Single object, centred, flat solid magenta #FF00FF background, no shadow on the background, no text, no people.`
- Save raw outputs to `gen\raw\` (gitignored). Only the processed files go into the game.

## 3. What to generate (13 files)
Each piece has a fixed box in the room (width × height in game pixels). Generate roughly that shape.
The game fits the sprite into the box: it keeps the aspect, centres it and stands it on the bottom edge.

| name | box | aspect | Describe | Refs |
|---|---|---|---|---|
| `backwall` | 320×104 | landscape, **no magenta**, fill the frame | Front wall of the apse seen straight on: cream plaster; Sacred Heart painting (Jesus in red and white, blue sky, green ground) in a gold frame in the centre, between two white marble columns; one arched stained-glass window each side; ochre murals of saints at far left and right. Flat wall, no floor. | altar, 100 |
| `altar` | 68×45 | wide | Stone altar table with a white cloth and a wide lace hem, a small gold tabernacle/crucifix on top | altar, 100 |
| `candles` | 24×48 | tall | Four tall gold candle pillars with crosses, lit, on a gold stand with a single leg | altar |
| `cross` | 12×63 | very tall | Gold processional cross on a thin pole | altar |
| `ambo` | 34×45 | square-ish | Grey marble lectern (ambo) with a carved cross and a red book on top | 100 |
| `banner` | 28×44 | tall | Red banner on a wooden pole with a bishop's coat of arms (white shield, green hat) | altar |
| `mary` | 48×53 | square | White marble niche with the Lourdes Madonna statue (white robe, blue sash), flowers and a harvest wreath at her feet | mary |
| `flags` | 20×70 | very tall | Three parish flags on gold-tipped poles (red, white, blue-and-gold) | mary |
| `flowers100` | 52×32 | wide | Big flower arrangement (red, pink, white lilies, gerberas, greenery) with a golden "100" in the middle | 100 |
| `pew` | 120×20 | **very wide, 6:1** | ONE light-pine church pew seen **from behind and slightly above**: backrest, seat edge, carved end panels | nave |
| `confessional` | 36×39 | square | Wooden confessional booth with a small gold cross | nave |
| `font` | 14×17 | small | Small marble holy-water font on a pedestal | none |
| `soltys` | 28×44 | tall | **Character**, not an object: full-body, front-facing, same proportions as `gen/npc_src/grandpa.png`. Man in his sixties: short grey hair, rectangular glasses, brown pinstripe suit, white shirt, grey tie, holding a round harvest bread on a white lace cloth with green leaves | soltys + `gen/npc_src/grandpa.png` (**Codex only**) |

## 4. Put them in the game
For each raw image:
```
python gen/prep_church_sprite.py gen/raw/<name>.png <name>
```
This keys out the magenta, crops the image, limits its size and saves `docs/img/church/<name>.png`.
The game loads every file in `docs/img/church/` automatically. A missing file keeps the hand-drawn version, so partial progress is safe.
There is **no code to change**.

## 5. Check it
```
python -m http.server 8765 --directory docs
```
1. Open http://localhost:8765/, press Enter, and walk to the church (the white church in the south-east; press M for the map). Press **E** at the door to go in.
2. Check: nothing floats or sinks into the floor, pews line up in two neat blocks, Arek walks *behind* pews and the altar,
   the Sołtys stands by the ambo and talks, and the "100" is readable. Walk out through the bottom door.
3. Run the tests. Each must end with `errors []`:
   `python test/church_test.py`, `python test/quest_test.py`, `python test/jump_test.py 1662 1747`
4. Check the screenshots `test/c2_aisle.png` and `test/c3_soltys.png`. Regenerate any piece that looks wrong:
   wrong perspective, text or watermark artifacts, a leftover magenta fringe, or a style that clashes with the church sprite.
   If a piece's shape really needs a different box, edit its entry in `CHURCH_PIECES` at the top of `docs/js/church.js`
   (and its `put()`/`block()` lines further down). If you do that, also update `BOX` in `gen/prep_church_sprite.py`.

## 6. Deploy
```
git status                      # references/ and gen/raw/ must NOT appear
git add docs/img/church HANDOFF.md      # includes manifest.json
git commit -m "Church interior and Sołtys: GPT pixel-art sprites"
git push origin claude/determined-mccarthy-b9096e
git checkout main
git pull
git merge --no-ff claude/determined-mccarthy-b9096e
git push origin main
```
Wait 1–2 minutes, then open https://itstomekk.github.io/arek-w-chlopkowie/ (hard refresh). Enter the church and confirm the new art is live.
Also try `?lang=en`.

## 7. Close out
- Update `HANDOFF.md`: which pieces are AI-made, which are still hand-drawn, cost per image, and any problems.
- Log image costs as usual in `C:\Users\Lenovo\AppData\Local\hermes\telemetry\image-gen-costs.jsonl`.
- Send Tomek two screenshots (the altar end and the nave) and the live link.
