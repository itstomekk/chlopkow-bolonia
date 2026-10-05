/* User-reviewed J12 yard objects. Keeps satellite uncertainty separate from local identification.
   Standalone overlay: no shared map PNG edits, no new NPCs/quests/save entries. */
(() => {
  'use strict';
  let started = false;
  async function install() {
    if (started || !window.ARK) return;
    started = true;
    const A = window.ARK;
    const diagnostic = window.__yardProps = { ready: false, error: null, props: [] };
    try {
      const response = await fetch('data/j12-yard-props.json');
      if (!response.ok) throw Error(`J12 props manifest HTTP ${response.status}`);
      const data = await response.json();
      if (data.review !== 'yard-evidence-j12-v1' || !Array.isArray(data.props)) throw Error('Invalid J12 props manifest');
      const images = Object.fromEntries(await Promise.all(Object.entries(data.assets).map(async ([kind, asset]) => {
        const image = await A.load(asset.src);
        if (image.width !== asset.size[0] || image.height !== asset.size[1]) throw Error(`J12 sprite size mismatch: ${kind}`);
        return [kind, image];
      })));
      const props = data.props;
      const solidAt = (x, y, air = false) => {
        if (A.room || x < 4800 || x > 5130 || y < 5620 || y > 6144) return false;
        return props.some(p => {
          const f = p.footprint;
          if (air && !f.tall) return false;
          const dx = (x - p.x) / f.rx, dy = (y - p.y - f.cy) / f.ry;
          return dx * dx + dy * dy <= 1;
        });
      };
      A.HOOKS.solidAt.push(solidAt);
      A.HOOKS.world.push((push, S, inView) => {
        if (A.room) return;
        for (const p of props) {
          const im = images[p.kind];
          // Cull by footprint edges as well as center (tall sprites at the viewport border).
          if (!inView(p.x, p.y) && !inView(p.x, p.y - im.height)) continue;
          push(p.y, () => {
            const [sx, sy] = S(p.x, p.y), z = A.zoom;
            A.ctx.save();
            A.ctx.imageSmoothingEnabled = false;
            A.shadow(sx + 2 * z, sy, z, im.width * .32);
            A.ctx.drawImage(im, Math.round(sx - im.width * z / 2), Math.round(sy - im.height * z), im.width * z, im.height * z);
            A.ctx.restore();
          });
        }
      });
      // A loaded save/debug coordinate inside a new obstacle gets the normal escape search.
      if (!A.room) A.unstick();
      Object.assign(diagnostic, { ready: true, props, assets: data.assets, solidAt,
        identificationSource: data.identificationSource });
    } catch (error) {
      diagnostic.error = String(error.message || error);
      console.warn('J12 yard props:', diagnostic.error);
    }
  }
  window.addEventListener('ark-ready', () => queueMicrotask(install), { once: true });
  if (window.ARK) queueMicrotask(install);
})();
