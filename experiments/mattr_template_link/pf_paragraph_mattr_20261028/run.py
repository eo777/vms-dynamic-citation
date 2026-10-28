"""Direct MATTR contributions of P/F words and paragraph-opening lines.

Uses the existing transcription and Path 1 groups, not a generated model. Peak
working arrays are a few MB; compact JSON/CSV outputs are under 300 KB. No word
arrays or model checkpoints are written.
"""
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import data as D

WINDOW = 100
PARTS = ['pf_opener', 'nonpf_opener', 'pf_rest_of_line', 'nonpf_rest_of_line']


def is_pf(word):
    return 'p' in word or 'f' in word


def flatten(lines):
    words, line_index, first, opener, nodes = [], [], [], [], []
    spans = []
    for j, row in enumerate(lines):
        start = len(words)
        for k, word in enumerate(row['words']):
            words.append(word)
            line_index.append(j)
            first.append(row['first'])
            opener.append(row['first'] and k == 0)
            nodes.append(row['node'])
        spans.append((start, len(words)))
    pf = np.array([is_pf(w) for w in words])
    first, opener = np.array(first), np.array(opener)
    has_pf = np.array([any(is_pf(w) for w in row['words']) for row in lines])
    return dict(words=np.array(words, dtype=object), pf=pf, first=first, opener=opener,
                line=np.array(line_index), nodes=np.array(nodes), spans=spans, has_pf=has_pf)


def contribution_partition(t, selected_lines):
    """Four disjoint word sets; exact average marginal loss over all 24 removal orders."""
    selected = selected_lines[t['line']]
    masks = [selected & t['pf'] & t['opener'], selected & ~t['pf'] & t['opener'],
             selected & t['pf'] & ~t['opener'], selected & ~t['pf'] & ~t['opener']]
    values = {}
    for coalition in range(16):
        drop = np.zeros(len(t['words']), dtype=bool)
        for j in range(4):
            if coalition & (1 << j):
                drop |= masks[j]
        values[coalition] = D.mattr(t['words'][~drop])
    allocation, order_ranges = {}, {}
    for j, name in enumerate(PARTS):
        terms = []
        total = 0.0
        for coalition in range(16):
            if coalition & (1 << j):
                continue
            size = coalition.bit_count() if hasattr(coalition, 'bit_count') else bin(coalition).count('1')
            weight = math.factorial(size) * math.factorial(3-size) / math.factorial(4)
            change = values[coalition] - values[coalition | (1 << j)]
            total += weight * change
            terms.append(change)
        allocation[name] = total
        order_ranges[name] = [min(terms), max(terms)]
    full_loss = values[0] - values[15]
    assert abs(sum(allocation.values()) - full_loss) < 1e-12
    pf = allocation['pf_opener'] + allocation['pf_rest_of_line']
    other = allocation['nonpf_opener'] + allocation['nonpf_rest_of_line']
    opening = allocation['pf_opener'] + allocation['nonpf_opener']
    return dict(lines=int(selected_lines.sum()), tokens=int(selected.sum()),
                counts={name: int(mask.sum()) for name, mask in zip(PARTS, masks)},
                original_mattr=values[0], after_removing_selected_lines=values[15],
                total_loss=full_loss, allocation=allocation, pf_loss=pf, nonpf_loss=other,
                opener_loss=opening, rest_of_line_loss=full_loss-opening,
                pf_share_of_loss=pf/full_loss if full_loss else None,
                opener_share_of_loss=opening/full_loss if full_loss else None,
                removal_order_ranges=order_ranges,
                ablations={str(k): v for k, v in values.items()})


