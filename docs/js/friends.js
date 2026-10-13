/* KOSTEK, PAWEŁ, DAREK, PIEKARZ, MAREK and WALDEK — fixed village friends, each near a real map anchor. */
'use strict';
(() => {
  const SEARCH_RADIUS = 160;
  const CLEARANCE = [[0, 0], [-24, 0], [24, 0], [0, -18], [0, 18], [-18, -12], [18, -12], [-18, 12], [18, 12]];
  // anchor: a POI or landmark from map.json; offset keeps him off the stop/door itself.
  // Optional per friend: radius (search radius), preferRoad (default true), clearance (free points around him).
  const FRIENDS = [
    {
      id: 'kostek',
      anchor: m => (m.pois || []).find(p => p.key === 'bus' && p.name === 'Chłopków Kolonia 09'),
      anchorName: 'Chłopków Kolonia 09 bus stop',
      offset: { x: 0, y: 70 },
      dialogue: {
        pl: ['Cześć! Kostek jestem. Tu na Kolonii zawsze jest coś do roboty.', 'Autobus? Jeździ, jak jeździ. Ja i tak wolę na nogach.', 'Jak będziesz szedł polami, uważaj na bele. Turlają się!'],
        en: ['Hi! I am Kostek. Out here in Kolonia there is always work to do.', 'The bus? It comes when it comes. I prefer walking anyway.', 'If you cross the fields, watch out for the hay bales. They roll!'],
      },
    },
    {
      id: 'pawel',
      anchor: m => (m.landmarks || []).find(l => l.key === 'swietlica'),
      anchorName: 'świetlica',
      offset: { x: 60, y: 30 },
      dialogue: {
        pl: ['O, siema! Paweł. Przy świetlicy zawsze ktoś się kręci.', 'Boisko jest zaraz obok. Wieczorem to tu się dzieje!', 'Wpadnij kiedyś, pogadamy dłużej.'],
        en: ['Oh, hey! Paweł. There is always someone around the community hall.', 'The football pitch is right next door. Evenings are lively here!', 'Drop by sometime, we will talk longer.'],
      },
    },
    {
      id: 'darek',
      anchor: m => (m.pois || []).find(p => p.key === 'shop'),
      anchorName: 'village shop',
      offset: { x: 70, y: 20 },
      dialogue: {
        pl: ['Siema! Darek. Lakiernik, ale po pracy zawsze elegancko.', 'Rysa na błotniku? Przyprowadź, zrobi się, że nie poznasz.', 'Sklep zaraz obok, gdyby co.'],
        en: ['Hey! Darek. Car painter, but always sharp after work.', 'A scratch on your fender? Bring it over, you will not even see it.', 'The shop is right next door, just in case.'],
      },
    },
    {
      id: 'piekarz',
      // Main dirt road north out of the village, where it leaves the forest (docs/img/map_terrain.png).
      anchor: () => ({ x: 2040, y: 680 }),
      anchorName: 'north road at the forest edge',
      offset: { x: 0, y: 0 },
      dialogue: {
        pl: ['Cześć! Piekarz jestem. Właśnie wróciłem z trasy.', 'Tirem to się człowiek najeździ, a i tak najlepiej wracać do Chłopkowa.', 'Ta droga przez las to wyjazd na północ.'],
        en: ['Hi! I am Piekarz. Just got back from a long haul.', 'You drive a truck all over, and coming back to Chłopków is still the best part.', 'This road through the forest is the way out north.'],
      },
    },
    {
      id: 'marek',
      anchor: m => (m.pois || []).find(p => p.key === 'river'),
      anchorName: 'river',
      offset: { x: -100, y: -15 },
      dialogue: {
        pl: ['Cześć, Marek. Lubię tu posiedzieć nad wodą.', 'Cicho, spokojnie, tylko woda szumi.', 'Kościół jest niedaleko, gdybyś szukał.'],
        en: ['Hi, Marek here. I like sitting by the water.', 'Quiet and calm, just the sound of the river.', 'The church is not far, if you are looking for it.'],
      },
    },
    {
      id: 'waldek',
      // Tomek: by the house next to the bus shelter north of Dom Muchy (Chłopków 3, opposite the świetlica),
      // standing between the two barns behind that house. Gap measured on docs/img/map_collide.png: x 2127-2159.
      anchor: () => ({ x: 2143, y: 4490 }),
      anchorName: 'barns behind the house by the bus shelter opposite the świetlica',
      offset: { x: 0, y: 0 },
      radius: 24,
      preferRoad: false,
      clearance: [[0, 0], [-6, 0], [6, 0], [0, -10], [0, 10]],
      dialogue: {
        pl: ['Dzień dobry! Waldek. Estrada to mój zawód: uczę tańczyć i śpiewać.', 'A jak trzeba, to jestem florystą. Każda scena ładniejsza z kwiatami!', 'Festyn, dożynki, wesele? Mikrofon w rękę i prowadzę jako MC.'],
        en: ['Good day! Waldek. The stage is my trade: I teach dancing and singing.', 'And when needed I am a florist too. Every stage looks better with flowers!', 'A village fair, a harvest festival, a wedding? Microphone in hand, I host it as MC.'],
      },
    },
  ];

  function sectorAt(x, y) {
    return String.fromCharCode(65 + Math.floor(Number(x) / 512)) + (Math.floor(Number(y) / 512) + 1);
  }

  function place(A, friend, reachable) {
    const anchor = friend.anchor(A.MAP);
    if (!anchor) return { installed: false, error: `No ${friend.anchorName} on the map` };
    const target = { x: Math.round(anchor.x + friend.offset.x), y: Math.round(anchor.y + friend.offset.y) };
    const radius = friend.radius || SEARCH_RADIUS, points = friend.clearance || CLEARANCE;
    const others = () => A.ITEMS.npcs.filter(n => n.id !== friend.id);
    const clear = (x, y) => points.every(([dx, dy]) => !A.blocked(x + dx, y + dy))
      && others().every(n => Math.hypot(x - n.x, y - n.y) >= 72);
    const road = (x, y) => { if (friend.preferRoad === false) return false; const t = A.terrainAt(x, y); return t === 'road' || t === 'track'; };
    const candidates = [];
    const step = radius < 60 ? 2 : 8;
    for (let y = target.y - radius; y <= target.y + radius; y += step) {
      for (let x = target.x - radius; x <= target.x + radius; x += step) {
        const d = (x - target.x) ** 2 + (y - target.y) ** 2;
        if (d <= radius ** 2) candidates.push({ x, y, priority: road(x, y) ? 0 : 1, d });
      }
    }
    // Stable order: road/track first, then nearest to the target, then y/x.
    candidates.sort((a, b) => a.priority - b.priority || a.d - b.d || a.y - b.y || a.x - b.x);
    const found = candidates.find(c => !A.blocked(c.x, c.y) && clear(c.x, c.y) && reachable(c.x, c.y));
    if (!found) return { installed: false, target, error: `No reachable clear position near ${friend.anchorName}` };
    A.ITEMS.npcs = A.ITEMS.npcs.filter(n => n.id !== friend.id);
    A.ITEMS.npcs.push({ id: friend.id, x: found.x, y: found.y, face: 'down', fixed: true });
    return { installed: true, target, x: found.x, y: found.y, sector: sectorAt(found.x, found.y), anchor: friend.anchorName };
  }

  function install() {
    if (window.__friends && window.__friends.installed) return;
    const A = window.ARK;
    if (!A || !A.ITEMS || !Array.isArray(A.ITEMS.npcs) || !A.MAP) return;
    const reachable = window.__game && typeof window.__game.isSpawnReachable === 'function'
      ? (x, y) => window.__game.isSpawnReachable(x, y)
      : () => false;
    const placed = {};
    for (const friend of FRIENDS) {
      placed[friend.id] = place(A, friend, reachable);
      if (!placed[friend.id].installed) console.warn(`${friend.id.toUpperCase()}: ${placed[friend.id].error}; not placed.`);
    }
    const byId = Object.fromEntries(FRIENDS.map(f => [f.id, f]));
    A.HOOKS.npcTalk.push(id => {
      const friend = byId[id];
      if (!friend || !placed[id].installed) return false;
      A.say(id, friend.dialogue[A.LANG === 'en' ? 'en' : 'pl']);
      return true;
    });
    window.__friends = {
      installed: FRIENDS.every(f => placed[f.id].installed),
      ids: FRIENDS.map(f => f.id),
      placed,
      position(id) {
        const npc = A.ITEMS.npcs.find(n => n.id === id);
        return npc ? { x: npc.x, y: npc.y, sector: sectorAt(npc.x, npc.y), terrain: A.terrainAt(npc.x, npc.y), reachable: reachable(npc.x, npc.y) } : null;
      },
    };
  }

  window.__friends = window.__friends || { installed: false };
  // game.js publishes __game just after ark-ready; use its real reachability mask.
  let scheduled = false;
  const ready = () => { if (!scheduled) { scheduled = true; queueMicrotask(install); } };
  window.addEventListener('ark-ready', ready, { once: true });
  if (window.ARK) ready();
})();
