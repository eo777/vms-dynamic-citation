"""Comparison page in the governor app's design (27 October, user's request): choose a sheet (bifolium) and see every
text version of it side by side, each word box coloured by H2, component diversity, word diversity or MATTR, with
the app's own palette and page geometry. Scores are precomputed here with the app's selector (component_measure.js,
the other study's own code) for every variant bundle written by heatmap_variants.py; the page itself is static.
Writes heatmap_variants/compare_data.json.gz, compare.html and compare.js. Serve heatmap_variants/ and open
http://127.0.0.1:8766/compare.html.
"""
import gzip
import json
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import data as D
import component_check as CC

OUT = HERE / 'heatmap_variants'
APP = D.src('apps/selfcitation_governor')
VARIANTS = [('manuscript', 'Manuscript', 'v'), ('manuscript_clean', 'Manuscript, oversized recorded boxes removed', 'v'),
            ('timm', 'Original Timm self-citation, no innovator (laid into the lines)', 'v'),
            ('noinnov_far0', 'Governed page-window copier without the innovator, far 0 (laid into the lines)', 'v'),
            ('timm_spatial', 'Original Timm, page draws from the words in view on the recorded geometry', 'v'),
            ('noinnov_spatial', 'Governed copier without the innovator, page draws from the words in view', 'v'),
            ('far0_spatial', 'Governed copier with the innovator (far 0), page draws from the words in view', 'v'),
            ('bigram_whole', 'Markov chain, whole manuscript', 'v'),
            ('bigram_currier', 'Markov chains, Currier A and B separately', 'v'), ('bigram_section', 'Markov chains, each section separately', 'v'),
            ('gart_own_lines', 'Gart der Gesundheit 1487, its own printed lines', 'l'), ('gart_character_budget', 'Gart 1487, each line filled to its character budget', 'l'),
            ('gart_one_word_per_box', 'Gart 1487, one word per manuscript box', 'l')]
MEASURES = ('h2', 'components', 'worddiv', 'mattr')


def page_frames():
    html = (APP / 'heatmap.html').read_text(encoding='utf8')
    out = {}
    for m in re.finditer(r'<figure style="--ratio:([0-9.]+)"><figcaption>([^<]+)</figcaption><svg role="group" aria-label="[^"]+" viewBox="([^"]+)">', html):
        out[m.group(2)] = dict(ratio=float(m.group(1)), viewBox=m.group(3))
    return out


def domain(values):
    v = values[np.isfinite(values)]
    if not len(v):
        return [0.0, 1.0]
    lo, hi = np.percentile(v, [5, 95])
    if hi - lo < 1e-9:
        lo, hi = float(v.min()), float(v.max())
    return [float(lo), float(hi)]


