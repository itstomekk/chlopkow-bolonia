#!/usr/bin/env bash
# Świetlica longer with a south annex (gym / siłownia), Tomek 2026-10-13. Edit of the approved pilot raw.
# Usage from project root: bash gen/pilot_2026-10-03-swietlica/gen_annex.sh [v1 v2]
set -u
cd "$(dirname "$0")/../.."
PY=C:/Users/Lenovo/AppData/Local/hermes/hermes-agent/.venv/Scripts/python.exe
R="$(pwd -W)"
D="$R/gen/pilot_2026-10-03-swietlica"
SAT=C:/Users/Lenovo/Hermes/image-gen/2026-10-02-chlopkow-streetview/top_52.26411_22.87549_z19.png
BASE="Image 1 is our approved pixel-art sprite of the village community hall (swietlica), seen in slight top-down 3/4 view from the south, long axis vertical (north-south). Image 2 is the real satellite top view: the hall is the long building right of centre, and at its SOUTH end (bottom) there is a lower, smaller annex with a lighter grey roof (it houses a small gym). Redraw image 1 keeping the main hall exactly as it is (same walls, roof, windows, colours, pixel style, size and camera), but make the whole building somewhat LONGER and add that single-storey annex attached to the SOUTH end, i.e. at the BOTTOM of the sprite, closest to the viewer. The annex is lower than the main roof, a bit narrower, light grey roof, the same beige plaster walls, a plain door and one or two small windows on its visible south wall. The sprite becomes taller than before; the north end stays at the top. Genuine low-resolution game pixel art, chunky square pixels, 1 pixel dark outline, 2-3 step shading lit from the upper left, about 24 flat colours, no anti-aliasing, no text. Plain perfectly flat solid magenta #FF00FF background, no ground, no cast shadow."
run() { # name, extra
  "$PY" "$R/gen/codex_gen.py" --ref "$D/swietlica_raw.png" --ref "$SAT" --aspect portrait \
    --prompt "$BASE $2" --out "$D/annex_$1_raw.png" > "$D/annex_$1_log.json" 2>&1
}
v1() { run v1 "Annex depth about one third of the main hall's length."; }
v2() { run v2 "Annex depth about one quarter of the main hall's length, with a slightly flatter roof."; }
# Round 2 (Tomek): the annex is attached DIRECTLY to the hall (no gap), so it covers the old south entrance;
# the annex has its own entrance with steps on its LEFT (west, road-side) wall.
FIX="Correction to an earlier attempt (image 3 shows it): the annex must be joined DIRECTLY and flush to the south gable of the main hall, with no gap, no separate roof edge floating between them, so it completely covers the hall's old south entrance; the main hall therefore shows NO door on its south end any more. The annex's only entrance is on its LEFT (west) side wall: a door reached by a few small concrete steps (stairs) with a little landing, clearly visible on the left side. The annex south wall has two small windows and no door."
v3() { "$PY" "$R/gen/codex_gen.py" --ref "$D/swietlica_raw.png" --ref "$SAT" --ref "$D/annex_v2_raw.png" --aspect portrait \
    --prompt "$BASE $FIX Annex depth about one third of the main hall's length." --out "$D/annex_v3_raw.png" > "$D/annex_v3_log.json" 2>&1; }
v4() { "$PY" "$R/gen/codex_gen.py" --ref "$D/annex_v2_raw.png" --ref "$SAT" --ref "$D/swietlica_raw.png" --aspect portrait \
    --prompt "Image 1 is our pixel-art community hall with a south annex; images 2-3 are the satellite view and the original hall. Edit image 1 only where needed, keeping its style, colours and size. $FIX Genuine low-resolution game pixel art, chunky square pixels, 1 pixel dark outline, about 24 flat colours, plain flat magenta #FF00FF background, no ground, no shadow, no text." \
    --out "$D/annex_v4_raw.png" > "$D/annex_v4_log.json" 2>&1; }
# v5: v3 kept, side entrance made chunky enough to survive the 43 px game grid.
v5() { "$PY" "$R/gen/codex_gen.py" --ref "$D/annex_v3_raw.png" --ref "$D/swietlica_raw.png" --aspect portrait \
    --prompt "Image 1 is our pixel-art community hall with its south annex. Keep everything exactly the same (hall, annex, roofs, windows, colours, camera, size), and change only the annex's entrance on its LEFT (west) side wall so it stays readable when the sprite is shrunk to about 45 pixels wide: make the door clearly bigger and darker (dark brown, almost as tall as the annex wall), and make the steps chunky: three wide light-grey concrete steps with dark outlines leading down to the left from the door, plus a small landing. No other door anywhere. Keep the old hall entrance hidden behind the annex. Genuine low-resolution pixel art, 1 pixel dark outline, about 24 flat colours, plain flat magenta #FF00FF background, no ground, no shadow, no text." \
    --out "$D/annex_v5_raw.png" > "$D/annex_v5_log.json" 2>&1; }
