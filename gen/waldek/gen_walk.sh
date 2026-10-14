#!/usr/bin/env bash
# WALDEK round 1 (2026-10-13): head of the Sestrada, slim and tall, black hair (not grey), navy blazer,
# vivid blue shirt, microphone in hand. Same flow as PIEKARZ face D (photo first, BERCIK walk raw as
# layout/style/scale template). Variants differ only in the hairstyle.
# Usage from project root: bash gen/waldek/gen_walk.sh [variant ...]
set -u
cd "$(dirname "$0")/../.."
PY=C:/Users/Lenovo/AppData/Local/hermes/hermes-agent/.venv/Scripts/python.exe
R="$(pwd -W)"
P="$R/references/waldek"
LOOK="WALDEK likeness from the photos: friendly man in his 50s, rounded-oval face with a high smooth forehead, thin rectangular glasses with thin dark metal frames, dark eyebrows, straight nose with a slightly rounded tip, broad warm open smile showing upper teeth, light skin with warm ruddy cheeks, clean-shaven, ears visible. BUILD (owner correction, overrides the photos): clearly SLIM and TALL, narrow shoulders, long legs, no belly."
OUTFIT="Outfit (keep exactly): tailored dark navy blazer worn open over a vivid saturated electric-blue collared shirt with no tie, dark charcoal trousers, black shoes. He is the head of the village Sestrada: a simple black handheld microphone in his right hand, held at chest height in every frame (partly hidden by the body in the walk-up frames)."
RULES="Layout: 4x2 grid, row 1 = walk down A, walk down B, walk right A, walk right B; row 2 = walk up A, walk up B, walk left A, walk left B. Exactly eight isolated complete equal-scale figures with alternating steps. Chunky low-resolution pixel art around 75px content height, 1px dark outline, compact adult proportions with a fairly large head, 2-3 shading steps, 24-32 colours, upper-left light. Pure flat magenta background, no text, no ground, no shadows, no overlapping cells."
TPL="$R/gen/bercik/bercik_walkcycle_raw.png"

run() { # name, hair
  local v=$1 hair=$2
  mkdir -p "gen/waldek/$v"
  "$PY" "$R/gen/codex_gen.py" --ref "$P/waldek_02.png" --ref "$P/waldek_01.png" --ref "$P/waldek_04.png" --ref "$TPL" \
    --aspect landscape \
    --prompt "Image 1 is a photo of WALDEK (images 2 and 3 are the same man). Turn this exact man into a 4x2 pixel-art walk sheet in the style, layout and scale of the pixel-art template image (image 4). Prioritise his facial likeness. Ignore all text, logos and graphics in the photos. $LOOK HAIR: $hair $OUTFIT $RULES" \
    --out "$R/gen/waldek/$v/waldek_walkcycle_raw.png" > "gen/waldek/$v/gen_log.json" 2>&1
}

hair_a() { run walk_hair_a "same hairline as in the photos (bald smooth crown, short hair only on the sides and back), but that side hair is BLACK, not grey."; }
hair_b() { run walk_hair_b "short full BLACK hair, neatly cut, slightly receding at the temples, not grey."; }
hair_c() { run walk_hair_c "short BLACK hair with a neat side part and a little volume on top, smart presenter look, not grey."; }

variants=("$@"); [ ${#variants[@]} -eq 0 ] && variants=(hair_a hair_b hair_c)
for v in "${variants[@]}"; do "$v" & done
wait
for v in "${variants[@]}"; do d="walk_${v}"; echo "$d: $(tail -c 300 "gen/waldek/$d/gen_log.json")"; done
