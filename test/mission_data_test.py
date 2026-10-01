"""D02 — static contract validation for authored missions (docs/missions.json).

Run: python test/mission_data_test.py

Data contract only, no runtime: missions.json is a static file served by
GitHub Pages. This suite drives the small validator in mission_validator.py
against the *current* generated artifacts (docs/items.json, docs/map.json,
osm/chlopkow.json) so a map rebuild cannot silently break an authored mission.
"""
import json
import math
import sys
import unittest
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "test"))

from mission_validator import validate_missions  # noqa: E402

Image.MAX_IMAGE_PIXELS = None

ITEMS = json.loads((ROOT / "docs/items.json").read_text(encoding="utf-8"))
MAP = json.loads((ROOT / "docs/map.json").read_text(encoding="utf-8"))
OSM = json.loads((ROOT / "osm/chlopkow.json").read_text(encoding="utf-8"))
BUILDINGS = {
    str(el["id"]): el["geometry"]
    for el in OSM["elements"]
    if el.get("type") == "way" and "building" in el.get("tags", {}) and el.get("geometry")
}

# The documented example contract: one outdoor checkpoint at a home's quiz board.
PILOT = {
    "id": "home-example",
    "steps": [{"id": "visit", "kind": "interact", "anchor": {"boardSpot": "house01"}}],
}
STEP = PILOT["steps"][0]


def load_missions():
    return json.loads((ROOT / "docs/missions.json").read_text(encoding="utf-8"))


class InvalidContractTest(unittest.TestCase):
    def errors(self, missions, items=ITEMS, map_data=MAP, buildings=BUILDINGS):
        return validate_missions(missions, items, map_data, buildings)

    def test_duplicate_mission_ids_rejected(self):
        missions = [PILOT, PILOT]
        errors = self.errors(missions)
        self.assertTrue(any("duplicate" in e.lower() and "home-example" in e for e in errors), errors)

    def test_duplicate_step_ids_rejected(self):
        missions = [{
            "id": "m1",
            "steps": [
                {"id": "s1", "kind": "interact", "anchor": {"boardSpot": "house02"}},
                {"id": "s1", "kind": "interact", "anchor": {"boardSpot": "house03"}},
            ],
        }]
        errors = self.errors(missions)
        self.assertTrue(any("duplicate" in e.lower() and "s1" in e for e in errors), errors)

    def test_missing_board_anchor_rejected(self):
        missions = [{
            "id": "m1",
            "steps": [{"id": "s1", "kind": "interact", "anchor": {"boardSpot": "not-a-real-spot"}}],
        }]
        errors = self.errors(missions)
        self.assertTrue(any("not-a-real-spot" in e and "board" in e.lower() for e in errors), errors)

    def test_missing_poi_anchor_rejected(self):
        missions = [{
            "id": "m1",
            "steps": [{"id": "s1", "kind": "interact", "anchor": {"poi": "nonsuch-poi"}}],
        }]
        errors = self.errors(missions)
        self.assertTrue(any("nonsuch-poi" in e and "poi" in e.lower() for e in errors), errors)

    def test_invalid_building_id_rejected(self):
        items = dict(ITEMS)
        items["boards"] = [
            dict(b, building_id="999999999") if b["spot"] == "house01" else b for b in ITEMS["boards"]
        ]
        errors = self.errors([PILOT], items=items)
        self.assertTrue(any("999999999" in e and "building" in e.lower() for e in errors), errors)

    def test_out_of_bounds_position_rejected(self):
        for pos in ({"x": MAP["w"] + 10, "y": 100}, {"x": 100, "y": MAP["h"] + 10}, {"x": -1, "y": 100}):
            missions = [{
                "id": "m1",
                "steps": [{"id": "s1", "kind": "interact", "anchor": dict(pos)}],
            }]
            errors = self.errors(missions)
            self.assertTrue(
                any("out of bounds" in e.lower() or "bounds" in e.lower() for e in errors),
                (pos, errors),
            )

    def test_broken_dependency_rejected(self):
        missions = [{
            "id": "m1",
            "steps": [
                {"id": "s1", "kind": "interact", "anchor": {"boardSpot": "house01"}},
                {"id": "s2", "kind": "interact", "anchor": {"boardSpot": "house02"}, "dependsOn": "ghost-step"},
            ],
        }]
        errors = self.errors(missions)
        self.assertTrue(any("ghost-step" in e and "depends" in e.lower() for e in errors), errors)

    def test_self_dependency_rejected(self):
        missions = [{
            "id": "m1",
            "steps": [{"id": "s1", "kind": "interact", "anchor": {"boardSpot": "house01"}, "dependsOn": "s1"}],
        }]
        errors = self.errors(missions)
        self.assertTrue(any("self" in e.lower() and "depends" in e.lower() for e in errors), errors)

    def test_unknown_step_kind_rejected(self):
        missions = [{
            "id": "m1",
            "steps": [{"id": "s1", "kind": "teleport", "anchor": {"boardSpot": "house01"}}],
        }]
        errors = self.errors(missions)
        self.assertTrue(any("teleport" in e and "kind" in e.lower() for e in errors), errors)

    def test_empty_ids_rejected(self):
        missions = [{"id": "", "steps": [{"id": "", "kind": "interact", "anchor": {"boardSpot": "house01"}}]}]
        errors = self.errors(missions)
        self.assertTrue(any("empty" in e.lower() or "id" in e.lower() for e in errors), errors)


class ValidContractTest(unittest.TestCase):
    def test_one_home_outdoor_checkpoint_passes(self):
        self.assertEqual(validate_missions([PILOT], ITEMS, MAP, BUILDINGS), [])

    def test_current_missions_file_passes_against_generated_artifacts(self):
        missions = load_missions()
        self.assertEqual(validate_missions(missions, ITEMS, MAP, BUILDINGS), [])
        self.assertEqual(len(missions), 1)
        mission = missions[0]
        self.assertEqual(len(mission["steps"]), 1)
        self.assertEqual(mission["steps"][0]["kind"], "interact")
        spot = mission["steps"][0]["anchor"]["boardSpot"]
        self.assertTrue(spot.startswith("house"), spot)
        # stable IDs are explicit strings, never array positions or display labels
        self.assertIsInstance(mission["id"], str)
        self.assertIsInstance(mission["steps"][0]["id"], str)

    def test_pilot_home_is_spawn_reachable_without_conflicting_npc(self):
        spot = load_missions()[0]["steps"][0]["anchor"]["boardSpot"]
        board = next(b for b in ITEMS["boards"] if b["spot"] == spot)
        x, y = board["x"], board["y"]
        solid = np.array(Image.open(ROOT / "docs/img/map_collide.png").convert("L")) > 64
        lab, _ = ndimage.label(~solid)
        home = lab[MAP["spawn"]["y"], MAP["spawn"]["x"]]
        win = lab[y - 3 : y + 4, x - 3 : x + 4]
        self.assertTrue((win == home).any(), f"{spot} board at {x},{y} is not connected to the spawn")
        # NPCs win interaction priority; keep the pilot clear of every NPC.
        nearest = min(math.dist((x, y), (n["x"], n["y"])) for n in ITEMS["npcs"])
        self.assertGreaterEqual(nearest, 100, f"NPC too close to {spot} board ({nearest:.0f}px)")


if __name__ == "__main__":
    unittest.main(verbosity=2)