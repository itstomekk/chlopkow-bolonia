"""Build hand-authored, deterministic pixel-art wild-animal atlas rows."""
import json
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
IMG = ROOT / "docs/img/critters.png"
META = ROOT / "docs/img/critters.json"
CELL, INK = 64, "#282433"
PALETTES = {
    "boar": ("#765044", "#a77a5e", "#513a36", "#d6b58a"),
    "mouse": ("#8c817f", "#c0aaa5", "#625d68", "#e0a4a2"),
    "hare": ("#ad8058", "#d1aa78", "#745341", "#f0ddc0"),
    "pig": ("#d98791", "#f1b1ae", "#ad606e", "#f8d3c3"),
    "butterfly": ("#ed70a1", "#ffd17a", "#9a4b83", "#f8e5c1"),
}


def poly(d, points, fill):
    d.polygon(points, fill=fill)


def draw_boar(d, phase, idle):
    m,l,sh,a=PALETTES['boar']; b=0 if idle else phase%2
    poly(d,[(10,34+b),(14,27+b),(24,24+b),(41,25+b),(49,30+b),(57,32+b),(61,37+b),(58,43+b),(50,46+b),(17,45+b),(11,41+b)],INK)
    poly(d,[(12,34+b),(16,29+b),(25,26+b),(41,27+b),(48,32+b),(56,34+b),(59,37+b),(57,41+b),(49,44+b),(18,43+b),(13,40+b)],m)
    poly(d,[(18,31+b),(28,28+b),(42,29+b),(48,33+b),(39,35+b),(22,35+b)],l)
    poly(d,[(42,28+b),(45,22+b),(51,25+b),(53,31+b)],INK); poly(d,[(44,28+b),(46,24+b),(50,26+b),(51,30+b)],sh)
    poly(d,[(51,34+b),(60,35+b),(63,39+b),(60,43+b),(52,42+b)],sh); d.rectangle((56,37+b,60,39+b),fill=a)
    d.point((53,32+b),fill=INK); d.point((53,31+b),fill="#fff0d0")
    for x,lift in ((20,0),(31,phase%2),(45,1-phase%2)):
        d.rectangle((x,42+b,x+4,55-lift),fill=INK); d.rectangle((x+1,43+b,x+3,53-lift),fill=sh)
    d.line((12,36+b,7,34+b,5,30+b),fill=INK,width=2); d.point((17,32+b),fill=a)


def draw_mouse(d, phase, idle):
    m,l,sh,a=PALETTES['mouse']; b=0 if idle else phase%2
    d.line((17,43+b,10,47+b,5,45+b,3,41+b),fill=INK,width=3); d.line((17,42+b,10,46+b,5,44+b,3,40+b),fill=l,width=1)
    poly(d,[(12,39+b),(16,32+b),(25,29+b),(39,30+b),(46,34+b),(52,36+b),(55,40+b),(51,45+b),(40,47+b),(20,46+b),(13,43+b)],INK)
    poly(d,[(14,39+b),(18,34+b),(26,31+b),(39,32+b),(45,35+b),(51,37+b),(53,40+b),(50,43+b),(39,45+b),(21,44+b),(15,42+b)],m)
    poly(d,[(20,36+b),(28,33+b),(40,34+b),(45,37+b),(37,39+b),(24,39+b)],l)
    d.ellipse((39,24+b,49,34+b),fill=INK); d.ellipse((41,26+b,47,32+b),fill=a); d.ellipse((43,28+b,46,31+b),fill=sh)
    poly(d,[(48,36+b),(56,37+b),(60,40+b),(56,42+b),(49,41+b)],INK); d.rectangle((53,38+b,57,40+b),fill=l)
    d.point((51,35+b),fill=INK); d.point((50,34+b),fill="#fff4e8"); d.line((53,41+b,60,44+b),fill=sh,width=1)
    for x in (24,38):
        lift=phase%2 if not idle else 0; d.rectangle((x,43+b,x+2,51-lift),fill=INK); d.rectangle((x+1,44+b,x+1,50-lift),fill=sh)


def draw_hare(d, phase, idle):
    m,l,sh,a=PALETTES['hare']; jump=(phase%2)*2 if not idle else 0
    poly(d,[(8,40-jump),(12,33-jump),(22,31-jump),(31,34-jump),(39,31-jump),(47,33-jump),(53,37-jump),(51,43-jump),(43,46-jump),(24,47-jump),(13,45-jump)],INK)
    poly(d,[(10,40-jump),(14,35-jump),(23,33-jump),(30,36-jump),(38,33-jump),(46,35-jump),(51,38-jump),(49,42-jump),(42,44-jump),(24,45-jump),(15,43-jump)],m)
    d.ellipse((14,35-jump,31,45-jump),fill=sh); d.rectangle((18,37-jump,24,41-jump),fill=l)
    poly(d,[(38,34-jump),(43,27-jump),(51,26-jump),(57,31-jump),(57,38-jump),(51,42-jump),(42,40-jump)],INK)
    poly(d,[(40,34-jump),(45,29-jump),(51,28-jump),(55,32-jump),(55,37-jump),(50,40-jump),(43,38-jump)],l)
    poly(d,[(43,30-jump),(36,19-jump),(38,13-jump),(42,16-jump),(47,29-jump)],INK); poly(d,[(44,28-jump),(38,19-jump),(39,16-jump),(41,18-jump),(46,29-jump)],m)
    poly(d,[(47,29-jump),(48,14-jump),(53,9-jump),(56,13-jump),(53,31-jump)],INK); poly(d,[(49,28-jump),(50,15-jump),(53,12-jump),(54,14-jump),(52,29-jump)],m)
    d.point((51,33-jump),fill=INK); d.point((50,32-jump),fill="#fff1d6"); d.point((56,37-jump),fill=sh); d.ellipse((6,39-jump,14,46-jump),fill=a)
    for x,h in ((26,7),(37,8),(46,5)):
        lift=phase%2 if not idle else 0; d.rectangle((x,42-jump,x+3,53-h-lift),fill=INK); d.rectangle((x+1,43-jump,x+2,52-h-lift),fill=sh)


