"""T12. What the transparent Herbal page boundary is made of (27 October, correction).

Section 6 first described Herbal's transparent boundary as re-use of a 'shared Herbal register', with
'plant-specific' words among the forms that occur once. That attributed content to words whose content is
unknown (no Herbal form is a confirmed plant word) and treated Herbal as one vocabulary. Herbal spans seven
Golf 2.1 groups on both sides of the A/B switch, and the gradient model fits a continuous movement of word
composition along the bifolium order. This script measures what consecutive Herbal pages share and how far
that sharing reaches along Path 1.
  (1) census: Herbal pages by group; Herbal->Herbal transitions by relation (same bifolium / other bifolium,
      same group / other bifolium, other group)
  (2) page-boundary penalty (cross/within, lags 1-50) for each relation
  (3) page-bag cosine between Herbal pages (>= 60 tokens) by relation: same bifolium; same group at bifolium
      rank distance 1, 2-4, 5+; adjacent groups; two or more groups apart on the same side; across the A/B switch
  (4) cross-bifolium cosine against bifolium rank distance inside Herbal A (1a, 1b, 1.5a, 2a), beside the
      cosine of the gradient model's fitted word distributions for the same bifolium pairs
  (5) the forms carried across Herbal boundaries: share of cross-boundary repeats made by the 50 most frequent
      forms of the transition's own group, against the same share for within-page repeats
"""
from collections import Counter, defaultdict
import gzip
import json
import sys

import numpy as np

sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
import data as D
from decompose import REFS, ref_words
from timing import laid_in
from visibility import pair_stats

MIN_TOKENS = 60
GROUP_ORDER = ['1a', '1b', '1.5a', '2a', '5a', '6', '3b', '3a', '3c', '4c', '4a']
A_SIDE = {'1a', '1b', '1.5a', '2a'}
HERBAL_A = A_SIDE
DIST_BINS = [(1, 1), (2, 3), (4, 7), (8, 15), (16, 99)]
REL_KEYS = ['same bifolium', 'same group, d 1', 'same group, d 2-4', 'same group, d 5+', 'adjacent groups', 'two or more groups apart', 'across A/B']


def cos(a, b):
    dot = sum(v * b[w] for w, v in a.items() if w in b)
    return dot / np.sqrt(sum(v * v for v in a.values()) * sum(v * v for v in b.values()))


def bin_name(d):
    for lo, hi in DIST_BINS:
        if lo <= d <= hi:
            return str(lo) if lo == hi else f'{lo}-{hi}'
    return None


def relation_of(pa, pb, rank):
    if pa['node'] == pb['node']:
        return 'same bifolium'
    ga, gb = pa['group'], pb['group']
    if ga == gb:
        d = abs(rank[pa['node']] - rank[pb['node']])
        return 'same group, d 1' if d == 1 else ('same group, d 2-4' if d <= 4 else 'same group, d 5+')
    if (ga in A_SIDE) != (gb in A_SIDE):
        return 'across A/B'
    return 'adjacent groups' if abs(GROUP_ORDER.index(ga) - GROUP_ORDER.index(gb)) == 1 else 'two or more groups apart'


def herbal_transitions(ms):
    pages = ms['pages']
    return [t for t in D.transitions(ms) if pages[t['index']]['section'] == 'H' and pages[t['index'] - 1]['section'] == 'H']


def census(ms, rank):
    pages = ms['pages']
    H = [p for p in pages if p['section'] == 'H']
    trans = herbal_transitions(ms)
    rel = Counter(relation_of(pages[t['index'] - 1], pages[t['index']], rank) for t in trans)
    return dict(pages=len(H), groups=dict(Counter(p['group'] for p in H)), bifolia=len({p['node'] for p in H}),
                transitions=len(trans), transition_relations=dict(rel))


def coarse(rel):
    if rel == 'same bifolium':
        return rel
    return 'other bifolium, same group' if rel.startswith('same group') else 'other bifolium, other group'


