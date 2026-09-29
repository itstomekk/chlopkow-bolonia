# HANDOFF — Character Selection Feature

## Current Status
- Character selector is implemented locally in `docs/js/game.js`; player can choose Arek, Marcin, Damian or Edytka on the title screen. Choice persists in localStorage and only changes appearance.
- New 4-direction sprite sheets are built for Marcin, Damian and Edytka. `gen/build_walk_cycles.py` removes the generated checkerboard only where it connects to the image border, preserving enclosed light pixels. New Zbyszek and Wesołych Świąt portraits are also keyed into the NPC atlas.
- Verification: `node --check docs/js/game.js`, Python compilation, character-selection browser test (including mobile tap and idle/walk rendering), start-flow test, sprite-background regression test, and full local suite all pass. Full suite: **15/15** against `http://127.0.0.1:8765/index.html`.
- These are uncommitted local changes only. Nothing was pushed or deployed. Existing unrelated workspace edits remain untouched.

## Implementation Notes
- Selector uses touch-friendly 2×2 buttons with sprite previews and a selected-state highlight.
- The same button geometry drives drawing and pointer hit-testing, including on mobile.
- All playable sheets load at init so switching updates the preview and active player immediately.
- Sheets are `520x680` (4 directions × 4 animation frames per direction, `130x170` cells); metadata includes `foot: 6`.
- Arek's cemetery no-sunglasses sprite remains available; other characters keep their generated appearance.
- Focused regression tests: `test/character_selection_test.py`, `test/sprite_background_test.py`; both are included in `test/run_all.py`.

## Files touched for this batch
- `docs/js/game.js`
- `gen/build_walk_cycles.py`
- `gen/build_npcs.py`
- `docs/img/npcs.png`
- `docs/img/{marcin,damian,edytka}_sheet.png` and matching JSON metadata
- `test/character_selection_test.py`
- `test/sprite_background_test.py`
- `test/run_all.py`
- `PLAN.md`
- This handoff

## Next step
Review the local character selection in-browser. If approved, commit/publish as a separate gameplay release after fetching and reconciling with current `origin/main`; do not mix in the other pending project edits without review.

### 1. ✅ Generated NPC Sprites (Single Frame)
- **Zbyszek** (Grandpa): 1024x1536px raw → scaled to 130x170px cell
- **Wesołych Świąt** (New character): 1024x1536px raw → scaled to 130x170px cell
- Command: `python gen/codex_gen.py` with GPT Image 2 reference photos
- Build: `python gen/build_npcs.py` → updated docs/img/npcs.png with both NPCs
- **ORDER updated**: `gen/build_npcs.py` line 5 now includes 'zbyszek', 'wesoly_swiat' at indices 9, 10

### 2. ✅ Generated Playable Character Walk-Cycles (4 directions)
- **Marcin** walk-cycle: 4 directions × 2 frames → gen/npc_src/marcin_walkcycle_raw.png (1402x1122)
- **Damian** walk-cycle: 4 directions × 2 frames → gen/npc_src/damian_walkcycle_raw.png (1536x1024)
- **Edytka** walk-cycle: 4 directions × 2 frames → gen/npc_src/edytka_walkcycle_raw.png (1536x1024)
- Command: `python gen/codex_gen.py` with reference photos

### 3. ✅ Built Sprite Sheets from Walk-Cycles
- Created `gen/build_walk_cycles.py`: parses 4x2 grid → 4 direction rows × 4 cells per row (130x170 px)
- Output:
  - `docs/img/marcin_sheet.png` + `docs/img/marcin_sheet.json`
  - `docs/img/damian_sheet.png` + `docs/img/damian_sheet.json`
  - `docs/img/edytka_sheet.png` + `docs/img/edytka_sheet.json`
- JSON format matches arek_sheet.json: `{image, anims: {walk_down, walk_up, walk_left, walk_right}}`

### 4. 📋 Documented Progress
- Updated PROMPTS-characters.md with generation log
- Added references/ folders with character photos (gitignored, never committed)

## What Still Needs To Be Done

### **CRITICAL: Implement Character Selection in game.js**

#### Phase 1: Add Character Selection UI
**Location**: `drawSplash()` function (line 927)
- Add 4 character buttons on title screen:
  - Button 1: Arek (default)
  - Button 2: Marcin
  - Button 3: Damian
  - Button 4: Edytka
