/* Single trees: click adds a tree (layer trees.add), right click / Alt+click removes the nearest added tree.
   Removing generated trees in an area is the polygon tool "Usuń drzewa" (trees.clear). */
(function () {
  const E = Editor;
  const opt = { r: 11, dark: false };
  function nearest(w) {
    const list = E.peek('trees').add || [];
    let best = -1, bd = Infinity;
    list.forEach((t, i) => { const [x, y] = GEO.P(t.lat, t.lon), d = Math.hypot(x - w.x, y - w.y); if (d < bd) { bd = d; best = i; } });
    return bd < Math.max(E.px(12), 14) ? best : -1;
  }
  function drawTree(ctx, x, y, r, dark, ghost) {
    ctx.globalAlpha = ghost ? .5 : 1;
    ctx.fillStyle = dark ? '#1e5a2a' : '#3f8f3a'; ctx.strokeStyle = '#fff'; ctx.lineWidth = E.px(1.5);
    ctx.beginPath(); ctx.arc(x, y - r * .6, r, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    ctx.fillStyle = '#6b4a2b'; ctx.fillRect(x - r * .15, y - r * .2, r * .3, r * .5);
    ctx.globalAlpha = 1;
  }
  E.registerTool({
    id: 'trees', label: 'Drzewo', title: 'Klik = dodaj drzewo, prawy/Alt+klik = usuń dodane', wantsRight: true,
    panel(el) {
      el.innerHTML = `<h3>Drzewo</h3>
        <label>Promień <input id="tr-r" type="range" min="5" max="20" value="${opt.r}"> <span id="tr-rv">${opt.r}</span></label>
        <label><input id="tr-d" type="checkbox" ${opt.dark ? 'checked' : ''}> ciemne</label>
        <p>Klik dodaje drzewo. Prawy klik lub Alt+klik usuwa dodane. Istniejące drzewa z generatora usuwasz narzędziem „Usuń drzewa”.</p>
        <p class="hint">Dodanych: ${(E.peek('trees').add || []).length}</p>`;
      el.querySelector('#tr-r').oninput = ev => { opt.r = +ev.target.value; el.querySelector('#tr-rv').textContent = opt.r; E.redraw(); };
      el.querySelector('#tr-d').onchange = ev => { opt.dark = ev.target.checked; };
    },
    down(ev, w) {
      if (ev.button === 2 || ev.altKey) {
        const i = nearest(w); if (i < 0) return;
        E.change(e => { e.layers.trees.add.splice(i, 1); }, 'Usunięto drzewo'); E.refreshPanel(); return;
      }
      if (ev.button !== 0) return;
      const [lat, lon] = GEO.toLL(w.x, w.y);
      E.change(() => { const L = E.layer('trees'); (L.add = L.add || []).push({ lat: +lat.toFixed(7), lon: +lon.toFixed(7), r: opt.r, dark: opt.dark }); }, 'Dodano drzewo');
      E.refreshPanel();
    },
    overlay(ctx) { (E.peek('trees').add || []).forEach(t => { const [x, y] = GEO.P(t.lat, t.lon); drawTree(ctx, x, y, t.r || 11, t.dark); }); },
    draw(ctx) {
      const i = nearest(E.cursor);
      if (i >= 0) { const t = E.edits.layers.trees.add[i], [x, y] = GEO.P(t.lat, t.lon); ctx.strokeStyle = '#ff4040'; ctx.lineWidth = E.px(2); ctx.beginPath(); ctx.arc(x, y - (t.r || 11) * .6, (t.r || 11) + E.px(4), 0, 7); ctx.stroke(); }
      drawTree(ctx, E.cursor.x, E.cursor.y, opt.r, opt.dark, true);
    },
  });
})();
