"""T2. Does a word on the previous page get re-used more when that page is physically visible?

On a flat bifolium sheet the two pages of one face are seen together; a page and the page on
the other side of the same leaf (or the other face of the sheet) are never seen together.
Path 1 steps through each bifolium page by page, so its page transitions split into
  same-face  : previous page on the same face of the same sheet (visible while writing)
  flip       : previous page on the other face of the same sheet (not visible)
  cross-sheet: previous page on another bifolium.
If the writer took word templates from the visible page, the first words of a page should
repeat the last words of the previous page more often after a same-face transition than
after a flip, at the same token lag. Memory, register and composition drift predict no
difference. Generated streams (which know nothing of faces) are the control for layout and
direction artefacts: for them same-face and flip must agree.

Second, order-free test: the six page pairs of a four-page bifolium are same-leaf (Ar-Av,
Br-Bv), same-face (Av-Br inner, Bv-Ar outer) or diagonal (Ar-Br, Av-Bv). Vocabulary sharing
by relation, within bifolium.
"""
from collections import defaultdict
import json
import sys

import numpy as np

sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
import data as D

rng = np.random.default_rng(20261026)
LAGS = 50
BANDS = [(1, 10), (11, 25), (26, 50), (51, 100)]


def ids_of(words):
    index = {}
    return np.array([index.setdefault(w, len(index)) for w in words])


def pair_stats(tok, max_lag=100):
    """Per current page and lag: [repeats, pairs] for pairs (i-d, i) inside the page and across from the previous page."""
    ids = ids_of(tok['words']); page = tok['page']; npages = int(page.max()) + 1
    within = np.zeros((npages, max_lag + 1, 2)); cross = np.zeros((npages, max_lag + 1, 2))
    for d in range(1, max_lag + 1):
        y = (ids[d:] == ids[:-d]).astype(float)
        cur = page[d:]; src = page[:-d]
        same = cur == src; prev = cur == src + 1
        within[:, d, 0] = np.bincount(cur[same], weights=y[same], minlength=npages)
        within[:, d, 1] = np.bincount(cur[same], minlength=npages)
        cross[:, d, 0] = np.bincount(cur[prev], weights=y[prev], minlength=npages)
        cross[:, d, 1] = np.bincount(cur[prev], minlength=npages)
    per_transition = {p: cross[p] for p in range(1, npages)}
    per_page_within = {p: within[p] for p in range(npages)}
    return per_transition, per_page_within


def rate(arr, lo, hi):
    s = arr[lo:hi + 1].sum(axis=0)
    return s[0] / s[1] if s[1] else np.nan


def summarize(tok, ms, label):
    per_tr, per_within = pair_stats(tok)
    trans = {t['index']: t for t in D.transitions(ms)}
    rows = []
    for p, arr in per_tr.items():
        t = trans[p]
        row = dict(page=p, cur=t['cur'], prev=t['prev'], cls=t['cls'], node=t['node'], group=t['group'],
                   direction=t['direction'])
        for lo, hi in BANDS:
            row[f'cross_{lo}_{hi}'] = rate(arr, lo, hi)
            row[f'within_{lo}_{hi}'] = rate(per_within[p], lo, hi)   # same lags, pairs inside the current page
            row[f'within_prev_{lo}_{hi}'] = rate(per_within[p - 1], lo, hi)
        row['cross_1_50'] = rate(arr, 1, LAGS); row['within_1_50'] = rate(per_within[p], 1, LAGS)
        row['within_prev_1_50'] = rate(per_within[p - 1], 1, LAGS)
        row['pairs_1_50'] = int(arr[1:LAGS + 1, 1].sum())
        rows.append(row)
    return rows


