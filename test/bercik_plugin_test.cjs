'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('docs/js/bercik.js', 'utf8');

async function run(canReach) {
  let ready;
  const warnings = [];
  const window = {
    ARK: {
      ITEMS: { npcs: [] }, MAP: { w: 5143, h: 7091 },
      HOOKS: { npcTalk: [] }, LANG: 'pl',
      blocked: () => false, terrainAt: () => 'track', say: () => {},
    },
    addEventListener: (name, fn) => { assert.equal(name, 'ark-ready'); ready = fn; },
  };
  vm.runInNewContext(source, { window, queueMicrotask, console: { warn: msg => warnings.push(msg) } });
  // game.js publishes __game immediately AFTER firing ark-ready.
  ready();
  window.__game = { isSpawnReachable: canReach };
  await Promise.resolve();
  return { window, warnings };
}

(async () => {
  const reachable = await run((x, y) => x === 4800 && y === 5800);
  const npcs = reachable.window.ARK.ITEMS.npcs;
  assert.equal(npcs.length, 1);
  assert.equal(npcs[0].x, 4800, 'must use spawn reachability, not the sector centre');
  assert.equal(npcs[0].y, 5800);
  assert.equal(reachable.window.__bercik.position().reachable, true);
  assert.equal(reachable.window.__bercik.directionFrame('down_right'), 'walk_right');
  assert.equal(reachable.window.__bercik.directionFrame('up_left'), 'walk_left');
  const none = await run(() => false);
  assert.equal(none.window.ARK.ITEMS.npcs.length, 0, 'never create an unchecked fallback NPC');
  assert.equal(none.window.__bercik.installed, false);
  assert.equal(none.warnings.length, 1);
  const unavailable = await run(undefined);
  assert.equal(unavailable.window.ARK.ITEMS.npcs.length, 0, 'missing reachability API must fail closed');
  assert.equal(unavailable.warnings.length, 1);
  console.log('BERCIK plugin PASS: post-ready reachability, runtime direction mapping, no unsafe fallback');
})().catch(error => { console.error(error); process.exitCode = 1; });
