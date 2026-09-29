# CHŁOPKÓW BOLONIA — asset consistency roadmap

Status: **planning and human selection only**. Approved direction (Tomek, 2026-09-28): refine the existing colorful pixel-art look, not a visual reset. Tomek will identify which existing assets to keep and which to change; **only his approved keepers define the reference style**. No assets have yet been classified in this roadmap. Do not infer that an asset is approved from its current use in the game.

This is a small-step workstream alongside `plans/2026-09-27-chlopkow-bolonia-roadmap.md` (gameplay) and `plans/2026-09-28-map-editor.md` (map editing). It does not supersede either. GPT Luna can own narrow, sequential tasks below; Tomek owns visual decisions, Sol/integrator owns cross-system review and release. No automatic publication, broad map rebuild, or bulk image generation.

## Goal and boundaries

Make future characters, houses, trees, animals, vehicles, landmarks, interiors and UI visually coherent and traceable from the in-game resource back to its build process and safe source references. Keep existing gameplay, coordinates, collision and saves intact unless an individually approved asset requires a specific, tested change. Do not replace every procedural house/tree or build a full asset-manager/editor before a representative pilot proves it necessary.

For the world map and characters, **raster pixel art is the output format** (transparent PNG or a tested lossless alternative; nearest-neighbor display where appropriate). Vector is fine as an authoring source for simple geometry, lettering or UI, but must be rasterized into the approved pixel grid before mixing with world sprites. The splash may use a richer illustrative pixel scale; judge it in context rather than forcing it into the NPC sprite grid.

### Existing pipeline: read before making decisions

- Runtime game and shipped resources: `docs/index.html`, `docs/js/game.js`, `docs/js/world-life.js`, `docs/js/church.js`, `docs/img/`, `docs/map.json`, `docs/items.json`.
- Map renderer: `osm/render_map.py` draws many houses and trees procedurally and composites individual `gen/lm_*.png` landmarks into `docs/img/map_objects.png`; it also emits map layers and collision. `osm/place_items.py` owns item/NPC placement. **Never edit generated `docs/img/map_*.png`, `docs/map.json` or `docs/items.json` by hand.**
- Local editor: `editor/README.md` and `plans/2026-09-28-map-editor.md`. The planned `osm/edits.json` generator integration remains a separate incomplete task; do not assume editor edits already survive a rebuild.
- NPC pipeline: `gen/npc_src/*.png` → `gen/build_npcs.py` → `docs/img/npcs.png`; atlas slot order is coupled to `NPC_IDX` in `docs/js/game.js`. Player and companion sheets use separate builders in `gen/`. Church pieces have `docs/img/church/manifest.json` (loader list, **not** a source/provenance catalogue). Landmark/cemetery prompt notes exist under `gen/`, but coverage is incomplete.
- `references/` holds private photos and is gitignored. `gen/raw/` is also gitignored. Some legacy prompt notes point to chat attachments or sources not retained locally: label those **source unavailable**, not reproducible. `PHOTOS-WANTED.md` is a wish list, not proof that a particular file is present. Prompt notes may be historical, not the final prompt for every shipped image.

## Decision and privacy gates

1. **Human classification first.** Every candidate is `unreviewed` until Tomek marks it `keep (style anchor)`, `keep (compatible, not anchor)`, `adjust`, `regenerate`, or `retire`. Unreviewed is not permission to replace or publish. Record his choices next to stable asset IDs, not just numbers on a contact sheet.
2. **No guessing the style.** A temporary audit can describe measurable properties, but the style guide is drafted only from approved style anchors and accepted by Tomek before generation or code changes. When different anchors disagree, show the conflict and ask rather than averaging them blindly.
3. **Source privacy.** Never commit or publish `references/`, real-person photos, raw photos or composite contact sheets containing those photos. The public asset catalogue may hold IDs, safe source descriptions, prompts, generated outputs, transformation recipes and licence/permission notes. A local-only mapping from source ID to private filename must stay gitignored. A finished, non-identifying sprite can be versioned after visual/privacy/licence review. Do not send photos of people to PPQ or other public-URL image services; check the chosen generation path and permissions before using any private reference. Confirm cost/quota before any paid generation, report per-image and total cost or explicitly unknown.
4. **No repo side effects without request.** Do not commit, push or deploy unless Tomek explicitly asks. This worktree is shared and currently has unrelated edits; check `git status` and diffs before every task, preserve them, and serialize any render that overwrites generated map files.

## Small tasks for GPT Luna (one bounded handoff per task)

### A0 — Audit and review sheet (first task; no art or game edits)

- [ ] Inspect the *current* tree and `git status`. Inventory only assets actually loaded/drawn by the game, plus their build inputs where traceable. Group into player/NPC, animals/vehicles, houses/trees/landmarks, terrain/map layers, church/memories, splash/UI. Mark `procedural`, `source image`, `packed atlas`, or `shipped file`. Note whether each is part of live or only local/uncommitted changes; do not infer live deployment from filenames.
- [ ] Prepare a local review sheet (thumbnail/contact sheets of **shipped/generated game images only**) with stable IDs, category, actual use, in-game scale/context and `unreviewed` labels. Split oversized map images into safe crops around representative procedural houses/trees. Never put private photos on this sheet.
- [ ] Make a human-readable source map: asset ID → output path → builder/input path or procedural function → game reference(s) → source status (`local private ref`, `public source`, `missing`, `none/algorithmic`, `unknown`). Do not put sensitive local filenames or images in any publishable file. If a link cannot be verified, mark `unknown`.
- [ ] Present Tomek the sheet and collect keep/adjust/regenerate/retire choices; record **his** answers. Stop here until he classifies a useful cross-section including at least one character, one building, one tree and one map/background element. No style anchors are preselected.
- Acceptance: all claims in the sheet have a code/file path; review images reveal no private photos; no `docs/`, `osm/` or generated outputs changed; no invented classifications.

