"""Fast regression check for the procedural OSM forest tree mix."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
map_data = json.loads((ROOT / "docs/map.json").read_text(encoding="utf-8"))
stats = map_data.get("tree_stats", {})
forest = map_data.get("forest_tree_stats", {})
assert len(stats) >= 3, f"expected at least three tree types, got {stats}"
assert set(forest) == {"conifer", "oak", "deciduous"}, f"missing forest tree types: {forest}"
assert forest["conifer"] > forest["oak"] > forest["deciduous"] > 0, f"unexpected forest mix: {forest}"
print(f"trees: PASS (all={stats}; forest={forest})")
