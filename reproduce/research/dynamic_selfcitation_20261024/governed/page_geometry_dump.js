'use strict';
// Dump the app's spatial source pool of every token: node page_geometry_dump.js in.json out.json <heatmap_sources.js> [options json]
// in.json = {words, lines:[{page,locus,bifolium,start,end}], geometry:[[x0,y0,x1,y1]|null], components:{word:[units]}}
// out.json = per token [indices, weights, available]
const fs = require('fs');
const S = require(process.argv[4]);
const d = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const opt = Object.assign({ left: 3, depth: 8, angle: 45, weight: 'distance', cap: 100 }, JSON.parse(process.argv[5] || '{}'));
const c = S.prepare(d);
const out = [];
for (let i = 0; i < d.words.length; i++) {
  const p = S.sourcePool(c, i, opt.cap, opt);
  out.push([p.indices, p.weights, p.available]);
}
fs.writeFileSync(process.argv[3], JSON.stringify(out));
