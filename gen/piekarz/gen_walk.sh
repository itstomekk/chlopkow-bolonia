#!/usr/bin/env bash
# PIEKARZ walk sheets (round 1, 2026-10-12). Photos may go to openai-codex (Tomek's OK, see AGENTS.md).
# Usage from project root: bash gen/piekarz/gen_walk.sh [variant ...]
set -u
cd "$(dirname "$0")/../.."
PY=C:/Users/Lenovo/AppData/Local/hermes/hermes-agent/.venv/Scripts/python.exe
BASE="Image 1 is the layout and style template: a 4x2 grid of eight chunky low-resolution pixel-art walking figures on a pure magenta background. Redraw the grid with the same layout, order, scale, cell spacing, pixel size and art style, but replace the character with PIEKARZ, the man in the other reference photos (a long-haul truck driver from a Polish village). Keep his likeness: broad roundish-square face, strong jaw, very short light-brown buzz cut slightly longer on top with slightly receding temples, short neatly trimmed light-brown stubble beard and goatee, friendly wide smile, stocky solid build with broad shoulders and thick forearms, late 30s. NO glasses and NO sunglasses at all, eyes clearly visible. Layout: row 1 = walk down A, walk down B, walk right A, walk right B; row 2 = walk up A, walk up B, walk left A, walk left B. Exactly eight isolated complete equal-scale figures with clear alternating steps, front/back/true side profiles. Chunky pixel art around 75px content height, 1px dark outline, compact adult proportions with a fairly large head like the template, 2-3 shading steps, 24-32 colours, upper-left light. Pure flat magenta background, no text, no ground, no shadows, no checkerboard, no overlapping cells."

declare -A OUTFIT=(
  [walk_polo]="white short-sleeved polo shirt with navy collar and cuff trim and a small round chest logo, thin gold chain necklace, silver wristwatch, dark navy work trousers, black work shoes (his trucker outfit)."
  [walk_leather]="black leather biker jacket with stand-up collar and zipped pockets, open over a white crew-neck T-shirt with a small dark-and-red chest print, dark blue jeans, black boots."
  [walk_tee]="black short-sleeved crew-neck T-shirt with a small red-and-white chest logo, olive-khaki cargo trousers, silver wristwatch, thin silver chain, brown work boots."
)

gen() {
  mkdir -p "gen/piekarz/$1"
  # codex_gen.py chdirs into hermes-agent, so every path must be absolute (native Windows form).
  local R; R="$(pwd -W)"
  "$PY" "$R/gen/codex_gen.py" \
    --ref "$R/gen/bercik/bercik_walkcycle_raw.png" \
    --ref "$R/references/piekarz/piekarz_01.png" --ref "$R/references/piekarz/piekarz_05.png" \
    --ref "$R/references/piekarz/piekarz_03.png" --ref "$R/references/piekarz/piekarz_02.png" \
    --aspect landscape --prompt "$BASE Outfit: ${OUTFIT[$1]}" \
    --out "$R/gen/piekarz/$1/piekarz_walkcycle_raw.png" > "gen/piekarz/$1/gen_log.json" 2>&1
}

variants=("$@"); [ ${#variants[@]} -eq 0 ] && variants=(walk_polo walk_leather walk_tee)
for v in "${variants[@]}"; do gen "$v" & done
wait
for v in "${variants[@]}"; do echo "$v: $(tail -c 300 "gen/piekarz/$v/gen_log.json")"; done
