/* Village shop interior + a standalone, Polish groszowy shopping challenge.
   Drawn from the supplied shop photos as anonymous pixel art; no real person or brand art. */
'use strict';

window.buildShop = function buildShop() {
  const W = 320, H = 440;
  const makeCanvas = () => { const c = document.createElement('canvas'); c.width = W; c.height = H; return c; };
  const ground = makeCanvas(), obj = makeCanvas();
  const g = ground.getContext('2d'), o = obj.getContext('2d');
  const solid = new Uint8Array(W * H), objects = [];
  const R = (c, x, y, w, h, color) => { c.fillStyle = color; c.fillRect(x, y, w, h); };
  const block = (x, y, w, h) => {
    const x0 = Math.max(0, x | 0), x1 = Math.min(W, (x + w) | 0);
    for (let yy = Math.max(0, y | 0); yy < Math.min(H, (y + h) | 0); yy++) solid.fill(2, yy * W + x0, yy * W + x1);
  };
  const put = (x, y, w, h, base) => objects.push({ x, y, w, h, base });
  let seed = 19;
  const rnd = () => (seed = seed * 16807 % 2147483647) / 2147483647;

  // Narrow aisle: warm square tiles, darker grout and occasional scuffs.
  for (let y = 108; y < H; y += 16) for (let x = 0; x < W; x += 16) {
    R(g, x, y, 16, 16, ((x / 16 + y / 16) | 0) % 2 ? '#d8c9aa' : '#e4d7bd');
    R(g, x, y, 16, 1, '#b9a987'); R(g, x, y, 1, 16, '#b9a987');
    if (rnd() < .2) R(g, x + 4 + (rnd() * 7 | 0), y + 5 + (rnd() * 7 | 0), 2, 1, '#eee5d1');
  }
  R(g, 0, 0, W, 108, '#d9c9ab');
  for (let y = 8; y < 108; y += 20) R(g, 0, y, W, 1, 'rgba(112,83,53,.12)');
  // Back wall, narrow side walls, and an open doorway at the south end.
  R(g, 0, 0, W, 8, '#6a4229'); R(g, 0, 104, W, 4, '#785239');
  R(g, 0, 108, 7, 320, '#8a6545'); R(g, W - 7, 108, 7, 320, '#8a6545');
  R(g, 0, 428, 136, 12, '#765139'); R(g, 184, 428, 136, 12, '#765139');
  R(g, 136, 428, 48, 12, '#3a291e');
  block(0, 0, W, 108); block(0, 0, 7, H); block(W - 7, 0, 7, H);
  block(0, 428, 136, 12); block(184, 428, 136, 12);

  // Two dark wooden, tightly stocked wall shelves. Shelf stock is original generic packaging.
  const shelf = (x, y, w) => {
    R(o, x, y, w, 6, '#51331f'); R(o, x + 2, y + 6, w - 4, 5, '#98683b');
    R(o, x, y + 10, w, 4, '#55361f'); R(o, x + 2, y + 13, w - 4, 6, '#98683b');
    R(o, x, y + 18, w, 4, '#51331f');
    const packCols = ['#c94a34', '#e0bc77', '#538b4a', '#e7dfcb', '#466987', '#ad743c', '#d3c9b6'];
    for (let row = 0; row < 2; row++) for (let px = x + 5; px < x + w - 6; px += 11) {
      const height = 8 + (px % 3) * 2, py = y - height + 6 + row * 11;
      R(o, px, py, 7, height, packCols[(px + row * 2) % packCols.length]);
      R(o, px + 1, py + 2, 5, 1, '#f1e5c8');
    }
    // White scalloped lace edge, rendered as tiny stepped pixels.
    R(o, x - 1, y + 4, w + 2, 2, '#f4f0e7');
    for (let px = x; px < x + w; px += 4) { R(o, px, y + 6, 2, 2, '#fffdf7'); R(o, px + 2, y + 7, 2, 1, '#e7dfd1'); }
    put(x - 2, y - 22, w + 4, 31, y + 10); block(x, y - 2, w, 24);
  };
  shelf(12, 150, 94); shelf(214, 150, 94);
  shelf(12, 204, 94); shelf(214, 204, 94);
  // Lace-trimmed high stock shelves on the back wall.
  shelf(111, 82, 98);

  // White upright cooler along the left wall, with lit glass, pale shelves and simple goods.
  R(o, 10, 238, 48, 119, '#f2f1e9'); R(o, 13, 241, 42, 112, '#d5d9d7');
  R(o, 16, 244, 36, 105, '#f7f7f0'); R(o, 16, 244, 36, 8, '#cbd5d5'); R(o, 16, 346, 36, 7, '#adb7b6');
  for (let y = 270; y < 346; y += 24) {
    R(o, 18, y, 32, 2, '#b7c3c1');
    for (let x = 20; x < 48; x += 8) { R(o, x, y - 10, 5, 10, x % 3 ? '#e7b24f' : '#d86249'); R(o, x + 1, y - 8, 3, 2, '#fff2c8'); }
  }
  R(o, 54, 262, 2, 82, '#99aaa8'); R(o, 50, 303, 2, 12, '#748783');
  put(8, 236, 52, 121, 356); block(10, 268, 48, 88);

  // Produce crates: red tomatoes are easy to recognize at a glance.
  const crate = (x, y, w, fruit) => {
    R(o, x, y, w, 19, '#9a6331'); R(o, x + 2, y + 3, w - 4, 13, fruit === 'tomato' ? '#6f3f27' : '#557339');
    for (let i = 0; i < 5; i++) {
      const fx = x + 5 + i * 9, fy = y + (i % 2) * 3;
      if (fruit === 'tomato') {
        R(o, fx, fy, 7, 6, i % 2 ? '#dc4131' : '#ee5540'); R(o, fx + 2, fy - 1, 3, 2, '#47713a');
      } else { R(o, fx, fy, 7, 6, i % 2 ? '#d6a73d' : '#79a34c'); R(o, fx + 2, fy + 1, 3, 2, '#a5bf62'); }
    }
    R(o, x, y + 17, w, 3, '#75451f'); R(o, x + 2, y + 19, 2, 5, '#4c321f'); R(o, x + w - 4, y + 19, 2, 5, '#4c321f');
    put(x - 2, y - 2, w + 4, 28, y + 24); block(x, y + 14, w, 9);
  };
  crate(65, 246, 48, 'tomato'); crate(67, 278, 48, 'apple');
  crate(73, 310, 48, 'tomato');

  // Red beverage crates and generic bottle necks; no labels or recognizable brands.
  const drinks = (x, y) => {
    R(o, x, y, 38, 27, '#a92f29'); R(o, x + 2, y + 3, 34, 20, '#c33b30');
    for (let i = 0; i < 4; i++) { R(o, x + 4 + i * 8, y + 4, 5, 14, '#6c3325'); R(o, x + 5 + i * 8, y + 2, 3, 3, '#e7c06d'); }
    for (let xx = x + 3; xx < x + 38; xx += 6) R(o, xx, y + 22, 3, 3, '#77241f');
    put(x - 2, y - 2, 42, 31, y + 28); block(x, y + 21, 38, 7);
  };
  drinks(12, 382); drinks(54, 382); drinks(236, 382); drinks(278, 382);

  // Central checkout: brown laminate counter and a green mechanical weighing scale.
  R(o, 124, 279, 78, 42, '#754629'); R(o, 128, 282, 70, 35, '#a36a3d');
  R(o, 124, 279, 78, 5, '#c38a55'); R(o, 126, 315, 74, 5, '#503321');
  for (let x = 130; x < 198; x += 10) R(o, x, 288, 1, 24, 'rgba(63,37,21,.3)');
  // Large green cast-metal scale, bowl, dial and red needle.
  R(o, 146, 248, 30, 5, '#344d35'); R(o, 149, 239, 24, 10, '#75945d');
  R(o, 152, 233, 18, 7, '#4c704b'); R(o, 154, 231, 14, 3, '#b9c8a5');
  R(o, 156, 232, 10, 7, '#e6e1cf'); R(o, 160, 233, 1, 5, '#bd3d32');
  R(o, 144, 248, 34, 3, '#283f30'); R(o, 156, 253, 10, 5, '#405d3e');
  R(o, 120, 273, 10, 4, '#d3c4a9'); R(o, 192, 273, 10, 4, '#d3c4a9');
  put(120, 230, 86, 94, 322); block(124, 279, 78, 43); block(145, 239, 32, 13);

  // Small hand-lettered notice: original text, no artwork or brand marks.
  R(o, 224, 232, 66, 30, '#f4ead1'); R(o, 222, 230, 70, 4, '#795337');
  R(o, 226, 236, 62, 22, '#fff8e8');
  o.fillStyle = '#263a2c'; o.font = 'bold 6px monospace'; o.textAlign = 'center';
  o.fillText('AKCEPTUJEMY', 257, 244); o.fillText('BITCOIN', 257, 253); o.textAlign = 'left';
  // Tiny orange coin mark made from circles, not a logo.
  o.fillStyle = '#cc8737'; o.beginPath(); o.arc(282, 248, 4, 0, Math.PI * 2); o.fill();
  R(o, 281, 245, 2, 6, '#fff1ca');
  put(222, 230, 70, 32, 262);

  // Bread basket and neutral brown paper loaves on the back of the counter.
  R(o, 130, 267, 28, 8, '#9b693a');
  for (let i = 0; i < 3; i++) { R(o, 132 + i * 8, 262 + (i % 2), 7, 7, '#d9ad69'); R(o, 134 + i * 8, 263, 3, 2, '#f0d39c'); }
  put(128, 260, 32, 16, 276);

  const pois = [
    { key: 'checkout', x: 160, y: 333, r: 44 },
    { key: 'bread', x: 144, y: 271, r: 24 },
    { key: 'produce', x: 91, y: 276, r: 30 },
    { key: 'scale', x: 161, y: 248, r: 22 },
    { key: 'bitcoin', x: 257, y: 266, r: 20 },
    { key: 'beer', x: 256, y: 380, r: 24 },
  ];
  return { w: W, h: H, top: 0, ground, obj, objects, solid, pois, spawn: { x: 160, y: 414 }, exit: { x0: 136, x1: 184, y: 433 } };
};

