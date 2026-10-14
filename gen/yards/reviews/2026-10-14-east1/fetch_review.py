"""Read (or reset) the review decisions stored on the game server (Worker chlopkow-api, route /review/<id>).

    python fetch_review.py                     # print the decisions (same JSON as the page's "Kopiuj JSON")
    python fetch_review.py get --out FILE      # ... write to FILE
    python fetch_review.py get --full          # whole stored document (state + export + client info) with rev / updated_at
    python fetch_review.py history             # last 20 saves (rev, time, bytes); add --rev N to print one
    python fetch_review.py put SEED.json       # replace the document (reset to the seeded v1 answers: build_v3_web.py --seed-out)
    python fetch_review.py hash                # SHA-256 of the key (the only thing the server stores)

The key is read from the file in $REVIEW_KEY_FILE, else review.key next to this script, else the main checkout copy
(gen/yards/reviews/2026-10-14-east1/review.key). The file is gitignored (*.key) and holds only the key. Never paste it into chat.
"""
import argparse
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAIN = Path("C:/Users/Lenovo/Hermes/projects/games/arek-w-chlopkowie/gen/yards/reviews/2026-10-14-east1")
API = "https://chlopkow-api.kolotom.workers.dev"
RID = "yard-east-v3"
ORIGIN = "https://itstomekk.pages.dev"


def read_key(path=None):
    for c in [path, os.environ.get("REVIEW_KEY_FILE"), HERE / "review.key", MAIN / "review.key"]:
        if c and Path(c).is_file():
            return Path(c).read_text(encoding="utf-8").strip().splitlines()[0].strip().removeprefix("k=")
    sys.exit("No review key file found (REVIEW_KEY_FILE / review.key)")


def call(method, url, key, body=None):
    req = urllib.request.Request(url, method=method, data=body, headers={"X-Review-Key": key, "Origin": ORIGIN, "User-Agent": "fetch_review/1", **({"Content-Type": "application/json"} if body is not None else {})})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", nargs="?", default="get", choices=["get", "history", "put", "hash"])
    ap.add_argument("file", nargs="?")
    ap.add_argument("--api", default=API)
    ap.add_argument("--id", default=RID)
    ap.add_argument("--key-file")
    ap.add_argument("--out")
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--rev", type=int)
    a = ap.parse_args()
    key = read_key(a.key_file)
    url = f"{a.api.rstrip('/')}/review/{a.id}"
    if a.cmd == "hash":
        print(hashlib.sha256(key.encode()).hexdigest())
        return
    if a.cmd == "put":
        doc = json.loads(Path(a.file).read_text(encoding="utf-8"))
        st, j = call("PUT", url, key, json.dumps(doc, ensure_ascii=False).encode("utf-8"))
        print(st, json.dumps(j))
        sys.exit(0 if st == 200 else 1)
    if a.cmd == "history":
        st, j = call("GET", url + "/history" + (f"?rev={a.rev}" if a.rev else ""), key)
        if st != 200:
            sys.exit(f"{st} {j}")
        if a.rev:
            print(json.dumps(j["doc"].get("export", j["doc"]), ensure_ascii=False, indent=2))
        else:
            for h in j["history"]:
                print(f"rev {h['rev']:4d}  {datetime.fromtimestamp(h['saved_at'] / 1000):%Y-%m-%d %H:%M:%S}  {h['bytes']} B")
        return
    st, j = call("GET", url, key)
    if st != 200:
        sys.exit(f"{st} {j}")
    doc = j["doc"]
    text = json.dumps({"rev": j["rev"], "updated_at": j["updated_at"], "doc": doc} if a.full else doc.get("export", doc), ensure_ascii=False, indent=2)
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
        print(f"rev {j['rev']}, saved {datetime.fromtimestamp(j['updated_at'] / 1000):%Y-%m-%d %H:%M:%S} -> {a.out}")
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        print(text)


if __name__ == "__main__":
    main()
