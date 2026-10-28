"""T9. Section continuity. Does the previous page matter more in Bio, where the text runs on, than in
Herbal, where each page is its own plant, with Stars resetting at paragraphs? Manuscript alone, by
section; the generators (section-blind) show what the layout alone does to each statistic, and natural
prose cut into the same pages shows a text that continues across every boundary without any reset.

  structure : share of pages whose first line opens a paragraph (does the text run on mid-paragraph?)
  P1/P2     : page-boundary penalty = repeat rate across the boundary / inside the page, same lags, by
              lag band and section (1.0 = the boundary is transparent)
  recency   : repeat rate inside pages by lag, over the page-shuffle expectation (1.0 = no recency)
  P3        : page-bag cosine, same bifolium / other bifolium adjacent / other bifolium distant, by section
  P4        : paragraph-boundary penalty = repeat rate across a paragraph boundary / inside paragraphs,
              lags 1-25, by section
  P5        : carry-over of diversity across the page boundary (previous page's last 100 against the
              page's first 100), by section
"""
from collections import Counter, defaultdict
import json
import sys

import numpy as np

sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
import data as D
from decompose import REFS, ref_words
from timing import laid_in
from visibility import pair_stats, ids_of

rng = np.random.default_rng(7)
BANDS = [(1, 10), (11, 25), (26, 50)]
SECTIONS = ('H', 'B', 'S', 'other')


def section_of(page):
    s = page['section']
    return s if s in ('H', 'B', 'S') else 'other'


def structure(ms):
    out = {}
    for sec in SECTIONS:
        pages = [p for p in ms['pages'] if section_of(p) == sec]
        first = [ms['lines'][p['start_line']]['first'] for p in pages]
        out[sec] = dict(pages=len(pages), first_line_opens_paragraph=float(np.mean(first)),
                        paragraphs_per_page=float(np.mean([sum(ms['lines'][l]['first'] for l in range(p['start_line'], p['end_line'])) for p in pages])))
    return out


def boundary_penalty(ms, tok):
    per_tr, per_within = pair_stats(tok)
    sec = {p['index']: section_of(p) for p in ms['pages']}
    acc = {s: {b: np.zeros((2, 2)) for b in BANDS} for s in SECTIONS}
    for p, arr in per_tr.items():
        if sec[p] != sec[p - 1]:
            continue
        for lo, hi in BANDS:
            acc[sec[p]][(lo, hi)][0] += arr[lo:hi + 1].sum(axis=0)
            acc[sec[p]][(lo, hi)][1] += per_within[p][lo:hi + 1].sum(axis=0)
    out = {}
    for s in SECTIONS:
        row = {}
        for b in BANDS:
            c, w = acc[s][b]
            row[f'{b[0]}-{b[1]}'] = dict(cross=c[0] / c[1] if c[1] else np.nan, within=w[0] / w[1] if w[1] else np.nan,
                                        penalty=(c[0] / c[1]) / (w[0] / w[1]) if c[1] and w[1] and w[0] else np.nan, cross_pairs=int(c[1]))
        c = sum(acc[s][b][0] for b in BANDS); w = sum(acc[s][b][1] for b in BANDS)
        row['1-50'] = dict(cross=c[0] / c[1], within=w[0] / w[1], penalty=(c[0] / c[1]) / (w[0] / w[1]), cross_pairs=int(c[1]))
        out[s] = row
    return out


def recency(ms, tok, max_lag=100):
    """Within-page repeat rate by lag over the page-shuffle expectation (Simpson index of the page bag)."""
    ids = ids_of(tok['words']); page = tok['page']; npages = int(page.max()) + 1
    sec = {p['index']: section_of(p) for p in ms['pages']}
    simpson = np.zeros(npages)
    for p in range(npages):
        c = np.array(list(Counter(ids[page == p]).values()), float); n = c.sum()
        simpson[p] = (c * (c - 1)).sum() / (n * (n - 1)) if n > 1 else np.nan
    bands = [(1, 1), (2, 5), (6, 10), (11, 25), (26, 50), (51, 100)]
    acc = {s: {b: [0.0, 0.0, 0.0] for b in bands} for s in SECTIONS}
    for d in range(1, max_lag + 1):
        y = (ids[d:] == ids[:-d]).astype(float); cur = page[d:]; same = cur == page[:-d]
        obs = np.bincount(cur[same], weights=y[same], minlength=npages); n = np.bincount(cur[same], minlength=npages)
        for p in range(npages):
            if n[p] and np.isfinite(simpson[p]):
                for b in bands:
                    if b[0] <= d <= b[1]:
                        a = acc[sec[p]][b]; a[0] += obs[p]; a[1] += n[p] * simpson[p]; a[2] += n[p]
    return {s: {f'{b[0]}-{b[1]}': (acc[s][b][0] / acc[s][b][1] if acc[s][b][1] else np.nan) for b in bands} for s in SECTIONS}


