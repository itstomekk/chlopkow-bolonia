# Character Roles and Upcoming Scenarios Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Give every existing character a clear dramatic and gameplay role, then design coherent introductions and short scenarios for the next characters added to Chłopków Bolonia.

**Architecture:** Keep character identity, dialogue, quest state, and gameplay interactions separate. Each character should have a one-page design record before implementation, followed by dialogue, quest/state changes, art requirements, and a focused browser test. Existing save data must remain compatible.

**Tech Stack:** Vanilla JavaScript game logic in `docs/js/game.js`, feature hooks in `docs/js/features.js`, JSON map/item data, generated pixel-art assets, Playwright browser tests.

---

## Current context

The current village roster is defined mainly in `docs/items.json` and `docs/js/game.js`:

| Character | Current identity / working role | Existing gameplay connection |
|---|---|---|
| Arek | Player protagonist and late, curious village boy | Movement, quests, minigames, final tractor reward |
| Frodo | Arek's dog and emotional companion | Follows Arek; Edytka's three-visit quest |
| Kasia | Baker preparing the harvest-festival pie | Collect 10 mushrooms; apples remain a separate collectible economy |
| Marcin | Bus-stop resident waiting for transport | Shop/orangeade quest; loiters near the bus stop |
| Damian | Football player | Lost-cap quest and football minigame context |
| Grandpa Zdzisiek | Windmill keeper and village elder | Unlocks the final tractor-key reward after three completed friend quests |
| Halina / Granny Irenka | Church and family elder presence | Church-related dialogue and indoor church context |
| Sołtys | Village head and secret observer | Hidden outdoor cameo plus indoor church dialogue |
| Michał | Range owner / operator | Shooting-range feature context |
| Kuba | Range-side companion / helper | Shooting-range feature context |
| Mateusz | Existing village resident | Role and scenario still need to be made explicit |
| Patryk | Existing village resident | Role and scenario still need to be made explicit |
| Edytka | Young woman who misses Frodo | Bring Frodo to her exactly three times; Frodo stays about 10 seconds each visit |

The next-character list has not yet been supplied. Do not invent names, biographies, or real-person claims before the user provides it.

## Design rules

1. Give each character one memorable local motivation, one relationship tension, and one useful contribution to the village or the finale.
2. Avoid making every character a fetch-quest giver. Alternate collection, escort, observation, repair, timing, dialogue, and minigame mechanics.
3. Keep local humor about generic village situations unless a depiction of a real person has been explicitly approved.
4. Make character roles geographically legible: the place where a character lives or works should reinforce their identity.
5. Tie scenarios together through shared village events, not disconnected errands.
6. Preserve current quest behavior and old saves while adding new optional scenarios.
7. Write Polish and English dialogue variants together, keeping the existing short pixel-game line style.

---

## Work sequence

### Task 1: Freeze the complete roster

**Objective:** Produce an authoritative roster of existing and planned characters before writing new dialogue.

**Files:**
- Read: `docs/items.json`
- Read: `docs/js/game.js`
- Read: `docs/js/features.js`
- Read: `docs/map.json`
- Create: `docs/characters/roster.md`
- Test: roster consistency script or a small assertion in `test/character_roster_test.py`

**Steps:**
1. Extract every NPC id, display name, sprite index, location, secret flag, and current quest state.
2. Add Arek and Frodo even though they are not ordinary entries in `items.json`.
3. Mark each role as `confirmed`, `working`, or `open`.
4. Add the user-provided upcoming characters only after their names and references arrive.
5. Verify that every non-secret NPC has a render path, dialogue path, and map position or explicit reason for being indoors/hidden.

**Acceptance:** No character exists only as an id or sprite without a documented purpose.

### Task 2: Define a character card for every current character

**Objective:** Turn the roster into usable writing and implementation briefs.

**Files:**
- Create: `docs/characters/cards/<character-id>.md`
- Reference: `docs/js/game.js`, `docs/js/features.js`, `docs/map.json`

**Each card must contain:**
- Name and pronunciation if needed
- Age range and visual anchors, without unnecessary personal claims
- Work, habit, want, fear, and comic contradiction
- Relationship to Arek, Frodo, and at least two other villagers
- Home/work location and map landmark
- Gameplay role and reward, if any
- Intro scene, repeat interaction, completion scene, and post-completion line
- Polish and English dialogue notes
- Art/audio requirements
- Save-state fields and migration impact
- Test cases

