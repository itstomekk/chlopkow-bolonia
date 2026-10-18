#!/usr/bin/env bash
# WAJPER round 2 (Tomek 2026-10-17): Skye-terrier look, cool SILVER lights (not cream), shaggier, fringe sometimes over
# the eyes and sometimes parted, more hair motion between frames, slightly smaller than Frodo (done in build).
# Every animation is one row of one sheet (no cross-sheet frames -> no zoom jumps), and row 1 of every pose sheet
# starts with a STANDING SIDE ANCHOR used by build_wajper.py to put every sheet on one scale.
# Image 1 = Frodo raw sheet (layout/pixel template only), Images 2+ = photos of the real dog.
# Run from anywhere: bash gen/wajper/gen_wajper.sh [walk idle yawn fun dig run sleep portrait]
# Round 1 (cream colours, cross-sheet anims): gen_wajper_r1.sh / build_wajper_r1.py, raws in raw/, output out_r1/.
set -u
cd "$(dirname "$0")/../.."
PY=C:/Users/Lenovo/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe
ROOT=$(pwd -W 2>/dev/null || pwd)
OUT=$ROOT/gen/wajper/${RAWDIR:-raw2}
mkdir -p "$OUT"
FRODO=$ROOT/gen/frodo_sheet_raw.png
R=$ROOT/references/wajper
PHOTOS=(--ref "$R/wajper_01.png" --ref "$R/wajper_08.png" --ref "$R/wajper_06.png" --ref "$R/wajper_04.png" --ref "$R/wajper_12.png")

DOG="WAJPER: a small shaggy Skye-terrier-type village dog. Long LOW body, very short legs, about 30 cm tall. \
Very long, shaggy, messy, wavy coat that parts along the spine and hangs down both sides almost to the ground, hiding the legs to mid-shin; \
long scruffy veil of hair on the head and a big beard. COLOURS ARE COOL, NOT WARM: the light hair is SILVER-WHITE and pale blue-grey \
(no cream, no yellow, no beige, no tan); head, beard, chest and leg fringes silver-white; long drop ears with dark charcoal-grey hair; \
dark charcoal / slate-grey saddle over the back and flanks with silver grizzled tips; only the paws slightly greyish-fawn. \
Black nose. Plumed tail curled up over the back, charcoal at the base with a silver-white tip. No collar."

STYLE="Chunky retro pixel art like Image 1: same big pixel blocks, bold 1-pixel near-black outline around the whole silhouette, \
flat limited palette (~20 colours) with strong contrast between the dark saddle and the silver hair so it reads clearly at small size; \
show the long hair as a few chunky strands/locks, not noise. Same top-down 3/4 game camera as Image 1. \
Image 1 is ONLY a template for grid, pixel size and outline: do NOT copy Frodo's black-and-tan colours, pointed ears, red collar. \
The other images are photos of the real dog: copy his shaggy coat, silver/charcoal colours, drop ears, beard and curled plume tail. \
Draw the SAME dog at the SAME scale in every cell. Flat solid magenta #FF00FF background, no shadows, no ground, no text, no grid lines. \
Every figure separate, fully inside its cell, not touching neighbours."

ANCHOR="Row 1 starts with an extra cell: the dog STANDING still in side profile facing right (size reference)."
HAIR="Hair motion: in consecutive frames the long coat locks, ears, beard and tail plume visibly swing and bounce (lag behind the movement)."

gen() { local name=$1 aspect=$2 prompt=$3; shift 3
  "$PY" "$ROOT/gen/codex_gen.py" --ref "$FRODO" "$@" "${PHOTOS[@]}" --aspect "$aspect" --out "$OUT/$name.png" --prompt "$prompt" > "$OUT/$name.log" 2>&1
  echo "$name: $(tail -1 "$OUT/$name.log")"; }

