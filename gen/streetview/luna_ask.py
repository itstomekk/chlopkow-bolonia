"""Ask Codex gpt-5.6-luna (via `hermes chat --image`) about images in parallel. Usage: luna_ask.py out_prefix "question" img..."""
import concurrent.futures as cf
import os
import subprocess
import sys

H = os.path.expandvars(r"%LOCALAPPDATA%\hermes\hermes-agent\.venv\Scripts\hermes.exe")
prefix, q, imgs = sys.argv[1], sys.argv[2], sys.argv[3:]


def ask(i_img):
    i, img = i_img
    r = subprocess.run([H, "chat", "-q", q.replace("{n}", str(i + 1)) + " Do not use tools.", "--image", img,
                        "--provider", "openai-codex", "-m", "gpt-5.6-luna", "-Q"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=400)
    out = "\n".join(l for l in r.stdout.splitlines() if "out of sync" not in l)
    open(f"{prefix}_{i + 1}.txt", "w", encoding="utf-8").write(out)
    return out


with cf.ThreadPoolExecutor(4) as ex:
    for i, o in enumerate(ex.map(ask, enumerate(imgs))):
        print(f"===== {i + 1}\n{o[-2500:]}")