def rolling_attribution(lines, t):
    """Exact step-by-step change of trailing MATTR, plus fixed-window type credit."""
    words, n = t['words'], len(t['words'])
    counts = Counter(words[:WINDOW])
    distinct = np.full(n, np.nan)
    distinct[WINDOW-1] = len(counts)/WINDOW
    delta = np.full(n, np.nan)
    arrivals, departures = np.zeros(n, dtype=int), np.zeros(n, dtype=int)
    categories = np.where(t['first'],
                          np.where(t['opener'], np.where(t['pf'], 0, 1), np.where(t['pf'], 2, 3)),
                          np.where(t['pf'], 4, 5))
    credit, exposure = np.zeros(6), np.zeros(6)

    def score_window(start):
        end = start+WINDOW
        weights = [1/counts[word] for word in words[start:end]]
        share = np.bincount(categories[start:end], weights=weights, minlength=6)
        assert abs(share.sum()-len(counts)) < 1e-10
        credit[:] += share
        exposure[:] += np.bincount(categories[start:end], minlength=6)

    score_window(0)
    for i in range(WINDOW, n):
        old = words[i-WINDOW]
        counts[old] -= 1
        if not counts[old]:
            del counts[old]
            departures[i] = 1
        if words[i] not in counts:
            arrivals[i] = 1
        counts[words[i]] += 1
        delta[i] = (arrivals[i]-departures[i])/WINDOW
        distinct[i] = len(counts)/WINDOW
        assert abs(distinct[i]-distinct[i-1]-delta[i]) < 1e-12
        score_window(i-WINDOW+1)
    windows = n-WINDOW+1
    assert abs(credit.sum()/(WINDOW*windows)-D.mattr(words)) < 1e-12
    names = PARTS + ['pf_later_lines', 'nonpf_later_lines']
    fixed = {name: dict(mattr_contribution=float(credit[j]/(WINDOW*windows)),
                        token_window_share=float(exposure[j]/(WINDOW*windows)),
                        distinct_credit_per_token=float(credit[j]/exposure[j]) if exposure[j] else None)
             for j, name in enumerate(names)}
    rows = []
    for j, (start, end) in enumerate(t['spans']):
        if start < WINDOW:
            continue
        pieces = {name: float(delta[start:end][categories[start:end] == k].sum())
                  for k, name in enumerate(names)}
        pf_gain = float(delta[start:end][t['pf'][start:end]].sum())
        nonpf_gain = float(delta[start:end][~t['pf'][start:end]].sum())
        row = dict(group=lines[j]['group'], page=lines[j]['folio'], locus=lines[j]['locus'],
                   bifolium=lines[j]['node'], paragraph_first=bool(lines[j]['first']),
                   has_pf=bool(t['has_pf'][j]), tokens=end-start, pf_tokens=int(t['pf'][start:end].sum()),
                   before=float(distinct[start-1]), after=float(distinct[end-1]),
                   net_gain=float(delta[start:end].sum()), pf_gain=pf_gain, nonpf_gain=nonpf_gain,
                   opener_gain=float(delta[start:end][t['opener'][start:end]].sum()),
                   new_spellings=int(arrivals[start:end].sum()), lost_spellings=int(departures[start:end].sum()),
                   **pieces)
        assert abs(row['after']-row['before']-row['net_gain']) < 1e-12
        assert abs(pf_gain+nonpf_gain-row['net_gain']) < 1e-12
        rows.append(row)
    summaries = {}
    tests = dict(paragraph_first=lambda r:r['paragraph_first'],
                 paragraph_first_with_pf=lambda r:r['paragraph_first'] and r['has_pf'],
                 paragraph_first_without_pf=lambda r:r['paragraph_first'] and not r['has_pf'],
                 all_pf_lines=lambda r:r['has_pf'])
    for name, predicate in tests.items():
        selected = [row for row in rows if predicate(row)]
        if not selected:
            continue
        fields = ['before', 'after', 'net_gain', 'pf_gain', 'nonpf_gain', 'opener_gain', *names]
        means = {f: float(np.mean([r[f] for r in selected])) for f in fields}
        by_node = defaultdict(list)
        for row in selected:
            by_node[row['bifolium']].append(row)
        blocks = list(by_node.values())
        sizes = np.array([len(block) for block in blocks])
        totals = np.array([[sum(r[f] for r in block) for f in ['net_gain', 'pf_gain', 'nonpf_gain']] for block in blocks])
        rng = np.random.default_rng(281026)
        draws = rng.integers(0, len(blocks), size=(4000, len(blocks)))
        samples = totals[draws].sum(axis=1)/sizes[draws].sum(axis=1)[:, None]
        bounds = np.quantile(samples, [.025, .975], axis=0)
        summaries[name] = dict(lines=len(selected), bifolia=len(blocks), means=means,
                                ci95_bifolium_bootstrap={f: bounds[:, j].tolist() for j, f in enumerate(['net_gain', 'pf_gain', 'nonpf_gain'])})
    return fixed, summaries, rows


