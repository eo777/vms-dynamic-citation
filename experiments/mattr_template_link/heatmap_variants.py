"""Heatmap pages of the experimental layouts in the governor app's own format (27 October, for verification).

For each layout used in sections 7 and 8 this writes a copy of the app's MATTR heatmap page whose word rectangles
and data bundle are the experimental text's, so the app's own code (heatmap.js, heatmap_sources.js, heatmap_math.js,
copied unchanged into heatmap_variants/shell/) draws the pages, colours the words by component diversity, H2, word
diversity or word impact, and shows the source cone and weighted pool when a word is clicked. The texts are built
exactly as in figures_pages.py (same seeds, same call order). Beside each page a CSV lists, for page f78r, every token's
box, pool size, component score, word diversity and outcomes as this study computed them, so the app's readout can
be checked against the numbers behind the tables.
Serve: python -m http.server 8766 in research/mattr_template_link_20261026/heatmap_variants, open http://127.0.0.1:8766/
"""
import csv
import gzip
from html import escape
import json
import re
import shutil
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import data as D
import component_check as CC
import layout_controls as LC
import native_layout as NL
from decompose import REFS, ref_words
from timing import laid_in

APP = D.src('apps/selfcitation_governor')
OUT = HERE / 'heatmap_variants'
SHELL = ['common.js', 'heatmap.js', 'heatmap_math.js', 'heatmap_sources.js', 'copy_math.js', 'spatial_review.js', 'heatmap_page.js', 'heatmap.css', 'style.css']
PAGE = 'f78r'


