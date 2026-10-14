#!/usr/bin/env bash
# MAREK walk sheets (round 1, 2026-10-12). Photos may go to openai-codex (see AGENTS.md).
# Usage from project root: bash gen/marek/gen_walk.sh [variant ...]
set -u
cd "$(dirname "$0")/../.."
PY=C:/Users/Lenovo/AppData/Local/hermes/hermes-agent/.venv/Scripts/python.exe
BASE="Image 1 is the layout and style template: a 4x2 grid of eight chunky low-resolution pixel-art walking figures on a pure magenta background. Redraw the grid with the same layout, order, scale, cell spacing, pixel size and art style, but replace the character with MAREK, the man in the other reference photos (a man from a Polish village). Keep his likeness: broad squarish face with a wide jaw, clean-shaven, short brown hair with some grey at the temples, cropped close on the sides and a little longer on top brushed back, slightly receding hairline, calm steady expression with a slight friendly smile, stocky solid build with a thick neck and broad shoulders, about 50 years old. No glasses. Layout: row 1 = walk down A, walk down B, walk right A, walk right B; row 2 = walk up A, walk up B, walk left A, walk left B. Exactly eight isolated complete equal-scale figures with clear alternating steps, front/back/true side profiles. Chunky pixel art around 75px content height, 1px dark outline, compact adult proportions with a fairly large head like the template, 2-3 shading steps, 24-32 colours, upper-left light. Pure flat magenta background, no text, no ground, no shadows, no checkerboard, no overlapping cells."

declare -A OUTFIT=(
  [walk_tee]="light grey-blue crew-neck T-shirt, dark blue jeans, brown leather belt, grey sneakers (relaxed riverside look)."
  [walk_henley]="dark charcoal long-sleeved henley top with a few brown buttons at the neck, dark brown trousers, brown leather shoes."
  [walk_flannel]="red-and-navy checked flannel shirt with rolled sleeves over a grey T-shirt, olive work trousers, brown work boots."
)

gen() {
  mkdir -p "gen/marek/$1"
  # codex_gen.py chdirs into hermes-agent, so every path must be absolute (native Windows form).
  local R; R="$(pwd -W)"
  "$PY" "$R/gen/codex_gen.py" \
    --ref "$R/gen/bercik/bercik_walkcycle_raw.png" \
    --ref "$R/references/marek/marek_01.png" --ref "$R/references/marek/marek_02.png" \
    --aspect landscape --prompt "$BASE Outfit: ${OUTFIT[$1]}" \
    --out "$R/gen/marek/$1/marek_walkcycle_raw.png" > "gen/marek/$1/gen_log.json" 2>&1
}

variants=("$@"); [ ${#variants[@]} -eq 0 ] && variants=(walk_tee walk_henley walk_flannel)
for v in "${variants[@]}"; do gen "$v" & done
wait
for v in "${variants[@]}"; do echo "$v: $(tail -c 300 "gen/marek/$v/gen_log.json")"; done