# v6/v7: in v3-v5 the camera shows the EAST long wall, so a west door is hidden. Turn the view so the WEST wall shows.
TURN="Image 1 is our pixel-art community hall with its south annex, currently seen from the south-east (its right/east long wall is visible). Redraw the SAME building seen from the SOUTH-WEST instead, so its LEFT (west) long side wall, which faces the road, is the visible long wall, lit from the upper left. Keep the dark grey roof, chimney, beige walls, row of white-framed windows (now on the visible left wall), and the lower light-grey-roofed annex joined flush to the south (bottom) end with two small windows on its south wall and no door there. The annex's entrance is on its LEFT (west) wall, now clearly visible: a dark brown door with three light-grey concrete steps and a small landing in front of it, steps going down to the left. No door on the main hall. Same size, slight top-down 3/4 view, long axis vertical. Genuine low-resolution pixel art, chunky pixels, 1 pixel dark outline, about 24 flat colours, plain flat magenta #FF00FF background, no ground, no shadow, no text."
v6() { "$PY" "$R/gen/codex_gen.py" --ref "$D/annex_v5_raw.png" --ref "$SAT" --aspect portrait --prompt "$TURN" \
    --out "$D/annex_v6_raw.png" > "$D/annex_v6_log.json" 2>&1; }
v7() { "$PY" "$R/gen/codex_gen.py" --ref "$D/annex_v3_raw.png" --ref "$D/swietlica_raw.png" --aspect portrait --prompt "$TURN Make the door and steps big enough to stay readable when the sprite is shrunk to about 45 pixels wide." \
    --out "$D/annex_v7_raw.png" > "$D/annex_v7_log.json" 2>&1; }
# Round 3 (Tomek picked v7): add a bit of building on the NORTH end with the bigger main entrance seen on Street View.
SVN="$R/references/swietlica-north-2026-10-13/junction_BDhFlk_yaw92_fov28.jpg"
NORTH="Image 1 is our approved pixel-art community hall (seen from the south-west, south annex at the bottom with its side door and steps). Image 2 is a real Street View photo of the hall's road side: note the slightly projecting entrance block, a bit yellower than the walls, with the main dark brown entrance door. Keep image 1 exactly as it is (hall, roof, windows, south annex, side steps, colours, camera, pixel style) and ADD a small single-storey entrance extension at the NORTH end (top of the sprite): the building gets a little longer northward. This is the hall's main, BIGGER entrance: a wide dark brown double door, a few wide light-grey concrete steps and a small landing in front of it. Genuine low-resolution pixel art, chunky square pixels, 1 pixel dark outline, about 24 flat colours, no anti-aliasing, plain flat magenta #FF00FF background, no ground, no shadow, no text. Make the door and steps big enough to stay readable when the sprite is shrunk to about 45 pixels wide."
n1() { "$PY" "$R/gen/codex_gen.py" --ref "$D/annex_v7_raw.png" --ref "$SVN" --aspect portrait --prompt "$NORTH The extension is a low block joined flush to the north gable, about as wide as the hall and about one fifth of its length, with a slightly lower flat-ish roof; the double door is on its visible LEFT (west, road) wall." \
    --out "$D/north_n1_raw.png" > "$D/north_n1_log.json" 2>&1; }
n2() { "$PY" "$R/gen/codex_gen.py" --ref "$D/annex_v7_raw.png" --ref "$SVN" --aspect portrait --prompt "$NORTH The extension is a narrower porch block (about half the hall's width) projecting from the north gable, with its own small gable roof in the same dark grey; the double door faces north with the steps in front of it, plus a small lamp over the door." \
    --out "$D/north_n2_raw.png" > "$D/north_n2_log.json" 2>&1; }
n3() { "$PY" "$R/gen/codex_gen.py" --ref "$D/annex_v7_raw.png" --ref "$SVN" --aspect portrait --prompt "$NORTH Like the photo: the main hall roof simply continues a bit further north, and at the north-west corner a slightly projecting entrance block, a bit yellower than the walls, sticks out to the LEFT (west, towards the road) holding the double door, with the steps going down to the left." \
    --out "$D/north_n3_raw.png" > "$D/north_n3_log.json" 2>&1; }
