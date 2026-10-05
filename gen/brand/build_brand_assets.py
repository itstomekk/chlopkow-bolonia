"""Build the CHŁOPKÓW POLONIA brand assets from the approved emblem illustration.

    python gen/brand/build_brand_assets.py

Input : gen/brand/emblem-source.png   (GPT Image art, no lettering, flat ivory background)
Output: docs/img/chlopkow-polonia-emblem.png   transparent emblem, no wordmark
        docs/img/chlopkow-polonia-logo.png     emblem + wordmark typeset in Silkscreen on the sign plank
        docs/img/favicon-polonia.png           128 px square crop (church, windmill, falcon)
        docs/img/og-polonia.png                1200x630 share card

The wordmark is real text (Silkscreen, the game's own pixel font) so Polish diacritics stay exact.
"""
import base64
import sys
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "gen" / "brand" / "emblem-source.png"
IMG = ROOT / "docs" / "img"
FONT_EXT = ROOT / "docs" / "fonts" / "Silkscreen-400-latin-ext.woff2"
FONT_LAT = ROOT / "docs" / "fonts" / "Silkscreen-400-latin.woff2"
WORDMARK = "CHŁOPKÓW POLONIA"
# Plank text area inside the cut emblem (measured from the artwork): centre and usable width.
PLANK_CENTER = (610, 742)
PLANK_WIDTH = 1020


def cut_background(path: Path) -> Image.Image:
    a = np.array(Image.open(path).convert("RGBA"))
    h, w = a.shape[:2]
    bg = a[5, 5, :3].astype(int)
    cand = np.abs(a[:, :, :3].astype(int) - bg).sum(2) < 28
    mask = np.zeros((h, w), bool)
    q = deque()
    for x in range(w):
        for y in (0, h - 1):
            if cand[y, x] and not mask[y, x]:
                mask[y, x] = True
                q.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if cand[y, x] and not mask[y, x]:
                mask[y, x] = True
                q.append((y, x))
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and cand[ny, nx] and not mask[ny, nx]:
                mask[ny, nx] = True
                q.append((ny, nx))
    a[mask, 3] = 0
    out = Image.fromarray(a)
    return out.crop(out.getchannel("A").getbbox())


def render_lockup(emblem_path: Path, out_path: Path):
    font_ext = base64.b64encode(FONT_EXT.read_bytes()).decode()
    font_lat = base64.b64encode(FONT_LAT.read_bytes()).decode()
    emblem64 = base64.b64encode(emblem_path.read_bytes()).decode()
    w, h = Image.open(emblem_path).size
    html = f"""<!doctype html><meta charset="utf-8"><style>
@font-face{{font-family:Silk;src:url(data:font/woff2;base64,{font_ext}) format('woff2');unicode-range:U+0100-02BA,U+1E00-1E9F}}
@font-face{{font-family:Silk;src:url(data:font/woff2;base64,{font_lat}) format('woff2');unicode-range:U+0000-00FF}}
html,body{{margin:0;background:transparent}}
#s{{position:relative;width:{w}px;height:{h}px}}
img{{position:absolute;inset:0;image-rendering:pixelated}}
#t{{position:absolute;left:{PLANK_CENTER[0]}px;top:{PLANK_CENTER[1]}px;transform:translate(-50%,-50%);
 font:400 100px/1 Silk;white-space:nowrap;color:#ffe9a6;letter-spacing:4px}}
</style><div id="s"><img src="data:image/png;base64,{emblem64}"><div id="t">{WORDMARK}</div></div>
<script>
const t=document.getElementById('t');
document.fonts.load('100px Silk','ŁÓ').then(()=>document.fonts.load('100px Silk','CH')).then(()=>{{
  const k={PLANK_WIDTH}/t.getBoundingClientRect().width; t.style.fontSize=(100*k)+'px';
  const p=Math.max(3,Math.round(100*k/16)); // hard pixel outline + shadow, like the in-game title
  const o=[];for(const [x,y] of [[-1,-1],[0,-1],[1,-1],[-1,0],[1,0],[-1,1],[0,1],[1,1]])o.push(`${{x*p}}px ${{y*p}}px 0 #1b1208`);
  o.push(`0 ${{p*2}}px 0 #1b1208`,`${{p}}px ${{p*2}}px 0 #1b1208`,`${{-p}}px ${{p*2}}px 0 #1b1208`);
  t.style.textShadow=o.join(',');document.body.dataset.ready='1';
}});
</script>"""
    tmp = out_path.with_suffix(".html")
    tmp.write_text(html, encoding="utf-8")
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": w, "height": h})
        pg.goto(tmp.as_uri())
        pg.wait_for_selector("body[data-ready='1']")
        pg.locator("#s").screenshot(path=str(out_path), omit_background=True)
        b.close()
    tmp.unlink()


def main():
    IMG.mkdir(parents=True, exist_ok=True)
    emblem = cut_background(SRC)
    emblem_path = IMG / "chlopkow-polonia-emblem.png"
    emblem.save(emblem_path, optimize=True)
    logo_path = IMG / "chlopkow-polonia-logo.png"
    render_lockup(emblem_path, logo_path)

    # Favicon: the scene above the plank, squared and reduced (nearest keeps the pixel look).
    scene = emblem.crop((0, 0, emblem.width, 660))
    side = max(scene.size)
    sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    sq.alpha_composite(scene, ((side - scene.width) // 2, (side - scene.height) // 2))
    sq.resize((128, 128), Image.LANCZOS).save(IMG / "favicon-polonia.png", optimize=True)

    # Share card: the real splash scene, dimmed, with the logo.
    card = Image.new("RGBA", (1200, 630), (16, 22, 58, 255))
    splash = Image.open(IMG / "splash.png").convert("RGBA")
    k = max(1200 / splash.width, 630 / splash.height)
    splash = splash.resize((round(splash.width * k), round(splash.height * k)), Image.NEAREST)
    card.alpha_composite(splash, ((1200 - splash.width) // 2, (630 - splash.height) // 2))
    card.alpha_composite(Image.new("RGBA", card.size, (8, 12, 28, 170)))
    logo = Image.open(logo_path).convert("RGBA")
    lk = 560 / logo.height
    logo = logo.resize((round(logo.width * lk), 560), Image.LANCZOS)
    card.alpha_composite(logo, ((1200 - logo.width) // 2, 35))
    card.convert("RGB").save(IMG / "og-polonia.png", optimize=True)
    for name in ("chlopkow-polonia-emblem", "chlopkow-polonia-logo", "favicon-polonia", "og-polonia"):
        f = IMG / f"{name}.png"
        print(f.name, Image.open(f).size, f.stat().st_size // 1024, "KB")


if __name__ == "__main__":
    sys.exit(main())
