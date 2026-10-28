'use strict';
// Per-token source-diversity measures with the other study's own selector and formulas
// (component_source_math.js = copy of research/timm_geometry_audit_20261026/component_repeat_20261027/
// source_math_snapshot.js, itself a copy of apps/selfcitation_governor/heatmap_sources.js at the time of its rerun).
// Input JSON: {words, lines:[{page,locus,bifolium,start,end}], geometry:[[x0,y0,x1,y1]|null], components:{word:[units]}}
// Output JSON: per-token arrays for the spatial cone (left 3, depth 8, 45 degrees, distance weights, cap 100),
// the preceding 99 tokens (reading order) and the following 99 tokens (reading order).
const fs = require('fs'), path = require('path');
const S = require(path.join(__dirname, 'component_source_math.js'));
const [inPath, outPath] = process.argv.slice(2);
const d = JSON.parse(fs.readFileSync(inPath, 'utf8'));
const c = S.prepare(d);
const options = { left: 3, depth: 8, angle: 45, weight: 'distance' };
const n = d.words.length;
const out = {};
for (const k of ['components', 'h1', 'h2', 'n', 'pair_ess', 'worddiv', 'back_components', 'back_h2', 'fwd_components', 'fwd_h2']) out[k] = new Array(n).fill(null);
const num = x => (Number.isFinite(x) ? x : null);
for (let i = 0; i < n; i++) {
  const s = S.measure(c, S.sourcePool(c, i, 100, options));
  out.components[i] = num(s.components); out.h1[i] = num(s.h1); out.h2[i] = num(s.h2);
  out.n[i] = s.n; out.pair_ess[i] = num(s.pairEss); out.worddiv[i] = num(s.worddiv);
  const b = S.measure(c, S.windowPool(c, i - 1, 99, 'backward'));
  out.back_components[i] = num(b.components); out.back_h2[i] = num(b.h2);
  const f = S.measure(c, S.windowPool(c, i + 1, 99, 'forward'));
  out.fwd_components[i] = num(f.components); out.fwd_h2[i] = num(f.h2);
}
fs.writeFileSync(outPath, JSON.stringify(out));
console.log(JSON.stringify({ tokens: n, valid_components: out.components.filter(x => x !== null).length }));
