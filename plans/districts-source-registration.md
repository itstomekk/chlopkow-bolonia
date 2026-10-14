# Districts source registration

Companion to `docs/data/districts.json`. Records how the user-supplied district map was turned into approximate WGS84 polygons, what evidence supports the placement, and where it is weak.

## Source

- File: `image_5971c1.png`, 2048 x 2048, supplied by Tomek in chat. Original path `C:\Users\Lenovo\AppData\Roaming\Hermes\composer-images\image_5971c1.png`.
- Local copy: `references/districts/image_5971c1.png` (the `references/` tree is gitignored; never publish or upload it).
- Content: an aerial/satellite-style photo (provider and date unknown) with hand-added translucent colored areas and text labels, titled "HISTORYCZNE DZIELNICE CHŁOPKOWA".
- Meaning: approximate, locally customary areas. The user says the names are in habitual use. The title word "historyczne" does not verify any history; no origin or date is claimed anywhere in the data. These are not official administrative boundaries.

## Districts extracted (exact displayed text)

| id | name | displayed as | tint | method | confidence |
|---|---|---|---|---|---|
| wies | Wieś | WIEŚ | mint | HSV hue segmentation | medium |
| dolina | Dolina | DOLINA | teal | HSV hue segmentation | medium |
| chlopkow-za-rzeka | Chłopków za Rzeką | CHŁOPKÓW ZA RZEKĄ | pale cyan | hue segmentation, low saturation, plus the saturated teal strip on its north edge | medium-low |
| kolonia-od-lasu | Kolonia od Lasu | KOLONIA OD LASU | green | hue segmentation; part runs under the title text | medium |
| kolonia-od-szpak | Kolonia od Szpak | KOLONIA OD SZPAK | blue | hue segmentation | medium |
| adamowo | Adamowo | ADAMOWO | yellow-green | hue segmentation | medium |
| peryczowka | Peryczówka | PERYCZÓWKA | orange | hue segmentation | medium |
| wapnica | Wapnica | wapnica (lowercase) | pale oval, faint outline | traced by eye on zoomed crops, one correction after overlay check (about +-30 source px) | low |
| sulow | Sułów | sułów (lowercase) | slate gray-blue veil | hue/saturation segmentation; part under the title text | low-medium |

Diacritics were read letter by letter from 3x crops of each label. `name` is the label in normal Polish capitalization; `displayedAs` keeps the source casing. The two lowercase labels (`wapnica`, `sułów`) are drawn like the small landmark labels but have their own shaded area, so they are included as areas. Whether Sułów is a district of the village or a neighbouring place is not established by the source (OSM has a `place=locality` "Sułów-Gajówka" at the matching spot); the parent may choose to drop it.

Labels with no shaded area of their own are NOT districts and are not in `districts[]`. They are listed in `labelOnlyFeatures[]`: szkoła, ZAGUMIENIE (a green highlighted strip; extent not traced), folwark, bagno, and the "duńcy" arrow (points off-image to the west/south-west). The landmark labels sklep, wiatrak, cmentarz, kościół are used as registration anchors.

## Schema

```
{ version: 1, approximate: true, note,
  source: { kind: 'user-supplied-local-map', filename, width, height, localCopy, title, provenance,
            registration: { model, gameXY, scaleGamePxPerSrcPx, tx, ty, metersPerSourcePx, linear{...},
                            sourceExtentLatLon, gameBboxInSourcePx, anchors[], residualRmsM, leaveOneOutM,
                            heldOutChecks[], uncertainty, imageryVerification } },
  districts: [ { id, name, displayedAs, color, polygon, label, sourcePolygon, sourceLabel,
                 method, confidence, fractionInsideGameBbox } ],
  labelOnlyFeatures: [ { name, sourcePoint, lon, lat, kind } ] }
```

- One ring per district, no holes, no multipolygons. Rings are implicitly closed (first point not repeated); winding is not normalised.
- `polygon` is `[lon,lat]`, `label` is `[lon,lat]`; `sourcePolygon` and `sourceLabel` are `[x,y]` pixels of the 2048 image.
- `label` is the text-label centre when it lies well inside the shape (adamowo, dolina, kolonia-od-lasu, wapnica, sulow), otherwise the pole of inaccessibility (deepest interior point). Every label is strictly inside its polygon (checked).
- `color` is the label/tint colour from the source (wapnica and sulow are approximations of pale/slate tints).
- Extra top-level `labelOnlyFeatures` and per-district `method`, `confidence`, `displayedAs`, `fractionInsideGameBbox` are additions to the requested schema; a strict reader should ignore unknown keys.
- Polygons have 21-66 vertices, simplified at 3 source px (about 7 m). Tiny overlaps (<= 36 source px, about 200 m2) remain between wies/chlopkow-za-rzeka, dolina/chlopkow-za-rzeka and adamowo/peryczowka; the plugin should resolve overlap deterministically (list order is fine).
- Uncovered land stays uncovered: the polygons follow the tinted shapes only; nothing was extended to fill gaps (the church label itself sits in a gap between Adamowo, Za Rzeką and Szpak).

## Registration

Model: north-up similarity (uniform scale + translation, rotation fixed at 0), in `osm/geo.py` art pixels, then `geo.to_latlon`.

