# GPT Image prompts: church interior and Sołtys

**Status (2026-09-27):** the interior and the Sołtys are drawn in code (`docs/js/church.js`) because the cloud session
had no Codex/PPQ access. Run these on Tomek's PC to get AI versions, then swap them in (see "Integration" below).

References: Tomek's photos of the church interior and the Sołtys were pasted into the chat on 2026-09-27.
They live only on the local machine. Copy them into `references/` (gitignored) as
`church_front.jpg`, `church_altar.jpg`, `church_nave.jpg`, `church_mary.jpg` and `soltys.jpg`. **Never commit them.**

## 1. Church interior background (top-down 3/4, 320×440 layout)

```
python gen/codex_gen.py --aspect portrait --ref references/church_altar.jpg --ref references/church_nave.jpg --ref references/church_mary.jpg --out gen/church_interior_v1.png --prompt "Top-down 3/4 view pixel-art game room, 16-bit JRPG style matching a cosy Stardew-like village game. Interior of a small white Polish village church, seen from the entrance looking toward the altar. Top: cream apse wall with a Sacred Heart painting (Jesus in red and white) between two white marble columns, two arched stained-glass windows, ochre murals on both sides. Below it: raised marble presbytery with three wide steps, altar with a white lace-edged cloth, four tall gold candles on a stand at left, gold processional cross, grey marble ambo with a carved cross at right, red banner with a bishop's coat of arms, flags. Left front: white marble niche with a Lourdes Mary statue (white robe, blue sash) and flowers. Nave: cream marble tile floor, central red carpet aisle, two blocks of seven light-pine wooden pews, tall leaded windows on the side walls casting light, small Stations of the Cross plaques, wooden confessional near the entrance, open wooden doors at the bottom centre. No people. Clean pixel art, crisp edges, limited palette, no text."
```

## 2. Sołtys sprite (for `img/npcs.png`, same style as Kasia/Marcin/Damian)

```
python gen/codex_gen.py --aspect portrait --ref references/soltys.jpg --ref gen/npc_src/grandpa.png --out gen/npc_src/soltys.png --prompt "Single full-body pixel-art game character, same style and proportions as the second reference image. A Polish village head (sołtys) in his sixties: short grey hair, rectangular glasses, brown pinstripe suit, white shirt, grey tie, holding a round harvest bread on a white lace cloth with green leaves. Front-facing, standing, flat solid magenta #FF00FF background, no shadow, no text."
```

## Integration

The full step-by-step for Hermes is in `gen/HERMES-PROMPT.md`. In short: `python gen/prep_church_sprite.py gen/raw/<name>.png <name>`
writes `docs/img/church/<name>.png`, and the game picks it up automatically. There is no code to change.
