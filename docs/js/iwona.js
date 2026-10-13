/* IWONA — looking for her husband Mariusz; her keys open the gym at the shooting range. */
'use strict';
(() => {
  const ID = 'iwona';
  // House Chłopków 20 (OSM way 909989528, 52.26605962, 22.86553264) -> osm/geo.py P() = (945, 4189).
  // Tomek moved her 100 m west of it (2 px per metre): target (745, 4189).
  const HOUSE = Object.freeze({ x: 945, y: 4189 }), WEST_PX = 200, SEARCH_RADIUS = 160;
  const DIRECTION_FRAMES = Object.freeze({
    down: 'walk_down', up: 'walk_up', left: 'walk_left', right: 'walk_right',
    down_right: 'walk_right', down_left: 'walk_down', up_right: 'walk_up', up_left: 'walk_left',
  });
  const CLEARANCE = [[0, 0], [-24, 0], [24, 0], [0, -18], [0, 18], [-18, -12], [18, -12], [-18, 12], [18, 12]];
  const DIALOGUE = {
    pl: [
      'Cześć! Jestem Iwona. Nie widziałeś gdzieś Mariusza? Mojego męża szukam.',
      'Te klucze? Od siłowni w strzelnicy. Bez nich nikt tam nie poćwiczy.',
      'Jak spotkasz Mariusza, powiedz mu, że go szukam. I że klucze są u mnie.',
    ],
    en: [
      'Hi! I am Iwona. Have you seen Mariusz anywhere? I am looking for my husband.',
      'These keys? They open the gym at the shooting range. Nobody trains there without them.',
      'If you run into Mariusz, tell him I am looking for him. And that I have the keys.',
    ],
  };

  function sectorAt(x, y) {
    return String.fromCharCode(65 + Math.floor(Number(x) / 512)) + (Math.floor(Number(y) / 512) + 1);
  }

  function directionFrame(dir) {
    return DIRECTION_FRAMES[dir] || (String(dir).startsWith('up_') ? 'walk_up' : 'walk_down');
  }

  function install() {
    if (window.__iwona && window.__iwona.installed) return;
    const A = window.ARK;
    if (!A || !A.ITEMS || !Array.isArray(A.ITEMS.npcs)) return;
    const target = { x: HOUSE.x - WEST_PX, y: HOUSE.y };

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
      window.__iwona = { installed: false, error: 'No reachable clear position west of Chłopków 20' };
      console.warn('IWONA: no reachable clear position west of Chłopków 20; no unsafe fallback placed.');
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

    window.__iwona = {
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

  window.__iwona = window.__iwona || { installed: false };
  // game.js publishes __game just after ark-ready; use its real reachability mask.
  let scheduled = false;
  const ready = () => { if (!scheduled) { scheduled = true; queueMicrotask(install); } };
  window.addEventListener('ark-ready', ready, { once: true });
  if (window.ARK) ready();
})();