def paired_test(rows, stat, a='same-face', b='flip', reps=3000):
    """Within-bifolium difference of mean stat between classes a and b; bootstrap over bifolia and a
    within-bifolium label permutation test."""
    by = defaultdict(lambda: defaultdict(list))
    for r in rows:
        if r['cls'] in (a, b) and np.isfinite(r[stat]):
            by[r['node']][r['cls']].append(r[stat])
    nodes = [n for n in by if by[n][a] and by[n][b]]
    diffs = np.array([np.mean(by[n][a]) - np.mean(by[n][b]) for n in nodes])
    if not len(diffs):
        return None
    boot = np.array([rng.choice(diffs, len(diffs)).mean() for _ in range(5000)])
    # permutation within bifolium: reassign which transitions are called a / b
    obs = diffs.mean(); count = 0
    pooled = [np.array(by[n][a] + by[n][b]) for n in nodes]; na = [len(by[n][a]) for n in nodes]
    for _ in range(reps):
        s = 0.0
        for vals, k in zip(pooled, na):
            perm = rng.permutation(vals)
            s += perm[:k].mean() - perm[k:].mean()
        if abs(s / len(nodes)) >= abs(obs) - 1e-15:
            count += 1
    return dict(n_bifolia=len(nodes), mean_diff=float(obs), ci95=[float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))],
                perm_p_two_sided=(count + 1) / (reps + 1), positive_bifolia=int((diffs > 0).sum()), negative_bifolia=int((diffs < 0).sum()),
                mean_a=float(np.mean([np.mean(by[n][a]) for n in nodes])), mean_b=float(np.mean([np.mean(by[n][b]) for n in nodes])))


def class_means(rows, stat):
    out = {}
    for cls in ('same-face', 'flip', 'cross-sheet'):
        v = [r[stat] for r in rows if r['cls'] == cls and np.isfinite(r[stat])]
        out[cls] = dict(mean=float(np.mean(v)), n=len(v), se=float(np.std(v, ddof=1) / np.sqrt(len(v))))
    return out


# ---------- order-free bag sharing within bifolia ----------
def sharing(ms, tok):
    ids = ids_of(tok['words'])
    pages_tokens = defaultdict(list)
    for i, p in enumerate(tok['page']):
        pages_tokens[int(p)].append(ids[i])
    pages_tokens = {p: np.array(v) for p, v in pages_tokens.items()}
    by_node = defaultdict(list)
    for pg in ms['pages']:
        by_node[pg['node']].append(pg)
    rows = []
    for node, pgs in by_node.items():
        if len(pgs) != 4 or any(p['panel'] for p in pgs):
            continue
        rel = {}
        for x in range(4):
            for y in range(x + 1, 4):
                a, b = pgs[x], pgs[y]
                if a['leaf'] == b['leaf']:
                    r = 'same-leaf'
                elif a['face'] == b['face']:
                    r = 'same-face-' + a['face']
                else:
                    r = 'diagonal'
                ta, tb = pages_tokens[a['index']], pages_tokens[b['index']]
                sa, sb = set(ta.tolist()), set(tb.tolist())
                share = (np.isin(ta, list(sb)).mean() + np.isin(tb, list(sa)).mean()) / 2
                jacc = len(sa & sb) / len(sa | sb)
                rows.append(dict(node=node, group=pgs[0]['group'], a=a['folio'], b=b['folio'], relation=r,
                                 token_share=float(share), jaccard=float(jacc), size=int(len(ta) * len(tb)),
                                 path_adjacent=abs(a['index'] - b['index']) == 1))
    return rows


def sharing_tests(rows, stat='token_share'):
    by = defaultdict(lambda: defaultdict(list))
    for r in rows:
        key = 'same-face' if r['relation'].startswith('same-face') else r['relation']
        by[r['node']][key].append(r[stat])
    out = {}
    for a, b in (('same-face', 'diagonal'), ('same-face', 'same-leaf'), ('same-leaf', 'diagonal')):
        nodes = [n for n in by if by[n][a] and by[n][b]]
        diffs = np.array([np.mean(by[n][a]) - np.mean(by[n][b]) for n in nodes])
        boot = np.array([rng.choice(diffs, len(diffs)).mean() for _ in range(5000)])
        out[f'{a} minus {b}'] = dict(n_bifolia=len(nodes), mean_diff=float(diffs.mean()),
                                     ci95=[float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))],
                                     positive=int((diffs > 0).sum()), negative=int((diffs < 0).sum()),
                                     sign_p=float(sign_test((diffs > 0).sum(), (diffs != 0).sum())))
    # inner vs outer face pairs
    inner = [r[stat] for r in rows if r['relation'] == 'same-face-inner']; outer = [r[stat] for r in rows if r['relation'] == 'same-face-outer']
    out['inner_face_mean'] = float(np.mean(inner)); out['outer_face_mean'] = float(np.mean(outer))
    out['diagonal_mean'] = float(np.mean([r[stat] for r in rows if r['relation'] == 'diagonal']))
    out['same_leaf_mean'] = float(np.mean([r[stat] for r in rows if r['relation'] == 'same-leaf']))
    return out