def paragraph_penalty(ms, tok, max_lag=25):
    ids = ids_of(tok['words']); page = tok['page']; par = np.cumsum(tok['since_par'] == 0)
    sec_tok = np.array([section_of(ms['pages'][p]) for p in page])
    acc = {s: np.zeros((2, 2)) for s in SECTIONS}
    for d in range(1, max_lag + 1):
        y = (ids[d:] == ids[:-d]).astype(float); same_page = page[d:] == page[:-d]; same_par = par[d:] == par[:-d]
        for s in SECTIONS:
            m = same_page & (sec_tok[d:] == s)
            acc[s][0] += [y[m & ~same_par].sum(), (m & ~same_par).sum()]
            acc[s][1] += [y[m & same_par].sum(), (m & same_par).sum()]
    out = {}
    for s in SECTIONS:
        (c, cn), (w, wn) = acc[s]
        out[s] = dict(cross_paragraph=c / cn if cn else np.nan, within_paragraph=w / wn if wn else np.nan,
                      penalty=(c / cn) / (w / wn) if cn and wn and w else np.nan, cross_pairs=int(cn))
    return out


def similarity_by_section(ms, tok, min_tokens=150):
    pages = {p['index']: p for p in ms['pages']}
    ids = np.array(tok['words'], dtype=object); page = tok['page']
    bags = {}
    for p in pages:
        m = page == p
        if m.sum() >= min_tokens:
            bags[p] = Counter(ids[m].tolist())
    out = {}
    for s in SECTIONS:
        ps = sorted(p for p in bags if section_of(pages[p]) == s)
        same = []; near = []; far = []
        for i, a in enumerate(ps):
            for b in ps[i + 1:]:
                ka, kb = bags[a], bags[b]
                dot = sum(v * kb[w] for w, v in ka.items() if w in kb)
                cos = dot / np.sqrt(sum(v * v for v in ka.values()) * sum(v * v for v in kb.values()))
                if pages[a]['node'] == pages[b]['node']:
                    same.append(cos)
                elif b - a <= 2:
                    near.append(cos)
                elif b - a >= 5:
                    far.append(cos)
        out[s] = dict(pages=len(ps), same_bifolium=float(np.mean(same)) if same else np.nan, other_bifolium_adjacent=float(np.mean(near)) if near else np.nan,
                      other_bifolium_distant=float(np.mean(far)) if far else np.nan)
    return out


def carry_over(ms, tok):
    words = tok['words']; page = tok['page']
    sec = {p['index']: section_of(p) for p in ms['pages']}
    starts = {int(p): int(i) for p, i in zip(*np.unique(page, return_index=True))}
    xs = defaultdict(list); ys = defaultdict(list)
    for p in range(1, int(page.max()) + 1):
        if sec[p] != sec[p - 1] or p not in starts:
            continue
        t0 = starts[p]
        if t0 < 100 or t0 + 100 > len(words):
            continue
        xs[sec[p]].append(len(set(words[t0 - 100:t0])) / 100); ys[sec[p]].append(len(set(words[t0:t0 + 100])) / 100)
    return {s: dict(n=len(xs[s]), r=float(np.corrcoef(xs[s], ys[s])[0, 1]) if len(xs[s]) > 3 else np.nan,
                    prev_end=float(np.mean(xs[s])) if xs[s] else np.nan, page_start=float(np.mean(ys[s])) if ys[s] else np.nan) for s in SECTIONS}