**Acceptance:** Mateusz and Patryk have explicit roles, and every existing character has a scenario hook even if their full quest is deferred.

### Task 3: Build the village relationship map

**Objective:** Connect individual scenarios into one coherent village story.

**Files:**
- Create: `docs/characters/relationship-map.md`
- Update after approval: `PLAN.md` or the active roadmap

**Steps:**
1. Map work, family, friendship, rivalry, mentorship, and animal relationships.
2. Identify three to five recurring motifs, such as harvest preparation, transport problems, church life, local sports, and village gossip.
3. Decide which characters form the main optional team around Arek.
4. Identify contradictions that can create scenes without requiring a new quest system.
5. Define how the village reacts after the tractor ending and after Edytka's Frodo quest.

**Acceptance:** Every character has at least one meaningful relationship beyond Arek.

### Task 4: Collect the upcoming-character brief

**Objective:** Turn the user's next-character list into a bounded implementation queue.

**Files:**
- Update: `docs/characters/roster.md`
- Create: `docs/characters/incoming/<character-id>-brief.md`

**Required input for each new character:**
- Name and preferred spelling
- Real, fictional, or fictionalized status
- Reference image or description, if a sprite is needed
- Connection to Chłopków and the existing cast
- Desired tone and boundaries
- Whether the character is a main NPC, cameo, secret, shopkeeper, animal, or quest-only voice

**Acceptance:** Unknown future characters remain explicit placeholders instead of guessed biographies.

### Task 5: Write scenario outlines before implementation

**Objective:** Draft playable scenarios for the approved incoming characters.

**Files:**
- Create: `docs/scenarios/<scenario-id>.md`

**Scenario template:**
1. Cold-open encounter and location
2. Character want and immediate problem
3. Player action and mechanic
4. Complication involving another existing character
5. Resolution and reward
6. Optional repeat dialogue
7. Failure, interruption, and reload behavior
8. Exact quest-state transitions
9. Polish/English line count budget
10. Art, sound, map, and test requirements

**Acceptance:** Each scenario has a beginning, middle, and end that can be implemented without inventing missing requirements.

### Task 6: Implement one vertical slice at a time

**Objective:** Add approved characters without destabilizing the existing game.

**Likely files:**
- Modify: `docs/js/game.js`
- Modify: `docs/js/features.js` when a feature hook is needed
- Modify: `docs/items.json`
- Modify: `docs/map.json`
- Add/regenerate: `docs/img/npcs.png` and sprite metadata when approved
- Add: `test/<character-or-scenario>_test.py`

**TDD loop for each slice:**
1. Add a failing browser assertion for the new NPC, dialogue, quest state, and reachability.
2. Implement the smallest state and interaction path.
3. Add Polish and English text.
4. Add art and map data only after the interaction works.
5. Verify old saves load without silently completing or resetting existing quests.
6. Run the focused test, then the complete regression suite.

**Acceptance:** Each new character is playable, reachable, persistent where necessary, and covered by a focused test.

### Task 7: Run narrative and technical review

**Objective:** Check the roster as a whole before expanding the cast further.

**Checks:**
- No duplicate gameplay roles without a deliberate contrast
- No character is only exposition
- Main optional team has a reason to cooperate
- Dialogue voice is distinct but consistent with the village tone
- No unapproved claims about identifiable real people
- All named locations are present and reachable
- New save fields have migration defaults
- `node --check docs/js/game.js`
- `python -m py_compile test/*.py osm/*.py`
- Focused tests plus `python -u test/run_all.py`

---

## Open questions

1. What is the exact list of upcoming characters?
2. Which of them are real people, fictionalized depictions, or wholly fictional?
3. Should the next arc continue the harvest-festival story, introduce a new village event, or build toward a larger team/finale?
4. Which existing open roles should become full quests first: Mateusz, Patryk, Halina, Michał, or Kuba?
5. Should scenarios remain short optional quests, or should some become a connected chapter with a shared completion condition?

## First handoff request

Provide the upcoming-character list with names and any reference notes. Then fill `docs/characters/roster.md` and create one character card per approved character before changing game code.
