'use strict';
// Full above-left selector and its below-right mirror, retaining the original scoring code.
// These are descriptive mirror measurements; a causal interpretation requires calibration.
// Includes same-line reach, distance weighting, and a cap of 100 source words.
const fs = require('fs'), path = require('path');
const S = require(path.join(__dirname, 'component_source_math.js'));
const [inPath, outPath] = process.argv.slice(2);
const d = JSON.parse(fs.readFileSync(inPath, 'utf8'));
const c = S.prepare(d);
const options = { left: 3, depth: 8, angle: 45, weight: 'distance' };

function mirrorPool(ctx, pos, limit, opts = {}) {
  const { left = 3, depth = 8, angle = 45, weight = 'distance' } = opts;
  const target = ctx.centers[pos];
  if (!target) return { indices: [], weights: [], available: 0, missingTarget: true };
  const line = ctx.lineOf[pos], page = ctx.pages.get(ctx.data.lines[line].page), candidates = [], tan = Math.tan(angle * Math.PI / 180);
  for (const i of page.indices) {
    if (i <= pos) continue;
    const b = ctx.centers[i];
    if (!b) continue;
    const dx = b.x - target.x, dy = b.y - target.y; // dy > 0: the candidate lies below N (y grows down the page)
    let distance, alignment = 1;
    if (ctx.lineOf[i] === line) {
      if (dx <= 0 || dx > left * page.wordWidth) continue;
      distance = dx / page.wordWidth;
    } else {
      // the candidate's recorded rectangle must intersect the finite cone below N (mirror of the rule above N)
      const box = ctx.data.geometry[i], near = Math.max(0, box[1] - target.y), far = Math.min(depth * page.pitch, box[3] - target.y);
      const horizontal = Math.max(box[0] - target.x, target.x - box[2], 0);
      if (dy <= 0 || far <= 0 || near > far || horizontal > far * tan + 1e-8) continue;
      distance = Math.hypot(dx, dy) / page.pitch;
      alignment = dy * dy / (dx * dx + dy * dy);
    }
    candidates.push({ i, distance, w: weight === 'uniform' ? 1 : alignment / (1 + distance) ** 2 });
  }
  candidates.sort((a, b) => b.w - a.w || a.distance - b.distance || a.i - b.i);
  const chosen = candidates.slice(0, limit).sort((a, b) => a.i - b.i);
  return { indices: chosen.map(x => x.i), weights: chosen.map(x => x.w), available: candidates.length, missingTarget: false };
}

const n = d.words.length, out = {};
for (const k of ['up_components', 'up_h2', 'up_worddiv', 'up_n', 'dn_components', 'dn_h2', 'dn_worddiv', 'dn_n']) out[k] = new Array(n).fill(null);
const num = x => (Number.isFinite(x) ? x : null);
for (let i = 0; i < n; i++) {
  const u = S.measure(c, S.sourcePool(c, i, 100, options));
  out.up_components[i] = num(u.components); out.up_h2[i] = num(u.h2); out.up_worddiv[i] = num(u.worddiv); out.up_n[i] = u.n;
  const m = S.measure(c, mirrorPool(c, i, 100, options));
  out.dn_components[i] = num(m.components); out.dn_h2[i] = num(m.h2); out.dn_worddiv[i] = num(m.worddiv); out.dn_n[i] = m.n;
}
fs.writeFileSync(outPath, JSON.stringify(out));
console.log(JSON.stringify({ tokens: n, valid_up: out.up_components.filter(x => x !== null).length, valid_dn: out.dn_components.filter(x => x !== null).length }));
