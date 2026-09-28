"""Deterministically build hand-authored pixel-art vehicle sprites."""
import json
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/img/vehicles.png"
META = ROOT / "docs/img/vehicles.json"
CELL = 64
C = {"ink":"#242431", "tire":"#20212a", "rubber":"#343640", "rim":"#9fa2a3", "hub":"#e0ad55", "red":"#bd3038", "red_l":"#ed5751", "red_s":"#7c2632", "green":"#397448", "green_l":"#69a257", "green_s":"#234b39", "glass":"#78b5c3", "glass_l":"#c2e3df", "glass_s":"#416d81", "metal":"#c0c5b8", "light":"#ffe3a0", "shadow":"#141822"}


def wheel(d, cx, cy, r, phase=0):
    d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=C['ink'])
    d.ellipse((cx-r+1,cy-r+1,cx+r-1,cy+r-1),fill=C['tire'])
    d.ellipse((cx-r+3,cy-r+3,cx+r-3,cy+r-3),fill=C['rubber'])
    d.ellipse((cx-3,cy-3,cx+3,cy+3),fill=C['rim'])
    d.ellipse((cx-1,cy-1,cx+1,cy+1),fill=C['hub'])
    # Four clear hub-spoke poses rotate as wheel frames advance.
    spokes=((cx-r+4,cy,cx+r-4,cy),(cx,cy-r+4,cx,cy+r-4),(cx-r+4,cy-r+4,cx+r-4,cy+r-4),(cx-r+4,cy+r-4,cx+r-4,cy-r+4))
    d.line(spokes[phase%4],fill=C['metal'],width=1)
    d.point((cx + (phase%4-1), cy-r+3),fill=C['hub'])


def side_tractor(d, phase):
    # Large rear wheel and smaller front wheel establish the Ursus silhouette.
    wheel(d,17,46,12,phase); wheel(d,48,49,7,phase)
    d.polygon([(7,34),(13,28),(27,27),(34,31),(48,31),(54,35),(54,43),(42,45),(27,43),(11,43)],fill=C['ink'])
    d.polygon([(9,34),(15,30),(27,29),(33,33),(46,33),(51,36),(51,41),(41,42),(27,41),(12,41)],fill=C['green'])
    d.polygon([(30,33),(47,33),(51,36),(50,39),(31,39)],fill=C['red'])
    d.rectangle((33,34,46,35),fill=C['red_l']); d.rectangle((34,37,49,38),fill=C['red_s'])
    # Cab frame, broad glass panes, roof and simple driver silhouette.
    d.polygon([(23,29),(23,11),(27,7),(40,7),(44,11),(44,31)],fill=C['ink'])
    d.polygon([(26,27),(26,12),(29,10),(38,10),(41,12),(41,28)],fill=C['green'])
    d.rectangle((28,12,39,25),fill=C['glass']); d.rectangle((28,12,30,23),fill=C['glass_l']); d.rectangle((36,18,39,25),fill=C['glass_s'])
    d.rectangle((32,15,34,19),fill=C['shadow']); d.rectangle((33,13,35,16),fill="#d7ad83")
    d.rectangle((21,6,45,9),fill=C['ink']); d.rectangle((23,5,43,7),fill=C['red']); d.rectangle((25,5,40,6),fill=C['red_l'])
    # Hood / front grille and rear red wheel guard.
    d.rectangle((43,28,55,33),fill=C['ink']); d.rectangle((45,29,54,32),fill=C['red']); d.rectangle((47,29,53,30),fill=C['red_l'])
    d.rectangle((53,32,56,34),fill=C['light']); d.rectangle((8,30,12,35),fill=C['ink']); d.rectangle((9,30,11,33),fill=C['red'])
    d.polygon([(9,33),(10,27),(15,25),(28,26),(29,29),(15,29),(13,35)],fill=C['ink'])
    d.polygon([(11,32),(12,28),(15,27),(26,28),(26,29),(15,29),(13,33)],fill=C['red'])
    d.rectangle((50,22,53,29),fill=C['ink']); d.rectangle((51,18,52,24),fill=C['metal']); d.point((51,17),fill=C['ink'])
    d.rectangle((6,42,13,44),fill=C['green_s']); d.rectangle((43,43,54,45),fill=C['green_s'])


def front_tractor(d, phase):
    wheel(d,12,48,8,phase); wheel(d,52,48,8,phase)
    d.polygon([(15,38),(18,29),(22,24),(42,24),(46,29),(49,38),(47,45),(17,45)],fill=C['ink'])
    d.polygon([(18,37),(21,30),(24,26),(40,26),(43,30),(46,37),(44,42),(20,42)],fill=C['red'])
    d.rectangle((22,28,42,36),fill=C['glass_s']); d.rectangle((24,29,40,35),fill=C['glass']); d.rectangle((25,29,29,34),fill=C['glass_l'])
    d.rectangle((20,24,44,27),fill=C['ink']); d.rectangle((22,23,42,25),fill=C['green']); d.rectangle((25,23,39,24),fill=C['green_l'])
    d.rectangle((26,37,38,42),fill=C['ink']); d.rectangle((28,38,36,41),fill=C['metal']); d.rectangle((30,38,34,39),fill=C['shadow'])
    d.rectangle((17,39,21,42),fill=C['light']); d.rectangle((43,39,47,42),fill=C['light'])
    d.polygon([(14,45),(50,45),(48,50),(16,50)],fill=C['green_s']); d.rectangle((30,45,34,48),fill=C['red'])
    d.line((46,25,49,17,51,17),fill=C['ink'],width=2); d.point((51,17),fill=C['metal'])