def sign_test(k, n):
    from math import comb
    k = min(k, n - k)
    return min(1.0, 2 * sum(comb(n, j) for j in range(0, k + 1)) / 2 ** n) if n else float('nan')


def main():
    ms = D.manuscript()
    results = {}
    texts = {'manuscript': [None]}
    for key, (label, srcs) in D.STREAMS.items():
        texts[key] = srcs
    for key, srcs in texts.items():
        all_rows = []; all_share = []
        for s in srcs:
            tok = D.tokenize(ms, None if s is None else D.read_stream(s))
            rows = summarize(tok, ms, key)
            for r in rows:
                r['seed_source'] = str(s) if s else 'manuscript'
            all_rows += rows
            all_share += sharing(ms, tok)
        res = dict(label=key if key == 'manuscript' else D.STREAMS[key][0], seeds=len(srcs))
        for stat in ('cross_1_50', 'cross_1_10', 'cross_11_25', 'cross_26_50', 'cross_51_100', 'within_1_50'):
            res[stat] = dict(by_class=class_means(all_rows, stat), paired_same_face_vs_flip=paired_test(all_rows, stat),
                             paired_flip_vs_cross_sheet=paired_test(all_rows, stat, 'flip', 'cross-sheet'))
        # cross/within ratio per transition (boundary penalty)
        for r in all_rows:
            r['penalty'] = r['cross_1_50'] / r['within_1_50'] if r['within_1_50'] else np.nan
            r['penalty_prev'] = r['cross_1_50'] / r['within_prev_1_50'] if r['within_prev_1_50'] else np.nan
        res['penalty'] = dict(by_class=class_means(all_rows, 'penalty'), paired_same_face_vs_flip=paired_test(all_rows, 'penalty'))
        res['penalty_prev'] = dict(by_class=class_means(all_rows, 'penalty_prev'), paired_same_face_vs_flip=paired_test(all_rows, 'penalty_prev'))
        # by group
        res['by_group'] = {}
        for g in sorted({r['group'] for r in all_rows}):
            sub = [r for r in all_rows if r['group'] == g]
            res['by_group'][g] = {cls: class_means(sub, 'cross_1_50')[cls] for cls in ('same-face', 'flip', 'cross-sheet') if any(r['cls'] == cls for r in sub)}
        res['sharing'] = dict(token_share=sharing_tests(all_share, 'token_share'), jaccard=sharing_tests(all_share, 'jaccard'))
        results[key] = res
        if key == 'manuscript':
            results['manuscript_transitions'] = all_rows
            results['manuscript_sharing_pairs'] = all_share
        m = res['cross_1_50']
        print(f"{key:14s} cross-page repeat rate (lags 1-50): same-face {m['by_class']['same-face']['mean']:.4f}  flip {m['by_class']['flip']['mean']:.4f}  "
              f"cross-sheet {m['by_class']['cross-sheet']['mean']:.4f} | within-page {res['within_1_50']['by_class']['flip']['mean']:.4f} | "
              f"paired same-face minus flip {m['paired_same_face_vs_flip']['mean_diff']:+.4f} CI {m['paired_same_face_vs_flip']['ci95']} p={m['paired_same_face_vs_flip']['perm_p_two_sided']:.3f} "
              f"({m['paired_same_face_vs_flip']['positive_bifolia']}+/{m['paired_same_face_vs_flip']['negative_bifolia']}-)")
        sh = res['sharing']['token_share']
        print(f"{'':14s} bag sharing: same-face {sh['same-face minus diagonal']['mean_a'] if 'mean_a' in sh['same-face minus diagonal'] else ''} inner {sh['inner_face_mean']:.4f} outer {sh['outer_face_mean']:.4f} same-leaf {sh['same_leaf_mean']:.4f} diagonal {sh['diagonal_mean']:.4f}; "
              f"same-face minus diagonal {sh['same-face minus diagonal']['mean_diff']:+.4f} CI {sh['same-face minus diagonal']['ci95']} ({sh['same-face minus diagonal']['positive']}+/{sh['same-face minus diagonal']['negative']}-) ; "
              f"same-face minus same-leaf {sh['same-face minus same-leaf']['mean_diff']:+.4f} CI {sh['same-face minus same-leaf']['ci95']}")
    (D.HERE / 'visibility.json').write_text(json.dumps(results, indent=1, default=float), encoding='utf-8')


if __name__ == '__main__':
    main()
