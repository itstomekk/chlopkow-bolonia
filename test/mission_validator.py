"""D02 — static validator for authored mission data.

Contract (small and explicit, no runtime):
    docs/missions.json        -> list of mission objects
    mission                   -> {"id": str, "steps": [...]}
    step                      -> {"id": str, "kind": "interact", "anchor": {...}}
    anchor                    -> exactly one of:
                                   {"boardSpot": spot}   spot = quiz board spot in docs/items.json
                                   {"poi": key}          key  = page POI/landmark in docs/map.json
                                   {"x": int, "y": int}  explicit map pixel position
    optional step field       -> "dependsOn": step id within the same mission

Stable IDs are explicit strings authored in missions.json, independent of
array position or display label. Validate against the *current* generated
artifacts (docs/items.json, docs/map.json, osm/chlopkow.json building ways),
so a map rebuild that breaks an anchor fails loudly here.

validate_missions(missions, items, map_data, buildings) -> list of error
strings ([] = valid). Each context argument is a loaded dict, or a path
(string/Path) to a JSON file to load.
"""
import json
from pathlib import Path

KINDS = ("interact",)


def _ctx(value):
    return json.loads(Path(value).read_text(encoding="utf-8")) if isinstance(value, (str, Path)) else value


def _building_ids(osm_data):
    return {
        str(el["id"]): el["geometry"]
        for el in osm_data.get("elements", [])
        if el.get("type") == "way" and "building" in el.get("tags", {}) and el.get("geometry")
    }


def validate_missions(missions, items, map_data, buildings):
    """Return a list of validation errors (empty list means valid)."""
    errors = []
    if not isinstance(missions, list):
        return ["missions.json must be a JSON list of mission objects"]

    items = _ctx(items)
    map_data = _ctx(map_data)
    buildings = _ctx(buildings)
    if isinstance(buildings, dict):
        geometries = buildings
    else:
        geometries = _building_ids(buildings)

    boards = {b["spot"]: b for b in items.get("boards", [])}
    poi_keys = {p["key"] for p in map_data.get("pois", [])} | {p["key"] for p in map_data.get("landmarks", [])}
    w, h = map_data.get("w"), map_data.get("h")

    seen_mission_ids = {}
    for mission in missions:
        if not isinstance(mission, dict):
            errors.append("mission entry is not an object")
            continue
        mid = mission.get("id")
        if not isinstance(mid, str) or not mid.strip():
            errors.append("mission has an empty or missing id")
            continue
        seen_mission_ids[mid] = seen_mission_ids.get(mid, 0) + 1

        steps = mission.get("steps")
        if not isinstance(steps, list) or not steps:
            errors.append(f"mission {mid!r}: steps must be a non-empty list")
            continue

        for field, what in (("title", "title"), ("desc", "description")):
            v = mission.get(field)
            if v is not None:
                if not isinstance(v, dict) or not isinstance(v.get("pl"), str) or not v["pl"].strip()                         or not isinstance(v.get("en"), str) or not v["en"].strip():
                    errors.append(f"mission {mid!r}: {what} must be {{pl, en}} non-empty strings")

        step_ids = set()
        for step in steps:
            if not isinstance(step, dict):
                errors.append(f"mission {mid!r}: step is not an object")
                continue
            sid = step.get("id")
            if not isinstance(sid, str) or not sid.strip():
                errors.append(f"mission {mid!r}: step has an empty or missing id")
                continue
            if sid in step_ids:
                errors.append(f"mission {mid!r}: duplicate step id {sid!r}")
            step_ids.add(sid)

        for step in steps:
            if not isinstance(step, dict):
                continue
            sid = step.get("id", "?")
            label = f"mission {mid!r} step {sid!r}"

            kind = step.get("kind")
            if kind not in KINDS:
                errors.append(f"{label}: unknown kind {kind!r} (allowed: {KINDS})")

            anchor = step.get("anchor")
            if not isinstance(anchor, dict):
                errors.append(f"{label}: missing anchor object")
                continue
            kinds = [k for k in anchor if k in ("boardSpot", "poi", "x", "y")]
            if kinds != ["boardSpot"] and kinds != ["poi"] and kinds != ["x", "y"]:
                errors.append(f"{label}: anchor must be exactly one of boardSpot / poi / x+y, got {sorted(anchor)}")
                continue

            x = y = None
            if "boardSpot" in anchor:
                spot = anchor["boardSpot"]
                board = boards.get(spot)
                if board is None:
                    errors.append(f"{label}: missing board anchor — no quiz board spot {spot!r} in items.json")
                    continue
                building_id = board.get("building_id")
                if building_id is not None and str(building_id) not in geometries:
                    errors.append(f"{label}: board {spot!r} building {building_id} is not in osm/chlopkow.json")
                x, y = board.get("x"), board.get("y")
            elif "poi" in anchor:
                key = anchor["poi"]
                if key not in poi_keys:
                    errors.append(f"{label}: missing POI anchor — no poi/landmark key {key!r} in map.json")
                    continue
                p = next((p for p in map_data.get("pois", []) + map_data.get("landmarks", []) if p["key"] == key), None)
                if p:
                    x, y = p.get("x"), p.get("y")
            else:
                x, y = anchor.get("x"), anchor.get("y")

            if x is not None and y is not None:
                if not (isinstance(x, (int, float)) and isinstance(y, (int, float))):
                    errors.append(f"{label}: anchor position must be numeric x/y")
                elif not (0 <= x < w and 0 <= y < h):
                    errors.append(f"{label}: anchor position ({x},{y}) is out of bounds for {w}x{h} map")

            dep = step.get("dependsOn")
            if dep is not None:
                if not isinstance(dep, str) or not dep.strip():
                    errors.append(f"{label}: empty dependsOn")
                elif dep == sid:
                    errors.append(f"{label}: dependsOn references itself")
                elif dep not in step_ids:
                    errors.append(f"{label}: broken dependency — dependsOn {dep!r} is not a step of this mission")

    for mid, count in seen_mission_ids.items():
        if count > 1:
            errors.append(f"duplicate mission id {mid!r} appears {count} times")
    return errors