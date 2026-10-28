"""T18. What the eye compares on the heatmap pages (27 October, user's observation).

Switching the app's colours between MATTR and component diversity, the manuscript's pages show the two tracking
each other and the natural text's pages do not. This script measures that: for each layout variant written by
heatmap_variants.py, the Spearman correlation between the app's MATTR colour (distinct share of the backward
100-token window ending at the token) and the spatial component diversity, word diversity and H2 of the words in
view, at token level, within pages (both demeaned by page) and between page means (pages of 100 or more scored
tokens), plus the spread of page-mean MATTR.
"""
import gzip
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import data as D
import component_check as CC
from geometry_inputs import validate_variant
from timing import shuffled_within

OUT = HERE / 'heatmap_variants'
VARIANTS = ('manuscript', 'manuscript_clean', 'timm', 'noinnov_far0', 'timm_spatial', 'noinnov_spatial', 'far0_spatial', 'bigram_whole', 'bigram_currier', 'bigram_section', 'gart_one_word_per_box', 'gart_character_budget', 'gart_own_lines')


def spearman(a, b):
    return float(np.corrcoef(np.argsort(np.argsort(a)), np.argsort(np.argsort(b)))[0, 1])


def demean(x, g):
    x = x.copy()
    for u in np.unique(g):
        m = g == u
        x[m] -= x[m].mean()
    return x


def main():
    res = {}
    print("MATTR colour (backward 100-token distinct share) against the diversity of the words in view")
    print(f"{'variant':24s} | {'tokens':>6s} | token-level Spearman: components, word diversity, H2 | within page: components, word diversity, H2 | page means (n): components, word diversity, H2 | sd of page-mean MATTR")
    texts = []
    app = CC.load_study_app('legacy')
    for key in VARIANTS:
        b = json.load(gzip.open(OUT / key / 'data/mattr_heatmap/words.json.gz', 'rt', encoding='utf8'))
        validate_variant(b, app)
        texts.append((key, dict(words=b['words'], lines=b['lines'], geometry=b['geometry'], components=b['components'])))
    # manuscript controls, built as in mechanism_check.py (same helper, same call order): words permuted inside paragraphs / pages, recorded boxes kept
    ms = D.manuscript()
    app = CC.load_study_app('legacy')
    tok = D.tokenize(ms)
    par_id = np.cumsum(tok['since_par'] == 0)
    texts.append(('manuscript_shuffled_paragraphs', CC.make_input(ms, shuffled_within(ms, tok, par_id), app['geometry'], CC.zattera)))
    texts.append(('manuscript_shuffled_pages', CC.make_input(ms, shuffled_within(ms, tok, tok['page']), app['geometry'], CC.zattera)))
    for key, inp in texts:
        meas = CC.measure(inp)
        words = inp['words']
        n = len(words)
        page = np.empty(n, dtype=object)
        for L in inp['lines']:
            page[L['start']:L['end']] = L['page']
        mattr = D.trailing_distinct(words, 100)
        m = np.isfinite(mattr) & np.isfinite(meas['components']) & np.isfinite(meas['h2'])
        c, w, h, y, g = meas['components'][m], meas['worddiv'][m], meas['h2'][m], mattr[m], page[m]
        pm = []
        for u in np.unique(g):
            mm = g == u
            if mm.sum() >= 100:
                pm.append((y[mm].mean(), c[mm].mean(), w[mm].mean(), h[mm].mean()))
        P = np.array(pm)
        r = dict(tokens=int(m.sum()), token=dict(components=spearman(y, c), worddiv=spearman(y, w), h2=spearman(y, h)),
                 within_page=dict(components=spearman(demean(y, g), demean(c, g)), worddiv=spearman(demean(y, g), demean(w, g)), h2=spearman(demean(y, g), demean(h, g))),
                 page_means=dict(pages=len(P), components=spearman(P[:, 0], P[:, 1]), worddiv=spearman(P[:, 0], P[:, 2]), h2=spearman(P[:, 0], P[:, 3])), sd_page_mean_mattr=float(P[:, 0].std()))
        res[key] = r
        print(f"{key:24s} | {r['tokens']:6d} | {r['token']['components']:+.2f} {r['token']['worddiv']:+.2f} {r['token']['h2']:+.2f} | "
              f"{r['within_page']['components']:+.2f} {r['within_page']['worddiv']:+.2f} {r['within_page']['h2']:+.2f} | ({len(P)}) {r['page_means']['components']:+.2f} {r['page_means']['worddiv']:+.2f} {r['page_means']['h2']:+.2f} | {r['sd_page_mean_mattr']:.3f}", flush=True)
    (HERE / 'mattr_vs_components.json').write_text(json.dumps(res, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
