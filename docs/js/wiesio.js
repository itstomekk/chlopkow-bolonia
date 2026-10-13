/* WIESIO — a fixed local in Peryczówka, about 250 m east of the church. */
'use strict';
(() => {
  const ID = 'wiesio';
  // Map scale is 2 px per metre (map.json scale 2.0); the church POI is the anchor.
  const EAST_OF_CHURCH_PX = 500, SEARCH_RADIUS = 160;
  const DIRECTION_FRAMES = Object.freeze({
    down: 'walk_down', up: 'walk_up', left: 'walk_left', right: 'walk_right',
    down_right: 'walk_right', down_left: 'walk_down', up_right: 'walk_up', up_left: 'walk_left',
  });
  const CLEARANCE = [[0, 0], [-24, 0], [24, 0], [0, -18], [0, 18], [-18, -12], [18, -12], [-18, 12], [18, 12]];
  const DIALOGUE = {
    pl: [
      'O, dzień dobry! Wiesio jestem. Tu, na Peryczówce, wszystko widać jak na dłoni.',
      'Do kościoła stąd rzut beretem. Ja się nigdzie nie spieszę, droga nie ucieknie.',
      'Uważaj na drodze, sąsiedzie. I zajrzyj jeszcze kiedyś.',
    ],
    en: [
      'Oh, good day! I am Wiesio. From here in Peryczówka you can see everything.',
      'The church is a stone\'s throw away. I am in no hurry, the road will not run off.',
      'Mind the road, neighbour. And drop by again some time.',
    ],
  };

  function sectorAt(x, y) {
    return String.fromCharCode(65 + Math.floor(Number(x) / 512)) + (Math.floor(Number(y) / 512) + 1);
  }

  function directionFrame(dir) {
    return DIRECTION_FRAMES[dir] || (String(dir).startsWith('up_') ? 'walk_up' : 'walk_down');
  }

  function install() {
    if (window.__wiesio && window.__wiesio.installed) return;
    const A = window.ARK;
    if (!A || !A.ITEMS || !Array.isArray(A.ITEMS.npcs) || !A.MAP) return;
    const church = (A.MAP.pois || []).find(p => p.key === 'church');
    if (!church) {
      window.__wiesio = { installed: false, error: 'No church POI on the map' };
      console.warn('WIESIO: no church POI; not placed.');
      return;
    }
    const target = { x: church.x + EAST_OF_CHURCH_PX, y: church.y };

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
    // Stable, bounded ordering: road/track first, then nearest to the target, then y/x.
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
      window.__wiesio = { installed: false, error: 'No reachable clear position near Peryczówka' };
      console.warn('WIESIO: no reachable clear position near Peryczówka; no unsafe fallback placed.');
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

    window.__wiesio = {
      installed: true,
      id: ID,
      target: { ...target },
      position() {
        const npc = A.ITEMS.npcs.find(n => n.id === ID);
        return npc ? { x: npc.x, y: npc.y, sector: sectorAt(npc.x, npc.y), terrain: A.terrainAt(npc.x, npc.y), reachable: reachable(npc.x, npc.y) } : null;
      },
      directionFrames() { return { ...DIRECTION_FRAMES }; },
      directionFrame,
    };
  }

  window.__wiesio = window.__wiesio || { installed: false };
  // game.js publishes __game just after ark-ready; use its real reachability mask.
  let scheduled = false;
  const ready = () => { if (!scheduled) { scheduled = true; queueMicrotask(install); } };
  window.addEventListener('ark-ready', ready, { once: true });
  if (window.ARK) ready();
})();