def draw_pig(d, phase, idle):
    m,l,sh,a=PALETTES['pig']; b=0 if idle else phase%2
    poly(d,[(7,35+b),(12,28+b),(24,25+b),(40,26+b),(49,30+b),(54,35+b),(60,36+b),(63,41+b),(60,46+b),(51,48+b),(16,46+b),(9,42+b)],INK)
    poly(d,[(9,35+b),(14,30+b),(25,27+b),(40,28+b),(48,32+b),(52,36+b),(58,37+b),(61,40+b),(59,43+b),(50,46+b),(17,44+b),(11,41+b)],m)
    poly(d,[(16,33+b),(25,29+b),(39,30+b),(46,33+b),(39,36+b),(22,36+b)],l)
    poly(d,[(41,29+b),(43,23+b),(49,25+b),(52,32+b)],INK); poly(d,[(43,29+b),(45,25+b),(48,26+b),(50,31+b)],sh)
    d.arc((7,29+b,16,38+b),190,500,fill=INK,width=2); d.arc((9,30+b,15,37+b),190,500,fill=l,width=1)
    d.rectangle((56,38+b,61,42+b),fill=a); d.point((58,39+b),fill=sh); d.point((60,39+b),fill=sh)
    d.point((51,33+b),fill=INK); d.point((50,32+b),fill="#fff7e8")
    for x,lift in ((19,0),(31,phase%2),(47,1-phase%2)):
        d.rectangle((x,43+b,x+4,54-lift),fill=INK); d.rectangle((x+1,44+b,x+2,52-lift),fill=sh)


def draw_butterfly(d, phase):
    m,l,sh,a=PALETTES['butterfly']; lift=(0,2,5,1)[phase]
    # Broad scalloped upper wings connect at the thorax and visibly sweep through four flap heights.
    left=[(30,31),(25,27-lift),(19,25-lift),(13,28),(12,32),(16,36),(23,36),(30,34)]
    right=[(34,31),(39,27-lift),(45,25-lift),(51,28),(52,32),(48,36),(41,36),(34,34)]
    poly(d,left,INK); poly(d,right,INK)
    poly(d,[(30,31),(25,28-lift),(19,27-lift),(14,29),(14,32),(17,34),(23,34),(30,33)],m)
    poly(d,[(34,31),(39,28-lift),(45,27-lift),(50,29),(50,32),(47,34),(41,34),(34,33)],m)
    poly(d,[(30,34),(24,35),(20,39),(23,42),(29,40)],INK); poly(d,[(34,34),(40,35),(44,39),(41,42),(35,40)],INK)
    poly(d,[(30,35),(25,36),(22,39),(24,40),(29,39)],sh); poly(d,[(34,35),(39,36),(42,39),(40,40),(35,39)],sh)
    d.point((19,29-lift),fill=l); d.point((45,29-lift),fill=l); d.point((16,32),fill=a); d.point((48,32),fill=a)
    d.ellipse((29,28,35,42),fill=INK); d.rectangle((31,30,33,39),fill=sh); d.point((31,32),fill=a); d.point((32,36),fill=l)
    d.line((30,29,27,24,24,22),fill=INK,width=1); d.line((33,29,36,24,39,22),fill=INK,width=1)


def main():
    old=Image.open(IMG).convert("RGBA"); meta=json.loads(META.read_text(encoding="utf-8"))
    out=Image.new("RGBA",(CELL*4,CELL*10),(0,0,0,0)); out.alpha_composite(old.crop((0,0,CELL*4,CELL*5)))
    kinds=["boar","mouse","hare","pig","butterfly"]
    drawers={"boar":draw_boar,"mouse":draw_mouse,"hare":draw_hare,"pig":draw_pig}
    for row,kind in enumerate(kinds,5):
        for phase in range(4):
            im=Image.new("RGBA",(CELL,CELL),(0,0,0,0)); d=ImageDraw.Draw(im)
            draw_butterfly(d,phase) if kind=="butterfly" else drawers[kind](d,phase,phase>=2)
            out.alpha_composite(im,(phase*CELL,row*CELL))
    # Transparent pixels must not contain matte RGB values.
    alpha=out.getchannel("A"); rgb=Image.new("RGBA",out.size,(0,0,0,0)); rgb.alpha_composite(out); rgb.putalpha(alpha); out=rgb
    out.save(IMG,optimize=True)
    for kind,row,h in [("boar",5,44),("mouse",6,18),("hare",7,28),("pig",8,42),("butterfly",9,21)]:
        frames=["flap1","flap2","flap3","flap4"] if kind=="butterfly" else ["walk1","walk2","idle1","idle2"]
        meta["rows"][kind]={"row":row,"frames":frames,"h":h}
    meta["cell"]=CELL; META.write_text(json.dumps(meta,indent=1)+"\n",encoding="utf-8")
    print(f"pixel critters: {out.width}x{out.height}, rows=boar,mouse,hare,pig,butterfly")

if __name__=="__main__": main()