def build_texts(ms, app):
    page_sizes = [sum(len(ms['lines'][l]['words']) for l in range(p['start_line'], p['end_line'])) for p in ms['pages']]
    frames = CC.line_frames(app, ms)
    LC.rng = np.random.default_rng(78)
    NL.rng = np.random.default_rng(78)
    ms_lines = [L['words'] for L in ms['lines']]
    timm = D.read_stream(D.STREAMS['timm'][1][0])              # m_timm: innovate False, Timm's own source choice
    noinnov = D.read_stream(D.STREAMS['noinnov_far0'][1][0])   # n_noinnov_far0: governed hooks, page window only, innovate False
    timm_sp = D.read_stream(D.STREAMS['timm_spatial'][1][0])        # p_timm_spatial: Timm with his page draws taken from the words in view (recorded geometry)
    noinnov_sp = D.read_stream(D.STREAMS['noinnov_spatial'][1][0])  # p_noinnov_spatial: the governed no-innovator copier, page draws from the words in view
    far0_sp = D.read_stream(D.STREAMS['far0_spatial'][1][0])        # p_far0_spatial: the far-0 configuration with the innovator, page draws from the words in view
    gart_words = ref_words(REFS['de_gart_augsburg1487'])
    gart_box = laid_in(ms, gart_words, page_sizes)
    gart_line = LC.fill_by_chars(ms, gart_words)
    gart_native, gart_native_geom, start = NL.native_layout(ms, app, NL.native_lines(NL.GART))
    bigram = LC.bigram_whole(ms)
    bigram_c = LC.markov_text(ms, 'currier')
    bigram_s = LC.markov_text(ms, 'section')
    letters = lambda w: list(w)
    flags = CC.oversized_flags(app, ms)
    clean = [None if flags[i] else g for i, g in enumerate(app['geometry'])]
    return [
        ('manuscript', 'Manuscript, recorded word boxes (the app\'s own data, oversized rectangles included as recorded)', ms_lines, app['geometry'], CC.zattera, 'zattera; lossless; within-word pairs only'),
        ('manuscript_clean', f'Manuscript, recorded word boxes with the {sum(flags)} oversized rectangles removed (those tokens keep their place but have no box)', ms_lines, clean, CC.zattera, 'zattera; lossless; within-word pairs only'),
        ('timm', 'Original Timm self-citation (no innovator), laid into the manuscript\'s lines; boxes by character position', timm, CC.synthetic_geometry(timm, frames, ms), CC.zattera, 'zattera; lossless; within-word pairs only'),
        ('noinnov_far0', 'Governed page-window copier without the innovator (far 0), laid into the manuscript\'s lines; boxes by character position', noinnov, CC.synthetic_geometry(noinnov, frames, ms), CC.zattera, 'zattera; lossless; within-word pairs only'),
        ('timm_spatial', 'Original Timm with his page draws taken from the words in view on the recorded page geometry (cone above, reach to the left, distance weights); laid into the lines as it was written', timm_sp, CC.synthetic_geometry(timm_sp, frames, ms), CC.zattera, 'zattera; lossless; within-word pairs only'),
        ('noinnov_spatial', 'Governed copier without the innovator, page draws from the words in view on the recorded page geometry (far 0); laid into the lines as it was written', noinnov_sp, CC.synthetic_geometry(noinnov_sp, frames, ms), CC.zattera, 'zattera; lossless; within-word pairs only'),
        ('far0_spatial', 'Governed copier with the innovator (far 0), page draws from the words in view on the recorded page geometry; laid into the lines as it was written', far0_sp, CC.synthetic_geometry(far0_sp, frames, ms), CC.zattera, 'zattera; lossless; within-word pairs only'),
        ('bigram_whole', 'Markov chain (word bigrams) trained on the whole manuscript, laid into the manuscript\'s lines; manuscript boxes, oversized ones removed', bigram, clean, CC.zattera, 'zattera; lossless; within-word pairs only'),
        ('bigram_currier', 'Markov chains (word bigrams) trained on Currier A and on Currier B separately, laid into the manuscript\'s lines', bigram_c, clean, CC.zattera, 'zattera; lossless; within-word pairs only'),
        ('bigram_section', 'Markov chains (word bigrams) trained on each section separately, laid into the manuscript\'s lines', bigram_s, clean, CC.zattera, 'zattera; lossless; within-word pairs only'),
        ('gart_one_word_per_box', 'Gart der Gesundheit 1487, one word per manuscript box (recorded boxes, oversized ones removed)', gart_box, clean, letters, 'letters; letter pairs'),
        ('gart_character_budget', 'Gart 1487, each manuscript line filled to its character budget; boxes by character position', gart_line, CC.synthetic_geometry(gart_line, frames, ms), letters, 'letters; letter pairs'),
        ('gart_own_lines', f'Gart 1487 in its own printed lines (from printed line {start + 1}), one per manuscript line slot', gart_native, gart_native_geom, letters, 'letters; letter pairs'),
    ]


def rounded(geometry):
    return [None if b is None else [int(round(v)) for v in b] for b in geometry]


