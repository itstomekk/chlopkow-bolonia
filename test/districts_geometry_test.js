'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const file = path.join(__dirname, '../docs/js/districts.js');
assert.ok(fs.existsSync(file), 'District geometry plugin is missing');
const window = { addEventListener() {} };
vm.runInNewContext(fs.readFileSync(file, 'utf8'), { window, console, Number, Math, document: {} });
const D = window.ARK_DISTRICTS;
assert.ok(D, 'Public district geometry API is missing');
// Synthetic geometry, never used as village data.
const ring = [[0, 0], [10, 0], [10, 10], [0, 10]];
for (const point of [[5, 5], [0, 5], [10, 10], [3, 0]]) assert.equal(D.contains(ring, ...point), true);
for (const point of [[-1, 5], [11, 5], [5, 11], [NaN, 5]]) assert.equal(D.contains(ring, ...point), false);
assert.equal(D.contains([[0, 0], [10, 0], [10, 4], [4, 4], [4, 10], [0, 10]], 8, 8), false);
const map = { bbox: [52.252935, 22.8586, 52.285, 22.896352], scale: 2, w: 5143, h: 7091 };
assert.deepEqual(Array.from(D.project(map, [map.bbox[1], map.bbox[2]])), [0, 0]);
const east = D.project(map, [map.bbox[3], map.bbox[0]]);
assert.ok(Math.abs(east[0] - map.w) < 1 && Math.abs(east[1] - map.h) < 1);
assert.throws(() => D.project(map, [null, 52.26]), /coordinate/i);
assert.throws(() => D.prepare({ approximate: true, districts: [] }, map), /district/i);
const fixture = { version: 1, approximate: true, districts: [
  { id: 'test-area', name: 'Za rzeką', color: '#00aabb', polygon: [[22.87, 52.26], [22.88, 52.26], [22.88, 52.27], [22.87, 52.27]], label: [22.875, 52.265] }
] };
const prepared = D.prepare(fixture, map);
assert.equal(prepared[0].name, 'Za rzeką');
assert.equal(prepared[0].polygon.length, 4);
const anchor = D.project(map, fixture.districts[0].label);
assert.equal(D.at(prepared, ...anchor).id, 'test-area');
assert.equal(D.at(prepared, -100, -100), null);
assert.throws(() => D.prepare({ ...fixture, approximate: false }, map), /approximate/i);
assert.throws(() => D.prepare({ ...fixture, districts: [fixture.districts[0], fixture.districts[0]] }, map), /duplicate/i);
assert.throws(() => D.prepare({ ...fixture, districts: [{ ...fixture.districts[0], polygon: [[22.87, 52.26], [22.88, 52.26]] }] }, map), /polygon/i);
assert.throws(() => D.prepare({ ...fixture, districts: [{ ...fixture.districts[0], label: [22.5, 52.1] }] }, map), /label/i);
console.log('District geometry: PASS boundaries, concavity, projection, outside coverage, validation');
