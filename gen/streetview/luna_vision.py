"""Direct Codex (ChatGPT OAuth) vision call with gpt-5.6-luna, bypassing Hermes' auxiliary vision routing.
Run with the Hermes venv python. Usage: luna_vision.py out.txt "question" img [img...]   (images sent together)"""
import base64
import json
import os
import sys

HA = os.path.expandvars(r"%LOCALAPPDATA%\hermes\hermes-agent")
sys.path.insert(0, HA); os.chdir(HA)
import hermes_bootstrap  # noqa: E402,F401
import httpx  # noqa: E402
from agent.auxiliary_client import _resolve_codex_credential_and_base  # noqa: E402
from agent.codex_headers import codex_cloudflare_headers  # noqa: E402

out, q, imgs = sys.argv[1], sys.argv[2], sys.argv[3:]
token, base = _resolve_codex_credential_and_base()
if not token:   # a stale per-model cooldown (other model) can hide the only pool entry; use it directly
    from agent.auxiliary_client import _pool_runtime_api_key, _pool_runtime_base_url
    from agent.credential_pool import load_pool
    from hermes_cli.auth_codex import _codex_pool_route_base_url
    for e in load_pool("openai-codex").entries():
        if e.last_status != "exhausted" and _pool_runtime_api_key(e):
            token, base = _pool_runtime_api_key(e), _codex_pool_route_base_url(_pool_runtime_base_url(e)); break
assert token, "no codex token"
content = [{"type": "input_text", "text": q}]
for p in imgs:
    content.append({"type": "input_image", "image_url": "data:image/png;base64," + base64.b64encode(open(p, "rb").read()).decode()})
body = {"model": os.environ.get("LUNA_MODEL", "gpt-5.6-luna"), "instructions": "You analyse images precisely.",
        "input": [{"role": "user", "content": content}], "stream": True, "store": False,
        "reasoning": {"effort": "medium"}}
hdr = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", **codex_cloudflare_headers(token, base_url=base)}
text = []
with httpx.stream("POST", base.rstrip("/") + "/responses", json=body, headers=hdr, timeout=400) as r:
    if r.status_code != 200:
        print("HTTP", r.status_code, r.read()[:500]); sys.exit(1)
    for line in r.iter_lines():
        if line.startswith("data: "):
            try: ev = json.loads(line[6:])
            except ValueError: continue
            if ev.get("type") == "response.output_text.delta": text.append(ev["delta"])
res = "".join(text)
open(out, "w", encoding="utf-8").write(res)
print(res)