def page_html(template, key, label, inp, keys):
    template = re.sub(r'((?:src|href)="[^"?]+)\?v=[^" ]+(?=")', r'\1', template)
    words = inp['words']
    geometry = inp['geometry']
    by_page = {}
    for L in inp['lines']:
        by_page.setdefault(L['page'], []).append((L['start'], L['end']))

    def rebuild(m):
        page = m.group(2)
        rects = []
        first = True
        for start, end in by_page.get(page, []):
            for i in range(start, end):
                b = geometry[i]
                if b is None:
                    continue
                w, h = max(1, b[2] - b[0]), max(1, b[3] - b[1])
                rects.append(f'<rect x="{b[0]}" y="{b[1]}" width="{w}" height="{h}" fill="#d5dadd" data-token-indices="{i}" data-d100="" role="button" '
                             f'tabindex="{0 if first else -1}" aria-label="Inspect {escape(words[i], quote=True)}"><title>{escape(words[i])}</title></rect>')
                first = False
        return m.group(1) + ''.join(rects) + m.group(4)

    html = re.sub(r'(<svg role="group" aria-label="([^"]+) word diversity" viewBox="[^"]+">)(.*?)(</svg>)', rebuild, template, flags=re.S)
    html = html.replace('<link rel="stylesheet" href="style.css">', '<link rel="stylesheet" href="../shell/style.css">')
    html = html.replace('<link rel="stylesheet" href="heatmap.css">', '<link rel="stylesheet" href="../shell/heatmap.css">')
    html = html.replace('<script src="site_nav.js" defer></script>', '')
    for f in ('common.js', 'heatmap_math.js', 'heatmap_sources.js', 'copy_math.js', 'spatial_review.js', 'heatmap_page.js', 'heatmap.js'):
        html = html.replace(f'<script src="{f}"></script>', f'<script src="../shell/{f}"></script>')
    html = html.replace('<title>Governed self-citation · MATTR heatmap</title>', f'<title>Layout variant · {escape(label)}</title>')
    links = ' · '.join(f'<a href="../{k}/heatmap.html">{escape(k)}</a>' for k in keys)
    html = re.sub(r'<nav class="site-nav">.*?</nav>', f'<nav class="site-nav"><a href="../index.html">Layout variants index</a> · {links}</nav>', html, count=1, flags=re.S)
    html = html.replace('<h1>MATTR heatmap', f'<h1>MATTR heatmap · variant: {escape(label)}', 1)
    assert html.count('data-token-indices=') == sum(1 for b in geometry if b is not None)
    return html


def token_csv(path, inp, meas, out, lines_meta):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['token_index', 'page', 'line_locus', 'word', 'x0', 'y0', 'x1', 'y1', 'pool_n', 'pair_ess', 'components', 'h2', 'worddiv',
                    'preceding99_components', 'app_impact', 'arrival_burden', 'repeat_in_preceding_99'])
        for i, (page, locus) in lines_meta.items():
            b = inp['geometry'][i] or [None] * 4
            w.writerow([i, page, locus, inp['words'][i], *b, int(meas['n'][i]), f"{meas['pair_ess'][i]:.3f}", f"{meas['components'][i]:.3f}", f"{meas['h2'][i]:.3f}",
                        f"{meas['worddiv'][i]:.3f}", f"{meas['back_components'][i]:.3f}", f"{out['app_impact'][i]:.4f}", f"{out['arrival'][i]:.4f}", int(out['repeat100'][i])])


def main():
    ms = D.manuscript()
    app = CC.load_study_app('legacy')
    template = (APP / 'heatmap.html').read_text(encoding='utf8')
    OUT.mkdir(exist_ok=True)
    (OUT / 'shell').mkdir(exist_ok=True)
    for f in SHELL:
        shutil.copy2(APP / f, OUT / 'shell' / f)
    variants = build_texts(ms, app)
    keys = [v[0] for v in variants]
    summary = []
    for key, label, lines, geometry, comp, mode in variants:
        inp = CC.make_input(ms, lines, geometry, comp)
        inp['geometry'] = rounded(inp['geometry'])
        meas = CC.measure(inp)
        node, group, bstart, bend = CC.token_meta(ms, lines)
        out = CC.outcomes(inp['words'], bstart, bend)
        folder = OUT / key
        (folder / 'data/mattr_heatmap').mkdir(parents=True, exist_ok=True)
        bundle = dict(schema=2, window=100, input_geometry_provenance=app['geometry_provenance'], words=inp['words'], lines=inp['lines'], geometry=inp['geometry'], components=inp['components'],
                      component_mode=mode, palette=app['palette'])
        (folder / 'data/mattr_heatmap/words.json.gz').write_bytes(gzip.compress(json.dumps(bundle, separators=(',', ':')).encode('utf8'), mtime=0))
        (folder / 'heatmap.html').write_text(page_html(template, key, label, inp, keys), encoding='utf8')
        lines_meta = {}
        for L in inp['lines']:
            if L['page'] == PAGE:
                for i in range(L['start'], L['end']):
                    lines_meta[i] = (L['page'], L['locus'])
        token_csv(folder / f'{PAGE}_tokens.csv', inp, meas, out, lines_meta)
        idx = np.array(sorted(lines_meta))
        valid = meas['components'][idx]
        summary.append(dict(key=key, label=label, tokens=len(inp['words']), page_tokens=len(idx), page_mean_components=float(np.nanmean(valid)),
                            page_mattr=D.mattr([inp['words'][i] for i in idx]), geometry_known=int(sum(1 for b in inp['geometry'] if b is not None))))
        print(key, 'written', flush=True)
    items = ''.join(f'<li><a href="{s["key"]}/heatmap.html"><b>{escape(s["key"])}</b></a>: {escape(s["label"])}. {s["tokens"]:,} tokens, {s["geometry_known"]:,} with boxes; '
                    f'page {PAGE}: {s["page_tokens"]} words, MATTR100 {s["page_mattr"]:.3f}, mean component score {s["page_mean_components"]:.1f}. '
                    f'<a href="{s["key"]}/{PAGE}_tokens.csv">{PAGE} token table</a></li>' for s in summary)
    index = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Layout variants in the app's heatmap</title>