def boundary_by_relation(ms, tok, rank, max_lag=50):
    pages = ms['pages']
    per_tr, per_within = pair_stats(tok, max_lag=max_lag)
    acc = defaultdict(lambda: np.zeros((2, 2)))
    for t in herbal_transitions(ms):
        p = t['index']
        key = coarse(relation_of(pages[p - 1], pages[p], rank))
        for k in (key, 'all'):
            acc[k][0] += per_tr[p][1:max_lag + 1].sum(axis=0)
            acc[k][1] += per_within[p][1:max_lag + 1].sum(axis=0)
    out = {}
    for k, a in acc.items():
        cross = a[0][0] / a[0][1] if a[0][1] else np.nan
        within = a[1][0] / a[1][1] if a[1][1] else np.nan
        out[k] = dict(cross_rate=float(1000 * cross), within_rate=float(1000 * within), penalty=float(cross / within) if within else np.nan)
    return out


def page_bags(ms, tok):
    words = np.array(tok['words'], dtype=object)
    page = tok['page']
    bags = {}
    for p in ms['pages']:
        if p['section'] != 'H':
            continue
        m = page == p['index']
        if m.sum() >= MIN_TOKENS:
            bags[p['index']] = Counter(words[m].tolist())
    return bags


def similarity_by_relation(ms, bags, rank):
    pages = {p['index']: p for p in ms['pages']}
    out = defaultdict(list)
    ps = sorted(bags)
    for i, a in enumerate(ps):
        for b in ps[i + 1:]:
            out[relation_of(pages[a], pages[b], rank)].append(cos(bags[a], bags[b]))
    return {k: dict(n=len(v), cosine=float(np.mean(v))) for k, v in out.items()}


def spearman(x, y):
    rx = np.argsort(np.argsort(x))
    ry = np.argsort(np.argsort(y))
    return float(np.corrcoef(rx, ry)[0, 1])


def decay_herbal_a(ms, bags, rank):
    """Cross-bifolium cosine by bifolium rank distance, pages of the Herbal A groups only."""
    pages = {p['index']: p for p in ms['pages']}
    ps = sorted(p for p in bags if pages[p]['group'] in HERBAL_A)
    by_bin = defaultdict(list)
    xs = []
    ys = []
    for i, a in enumerate(ps):
        for b in ps[i + 1:]:
            if pages[a]['node'] == pages[b]['node']:
                continue
            d = abs(rank[pages[a]['node']] - rank[pages[b]['node']])
            c = cos(bags[a], bags[b])
            xs.append(d)
            ys.append(c)
            by_bin[bin_name(d)].append(c)
    return dict(by_distance={k: dict(n=len(v), cosine=float(np.mean(v))) for k, v in by_bin.items()},
                spearman=spearman(xs, ys), pairs=len(xs))


def fitted_gradient_decay(ms, asset, rank):
    """Cosine of the gradient model's fitted word distributions (word_gradual columns) between Herbal A bifolia
    by rank distance, and the fitted total-variation movement per step along the path, by group change."""
    W = np.array(asset['word_gradual'], dtype=float)  # 7,180 x 50, columns sum to 10,000
    nodes = ms['nodes']
    herbal_ids = {p['node'] for p in ms['pages'] if p['section'] == 'H'}
    herbal_nodes = [n for n in nodes if n['group'] in HERBAL_A and n['id'] in herbal_ids]
    col = {n['id']: i for i, n in enumerate(nodes)}
    by_bin = defaultdict(list)
    for i, a in enumerate(herbal_nodes):
        for b in herbal_nodes[i + 1:]:
            d = abs(rank[a['id']] - rank[b['id']])
            u = W[:, col[a['id']]]
            v = W[:, col[b['id']]]
            by_bin[bin_name(d)].append(float(u @ v / np.sqrt((u @ u) * (v @ v))))
    movement = asset['chronology']['movement']
    steps = []
    for i in range(len(nodes) - 1):
        a, b = nodes[i], nodes[i + 1]
        steps.append(dict(step=f"{a['id']}->{b['id']}", from_group=a['group'], to_group=b['group'], movement=float(movement[i])))
    within_a = [s['movement'] for s in steps if s['from_group'] == s['to_group'] and s['from_group'] in HERBAL_A]
    change_a = [s['movement'] for s in steps if s['from_group'] != s['to_group'] and s['from_group'] in HERBAL_A and s['to_group'] in HERBAL_A]
    into_b = [s['movement'] for s in steps if s['from_group'] in ('5a', '6') and s['to_group'] == '3b']
    return dict(by_distance={k: dict(n=len(v), cosine=float(np.mean(v))) for k, v in by_bin.items()},
                movement_within_group_steps_herbal_a=dict(n=len(within_a), mean=float(np.mean(within_a)), max=float(np.max(within_a))),
                movement_group_change_steps_herbal_a=dict(n=len(change_a), values=change_a),
                movement_into_b=into_b, steps=steps)


