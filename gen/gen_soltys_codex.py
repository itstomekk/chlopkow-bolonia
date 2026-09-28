"""Generate matching Sołtys and Zbyszek atlas sprites with Codex GPT Image.

Run from the repository root using the project Python (Pillow, numpy and scipy installed):
  python gen/gen_soltys_codex.py
The script invokes Hermes' isolated Codex-authenticated Python for image calls.

Private reference photos remain local in references/ and are not committed or uploaded to other providers.
"""
from pathlib import Path
import subprocess
import sys

from PIL import Image
import numpy as np
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
CODEX_PY = r"C:\Users\Lenovo\AppData\Local\hermes\hermes-agent\.venv\Scripts\python.exe"

JOBS = {
    "soltys": {
        "refs": [ROOT / "references/soltys.png", ROOT / "gen/npc_src/patryk.png", ROOT / "gen/npc_src/grandpa.png"],
        "aspect": "portrait",
        "prompt": (
            "Create one full-body 16-bit pixel-art NPC sprite, front-facing with a slight 3/4 turn, "
            "of the older man shown in the first reference: short neatly combed gray hair, rectangular "
            "glasses, clean-shaven, dark brown pinstriped suit jacket, white shirt, pale gray tie, "
            "dark brown trousers and dress shoes. He is a dignified, friendly village head and holds "
            "a festive round golden harvest loaf on a small white lace cloth platter with both hands "
            "at waist height. Match the chunky, crisp clustered pixels, proportions, dark clean outline, "
            "and visual style of the pixel-art character references (ignore their character designs). "
            "Render as genuine low-resolution game pixel art: "
            "work on an approximately 64x128 pixel grid, large crisp color clusters, 1-2 pixel dark outline, "
            "about 24 flat colors total, no anti-aliasing, no fine noise, no smooth gradients, no painted texture. "
            "Single centered character, full body, feet visible, no crop, no cast shadow. Plain perfectly flat "
            "solid magenta #FF00FF background for removal. No text, no extra people."
        ),
    },
    "zbyszek": {
        "refs": [ROOT / "references/zbyszek/zbyszek_ref.png", ROOT / "gen/npc_src/patryk.png", ROOT / "gen/npc_src/grandpa.png"],
        "aspect": "portrait",
        "prompt": (
            "Create one full-body 16-bit pixel-art NPC sprite of the man in the first reference photo. "
            "Preserve his distinguishing look: older, sturdy rural man, gray-white short beard and stubble, "
            "green baseball cap with a small red patch, ruddy face, open rust-red/brown plaid flannel shirt "
            "over a dark undershirt, dark work trousers and brown work shoes. Relaxed slightly angled front-facing "
            "standing pose, one hand near his hip. Match the chunky pixel art style and clean outline of the "
            "pixel-art character references (ignore their character designs). Render as genuine low-resolution game pixel art: "
            "work on an approximately 64x128 pixel grid, broad stocky torso and legs, large crisp color clusters, "
            "1-2 pixel dark outline, about 24 flat colors total, no anti-aliasing, no fine noise, no smooth gradients, "
            "no painted texture. Single centered character, full body, feet visible, no crop, no cast shadow. "
            "Plain perfectly flat solid magenta #FF00FF background for removal. No text, no extra people."
        ),
    },
}


def clean_and_crop(raw: Path, output: Path) -> Image.Image:
    """Key magenta, despeckle detached debris and crop to transparent figure bounds."""
    # Reuse the repo's magenta/fringe despill implementation.
    sys.path.insert(0, str(ROOT / "gen"))
    from build_walk_cycles import remove_magenta_background

    arr = np.array(remove_magenta_background(Image.open(raw)), dtype=np.uint8)
    labels, count = ndimage.label(arr[..., 3] > 0, structure=np.ones((3, 3), dtype=bool))
    if count:
        sizes = np.bincount(labels.ravel())
        sizes[0] = 0
        keep = int(sizes.max())
        arr[(labels > 0) & (sizes[labels] < max(60, keep * 0.01)), 3] = 0
    arr[arr[..., 3] == 0, :3] = 0
    image = Image.fromarray(arr)
    box = image.getbbox()
    if not box:
        raise RuntimeError(f"No figure pixels remained after background removal: {raw}")
    image = image.crop(box)
    # Peel any remaining magenta-tinted edge pixels until the silhouette boundary is clean.
    pix = np.array(image, dtype=np.uint8)
    for _ in range(20):
        edge = (pix[..., 3] > 0) & ndimage.binary_dilation(pix[..., 3] == 0)
        rgb = pix[..., :3].astype(np.int16)
        tinted = edge & (rgb[..., 0] - rgb[..., 1] > 35) & (rgb[..., 2] - rgb[..., 1] > 25)
        if not tinted.any():
            break
        pix[tinted, 3] = 0
        pix[tinted, :3] = 0
    image = Image.fromarray(pix).crop(Image.fromarray(pix).getbbox())
    pix = np.array(image, dtype=np.uint8)
    edge = (pix[..., 3] > 0) & ndimage.binary_dilation(pix[..., 3] == 0)
    rgb = pix[..., :3].astype(np.int16)
    tinted = edge & (rgb[..., 0] - rgb[..., 1] > 35) & (rgb[..., 2] - rgb[..., 1] > 25)
    count = int(tinted.sum())
    if count:
        raise RuntimeError(f"{raw}: {count} magenta-tinted edge pixels remain")

    # Reduce AI micro-detail to a controlled pixel grid and palette before final atlas scaling.
    grid_h = 84
    grid_w = max(1, round(image.width * grid_h / image.height))
    small = image.resize((grid_w, grid_h), Image.Resampling.LANCZOS)
    colors = small.convert("RGB").quantize(colors=40, dither=Image.Dither.NONE).convert("RGB")
    colors.putalpha(small.getchannel("A"))
    sprite = colors.resize((max(1, round(colors.width * 150 / colors.height)), 150), Image.Resampling.NEAREST)
    sprite.save(output)
    return sprite


def process_existing(name: str) -> None:
    raw = ROOT / f"gen/npc_src/{name}_raw.png"
    sprite = clean_and_crop(raw, ROOT / f"gen/npc_src/{name}.png")
    print(f"{name}: cleaned {sprite.width}x{sprite.height}, edge magenta=0")
    if name == "soltys":
        # Preserve the legacy church sprite's ~0.56 aspect ratio in its 28x44 fit box.
        sprite = sprite.resize((round(sprite.height * 0.56), sprite.height), Image.Resampling.NEAREST)
        sprite.save(ROOT / f"gen/npc_src/{name}.png")
        sprite.save(ROOT / "docs/img/church/soltys.png")
        print(f"church sprite: {sprite.width}x{sprite.height}")


def generate(name: str) -> None:
    job = JOBS[name]
    raw = ROOT / f"gen/npc_src/{name}_raw.png"
    args = [CODEX_PY, str(ROOT / "gen/codex_gen.py"), "--aspect", job["aspect"], "--prompt", job["prompt"], "--out", str(raw)]
    for ref in job["refs"]:
        args.extend(["--ref", str(ref)])
    subprocess.run(args, cwd=ROOT, check=True)
    process_existing(name)


if __name__ == "__main__":
    if sys.argv[1:2] == ["--process-existing"]:
        for character in sys.argv[2:] or list(JOBS):
            process_existing(character)
    else:
        for character in sys.argv[1:] or list(JOBS):
            generate(character)