def main():
    ms = D.manuscript()
    texts = {'manuscript': [[L['words'] for L in ms['lines']]]}
    for key, (label, srcs) in D.STREAMS.items():
        texts[key] = [D.read_stream(s) for s in srcs[:3]]
    page_sizes = [sum(len(ms['lines'][l]['words']) for l in range(p['start_line'], p['end_line'])) for p in ms['pages']]
    for key in ('la_galen_simplicium', 'la_dioscorides_longob', 'la_rhazes_almansor', 'la_hildegard_physica', 'de_gart_augsburg1487'):
        words = ref_words(REFS[key])
        if len(words) >= sum(page_sizes) + 10:
            texts['ref_' + key] = [laid_in(ms, words, page_sizes)]
    results = dict(structure=structure(ms), boundary={}, recency={}, paragraph={}, similarity={}, carry_over={})

    def mean_nested(dicts):
        if isinstance(dicts[0], dict):
            return {k: mean_nested([d[k] for d in dicts]) for k in dicts[0]}
        return float(np.nanmean(dicts))

    for key, variants in texts.items():
        toks = [D.tokenize(ms, lines) for lines in variants]
        results['boundary'][key] = mean_nested([boundary_penalty(ms, t) for t in toks])
        results['recency'][key] = mean_nested([recency(ms, t) for t in toks])
        results['paragraph'][key] = mean_nested([paragraph_penalty(ms, t) for t in toks])
        results['similarity'][key] = mean_nested([similarity_by_section(ms, t) for t in toks])
        results['carry_over'][key] = mean_nested([carry_over(ms, t) for t in toks])
    (D.HERE / 'continuity.json').write_text(json.dumps(results, indent=1), encoding='utf-8')

    print('== structure (manuscript): pages, share of pages whose first line opens a paragraph, paragraphs per page')
    for s, r in results['structure'].items():
        print(f"  {s:6s} pages {r['pages']:3d}  first line opens paragraph {r['first_line_opens_paragraph']:.2f}  paragraphs/page {r['paragraphs_per_page']:.1f}")
    print('\n== P1/P2 page-boundary penalty (cross-boundary repeat rate / within-page rate, same lags) by section and lag band')
    print(f"{'text':26s} " + ' '.join(f"{s + ' ' + b:>12s}" for s in SECTIONS for b in ('1-10', '11-25', '26-50', '1-50')))
    for key, r in results['boundary'].items():
        print(f"{key:26s} " + ' '.join(f"{r[s][b]['penalty']:12.2f}" for s in SECTIONS for b in ('1-10', '11-25', '26-50', '1-50')))
    print('   cross-boundary pairs (manuscript, lags 1-50):', {s: results['boundary']['manuscript'][s]['1-50']['cross_pairs'] for s in SECTIONS})
    print('\n== recency inside pages: repeat rate over the page-shuffle expectation, by lag band and section (1.0 = none)')
    print(f"{'text':26s} " + ' '.join(f"{s + ' ' + b:>10s}" for s in SECTIONS for b in ('1-1', '2-5', '6-10', '11-25', '26-50', '51-100')))
    for key, r in results['recency'].items():
        print(f"{key:26s} " + ' '.join(f"{r[s][b]:10.2f}" for s in SECTIONS for b in ('1-1', '2-5', '6-10', '11-25', '26-50', '51-100')))
    print('\n== P4 paragraph-boundary penalty (repeat rate across a paragraph boundary / inside paragraphs, lags 1-25) by section')
    print(f"{'text':26s} " + ' '.join(f"{s:>8s}" for s in SECTIONS))
    for key, r in results['paragraph'].items():
        print(f"{key:26s} " + ' '.join(f"{r[s]['penalty']:8.2f}" for s in SECTIONS))
    print('\n== P3 page-bag cosine by section: same bifolium / other bifolium adjacent (d<=2) / other bifolium distant (d>=5)')
    for key, r in results['similarity'].items():
        print(f"{key:26s} " + '  '.join(f"{s}: {r[s]['same_bifolium']:.2f}/{r[s]['other_bifolium_adjacent']:.2f}/{r[s]['other_bifolium_distant']:.2f}" for s in SECTIONS))
    print('\n== P5 carry-over across the page boundary: r(previous page last-100 distinct share, page first-100 distinct share) by section; n transitions')
    for key, r in results['carry_over'].items():
        print(f"{key:26s} " + '  '.join(f"{s}: r {r[s]['r']:+.2f} (n {r[s]['n']:.0f}; {r[s]['prev_end']:.2f}->{r[s]['page_start']:.2f})" for s in SECTIONS))


if __name__ == '__main__':
    main()
