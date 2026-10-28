// Freeze one real example using the geometry of the 27 October study.
// Run from either the research workspace or the published repository.
const fs = require('fs');
const path = require('path');
const zlib = require('zlib');
const crypto = require('crypto');
const S = require('../component_source_math.js');

let root = __dirname, input;
while (true) {
  for (const relative of ['apps/selfcitation_governor/data/mattr_heatmap/words.json.gz', 'data/mattr_heatmap/words.json.gz']) {
    const candidate = path.join(root, relative);
    if (fs.existsSync(candidate)) { input = candidate; break; }
  }
  if (input || path.dirname(root) === root) break;
  root = path.dirname(root);
}
if (!input) throw new Error('Cannot find the manuscript word bundle');
const data = JSON.parse(zlib.gunzipSync(fs.readFileSync(input)));
if (data.spatialReview && !data.legacyGeometry) throw new Error('Historical geometry is required');
data.geometry = data.legacyGeometry || data.geometry;
const target = 31343;
if (data.words[target] !== 'otedy') throw new Error('Target index changed');
const ctx = S.prepare(data);
const options = {left: 3, depth: 8, angle: 45, weight: 'distance'};
const pool = S.sourcePool(ctx, target, 100, options);
const score = S.measure(ctx, pool);
const pageName = data.lines[ctx.lineOf[target]].page;
const page = ctx.pages.get(pageName);
const repeatWords = data.words.slice(target - 99, target + 100);
let repeats = 0;
for (let start = 0; start < 100; start++) {
  if (repeatWords.slice(start, start + 100).filter(w => w === data.words[target]).length > 1) repeats++;
}
if (pool.indices.length !== 40 || repeats !== 83 || Math.abs(score.components - 20.319234350444056) > 1e-9) {
  throw new Error('The frozen example no longer matches the 27 October measurements');
}
// Python's saved report uses NaN for empty subgroups; the manuscript value is finite.
const metrics = JSON.parse(fs.readFileSync(path.join(__dirname, '../mechanism_check.json'), 'utf8')
  .replace(/:\s*NaN(?=\s*[,}])/g, ': null'));
const result = {
  geometry_policy: 'legacy (27 October 2026)',
  geometry_sha256: crypto.createHash('sha256').update(JSON.stringify(data.geometry)).digest('hex'),
  selector_sha256: crypto.createHash('sha256').update(fs.readFileSync(path.join(__dirname, '../component_source_math.js'))).digest('hex'),
  page: pageName, target, word: data.words[target],
  target_box: data.geometry[target], pitch: page.pitch, word_width: page.wordWidth,
  options, sources: pool.indices, weights: pool.weights, score,
  page_words: page.indices.map(i => ({i, word: data.words[i], box: data.geometry[i]})),
  example_word: 'chedy', example_units: data.components.chedy,
  repeat_context: repeatWords, repeat_windows: repeats, total_windows: 100,
  manuscript_contrast: metrics.manuscript.components.all
};
fs.writeFileSync(path.join(__dirname, 'method_example.json'), JSON.stringify(result, null, 2) + '\n');
console.log('Saved f78r / otedy: 40 sources; 83 of 100 windows contain a repeat.');
