"""T3. Is a manuscript MATTR drop a change of vocabulary concentration or a local clustering of repeats?

For every bifolium and page: actual MATTR100 (windows wholly inside the unit), the exact expectation
after shuffling the unit's own word bag (bag100), and the clustering gap bag100 - MATTR100. A copying
feedback loop produces its loss as clustering (the same forms recur within a stretch); a register
with fewer, more frequent word types produces its loss in the bag. Also the expectation of 100 i.i.d.
draws from the group's whole frequency distribution (group100): page bag below group bag = the page
concentrates on its own subset of the group's vocabulary (page-level bursts).
Manuscript, every generated stream (seed means), and natural-language references cut to the
manuscript's bifolium sizes.
"""
from collections import Counter, defaultdict
import json
import re
import sys
import unicodedata

import numpy as np

sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
import data as D

REFS = {
    'la_macer_milan1482': D.src('research/reference_corpus/texts/la/foxtrot/foxtrot_macer_milan1482_ocr_la.txt'),
    'la_psapuleius1543': D.src('research/reference_corpus/texts/la/foxtrot/foxtrot_psapuleius_paris1543_ocr_la.txt'),
    'la_galen_simplicium': D.src('research/reference_corpus/texts/la/foxtrot/foxtrot_galen_simplicium_wuerzburg_la.txt'),
    'la_dioscorides_longob': D.src('research/reference_corpus/texts/la/foxtrot/foxtrot_dioscorides_longobardus_ocr_la.txt'),
    'la_rhazes_almansor': D.src('research/reference_corpus/texts/la/foxtrot/foxtrot_rhazes_almansor_wuerzburg_la.txt'),
    'la_hildegard_physica': D.src('research/reference_corpus/texts/la/hildegard_physica_plants_trees_la.txt'),
    'la_vulgate_train': D.src('research/reference_corpus/derived/legacy_controls/c_lat_train.txt'),
    'de_gart_augsburg1487': D.src('research/reference_corpus/texts/de/foxtrot/foxtrot_gart_augsburg1487_ocr_de.txt'),
    'mhg_train': D.src('research/reference_corpus/derived/legacy_controls/c_mhg_train.txt'),
    'ita_train': D.src('research/reference_corpus/derived/legacy_controls/c_ita_train.txt'),
}


def ref_words(path, limit=60000):
    text = path.read_text(encoding='utf-8', errors='ignore').lower()
    text = unicodedata.normalize('NFKC', text)
    words = re.findall(r"[^\W\d_]+", text)
    return words[:limit]


def unit_metrics(words, group_probs=None):
    m = D.mattr(words); b = D.bag_mattr(words)
    out = dict(tokens=len(words), types=len(set(words)), mattr100=m, bag100=b, gap=b - m)
    if group_probs is not None:
        out['group100'] = D.iid_mattr(group_probs.values())
        c = Counter(words); n = len(words)
        out['page_iid100'] = D.iid_mattr([v / n for v in c.values()])
    return out


def stream_units(ms, lines):
    """Bifolium and page metrics of a line-aligned text."""
    nodes_units = defaultdict(list); page_units = defaultdict(list)
    for li, L in enumerate(ms['lines']):
        ws = lines[li]
        nodes_units[L['node']] += ws; page_units[L['page']] += ws
    group_words = defaultdict(list)
    for L, ws in zip(ms['lines'], lines):
        group_words[L['group']] += ws
    group_probs = {}
    for g, ws in group_words.items():
        c = Counter(ws); n = len(ws)
        group_probs[g] = {w: v / n for w, v in c.items()}
    out_nodes = {}
    for node in ms['nodes']:
        out_nodes[node['id']] = unit_metrics(nodes_units[node['id']], group_probs[node['group']])
    out_pages = {}
    for pg in ms['pages']:
        out_pages[pg['folio']] = unit_metrics(page_units[pg['index']], group_probs[pg['group']])
    return out_nodes, out_pages


def group_table(ms, out_nodes):
    """Token-weighted group means of the node metrics."""
    by = defaultdict(list)
    for node in ms['nodes']:
        by[node['group']].append((node['N'], out_nodes[node['id']]))
    res = {}
    for g, items in by.items():
        w = np.array([n for n, _ in items], dtype=float)
        res[g] = {k: float(np.average([m[k] for _, m in items], weights=w)) for k in ('mattr100', 'bag100', 'gap', 'group100')}
    return res


