/* Polygon tools. One factory, many layers: add a new polygon edit type by adding one entry to TOOLS below
   (and its layer in osm/edits.py).
   Klik = punkt, Enter/dwuklik = zamknij, Backspace = cofnij punkt, Esc = anuluj,
   klik w istniejący obszar = zaznacz, przeciągnij wierzchołek = popraw, Delete = usuń. */
(function () {
  const E = Editor;
  const ZONE_COLORS = { music: '#b070ff', animals: '#ffb040', people: '#40c0ff', custom: '#d0d0d0' };
  const TOOLS = [
    { id: 'clear', label: 'Usuń drzewa', layer: 'trees', key: 'clear', color: '#ff8a30', title: 'Obszar, w którym generator nie stawia drzew (np. brzeg rzeki)' },
    { id: 'forest+', label: 'Las +', layer: 'forest', key: 'add', color: '#30c050', title: 'Dodaj las (gęsta korona, można chodzić między pniami)' },
    { id: 'forest-', label: 'Las −', layer: 'forest', key: 'remove', color: '#e05050', title: 'Usuń las z OSM w tym obszarze' },
    { id: 'water', label: 'Woda', layer: 'water', key: 'add', color: '#3a8ef0', title: 'Staw / oczko wodne (z kolizją)', fields: [['name', 'Nazwa']] },
    { id: 'block', label: 'Blokada', layer: 'collision', key: 'block', color: '#ff3030', title: 'Tu nie da się przejść (drogi zawsze przejezdne)' },
    { id: 'free', label: 'Przejście', layer: 'collision', key: 'free', color: '#30ff90', title: 'Tu da się przejść mimo kolizji z generatora' },
    { id: 'zones', label: 'Strefy', layer: 'zones', key: 'items', color: '#b070ff', title: 'Strefy: muzyka, zwierzęta, ludzie (gra czyta je w kolejnej wersji)', zone: true },
  ];
  const zoneOpt = { kind: 'music', id: '', props: '{"track": "jazz"}' };

  function list(cfg) { return (E.peek(cfg.layer)[cfg.key]) || []; }
  function colorOf(cfg, o) { return cfg.zone ? ZONE_COLORS[o.kind] || cfg.color : cfg.color; }
  function hex2rgba(h, a) { const n = parseInt(h.slice(1), 16); return `rgba(${n >> 16},${(n >> 8) & 255},${n & 255},${a})`; }

  TOOLS.forEach(cfg => {
    let draft = [], dragV = null;
    const selected = () => E.sel && E.sel.tool === cfg.id ? list(cfg)[E.sel.i] : null;
    const pickVertex = w => {
      const o = selected(); if (!o) return -1;
      const r = Math.max(E.px(8), 3);
      return o.poly.findIndex(([la, lo]) => { const [x, y] = GEO.P(la, lo); return Math.hypot(x - w.x, y - w.y) < r; });
    };
    function close() {
      if (draft.length < 3) { E.status('Wielokąt potrzebuje co najmniej 3 punktów', true); return; }
      const poly = draft.map(([x, y]) => GEO.toLL(x, y).map(v => +v.toFixed(7)));
      const item = { poly };
      if (cfg.zone) {
        let props = {};
        try { props = zoneOpt.props.trim() ? JSON.parse(zoneOpt.props) : {}; } catch (e) { E.status('Props: niepoprawny JSON', true); return; }
        item.kind = zoneOpt.kind; item.id = zoneOpt.id.trim() || `${zoneOpt.kind}-${list(cfg).length + 1}`; item.props = props;
      }
      (cfg.fields || []).forEach(([k]) => { const v = (cfg['_' + k] || '').trim(); if (v) item[k] = v; });
      E.change(() => { const L = E.layer(cfg.layer); (L[cfg.key] = L[cfg.key] || []).push(item); E.sel = { tool: cfg.id, i: L[cfg.key].length - 1 }; }, `${cfg.label}: dodano obszar`);
      draft = []; E.refreshPanel();
    }
    function drawPoly(ctx, o, isSel) {
      const pts = GEO.polyPx(o.poly), c = colorOf(cfg, o);
      E.pathPoly(pts);
      ctx.fillStyle = hex2rgba(c, isSel ? .35 : .2); ctx.fill();
      ctx.strokeStyle = c; ctx.lineWidth = E.px(isSel ? 2.5 : 1.5); ctx.setLineDash(cfg.id === 'forest-' || cfg.id === 'clear' ? [E.px(6), E.px(4)] : []); ctx.stroke(); ctx.setLineDash([]);
      const label = o.name || o.id;
      if (label && E.view.z > .15) {
        const cx = pts.reduce((s, p) => s + p[0], 0) / pts.length, cy = pts.reduce((s, p) => s + p[1], 0) / pts.length;
        ctx.font = `${E.px(12)}px system-ui`; ctx.fillStyle = '#fff'; ctx.strokeStyle = '#000'; ctx.lineWidth = E.px(3);
        ctx.strokeText(label, cx, cy); ctx.fillText(label, cx, cy);
      }
      if (isSel) pts.forEach(([x, y]) => { ctx.fillStyle = '#fff'; ctx.fillRect(x - E.px(4), y - E.px(4), E.px(8), E.px(8)); ctx.strokeStyle = c; ctx.lineWidth = E.px(1.5); ctx.strokeRect(x - E.px(4), y - E.px(4), E.px(8), E.px(8)); });
    }

    E.registerTool({
      id: cfg.id, label: cfg.label, title: cfg.title,
      activate() { draft = []; },
      deactivate() { draft = []; },
      panel(el) {
        const o = selected();
        let h = `<h3>${cfg.label}</h3><p>${cfg.title}</p><p class="hint">Klik = punkt, Enter / dwuklik = zamknij, Backspace = cofnij punkt, klik w obszar = zaznacz, Delete = usuń. Obszarów: ${list(cfg).length}</p>`;
        if (cfg.zone) h += `<label>Rodzaj <select id="z-kind">${Object.keys(ZONE_COLORS).map(k => `<option ${k === (o ? o.kind : zoneOpt.kind) ? 'selected' : ''}>${k}</option>`).join('')}</select></label>
          <label>Id <input id="z-id" value="${(o ? o.id : zoneOpt.id).replace(/"/g, '&quot;')}" placeholder="np. jazz-w-stodole"></label>
          <label style="display:block">Props (JSON)<textarea id="z-props">${JSON.stringify(o ? o.props || {} : JSON.parse(zoneOpt.props || '{}'), null, 1)}</textarea></label>
          <p class="hint">Przykłady: music {"track":"jazz"}, animals {"species":["kura"],"count":6}, people {"npc":["marcin"]}.</p>`;
        (cfg.fields || []).forEach(([k, lbl]) => { h += `<label>${lbl} <input id="f-${k}" value="${((o ? o[k] : cfg['_' + k]) || '').replace(/"/g, '&quot;')}"></label>`; });
        if (o) h += `<div class="row"><button id="p-apply">Zapisz pola</button><button id="p-del">Usuń obszar</button></div>`;
        el.innerHTML = h;
        const read = () => {
          if (cfg.zone) { zoneOpt.kind = el.querySelector('#z-kind').value; zoneOpt.id = el.querySelector('#z-id').value; zoneOpt.props = el.querySelector('#z-props').value; }
          (cfg.fields || []).forEach(([k]) => { cfg['_' + k] = el.querySelector('#f-' + k).value; });
        };
        el.querySelectorAll('input,select,textarea').forEach(i => i.addEventListener('input', read));
        if (o) {
          el.querySelector('#p-del').onclick = () => { const i = E.sel.i; E.sel = null; E.change(() => E.layer(cfg.layer)[cfg.key].splice(i, 1), 'Usunięto obszar'); E.refreshPanel(); };
          el.querySelector('#p-apply').onclick = () => {
            read(); const i = E.sel.i;
            let props;
            if (cfg.zone) { try { props = JSON.parse(zoneOpt.props || '{}'); } catch (e) { return E.status('Props: niepoprawny JSON', true); } }
            E.change(() => {
              const it = E.layer(cfg.layer)[cfg.key][i];
              if (cfg.zone) Object.assign(it, { kind: zoneOpt.kind, id: zoneOpt.id.trim() || it.id, props });
              (cfg.fields || []).forEach(([k]) => { const v = (cfg['_' + k] || '').trim(); if (v) it[k] = v; else delete it[k]; });
            }, 'Zapisano pola');
          };
        }
      },
      down(ev, w) {
        if (ev.button !== 0) return;
        if (!draft.length) {
          const v = pickVertex(w);
          if (v >= 0) { dragV = { v, before: JSON.stringify(E.edits) }; return; }
          const hit = list(cfg).map((o, i) => [o, i]).reverse().find(([o]) => E.pointInPoly(w.x, w.y, GEO.polyPx(o.poly)));
          if (hit && !ev.shiftKey) { E.sel = { tool: cfg.id, i: hit[1] }; E.refreshPanel(); E.redraw(); return; }
          if (E.sel) { E.sel = null; E.refreshPanel(); }
        }
        draft.push([w.x, w.y]); E.redraw();
      },
      move(ev, w) {
        if (!dragV) return;
        const o = selected(); o.poly[dragV.v] = GEO.toLL(w.x, w.y).map(v => +v.toFixed(7)); E.redraw();
      },
      up() {
        if (!dragV) return;
        const after = JSON.parse(JSON.stringify(E.edits)); E.edits = JSON.parse(dragV.before); dragV = null;
        E.change(e => { e.layers = after.layers; }, 'Przesunięto wierzchołek');
      },
      dbl() { if (draft.length >= 2) { const a = draft[draft.length - 1], b = draft[draft.length - 2]; if (Math.hypot(a[0] - b[0], a[1] - b[1]) < E.px(6)) draft.pop(); } close(); },
      keydown(ev) {
        if (ev.key === 'Enter' && draft.length) { close(); return true; }
        if (ev.key === 'Backspace' && draft.length) { draft.pop(); return true; }
        if (ev.key === 'Escape' && draft.length) { draft = []; return true; }
        if ((ev.key === 'Delete' || ev.key === 'Backspace') && selected()) { const i = E.sel.i; E.sel = null; E.change(() => E.layer(cfg.layer)[cfg.key].splice(i, 1), 'Usunięto obszar'); E.refreshPanel(); return true; }
        return false;
      },
      overlay(ctx) { list(cfg).forEach((o, i) => drawPoly(ctx, o, E.sel && E.sel.tool === cfg.id && E.sel.i === i)); },
      draw(ctx) {
        if (!draft.length) return;
        const pts = draft.concat([[E.cursor.x, E.cursor.y]]);
        E.pathPoly(pts, false); ctx.strokeStyle = cfg.color; ctx.lineWidth = E.px(2); ctx.stroke();
        if (pts.length > 2) { E.pathPoly(pts); ctx.fillStyle = hex2rgba(cfg.color, .15); ctx.fill(); }
        draft.forEach(([x, y]) => { ctx.fillStyle = cfg.color; ctx.fillRect(x - E.px(3), y - E.px(3), E.px(6), E.px(6)); });
      },
    });
  });
})();
