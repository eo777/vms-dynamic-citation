'use strict';
// Overlap test (28 October, user's request): the study's spatial selector with NO same-line reach (left 0: the cone holds
// words on other lines only; depth 8 line spacings, 45 degrees, tokens before N, distance weights, cap 100) and its mirror
// below N (tokens after N). Besides the pool measures, the indices of the pooled words are written out, so that the
// repeat outcome can be computed against words OUTSIDE the cone (overlap_check.py).
const fs = require('fs'), path = require('path');
const S = require(path.join(__dirname, 'component_source_math.js'));
const [inPath, outPath] = process.argv.slice(2);
const d = JSON.parse(fs.readFileSync(inPath, 'utf8'));
const c = S.prepare(d);
const options = { left: 0, depth: 8, angle: 45, weight: 'distance' };

function mirrorPool(ctx, pos, limit, opts = {}) {
  const { left = 3, depth = 8, angle = 45, weight = 'distance' } = opts;
  const target = ctx.centers[pos];
  if (!target) return { indices: [], weights: [], available: 0, missingTarget: true };
  const line = ctx.lineOf[pos], page = ctx.pages.get(ctx.data.lines[line].page), candidates = [], tan = Math.tan(angle * Math.PI / 180);
  for (const i of page.indices) {
    if (i <= pos) continue;
    const b = ctx.centers[i];
    if (!b) continue;
    const dx = b.x - target.x, dy = b.y - target.y;
    let distance, alignment = 1;
    if (ctx.lineOf[i] === line) {
      if (dx <= 0 || dx > left * page.wordWidth) continue;
      distance = dx / page.wordWidth;
    } else {
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
for (const k of ['up_components', 'up_worddiv', 'up_n', 'dn_components', 'dn_worddiv', 'dn_n']) out[k] = new Array(n).fill(null);
out.up_idx = new Array(n); out.dn_idx = new Array(n);
const num = x => (Number.isFinite(x) ? x : null);
for (let i = 0; i < n; i++) {
  const up = S.sourcePool(c, i, 100, options), u = S.measure(c, up);
  out.up_components[i] = num(u.components); out.up_worddiv[i] = num(u.worddiv); out.up_n[i] = u.n; out.up_idx[i] = up.indices;
  const dn = mirrorPool(c, i, 100, options), m = S.measure(c, dn);
  out.dn_components[i] = num(m.components); out.dn_worddiv[i] = num(m.worddiv); out.dn_n[i] = m.n; out.dn_idx[i] = dn.indices;
}
fs.writeFileSync(outPath, JSON.stringify(out));
console.log(JSON.stringify({ tokens: n, valid_up: out.up_components.filter(x => x !== null).length, valid_dn: out.dn_components.filter(x => x !== null).length }));