def region(lines, do_windows=True):
    t = flatten(lines)
    first_lines = np.array([row['first'] for row in lines])
    masks = dict(all_pf=t['pf'], paragraph_opener=t['opener'], paragraph_first_line=t['first'],
                 pf_on_first_line=t['pf'] & t['first'], nonpf_on_first_line=~t['pf'] & t['first'])
    ablations = {name: dict(removed_tokens=int(mask.sum()), remaining_mattr=D.mattr(t['words'][~mask])) for name, mask in masks.items()}
    result = dict(tokens=len(t['words']), lines=len(lines), pf_tokens=int(t['pf'].sum()),
                  paragraph_first_lines=int(first_lines.sum()), baseline_mattr=D.mattr(t['words']),
                  ablations=ablations,
                  opening_lines=contribution_partition(t, first_lines),
                  pf_bearing_opening_lines=contribution_partition(t, first_lines & t['has_pf']),
                  all_pf_lines=contribution_partition(t, t['has_pf']))
    rows = []
    if do_windows:
        result['fixed_windows'], result['rolling_line_change'], rows = rolling_attribution(lines, t)
    return result, rows


def main():
    ms = D.manuscript()
    source = json.loads((HERE.parent/'layout_controls.json').read_text(encoding='utf-8'))
    results, line_rows = {}, []
    for g in ['3c', '4c', '4a']:
        lines = [row for row in ms['lines'] if row['group'] == g]
        results[g], rows = region(lines)
        line_rows.extend(rows)
        assert abs(results[g]['baseline_mattr']-source['manuscript'][0]['route']['groups'][g]['mattr100']) < 1e-12
        r = results[g]
        p = r['opening_lines']
        print(f'{g}: MATTR {r["baseline_mattr"]:.6f}; first-line loss {p["total_loss"]*100:.3f} pp = PF {p["pf_loss"]*100:.3f} + other {p["nonpf_loss"]*100:.3f}; opener {p["opener_loss"]*100:.3f} pp', flush=True)
    # Same-group physical-section sensitivity. This sensitivity explicitly
    # concatenates only lines in the named physical section, as a deletion test.
    physical = {}
    for g, section in [('3c', 'S'), ('4c', 'S'), ('4a', 'B')]:
        lines = [row for row in ms['lines'] if row['group'] == g and ms['pages'][row['page']]['section'] == section]
        physical[g], _ = region(lines, do_windows=False)
    gap = results['3c']['baseline_mattr']-results['4a']['baseline_mattr']
    gap_checks = {}
    for key in ['all_pf', 'paragraph_opener', 'paragraph_first_line']:
        after = results['3c']['ablations'][key]['remaining_mattr']-results['4a']['ablations'][key]['remaining_mattr']
        gap_checks[key] = dict(original_gap=gap, remaining_gap=after, reduction=gap-after, fraction_remaining=after/gap)
    payload = dict(window=WINDOW,
                   definitions=dict(pf='Literal p or f anywhere in a study word, including cph/cfh.',
                                    opener='First word of a line whose recorded paragraph-first flag is true.',
                                    removal='Delete selected tokens, keep all remaining words in order, recompute MATTR100.',
                                    allocation='Exact Shapley allocation across four disjoint sets: PF opener, non-PF opener, other PF on selected line, other non-PF on selected line; average over all 24 removal orders.',
                                    fixed_windows='Each distinct spelling contributes 1/100 in its original window; divide its credit equally among its occurrences.',
                                    rolling='End-of-line minus pre-line trailing MATTR100; each arrival gets its new-spelling gain minus the spelling loss from its departing token.',
                                    groups='Same Path 1 Golf groups as the published report; 3c/4a include some pages outside physical Stars/Bio. Physical-only sensitivity reported separately.'),
                   provenance={name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in [('tokens', D.TOKENS), ('path_asset', D.ASSET), ('physical_map', D.PHYS)]},
                   groups=results, physical_section_only=physical, stars_to_bio_gap=gap_checks,
                   checks=dict(saved_manuscript_mattr_reproduced=True, shapley_additivity=True,
                               fixed_window_credit_additivity=True, rolling_changes_telescope=True))
    (HERE/'metrics.json').write_text(json.dumps(payload, indent=2)+'\n', encoding='utf-8')
    with (HERE/'line_changes.csv').open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(line_rows[0]))
        writer.writeheader();writer.writerows(line_rows)
    print('Saved compact metrics and per-line changes; no model runs or large arrays.', flush=True)


if __name__ == '__main__':
    main()
