/* BERCIK — a fixed, friendly traveller in sector J12. */
'use strict';
(() => {
  const ID = 'bercik';
  const J12 = Object.freeze({ x0: 4608, x1: 5119, y0: 5632, y1: 6143, sector: 'J12' });
  const DIRECTION_FRAMES = Object.freeze({
    down: 'walk_down', up: 'walk_up', left: 'walk_left', right: 'walk_right',
    down_right: 'walk_right', down_left: 'walk_down', up_right: 'walk_up', up_left: 'walk_left',
  });
  const CLEARANCE = [[0, 0], [-24, 0], [24, 0], [0, -18], [0, 18], [-18, -12], [18, -12], [-18, 12], [18, 12]];
  const DIALOGUE = {
    pl: [
      'Cześć! Jestem Bercik, życzliwy wędrowiec. Zatrzymałem się tu na chwilę, żeby odpocząć przy drodze.',
      'Lubię takie spokojne zakątki. Każda wiejska ścieżka ma własną opowieść.',
      'Powodzenia w twojej wędrówce! Może jeszcze się spotkamy.',
    ],
    en: [
      'Hi! I am Bercik, a friendly traveller. I stopped here for a moment to rest by the road.',
      'I like quiet corners like this. Every country path has a story of its own.',
      'Good luck on your journey! Perhaps we will meet again.',
    ],
  };

  function sectorAt(x, y) {
    return String.fromCharCode(65 + Math.floor(Number(x) / 512)) + (Math.floor(Number(y) / 512) + 1);
  }

  function directionFrame(dir) {
    return DIRECTION_FRAMES[dir] || (String(dir).startsWith('up_') ? 'walk_up' : 'walk_down');
  }

  function install() {
    if (window.__bercik && window.__bercik.installed) return;
    const A = window.ARK;
    if (!A || !A.ITEMS || !Array.isArray(A.ITEMS.npcs)) return;

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
    const cx = (J12.x0 + J12.x1) / 2, cy = (J12.y0 + J12.y1) / 2;
    // Stable, bounded ordering: road/track first, then nearest to the centre of J12, then x/y.
    for (let y = J12.y0; y <= J12.y1; y += 8) for (let x = J12.x0; x <= J12.x1; x += 8) {
      candidates.push({ x, y, priority: road({ x, y }) ? 0 : 1, d: (x - cx) ** 2 + (y - cy) ** 2 });
    }
    candidates.sort((a, b) => a.priority - b.priority || a.d - b.d || a.y - b.y || a.x - b.x);
    const found = candidates.find(c => !A.blocked(c.x, c.y) && clear(c.x, c.y) && reachable(c.x, c.y));
    if (!found) {
      window.__bercik = { installed: false, error: 'No reachable clear position in J12' };
      console.warn('BERCIK: no reachable clear position in J12; no unsafe fallback placed.');
      return;
    }
    const placement = found;

    // Replace stale duplicates with one authored runtime record and keep its position fixed.
    A.ITEMS.npcs = A.ITEMS.npcs.filter(n => n.id !== ID);
    A.ITEMS.npcs.push({ id: ID, x: placement.x, y: placement.y, face: 'down', fixed: true });
    A.HOOKS.npcTalk.push(id => {
      if (id !== ID) return false;
      A.say(ID, DIALOGUE[A.LANG === 'en' ? 'en' : 'pl']);
      return true;
    });

    window.__bercik = {
      installed: true,
      id: ID,
      bounds: J12,
      position() {
        const npc = A.ITEMS.npcs.find(n => n.id === ID);
        return npc ? { x: npc.x, y: npc.y, sector: sectorAt(npc.x, npc.y), terrain: A.terrainAt(npc.x, npc.y), reachable: reachable(npc.x, npc.y) } : null;
      },
      directionFrames() { return { ...DIRECTION_FRAMES }; },
      directionFrame,
    };
  }

  window.__bercik = window.__bercik || { installed: false };
  // game.js publishes __game just after ark-ready; use its real reachability mask.
  let scheduled = false;
  const ready = () => { if (!scheduled) { scheduled = true; queueMicrotask(install); } };
  window.addEventListener('ark-ready', ready, { once: true });
  if (window.ARK) ready();
})();