# Round 4 (Tomek rejected N1-N3: no extension). Same building one window bay longer at the north end, same roof,
# with a recessed entrance niche (wnęka) holding the door. Outputs annex_r*_raw.png.
LONG="Image 1 is our approved pixel-art community hall, seen from the south-west, with its south annex and left side steps. Image 2 is a real Street View photo of its road side (note the entrance set into the wall). Keep image 1 exactly as it is (roof colour and shape, chimney, walls, windows, south annex with its side steps, colours, camera, lighting, pixel style). Change only this: make the main hall ONE window bay LONGER at its NORTH end (top of the sprite); the same roof and the same walls simply continue, NO added block, NO porch, NO separate roof, nothing sticking out. In that new northern bay, on the visible LEFT (west) long wall, there is a recessed entrance niche cut into the wall: a darker shadowed inset with a dark brown double door inside it and one low step. Make the niche and door chunky enough to stay readable when the sprite is shrunk to about 45 pixels wide. Genuine low-resolution pixel art, chunky square pixels, 1 pixel dark outline, about 24 flat colours, no anti-aliasing, plain flat magenta #FF00FF background, no ground, no shadow, no text."
r1() { "$PY" "$R/gen/codex_gen.py" --ref "$D/annex_v7_raw.png" --ref "$SVN" --aspect portrait --prompt "$LONG" \
    --out "$D/annex_r1_raw.png" > "$D/annex_r1_log.json" 2>&1; }
r2() { "$PY" "$R/gen/codex_gen.py" --ref "$D/annex_v7_raw.png" --ref "$SVN" --aspect portrait --prompt "$LONG Put the niche right at the north-west corner of the hall, so the corner looks cut in." \
    --out "$D/annex_r2_raw.png" > "$D/annex_r2_log.json" 2>&1; }
r3() { "$PY" "$R/gen/codex_gen.py" --ref "$D/annex_v7_raw.png" --ref "$SVN" --aspect portrait --prompt "$LONG Put the niche in the middle of the new bay, with a small wall lamp above it." \
    --out "$D/annex_r3_raw.png" > "$D/annex_r3_log.json" 2>&1; }
# Round 5 (Tomek: "not longer, build it anew, try a few times"): fresh generations, v7 only as style/colour ref.
SV2=C:/Users/Lenovo/Hermes/image-gen/2026-10-02-chlopkow-streetview/landmarks/swietlica_2_d14m_yaw97.jpg
NEW="Images 1-2 are real Street View photos of a Polish village community hall (swietlica), image 3 is the satellite top view (the hall is the long building right of centre), image 4 is our earlier pixel-art sprite of it, use it ONLY for the pixel style, colours and camera. Draw the hall anew as ONE game sprite, seen from the SOUTH-WEST in slight top-down 3/4 view, long axis VERTICAL (north at the top), lit from the upper left. Proportions are the key point: the building is LONG AND NARROW, its whole length (top to bottom) is about FOUR times its width; the visible left (west) long wall carries a row of SIX white-framed windows. One continuous dark grey gable roof with a small chimney. Beige plaster walls. At the SOUTH end (bottom) a lower single-storey annex joined flush, light grey roof, two small windows on its south wall and its own dark brown door with three light-grey concrete steps on its LEFT wall. Near the NORTH end (top) of the left wall, under the same roof (nothing sticking out), a recessed entrance niche: a darker shadowed inset with a dark brown double door and one low step. Make doors and steps chunky so they stay readable when the sprite is shrunk to about 45 pixels wide. Genuine low-resolution pixel art, chunky square pixels, 1 pixel dark outline, about 24 flat colours, no anti-aliasing, plain flat magenta #FF00FF background, no ground, no shadow, no text."
fresh() { "$PY" "$R/gen/codex_gen.py" --ref "$SVN" --ref "$SV2" --ref "$SAT" --ref "$D/annex_v7_raw.png" --aspect portrait --prompt "$NEW $2" \
    --out "$D/annex_$1_raw.png" > "$D/annex_$1_log.json" 2>&1; }
f1() { fresh f1 ""; }
f2() { fresh f2 "Seven windows instead of six, the building even a little longer."; }
f3() { fresh f3 "Keep the roof ridge clearly visible along the whole length."; }
f4() { fresh f4 "The annex is about one fifth of the total length."; }
variants=("$@"); [ ${#variants[@]} -eq 0 ] && variants=(v1 v2)
for v in "${variants[@]}"; do "$v" & done
wait
for v in "${variants[@]}"; do echo "$v: $(tail -c 250 "$D/annex_${v}_log.json")"; done
