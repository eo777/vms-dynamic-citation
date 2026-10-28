"""T7. Tests that do not depend on how any generator assembles words.

(a) Shift-share. The flowing novelty rate (share of tokens not seen in the previous 100) of a group is the
    layout's distribution of tokens over paragraph depth and page position, times the text's novelty rate
    in each cell. A step between groups splits exactly into a LAYOUT part (the cell shares change, rates
    held) and a RATE part (the rates change, shares held). For a text whose falls are made by the layout
    the layout part carries the step; for a change of register the rate part does.
(b) Within a group, does page novelty track the page's paragraph length and line width (the features that
    move the generators)? Partial correlations controlling page size; natural texts cut into the same
    pages share the covariates exactly and cannot respond, so they give the noise band.
(c) Is a page's vocabulary inherited from the pages just before it or drawn from a section-wide register?
    Cosine similarity of page bags by Path 1 distance, cross-bifolium; same-bifolium pairs by physical
    relation and distance.
"""
from collections import Counter, defaultdict
import json
import sys

import numpy as np

sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
import data as D
from decompose import REFS, ref_words
from timing import laid_in

rng = np.random.default_rng(9)
MIN_TOKENS = 150
PAR_BINS = [(0, 1), (1, 10), (10, 20), (20, 40), (40, 80), (80, 10 ** 6)]
PAGE_BINS = [(0, 10), (10, 30), (30, 10 ** 6)]
STEPS = [('1b', '1.5a'), ('3b', '3a'), ('3c', '4c'), ('4c', '4a'), ('3c', '4a')]


def cells(tok):
    c = np.full(len(tok['words']), -1)
    for i, (a, b) in enumerate(PAR_BINS):
        for j, (p, q) in enumerate(PAGE_BINS):
            m = (tok['since_par'] >= a) & (tok['since_par'] < b) & (tok['since_page'] >= p) & (tok['since_page'] < q)
            c[m] = i * len(PAGE_BINS) + j
    return c


def shift_share(ms, tok, groups_of_token):
    fresh = D.fresh_indicator(tok['words']).astype(float); cell = cells(tok)
    ncell = len(PAR_BINS) * len(PAGE_BINS)
    share = {}; rate = {}; F = {}
    for g in set(groups_of_token):
        m = groups_of_token == g
        share[g] = np.array([(cell[m] == c).mean() for c in range(ncell)])
        rate[g] = np.array([fresh[m & (cell == c)].mean() if (m & (cell == c)).any() else np.nan for c in range(ncell)])
        F[g] = float(fresh[m].mean())
    out = {}
    for g1, g2 in STEPS:
        r1 = np.nan_to_num(rate[g1], nan=np.nanmean(rate[g1])); r2 = np.nan_to_num(rate[g2], nan=np.nanmean(rate[g2]))
        layout = 0.5 * (((share[g2] - share[g1]) * r1).sum() + ((share[g2] - share[g1]) * r2).sum())
        rates = 0.5 * ((share[g2] * (r2 - r1)).sum() + (share[g1] * (r2 - r1)).sum())
        out[f'{g1}->{g2}'] = dict(total=F[g2] - F[g1], layout=float(layout), rate=float(rates), F1=F[g1], F2=F[g2])
    return out


def page_table(ms, tok):
    fresh = D.fresh_indicator(tok['words'])
    rows = []
    for p in ms['pages']:
        m = tok['page'] == p['index']
        n = int(m.sum())
        if n < MIN_TOKENS:
            continue
        ls = range(p['start_line'], p['end_line'])
        n_par = sum(1 for l in ls if ms['lines'][l]['first']) or 1
        rows.append(dict(page=p['index'], group=p['group'], node=p['node'], tokens=n, fresh=float(fresh[m].mean()),
                         par_tokens=n / n_par, line_chars=float(np.mean([ms['lines'][l]['chars'] for l in ls])),
                         counter=Counter(np.array(tok['words'], dtype=object)[m].tolist())))
    return rows


def demean(x, groups):
    x = np.asarray(x, float); out = x.copy()
    for g in set(groups):
        m = np.array([gg == g for gg in groups]); out[m] -= x[m].mean()
    return out


def partial_r(y, x, z):
    """Correlation of y and x after regressing both on z (with intercept)."""
    Z = np.column_stack([np.ones(len(z)), z])
    ry = y - Z @ np.linalg.lstsq(Z, y, rcond=None)[0]; rx = x - Z @ np.linalg.lstsq(Z, x, rcond=None)[0]
    return float(np.corrcoef(ry, rx)[0, 1])


def layout_association(rows, scope):
    rows = [r for r in rows if scope is None or r['group'] == scope]
    counts = Counter(r['group'] for r in rows); rows = [r for r in rows if counts[r['group']] >= 3]
    groups = [r['group'] for r in rows]
    y = demean([r['fresh'] for r in rows], groups); size = demean(np.log([r['tokens'] for r in rows]), groups)
    out = dict(pages=len(rows))
    for cov in ('par_tokens', 'line_chars'):
        x = demean(np.log([r[cov] for r in rows]), groups)
        out[f'fresh~{cov}'] = partial_r(y, x, size)
    return out


def relation(pa, pb):
    if pa['leaf'] == pb['leaf']:
        return 'same leaf'
    return 'same face' if pa['face'] == pb['face'] else 'diagonal'


