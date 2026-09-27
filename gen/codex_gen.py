"""GPT Image 2 via the Hermes openai-codex image plugin (ChatGPT/Codex OAuth, local reference files).
Run with Hermes' venv python:
  C:/Users/Lenovo/AppData/Local/hermes/hermes-agent/.venv/Scripts/python.exe codex_gen.py \
      --ref a.png --ref b.png --aspect square --prompt "..." --out out.png
aspect: landscape | square | portrait
"""
import argparse, importlib.util, json, os, shutil, sys, time
HA = r"C:\Users\Lenovo\AppData\Local\hermes\hermes-agent"
os.environ.setdefault("HERMES_HOME", r"C:\Users\Lenovo\AppData\Local\hermes")
sys.path.insert(0, HA)
os.chdir(HA)
import hermes_bootstrap  # noqa: F401  (credential pool / config wiring)
ap = argparse.ArgumentParser()
ap.add_argument("--ref", action="append", default=[])
ap.add_argument("--prompt", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--aspect", default="square")
a = ap.parse_args()
spec = importlib.util.spec_from_file_location("plugins.image_gen.openai_codex_direct", os.path.join(HA, "plugins", "image_gen", "openai-codex", "__init__.py"))
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
prov = mod.OpenAICodexImageGenProvider()
refs = [os.path.abspath(r) for r in a.ref]
t0 = time.time()
res = prov.generate(a.prompt, a.aspect, image_url=refs[0] if refs else None, reference_image_urls=refs[1:] or None)
if not res.get("success"):
    print(json.dumps({"ok": False, "error": res.get("error"), "type": res.get("error_type")})); sys.exit(1)
shutil.copy(res["image"], a.out)
print(json.dumps({"ok": True, "saved": a.out, "secs": round(time.time() - t0), "size": res.get("pixel_size") or res.get("size"), "model": res.get("model")}))