def carried_forms(ms, tok, max_lag=50, top=50):
    """Cross-boundary repeats at Herbal boundaries: which forms, and the share made by the transition group's
    50 most frequent Herbal forms; the same share for within-page repeats in Herbal."""
    words = tok['words']
    page = tok['page']
    pages = ms['pages']
    warr = np.array(words, dtype=object)
    group_of_tok = np.array([pages[p]['group'] for p in page], dtype=object)
    sec_of_tok = np.array([pages[p]['section'] for p in page], dtype=object)
    top_forms = {}
    for g in set(group_of_tok.tolist()):
        m = (group_of_tok == g) & (sec_of_tok == 'H')
        top_forms[g] = {w for w, _ in Counter(warr[m].tolist()).most_common(top)}
    cross = Counter()
    cross_top = cross_n = within_top = within_n = 0
    for i, w in enumerate(words):
        p = int(page[i])
        if pages[p]['section'] != 'H':
            continue
        g = pages[p]['group']
        for d in range(1, max_lag + 1):
            j = i - d
            if j < 0 or words[j] != w:
                continue
            if page[j] == p:
                within_n += 1
                within_top += w in top_forms[g]
            elif page[j] == p - 1 and pages[p - 1]['section'] == 'H':
                cross_n += 1
                cross_top += w in top_forms[g]
                cross[w] += 1
    return dict(cross_repeats=cross_n, cross_share_in_group_top50=cross_top / cross_n if cross_n else np.nan,
                within_repeats=within_n, within_share_in_group_top50=within_top / within_n if within_n else np.nan,
                top_carried=cross.most_common(12))


def mean_nested(dicts):
    if isinstance(dicts[0], dict):
        return {k: mean_nested([d[k] for d in dicts if k in d]) for k in dicts[0]}
    return float(np.nanmean(dicts))


