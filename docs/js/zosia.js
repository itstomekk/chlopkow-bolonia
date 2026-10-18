/* ZOSIA — lives by the forest, picks mushrooms, pushes her bike with baskets and shopping net bags.
   Her house by the forest comes later; for now she loiters ("kręci się") about 1 km north of the
   cemetery, near JAZZ W STODOLE. game.js WANDER.zosia moves her around npc.home. */
'use strict';
(() => {
  const ID = 'zosia';
  // Cemetery POI (2558, 3616); 1 km north at 2 px per metre = y - 2000. JAZZ W STODOLE is at (2892, 1758);
  // nudged a little east toward it but kept outside its 140 px area: target (2600, 1616), ~325 px from JAZZ.
  const CEMETERY = Object.freeze({ x: 2558, y: 3616 }), NORTH_PX = 2000, EAST_PX = 42, SEARCH_RADIUS = 220;
  const CLEARANCE = [[0, 0], [-24, 0], [24, 0], [0, -18], [0, 18], [-18, -12], [18, -12], [-18, 12], [18, 12]];
  const DIALOGUE = {
    pl: [
      'Dzień dobry! Zosia jestem, mieszkam tam pod lasem.',
      'Rowerem wszędzie jeżdżę. Koszyk z przodu na grzyby, siatki na zakupy.',
      'Grzyby? Las wie, gdzie rosną. Ja tylko wiem, kiedy iść.',
    ],
    en: [
      'Good morning! I am Zosia, I live over there by the forest.',
      'I go everywhere by bike. The front basket is for mushrooms, the net bags for shopping.',
      'Mushrooms? The forest knows where they grow. I only know when to go.',
    ],
  };

  function sectorAt(x, y) {
    return String.fromCharCode(65 + Math.floor(Number(x) / 512)) + (Math.floor(Number(y) / 512) + 1);
  }

  function install() {
    if (window.__zosia && window.__zosia.installed) return;
    const A = window.ARK;
    if (!A || !A.ITEMS || !Array.isArray(A.ITEMS.npcs)) return;
    const target = { x: CEMETERY.x + EAST_PX, y: CEMETERY.y - NORTH_PX };
    const reachable = window.__game && typeof window.__game.isSpawnReachable === 'function'
      ? (x, y) => window.__game.isSpawnReachable(x, y)
      : () => false;
    const others = () => A.ITEMS.npcs.filter(n => n.id !== ID);
    const clear = (x, y) => CLEARANCE.every(([dx, dy]) => !A.blocked(x + dx, y + dy))
      && others().every(n => Math.hypot(x - n.x, y - n.y) >= 72);
    const road = c => {
      const terrain = A.terrainAt(c.x, c.y);
      return terrain === 'road' || terrain === 'track';
    };
    const candidates = [];
    // Stable, bounded ordering: road/track first (she pushes a bike), then nearest to the target, then y/x.
    for (let y = target.y - SEARCH_RADIUS; y <= target.y + SEARCH_RADIUS; y += 8) {
      for (let x = target.x - SEARCH_RADIUS; x <= target.x + SEARCH_RADIUS; x += 8) {
        const d = (x - target.x) ** 2 + (y - target.y) ** 2;
        if (d > SEARCH_RADIUS ** 2) continue;
        candidates.push({ x, y, priority: road({ x, y }) ? 0 : 1, d });
      }
    }
    candidates.sort((a, b) => a.priority - b.priority || a.d - b.d || a.y - b.y || a.x - b.x);
    const found = candidates.find(c => !A.blocked(c.x, c.y) && clear(c.x, c.y) && reachable(c.x, c.y));
    if (!found) {
      window.__zosia = { installed: false, error: 'No reachable clear position north of the cemetery' };
      console.warn('ZOSIA: no reachable clear position north of the cemetery; no unsafe fallback placed.');
      return;
    }

    A.ITEMS.npcs = A.ITEMS.npcs.filter(n => n.id !== ID);
    const home = { x: found.x, y: found.y };
    A.ITEMS.npcs.push({ id: ID, x: found.x, y: found.y, face: 'down', fixed: true, home });
    A.HOOKS.npcTalk.push(id => {
      if (id !== ID) return false;
      A.say(ID, DIALOGUE[A.LANG === 'en' ? 'en' : 'pl']);
      return true;
    });

    window.__zosia = {
      installed: true,
      id: ID,
      target: { ...target },
      home: { ...home },
      position() {
        const npc = A.ITEMS.npcs.find(n => n.id === ID);
        return npc ? { x: npc.x, y: npc.y, face: npc.face, sector: sectorAt(npc.x, npc.y), terrain: A.terrainAt(npc.x, npc.y), reachable: reachable(npc.x, npc.y) } : null;
      },
    };
  }

  window.__zosia = window.__zosia || { installed: false };
  let scheduled = false;
  const ready = () => { if (!scheduled) { scheduled = true; queueMicrotask(install); } };
  window.addEventListener('ark-ready', ready, { once: true });
  if (window.ARK) ready();
})();
