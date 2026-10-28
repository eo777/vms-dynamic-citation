"""T10. What happens at a Bio page boundary: a supply shrink (novelty falls at the page start, as in a
page-window copier) or a change of unit (novelty rises, the new page uses other words)? By section.
  (1) novelty rate by tokens since the page start, with the previous page's last 50 tokens as reference
  (2) page-boundary penalty with the within-page denominator restricted to pairs that also cross a
      paragraph boundary (the page boundary beyond an ordinary paragraph boundary)
  (3) cosine of the first half of a page with the second half of the previous page (adjacent halves)
      against the second half of its own page (same-page halves), equal sizes
"""
from collections import Counter
import json
import sys

import numpy as np

sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
import data as D
from decompose import REFS, ref_words
from timing import laid_in
from visibility import ids_of
from continuity import section_of, SECTIONS

PAGE_BINS = [(0, 10), (10, 30), (30, 60), (60, 100), (100, 10 ** 6)]


def page_start_profile(ms, tok):
    fresh = D.fresh_indicator(tok['words']); page = tok['page']; sp = tok['since_page']
    sec_tok = np.array([section_of(ms['pages'][p]) for p in page])
    # tokens in the last 50 of a page whose NEXT page is in the same section
    npages = int(page.max()) + 1
    page_len = np.bincount(page, minlength=npages); from_end = page_len[page] - sp
    out = {}
    for s in SECTIONS:
        m = sec_tok == s
        row = {f'{a}-{b}': float(fresh[m & (sp >= a) & (sp < b) & (sp > 0)].mean()) for a, b in PAGE_BINS}
        row['first_word'] = float(fresh[m & (sp == 0)].mean())
        row['prev_last_50'] = float(fresh[m & (from_end <= 50)].mean())
        out[s] = row
    return out


def penalty_vs_paragraph(ms, tok, max_lag=50):
    ids = ids_of(tok['words']); page = tok['page']; par = np.cumsum(tok['since_par'] == 0)
    sec = {p['index']: section_of(p) for p in ms['pages']}
    sec_tok = np.array([sec[p] for p in page])
    acc = {s: np.zeros((2, 2)) for s in SECTIONS}
    for d in range(1, max_lag + 1):
        y = (ids[d:] == ids[:-d]).astype(float); cur = page[d:]; src = page[:-d]
        prev = cur == src + 1; same_sec = sec_tok[d:] == sec_tok[:-d]
        within_cross_par = (cur == src) & (par[d:] != par[:-d])
        for s in SECTIONS:
            m = sec_tok[d:] == s
            acc[s][0] += [y[m & prev & same_sec].sum(), (m & prev & same_sec).sum()]
            acc[s][1] += [y[m & within_cross_par].sum(), (m & within_cross_par).sum()]
    return {s: float((acc[s][0][0] / acc[s][0][1]) / (acc[s][1][0] / acc[s][1][1])) if acc[s][0][1] and acc[s][1][1] and acc[s][1][0] else np.nan for s in SECTIONS}


def cos(a, b):
    dot = sum(v * b[w] for w, v in a.items() if w in b)
    return dot / np.sqrt(sum(v * v for v in a.values()) * sum(v * v for v in b.values()))


def halves(ms, tok, min_tokens=120):
    words = np.array(tok['words'], dtype=object); page = tok['page']
    sec = {p['index']: section_of(p) for p in ms['pages']}
    npages = int(page.max()) + 1
    half = {}
    for p in range(npages):
        w = words[page == p]
        if len(w) >= min_tokens:
            h = len(w) // 2; half[p] = (Counter(w[:h].tolist()), Counter(w[h:].tolist()))
    out = {}
    for s in SECTIONS:
        adj = []; same = []
        for p in range(1, npages):
            if sec[p] == s and sec[p - 1] == s and p in half and p - 1 in half:
                adj.append(cos(half[p][0], half[p - 1][1])); same.append(cos(half[p][0], half[p][1]))
        out[s] = dict(n=len(adj), adjacent_halves=float(np.mean(adj)) if adj else np.nan, same_page_halves=float(np.mean(same)) if same else np.nan,
                      ratio=float(np.mean(adj) / np.mean(same)) if adj else np.nan)
    return out


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

    def mean_nested(dicts):
        if isinstance(dicts[0], dict):
            return {k: mean_nested([d[k] for d in dicts]) for k in dicts[0]}
        return float(np.nanmean(dicts))

    res = dict(page_start={}, penalty_vs_paragraph={}, halves={})
    for key, variants in texts.items():
        toks = [D.tokenize(ms, lines) for lines in variants]
        res['page_start'][key] = mean_nested([page_start_profile(ms, t) for t in toks])
        res['penalty_vs_paragraph'][key] = mean_nested([penalty_vs_paragraph(ms, t) for t in toks])
        res['halves'][key] = mean_nested([halves(ms, t) for t in toks])
    (D.HERE / 'pagestart.json').write_text(json.dumps(res, indent=1), encoding='utf-8')
    cols = ['prev_last_50', 'first_word'] + [f'{a}-{b}' for a, b in PAGE_BINS]
    for s in ('B', 'H', 'S'):
        print(f"\n== novelty by tokens since page start, section {s}: previous page's last 50 | first word | 1-9 | 10-29 | 30-59 | 60-99 | 100+")
        for key, r in res['page_start'].items():
            print(f"  {key:26s} " + ' '.join(f"{r[s][c]:6.3f}" for c in cols))
    print('\n== page-boundary penalty against within-page pairs that also cross a paragraph boundary (lags 1-50)')
    print(f"  {'text':26s} " + ' '.join(f"{s:>7s}" for s in SECTIONS))
    for key, r in res['penalty_vs_paragraph'].items():
        print(f"  {key:26s} " + ' '.join(f"{r[s]:7.2f}" for s in SECTIONS))
    print('\n== cosine: first half of a page with the previous page\'s second half / with its own second half (ratio; n transitions)')
    for key, r in res['halves'].items():
        print(f"  {key:26s} " + '  '.join(f"{s}: {r[s]['adjacent_halves']:.2f}/{r[s]['same_page_halves']:.2f} = {r[s]['ratio']:.2f} (n {r[s]['n']:.0f})" for s in SECTIONS))


if __name__ == '__main__':
    main()
