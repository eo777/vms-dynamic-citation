"""T3b. At what scale does each text lose local diversity? An exact decomposition by scale.

For a group of pages, with hypergeometric (shuffled-bag) expectations of the distinct share of a
random 100-token subset:
  G = expectation from the whole group's bag
  B = token-weighted mean of the bifolium bags' expectations
  P = token-weighted mean of the page bags' expectations
  A = token-weighted mean of the pages' actual MATTR100 (windows wholly inside the page)
Under exchangeability of tokens across the pages of a bifolium (or bifolia of a group) the
expectations agree exactly, whatever the page sizes, so
  G - A = (G - B) + (B - P) + (P - A)
splits the group's local-diversity deficit into concentration at the bifolium level, at the
page level, and clustering inside pages. Manuscript and every stream (seed means).
"""
from collections import defaultdict
import json
import sys

import numpy as np

sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
import data as D


def decompose(ms, lines):
    group_words = defaultdict(list); node_words = defaultdict(list); page_words = defaultdict(list)
    for L, ws in zip(ms['lines'], lines):
        group_words[L['group']] += ws; node_words[L['node']] += ws; page_words[L['page']] += ws
    out = {}
    for g in dict.fromkeys(n['group'] for n in ms['nodes']):
        nodes = [n for n in ms['nodes'] if n['group'] == g]
        pages = [p for p in ms['pages'] if p['group'] == g]
        G = D.bag_mattr(group_words[g])
        nw = np.array([len(node_words[n['id']]) for n in nodes], float)
        B = float(np.average([D.bag_mattr(node_words[n['id']]) for n in nodes], weights=nw))
        pw = np.array([len(page_words[p['index']]) for p in pages], float)
        P = float(np.average([D.bag_mattr(page_words[p['index']]) for p in pages], weights=pw))
        A = float(np.average([D.mattr(page_words[p['index']]) for p in pages], weights=pw))
        out[g] = dict(G=G, B=B, P=P, A=A, bifolium_level=G - B, page_level=B - P, within_page=P - A, total=G - A, tokens=int(pw.sum()))
    return out


def main():
    ms = D.manuscript()
    groups = list(dict.fromkeys(n['group'] for n in ms['nodes']))
    results = {}
    results['manuscript'] = decompose(ms, [L['words'] for L in ms['lines']])
    for key, (label, srcs) in D.STREAMS.items():
        per = [decompose(ms, D.read_stream(s)) for s in srcs]
        results[key] = {g: {k: float(np.mean([p[g][k] for p in per])) for k in per[0][g]} for g in groups}
    # natural-language references laid into the manuscript's page structure (same page, bifolium and group sizes)
    from decompose import REFS, ref_words
    rng = np.random.default_rng(11)
    page_sizes = [sum(len(ms['lines'][l]['words']) for l in range(p['start_line'], p['end_line'])) for p in ms['pages']]
    total = sum(page_sizes)
    refs = {}
    for key in ('la_galen_simplicium', 'la_dioscorides_longob', 'la_rhazes_almansor', 'la_hildegard_physica', 'de_gart_augsburg1487', 'la_vulgate_train', 'mhg_train', 'ita_train'):
        words = ref_words(REFS[key])
        if len(words) < total + 10:
            continue
        per = []
        for rep in range(3):
            start = int(rng.integers(0, len(words) - total)); seq = words[start:start + total]
            fake_lines = []; at = 0
            for p, sz in zip(ms['pages'], page_sizes):
                page_tokens = seq[at:at + sz]; at += sz
                # distribute the page's tokens over its lines with the manuscript's line lengths
                k = 0
                for l in range(p['start_line'], p['end_line']):
                    n = len(ms['lines'][l]['words']); fake_lines.append(page_tokens[k:k + n]); k += n
            per.append(decompose(ms, fake_lines))
        refs[key] = {g: {k: float(np.mean([x[g][k] for x in per])) for k in per[0][g]} for g in groups}
    results.update({f'ref_{k}': v for k, v in refs.items()})
    (D.HERE / 'scales.json').write_text(json.dumps(results, indent=1), encoding='utf-8')
    print('group: G (group bag) | bifolium-level | page-level | within-page | A (actual page MATTR)')
    for key, res in results.items():
        print(key)
        for g in groups:
            r = res[g]
            print(f"  {g:5s} G {r['G']:.3f} | bif {r['bifolium_level']:+.3f} | page {r['page_level']:+.3f} | within {r['within_page']:+.3f} | A {r['A']:.3f}  (tokens {r['tokens']})")
    # route-wide token-weighted means of the three components
    print('\ntoken-weighted route means of the components:')
    for key, res in results.items():
        w = np.array([res[g]['tokens'] for g in groups], float)
        comp = {k: float(np.average([res[g][k] for g in groups], weights=w)) for k in ('bifolium_level', 'page_level', 'within_page', 'total')}
        print(f"  {key:13s} bifolium {comp['bifolium_level']:+.4f} page {comp['page_level']:+.4f} within-page {comp['within_page']:+.4f} total {comp['total']:+.4f}")


if __name__ == '__main__':
    main()