def distance_decay(rows, ms, scope):
    pages = {p['index']: p for p in ms['pages']}
    rows = [r for r in rows if scope is None or r['group'] == scope]
    by_group = defaultdict(list)
    for r in rows:
        by_group[r['group']].append(r)
    cross = defaultdict(list); same = defaultdict(list)
    for g, rs in by_group.items():
        for i, a in enumerate(rs):
            for b in rs[i + 1:]:
                d = b['page'] - a['page']
                ka, kb = a['counter'], b['counter']
                dot = sum(v * kb[w] for w, v in ka.items() if w in kb)
                cos = dot / np.sqrt(sum(v * v for v in ka.values()) * sum(v * v for v in kb.values()))
                if a['node'] == b['node']:
                    same[(relation(pages[a['page']], pages[b['page']]), d)].append(cos)
                else:
                    cross[min(d, 8)].append(cos)
    xs = []; ys = []
    for k, v in cross.items():
        xs += [k] * len(v); ys += v
    return dict(cross_by_distance={str(k): float(np.mean(v)) for k, v in sorted(cross.items())},
                cross_slope=float(np.polyfit(xs, ys, 1)[0]) if len(set(xs)) > 1 else float('nan'),
                cross_1=float(np.mean(cross[1])) if cross[1] else None, cross_5plus=float(np.mean([c for k, v in cross.items() if k >= 5 for c in v])),
                same_by_relation={f'{rel} d{d}': dict(n=len(v), cosine=float(np.mean(v))) for (rel, d), v in sorted(same.items())})


def main():
    ms = D.manuscript()
    texts = {'manuscript': [[L['words'] for L in ms['lines']]]}
    for key, (label, srcs) in D.STREAMS.items():
        texts[key] = [D.read_stream(s) for s in srcs]
    page_sizes = [sum(len(ms['lines'][l]['words']) for l in range(p['start_line'], p['end_line'])) for p in ms['pages']]
    for key in ('la_galen_simplicium', 'la_dioscorides_longob', 'la_rhazes_almansor', 'la_hildegard_physica', 'de_gart_augsburg1487'):
        words = ref_words(REFS[key])
        if len(words) >= sum(page_sizes) + 10:
            texts['ref_' + key] = [laid_in(ms, words, page_sizes)]
    results = dict(shift_share={}, layout_association={}, distance_decay={})
    for key, variants in texts.items():
        toks = [D.tokenize(ms, lines) for lines in variants]
        ss = [shift_share(ms, t, np.array([ms['lines'][l]['group'] for l in t['line']])) for t in toks]
        results['shift_share'][key] = {s: {k: float(np.mean([x[s][k] for x in ss])) for k in ss[0][s]} for s in ss[0]}
        tabs = [page_table(ms, t) for t in toks]
        for scope, name in ((None, 'all_within_group'), ('4a', 'bio')):
            per = [layout_association(t, scope) for t in tabs]
            results['layout_association'].setdefault(name, {})[key] = {k: float(np.mean([p[k] for p in per])) for k in per[0]}
            perd = [distance_decay(t, ms, scope) for t in tabs]
            agg = dict(cross_slope=float(np.mean([p['cross_slope'] for p in perd])), cross_1=float(np.mean([p['cross_1'] for p in perd])),
                       cross_5plus=float(np.mean([p['cross_5plus'] for p in perd])),
                       cross_by_distance={k: float(np.mean([p['cross_by_distance'][k] for p in perd])) for k in perd[0]['cross_by_distance']},
                       same_by_relation={k: float(np.mean([p['same_by_relation'][k]['cosine'] for p in perd if k in p['same_by_relation']])) for k in perd[0]['same_by_relation']},
                       same_n={k: perd[0]['same_by_relation'][k]['n'] for k in perd[0]['same_by_relation']})
            results['distance_decay'].setdefault(name, {})[key] = agg
    (D.HERE / 'layout_within.json').write_text(json.dumps(results, indent=1), encoding='utf-8')

    print('== shift-share of the flowing novelty rate (fresh at lag 100): total = layout part + rate part')
    for step in [f'{a}->{b}' for a, b in STEPS]:
        print(f'\n{step}')
        for key, r in results['shift_share'].items():
            s = r[step]
            print(f"  {key:28s} F {s['F1']:.3f} -> {s['F2']:.3f}  total {s['total']:+.3f} = layout {s['layout']:+.3f} + rate {s['rate']:+.3f}")
    for name in ('all_within_group', 'bio'):
        la = results['layout_association'][name]
        print(f"\n== page novelty against layout, {name} ({la['manuscript']['pages']:.0f} pages), partial r controlling page size, demeaned by group")
        print(f"{'text':28s} {'fresh~par_tokens':>17s} {'fresh~line_chars':>17s}")
        for key, r in la.items():
            print(f"{key:28s} {r['fresh~par_tokens']:+17.2f} {r['fresh~line_chars']:+17.2f}")
    for name in ('bio', 'all_within_group'):
        dd = results['distance_decay'][name]
        print(f"\n== page-bag cosine by Path 1 distance, {name}: cross-bifolium d=1, d>=5, slope; same-bifolium by relation and distance")
        for key, r in dd.items():
            same = ' '.join(f"{k}:{v:.3f}" for k, v in r['same_by_relation'].items())
            print(f"{key:28s} cross d1 {r['cross_1']:.3f} d5+ {r['cross_5plus']:.3f} slope {r['cross_slope']:+.4f} | " + ' '.join(f"{k}:{v:.3f}" for k, v in r['cross_by_distance'].items()))
            print(f"{'':28s} same bifolium: {same}")
        print('   same-bifolium pair counts:', dd['manuscript']['same_n'])


if __name__ == '__main__':
    main()
