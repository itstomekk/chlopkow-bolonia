/* Buildings: select an OSM building, move / resize / rotate / delete it, or draw a new rectangle.
   Stored in layers.buildings:
     add:    [{lat, lon, len, wid, angle, kind}]   new rectangles (metres, degrees)
     modify: {"<osm way id>": {lat, lon, len, wid, angle}}
     remove: [<osm way id>, ...]
   The editor shows the real OSM footprint; the game draws houses a bit larger (1.25-2.3x) unless the
   building was edited, in which case the exact size is used. Every building blocks movement. */
(function () {
  const E = Editor;
  let OSM = [], drag = null, draft = null, kind = 'house';
  const f7 = v => +(+v).toFixed(7), f2 = v => +(+v).toFixed(2);

  E.loadBuildings = async () => { try { OSM = (await fetch('/api/buildings').then(r => r.json())).buildings || []; E.redraw(); } catch (e) { E.status('Budynki: ' + e.message, true); } };
  const L = () => E.peek('buildings');
  const removed = id => (L().remove || []).includes(id);
  // the current rectangle of a building record: edited version if any
  function rect(b) { return b.osm ? Object.assign({}, b, (L().modify || {})[b.id] || {}) : b; }
  function all() {
    const out = OSM.map(o => ({ ...o, osm: true })).filter(o => !removed(o.id));
    (L().add || []).forEach((a, i) => out.push({ ...a, idx: i, osm: false }));
    return out;
  }
  function corners(r) {
    const [cx, cy] = GEO.P(r.lat, r.lon), a = (r.angle || 0) * Math.PI / 180, A = GEO.a;
    const ax = [Math.cos(a), Math.sin(a)], nx = [-Math.sin(a), Math.cos(a)], hl = r.len * A / 2, hw = r.wid * A / 2;
    return [[-1, -1], [1, -1], [1, 1], [-1, 1]].map(([s, t]) => [cx + ax[0] * s * hl + nx[0] * t * hw, cy + ax[1] * s * hl + nx[1] * t * hw]);
  }
  const selRec = () => E.sel && E.sel.tool === 'buildings' ? all().find(b => b.osm === E.sel.osm && (b.osm ? b.id === E.sel.id : b.idx === E.sel.idx)) : null;
  function hit(w) {
    const list = all();
    for (let i = list.length - 1; i >= 0; i--) if (E.pointInPoly(w.x, w.y, corners(rect(list[i])))) return list[i];
    return null;
  }
  function handles(r) {
    const c = corners(r), [cx, cy] = GEO.P(r.lat, r.lon), a = (r.angle || 0) * Math.PI / 180;
    const mid = (p, q) => [(p[0] + q[0]) / 2, (p[1] + q[1]) / 2];
    const rotR = r.len * GEO.a / 2 + E.px(22);
    return { len: mid(c[1], c[2]), wid: mid(c[2], c[3]), rot: [cx + Math.cos(a) * rotR, cy + Math.sin(a) * rotR], c: [cx, cy] };
  }
  function writeRec(b, r) {
    const clean = { lat: f7(r.lat), lon: f7(r.lon), len: f2(Math.max(1, r.len)), wid: f2(Math.max(1, r.wid)), angle: f2(((r.angle % 360) + 540) % 360 - 180) };
    if (b.osm) { const B = E.layer('buildings'); (B.modify = B.modify || {})[b.id] = clean; }
    else { const B = E.layer('buildings'); B.add[b.idx] = Object.assign({ kind: b.kind || 'house' }, clean); }
  }
  function del(b) {
    E.sel = null;
    E.change(() => {
      const B = E.layer('buildings');
      if (b.osm) { (B.remove = B.remove || []).push(b.id); if (B.modify) delete B.modify[b.id]; }
      else B.add.splice(b.idx, 1);
    }, 'Usunięto budynek');
    E.refreshPanel();
  }

  E.registerTool({
    id: 'buildings', label: 'Budynki', title: 'Zaznacz budynek: przesuń, zmień rozmiar, obróć, usuń. Przeciągnij na pustym = nowy prostokąt',
    activate() { if (!OSM.length) E.loadBuildings(); },
    panel(el) {
      const b = selRec(), r = b && rect(b), l = L();
      let h = `<h3>Budynki</h3><p class="hint">Klik = zaznacz. Przeciągnij środek = przesuń, kwadraty = długość/szerokość, kółko = obrót (Shift = co 15°). Przeciągnij na pustym polu = nowy budynek. Delete = usuń.</p>
        <label>Nowe jako <select id="bd-kind"><option value="house" ${kind === 'house' ? 'selected' : ''}>dom</option><option value="farm" ${kind === 'farm' ? 'selected' : ''}>gospodarczy</option></select></label>
        <p class="hint">OSM: ${OSM.length}, zmienione: ${Object.keys(l.modify || {}).length}, usunięte: ${(l.remove || []).length}, nowe: ${(l.add || []).length}</p>`;
      if (r) {
        h += `<p><b>${b.osm ? (r.name || r.osmKind || 'budynek') + ' · OSM ' + b.id : 'nowy budynek #' + (b.idx + 1)}</b>${b.landmark ? '<br><span class="hint">landmark z własną grafiką (kościół) — zmiany może nie widać w grze</span>' : ''}</p>
          <div class="row">dł. <input id="bd-len" value="${f2(r.len)}" size="4"> m szer. <input id="bd-wid" value="${f2(r.wid)}" size="4"> m</div>
          <div class="row">obrót <input id="bd-ang" value="${f2(r.angle || 0)}" size="4">°</div>
          <div class="row"><button id="bd-apply">Ustaw</button><button id="bd-del">Usuń</button>${b.osm && (l.modify || {})[b.id] ? '<button id="bd-reset">Przywróć OSM</button>' : ''}</div>`;
      }
      if ((l.remove || []).length) h += `<button id="bd-undel">Przywróć usunięte (${l.remove.length})</button>`;
      el.innerHTML = h;
      el.querySelector('#bd-kind').onchange = ev => { kind = ev.target.value; };
      const q = s => el.querySelector(s);
      if (q('#bd-apply')) q('#bd-apply').onclick = () => {
        const nr = Object.assign({}, r, { len: +q('#bd-len').value, wid: +q('#bd-wid').value, angle: +q('#bd-ang').value });
        if (![nr.len, nr.wid, nr.angle].every(Number.isFinite)) return E.status('Podaj liczby', true);
        E.change(() => writeRec(b, nr), 'Zmieniono budynek'); E.refreshPanel();
      };
      if (q('#bd-del')) q('#bd-del').onclick = () => del(b);
      if (q('#bd-reset')) q('#bd-reset').onclick = () => { E.change(e => { delete e.layers.buildings.modify[b.id]; }, 'Przywrócono kształt z OSM'); E.refreshPanel(); };
      if (q('#bd-undel')) q('#bd-undel').onclick = () => { E.change(e => { e.layers.buildings.remove = []; }, 'Przywrócono usunięte budynki'); E.refreshPanel(); };
    },
    down(ev, w) {
      if (ev.button !== 0) return;
      const b = selRec();
      if (b) {
        const r = rect(b), hd = handles(r), near = p => Math.hypot(p[0] - w.x, p[1] - w.y) < Math.max(E.px(9), 2);
        const mode = near(hd.rot) ? 'rot' : near(hd.len) ? 'len' : near(hd.wid) ? 'wid' : E.pointInPoly(w.x, w.y, corners(r)) ? 'move' : null;
        if (mode) { drag = { mode, b, r0: r, w0: w, r: Object.assign({}, r) }; return; }
      }
      const h = hit(w);
      if (h) { E.sel = { tool: 'buildings', osm: h.osm, id: h.id, idx: h.idx }; drag = { mode: 'move', b: h, r0: rect(h), w0: w, r: Object.assign({}, rect(h)) }; E.refreshPanel(); E.redraw(); return; }
      E.sel = null; E.refreshPanel();
      draft = { a: w, b: w };
    },
    move(ev, w) {
      if (draft) { draft.b = w; E.redraw(); return; }
      if (!drag) return;
      const { r0, w0 } = drag, r = drag.r, [cx, cy] = GEO.P(r0.lat, r0.lon), a = (r0.angle || 0) * Math.PI / 180;
      if (drag.mode === 'move') { [r.lat, r.lon] = GEO.toLL(cx + w.x - w0.x, cy + w.y - w0.y); }
      else if (drag.mode === 'rot') { let d = Math.atan2(w.y - cy, w.x - cx) * 180 / Math.PI; if (ev.shiftKey) d = Math.round(d / 15) * 15; r.angle = d; }
      else {
        const along = drag.mode === 'len' ? [Math.cos(a), Math.sin(a)] : [-Math.sin(a), Math.cos(a)];
        const d = Math.abs((w.x - cx) * along[0] + (w.y - cy) * along[1]) * 2 / GEO.a;
        r[drag.mode] = Math.max(1, d);
      }
      drag.moved = true; E.redraw();
    },
    up() {
      if (draft) {
        const { a, b } = draft; draft = null;
        const wpx = Math.abs(b.x - a.x), hpx = Math.abs(b.y - a.y);
        if (wpx < 4 || hpx < 4) { E.redraw(); return; }
        const [lat, lon] = GEO.toLL((a.x + b.x) / 2, (a.y + b.y) / 2);
        E.change(() => { const B = E.layer('buildings'); (B.add = B.add || []).push({ lat: f7(lat), lon: f7(lon), len: f2(wpx / GEO.a), wid: f2(hpx / GEO.a), angle: 0, kind });
          E.sel = { tool: 'buildings', osm: false, idx: B.add.length - 1 }; }, 'Dodano budynek');
        E.refreshPanel(); return;
      }
      if (!drag) return;
      const d = drag; drag = null;
      if (d.moved) { E.change(() => writeRec(d.b, d.r), d.mode === 'move' ? 'Przesunięto budynek' : d.mode === 'rot' ? 'Obrócono budynek' : 'Zmieniono rozmiar'); E.refreshPanel(); }
    },
    keydown(ev) {
      const b = selRec();
      if (b && (ev.key === 'Delete' || ev.key === 'Backspace')) { del(b); return true; }
      if (b && /^Arrow/.test(ev.key)) {
        const s = ev.shiftKey ? 10 : 1, r = rect(b), [cx, cy] = GEO.P(r.lat, r.lon);
        const dx = ev.key === 'ArrowLeft' ? -s : ev.key === 'ArrowRight' ? s : 0, dy = ev.key === 'ArrowUp' ? -s : ev.key === 'ArrowDown' ? s : 0;
        const nr = Object.assign({}, r); [nr.lat, nr.lon] = GEO.toLL(cx + dx, cy + dy);
        E.change(() => writeRec(b, nr), 'Przesunięto budynek'); return true;
      }
      return false;
    },
    overlay(ctx) {
      const active = E.tool && E.tool.id === 'buildings', l = L();
      // removed OSM buildings: crossed out
      OSM.filter(o => removed(o.id)).forEach(o => {
        const c = corners(o); E.pathPoly(c); ctx.fillStyle = 'rgba(255,40,40,.25)'; ctx.fill();
        ctx.strokeStyle = '#ff4040'; ctx.lineWidth = E.px(1.5); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(...c[0]); ctx.lineTo(...c[2]); ctx.moveTo(...c[1]); ctx.lineTo(...c[3]); ctx.stroke();
      });
      all().forEach(b => {
        const edited = !b.osm || (l.modify || {})[b.id];
        if (!active && !edited) return;
        const r = drag && drag.b === b && drag.moved ? drag.r : rect(b);
        if (b.osm && edited) { E.pathPoly(corners(b)); ctx.setLineDash([E.px(3), E.px(3)]); ctx.strokeStyle = 'rgba(255,255,255,.6)'; ctx.lineWidth = E.px(1); ctx.stroke(); ctx.setLineDash([]); }
        E.pathPoly(corners(r));
        ctx.fillStyle = !b.osm ? 'rgba(80,200,255,.35)' : edited ? 'rgba(255,200,60,.35)' : 'rgba(255,255,255,.08)'; ctx.fill();
        ctx.strokeStyle = !b.osm ? '#50c8ff' : edited ? '#ffc83c' : 'rgba(255,255,255,.55)'; ctx.lineWidth = E.px(1.2); ctx.stroke();
      });
    },
    draw(ctx) {
      if (draft) {
        const { a, b } = draft; ctx.strokeStyle = '#50c8ff'; ctx.lineWidth = E.px(2); ctx.setLineDash([E.px(5), E.px(3)]);
        ctx.strokeRect(Math.min(a.x, b.x), Math.min(a.y, b.y), Math.abs(b.x - a.x), Math.abs(b.y - a.y)); ctx.setLineDash([]);
        ctx.font = `${E.px(12)}px system-ui`; ctx.fillStyle = '#fff';
        ctx.fillText(`${(Math.abs(b.x - a.x) / GEO.a).toFixed(1)} × ${(Math.abs(b.y - a.y) / GEO.a).toFixed(1)} m`, Math.max(a.x, b.x) + E.px(6), Math.max(a.y, b.y));
      }
      const b = selRec(); if (!b) return;
      const r = drag && drag.b === b && drag.moved ? drag.r : rect(b), hd = handles(r);
      E.pathPoly(corners(r)); ctx.strokeStyle = '#fff'; ctx.lineWidth = E.px(2.5); ctx.stroke();
      ctx.strokeStyle = '#fff'; ctx.lineWidth = E.px(1); ctx.beginPath(); ctx.moveTo(...hd.c); ctx.lineTo(...hd.rot); ctx.stroke();
      [hd.len, hd.wid].forEach(([x, y]) => { ctx.fillStyle = '#fff'; ctx.fillRect(x - E.px(5), y - E.px(5), E.px(10), E.px(10)); ctx.strokeStyle = '#000'; ctx.strokeRect(x - E.px(5), y - E.px(5), E.px(10), E.px(10)); });
      ctx.beginPath(); ctx.arc(hd.rot[0], hd.rot[1], E.px(6), 0, 7); ctx.fillStyle = '#ffc83c'; ctx.fill(); ctx.strokeStyle = '#000'; ctx.stroke();
      ctx.font = `${E.px(12)}px system-ui`; ctx.fillStyle = '#fff'; ctx.strokeStyle = '#000'; ctx.lineWidth = E.px(3);
      const t = `${f2(r.len)} × ${f2(r.wid)} m, ${f2(r.angle || 0)}°`; ctx.strokeText(t, hd.c[0] + E.px(8), hd.c[1] - E.px(8)); ctx.fillText(t, hd.c[0] + E.px(8), hd.c[1] - E.px(8));
    },
  });
  E.loadBuildings();
})();
