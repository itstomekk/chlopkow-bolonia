/* Entities: drag NPCs, landmarks and minigame venues. Stored as layers.entities["kind:id"] = {lat, lon}.
   The overlay shows the generated position, and an arrow to the override when one exists. */
(function () {
  const E = Editor;
  const COL = { npc: '#ffd23f', landmark: '#7fd0ff', venue: '#ff7fd0' };
  let drag = null;
  const pos = en => { const o = (E.peek('entities'))[en.key]; return o ? GEO.P(o.lat, o.lon) : [en.x, en.y]; };
  function pick(w) {
    let best = null, bd = Math.max(E.px(12), 10);
    (E.entities || []).forEach(en => { const [x, y] = pos(en), d = Math.hypot(x - w.x, y - w.y); if (d < bd) { bd = d; best = en; } });
    return best;
  }
  E.registerTool({
    id: 'entities', label: 'Postacie', title: 'Przeciągnij postać, miejsce lub minigrę',
    panel(el) {
      const en = E.sel && E.sel.tool === 'entities' ? (E.entities || []).find(e => e.key === E.sel.key) : null;
      const n = Object.keys(E.peek('entities')).length;
      let h = `<h3>Postacie i miejsca</h3><p>Przeciągnij znacznik. Żółte = postacie, niebieskie = miejsca, różowe = minigry.</p><p class="hint">Przesuniętych: ${n}</p>`;
      if (en) {
        const [x, y] = pos(en), moved = !!E.peek('entities')[en.key];
        h += `<p><b>${en.label}</b><br><code>${en.key}</code><br>${Math.round(x)}, ${Math.round(y)} ${moved ? '(przesunięte)' : ''}</p>`;
        if (moved) h += `<button id="en-reset">Przywróć pozycję z generatora</button>`;
      }
      el.innerHTML = h;
      const b = el.querySelector('#en-reset');
      if (b) b.onclick = () => { const k = en.key; E.change(e => { delete e.layers.entities[k]; }, 'Przywrócono ' + en.label); E.refreshPanel(); };
    },
    down(ev, w) {
      if (ev.button !== 0) return;
      const en = pick(w);
      E.sel = en ? { tool: 'entities', key: en.key } : null; E.refreshPanel();
      if (en) drag = { en, x: w.x, y: w.y, moved: false };
      E.redraw();
    },
    move(ev, w) { if (drag) { drag.x = w.x; drag.y = w.y; drag.moved = true; E.redraw(); } },
    up() {
      if (!drag) return;
      const d = drag; drag = null;
      if (!d.moved) return;
      const [lat, lon] = GEO.toLL(d.x, d.y);
      E.change(() => { E.layer('entities')[d.en.key] = { lat: +lat.toFixed(7), lon: +lon.toFixed(7) }; }, `Przesunięto ${d.en.label}`);
      E.refreshPanel();
    },
    keydown(ev) {
      if ((ev.key === 'Delete' || ev.key === 'Backspace') && E.sel && E.sel.tool === 'entities' && E.peek('entities')[E.sel.key]) {
        const k = E.sel.key; E.change(e => { delete e.layers.entities[k]; }, 'Przywrócono pozycję'); E.refreshPanel(); return true;
      }
      return false;
    },
    entityOverlay(ctx) {
      const r = Math.max(E.px(6), 4), showLabels = E.view.z > .2;
      ctx.font = `${E.px(11)}px system-ui`;
      (E.entities || []).forEach(en => {
        const moved = E.peek('entities')[en.key];
        let [x, y] = pos(en);
        if (drag && drag.en === en && drag.moved) [x, y] = [drag.x, drag.y];
        if (moved || (drag && drag.en === en && drag.moved)) {
          ctx.strokeStyle = '#fff'; ctx.lineWidth = E.px(1.5); ctx.setLineDash([E.px(4), E.px(3)]);
          ctx.beginPath(); ctx.moveTo(en.x, en.y); ctx.lineTo(x, y); ctx.stroke(); ctx.setLineDash([]);
          ctx.strokeStyle = COL[en.kind]; ctx.beginPath(); ctx.arc(en.x, en.y, r * .7, 0, 7); ctx.stroke();
        }
        const sel = E.sel && E.sel.key === en.key;
        ctx.fillStyle = COL[en.kind]; ctx.strokeStyle = sel ? '#fff' : '#000'; ctx.lineWidth = E.px(sel ? 3 : 1.5);
        ctx.beginPath(); ctx.arc(x, y, r, 0, 7); ctx.fill(); ctx.stroke();
        if (showLabels || sel) { ctx.fillStyle = '#fff'; ctx.strokeStyle = '#000'; ctx.lineWidth = E.px(3); ctx.strokeText(en.label, x + r + E.px(3), y + E.px(4)); ctx.fillText(en.label, x + r + E.px(3), y + E.px(4)); }
      });
    },
  });
})();