### A1 — Style guide from approved keepers (after A0 and Tomek's choices)

- [ ] Draft an English `plans/asset-style-guide.md` that names the approved anchor IDs and shows them at actual gameplay scale beside map/character context. The document separates **required** rules from category-specific differences (world sprites versus UI/splash/illustrations).
- [ ] Derive rules from the selected anchors: camera/perspective, outline and silhouette, light/shadow direction, pixel-cluster/detail density, palette and contrast, alpha/background, baseline/ground contact, relative scale and animation frame consistency. Record concrete examples and an avoid-list for common AI artefacts (blurred scaling, inconsistent perspective, malformed text/limbs, magenta halos). Do not invent numerical pixel sizes, palette limits or a universal shadow if anchors do not support them; bring proposed measurements to Tomek for approval.
- [ ] Include a standard generation handoff: approved anchor images (not private reference photos), asset purpose and viewed size, prompts/negative constraints, raw-to-final preprocessing, visual review in real gameplay at desktop/mobile size. Add a brief source/rights and cost field to each asset's record.
- [ ] Ask Tomek to approve the guide and resolve conflicting anchors before treating it as normative.
- Acceptance: every normative rule points to an approved visual example; a new asset can be judged against a repeatable side-by-side QA sheet; no game/runtime changes.

### A2 — One-house/one-tree pilot (after A1; separate tiny worker tasks)

- [ ] Pick **one** user-marked house and **one** user-marked tree or tree family. Trace their exact renderer path and placement/collision before changing anything. Decide with Sol whether a procedural palette/shape change or a sprite substitution is the smallest safe solution. Do not replace all houses or all trees.
- [ ] Make a local candidate for **one asset at a time**. Preserve the source/output mapping and any unchanged reference; do not overwrite a keeper or modify unrelated atlas cells. Compare candidate versus old art in place and in a review sheet; Tomek approves or rejects each candidate before adoption.
- [ ] For a proposed game integration, run a baseline first, add a focused test for placement/sort/scale/collision as applicable, rebuild only under exclusive map ownership, then verify unchanged landmarks, walking access and asset readability on desktop/mobile. Stop if the existing uncommitted map work cannot be isolated; coordinate with its owner instead of overwriting it. For source that cannot be recreated (lost chat reference), mark the gap and request a new reference or use an approved anchor, never claim exact recreation.
- Acceptance: old and new previews are available, Tomek explicitly approves the visual change, source mapping and regeneration recipe are recorded, no regression in relevant tests. **A preview is not a published change.**

### A3 — Expand one category at a time (only after pilot is approved)

- [ ] Prioritize the most visually frequent mismatches Tomek marked. Tackle e.g. houses/trees, characters/animals, landmarks/vehicles, interiors, UI/splash as separate batches; actual order comes from the review sheet. Each batch has IDs, a max scope chosen before work, baseline, representative side-by-side, approval and regression gate.
- [ ] For procedural repeated scenery, prefer a small set of approved variants over one unique sprite per OSM object. Keep deterministic selection so a rerender does not randomly change the village. Keep edits in source/generator data, not manually on baked map PNGs.
- [ ] For NPC/player atlases, preserve slot and frame order, transparency, saved NPC IDs and collision/hitboxes unless separately specified. For maps, preserve OSM anchors/geographic placement and existing save behavior. Record any deviation explicitly and test it.
- [ ] After each approved batch, update catalogue and style-guide exceptions, run relevant focused tests and `python test/run_all.py` on a local HTTP server if game output changed; report the actual pass/fail baseline and any visual/browser checks. Publication needs a separate request and release gate.

### A4 — Asset library/editor integration only if needed

- [ ] After repeated approved replacements, assess whether asset IDs and a selector in `editor/` would remove genuine work. If yes, design stable ID → resource/procedural recipe → placement mapping with versioning and migration, in coordination with the unfinished editor generator hooks. Do not start this task from A0 by default.
- Acceptance: a specific recurring manual step and expected gain are documented before implementing a new catalogue UI or runtime loader.

## Per-task worker handoff template

> Project: `C:\Users\Lenovo\Hermes\projects\games\arek-w-chlopkowie` (`chlopkow-bolonia`). Read `AGENTS.md`, `PLAN.md`, `HANDOFF.md`, this roadmap, `DEVELOPMENT.md`, relevant generator and actual game usage. Own only task [A0/A1/A2/approved A3 batch] and name exact files before writing. Check `git status` and preserve all pre-existing changes. No commit/push/deploy, no bulk regeneration, no private-photo publication or paid image generation without explicit permission. Work in small testable increments; show Tomek reviewable visual outputs at the human gates. Return changed paths, evidence/tests actually run, costs if any, blocked decisions and the next *single* task. Stop rather than guess style anchors or overwrite shared map output.

## Current next action

**A0 only:** Luna inventories current game-used art and prepares a safe visual review sheet. Tomek then labels keepers and mismatches; A1 and any image generation must wait for those choices. No asset migration or editor architecture is authorized by this plan alone.
