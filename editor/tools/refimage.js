/* Reference image (e.g. a Google Maps screenshot) laid over the map.
   Load a file, then calibrate with 2 point pairs: click a point on the image, then the same place on the map,
   twice. The similarity transform (scale, rotation, offset) is solved from the pairs.
   The image stays in this browser (localStorage when small enough); nothing is uploaded. */
(function () {
  const E = Editor;
  const R = { img: null, name: '', s: 1, rot: 0, tx: 0, ty: 0, opacity: .6, cal: null };
  const KEY = 'mapedit.ref';
  let move = null;

  // image px (u, v) -> world
  const fwd = (u, v) => { const c = Math.cos(R.rot) * R.s, s = Math.sin(R.rot) * R.s; return [R.tx + c * u - s * v, R.ty + s * u + c * v]; };
  const inv = (x, y) => { const dx = x - R.tx, dy = y - R.ty, c = Math.cos(-R.rot) / R.s, s = Math.sin(-R.rot) / R.s; return [c * dx - s * dy, s * dx + c * dy]; };
  function persist() {
    const meta = { name: R.name, s: R.s, rot: R.rot, tx: R.tx, ty: R.ty, opacity: R.opacity };
    try { localStorage.setItem(KEY, JSON.stringify(Object.assign(meta, { src: R.img && R.img.src.length < 4.5e6 ? R.img.src : null }))); }
    catch (e) { localStorage.setItem(KEY, JSON.stringify(meta)); }
  }
  function restore() {
    const d = JSON.parse(localStorage.getItem(KEY) || 'null'); if (!d) return;
    Object.assign(R, d);
    if (d.src) { const im = new Image(); im.onload = () => { R.img = im; E.redraw(); }; im.src = d.src; }
  }
  function load(file) {
    const fr = new FileReader();
    fr.onload = () => {
      const im = new Image();
      im.onload = () => {
        R.img = im; R.name = file.name; R.rot = 0;
        // first placement: fill ~60% of the current view, centred
        const vw = E.cv.clientWidth / E.view.z, vh = E.cv.clientHeight / E.view.z;
        R.s = Math.min(vw / im.width, vh / im.height) * .6;
        R.tx = E.view.x + (vw - im.width * R.s) / 2; R.ty = E.view.y + (vh - im.height * R.s) / 2;
        E.vis.ref = true; document.querySelector('[data-layer=ref]').checked = true;
        persist(); E.refreshPanel(); E.redraw(); E.status('Wczytano ' + file.name + '. Kalibruj: 2 pary punktów.');
      };
      im.src = fr.result;
    };
    fr.readAsDataURL(file);
  }
  function solve(u1, m1, u2, m2) {
    const du = [u2[0] - u1[0], u2[1] - u1[1]], dm = [m2[0] - m1[0], m2[1] - m1[1]];
    const lu = Math.hypot(...du), lm = Math.hypot(...dm);
    if (lu < 2 || lm < 2) return E.status('Punkty są za blisko siebie', true);
    R.s = lm / lu; R.rot = Math.atan2(dm[1], dm[0]) - Math.atan2(du[1], du[0]);
    const c = Math.cos(R.rot) * R.s, s = Math.sin(R.rot) * R.s;
    R.tx = m1[0] - (c * u1[0] - s * u1[1]); R.ty = m1[1] - (s * u1[0] + c * u1[1]);
    const mpp = R.s / GEO.a;   // metres per image pixel (art px per image px / art px per metre)
    E.status(`Skalibrowano: 1 px obrazu = ${mpp.toFixed(2)} m, szerokość obrazu ≈ ${Math.round(mpp * R.img.width)} m, obrót ${(R.rot * 180 / Math.PI).toFixed(1)}°`);
    persist();
  }
  const STEPS = ['Kliknij punkt 1 na OBRAZIE', 'Kliknij to samo miejsce na MAPIE (wyłącz obraz: suwak lub warstwa)', 'Kliknij punkt 2 na OBRAZIE', 'Kliknij to samo miejsce 2 na MAPIE'];

  E.registerTool({
    id: 'ref', label: 'Obraz', title: 'Własny screen jako podkład: wczytaj i skalibruj 2 punktami',
    activate() { restore(); },
    panel(el) {
      el.innerHTML = `<h3>Własny obraz</h3>
        <label class="btn" style="justify-content:center">Wczytaj obraz…<input id="rf-file" type="file" accept="image/*" hidden></label>
        <p class="hint">${R.img ? R.name : 'Brak obrazu'}</p>
        <label>Przezroczystość <input id="rf-op" type="range" min="0" max="1" step=".05" value="${R.opacity}"></label>
        <div class="row"><button id="rf-cal" ${R.img ? '' : 'disabled'}>Kalibruj 2 punktami</button><button id="rf-del" ${R.img ? '' : 'disabled'}>Usuń</button></div>
        <p id="rf-step" class="hint">${R.cal ? STEPS[R.cal.length] : 'Przeciągnij obraz lewym przyciskiem. Alt+kółko = skala, Shift+kółko = obrót.'}</p>`;
      el.querySelector('#rf-file').onchange = ev => ev.target.files[0] && load(ev.target.files[0]);
      el.querySelector('#rf-op').oninput = ev => { R.opacity = +ev.target.value; persist(); E.redraw(); };
      el.querySelector('#rf-cal').onclick = () => { R.cal = []; E.vis.ref = true; E.refreshPanel(); E.redraw(); };
      el.querySelector('#rf-del').onclick = () => { R.img = null; R.name = ''; localStorage.removeItem(KEY); E.refreshPanel(); E.redraw(); };
      el.querySelector('#rf-op').addEventListener('wheel', ev => ev.stopPropagation());
    },
    down(ev, w) {
      if (!R.img || ev.button !== 0) return;
      if (R.cal) {
        const i = R.cal.length;
        R.cal.push(i % 2 === 0 ? inv(w.x, w.y) : [w.x, w.y]);
        if (R.cal.length === 4) { const [u1, m1, u2, m2] = R.cal; R.cal = null; solve(u1, m1, u2, m2); }
        E.refreshPanel(); E.redraw(); return;
      }
      move = { x: w.x, y: w.y, tx: R.tx, ty: R.ty };
    },
    move(ev, w) { if (move) { R.tx = move.tx + w.x - move.x; R.ty = move.ty + w.y - move.y; E.redraw(); } },
    up() { if (move) { move = null; persist(); } },
    keydown(ev) { if (ev.key === 'Escape' && R.cal) { R.cal = null; E.refreshPanel(); return true; } return false; },
    underlay(ctx) {
      if (!E.vis.ref || !R.img) return;
      ctx.save(); ctx.globalAlpha = R.opacity;
      ctx.translate(R.tx, R.ty); ctx.rotate(R.rot); ctx.scale(R.s, R.s); ctx.drawImage(R.img, 0, 0);
      ctx.restore();
    },
    draw(ctx) {
      if (!R.cal) return;
      R.cal.forEach((p, i) => {
        const [x, y] = i % 2 === 0 ? fwd(p[0], p[1]) : p;
        ctx.strokeStyle = i % 2 === 0 ? '#ff40ff' : '#40ffff'; ctx.lineWidth = E.px(2);
        ctx.beginPath(); ctx.moveTo(x - E.px(10), y); ctx.lineTo(x + E.px(10), y); ctx.moveTo(x, y - E.px(10)); ctx.lineTo(x, y + E.px(10)); ctx.stroke();
      });
    },
  });
  // Alt+wheel scales, Shift+wheel rotates the reference image around the cursor while the tool is active
  E.cv.addEventListener('wheel', ev => {
    if (!E.tool || E.tool.id !== 'ref' || !R.img || !(ev.altKey || ev.shiftKey)) return;
    ev.stopImmediatePropagation(); ev.preventDefault();
    const w = E.cursor, [u, v] = inv(w.x, w.y);
    if (ev.altKey) R.s *= Math.exp(-ev.deltaY * .001); else R.rot += ev.deltaY * .0015;
    const [nx, ny] = fwd(u, v); R.tx += w.x - nx; R.ty += w.y - ny; persist(); E.redraw();
  }, { passive: false, capture: true });
  restore();
})();
