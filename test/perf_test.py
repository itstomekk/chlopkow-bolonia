"""Repeatable runtime benchmark for the newest Arek game systems.

Run with: python test/perf_test.py [URL]
Set ARK_URL to override the default URL. Uses Chromium CDP 4x CPU throttling.
"""
import os
import sys
import time
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html")
DURATION_MS = 5000

with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context(viewport={"width": 1280, "height": 720})
    page = context.new_page()
    cdp = context.new_cdp_session(page)
    cdp.send("Emulation.setCPUThrottlingRate", {"rate": 4})
    cdp.send("Performance.enable")
    load_started = time.perf_counter()
    page.goto(URL, wait_until="load")
    page.wait_for_function("window.ARK && window.__game", timeout=60000)
    ready_ms = (time.perf_counter() - load_started) * 1000
    page.evaluate("localStorage.clear()")
    page.reload(wait_until="load")
    page.wait_for_function("window.ARK && window.__game", timeout=60000)
    page.keyboard.press("KeyN")
    page.locator("#player-name-input").fill("Perf")
    page.locator("#player-name-submit").click()
    page.wait_for_function("__game.scene === 'play'", timeout=30000)
    page.wait_for_function("window.__worldLife && __worldLife.animals.length > 0", timeout=30000)

    def measure(label, setup, walking=False):
        setup()
        if walking:
            page.keyboard.down("ArrowRight")
        try:
            result = page.evaluate("""async duration => {
              const times = []; let previous = 0;
              await new Promise(resolve => {
                const start = performance.now();
                function frame(now) {
                  if (previous) times.push(now - previous);
                  previous = now;
                  if (now - start < duration) requestAnimationFrame(frame); else resolve();
                }
                requestAnimationFrame(frame);
              });
              times.sort((a,b) => a-b);
              const sum = times.reduce((a,b) => a+b, 0);
              return {frames: times.length, meanMs: sum / Math.max(1,times.length),
                p95Ms: times[Math.min(times.length-1, Math.floor(times.length*.95))] || 0};
            }""", DURATION_MS)
        finally:
            if walking:
                page.keyboard.up("ArrowRight")
        metrics = cdp.send("Performance.getMetrics").get("metrics", [])
        heap = next((m["value"] / 1048576 for m in metrics if m["name"] == "JSHeapUsedSize"), None)
        result["heapMiB"] = round(heap, 1) if heap is not None else None
        result["label"] = label
        print(f"{label}: frames={result['frames']} mean={result['meanMs']:.2f}ms p95={result['p95Ms']:.2f}ms heap={result['heapMiB']}MiB")
        return result

    centre = lambda: page.evaluate("ARK.teleport(ARK.MAP.spawn.x, ARK.MAP.spawn.y)")
    field = lambda: page.evaluate("ARK.teleport(ARK.MAP.bales[0].x, ARK.MAP.bales[0].y)")
    results = [measure("village centre", centre), measure("field with bales", field), measure("continuous walking", centre, True)]

    # Capture a short V8 CPU profile at the bale site; summarize sampled self-time by function.
    field()
    cdp.send("Profiler.enable")
    cdp.send("Profiler.start")
    page.wait_for_timeout(5000)
    profile = cdp.send("Profiler.stop")["profile"]
    nodes = {n["id"]: n for n in profile["nodes"]}
    samples = profile.get("samples", [])
    deltas = profile.get("timeDeltas", [])
    totals = {}
    for node_id, delta in zip(samples, deltas):
        node = nodes[node_id]
        frame = node.get("callFrame", {})
        name = frame.get("functionName") or "(anonymous)"
        location = f"{frame.get('url', '').rsplit('/', 1)[-1]}:{frame.get('lineNumber', -1) + 1}"
        key = f"{name}@{location}"
        totals[key] = totals.get(key, 0) + delta
    top = sorted(totals.items(), key=lambda x: x[1], reverse=True)[:12]
    print("CPU profile top sampled functions (bales, 5s):", ", ".join(f"{n}={us/1000:.1f}ms" for n, us in top))
    print(f"page ready: {ready_ms:.0f}ms; cpu throttle: 4x")
    browser.close()
