#!/usr/bin/env python3
"""
Generate NPC sprites using Codex GPT Image.
NPCs: grandpa (Zbyszek), Wesołych Świąt
Run: python gen/gen_npc_codex.py
Outputs: gen/npc_src/zbyszek.png, gen/npc_src/wesoly_swiat.png
"""
import subprocess
import json
import os
import sys

HA = r"C:\Users\Lenovo\AppData\Local\hermes\hermes-agent"
CODEX_PY = os.path.join(HA, "plugins", "image_gen", "openai-codex", "__init__.py")
REPO_ROOT = "."

npcs = {
    "zbyszek": {
        "prompt": "8-bit pixel art NPC sprite of an elderly farmer man with gray hair and beard, wearing a green/red cap and flannel shirt, front-facing standing pose, village farmer style, NES game style, isolated on transparent background, 200x250 pixels",
        "ref": "references/zbyszek/zbyszek_ref.png",
    },
    "wesoly_swiat": {
        "prompt": "8-bit pixel art NPC sprite of a middle-aged man with gray hair wearing a flannel shirt and cap, craftsman/boat builder, front-facing standing pose, working man style, NES game style, isolated on transparent background, 200x250 pixels",
        "ref": "references/wesoly_swiat/wesoly_swiat_ref.png",
    },
}

os.chdir(REPO_ROOT)

for name, cfg in npcs.items():
    out = f"gen/npc_src/{name}.png"
    ref_path = os.path.abspath(cfg["ref"])
    
    if not os.path.exists(ref_path):
        print(f"ERROR: Reference {ref_path} not found")
        continue
    
    print(f"\nGenerating {name}...")
    cmd = [
        sys.executable,
        os.path.join(HA, "gen_codex_cli.py"),
        "--ref", ref_path,
        "--aspect", "square",
        "--prompt", cfg["prompt"],
        "--out", out,
    ]
    
    # Use the codex_gen.py wrapper instead
    cmd = [
        sys.executable,
        "gen/codex_gen.py",
        "--ref", ref_path,
        "--aspect", "square",
        "--prompt", cfg["prompt"],
        "--out", out,
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print("STDERR:", result.stderr)
        print(f"Failed to generate {name}")
    else:
        print(f"✓ {name} -> {out}")

print("\nDone! Run: python gen/build_npcs.py")
