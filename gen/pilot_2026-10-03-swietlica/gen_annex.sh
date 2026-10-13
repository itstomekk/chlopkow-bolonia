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
variants=("$@"); [ ${#variants[@]} -eq 0 ] && variants=(v1 v2)
for v in "${variants[@]}"; do "$v" & done
wait
for v in "${variants[@]}"; do echo "$v: $(tail -c 250 "$D/annex_${v}_log.json")"; done