def main():
    ms = D.manuscript()
    frames = page_frames()
    app = json.load(gzip.open(APP / 'data/mattr_heatmap/words.json.gz', 'rt', encoding='utf8'))
    pages = {p['folio']: dict(frames.get(p['folio'], dict(ratio=0.75, viewBox='0 0 1100 1500')), bifolium=p['node'], group=p['group'], section=p['section']) for p in ms['pages']}
    bifolia = [dict(id=n['id'], group=n['group'], section=D.GROUP_SECTION.get(n['group'], ''), pages=n['pages']) for n in ms['nodes']]
    data = dict(pages=pages, bifolia=bifolia, palette=app['palette'], measures=dict(
        h2='H2: conditional glyph entropy of the words in view (bits)', components='component diversity: effective number of unit pairs among the words in view',
        worddiv='word diversity of the words in view: 1 − Σ p(spelling)²', mattr='MATTR colour: distinct share of the backward 100-token window'), variants=[])
    pooled = {u: {m: [] for m in MEASURES} for u in ('v', 'l')}
    for key, label, unit in VARIANTS:
        b = json.load(gzip.open(OUT / key / 'data/mattr_heatmap/words.json.gz', 'rt', encoding='utf8'))
        inp = dict(words=b['words'], lines=b['lines'], geometry=b['geometry'], components=b['components'])
        meas = CC.measure(inp)
        mattr = D.trailing_distinct(inp['words'], 100)
        series = dict(h2=meas['h2'], components=meas['components'], worddiv=meas['worddiv'], mattr=mattr)
        per_page = {}
        for L in inp['lines']:
            pg = per_page.setdefault(L['page'], dict(words=[], boxes=[], h2=[], components=[], worddiv=[], mattr=[]))
            for i in range(L['start'], L['end']):
                g = inp['geometry'][i]
                if g is None:
                    continue
                pg['words'].append(inp['words'][i])
                pg['boxes'].append([int(round(g[0])), int(round(g[1])), max(1, int(round(g[2] - g[0]))), max(1, int(round(g[3] - g[1])))])
                for m in MEASURES:
                    v = series[m][i]
                    pg[m].append(None if not np.isfinite(v) else round(float(v), 3))
        for m in MEASURES:
            pooled[unit][m].append(series[m])
        data['variants'].append(dict(key=key, label=label, unit=unit, tokens=len(inp['words']),
                                     domains={m: domain(series[m]) for m in MEASURES}, pages=per_page))
        print(key, 'scored', flush=True)
    data['shared_domains'] = {u: {m: domain(np.concatenate(pooled[u][m])) for m in MEASURES} for u in pooled}
    (OUT / 'compare_data.json.gz').write_bytes(gzip.compress(json.dumps(data, separators=(',', ':')).encode('utf8'), mtime=0))
    (OUT / 'compare.html').write_text(HTML, encoding='utf8')
    (OUT / 'compare.js').write_text(JS, encoding='utf8')
    print('wrote compare_data.json.gz, compare.html, compare.js')


HTML = '''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Layout variants · one sheet, every text version</title>
<link rel="stylesheet" href="shell/style.css"><link rel="stylesheet" href="shell/heatmap.css">
<style>
.heatmap-atlas .bifolio header{align-items:baseline}
.heatmap-atlas .variant-note{color:var(--ink2);font-size:.85rem;margin:.1rem 0 0}
.heatmap-atlas .legends{display:flex;gap:2rem;flex-wrap:wrap;margin:.6rem 0 1rem}
.heatmap-atlas .legends .legend{min-width:16rem}
.heatmap-atlas .explain{color:var(--ink2);font-size:.9rem;max-width:70rem;line-height:1.45}
.compare-grid{display:grid;grid-template-columns:5rem repeat(var(--cols),minmax(0,1fr));gap:.4rem .5rem;align-items:start;margin-top:1rem}
.compare-grid .col-head{font-size:.78rem;color:var(--ink);text-align:center;line-height:1.25;align-self:end}
.compare-grid .row-head{font-size:.85rem;color:var(--ink);font-weight:600;padding-top:.4rem}
.compare-grid .cell figure{margin:0;width:100%}.compare-grid .cell svg{width:100%;height:auto;aspect-ratio:var(--ratio);display:block;background:var(--surface);border:1px solid var(--line)}
.compare-grid .cell figcaption{font-size:.72rem;color:var(--ink2);text-align:center;margin-top:.15rem}
.compare-grid.pages-across{grid-template-columns:11rem repeat(var(--cols),minmax(0,1fr))}
.compare-grid.pages-across .col-head{font-weight:600;font-size:.85rem}.compare-grid.pages-across .row-head{font-size:.8rem;line-height:1.3}
/* compact: every page at one height (all pages share one scale), about the size a page has with texts across */
.compare-grid.pages-compact{container-type:inline-size;grid-template-columns:11rem repeat(var(--cols),max-content);justify-content:start}
.compare-grid.pages-compact .cell figure{width:max-content}
.compare-grid.pages-compact .cell svg{width:auto;height:calc((100cqw - 5rem - var(--n) * .5rem) / var(--n) / .75)}
</style></head>
<body class="heatmap-page">
<nav class="site-nav"><a href="index.html">Layout variants index</a></nav>
<header class="masthead"><h1>One sheet, every text version</h1>
<p>Pick a bifolium. Columns are the text versions and rows the sheet's pages in singulion order (Arrange swaps them); every word box is coloured by the chosen score of the words in view above and to the left of it,
computed with the app's own source selector (cone of 8 line spacings and 45°, 3 word widths to the left, at most 100 sources, distance weights).</p></header>
<main class="heatmap-atlas" id="atlas">
<div class="controls">
<label>Sheet <select id="sheet"></select></label>
<label>Colour by <select id="measure"><option value="h2">Glyph H2 (conditional)</option><option value="components">Component diversity</option><option value="worddiv">Source word diversity</option><option value="mattr">MATTR (backward 100)</option></select></label>
<label>Colour scale <select id="scale"><option value="shared">shared across texts of the same unit system</option><option value="own">each text\\'s own 5–95 % range (as the app does)</option></select></label>
<label>Arrange <select id="layout"><option value="texts">texts across, pages down</option><option value="pages">pages across, texts down</option><option value="compact">pages across, texts down, compact</option></select></label>
</div>
<div class="legends" id="legends"></div>
<p class="explain" id="explain"></p>
<div id="blocks"></div>
</main>
<script src="compare.js"></script>
</body></html>'''