walk() { gen walk square "Sprite sheet, 4 rows x 4 columns, walk cycle of $DOG $STYLE $HAIR \
Row 1 walking toward the viewer (front view), row 2 walking away (back view, curled tail on top), row 3 walking RIGHT in side profile, row 4 walking LEFT in side profile. \
4 frames per row: left step, passing, right step, passing; short legs, small trotting steps, feet lift only a little. \
Fringe falls over the eyes in rows 1-2 (eyes hidden), the coat bounces with each step."; }

idle() { gen idle landscape "Sheet of $DOG $STYLE $ANCHOR All poses face RIGHT, side or 3/4 view. \
Row 1 (5 cells): standing anchor; then a 4-frame PANT loop sitting: mouth open, small pink tongue, fringe PARTED so two small dark eyes are visible, \
body identical in all 4, only tongue, ears and beard locks move slightly. \
Row 2 (4 cells): 2-frame SCRATCH (sitting, hind leg scratching behind the ear, leg up / leg down, ear flapping), then 2-frame SNIFF (nose to the ground, tail up, nose and ears shift)."; }

yawn() { gen yawn landscape "Sheet of $DOG $STYLE $ANCHOR All poses SITTING, facing RIGHT, the SAME size and the SAME body position in every frame: \
the body, legs and tail are pixel-identical, ONLY the head changes. \
Row 1 (5 cells): standing anchor; then a 4-frame YAWN: mouth closed, mouth half open, mouth WIDE open with curled pink tongue and eyes squeezed shut, mouth closing. \
Row 2 (4 cells): a 4-frame HEAD TILT: looking straight with eyes visible, head tilted to one side (ear flops down, fringe slides off the eyes), head straight, head tilted to the other side. \
Do NOT zoom or change the dog's size between frames."; }

fun() { gen fun landscape "Sheet of $DOG $STYLE $ANCHOR All poses face RIGHT. $HAIR \
Row 1 (5 cells): standing anchor; then a 4-frame WET-DOG SHAKE: the long coat flies out to one side, to the other side, a cloud of messy hair, settling; a few water drops. \
Row 2 (4 cells): 2-frame BARK (standing, mouth closed / mouth open barking, beard bouncing), 2-frame HOWL (sitting, nose pointed up to the sky, mouth closed / open)."; }

dig() { gen dig landscape "Sheet of $DOG $STYLE $ANCHOR All poses face RIGHT. $HAIR \
Row 1 (5 cells): standing anchor; then a 4-frame DIG loop: front paws scraping the ground, nose down, tail up, small dirt clumps flying back. \
Row 2 (4 cells): PLAY BOW (front down, rear and tail up), LYING on the belly head on paws, then 2-frame ROLL ON BACK belly up with paws in the air wiggling (hair spread on the ground)."; }

run() { gen run landscape "Sheet of $DOG $STYLE $ANCHOR All poses face RIGHT. $HAIR \
Row 1 (5 cells): standing anchor; then a 4-frame GALLOP cycle (gather, extended, gather, extended), short legs, ears and long coat streaming back. \
Row 2 (4 cells): JUMP up happily (all paws off the ground), BEG standing on hind legs, then 2-frame TAIL WAG standing (tail plume left / right, rear coat swinging)."; }

sleep() { gen sleep landscape "Sheet of $DOG $STYLE $ANCHOR All poses face RIGHT. \
Row 1 (5 cells): standing anchor; then 2-frame SLEEP curled in a ball with the tail over the nose (breathing in / out), then 2-frame STRETCH (front stretch with rear up, rear stretch with hind legs back). \
Row 2 (4 cells): sitting LICK loop: tongue out, tongue further out, licking own front paw (paw raised), paw lick with tongue on the paw. Same body in all 4."; }

portrait() { gen portrait square "Pixel-art character-select portrait of $DOG Sitting front view, full body, head slightly tilted, fringe parted so two dark eyes shine, happy open mouth, \
big and readable, chunky pixel art, bold 1-pixel near-black outline, flat limited cool palette. Flat solid magenta #FF00FF background, no text, no frame."; }

names=("$@"); [ ${#names[@]} -eq 0 ] && names=(walk idle yawn fun dig run sleep portrait)
for n in "${names[@]}"; do "$n" & done
wait
