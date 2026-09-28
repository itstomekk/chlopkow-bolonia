"""Regression coverage for the 40-question Chłopków quiz expansion."""
import json
import math
import os
import subprocess
import sys
import unittest
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
URL = os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html")
OLD_QUESTION_COUNT = 19


def quiz_data():
    script = "const fs=require('fs'),vm=require('vm');const window={};vm.runInNewContext(fs.readFileSync('docs/js/quiz.js','utf8'),{window});process.stdout.write(JSON.stringify(window.QUIZ));"
    raw = subprocess.check_output(["node", "-e", script], cwd=ROOT, text=True)
    return json.loads(raw)


def inside_polygon(point, polygon):
    x, y = point
    inside = False
    for i, (x1, y1) in enumerate(polygon):
        x2, y2 = polygon[(i + 1) % len(polygon)]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


class QuizExpansionTest(unittest.TestCase):
    def test_quiz_pool_has_40_questions_and_keeps_old_completion_count(self):
        questions = quiz_data()
        self.assertEqual(len(questions), 40)
        self.assertEqual(len({q["id"] for q in questions}), 40)
        self.assertEqual(sum(q["spot"] == "halina" for q in questions), 1)
        self.assertEqual(sum(not q.get("optional", False) for q in questions), OLD_QUESTION_COUNT)
        for q in questions:
            for language in ("pl", "en"):
                self.assertTrue(q[language]["q"].strip(), q["id"])
                self.assertEqual(len(q[language]["a"]), 4, q["id"])
                self.assertTrue(q[language]["fact"].strip(), q["id"])
        optional = [q for q in questions if q.get("optional")]
        self.assertEqual(len(optional), 21)
        self.assertTrue(all(q.get("source", "").strip() for q in optional))

    def test_optional_question_markers_are_on_distinct_buildings_and_spread_out(self):
        questions = quiz_data()
        optional = {q["spot"] for q in questions if q.get("optional")}
        items = json.loads((ROOT / "docs/items.json").read_text(encoding="utf-8"))
        buildings = {}
        for element in json.loads((ROOT / "osm/chlopkow.json").read_text(encoding="utf-8"))["elements"]:
            if element.get("type") == "way" and "building" in element.get("tags", {}) and element.get("geometry"):
                buildings[str(element["id"])] = element["geometry"]
        sys.path.insert(0, str(ROOT / "osm"))
        from geo import P

        boards = {b["spot"]: b for b in items["boards"]}
        self.assertEqual(len(items["boards"]), 39)
        self.assertEqual(len(boards), 39)
        self.assertEqual(set(boards), {q["spot"] for q in questions if q["spot"] != "halina"})
        used_buildings = set()
        markers = []
        for spot in sorted(optional):
            board = boards[spot]
            building_id = str(board["building_id"])
            self.assertIn(building_id, buildings)
            self.assertNotIn(building_id, used_buildings)
            used_buildings.add(building_id)
            marker = board["marker"]
            polygon = [P(p["lat"], p["lon"]) for p in buildings[building_id]]
            if polygon[0] == polygon[-1]:
                polygon.pop()
            self.assertTrue(inside_polygon((marker["x"], marker["y"]), polygon), spot)
            self.assertGreaterEqual(marker["base"], max(y for _, y in polygon), spot)
            self.assertLessEqual(math.dist((marker["x"], marker["y"]), (board["x"], board["y"])), 55, spot)
            markers.append((marker["x"], marker["y"]))
        min_gap = min(math.dist(a, b) for i, a in enumerate(markers) for b in markers[i + 1 :])
        print(f"optional marker minimum separation: {min_gap:.1f} map px")
        self.assertGreaterEqual(min_gap, 100, "building choice should keep new markers reasonably spread")

    def test_each_optional_doorway_opens_its_question_and_old_count_still_completes_quiz(self):
        questions = quiz_data()
        old_required_ids = {q["id"] for q in questions if not q.get("optional", False)}
        optional_spots = {q["spot"] for q in questions if q.get("optional")}
        self.assertEqual(len(optional_spots), 21)
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 720})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(URL)
            page.evaluate("localStorage.clear()")
            page.reload()
            page.wait_for_function("window.__game && window.__features")
            page.keyboard.press("KeyN")
            if page.locator("#player-name-input").count():
                page.locator("#player-name-input").fill("Quiz Test")
                page.locator("#player-name-submit").click()
            page.wait_for_function("__game.scene === 'play'")
            boards = page.evaluate("__game.ITEMS.boards")
            for board in boards:
                if board["spot"] not in optional_spots:
                    continue
                page.evaluate(f"__game.P.x={board['x']};__game.P.y={board['y']}")
                page.keyboard.press("Enter")
                page.wait_for_function("!!(__features.QZ && __features.QZ.q)")
                self.assertEqual(page.evaluate("__features.QZ.q.spot"), board["spot"])
                slot = page.evaluate("__features.QZ.order.indexOf(__features.QZ.q.ok)")
                page.keyboard.press(f"Digit{slot + 1}")
                page.wait_for_timeout(80)
                page.keyboard.press("Space")
                page.wait_for_timeout(300)
                page.keyboard.press("Space")
                page.wait_for_timeout(100)
            page.evaluate(f"__game.Q.quiz=Object.fromEntries({json.dumps(sorted(old_required_ids))}.map(id=>[id,1]));__game.Q.halina=0")
            halina = page.evaluate("__game.ITEMS.npcs.find(n=>n.id==='halina')")
            page.evaluate(f"__game.P.x={halina['x']};__game.P.y={halina['y']+18}")
            page.keyboard.press("Enter")
            page.wait_for_timeout(250)
            self.assertEqual(page.evaluate("__game.Q.halina"), 2)
            self.assertFalse(errors, errors)
            browser.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
