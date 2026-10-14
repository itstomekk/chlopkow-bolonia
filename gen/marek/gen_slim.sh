#!/usr/bin/env bash
# MAREK round 2 (2026-10-12): Tomek picked variant 1 (walk_tee), a bit slimmer and a bit shorter than BERCIK.
# Two img2img edits of the walk_tee raw with different slimming strength; height is set in the build step.
# Usage from project root: bash gen/marek/gen_slim.sh [variant ...]
set -u
cd "$(dirname "$0")/../.."
PY=C:/Users/Lenovo/AppData/Local/hermes/hermes-agent/.venv/Scripts/python.exe
R="$(pwd -W)"
KEEP="Image 1 is an existing 4x2 pixel-art walk sheet of MAREK on magenta. Keep everything else exactly the same: layout and order of the eight figures, poses, alternating steps, head, face, hair, clean-shaven look, outfit (light grey-blue T-shirt, dark blue jeans, brown belt, grey sneakers), colours, 1px dark outline, pixel size and art style. The other images are photos of MAREK for likeness only. Pure flat magenta background, no text, no ground, no shadows, no overlapping cells."
declare -A EDIT=(
  [walk_tee_slim]="Change only his body: make him a little slimmer, a normal medium build instead of stocky; slightly narrower shoulders and torso, smaller belly, slightly thinner arms and legs."
  [walk_tee_slimmer]="Change only his body: make him clearly slimmer, a lean build; noticeably narrower shoulders, flat stomach, thinner arms, neck and legs, while keeping the same head."
)
gen() {
  mkdir -p "gen/marek/$1"
  "$PY" "$R/gen/codex_gen.py" --ref "$R/gen/marek/walk_tee/marek_walkcycle_raw.png" \
    --ref "$R/references/marek/marek_01.png" --ref "$R/references/marek/marek_02.png" \
    --aspect landscape --prompt "$KEEP ${EDIT[$1]}" \
    --out "$R/gen/marek/$1/marek_walkcycle_raw.png" > "gen/marek/$1/gen_log.json" 2>&1
}
# Pass 2: walk_tee (and so both slim edits) drew denim shorts in the front/back frames but long jeans in the
# side frames. `bash gen/marek/gen_slim.sh --jeans` edits each slim raw in place (originals kept as *_shorts.png).
jeans() {
  local raw="gen/marek/$1/marek_walkcycle_raw.png"
  [ -f "gen/marek/$1/marek_walkcycle_raw_shorts.png" ] || cp "$raw" "gen/marek/$1/marek_walkcycle_raw_shorts.png"
  "$PY" "$R/gen/codex_gen.py" --ref "$R/gen/marek/$1/marek_walkcycle_raw_shorts.png" \
    --aspect landscape --prompt "Image 1 is a 4x2 pixel-art walk sheet on magenta. Keep everything exactly the same (layout, poses, body, head, face, hair, T-shirt, belt, shoes, colours, outline, pixel size) except one fix: in ALL eight figures he wears full-length dark blue jeans reaching down to the shoes, with no bare knees or shins. The front and back figures currently show shorts; change them to the same long jeans as the side figures. Pure flat magenta background, no text." \
    --out "$R/$raw" > "gen/marek/$1/gen_log_jeans.json" 2>&1
}
if [ "${1:-}" = "--jeans" ]; then
  for v in walk_tee_slim walk_tee_slimmer; do jeans "$v" & done
  wait
  for v in walk_tee_slim walk_tee_slimmer; do echo "$v: $(tail -c 300 "gen/marek/$v/gen_log_jeans.json")"; done
  exit 0
fi
variants=("$@"); [ ${#variants[@]} -eq 0 ] && variants=(walk_tee_slim walk_tee_slimmer)
for v in "${variants[@]}"; do gen "$v" & done
wait
for v in "${variants[@]}"; do echo "$v: $(tail -c 300 "gen/marek/$v/gen_log.json")"; done
