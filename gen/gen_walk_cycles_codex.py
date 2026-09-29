#!/usr/bin/env python3
"""
Generate 4-direction walk-cycle sprites for playable characters using Codex.
Characters: Marcin, Damian, Edytka
Each generates 4 directions (down, right, up, left) with 2 walk frames each.
Run: python gen/gen_walk_cycles_codex.py
Outputs: gen/npc_src/marcin_walkcycle.png (directions as rows), etc.
"""
import subprocess
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(".")
GEN_DIR = REPO_ROOT / "gen"

# Characters: (name, gender, description, ref_image, walk_style)
characters = {
    "marcin": {
        "ref": "references/marcin/marcin_ref.png",
        "desc": "teenage boy with dark hair, village clothes, youthful, athletic build",
        "style": "boy",
    },
    "damian": {
        "ref": "references/damian/damian_ref.png", 
        "desc": "teenage boy with light/brown hair, casual village clothes",
        "style": "boy",
    },
    "edytka": {
        "ref": "references/edytka/edytka_ref.png",
        "desc": "adult woman with light hair, flannel shirt, working clothes",
        "style": "woman",
    },
}

# Base prompt template for walk cycles
PROMPT_TEMPLATE = """8-bit pixel art sprite sheet showing a {desc} in a 4x2 grid:
- Top row (4 columns): walking frames going DOWN (frame 1, frame 2, frame 1, frame 2) 
- Row 2 (4 columns): walking frames going RIGHT (frame 1, frame 2, frame 1, frame 2)
- Row 3 (4 columns): walking frames going UP (frame 1, frame 2, frame 1, frame 2)  
- Row 4 (4 columns): walking frames going LEFT (frame 1, frame 2, frame 1, frame 2)
NES/SNES pixel art style, each frame 64x80 pixels, transparent background, consistent scale and pose style
Style: {style} walk cycle, village/farm setting"""

def gen_walkcycle(name, ref_path, desc, style):
    """Generate walk cycle for one character"""
    print(f"\nGenerating {name} walk-cycle...")
    
    # Ensure reference exists
    ref_abs = REPO_ROOT / ref_path
    if not ref_abs.exists():
        print(f"  ERROR: Reference {ref_abs} not found")
        return False
    
    # Generate prompt
    prompt = PROMPT_TEMPLATE.format(desc=desc, style=style)
    
    # Output path
    out_file = GEN_DIR / "npc_src" / f"{name}_walkcycle_raw.png"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Run Codex generation
    cmd = [
        sys.executable,
        str(GEN_DIR / "codex_gen.py"),
        "--ref", str(ref_abs),
        "--aspect", "landscape",
        "--prompt", prompt,
        "--out", str(out_file),
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    try:
        res = json.loads(result.stdout)
        if res.get("ok"):
            print(f"  ✓ {name} -> {out_file}")
            print(f"    Size: {res.get('size')}, Model: {res.get('model')}, Time: {res.get('secs')}s")
            return True
        else:
            print(f"  ERROR: {res.get('error')}")
            return False
    except:
        print(f"  STDERR: {result.stderr}")
        return False

os.chdir(REPO_ROOT)

# Generate all characters
results = {}
for name, cfg in characters.items():
    results[name] = gen_walkcycle(
        name,
        cfg["ref"],
        cfg["desc"],
        cfg["style"],
    )

print("\n" + "="*60)
if all(results.values()):
    print("✓ All walk-cycles generated!")
    print("\nNext step: slice and build sprite sheets")
    print("  python gen/build_walk_cycles.py")
else:
    failed = [k for k, v in results.items() if not v]
    print(f"✗ Failed: {failed}")