JS = r"""
"use strict";
(async () => {
 const r = await fetch('compare_data.json.gz');
 const data = JSON.parse(await new Response(r.body.pipeThrough(new DecompressionStream('gzip'))).text());
 const sheet = document.getElementById('sheet'), measure = document.getElementById('measure'), scale = document.getElementById('scale');
 const blocks = document.getElementById('blocks'), legends = document.getElementById('legends'), explain = document.getElementById('explain');
 const layout = document.getElementById('layout');
 const variants = data.variants.filter(v => v.key !== 'manuscript'); // the cleaned manuscript replaces the as-recorded one (user, 27 Oct)
 const short = {manuscript_clean: 'Manuscript', manuscript: 'Manuscript', timm: 'Original Timm (self-citation)', noinnov_far0: 'Far 0 without innovator (page-window copier)', timm_spatial: 'Original Timm, sources in view (spatial)', noinnov_spatial: 'Far 0 without innovator, sources in view (spatial)', far0_spatial: 'Far 0 with innovator, sources in view (spatial)', bigram_whole: 'Markov chain, whole manuscript', bigram_currier: 'Markov chains, Currier A / B',
  bigram_section: 'Markov chains, by section', gart_own_lines: 'Gart 1487, its own printed lines', gart_character_budget: 'Gart 1487, character-budget fill', gart_one_word_per_box: 'Gart 1487, one word per manuscript box'};
 for (const b of data.bifolia) sheet.append(new Option(`${b.id} · group ${b.group} (${b.section}) · ${singulion(b.pages).join(' ')}`, b.id));
 const start = new URLSearchParams(location.hash.slice(1));
 sheet.value = start.get('sheet') || 'M:75-84';
 if (start.get('measure')) measure.value = start.get('measure');
 if (start.get('scale')) scale.value = start.get('scale');
 if (start.get('layout')) layout.value = start.get('layout');
 // Singulion order: the first leaf's recto then verso, then the second leaf's; a foldout's panels keep their recorded
 // order, and a page without a folio number (fRos) stays beside the page before it.
 function leafKey(folio) { const k = /^f(\d+)([rv])/.exec(folio); return k ? [+k[1], k[2] === 'r' ? 0 : 1] : null; }
 function singulion(pages) {
  let last = [0, 0];
  const keyed = pages.map((folio, k) => { const key = leafKey(folio) || last; last = key; return {folio, k, key}; });
  return keyed.sort((a, b) => a.key[0] - b.key[0] || a.key[1] - b.key[1] || a.k - b.k).map(x => x.folio);
 }
 const paint = (v, lo, hi) => {
  if (v === null || v === undefined || !Number.isFinite(v)) return 'var(--line2)';
  const frac = Math.max(0, Math.min(1, (v - lo) / (hi - lo)));
  return data.palette[Math.max(0, Math.min(500, Math.floor(frac * 501)))];
 };
 const dom = (variant, m) => m === 'mattr' ? [0.5, 1.0] : (scale.value === 'shared' ? data.shared_domains[variant.unit][m] : variant.domains[m]);
 const fmt = (v, m) => m === 'components' ? v.toFixed(1) : v.toFixed(3);
 const unitName = {v: 'Voynich texts (Zattera glyph units)', l: 'German text (letters)'};
 function pageFigure(v, folio, m) {
  const pg = v.pages[folio], pf = data.pages[folio], [lo, hi] = dom(v, m);
  const fig = document.createElement('figure'); fig.style.setProperty('--ratio', pf.ratio);
  const ns = 'http://www.w3.org/2000/svg', svg = document.createElementNS(ns, 'svg');
  svg.setAttribute('role', 'img'); svg.setAttribute('aria-label', `${folio} · ${v.label}`); svg.setAttribute('viewBox', pf.viewBox);
  let sum = 0, n = 0;
  if (pg) for (let i = 0; i < pg.boxes.length; i++) {
   const [x, y, w, h] = pg.boxes[i], val = pg[m][i];
   const rect = document.createElementNS(ns, 'rect');
   rect.setAttribute('x', x); rect.setAttribute('y', y); rect.setAttribute('width', w); rect.setAttribute('height', h); rect.setAttribute('fill', paint(val, lo, hi));
   const t = document.createElementNS(ns, 'title'); t.textContent = `${pg.words[i]} · ${val === null ? 'no score' : fmt(val, m)}`; rect.append(t); svg.append(rect);
   if (val !== null) { sum += val; n++; }
  }
  const cap = document.createElement('figcaption'); cap.textContent = n ? `mean ${fmt(sum / n, m)}` : 'no score';
  fig.append(svg, cap); return fig;
 }
 function render() {
  const b = data.bifolia.find(x => x.id === sheet.value), m = measure.value;
  history.replaceState(null, '', '#' + new URLSearchParams({sheet: sheet.value, measure: m, scale: scale.value, layout: layout.value}));
  explain.textContent = data.measures[m] + '. Grey: fewer than 5 contributing source words (or, for MATTR, fewer than 100 preceding tokens). '
   + (m === 'mattr' ? 'MATTR is coloured on its absolute scale 0.5 to 1.0.' : scale.value === 'shared'
      ? 'One colour range per unit system (5th to 95th percentile over all texts of that system), so levels are comparable between texts.'
      : 'Each text uses its own 5th to 95th percentile range, as the app does for a single text; levels are then not comparable between texts.');
  legends.replaceChildren();
  const shown = m === 'mattr' ? [['', [0.5, 1.0]]] : (scale.value === 'shared' ? Object.entries(data.shared_domains).map(([u, d]) => [unitName[u], d[m]]) : []);
  for (const [name, [lo, hi]] of shown) {
   const div = document.createElement('div'); div.className = 'legend';
   const stops = Array.from({length: 11}, (_, k) => data.palette[Math.min(500, Math.floor(k / 10 * 500))]).join(',');
   div.innerHTML = `<div class="spectrum" style="background:linear-gradient(90deg,${stops})"></div><div class="ticks"><span>${fmt(lo, m)}</span><span>${fmt((lo + hi) / 2, m)}</span><span>${fmt(hi, m)}</span></div><small>${name}</small>`;
   legends.append(div);
  }
  blocks.replaceChildren();
  // Texts across and pages down, or transposed: pages across and each text version down. Compact keeps every page at
  // one height, about the size a page has with texts across.
  const pages = singulion(b.pages), across = layout.value !== 'texts', compact = layout.value === 'compact', name = v => short[v.key] || v.label;
  const cols = across ? pages : variants, rows = across ? variants : pages;
  const table = document.createElement('div'); table.className = 'compare-grid' + (across ? ' pages-across' : '') + (compact ? ' pages-compact' : ''); table.style.setProperty('--cols', cols.length); table.style.setProperty('--n', variants.length);
  table.append(document.createElement('div'));
  for (const c of cols) { const h = document.createElement('div'); h.className = 'col-head'; h.textContent = across ? c : name(c); table.append(h); }
  for (const r of rows) {
   const rh = document.createElement('div'); rh.className = 'row-head'; rh.textContent = across ? name(r) : r; table.append(rh);
   for (const c of cols) { const cell = document.createElement('div'); cell.className = 'cell'; cell.append(across ? pageFigure(r, c, m) : pageFigure(c, r, m)); table.append(cell); }
  }
  blocks.append(table);
 }
 for (const el of [sheet, measure, scale, layout]) el.addEventListener('change', render);
 render();
})();
"""

if __name__ == '__main__':
    main()