def main():
    ms = D.manuscript()
    rank = {n['id']: n['rank'] for n in ms['nodes']}
    asset = json.load(gzip.open(D.ASSET, 'rt', encoding='utf-8'))
    texts = {'manuscript': [[L['words'] for L in ms['lines']]]}
    for key, (label, srcs) in D.STREAMS.items():
        texts[key] = [D.read_stream(s) for s in srcs[:3]]
    page_sizes = [sum(len(ms['lines'][l]['words']) for l in range(p['start_line'], p['end_line'])) for p in ms['pages']]
    for key in ('la_galen_simplicium', 'la_dioscorides_longob', 'la_rhazes_almansor', 'la_hildegard_physica', 'de_gart_augsburg1487'):
        words = ref_words(REFS[key])
        if len(words) >= sum(page_sizes) + 10:
            texts['ref_' + key] = [laid_in(ms, words, page_sizes)]

    res = dict(census=census(ms, rank), boundary={}, similarity={}, decay_herbal_a={},
               fitted=fitted_gradient_decay(ms, asset, rank), carried={})
    for key, variants in texts.items():
        toks = [D.tokenize(ms, lines) for lines in variants]
        res['boundary'][key] = mean_nested([boundary_by_relation(ms, t, rank) for t in toks])
        bags = [page_bags(ms, t) for t in toks]
        res['similarity'][key] = mean_nested([similarity_by_relation(ms, b, rank) for b in bags])
        res['decay_herbal_a'][key] = mean_nested([decay_herbal_a(ms, b, rank) for b in bags])
        cf = [carried_forms(ms, t) for t in toks]
        res['carried'][key] = {k: float(np.mean([c[k] for c in cf])) for k in ('cross_repeats', 'cross_share_in_group_top50', 'within_repeats', 'within_share_in_group_top50')}
        if key == 'manuscript':
            res['carried'][key]['top_carried'] = cf[0]['top_carried']
    (D.HERE / 'herbal_boundary.json').write_text(json.dumps(res, indent=1, default=float), encoding='utf-8')

    c = res['census']
    print(f"== Herbal: {c['pages']} pages in {c['bifolia']} bifolia; groups {c['groups']}")
    print(f"   Herbal->Herbal transitions {c['transitions']}: {c['transition_relations']}")
    print('\n== page-boundary penalty (cross/within, lags 1-50) by relation of the two pages')
    keys = ['all', 'same bifolium', 'other bifolium, same group', 'other bifolium, other group']
    print(f"  {'text':26s} " + ' '.join(f"{k:>28s}" for k in keys))
    for key, r in res['boundary'].items():
        print(f"  {key:26s} " + ' '.join(f"{r[k]['penalty']:28.2f}" if k in r else f"{'':>28s}" for k in keys))
    print('  manuscript cross repeats per 1,000 pairs: ' + ', '.join(f"{k} {res['boundary']['manuscript'][k]['cross_rate']:.1f}" for k in keys if k in res['boundary']['manuscript']))
    print(f"\n== page-bag cosine by relation, Herbal pages of {MIN_TOKENS}+ tokens (n pairs from the manuscript)")
    print(f"  {'text':26s} " + ' '.join(f"{k:>24s}" for k in REL_KEYS))
    print(f"  {'(pairs)':26s} " + ' '.join(f"{res['similarity']['manuscript'].get(k, {}).get('n', 0):24.0f}" for k in REL_KEYS))
    for key, r in res['similarity'].items():
        print(f"  {key:26s} " + ' '.join(f"{r[k]['cosine']:24.3f}" if k in r else f"{'':>24s}" for k in REL_KEYS))
    print('\n== Herbal A, cross-bifolium cosine by bifolium rank distance: observed page bags, and the fitted gradient (word_gradual columns, bifolium level)')
    bins = [str(lo) if lo == hi else f'{lo}-{hi}' for lo, hi in DIST_BINS]
    print(f"  {'text':26s} " + ' '.join(f"{b:>8s}" for b in bins) + '   spearman(d, cos)')
    for key, r in res['decay_herbal_a'].items():
        print(f"  {key:26s} " + ' '.join(f"{r['by_distance'][b]['cosine']:8.3f}" if b in r['by_distance'] else f"{'':>8s}" for b in bins) + f"   {r['spearman']:+.2f}  (pairs {r['pairs']:.0f})")
    f = res['fitted']
    print(f"  {'fitted gradient':26s} " + ' '.join(f"{f['by_distance'][b]['cosine']:8.3f}" if b in f['by_distance'] else f"{'':>8s}" for b in bins) + '   (bifolium pairs ' + ', '.join(str(f['by_distance'][b]['n']) for b in bins if b in f['by_distance']) + ')')
    mw = f['movement_within_group_steps_herbal_a']
    print(f"  fitted movement per step inside Herbal A: {mw['n']} within-group steps mean {mw['mean']:.4f} max {mw['max']:.4f}; group-change steps "
          + ', '.join(f'{v:.4f}' for v in f['movement_group_change_steps_herbal_a']['values']) + '; into B ' + ', '.join(f'{v:.4f}' for v in f['movement_into_b']))
    print("\n== forms carried across Herbal boundaries (lags 1-50): share of cross-boundary repeats made by the group's 50 most frequent Herbal forms, and the same share for within-page repeats")
    for key, r in res['carried'].items():
        print(f"  {key:26s} cross {r['cross_repeats']:.0f} repeats, share {r['cross_share_in_group_top50']:.2f}; within {r['within_repeats']:.0f}, share {r['within_share_in_group_top50']:.2f}")
    print('  manuscript, most carried forms:', res['carried']['manuscript']['top_carried'])


if __name__ == '__main__':
    main()
