"""Shared map geometry for osm/render_map.py and osm/place_items.py.

The game map is an equirectangular projection of BBOX at A art pixels per metre.
Hand-placed spots (venues, shrines, the village sign, quiz anchors) were originally tuned
in the first, smaller map. `legacy(x, y)` converts those old art coordinates to lat/lon
and back into the current map, so the map can be resized without re-tuning anything.
"""
import math

A = 2.0                                           # art pixels per metre
BBOX = (52.25585, 22.8586, 52.2850, 22.89292)    # minlat, minlon, maxlat, maxlon  (village + northern forest)
# 2026-09-28: extended 10% south (52.2585 -> 52.25585) and 20% east (22.8872 -> 22.89292).
# The north-west corner (maxlat, minlon) is the pixel origin and did not move, so every art coordinate stays valid.
PRE_SE_BBOX = (52.2585, 22.8586, 52.2850, 22.8872)   # the map before that extension (3896 x 5860)
LEGACY_BBOX = (52.2588, 22.8630, 52.2700, 22.8800)  # the first map (2316 x 2476 px)

# Named sites supplied for the expanded map. Keep these as coordinates, rather than
# photographic assets or guessed OSM tags, so the renderer can use procedural art.
REAL_POIS = (
    dict(key='kapliczka', name='Kapliczka', lat=52.265937, lon=22.8658023),
    dict(key='chata', name='Chata', lat=52.2669308, lon=22.8674792),
    dict(key='swietlica', name='Świetlica', lat=52.2641139, lon=22.8754946),
    dict(key='cemetery_real', name='Cmentarz', lat=52.2685251, lon=22.8772688),
    dict(key='shooting_range', name='PPM Strzelectwo', lat=52.2736642, lon=22.867767),
)

# These user-supplied coordinates refer to the immediately previous 3897x2698 map,
# not the first 2316x2476 map used by legacy_i().
PRE_EXPANSION_BBOX = (52.2585, 22.8586, 52.2707, 22.8872)
PRE_EXPANSION_ADDITIONS = dict(bus_budka=(1135, 1085), football_pitch=(2339, 1468), race_oval=(610, 2417), soltys=(1887, 1237))

MY = 110574.0


def _mx(bbox):
    return 111320 * math.cos(math.radians((bbox[0] + bbox[2]) / 2))


MX = _mx(BBOX)
W = int((BBOX[3] - BBOX[1]) * MX * A)
H = int((BBOX[2] - BBOX[0]) * MY * A)


def P(lat, lon):
    """lat/lon -> art pixels in the current map."""
    return ((lon - BBOX[1]) * MX * A, (BBOX[2] - lat) * MY * A)


def to_latlon(x, y, bbox=BBOX):
    return bbox[2] - y / (MY * A), bbox[1] + x / (_mx(bbox) * A)


def legacy(x, y):
    """Art coords of the first (legacy) map -> art coords of the current map."""
    return P(*to_latlon(x, y, LEGACY_BBOX))


def pre_expansion_i(x, y):
    """Art coords of the preceding 3897x2698 map -> current map."""
    px, py = P(*to_latlon(x, y, PRE_EXPANSION_BBOX))
    return int(round(px)), int(round(py))

def legacy_i(x, y):
    px, py = legacy(x, y)
    return int(round(px)), int(round(py))
