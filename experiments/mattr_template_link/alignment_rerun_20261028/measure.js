'use strict';
// Persistent scorer: build pools once, then shuffle spellings in fixed physical
// slots. The alignment eligibility mask never follows a shuffled word.
const fs = require('fs'), crypto = require('crypto'), readline = require('readline');
const [input, selector, live] = process.argv.slice(2);
const d = JSON.parse(fs.readFileSync(input, 'utf8')), S = require(selector);
if (live === 'live') d.spatialReview = {tokens: d.words.map(() => ({}))};
const ctx = S.prepare(d), pools = d.words.map((_, i) => S.sourcePool(ctx, i, 100,
  {left: 3, depth: 8, angle: 45, weight: 'distance'}));
const keys = ['components', 'h1', 'h2', 'worddiv', 'n', 'pair_ess', 'repeat_source'];
const out = Object.fromEntries(keys.map(k => [k, []]));
for (let i = 0; i < pools.length; i++) {
  const s = S.measure(ctx, pools[i]);
  for (const k of keys) out[k].push(k === 'repeat_source' ? +pools[i].indices.some(j => d.words[j] === d.words[i])
    : k === 'pair_ess' ? s.pairEss : s[k]);
}
const vocabulary = [...new Set(d.words)].sort(), ids = new Map(vocabulary.map((w,i) => [w,i]));
const paired = vocabulary.map(w => d.components[w].length >= 2);
function fast(words) {
  const worddiv = [], valid = [], repeat_source = [];
  for (let i = 0; i < pools.length; i++) {
    const pool = pools[i], types = new Map();
    let mass = 0, pairMass = 0, pairSquared = 0, pairWords = 0;
    pool.indices.forEach((j,k) => {
      const w = pool.weights[k], id = words[j];
      mass += w; types.set(id, (types.get(id) || 0) + w);
      if (paired[id]) { pairWords++; pairMass += w; pairSquared += w*w; }
    });
    let collision = 0; for (const w of types.values()) collision += (w/mass)**2;
    worddiv.push(pool.indices.length ? Math.max(0,1-collision) : null);
    valid.push(pairWords >= 5 && pairSquared > 0 && pairMass*pairMass/pairSquared >= 3);
    repeat_source.push(+types.has(words[i]));
  }
  return {worddiv, valid, repeat_source};
}
const quick = fast(d.words.map(w => ids.get(w)));
for (let i = 0; i < d.words.length; i++) {
  if (quick.valid[i] !== Number.isFinite(out.components[i]) ||
      (out.worddiv[i] != null && Math.abs(quick.worddiv[i] - out.worddiv[i]) > 1e-12))
    throw Error('Fast/full scorer disagreement at ' + i);
}
const digest = crypto.createHash('sha256');
for (const p of pools) digest.update(JSON.stringify(p));
console.log(JSON.stringify({measures: out, vocabulary, pools_sha256: digest.digest('hex'),
  edges: pools.reduce((s,p) => s+p.indices.length,0),
  pages: [...ctx.pages].map(([page,v]) => ({page,wordWidth:v.wordWidth,pitch:v.pitch}))}));
const rl = readline.createInterface({input:process.stdin, crlfDelay:Infinity});
rl.on('line', line => console.log(JSON.stringify(fast(JSON.parse(line)))));