def back_tractor(d, phase):
    wheel(d,12,48,8,phase); wheel(d,52,48,8,phase)
    d.polygon([(15,37),(19,28),(23,24),(41,24),(45,28),(49,37),(47,45),(17,45)],fill=C['ink'])
    d.polygon([(18,36),(22,29),(25,26),(39,26),(42,29),(46,36),(44,42),(20,42)],fill=C['green'])
    d.rectangle((23,28,41,35),fill=C['glass_s']); d.rectangle((25,29,39,34),fill=C['glass']); d.rectangle((26,29,30,33),fill=C['glass_l'])
    d.rectangle((20,23,44,26),fill=C['ink']); d.rectangle((22,22,42,24),fill=C['red']); d.rectangle((25,22,39,23),fill=C['red_l'])
    d.rectangle((20,37,44,44),fill=C['ink']); d.rectangle((22,38,42,42),fill=C['red']); d.rectangle((25,39,39,40),fill=C['red_l'])
    d.rectangle((22,39,25,42),fill="#f5d98b"); d.rectangle((39,39,42,42),fill="#f5d98b")
    d.rectangle((29,40,35,45),fill=C['metal']); d.rectangle((31,41,33,44),fill=C['shadow'])
    d.rectangle((30,45,34,49),fill=C['green_s']); d.line((18,27,14,19,12,19),fill=C['ink'],width=2)


def car_sprite(d, phase):
    # Side-profile Polski hatchback, deliberately brighter and more detailed than the old blocks.
    wheel(d,17,47,7,phase); wheel(d,47,47,7,phase)
    d.polygon([(4,39),(8,34),(18,32),(24,23),(31,18),(43,19),(51,29),(58,32),(61,39),(59,45),(53,47),(51,41),(45,39),(39,41),(24,41),(21,47),(12,47),(10,42),(5,42)],fill=C['ink'])
    d.polygon([(7,38),(11,35),(20,34),(26,25),(32,20),(42,21),(49,30),(56,33),(58,38),(57,42),(52,42),(50,39),(45,37),(40,39),(24,39),(21,42),(13,42),(11,39)],fill=C['red'])
    d.polygon([(26,25),(32,21),(41,22),(47,30),(39,29),(29,29)],fill=C['glass_s'])
    d.polygon([(29,25),(33,22),(39,23),(39,28),(29,28)],fill=C['glass']); d.rectangle((33,22,35,23),fill=C['glass_l'])
    d.polygon([(40,22),(42,22),(47,29),(41,29)],fill=C['glass'])
    d.rectangle((8,35,19,36),fill=C['red_l']); d.rectangle((22,32,46,34),fill=C['red_l'])
    d.rectangle((4,37,8,40),fill=C['light']); d.rectangle((55,36,59,39),fill="#d95d50")
    d.rectangle((28,38,36,39),fill=C['red_s']); d.point((31,38),fill=C['metal'])
    d.rectangle((12,40,21,42),fill=C['ink']); d.rectangle((41,40,51,42),fill=C['ink'])
    d.line((25,29,22,34),fill=C['red_s'],width=1); d.rectangle((49,31,53,33),fill=C['red_s'])


def main():
    rows=[("tractor_side",side_tractor,"side-right"),("tractor_front",front_tractor,"front"),("tractor_back",back_tractor,"rear"),("car",car_sprite,"side-3/4")]
    atlas=Image.new("RGBA",(CELL*4,CELL*len(rows)),(0,0,0,0))
    for row,(name,draw_fn,view) in enumerate(rows):
        for frame in range(4):
            tile=Image.new("RGBA",(CELL,CELL),(0,0,0,0)); draw_fn(ImageDraw.Draw(tile),frame); atlas.alpha_composite(tile,(frame*CELL,row*CELL))
    atlas.save(OUT,optimize=True)
    meta={"cell":CELL,"rows":{name:{"row":i,"view":view,"frames":["wheel1","wheel2","wheel3","wheel4"] if name.startswith("tractor") else ["idle1","idle2","idle3","idle4"]} for i,(name,_,view) in enumerate(rows)}}
    META.write_text(json.dumps(meta,indent=1)+"\n",encoding="utf-8")
    print(f"vehicle pixel atlas: {atlas.width}x{atlas.height}, rows={','.join(x[0] for x in rows)}")

if __name__=="__main__": main()
