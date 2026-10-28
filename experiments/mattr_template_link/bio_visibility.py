"""T11. Visibility inside Bio only. The pooled same-face/flip test (section 3) was dominated by Herbal.
Within Bio's five bifolia: cross-page re-use of the previous page's words after a co-visible (inner-face)
transition, an outer-face transition, a flip and a cross-sheet transition. Three statistics per transition:
  cross_rate : exact repeats at lags 1-50 across the boundary, per 1,000 pairs (end of previous page)
  penalty    : cross_rate / within-page rate at the same lags
  anywhere   : share of the page's first 50 tokens whose form occurs anywhere on the previous page
             (a visible page offers all its words, not only its last line)
Permutation test: class labels shuffled within bifolium. The generators are face-blind: their inner/flip
spread is the noise level for five bifolia. Also bag sharing by physical relation within Bio bifolia, and
the words carried across the two strongest boundaries.
"""
from collections import Counter, defaultdict
import json
import sys

import numpy as np

sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
import data as D
from visibility import ids_of, pair_stats

rng = np.random.default_rng(83)
BIO = '4a'


def face_class(ms, t):
    pa = ms['pages'][t['index'] - 1]; pb = ms['pages'][t['index']]
    if t['cls'] == 'same-face':
        return 'inner face' if pa['face'] == 'inner' else 'outer face'
    return t['cls']


def transition_rows(ms, tok):
    per_tr, per_within = pair_stats(tok, max_lag=50)
    words = np.array(tok['words'], dtype=object); page = tok['page']
    bags = {p: set(words[page == p].tolist()) for p in range(int(page.max()) + 1)}
    rows = []
    for t in D.transitions(ms):
        if t['group'] != BIO:
            continue
        p = t['index']
        c = per_tr[p][1:51].sum(axis=0); w = per_within[p][1:51].sum(axis=0)
        first = words[page == p][:50]
        rows.append(dict(cur=t['cur'], prev=t['prev'], node=t['node'], cls=face_class(ms, t), cross_rate=1000 * c[0] / c[1],
                         penalty=(c[0] / c[1]) / (w[0] / w[1]), anywhere=float(np.mean([x in bags[p - 1] for x in first]))))
    return rows


def class_table(rows, stat):
    return {cls: dict(n=len(v), mean=float(np.mean(v)), values=[round(float(x), 2) for x in v])
            for cls, v in ((c, [r[stat] for r in rows if r['cls'] == c]) for c in ('inner face', 'outer face', 'flip', 'cross-sheet')) if v}


def perm_test(rows, stat, a=('inner face',), b=('flip', 'outer face', 'cross-sheet'), reps=20000):
    """Mean(a) - mean(b); labels permuted within bifolium."""
    by = defaultdict(list)
    for r in rows:
        by[r['node']].append(r)
    def diff(rs):
        va = [r[stat] for r in rs if r['_cls'] in a]; vb = [r[stat] for r in rs if r['_cls'] in b]
        return np.mean(va) - np.mean(vb)
    for r in rows:
        r['_cls'] = r['cls']
    obs = diff(rows); count = 0
    for _ in range(reps):
        for node, rs in by.items():
            labels = [r['cls'] for r in rs]; rng.shuffle(labels)
            for r, l in zip(rs, labels):
                r['_cls'] = l
        if abs(diff(rows)) >= abs(obs) - 1e-12:
            count += 1
    for r in rows:
        r['_cls'] = r['cls']
    return dict(diff=float(obs), p_two_sided=(count + 1) / (reps + 1))


def sharing(ms, tok):
    words = np.array(tok['words'], dtype=object); page = tok['page']
    pages = {p['index']: p for p in ms['pages']}
    out = defaultdict(list)
    for node in [n for n in ms['nodes'] if n['group'] == BIO]:
        idx = [p['index'] for p in ms['pages'] if p['node'] == node['id']]
        for i, a in enumerate(idx):
            for b in idx[i + 1:]:
                pa, pb = pages[a], pages[b]
                rel = 'same leaf' if pa['leaf'] == pb['leaf'] else ('inner face' if pa['face'] == pb['face'] == 'inner' else ('outer face' if pa['face'] == pb['face'] else 'diagonal'))
                wa = words[page == a]; wb = words[page == b]; sb = set(wb.tolist()); sa = set(wa.tolist())
                out[rel].append(0.5 * (np.mean([x in sb for x in wa]) + np.mean([x in sa for x in wb])))
    return {k: dict(n=len(v), token_share=float(np.mean(v))) for k, v in out.items()}


