# Wapnica ground sprite

`ground.png` is a top-down pixel-art ground decal for the Chłopków Bolonia map, generated with GPT Image and processed by `process.py`.

- Source: `source_gpt_image.png`, generated with `gpt-image-2-medium` via OpenAI Codex OAuth on 2026-10-05. Style references: `gen/lm_shrine_stone.png` and `gen/lm_cross_iron.png`; geographic cue: Esri World Imagery crop of the roadside scrub/rubble feature.
- Processing: magenta chroma-key removal; BOX reduction to 160×84; no-dither 16-colour quantization; nearest-neighbour 15° clockwise rotation; nearest-neighbour 2× output. No smoothing.
- Constraints: no Wapnica sign, no long internal tire rut/path line, no road inside the decal. The road remains a separate map layer.
- The rendered-site outline in `osm/local_features.json` is a local visual approximation from imagery, not a surveyed/legal boundary.

Rebuild the generated decal from repo root with `python gen/wapnica/process.py`.