<link rel="stylesheet" href="shell/style.css"><style>main{{max-width:60rem;margin:2rem auto;padding:0 1rem;line-height:1.45}}li{{margin:.6rem 0}}</style></head>
<body><main><h1>Layout variants in the governor app's heatmap format</h1>
<p>Each page below is the app's own MATTR heatmap (its scripts copied unchanged into <code>shell/</code>) with the word rectangles and data bundle replaced by one
experimental text of <code>research/mattr_template_link_20261026</code>, sections 7 and 8. In each page choose <b>Direction: Spatial sources</b> and
<b>Colors: Component diversity</b> (or Source word diversity, Glyph H2, Word repetition impact), pick a scope, and click any word to see its cone, its
weighted source pool and its score, computed by the app's code. The CSV beside each page lists the study's own per-token numbers for page {PAGE}
(pool size, effective pair sources, component score, H2, word diversity, preceding-99 components, word impact, arrival burden, repeat flag) for
comparison with the app's readout.</p>
<p><b>How the study's statistic is determined.</b> For token N: (1) the pool = earlier tokens on the same page whose rectangle intersects the cone
(8 line spacings up, 45° half-angle) or lies within 3 median word widths to the left on the same line, distance-weighted, at most 100; (2) component
score = 2 to the power of the entropy of the within-word unit pairs over the pool (Zattera units for Voynich text, letters for Gart); word diversity =
1 − Σ p(spelling)²; (3) outcome = word impact: the share of the 100-token windows containing N in which another copy of N's spelling occurs; (4) within
each bifolium, tokens whose 100 windows lie inside the bifolium are split into quintiles of the score, and the mean outcome of the lowest quintile minus
the highest is pooled over bifolia; (5) the pool-size-stratified version repeats (4) inside tertiles of pool size and averages the three.</p>
<ul>{items}</ul>
<p>The manuscript variant is the app's own data, as a check that this builder reproduces the app; it keeps the app's oversized recorded rectangles
(on f78r the box of dar spans the text block). The manuscript_clean variant and every other recorded-box variant drop those rectangles: the tokens keep
their place in the text but have no box, so they are neither drawn nor eligible as sources or targets. Geometry for texts whose words do not match the recorded
boxes is synthetic: boxes laid by character position inside each manuscript line's recorded extent (Original Timm, no-innovator far 0, Gart character budget) or, for Gart's own
lines, from the line's left edge with the page's character width.</p></main></body></html>'''
    (OUT / 'index.html').write_text(index, encoding='utf8')
    (OUT / 'summary.json').write_text(json.dumps(summary, indent=1), encoding='utf8')
    print('index written;', len(summary), 'variants')


if __name__ == '__main__':
    main()