- Display as 2×2 grid (or horizontal row) in the title screen
- Show which character is currently selected (highlight/border)
- Save selection to localStorage under key `'arek-chlopkow-character-v1'`

#### Phase 2: Load Selected Sheet on Init
**Location**: `init()` function (line 1114), specifically line 1119
- Instead of hardcoding `load('img/arek_sheet.png')`:
  ```javascript
  const selectedChar = localStorage.getItem('arek-chlopkow-character-v1') || 'arek';
  const sheetName = selectedChar === 'arek' ? 'arek_sheet' : `${selectedChar}_sheet`;
  load(`img/${sheetName}.png`)
  fetch(`img/${sheetName}.json`).then(r => r.json())
  ```
- Also load the noglasses variant: `${sheetName}_noglasses.png` (only exists for arek; others reuse arek's)

#### Phase 3: Update Player State
**Location**: Near `const SPR = { sheet, meta }` (line 1128)
- Store which character is playing: `P.character = selectedChar`
- Use this in HUD/dialogue references if needed (currently game always says "Arek" which is fine)

#### Phase 4: Handle character selection clicks
- Add pointer/click handler on title screen to detect button taps
- Call `selectCharacter('marcin')` / `selectCharacter('damian')` / etc
- Transition from title → play after selection (existing startGame() flow)

### **SECONDARY: Add Entry Points in docs/index.html**
- Load all 4 sheets as preload hints (optional, for faster transition)
- Or keep lazy-load (current approach is fine)

### **TERTIARY: Test All Scenarios**
- Run `python test/run_all.py https://.../index.html` with ?character=marcin, ?character=damian, ?character=edytka
- Verify walk animations in all 4 directions for each character
- Verify cemetery sunglasses work (load arek_sheet_noglasses, ignore for other chars OR create variants)
- Test character selection UI is clickable on mobile (touch targets ≥44×44px)

## Files Involved

### Generated (Ready to Use)
```
docs/img/
  marcin_sheet.png + .json
  damian_sheet.png + .json
  edytka_sheet.png + .json
gen/
  build_walk_cycles.py (new builder script)
  PROMPTS-characters.md (generation log)
references/
  {marcin,damian,edytka,zbyszek,wesoly_swiat}/
    [reference photos, gitignored]
```

### Must Edit
```
docs/js/game.js
  - drawSplash() (add UI)
  - init() (load selected sheet)
  - Add selectCharacter() function
  - Add pointer/click handler for title screen
docs/index.html (optional: preload hints)
```

### Optional Updates
```
test/run_all.py (add character selection test scenario)
HANDOFF.md (this file, update after impl)
```

## Known Limitations / Decisions

- **Cosmetic Only**: All characters have identical gameplay, stats, abilities, and dialogue.
- **Cemetery Sunglasses**: Only Arek has arek_sheet_noglasses.png for cemetery. Other characters will keep their sunglasses (or equivalent - check if they have glasses). If this looks wrong, create noglasses variants for them too.
- **Tile Size**: All sheets use 130×170 px cells (matching Arek). Walk-cycle builder auto-scales to fit.
- **No DLC**: Character sheets are baked into the repo; no dynamic loading from URLs.

## Implementation Order

1. **First**: Add character selection UI in drawSplash() + localStorage save
2. **Second**: Modify init() to load selected sheet dynamically
3. **Third**: Add selectCharacter() click handler
4. **Fourth**: Test with run_all.py
5. **Fifth**: Commit + push to GitHub Pages

## Cost Summary (if you generate more assets)
- **Codex GPT Image 2** (already done):
  - 2 NPC sprites: ~50 secs, model: gpt-image-2-medium
  - 3 walk-cycles: ~54+25+25 = 104 secs, model: gpt-image-2-medium
  - Estimated cost: ~$0.30-0.50 (rough; check Codex invoice)

## Next Steps
1. Assign someone to implement Phase 1-4 in game.js
2. Run tests
3. Merge to main + deploy to GitHub Pages
4. Celebrate! 🎉

---
Documented: 2026-09-28
Character generation: Codex GPT Image 2 (reference-based pixel art)
Status: **Awaiting game.js implementation**