def main():
    ms = D.manuscript()
    order = [n['group'] for n in ms['nodes']]
    groups = list(dict.fromkeys(order))
    results = dict(groups=groups, streams={})
    ms_lines = [L['words'] for L in ms['lines']]
    nodes_ms, pages_ms = stream_units(ms, ms_lines)
    results['streams']['manuscript'] = dict(label='Manuscript', nodes=nodes_ms, pages=pages_ms, groups=group_table(ms, nodes_ms))
    for key, (label, srcs) in D.STREAMS.items():
        per_seed_nodes = []; per_seed_pages = []
        for s in srcs:
            n_, p_ = stream_units(ms, D.read_stream(s)); per_seed_nodes.append(n_); per_seed_pages.append(p_)
        nodes_mean = {nid: {k: float(np.mean([d[nid][k] for d in per_seed_nodes])) for k in per_seed_nodes[0][nid]} for nid in per_seed_nodes[0]}
        pages_mean = {pid: {k: float(np.mean([d[pid][k] for d in per_seed_pages])) for k in per_seed_pages[0][pid]} for pid in per_seed_pages[0]}
        results['streams'][key] = dict(label=label, seeds=len(srcs), nodes=nodes_mean, pages=pages_mean, groups=group_table(ms, nodes_mean))
    # natural-language references cut to the manuscript's bifolium sizes (Path order sizes), five random offsets
    sizes = [n['N'] for n in ms['nodes']]
    rng = np.random.default_rng(7)
    refs = {}
    for key, path in REFS.items():
        if not path.exists():
            continue
        words = ref_words(path)
        total = sum(sizes)
        if len(words) < total + 1000:
            # tile offsets inside what exists
            continue
        rows = []
        for rep in range(5):
            start = int(rng.integers(0, len(words) - total))
            at = start
            for sz in sizes:
                rows.append(unit_metrics(words[at:at + sz])); at += sz
        refs[key] = dict(tokens_available=len(words), units=len(rows),
                         mattr100=float(np.mean([r['mattr100'] for r in rows])), bag100=float(np.mean([r['bag100'] for r in rows])),
                         gap_mean=float(np.mean([r['gap'] for r in rows])), gap_p90=float(np.percentile([r['gap'] for r in rows], 90)),
                         gap_max=float(np.max([r['gap'] for r in rows])),
                         gap_by_size=[dict(size=sz, gap=float(np.mean([r['gap'] for r in rows[i::len(sizes)]]))) for i, sz in enumerate(sizes)][:0])
    results['references'] = refs
    # route-level summary: how much of each group step is bag vs gap, manuscript and streams
    steps = [('1a', '1b'), ('1b', '1.5a'), ('3b', '3a'), ('3c', '4c'), ('4c', '4a'), ('3c', '4a')]
    summary = {}
    for key, st in results['streams'].items():
        g = st['groups']
        summary[key] = {f'{a}->{b}': dict(d_mattr=g[b]['mattr100'] - g[a]['mattr100'], d_bag=g[b]['bag100'] - g[a]['bag100'],
                                           d_gap=g[b]['gap'] - g[a]['gap']) for a, b in steps}
    results['steps'] = summary
    (D.HERE / 'decompose.json').write_text(json.dumps(results, indent=1, default=float), encoding='utf-8')
    # print
    print('group means (MATTR100 / bag100 / gap / group-iid100):')
    for key, st in results['streams'].items():
        g = st['groups']
        print(f"{key:13s} " + ' '.join(f"{gr}:{g[gr]['mattr100']:.3f}/{g[gr]['bag100']:.3f}/{g[gr]['gap']:.3f}/{g[gr]['group100']:.3f}" for gr in groups))
    print('\nsteps (d_mattr, d_bag, d_gap):')
    for key, s in summary.items():
        print(f"{key:13s} " + ' '.join(f"{k}: {v['d_mattr']:+.3f} {v['d_bag']:+.3f} {v['d_gap']:+.3f}" for k, v in s.items()))
    print('\nreferences:')
    for k, r in refs.items():
        print(f"{k:24s} mattr {r['mattr100']:.3f} bag {r['bag100']:.3f} gap mean {r['gap_mean']:.3f} p90 {r['gap_p90']:.3f} max {r['gap_max']:.3f}")
    gaps = [nodes_ms[n['id']]['gap'] for n in ms['nodes']]
    print(f"\nmanuscript bifolium gap: mean {np.mean(gaps):.3f} p90 {np.percentile(gaps,90):.3f} max {np.max(gaps):.3f}")
    for key, st in results['streams'].items():
        gaps = [st['nodes'][n['id']]['gap'] for n in ms['nodes']]
        print(f"{key:13s} bifolium gap mean {np.mean(gaps):.3f} p90 {np.percentile(gaps,90):.3f} max {np.max(gaps):.3f}")


if __name__ == '__main__':
    main()
