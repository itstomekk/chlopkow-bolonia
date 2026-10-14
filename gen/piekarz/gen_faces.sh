#!/usr/bin/env bash
# PIEKARZ round 2 (2026-10-12): Tomek liked variant 2 (leather) but hair is darker in reality and the face is not
# similar enough. Four face attempts, all leather outfit, dark brown hair, face crops as likeness refs.
# Usage from project root: bash gen/piekarz/gen_faces.sh [variant ...]
set -u
cd "$(dirname "$0")/../.."
PY=C:/Users/Lenovo/AppData/Local/hermes/hermes-agent/.venv/Scripts/python.exe
R="$(pwd -W)"
P="$R/references/piekarz"
LOOK="PIEKARZ likeness from the photos: dark brown very short hair (clearly dark brown, NOT grey, NOT blond), buzzed short on the sides with the top slightly longer, receding at the temples so the forehead is wide; straight medium-thick dark eyebrows sitting low over slightly deep-set eyes; strong squared jaw and squared chin; moderately high cheekbones; straight nose with a slightly broad rounded tip; wide warm smile; short neatly trimmed dark brown goatee joined to a thin moustache, short stubble along the jaw, cheeks mostly clean; ears flat to the head; stocky build with broad shoulders; late 30s. NO glasses or sunglasses."
OUTFIT="Outfit (keep exactly): black leather biker jacket with stand-up collar and zipped pockets, open over a white crew-neck T-shirt with a small dark-and-red chest print, dark blue jeans, black boots."
RULES="Layout: 4x2 grid, row 1 = walk down A, walk down B, walk right A, walk right B; row 2 = walk up A, walk up B, walk left A, walk left B. Exactly eight isolated complete equal-scale figures with alternating steps. Chunky low-resolution pixel art around 75px content height, 1px dark outline, compact adult proportions with a fairly large head, 2-3 shading steps, 24-32 colours, upper-left light. Pure flat magenta background, no text, no ground, no shadows, no overlapping cells."

run() { # name, prompt, refs...
  local v=$1 prompt=$2; shift 2
  mkdir -p "gen/piekarz/$v"
  local args=(); for r in "$@"; do args+=(--ref "$r"); done
  "$PY" "$R/gen/codex_gen.py" "${args[@]}" --aspect landscape --prompt "$prompt" \
    --out "$R/gen/piekarz/$v/piekarz_walkcycle_raw.png" > "gen/piekarz/$v/gen_log.json" 2>&1
}

face_a() { run walk_face_a "Image 1 is an existing pixel-art walk sheet of PIEKARZ. Keep the layout, poses, body, outfit, pixel size and style exactly. Redraw only the heads in all eight figures so they match the man in the other photos. $LOOK $RULES" \
  "$R/gen/piekarz/walk_leather/piekarz_walkcycle_raw.png" "$P/face_01.png" "$P/face_05.png" "$P/piekarz_01.png"; }
face_b() { run walk_face_b "Image 1 is the layout and style template (4x2 pixel-art walk grid on magenta). Redraw it with the same layout, scale and pixel style, but as PIEKARZ, the man in the photos. $LOOK $OUTFIT $RULES" \
  "$R/gen/bercik/bercik_walkcycle_raw.png" "$P/face_01.png" "$P/face_05.png" "$P/piekarz_01.png"; }
face_c() { run walk_face_c "Image 1 is the layout and style template (4x2 pixel-art walk grid on magenta, note its simple readable pixel face style). Redraw it with the same layout, scale and pixel style, but as PIEKARZ, the man in the photos. $LOOK $OUTFIT $RULES" \
  "$R/gen/kostek/walk/kostek_walkcycle_raw.png" "$P/face_01.png" "$P/face_05.png" "$P/piekarz_01.png"; }
face_d() { run walk_face_d "Image 1 is a photo of PIEKARZ. Turn this exact man into a 4x2 pixel-art walk sheet in the style, layout and scale of the pixel-art template image (image 4). Prioritise his facial likeness. $LOOK $OUTFIT $RULES" \
  "$P/face_01.png" "$P/face_05.png" "$P/piekarz_01.png" "$R/gen/bercik/bercik_walkcycle_raw.png"; }

variants=("$@"); [ ${#variants[@]} -eq 0 ] && variants=(face_a face_b face_c face_d)
for v in "${variants[@]}"; do "$v" & done
wait
for v in "${variants[@]}"; do d="walk_${v}"; echo "$d: $(tail -c 300 "gen/piekarz/$d/gen_log.json")"; done
