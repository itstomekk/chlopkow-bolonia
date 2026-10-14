# Minigame design direction (Tomek voice note, 2026-10-11)

Status: SAVED FOR LATER. Not scheduled, nothing to build now. Keep in mind when designing or changing any minigame.

## Core idea
- The open world is the frame: people wander, do small quests and visit places.
- The entertainment is in the places themselves: the minigames (shooting gallery, running/race, catching the pig, dogs, and the rest).
- So each minigame must be fun on its own, as a reason to visit a place just to play.

## Pillars
1. **Local play and friendly competition.** People can play on the same computer and compete with friends.
2. **High scores everywhere.** Every game keeps scores. Already partly there as local records (race ghost, medals).
3. **Global leaderboard (future).** Scores saved globally, so even a solo player without local friends competes against the global history of results. Needs a backend or a Nostr-based store (see `plans/2026-10-04-multiplayer.md` and `docs/js/local-competition.js`). Open questions: anti-cheat, name display, per-game boards, reset policy.
4. **One CPU opponent per game.** Each minigame gets one computer-steered NPC. Its result is always the average of past results (global history once it exists, local history until then). It works as a benchmark: beat the average, beat the CPU.

## Design implications to keep in mind
- Every minigame should expose a single comparable score (time, points, count) and a way to record it.
- CPU result = rolling average of past results; with no history, use a sensible default per game.
- Keep the score and CPU hooks generic, not per-game hacks, when a minigame is touched.

## Source
Tomek, Telegram voice note, Arek w Chlopkowie topic, 2026-10-11 (1:40). Transcribed locally (faster-whisper), paraphrased here.

## Standing instruction: be Tomek's game coach
Tomek (voice note, 2026-10-11): throughout this project, proactively recommend things. Act as a coach and think about what is playable, what speaks to the lore, and what people would actually like to play, including what could go viral. Practical reading: when finishing or planning work, add short, concrete suggestions (a minigame twist, a lore hook, a shareable moment, a score or CPU-rival idea) instead of only executing. Keep them brief and clearly marked as suggestions, not changes.
