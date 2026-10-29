'use strict';
// Geometry sweep (28 October, user's request): many pool shapes in one pass. Each configuration in the input's `configs` list
// has {name, dir ('up' = tokens before N, 'down' = tokens after N), left (same-line reach in word widths for 'up'),
// right (same-line reach for 'down'), depth (line spacings into the other lines; 0 = same line only), angle (half-angle in
// degrees), offset (horizontal displacement of the cone's apex in word widths; negative = left)}. Distance weights and the
// cap of 100 as in the study selector; a configuration with left 3, depth 8, angle 45, offset 0, dir up IS the study selector.
// Output per configuration: component diversity, pool size, and repeat_out (1 if another token of N's spelling lies within
// 99 tokens before or after N and outside N's pool).
const fs = require('fs'), path = require('path');
const S = require(path.join(__dirname, 'component_source_math.js'));
const [inPath, outPath] = process.argv.slice(2);
const d = JSON.parse(fs.readFileSync(inPath, 'utf8'));
const c = S.prepare(d);
const n = d.words.length;

const positions = new Map();
d.words.forEach((w, i) => { if (!positions.has(w)) positions.set(w, []); positions.get(w).push(i); });

function pool(ctx, pos, cfg) {
  const target = ctx.centers[pos];
  if (!target) return { indices: [], weights: [], available: 0, missingTarget: true };
  const line = ctx.lineOf[pos], page = ctx.pages.get(ctx.data.lines[line].page), cand = [], tan = Math.tan(cfg.angle * Math.PI / 180);
  const up = cfg.dir === 'up', ax = target.x + (cfg.offset || 0) * page.wordWidth;
  for (const i of page.indices) {
    if (up) { if (i >= pos) break; } else if (i <= pos) continue;
    const b = ctx.centers[i];
    if (!b) continue;
    let distance, alignment = 1;
    if (ctx.lineOf[i] === line) {
      const dx = b.x - target.x;
      if (up) { if (!cfg.left || dx >= 0 || -dx > cfg.left * page.wordWidth) continue; distance = -dx / page.wordWidth; }
      else { if (!cfg.right || dx <= 0 || dx > cfg.right * page.wordWidth) continue; distance = dx / page.wordWidth; }
      if (cfg.metric === 'edge') {
        // width-neutral: the gap between the two boxes, in word widths, plus one; an adjacent word has distance 1 whatever
        // the lengths of N and of the neighbour (centre to centre, a short N has its neighbour's centre closer)
        const tb = ctx.data.geometry[pos], nb = ctx.data.geometry[i];
        const gap = up ? tb[0] - nb[2] : nb[0] - tb[2];
        distance = 1 + Math.max(0, gap) / page.wordWidth;
      }
    } else {
      if (!cfg.depth) continue;
      const box = ctx.data.geometry[i];
      const dy = up ? target.y - b.y : b.y - target.y;
      const near = up ? Math.max(0, target.y - box[3]) : Math.max(0, box[1] - target.y);
      const far = up ? Math.min(cfg.depth * page.pitch, target.y - box[1]) : Math.min(cfg.depth * page.pitch, box[3] - target.y);
      const horizontal = Math.max(box[0] - ax, ax - box[2], 0);
      if (dy <= 0 || far <= 0 || near > far || horizontal > far * tan + 1e-8) continue;
      const ddx = b.x - ax;
      distance = Math.hypot(ddx, dy) / page.pitch;
      alignment = dy * dy / (ddx * ddx + dy * dy);
    }
    cand.push({ i, distance, w: cfg.weight === 'uniform' ? 1 : alignment / (1 + distance) ** 2 });
  }
  cand.sort((a, b) => b.w - a.w || a.distance - b.distance || (up ? b.i - a.i : a.i - b.i));
  const chosen = cand.slice(0, 100).sort((a, b) => a.i - b.i);
  return { indices: chosen.map(x => x.i), weights: chosen.map(x => x.w), available: cand.length, missingTarget: false };
}

function repeatOutside(i, indices) {
  const P = positions.get(d.words[i]);
  if (P.length === 1) return 0;
  const inPool = new Set(indices);
  for (const j of P) {
    if (j < i - 99) continue;
    if (j > i + 99) break;
    if (j !== i && !inPool.has(j)) return 1;
  }
  return 0;
}

const num = x => (Number.isFinite(x) ? x : null);
const out = {};
for (const cfg of d.configs) {
  const comp = new Array(n).fill(null), h2 = new Array(n).fill(null), wdiv = new Array(n).fill(null), size = new Array(n).fill(0), rep = new Array(n).fill(0);
  for (let i = 0; i < n; i++) {
    const p = pool(c, i, cfg), m = S.measure(c, p);
    comp[i] = num(m.components); h2[i] = num(m.h2); wdiv[i] = num(m.worddiv); size[i] = m.n; rep[i] = repeatOutside(i, p.indices);
  }
  out[cfg.name] = { components: comp, h2: h2, worddiv: wdiv, n: size, repeat_out: rep };
}
fs.writeFileSync(outPath, JSON.stringify(out));
console.log(JSON.stringify({ tokens: n, configs: d.configs.length }));