def carried_words(ms, tok, cur, prev, max_lag=50):
    ids = tok['words']; page = tok['page']
    pi = {p['folio']: p['index'] for p in ms['pages']}
    c, pr = pi[cur], pi[prev]
    i_cur = np.where(page == c)[0]; i_prev = np.where(page == pr)[0]
    start = i_cur[0]
    cnt = Counter()
    for i in i_cur[:max_lag]:
        for d in range(1, max_lag + 1):
            j = i - d
            if j < start and j >= i_prev[0] and ids[i] == ids[j]:
                cnt[ids[i]] += 1
    return cnt.most_common(8)


def main():
    ms = D.manuscript()
    texts = {'manuscript': [[L['words'] for L in ms['lines']]]}
    for key, (label, srcs) in D.STREAMS.items():
        texts[key] = [D.read_stream(s) for s in srcs]
    res = {}
    for key, variants in texts.items():
        per = []
        for lines in variants:
            tok = D.tokenize(ms, lines); rows = transition_rows(ms, tok)
            per.append(dict(rows=rows, tables={s: class_table(rows, s) for s in ('cross_rate', 'penalty', 'anywhere')},
                            tests={s: perm_test(rows, s) for s in ('cross_rate', 'penalty', 'anywhere')},
                            tests_same_face_vs_flip={s: perm_test(rows, s, a=('inner face', 'outer face'), b=('flip',)) for s in ('cross_rate', 'penalty', 'anywhere')},
                            sharing=sharing(ms, tok)))
        res[key] = per
    ms_tok = D.tokenize(ms)
    res['carried'] = {f'{c}<-{p}': carried_words(ms, ms_tok, c, p) for c, p in (('f83r', 'f76v'), ('f82r', 'f77v'), ('f80r', 'f79v'), ('f81r', 'f78v'), ('f84r', 'f75v'))}
    json.dump(res, open(D.HERE / 'bio_visibility.json', 'w', encoding='utf-8'), indent=1, default=float)

    print('== manuscript, Bio transitions')
    for r in res['manuscript'][0]['rows']:
        print(f"  {r['cur']:5s} <- {r['prev']:5s} {r['cls']:12s} cross {r['cross_rate']:5.1f}/1000  penalty {r['penalty']:.2f}  anywhere {r['anywhere']:.2f}")
    for stat in ('cross_rate', 'penalty', 'anywhere'):
        print(f"\n== {stat}: class means (inner face / outer face / flip / cross-sheet), inner-face minus rest with permutation p, same-face minus flip with p")
        for key, per in res.items():
            if key == 'carried':
                continue
            means = []; d1 = []; p1 = []; d2 = []; p2 = []
            for x in per:
                t = x['tables'][stat]
                means.append([t.get(c, {}).get('mean', np.nan) for c in ('inner face', 'outer face', 'flip', 'cross-sheet')])
                d1.append(x['tests'][stat]['diff']); p1.append(x['tests'][stat]['p_two_sided'])
                d2.append(x['tests_same_face_vs_flip'][stat]['diff']); p2.append(x['tests_same_face_vs_flip'][stat]['p_two_sided'])
            m = np.nanmean(means, axis=0)
            fmt = '{:6.2f}' if stat != 'cross_rate' else '{:6.1f}'
            print(f"  {key:14s} " + ' '.join(fmt.format(v) for v in m) + f"   inner-rest {np.mean(d1):+.2f} (p {np.mean(p1):.2f}; per seed " + ' '.join(f"{p:.2f}" for p in p1) + f")   same-face-flip {np.mean(d2):+.2f} (p {np.mean(p2):.2f})")
    print('\n== bag sharing within Bio bifolia by relation (token share with a form on the other page)')
    for key, per in res.items():
        if key == 'carried':
            continue
        sh = {rel: np.mean([x['sharing'][rel]['token_share'] for x in per]) for rel in per[0]['sharing']}
        print(f"  {key:14s} " + '  '.join(f"{rel} {v:.3f}" for rel, v in sh.items()))
    print('\n== words carried across the boundary (manuscript, lags 1-50)')
    for k, v in res['carried'].items():
        print(f"  {k}: {v}")


if __name__ == '__main__':
    main()
