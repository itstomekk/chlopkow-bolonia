/* BOSIOWA — the mushroom queen and businesswoman, by the buildings next to Kasia's home. */
'use strict';
(() => {
  const ID = 'bosiowa';
  // Kasia's home is items.json (3699, 4952); the nearest buildings are the yard at (3744, 4910)
  // and (3683-3771, 4830-4853). Stand just south-east of that yard, beside the buildings.
  const KASIA_HOME = Object.freeze({ x: 3699, y: 4952 }), TARGET = Object.freeze({ x: 3790, y: 4950 }), SEARCH_RADIUS = 140;
  const DIRECTION_FRAMES = Object.freeze({
    down: 'walk_down', up: 'walk_up', left: 'walk_left', right: 'walk_right',
    down_right: 'walk_right', down_left: 'walk_down', up_right: 'walk_up', up_left: 'walk_left',
  });
  const CLEARANCE = [[0, 0], [-24, 0], [24, 0], [0, -18], [0, 18], [-18, -12], [18, -12], [-18, 12], [18, 12]];
  const DIALOGUE = {
    pl: [
      'Dzień dobry! Bosiowa, królowa pieczarek. Tak, ta Bosiowa.',
      'Moje pieczarki jadą w świat. Ta skrzynka to tylko próbka towaru.',
      'Kasia zbiera pieczarki do koszyczka? Urocze. U mnie rosną na zamówienie.',
    ],
    en: [
      'Good day! Bosiowa, the mushroom queen. Yes, that Bosiowa.',
      'My mushrooms travel far. This crate is just a sample.',
      'Kasia picks mushrooms into a little basket? Cute. Mine grow to order.',
    ],
  };

  function sectorAt(x, y) {
    return String.fromCharCode(65 + Math.floor(Number(x) / 512)) + (Math.floor(Number(y) / 512) + 1);
  }

  function directionFrame(dir) {
    return DIRECTION_FRAMES[dir] || (String(dir).startsWith('up_') ? 'walk_up' : 'walk_down');
  }

  function install() {
    if (window.__bosiowa && window.__bosiowa.installed) return;
    const A = window.ARK;
    if (!A || !A.ITEMS || !Array.isArray(A.ITEMS.npcs)) return;
    const target = { ...TARGET };

    const reachable = window.__game && typeof window.__game.isSpawnReachable === 'function'
      ? (x, y) => window.__game.isSpawnReachable(x, y)
      : () => false;
    const others = () => A.ITEMS.npcs.filter(n => n.id !== ID);
    const clear = (x, y) => CLEARANCE.every(([dx, dy]) => !A.blocked(x + dx, y + dy))
      && others().every(n => Math.hypot(x - n.x, y - n.y) >= 72);
    const candidates = [];
    // Stable, bounded ordering: nearest to the target, then y/x.
    for (let y = target.y - SEARCH_RADIUS; y <= target.y + SEARCH_RADIUS; y += 8) {
      for (let x = target.x - SEARCH_RADIUS; x <= target.x + SEARCH_RADIUS; x += 8) {
        const d = (x - target.x) ** 2 + (y - target.y) ** 2;
        if (d > SEARCH_RADIUS ** 2) continue;
        // Beside the buildings on the yard/grass: crop fields and forest only as a last resort.
        const terrain = A.terrainAt(x, y);
        candidates.push({ x, y, priority: terrain === 'field' || terrain === 'forest' ? 1 : 0, d });
      }
    }
    candidates.sort((a, b) => a.priority - b.priority || a.d - b.d || a.y - b.y || a.x - b.x);
    const found = candidates.find(c => !A.blocked(c.x, c.y) && clear(c.x, c.y) && reachable(c.x, c.y));
    if (!found) {
      window.__bosiowa = { installed: false, error: 'No reachable clear position near Kasia\'s home' };
      console.warn("BOSIOWA: no reachable clear position near Kasia's home; no unsafe fallback placed.");
      return;
    }

    // Replace stale duplicates with one authored runtime record and keep its position fixed.
    A.ITEMS.npcs = A.ITEMS.npcs.filter(n => n.id !== ID);
    A.ITEMS.npcs.push({ id: ID, x: found.x, y: found.y, face: 'down', fixed: true });
    A.HOOKS.npcTalk.push(id => {
      if (id !== ID) return false;
      A.say(ID, DIALOGUE[A.LANG === 'en' ? 'en' : 'pl']);
      return true;
    });

    window.__bosiowa = {
      installed: true,
      id: ID,
      target: { ...target },
      kasiaHome: { ...KASIA_HOME },
      position() {
        const npc = A.ITEMS.npcs.find(n => n.id === ID);
        return npc ? { x: npc.x, y: npc.y, sector: sectorAt(npc.x, npc.y), terrain: A.terrainAt(npc.x, npc.y), reachable: reachable(npc.x, npc.y) } : null;
      },
      directionFrames() { return { ...DIRECTION_FRAMES }; },
      directionFrame,
    };
  }

  window.__bosiowa = window.__bosiowa || { installed: false };
  // game.js publishes __game just after ark-ready; use its real reachability mask.
  let scheduled = false;
  const ready = () => { if (!scheduled) { scheduled = true; queueMicrotask(install); } };
  window.addEventListener('ark-ready', ready, { once: true });
  if (window.ARK) ready();
})();
