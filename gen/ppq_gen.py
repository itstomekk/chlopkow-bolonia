"""PPQ gpt-image-2 generation with one uploaded reference (reuses generate_dragon_saga plumbing).
python ppq_gen.py --ref file.png --prompt "..." --out out.png [--aspect landscape_16_9|square_1_1]"""
import argparse, json, sys, datetime
from pathlib import Path
sys.path.insert(0, r"C:\Users\Lenovo\Hermes\image-gen\2026-09-23-gta-loading-screen-v2")
import generate_dragon_saga as base
ap = argparse.ArgumentParser()
ap.add_argument("--ref"); ap.add_argument("--prompt", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--aspect", default="landscape_16_9")
a = ap.parse_args()
key = base.load_api_key()
url = base.upload_local_file(Path(a.ref), base.DEFAULT_UPLOAD_CMD, {}) if a.ref else None
orig = base.build_api_payload
def bp(prompt, image_url):
    p = orig(prompt, image_url); p["aspect_ratio"] = a.aspect; return p
base.build_api_payload = bp
gen = base.call_ppq_generation(a.prompt, url, key)
img = base.download_generated_image(gen["url"], key, gen.get("cost"))
Path(a.out).write_bytes(img)
rec = {"ts": datetime.datetime.now(datetime.timezone.utc).isoformat(), "provider": "ppq", "model": "gpt-image-2",
       "cost_usd": gen.get("cost"), "session_id": "claude-code-digital-collage-2026-09-27", "note": "digital-collage: " + Path(a.out).name}
try:
    with open(r"C:\Users\Lenovo\AppData\Local\hermes\telemetry\image-gen-costs.jsonl", "a", encoding="utf-8") as f: f.write(json.dumps(rec) + "\n")
except Exception as e: print("log fail", e)
print(json.dumps({"saved": a.out, "cost": gen.get("cost"), "ref_url": url}))
