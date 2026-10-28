"""Small supplementary statistics: inner- vs outer-face sharing, cross-boundary repeat counts at the
shortest lags, and the persistence (autocorrelation) of the fresh indicator inside bifolia."""
from collections import defaultdict
import json
import re
import sys
import unicodedata

import numpy as np

sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
import data as D
from decompose import REFS, ref_words

rng = np.random.default_rng(3)


def inner_outer(pairs):
    by = defaultdict(dict)
    for r in pairs:
        if r['relation'].startswith('same-face'):
            by[r['node']][r['relation']] = r['token_share']
    d = np.array([v['same-face-inner'] - v['same-face-outer'] for v in by.values() if len(v) == 2])
    boot = [rng.choice(d, len(d)).mean() for _ in range(5000)]
    return dict(n=len(d), mean=float(d.mean()), ci95=[float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))], positive=int((d > 0).sum()))


def autocorr(fresh, unit, lags):
    """Autocorrelation of the fresh indicator after removing unit (bifolium) means."""
    x = fresh.astype(float).copy()
    for u in np.unique(unit):
        m = unit == u; x[m] -= x[m].mean()
    out = {}
    for k in lags:
        a = x[:-k]; b = x[k:]; same = unit[:-k] == unit[k:]
        out[k] = float(np.corrcoef(a[same], b[same])[0, 1])
    return out


def main():
    ms = D.manuscript()
    v = json.load(open(D.HERE / 'visibility.json', encoding='utf-8'))
    res = dict(inner_minus_outer_manuscript=inner_outer(v['manuscript_sharing_pairs']))
    # raw counts of cross-boundary repeats at lags 1-10 by class (manuscript)
    tok = D.tokenize(ms)
    ids = np.array([hash(w) for w in tok['words']]); page = tok['page']
    trans = {t['index']: t['cls'] for t in D.transitions(ms)}
    counts = defaultdict(lambda: [0, 0])
    for d in range(1, 11):
        y = ids[d:] == ids[:-d]; prev = page[d:] == page[:-d] + 1
        for p in np.unique(page[d:][prev]):
            m = prev & (page[d:] == p)
            counts[trans[int(p)]][0] += int(y[m].sum()); counts[trans[int(p)]][1] += int(m.sum())
    res['cross_lag1_10_counts_manuscript'] = {k: dict(repeats=a, pairs=b, rate=a / b) for k, (a, b) in counts.items()}
    # persistence
    lags = [1, 2, 5, 10, 25, 50, 100, 150, 200]
    node_index = {n['id']: i for i, n in enumerate(ms['nodes'])}
    unit = np.array([node_index[ms['lines'][l]['node']] for l in tok['line']])
    pers = {}
    pers['manuscript'] = autocorr(D.fresh_indicator(tok['words']), unit, lags)
    for key, (label, srcs) in D.STREAMS.items():
        acc = []
        for s in srcs:
            t = D.tokenize(ms, D.read_stream(s)); u = np.array([node_index[ms['lines'][l]['node']] for l in t['line']])
            acc.append(autocorr(D.fresh_indicator(t['words']), u, lags))
        pers[key] = {k: float(np.mean([a[k] for a in acc])) for k in lags}
    sizes = [n['N'] for n in ms['nodes']]
    for key in ('la_galen_simplicium', 'la_dioscorides_longob', 'la_rhazes_almansor', 'de_gart_augsburg1487', 'la_vulgate_train'):
        words = ref_words(REFS[key]); total = sum(sizes)
        start = int(rng.integers(0, len(words) - total)); words = words[start:start + total]
        u = np.concatenate([np.full(sz, i) for i, sz in enumerate(sizes)])
        pers[key] = autocorr(D.fresh_indicator(words), u, lags)
    res['persistence'] = pers
    (D.HERE / 'extras.json').write_text(json.dumps(res, indent=1), encoding='utf-8')
    print('inner minus outer face sharing (manuscript):', res['inner_minus_outer_manuscript'])
    print('cross-boundary repeats, lags 1-10 (manuscript):', res['cross_lag1_10_counts_manuscript'])
    print('\nautocorrelation of the fresh indicator within bifolia (unit means removed):')
    print(f"{'':24s}" + ' '.join(f"{k:>7d}" for k in lags))
    for key, a in pers.items():
        print(f"{key:24s}" + ' '.join(f"{a[k]:+7.3f}" for k in lags))


if __name__ == '__main__':
    main()
