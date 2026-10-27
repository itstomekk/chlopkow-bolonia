"""Human pose sets (dog-style 'poses' pipeline for people). Tomek 2026-10-26: full pose set + portrait for every character.

Identity/style source is the character's own shipped walk sheet (docs/img/<id>_sheet.png), composited on magenta.
No private reference photos are sent anywhere by this script.
Run: python gen/poses/gen_poses.py <id> [sheet ...]     -> gen/poses/<id>/raw/<sheet>.png
Sheets: talk emote act move work portrait
"""
import subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PY = r"C:/Users/Lenovo/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe"

STYLE = ("Chunky retro pixel art exactly like Image 1 (same big pixel blocks, same bold dark outline, same flat limited palette and shading, same top-down 3/4 game camera, "
         "same proportions, head-to-body ratio and clothes). Image 1 is the shipped walk sheet of this character: copy the face, hair, glasses/beard if any, clothes and colours EXACTLY. "
         "Draw the SAME person at the SAME scale in every cell. Flat solid magenta #FF00FF background, no shadows, no ground, no text, no grid lines. "
         "Every figure separate, fully inside its own cell, not touching neighbours.")
ANCHOR = "Row 1 starts with an extra cell: the character STANDING relaxed in side profile facing right (size reference)."
SHEETS = {
    "talk": ("Row 1 (5 cells): standing anchor; then a 4-frame TALKING loop, side view facing right: mouth closed, mouth open, mouth wide, mouth open, one hand gesturing a little; body identical, only mouth and hand move. "
             "Row 2 (4 cells): a 4-frame WAVE hello, facing the viewer in 3/4 view: arm down, arm raised, hand swung left, hand swung right, friendly smile."),
    "emote": ("Row 1 (5 cells): standing anchor; then a 4-frame LAUGH loop, facing the viewer in 3/4 view: head back, mouth wide open, shoulders shaking, eyes squeezed, hand on belly. "
              "Row 2 (4 cells): THINK (hand on chin, eyes up), SURPRISED (jumps back a little, mouth open, hands up), SAD (head down, shoulders low), ANGRY (fists clenched, frown)."),
    "act": ("Row 1 (5 cells): standing anchor; then POINT forward (arm straight out to the right), POINT up (arm raised), CHEER 1 (both arms up, mouth open), CHEER 2 (arms up, one foot off the ground). "
            "Row 2 (4 cells): SIT 1 (sitting on the ground, knees up, side view, breathing in), SIT 2 (the same, breathing out), SLEEP 1 (lying on the side asleep, eyes closed), SLEEP 2 (same, breathing)."),
    "move": ("Row 1 (5 cells): standing anchor; then a 4-frame RUN cycle, side view facing right: leaning forward, arms pumping, legs wide, feet lifting (stride, passing, stride, passing). "
             "Row 2 (4 cells): JUMP (both feet off the ground, arms up), HURT 1 (flinching, one hand on the head), HURT 2 (doubled over, hand on stomach), KNOCKED OUT (lying flat on the back, eyes closed, little stars)."),
    "work": ("Row 1 (5 cells): standing anchor; then a 4-frame DIG loop with a small shovel, side view facing right: shovel raised, shovel down into the dirt, lifting a scoop, tossing it. "
             "Row 2 (4 cells): CROUCH (crouching down to pick something up from the ground), PICK UP (standing up holding a small item), THROW 1 (arm cocked back), THROW 2 (arm swung forward, follow-through)."),
}


def make_ref(cid, out):
    d = ROOT / "docs" / "img"
    src = d / f"{cid}_sheet_8dir.png"
    im = Image.open(src if src.exists() else d / f"{cid}_sheet.png").convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 0, 255, 255))
    bg.alpha_composite(im)
    bg.convert("RGB").save(out)


def run(cid, name, ref, out):
    f = out / f"{name}.png"
    if f.exists():
        return name, "skip"
    if name == "portrait":
        asp = "square"
        prompt = ("Pixel-art character-select portrait of the character in Image 1: full body standing front view, friendly, big and readable, same face, hair, clothes and colours exactly as Image 1. "
                  "Chunky retro pixel art like Image 1, bold dark outline, flat limited palette. Flat solid magenta #FF00FF background, no text, no frame.")
    else:
        asp = "landscape"
        prompt = f"Sheet of the character in Image 1. {STYLE} {ANCHOR} {SHEETS[name]}"
    r = None
    for attempt in range(3):
        r = subprocess.run([PY, str(ROOT / "gen" / "codex_gen.py"), "--ref", str(ref), "--aspect", asp, "--out", str(f), "--prompt", prompt], capture_output=True, text=True)
        (out / f"{name}.log").write_text((r.stdout or "") + (r.stderr or ""), encoding="utf-8")
        if r.returncode == 0 and f.exists():
            return name, "ok"
        time.sleep(20 * (attempt + 1))
    return name, "FAILED " + (r.stdout or "")[-200:]


if __name__ == "__main__":
    cid = sys.argv[1]
    names = sys.argv[2:] or list(SHEETS) + ["portrait"]
    out = HERE / cid / "raw"
    out.mkdir(parents=True, exist_ok=True)
    ref = HERE / cid / "ref.png"
    make_ref(cid, ref)
    with ThreadPoolExecutor(3) as ex:
        for n, s in ex.map(lambda n: run(cid, n, ref, out), names):
            print(cid, n, s, flush=True)