/* ShopGame is standalone: create() mounts an accessible overlay, while quote() and
   negotiateCredit() are usable by another controller. All prices stay integer grosze. */
window.ShopGame = (() => {
  const defaults = { tomatoesGrams: 750, tomatoPricePerKgGrosz: 800, breadGrosz: 320, beerGrosz: 350, cashGrosz: 2000 };
  function quote(values = {}) {
    const v = { ...defaults, ...values };
    for (const key of Object.keys(defaults)) if (!Number.isSafeInteger(v[key]) || v[key] < 0) throw new TypeError(`${key} must be a non-negative integer`);
    const tomatoCents = (BigInt(v.tomatoesGrams) * BigInt(v.tomatoPricePerKgGrosz) + 500n) / 1000n;
    if (tomatoCents > BigInt(Number.MAX_SAFE_INTEGER)) throw new RangeError('tomato price is too large');
    const tomatoesGrosz = Number(tomatoCents);
    const totalGrosz = v.breadGrosz + tomatoesGrosz + v.beerGrosz;
    if (!Number.isSafeInteger(totalGrosz)) throw new RangeError('basket total is too large');
    return { ...v, tomatoesGrosz, totalGrosz, changeGrosz: Math.max(0, v.cashGrosz - totalGrosz), shortfallGrosz: Math.max(0, totalGrosz - v.cashGrosz) };
  }
  const money = value => `${value} grosz`;
  function create(options = {}) {
    const basket = quote(options.basket);
    const timeLimitMs = Math.max(1000, Number.isFinite(options.timeLimitMs) ? options.timeLimitMs : 15000);
    const doc = document, root = doc.createElement('section');
    root.className = 'shop-game'; root.dataset.shopGame = ''; root.dataset.phase = 'ready';
    root.setAttribute('role', 'dialog'); root.setAttribute('aria-modal', 'true'); root.setAttribute('aria-labelledby', 'shop-title');
    const style = doc.createElement('style');
    style.textContent = `
      .shop-game{position:fixed;z-index:10000;inset:0;background:rgba(25,20,15,.78);display:flex;align-items:center;justify-content:center;padding:14px;box-sizing:border-box;font:16px system-ui,sans-serif;color:#2e2419}
      .shop-card{width:min(100%,520px);max-height:94dvh;overflow:auto;background:#f3e8d2;border:5px solid #68472e;box-shadow:0 0 0 4px #e5d8bb,8px 10px 0 #16120f;padding:clamp(16px,5vw,28px);box-sizing:border-box}
      .shop-card h2{font-size:clamp(20px,6vw,28px);margin:0 0 10px;color:#51351f}.shop-copy{line-height:1.5;margin:10px 0}
      .shop-game button,.shop-game input{font:inherit;min-height:48px;border:3px solid #68472e;box-sizing:border-box;border-radius:4px}
      .shop-game input{width:100%;padding:9px 12px;background:#fffdf6;font-size:22px;touch-action:manipulation}
      .shop-game button{width:100%;margin:8px 0;padding:9px 12px;background:#d7b77b;color:#2a2119;font-weight:700;cursor:pointer;touch-action:manipulation}
      .shop-game button:focus,.shop-game input:focus{outline:3px solid #3e7044;outline-offset:2px}
      .shop-meter{font-weight:700;color:#38583b}.shop-message{min-height:1.5em;color:#7a3328}
      @media(max-width:480px){.shop-card{max-height:96dvh;padding:16px}.shop-game button{min-height:52px}}
    `;
    root.appendChild(style);
    const card = doc.createElement('div'); card.className = 'shop-card';
    card.innerHTML = `<h2 id="shop-title">Sklep uśmiechniętej wagi</h2><p class="shop-copy" data-shop-intro>Koszyk: chleb, pomidory na wagę i napój. Ceny liczymy w całych groszach.</p><p class="shop-meter" data-shop-clock aria-live="polite"></p><p class="shop-copy" data-shop-question></p><p class="shop-message" data-shop-message aria-live="polite"></p><form data-shop-form><label for="shop-answer">Twoja odpowiedź (grosze)</label><input id="shop-answer" type="number" step="1" inputmode="numeric" autocomplete="off" data-shop-answer required><button type="submit" data-shop-submit>Sprawdź</button></form><div data-shop-credit-box><label for="shop-credit-amount">Uzgodniona kwota w zeszycie gry (grosze)</label><input id="shop-credit-amount" type="number" min="0" step="1" inputmode="numeric" value="${basket.shortfallGrosz || Math.max(1, Math.floor(basket.totalGrosz / 2))}" data-shop-credit-amount><button type="button" data-shop-credit>Zapisz uzgodnioną kwotę — tylko postęp gry</button><p class="shop-copy" data-shop-credit-status>Sklepowy zeszyt gry: 0 groszy</p></div><button type="button" data-shop-start>Rozpocznij zakupy</button><button type="button" data-shop-close aria-label="Zamknij grę">Zamknij</button>`;
    root.appendChild(card);
    const $ = selector => root.querySelector(selector);
    const prompts = [
      { text: `Pomnóż wagę pomidorów (${basket.tomatoesGrams} g) przez cenę ${basket.tomatoPricePerKgGrosz} groszy za kilogram. Ile kosztują?`, answer: basket.tomatoesGrosz },
      { text: `Dodaj chleb (${money(basket.breadGrosz)}), pomidory (${money(basket.tomatoesGrosz)}) i piwo (${money(basket.beerGrosz)}). Ile razem?`, answer: basket.totalGrosz },
      { text: `Płacisz ${money(basket.cashGrosz)} za zakupy za ${money(basket.totalGrosz)}. Ile reszty dostaniesz?`, answer: basket.changeGrosz },
    ];
    let phase = 'ready', index = 0, remaining = timeLimitMs, credit = 0, tick = null, startedAt = 0;
    const state = () => ({ phase, question: index, remainingMs: remaining, creditGrosz: credit, basket: { ...basket } });
    const render = () => {
      root.dataset.phase = phase; root.dataset.creditGrosz = String(credit);
      $('[data-shop-question]').textContent = phase === 'ready' ? 'Gotowy na rachunek? Naciśnij „Rozpocznij zakupy”.'
        : phase === 'run' ? `Zadanie ${index + 1}/3 — ${prompts[index].text}`
          : phase === 'complete' ? `Zakupy gotowe! Reszta: ${money(basket.changeGrosz)}. Sklepowy zeszyt gry: ${money(credit)} (to wyłącznie postęp w grze, nie prawdziwy dług).`
            : 'Czas minął. Możesz spróbować ponownie albo uzgodnić zapis w zeszycie gry.';
      $('[data-shop-clock]').textContent = phase === 'run' ? `Pozostało: ${(remaining / 1000).toFixed(1)} s` : '';
      $('[data-shop-credit-status]').textContent = `Sklepowy zeszyt gry: ${money(credit)}`;
      $('[data-shop-form]').hidden = phase !== 'run'; $('[data-shop-start]').hidden = phase === 'run';
      $('[data-shop-credit-box]').hidden = phase === 'ready' || phase === 'complete';
      if (phase === 'run') $('[data-shop-answer]').focus({ preventScroll: true });
    };
    const finish = () => { phase = 'complete'; if (tick) clearInterval(tick); tick = null; render(); if (typeof options.onComplete === 'function') options.onComplete(state()); };
    const begin = () => { if (tick) clearInterval(tick); credit = 0; $('[data-shop-message]').textContent = ''; phase = 'run'; index = 0; remaining = timeLimitMs; startedAt = Date.now(); render(); tick = setInterval(() => {
      remaining = Math.max(0, timeLimitMs - (Date.now() - startedAt));
      if (!remaining) { phase = 'timeout'; clearInterval(tick); tick = null; }
      render();
    }, 100); };
    const submit = value => {
      if (phase !== 'run') return false;
      const answer = typeof value === 'number' ? value : Number(value);
      if (!Number.isSafeInteger(answer)) { $('[data-shop-message]').textContent = 'Wpisz całkowitą liczbę groszy.'; return false; }
      if (answer !== prompts[index].answer) { $('[data-shop-message]').textContent = 'Jeszcze raz — policz spokojnie.'; return false; }
      $('[data-shop-message]').textContent = 'Dobrze policzone!';
      if (++index >= prompts.length) finish(); else { remaining = timeLimitMs; startedAt = Date.now(); render(); }
      return true;
    };
    const negotiateCredit = amount => {
      const suggested = basket.shortfallGrosz || Math.max(1, Math.floor(basket.totalGrosz / 2));
      const asked = amount === undefined ? suggested : Number(amount);
      if (!Number.isSafeInteger(asked) || asked < 0) throw new TypeError('credit amount must be a non-negative integer grosz');
      credit = Math.min(asked, basket.totalGrosz); finish(); return credit;
    };
    $('[data-shop-form]').addEventListener('submit', event => { event.preventDefault(); submit($('[data-shop-answer]').value); });
    $('[data-shop-start]').addEventListener('click', begin);
    $('[data-shop-credit]').addEventListener('click', () => negotiateCredit(Number($('[data-shop-credit-amount]').value)));
    $('[data-shop-close]').addEventListener('click', () => api.destroy());
    const api = { element: root, start: begin, submit, negotiateCredit, destroy() { if (tick) clearInterval(tick); tick = null; root.remove(); phase = 'closed'; }, get state() { return state(); } };
    render(); return api;
  }
  return { quote, create };
})();
