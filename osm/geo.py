"""Shared map geometry for osm/render_map.py and osm/place_items.py.

The game map is an equirectangular projection of BBOX at A art pixels per metre.
Hand-placed spots (venues, shrines, the village sign, quiz anchors) were originally tuned
in the first, smaller map. `legacy(x, y)` converts those old art coordinates to lat/lon
and back into the current map, so the map can be resized without re-tuning anything.
"""
import math

A = 2.0                                           # art pixels per metre
BBOX = (52.2585, 22.8586, 52.2707, 22.8872)       # minlat, minlon, maxlat, maxlon  (village + Kolonia, ~1.95 x 1.35 km)
LEGACY_BBOX = (52.2588, 22.8630, 52.2700, 22.8800)  # the first map (2316 x 2476 px)

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


def legacy_i(x, y):
    px, py = legacy(x, y)
    return int(round(px)), int(round(py))
