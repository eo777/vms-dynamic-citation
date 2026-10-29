"""Opening-line MATTR attribution after P/F substitutions.

Retain the original P/F and paragraph-position labels after changing spellings.
Uses existing words only, a few MB of working memory and compact JSON output.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path

import numpy as np

import run as R
from normalize_pf import normalize

HERE = Path(__file__).resolve().parent


def fixed_credit_for_mask(words, selected):
    """Type credit for a specified subset within the unchanged 100-word windows."""
    counts = Counter(words[:R.WINDOW])
    credit, exposure = 0.0, 0
    for start in range(len(words)-R.WINDOW+1):
        if start:
            old, new = words[start-1], words[start+R.WINDOW-1]
            counts[old] -= 1
            if not counts[old]:
                del counts[old]
            counts[new] += 1
        for i in range(start, start+R.WINDOW):
            if selected[i]:
                credit += 1/counts[words[i]]
                exposure += 1
    return dict(distinct_credit_per_token=credit/exposure,
                token_window_exposures=exposure,
                mattr_contribution=credit/(R.WINDOW*(len(words)-R.WINDOW+1)))


def analyze(lines, replacement):
    t = R.flatten(lines)
    if replacement != 'original':
        t['words'] = np.array([normalize(w, replacement) for w in t['words']], dtype=object)
    first_lines = np.array([row['first'] for row in lines])
    fixed, rolling, _ = R.rolling_attribution(lines, t)
    all_opening = R.contribution_partition(t, first_lines)
    pf_opening = R.contribution_partition(t, first_lines & t['has_pf'])
    # Equal-token comparison: distinct-type credit per exposure to a 100-word
    # window. Each type's unit credit is divided among its occurrences.
    other_opening = fixed['nonpf_rest_of_line']['distinct_credit_per_token']
    other_later = fixed['nonpf_later_lines']['distinct_credit_per_token']
    same_pf_line = fixed_credit_for_mask(t['words'], t['first'] & ~t['opener'] & ~t['pf'] & t['has_pf'][t['line']])
    same_pf_line['later_line_credit_per_token'] = other_later
    same_pf_line['difference'] = same_pf_line['distinct_credit_per_token']-other_later
    return dict(opening_lines=all_opening, pf_bearing_opening_lines=pf_opening,
                fixed_windows=fixed, rolling_line_change=rolling,
                nonpf_after_opener_on_pf_bearing_lines=same_pf_line,
                nonpf_after_opener_vs_later_lines=dict(
                    opening_line_credit_per_token=other_opening,
                    later_line_credit_per_token=other_later,
                    difference=other_opening-other_later))


def main():
    manuscript = R.D.manuscript()
    baseline = json.loads((HERE/'metrics.json').read_text())['groups']
    normalized = json.loads((HERE/'normalization_comparison.json').read_text())
    results = {}
    for replacement in ['original', 'k', 'ke', 't']:
        results[replacement] = {}
        for group in ['3c', '4c', '4a']:
            lines = [line for line in manuscript['lines'] if line['group'] == group]
            result = analyze(lines, replacement)
            part = result['opening_lines']
            if replacement == 'original':
                assert part == baseline[group]['opening_lines']
                assert result['fixed_windows'] == baseline[group]['fixed_windows']
                expected = baseline[group]['baseline_mattr']
            else:
                expected = normalized[replacement]['groups'][group]['normalized_mattr']
            assert abs(part['original_mattr']-expected) < 1e-12
            assert part['counts'] == baseline[group]['opening_lines']['counts']
            results[replacement][group] = result
            credit = result['nonpf_after_opener_vs_later_lines']
            print(f'{replacement} {group}: opening line {part["total_loss"]*100:.3f} pp; '
                  f'PF {part["pf_loss"]*100:.3f}, nonPF {part["nonpf_loss"]*100:.3f}; '
                  f'opener {part["opener_loss"]*100:.3f}, rest {part["rest_of_line_loss"]*100:.3f}; '
                  f'nonPF rest {part["allocation"]["nonpf_rest_of_line"]*100:.3f}; '
                  f'nonPF per-token credit {credit["opening_line_credit_per_token"]:.4f} vs '
                  f'{credit["later_line_credit_per_token"]:.4f}', flush=True)
    payload = dict(window=100,
                   definitions=dict(
                       substitution='Literal p and f both become the stated replacement, everywhere in all words.',
                       labels='P/F membership and paragraph position are fixed from the original text, before substitution.',
                       removal='Same four-set Shapley removal attribution as run.py; gaps close after removing words.',
                       fixed='Original token positions and windows; every type has unit credit divided among its occurrences. Per-token means divide by token-window exposure.',
                       comparison='Compare non-P/F words after the first word of opening lines with non-P/F words on subsequent lines. All opening lines are included.',
                       rolling='End-of-line minus pre-line trailing diversity; arriving words receive new-type gain minus departing-type loss.'),
                   inputs_sha256={name: hashlib.sha256(path.read_bytes()).hexdigest()
                                  for name, path in [('tokens', R.D.TOKENS), ('path_asset', R.D.ASSET), ('physical_map', R.D.PHYS)]},
                   variants=results,
                   checks=dict(original_results_reproduced=True, normalized_mattr_reproduced=True,
                               original_class_membership_preserved=True, shapley_additivity=True,
                               fixed_window_credit_additivity=True, rolling_changes_telescope=True))
    (HERE/'opening_line_normalization.json').write_text(json.dumps(payload, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
