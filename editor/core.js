/* Map editor core: viewer, layers, undo/redo, save/rebuild, tool registry.
   Tools live in editor/tools/*.js and call Editor.registerTool({...}); the core never hardcodes a tool.

   Tool interface (all optional except id/label):
     id, label, key                  toolbar button + number shortcut
     panel(el)                       fill the side panel when the tool is active
     activate(), deactivate()
     down(ev, w), move(ev, w), up(ev, w), dbl(ev, w)   pointer events; w = {x, y} in map art pixels
     keydown(ev) -> true if handled
     draw(ctx)                       extra drawing while the tool is active (world transform set)
     overlay(ctx)                    always-on drawing of this tool's data when the "edits" layer is on
*/
(function () {
  const $ = s => document.querySelector(s);
  const cv = $('#cv'), ctx = cv.getContext('2d');
  const E = {
    geo: null, edits: null, map: null, items: null,
    view: { x: 0, y: 0, z: .25 }, cursor: { x: 0, y: 0 }, screen: { x: 0, y: 0 },
    tools: [], tool: null, sel: null, dirty: false,
    img: {}, tiles: new Map(), undoStack: [], redoStack: [], savedJson: '',
    vis: Object.assign({ ground: true, objects: true, collide: false, edits: true, entities: true, grid: false, basemap: false, ref: false },
      JSON.parse(localStorage.getItem('mapedit.vis') || '{}')),
    basemap: { src: localStorage.getItem('mapedit.src') || 'esri', opacity: +(localStorage.getItem('mapedit.op') || .6) },
    ctx, cv,
  };
  window.Editor = E;

  // ---------------------------------------------------------------- helpers
  E.status = (msg, err = false) => { const s = $('#status'); s.textContent = msg; s.className = err ? 'err' : ''; };
  E.toWorld = (sx, sy) => ({ x: E.view.x + sx / E.view.z, y: E.view.y + sy / E.view.z });
  E.toScreen = (x, y) => ({ x: (x - E.view.x) * E.view.z, y: (y - E.view.y) * E.view.z });
  E.px = n => n / E.view.z;                         // screen pixels -> world units (for line widths, hit radii)
  E.fmt = (x, y) => { const [la, lo] = GEO.toLL(x, y); return `${Math.round(x)},${Math.round(y)}  (${la.toFixed(6)}, ${lo.toFixed(6)})  ${GEO.sector(x, y)}`; };
  E.pointInPoly = (x, y, pts) => {
    let inside = false;
    for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) {
      const [ax, ay] = pts[i], [bx, by] = pts[j];
      if ((ay > y) !== (by > y) && x < ax + (y - ay) * (bx - ax) / (by - ay)) inside = !inside;
    }
    return inside;
  };
  E.layer = (name, dflt) => {
    const L = E.edits.layers;
    if (!L[name]) L[name] = dflt ? JSON.parse(JSON.stringify(dflt)) : {};
    return L[name];
  };
  E.peek = name => E.edits.layers[name] || {};
  E.pathPoly = (pts, close = true) => {
    ctx.beginPath();
    pts.forEach(([x, y], i) => i ? ctx.lineTo(x, y) : ctx.moveTo(x, y));
    if (close) ctx.closePath();
  };

  // ---------------------------------------------------------------- undo / dirty
  E.change = (fn, label = 'zmiana') => {
    E.undoStack.push(JSON.stringify(E.edits));
    if (E.undoStack.length > 300) E.undoStack.shift();
    E.redoStack.length = 0;
    fn(E.edits);
    // drop empty layers so the saved file stays small and readable
    for (const [k, v] of Object.entries(E.edits.layers)) if (v && typeof v === 'object' && !Object.values(v).some(x => Array.isArray(x) ? x.length : x && typeof x === 'object' ? Object.keys(x).length : x)) delete E.edits.layers[k];
    E.markDirty(); E.status(label); E.redraw();
  };
  E.undo = () => { if (!E.undoStack.length) return; E.redoStack.push(JSON.stringify(E.edits)); E.edits = JSON.parse(E.undoStack.pop()); E.sel = null; E.markDirty(); E.refreshPanel(); E.redraw(); E.status('cofnięto'); };
  E.redo = () => { if (!E.redoStack.length) return; E.undoStack.push(JSON.stringify(E.edits)); E.edits = JSON.parse(E.redoStack.pop()); E.sel = null; E.markDirty(); E.refreshPanel(); E.redraw(); E.status('ponowiono'); };
  E.markDirty = () => {
    E.dirty = JSON.stringify(E.edits.layers) !== E.savedJson;
    $('#dirty').classList.toggle('on', E.dirty);
    $('#btn-undo').disabled = !E.undoStack.length; $('#btn-redo').disabled = !E.redoStack.length;
  };

  // ---------------------------------------------------------------- server calls
  E.save = async () => {
    const r = await fetch('/api/edits', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(E.edits) });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) { E.status('Błąd zapisu: ' + (j.details ? j.details.join('; ') : j.error || r.status), true); return false; }
    E.edits.meta = Object.assign(E.edits.meta || {}, { updated: j.updated });
    E.savedJson = JSON.stringify(E.edits.layers); E.markDirty(); E.status('Zapisano osm/edits.json ' + j.updated);
    return true;
  };
  E.rebuild = async () => {
    if (E.dirty && !(await E.save())) return;
    const b = $('#btn-rebuild'); b.disabled = true; E.status('Przebudowa mapy… (to trwa około minuty)');
    try {
      const r = await fetch('/api/rebuild', { method: 'POST' });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) { E.status('Przebudowa: ' + (j.error || ('błąd ' + j.code)), true); if (j.log) console.log(j.log); return; }
      console.log(j.log); await E.loadMapImages(true); E.status('Mapa przebudowana');
    } finally { b.disabled = false; }
  };

  // ---------------------------------------------------------------- loading
  const loadImg = src => new Promise((ok, bad) => { const i = new Image(); i.onload = () => ok(i); i.onerror = () => bad(new Error('nie wczytano ' + src)); i.src = src; });
  E.loadMapImages = async (bust) => {
    const q = bust ? '?t=' + Date.now() : '';
    const [map, items, ground, objects] = await Promise.all([
      fetch('/game/map.json' + q).then(r => r.json()), fetch('/game/items.json' + q).then(r => r.json()),
      loadImg('/game/img/map_ground.png' + q), loadImg('/game/img/map_objects.png' + q)]);
    Object.assign(E, { map, items }); E.img.ground = ground; E.img.objects = objects; E.img.collide = null;
    E.buildEntities(); E.redraw();
  };
  E.buildEntities = () => {
    const out = [], m = E.map || {}, it = E.items || {};
    (it.npcs || []).forEach(n => out.push({ key: 'npc:' + n.id, label: n.id, kind: 'npc', x: n.x, y: n.y }));
    (m.landmarks || it.landmarks || []).forEach(l => out.push({ key: 'landmark:' + l.key, label: l.name || l.key, kind: 'landmark', x: l.x, y: l.y }));
    const venue = (name, o, cx = 'cx', cy = 'cy') => o && out.push({ key: 'venue:' + name, label: name, kind: 'venue', x: o[cx], y: o[cy] });
    venue('track', m.track); venue('corral', m.corral); venue('range', m.range, 'x', 'y'); venue('football_pitch', m.football_pitch); venue('spawn', m.spawn, 'x', 'y');
    if (m.meadow) out.push({ key: 'venue:meadow', label: 'meadow', kind: 'venue', x: (m.meadow.x0 + m.meadow.x1) / 2, y: (m.meadow.y0 + m.meadow.y1) / 2 });
    E.entities = out.filter(e => Number.isFinite(e.x) && Number.isFinite(e.y));
  };
  function collideCanvas() {
    if (E.img.collide !== null && E.img.collide !== undefined) return E.img.collide;
    E.img.collide = false;
    loadImg('/game/img/map_collide.png?t=' + Date.now()).then(im => {
      const c = document.createElement('canvas'); c.width = im.width; c.height = im.height;
      const g = c.getContext('2d'); g.drawImage(im, 0, 0);
      const d = g.getImageData(0, 0, c.width, c.height), a = d.data;
      for (let i = 0; i < a.length; i += 4) {
        const v = a[i];
        if (v > 200) { a[i] = 230; a[i + 1] = 40; a[i + 2] = 40; a[i + 3] = 140; }
        else if (v > 60) { a[i] = 240; a[i + 1] = 200; a[i + 2] = 40; a[i + 3] = 120; }
        else a[i + 3] = 0;
      }
      g.putImageData(d, 0, 0); E.img.collide = c; E.redraw();
    }).catch(e => E.status(e.message, true));
    return false;
  }

  // ---------------------------------------------------------------- rendering
  let raf = 0;
  E.redraw = () => { if (!raf) raf = requestAnimationFrame(render); };
  function tileZ() { return Math.max(0, Math.min(4, Math.floor(Math.log2(1 / E.view.z)))); }
  function drawBasemap(W, H) {
    const z = tileZ(), span = E.geo.tile * 2 ** z, src = E.basemap.src;
    const x0 = Math.max(0, Math.floor(E.view.x / span)), y0 = Math.max(0, Math.floor(E.view.y / span));
    const x1 = Math.min(Math.ceil(E.geo.w / span) - 1, Math.floor((E.view.x + W / E.view.z) / span));
    const y1 = Math.min(Math.ceil(E.geo.h / span) - 1, Math.floor((E.view.y + H / E.view.z) / span));
    ctx.globalAlpha = E.basemap.opacity;
    let failed = 0;
    for (let ty = y0; ty <= y1; ty++) for (let tx = x0; tx <= x1; tx++) {
      const key = `${src}/${z}/${tx}_${ty}`;
      let t = E.tiles.get(key);
      if (!t) {
        t = { img: new Image(), ok: false, bad: false };
        t.img.onload = () => { t.ok = true; E.redraw(); };
        t.img.onerror = () => { t.bad = true; E.redraw(); };
        t.img.src = `/api/basemap/${z}/${tx}/${ty}.jpg?src=${src}`;
        E.tiles.set(key, t);
      }
      if (t.ok) ctx.drawImage(t.img, tx * span, ty * span, span, span);
      else if (t.bad) failed++;
    }
    ctx.globalAlpha = 1;
    if (failed) E.status(`Satelita (${src}): ${failed} kafelków niedostępnych`, true);
  }
  function drawGrid(W, H) {
    const S = GEO.SECTOR;
    ctx.strokeStyle = 'rgba(255,255,255,.45)'; ctx.lineWidth = E.px(1);
    ctx.beginPath();
    for (let x = 0; x <= E.geo.w; x += S) { ctx.moveTo(x, 0); ctx.lineTo(x, E.geo.h); }
    for (let y = 0; y <= E.geo.h; y += S) { ctx.moveTo(0, y); ctx.lineTo(E.geo.w, y); }
    ctx.stroke();
    ctx.fillStyle = 'rgba(255,255,255,.8)'; ctx.font = `${E.px(12)}px system-ui`;
    for (let x = 0; x < E.geo.w; x += S) for (let y = 0; y < E.geo.h; y += S) ctx.fillText(GEO.sector(x + 1, y + 1), x + E.px(4), y + E.px(14));
  }
  function render() {
    raf = 0;
    const dpr = window.devicePixelRatio || 1, W = cv.clientWidth, H = cv.clientHeight;
    if (cv.width !== Math.round(W * dpr) || cv.height !== Math.round(H * dpr)) { cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr); }
    ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.fillStyle = '#101214'; ctx.fillRect(0, 0, cv.width, cv.height);
    if (!E.geo) return;
    const z = E.view.z;
    ctx.setTransform(dpr * z, 0, 0, dpr * z, -E.view.x * z * dpr, -E.view.y * z * dpr);
    ctx.imageSmoothingEnabled = z < 1;
    if (E.vis.ground && E.img.ground) ctx.drawImage(E.img.ground, 0, 0);
    if (E.vis.objects && E.img.objects) ctx.drawImage(E.img.objects, 0, 0);
    if (E.vis.basemap) drawBasemap(W, H);
    E.tools.forEach(t => t.underlay && t.underlay(ctx));
    if (E.vis.collide) { const c = collideCanvas(); if (c) ctx.drawImage(c, 0, 0); }
    ctx.strokeStyle = '#000'; ctx.lineWidth = E.px(2); ctx.strokeRect(0, 0, E.geo.w, E.geo.h);
    if (E.vis.grid) drawGrid(W, H);
    if (E.vis.edits) E.tools.forEach(t => t.overlay && t.overlay(ctx));
    E.tools.forEach(t => t.entityOverlay && E.vis.entities && t.entityOverlay(ctx));
    if (E.tool && E.tool.draw) E.tool.draw(ctx);
  }

  // ---------------------------------------------------------------- tools
  E.registerTool = t => {
    E.tools.push(t);
    const b = document.createElement('button');
    const n = E.tools.length;
    b.innerHTML = `${t.label}<span class="k">${n <= 9 ? n : ''}</span>`; b.title = t.title || t.label;
    b.onclick = () => E.setTool(t.id); t._btn = b; $('#tools').appendChild(b);
  };
  E.setTool = id => {
    const t = E.tools.find(x => x.id === id); if (!t || t === E.tool) return;
    if (E.tool) { E.tool.deactivate && E.tool.deactivate(); E.tool._btn.classList.remove('on'); }
    E.tool = t; E.sel = null; t._btn.classList.add('on'); cv.style.cursor = t.cursor || 'crosshair';
    t.activate && t.activate(); E.refreshPanel(); localStorage.setItem('mapedit.tool', id); E.redraw();
  };
  E.refreshPanel = () => { const p = $('#tool-panel'); p.innerHTML = ''; if (E.tool && E.tool.panel) E.tool.panel(p); };

  // ---------------------------------------------------------------- navigation + input
  let drag = null, spaceDown = false;
  const world = ev => { const r = cv.getBoundingClientRect(); E.screen = { x: ev.clientX - r.left, y: ev.clientY - r.top }; return E.toWorld(E.screen.x, E.screen.y); };
  function updateReadout() {
    const c = E.cursor;
    $('#readout').textContent = `x ${Math.round(c.x)}  y ${Math.round(c.y)}\n${GEO.toLL(c.x, c.y).map(v => v.toFixed(6)).join(', ')}\nsektor ${GEO.sector(c.x, c.y)}   zoom ${E.view.z.toFixed(2)}×`;
  }
  function saveView() { history.replaceState(null, '', `#${Math.round(E.view.x + cv.clientWidth / 2 / E.view.z)},${Math.round(E.view.y + cv.clientHeight / 2 / E.view.z)},${E.view.z.toFixed(3)}`); }
  E.centerOn = (x, y, z = E.view.z) => { E.view.z = z; E.view.x = x - cv.clientWidth / 2 / z; E.view.y = y - cv.clientHeight / 2 / z; saveView(); E.redraw(); };

  cv.addEventListener('contextmenu', ev => ev.preventDefault());
  cv.addEventListener('pointerdown', ev => {
    cv.setPointerCapture(ev.pointerId);
    const w = world(ev);
    const panBtn = ev.button === 1 || (ev.button === 2 && !(E.tool && E.tool.wantsRight)) || (ev.button === 0 && (spaceDown || (E.tool && E.tool.pans)));
    if (panBtn) { drag = { sx: ev.clientX, sy: ev.clientY, vx: E.view.x, vy: E.view.y }; cv.style.cursor = 'grabbing'; return; }
    E.tool && E.tool.down && E.tool.down(ev, w);
  });
  cv.addEventListener('pointermove', ev => {
    const w = world(ev); E.cursor = w; updateReadout();
    if (drag) { E.view.x = drag.vx - (ev.clientX - drag.sx) / E.view.z; E.view.y = drag.vy - (ev.clientY - drag.sy) / E.view.z; E.redraw(); return; }
    E.tool && E.tool.move && E.tool.move(ev, w);
    if (E.tool && E.tool.draw) E.redraw();
  });
  cv.addEventListener('pointerup', ev => {
    if (drag) { drag = null; cv.style.cursor = (E.tool && E.tool.cursor) || 'crosshair'; saveView(); return; }
    E.tool && E.tool.up && E.tool.up(ev, world(ev));
  });
  cv.addEventListener('dblclick', ev => { E.tool && E.tool.dbl && E.tool.dbl(ev, world(ev)); });
  cv.addEventListener('wheel', ev => {
    ev.preventDefault();
    const w = world(ev), k = Math.exp(-ev.deltaY * (ev.ctrlKey ? .01 : .0015));
    const z = Math.max(.04, Math.min(8, E.view.z * k));
    E.view.x = w.x - E.screen.x / z; E.view.y = w.y - E.screen.y / z; E.view.z = z;
    updateReadout(); saveView(); E.redraw();
  }, { passive: false });
  window.addEventListener('resize', E.redraw);
  window.addEventListener('keyup', ev => { if (ev.code === 'Space') spaceDown = false; });
  window.addEventListener('keydown', ev => {
    const typing = /INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName);
    if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === 's') { ev.preventDefault(); E.save(); return; }
    if (typing) return;
    if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === 'z') { ev.preventDefault(); ev.shiftKey ? E.redo() : E.undo(); return; }
    if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === 'y') { ev.preventDefault(); E.redo(); return; }
    if (E.tool && E.tool.keydown && E.tool.keydown(ev)) { ev.preventDefault(); E.redraw(); return; }
    if (ev.code === 'Space') { spaceDown = true; ev.preventDefault(); return; }
    if (/^[1-9]$/.test(ev.key) && E.tools[+ev.key - 1]) { E.setTool(E.tools[+ev.key - 1].id); return; }
    if (ev.key === 'p' || ev.key === 'P') { E.play(); return; }
    if (ev.key === 'c' || ev.key === 'C') { navigator.clipboard && navigator.clipboard.writeText(E.fmt(E.cursor.x, E.cursor.y)); E.status('Skopiowano ' + E.fmt(E.cursor.x, E.cursor.y)); return; }
    if (ev.key === '?') { $('#help').hidden = !$('#help').hidden; return; }
    if (ev.key === 'Escape') { E.sel = null; E.refreshPanel(); E.redraw(); }
  });
  E.play = () => window.open(`/game/index.html?x=${Math.round(E.cursor.x)}&y=${Math.round(E.cursor.y)}`, '_blank');

  function gotoParse(s) {
    s = s.trim();
    let m = s.match(/^([A-Za-z])\s*(\d+)$/);
    if (m) return [(m[1].toUpperCase().charCodeAt(0) - 65 + .5) * GEO.SECTOR, (+m[2] - .5) * GEO.SECTOR];
    m = s.match(/(-?\d+(?:\.\d+)?)[\s,;]+(-?\d+(?:\.\d+)?)/);
    if (!m) return null;
    const a = +m[1], b = +m[2];
    if (Math.abs(a) <= 90 && Math.abs(b) <= 180 && (String(m[1]).includes('.') || String(m[2]).includes('.')) && a > 40) return GEO.P(a, b);
    return [a, b];
  }

  // ---------------------------------------------------------------- UI wiring
  function wireUi() {
    $('#btn-save').onclick = E.save; $('#btn-undo').onclick = E.undo; $('#btn-redo').onclick = E.redo;
    $('#btn-rebuild').onclick = E.rebuild; $('#btn-play').onclick = () => { E.cursor = E.toWorld(cv.clientWidth / 2, cv.clientHeight / 2); E.play(); };
    $('#btn-help').onclick = () => { $('#help').hidden = !$('#help').hidden; };
    $('#btn-rebuild').title = E.geo.allowRebuild ? 'Przebuduj mapę z edycjami' : 'Wyłączone: uruchom serwer z --allow-rebuild';
    $('#btn-export').onclick = () => {
      const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([JSON.stringify(E.edits, null, 1)], { type: 'application/json' }));
      a.download = 'edits.json'; a.click();
    };
    $('#file-import').onchange = async ev => {
      const f = ev.target.files[0]; if (!f) return;
      try { const d = JSON.parse(await f.text()); E.change(e => { e.layers = d.layers || {}; e.version = d.version || 1; }, 'Zaimportowano ' + f.name); }
      catch (e) { E.status('Import: ' + e.message, true); }
      ev.target.value = '';
    };
    document.querySelectorAll('[data-layer]').forEach(cb => {
      cb.checked = !!E.vis[cb.dataset.layer];
      cb.onchange = () => { E.vis[cb.dataset.layer] = cb.checked; localStorage.setItem('mapedit.vis', JSON.stringify(E.vis)); E.redraw(); };
    });
    const sel = $('#basemap-src');
    Object.entries(E.geo.sources).forEach(([k, v]) => { const o = document.createElement('option'); o.value = k; o.textContent = k; o.title = v; sel.appendChild(o); });
    sel.value = E.basemap.src in E.geo.sources ? E.basemap.src : 'esri';
    sel.onchange = () => { E.basemap.src = sel.value; localStorage.setItem('mapedit.src', sel.value); E.status(E.geo.sources[sel.value]); E.redraw(); };
    const op = $('#basemap-opacity'); op.value = E.basemap.opacity;
    op.oninput = () => { E.basemap.opacity = +op.value; localStorage.setItem('mapedit.op', op.value); E.redraw(); };
    $('#goto').onkeydown = ev => {
      if (ev.key !== 'Enter') return;
      const p = gotoParse(ev.target.value);
      if (!p) return E.status('Nie rozumiem współrzędnych', true);
      E.cursor = { x: p[0], y: p[1] }; E.centerOn(p[0], p[1], Math.max(E.view.z, 1)); E.flash = { x: p[0], y: p[1], t: performance.now() };
    };
    window.addEventListener('beforeunload', ev => { if (E.dirty) { ev.preventDefault(); ev.returnValue = ''; } });
  }

  E.start = async () => {
    try {
      E.geo = await fetch('/api/geo').then(r => r.json()); GEO.init(E.geo);
      E.edits = await fetch('/api/edits').then(r => r.json());
      if (E.edits.error) throw new Error(E.edits.error);
      E.savedJson = JSON.stringify(E.edits.layers);
      wireUi(); E.markDirty();
      const h = location.hash.slice(1).split(',').map(Number);
      requestAnimationFrame(() => {
        if (h.length === 3 && h.every(Number.isFinite)) E.centerOn(h[0], h[1], h[2]);
        else E.centerOn(949, 4665, .5);
      });
      E.setTool(localStorage.getItem('mapedit.tool') || E.tools[0].id);
      if (!E.tool) E.setTool(E.tools[0].id);
      await E.loadMapImages();
      E.status('Gotowe. ? = skróty');
    } catch (e) { E.status('Start: ' + e.message, true); console.error(e); }
  };
})();
