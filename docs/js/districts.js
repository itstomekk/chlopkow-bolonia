/* Local customary areas from Tomek's approximate source map, not official boundaries. */
'use strict';
(() => {
  function contains(ring, x, y) {
    if (!Number.isFinite(x) || !Number.isFinite(y)) return false;
    let inside = false;
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const [ax, ay] = ring[j], [bx, by] = ring[i];
      const cross = (x - ax) * (by - ay) - (y - ay) * (bx - ax);
      if (Math.abs(cross) < 1e-7 && x >= Math.min(ax, bx) - 1e-7 && x <= Math.max(ax, bx) + 1e-7 && y >= Math.min(ay, by) - 1e-7 && y <= Math.max(ay, by) + 1e-7) return true;
      if ((ay > y) !== (by > y) && x < (bx - ax) * (y - ay) / (by - ay) + ax) inside = !inside;
    }
    return inside;
  }

  function project(map, coordinate) {
    if (!Array.isArray(coordinate) || coordinate.length !== 2 || !coordinate.every(v => typeof v === 'number' && Number.isFinite(v))) throw new Error('Invalid district coordinate');
    const [minLat, minLon, maxLat] = map.bbox;
    const mx = 111320 * Math.cos((minLat + maxLat) / 2 * Math.PI / 180);
    return [(coordinate[0] - minLon) * mx * map.scale, (maxLat - coordinate[1]) * 110574 * map.scale];
  }

  function prepare(data, map) {
    if (data.approximate !== true) throw new Error('District data must be approximate');
    if (data.version !== 1 || !Array.isArray(data.districts) || !data.districts.length) throw new Error('Invalid district data');
    const ids = new Set();
    return data.districts.map(d => {
      if (typeof d.id !== 'string' || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(d.id) || ids.has(d.id)) throw new Error('Invalid or duplicate district id');
      ids.add(d.id);
      if (typeof d.name !== 'string' || !d.name.trim() || d.name.length > 64 || !/^#[0-9a-f]{6}$/i.test(d.color)) throw new Error('Invalid district name or color');
      if (!Array.isArray(d.polygon) || d.polygon.length < 3) throw new Error('Invalid district polygon');
      const polygon = d.polygon.map(point => project(map, point));
      const label = project(map, d.label);
      if (!contains(polygon, ...label)) throw new Error('District label must be inside its polygon');
      const xs = polygon.map(p => p[0]), ys = polygon.map(p => p[1]);
      return { id: d.id, name: d.name, color: d.color, polygon, label,
        bounds: [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)] };
    });
  }

  function at(districts, x, y) {
    return districts.find(d => x >= d.bounds[0] && y >= d.bounds[1] && x <= d.bounds[2] && y <= d.bounds[3] && contains(d.polygon, x, y)) || null;
  }

  window.ARK_DISTRICTS = { contains, project, prepare, at };

  function install() {
    const A = window.ARK;
    if (!A || window.__districts) return;
    const ctx = A.ctx, game = window.__game;
    let status = 'loading', error = '', regions = [], current = null, pending = null, pendingTime = 0;
    let lastBadge = { shown: false }, lastLabels = [], lastBounds = null, layoutKey = '', cachedLabels = [];
    const statusNode = document.createElement('span');
    statusNode.id = 'district-name-status';
    statusNode.setAttribute('role', 'status');
    statusNode.setAttribute('aria-live', 'polite');
    statusNode.style.cssText = 'position:fixed;width:1px;height:1px;overflow:hidden;clip-path:inset(50%);pointer-events:none';
    document.body.appendChild(statusNode);
    const outdoor = () => A.scene === 'play' && !A.room && !A.talk && !A.HOOKS.busy.some(f => f());
    const badgeVisible = () => outdoor() && !game.showMap && status === 'ready' && current;
    const mapVisible = () => outdoor() && game.showMap;

    function words(text, maxWidth) {
      const lines = []; let line = '';
      for (const word of text.split(' ')) {
        const next = line ? line + ' ' + word : word;
        if (line && ctx.measureText(next).width > maxWidth) { lines.push(line); line = word; }
        else line = next;
      }
      if (line) lines.push(line);
      return lines;
    }

    function badge(U, W) {
      const ratio = W / Math.max(1, window.innerWidth);
      const font = Math.max(9 * ratio, U * 1.25), mw = U * 16;
      ctx.font = `${font}px PixelifySans`;
      const maxWidth = Math.max(mw, W * .32) - U * 2;
      const lines = words(current.name, maxWidth), pad = U * .8;
      const w = Math.max(...lines.map(line => ctx.measureText(line).width)) + pad * 2;
      return { shown: true, text: current.name, lines, font, x: W - U * 2 - w,
        y: U * 3 + mw * A.MAP.h / A.MAP.w, w, h: lines.length * font * 1.3 + pad * 2, pad };
    }

    const overlaps = (a, b, gap = 2) => a.x < b.x + b.w + gap && a.x + a.w + gap > b.x && a.y < b.y + b.h + gap && a.y + a.h + gap > b.y;

    function labels(U, W, H, bounds) {
      const ratio = W / Math.max(1, window.innerWidth), font = Math.max(8 * ratio, Math.min(12 * ratio, U * 1.4));
      const key = [W, H, font, regions.length].join(':');
      if (key === layoutKey) return cachedLabels;
      ctx.font = `${font}px PixelifySans`;
      const result = [], margin = Math.max(3 * ratio, U * .5), lineHeight = font * 1.3;
      const inner = { x: bounds.x + margin, y: bounds.y + font * 3.5,
        w: bounds.w - margin * 2, h: bounds.h - font * 3.5 - margin };
      const sorted = regions.slice().sort((a, b) => a.label[1] - b.label[1] || a.label[0] - b.label[0]);
      for (const r of sorted) {
        const lines = words(r.name, Math.min(inner.w * .55, 160 * ratio));
        const w = Math.max(...lines.map(line => ctx.measureText(line).width)) + margin * 2, h = lines.length * lineHeight + margin;
        const anchor = [bounds.x + r.label[0] / A.MAP.w * bounds.w, bounds.y + r.label[1] / A.MAP.h * bounds.h];
        let best = null;
        // Search near the true anchor, then the whole map. Never drop a name silently.
        for (let y = inner.y; y + h <= inner.y + inner.h; y += lineHeight + margin) {
          for (let x = inner.x; x + w <= inner.x + inner.w; x += Math.max(8 * ratio, font)) {
            const candidate = { x, y, w, h };
            if (result.some(other => overlaps(candidate, other, margin))) continue;
            const score = (x + w / 2 - anchor[0]) ** 2 + (y + h / 2 - anchor[1]) ** 2;
            if (!best || score < best.score) best = { ...candidate, score };
          }
        }
        if (!best) throw new Error('District names do not fit the map');
        result.push({ id: r.id, name: r.name, color: r.color, ...best, lines, font, lineHeight, margin, anchor });
      }
      layoutKey = key; cachedLabels = result;
      return result;
    }

    A.HOOKS.update.push(dt => {
      if (status !== 'ready' || A.room) { current = null; pending = null; pendingTime = 0; return; }
      const candidate = at(regions, A.P.x, A.P.y);
      if ((candidate && candidate.id) === (current && current.id)) { pending = null; pendingTime = 0; return; }
      if ((candidate && candidate.id) !== (pending && pending.id)) { pending = candidate; pendingTime = 0; }
      pendingTime += dt;
      if (pendingTime >= .25) { current = candidate; pending = null; pendingTime = 0; }
    });

    A.HOOKS.hud.push((U, W, H) => {
      lastBadge = { shown: false }; lastLabels = [];
      ctx.save(); ctx.textBaseline = 'middle';
      if (badgeVisible()) {
        const b = lastBadge = badge(U, W);
        ctx.fillStyle = 'rgba(8,12,40,.65)'; ctx.fillRect(b.x, b.y, b.w, b.h);
        ctx.font = `${b.font}px PixelifySans`; ctx.textAlign = 'right'; ctx.fillStyle = '#fff7d6';
        b.lines.forEach((line, i) => ctx.fillText(line, b.x + b.w - b.pad, b.y + b.pad + b.font * .65 + i * b.font * 1.3));
      }
      if (mapVisible()) {
        const mw = Math.min(W * .8, H * .8 * A.MAP.w / A.MAP.h), mh = mw * A.MAP.h / A.MAP.w;
        const bounds = lastBounds = { x: (W - mw) / 2, y: (H - mh) / 2, w: mw, h: mh };
        const ratio = W / Math.max(1, window.innerWidth), font = Math.max(8 * ratio, Math.min(12 * ratio, U * 1.4));
        ctx.font = `${font}px PixelifySans`; ctx.textAlign = 'center'; ctx.lineWidth = Math.max(2, ratio * 3); ctx.strokeStyle = '#10163a';
        const note = status === 'error' ? (A.LANG === 'en' ? 'AREA NAMES UNAVAILABLE' : 'NAZWY OKOLIC NIEDOSTĘPNE')
          : status === 'loading' ? (A.LANG === 'en' ? 'LOADING AREA NAMES' : 'ŁADOWANIE NAZW OKOLIC')
            : (A.LANG === 'en' ? 'LOCAL AREAS · APPROXIMATE BOUNDARIES' : 'OKOLICE · GRANICE ORIENTACYJNE');
        words(note, bounds.w - U * 2).forEach((line, i) => {
          const y = bounds.y + font * (1.1 + i * 1.3);
          ctx.strokeText(line, W / 2, y); ctx.fillStyle = '#fff7d6'; ctx.fillText(line, W / 2, y);
        });
        if (status === 'ready') {
          const all = lastLabels = labels(U, W, H, bounds);
          ctx.beginPath(); ctx.rect(bounds.x, bounds.y, bounds.w, bounds.h); ctx.clip();
          for (const label of all) {
            const tx = label.x + label.w / 2, ty = label.y + label.h / 2;
            ctx.beginPath(); ctx.moveTo(...label.anchor); ctx.lineTo(tx, ty);
            ctx.strokeStyle = label.color; ctx.lineWidth = Math.max(1, ratio); ctx.globalAlpha = .75; ctx.stroke(); ctx.globalAlpha = 1;
          }
          for (const label of all) {
            ctx.font = `${label.font}px PixelifySans`; ctx.strokeStyle = '#10163a'; ctx.lineWidth = Math.max(3 * ratio, 2);
            label.lines.forEach((line, i) => {
              const x = label.x + label.w / 2, y = label.y + label.margin / 2 + label.lineHeight * (i + .5);
              ctx.strokeText(line, x, y); ctx.fillStyle = '#fff7d6'; ctx.fillText(line, x, y);
            });
          }
        }
      }
      ctx.restore();
      const announced = badgeVisible() ? current.name : '';
      if (statusNode.textContent !== announced) statusNode.textContent = announced;
    });

    window.__districts = {
      get status() { return status; }, get error() { return error; }, get regions() { return regions; },
      get current() { return A.room ? null : current; }, at: (x, y) => at(regions, x, y),
      get badge() { return badgeVisible() ? lastBadge : { shown: false }; },
      get mapLabels() { return mapVisible() ? lastLabels : []; }, get mapBounds() { return lastBounds; },
    };
    const controller = new AbortController(), timeout = setTimeout(() => controller.abort(), 8000);
    fetch('data/districts.json', { signal: controller.signal }).then(response => {
      if (!response.ok) throw new Error(`District data HTTP ${response.status}`);
      return response.json();
    }).then(data => { regions = prepare(data, A.MAP); status = 'ready'; })
      .catch(e => { status = 'error'; error = e.message; console.warn('District names unavailable:', error); })
      .finally(() => clearTimeout(timeout));
  }

  const schedule = () => window.queueMicrotask(install);
  window.addEventListener('ark-ready', schedule, { once: true });
  if (window.ARK) schedule();
})();