```
gameX = 4.779425 * x - 1524.828
gameY = 4.779425 * y - 1430.143          # 2.3897 m per source pixel (2048 px ~ 4.89 km)
lon   = 22.847408 + 3.5079e-5 * x        # linear equivalent (equirectangular, same as geo.P)
lat   = 52.291467 - 2.1612e-5 * y
```

Source extent: lat 52.2472-52.2915, lon 22.8474-22.9193. The current game bbox (52.252935,22.8586,52.285,22.896352) occupies source x 319-1395, y 299-1783, so the game covers the middle of the source. Dolina is 23% inside the game bbox, Sułów 49%, Kolonia od Szpak 64%, Peryczówka 76%, Wapnica 85%; the others are fully or almost fully inside (see `fractionInsideGameBbox`). Parts outside the bbox are kept in the data on purpose.

### Anchors (label centre in source px -> independent coordinate)

| Anchor | Source px | Reference | Residual E / N (m) |
|---|---|---|---|
| sklep | 549,1136 | OSM shop node, 52.26694 22.86750 | -57.0 / -2.9 |
| wiatrak | 750,1093 | OSM windmill "Koźlak", 52.26829 22.87398 | -18.0 / -48.8 |
| cmentarz | 858,1067 | OSM cemetery polygon centroid, 52.26855 22.87723 | +18.6 / -16.1 |
| kościół | 888,1402 | OSM church building centroid, 52.26055 22.87773 | +56.4 / +67.8 |

Label centres were measured on the pixels (white text boxes detected by colour), not read by eye. Residual RMS 60 m; leave-one-out error 133 m (sklep), 73 m (wiatrak), 33 m (cmentarz), 160 m (kościół). Residuals of this size are expected because a label sits next to its feature, not exactly on it.

### Checks that were not used in the fit

- Sułów label vs OSM `place=locality` Sułów-Gajówka: 162 m apart.
- Wapnica: the game's own "Wapnica" gravel POI (52.27373, 22.86420) lands inside the wapnica oval, about 110 m from its label.
- OSM points land in plausible districts: village node Chłopków -> Wieś; shop and kapliczka -> Wieś; football pitch -> Adamowo; Chłopków-Kolonia node and the Kolonia bus stops -> Peryczówka; PPM Strzelectwo range -> Wapnica; "Jazz w stodole" -> Kolonia od Lasu.
- Of 357 OSM buildings in the game area, 294 (82%) fall inside the seven settled districts, which cover about 24% of the source frame (all nine areas: 32%). Shifting the whole registration by 100 m changes this little (maximum 320 around +100 m E/S), by 300 m it drops to roughly 240-250, so the translation is supported to about +-150 m. This is a weak test (buildings cluster in the village) and not a precise calibration.

## Not achieved, and limitations

- **No registration against imagery.** Matching the source photo to Esri World Imagery (the same imagery the repo already uses: SIFT, template matching, gradient correlation, dark/forest-mask correlation at several scales and rotations, with the prior and without) never produced a consistent peak. Likely causes: different imagery date or provider, 30%+ of the pixels covered by tints and labels, low photo resolution. The map therefore rests on four label-to-landmark anchors that sit within a 310 x 270 px block in the middle of the 2048 px frame.
- **Rotation is assumed zero.** A free-rotation fit gives 3.8 degrees at the same residual (rotation is unconstrained by four close anchors). Using it instead would move vertices by 85 m on average and up to about 200 m (largest for Sułów, Kolonia od Szpak, Kolonia od Lasu, Peryczówka). North-up screenshot assumption is the simplest and is consistent with the shop/church/windmill/cemetery geometry, but not proven.
- **Scale is extrapolated** from a small baseline, so the far edges (Sułów, Kolonia od Szpak, Dolina, eastern Peryczówka) carry the largest error. Expect roughly 60-100 m typical, up to about 150-200 m at the edges: good enough for "which area am I in" at the width of a district, not for a street or property line.
- **Edges are tint edges**, found by colour segmentation, then smoothed (about 8 source px blur, about 19 m) and simplified. Where a tint meets dark forest or the title lettering, the boundary is uncertain. Wapnica (faint pale oval) and Sułów (slate veil) are the least reliable shapes.
- Chłopków za Rzeką includes the teal strip along its north edge that the colour classifier first assigned to Dolina; this was decided by looking at crops, not by data.
- Do not present these shapes as official, surveyed, or historically verified. No quest, discovery progress, or terrain logic should depend on them.

## Parent integration checks

The runtime dataset deliberately omits the machine's absolute source path; the original remains recorded privately in this note. The parent verified original/copy SHA equality, polygon vertex transforms (maximum difference 0.127 art pixels from JSON rounding), and a recalculated anchor RMS of 59.9 m. A side-by-side local review is in `asset-review/districts/source-game-overlay.png`; colors and numbered pins are review-only. Runtime draws names and a current-area badge. Visual area-scale plausibility is NOT independent imagery registration or a survey. The data is a tentative placement requiring Tomek's local boundary review.

## Rebuild details

Working files were kept in the Hermes scratch directory (not in the repo). The pipeline was: label text colour sampling -> HSV hue windows per district -> morphological close/open -> component nearest the label -> fill holes -> 8 px blur threshold -> polygon simplify (3 px) -> similarity transform above -> `geo.to_latlon`. Redo the registration if a better anchor set (for example a road junction or the school position confirmed on the ground) becomes available: only `tx`, `ty` and scale in this document and the `polygon`/`label` values in the JSON need recomputing; `sourcePolygon` and `sourceLabel` stay valid.
