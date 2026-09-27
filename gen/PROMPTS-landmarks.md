# Generated village house and wayside landmarks

Generated with Hermes image generation via OpenAI Codex, model `gpt-image-2-medium`; output metadata reported quality `low`. Original chat photos remain outside the repository and must never be committed.

## Source assets

- `lm_house_generic.png` — one composite, generic rural house; references `image_7d8047.png`, `image_a2bdbd.png`, `lm_shop.png`, and `lm_church.png`. It is not intended to represent any exact photographed house.
- `lm_cross_iron.png` — ornate openwork iron cross with flower clusters; source `image_b93a3d.png`.
- `lm_shrine_stone.png` — stepped, weathered stone-and-brick shrine with pointed niches; source `image_4a2c1b.png`.
- `lm_shrine_white.png` — white shrine with red brick niche trim and Mary; source `image_d02578.png`.
- `lm_shrine_fenced.png` — fenced chapel with colored ribbons; source `image_fcbdda.png`.
- `lm_village_sign.png` — two-panel entrance sign prepared by `build_village_sign.py` from the GPT-generated draft `lm_village_sign_raw.png`; the script keys/crops the art and overlays exact hand-drawn bitmap lettering `CHŁOPKÓW`. The original reference photo is not copied here.

All generated sprites use a magenta key background. `osm/render_map.py` keys, crops, nearest-neighbor scales, positions, and composites them into the y-sorted object layer.

## Approximate placements

The chat photos contain no GPS metadata. These are approximate positions at OSM road junctions, not verified real-world locations:

| Sprite | Map pixel (x, y) | Footprint/width |
|---|---:|---:|
| `cross_iron` | 1643, 628 | 42 px |
| `shrine_stone` | 1705, 1284 | 68 px |
| `shrine_white` | 1457, 2358 | 68 px |
| `shrine_fenced` | 558, 959 | 78 px |
| `house_generic` | OSM way 1095382322 | 90 px |

If Tomek provides actual shrine locations or identifies which real house each photo depicts, move only the matching asset; keep the other house photos as unassigned references until then.
