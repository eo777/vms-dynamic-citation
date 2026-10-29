"""T24. Do the prose controls' interior associations survive word shuffling? (28 October, user's question)

prose_interior_check.py found that on interior words the lines above alone give natural prose small positive associations under
the joint control (components -0.007 to +0.033). Here each prose text (cut into the manuscript's lines and re-typeset into its
frames, letters as units) is compared with K size-matched paragraph shuffles of itself, re-typeset the same way, on the interior
cohort, for the study selector and the lines above only: observed value, shuffle mean and range, and the observed value's rank.
The manuscript's own comparison of this kind is in interior_check.log. Run from anywhere: python prose_shuffle_check.py > prose_shuffle_check.log
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import data as D  # noqa: E402
import component_check as CC  # noqa: E402
import sweep_check as SW  # noqa: E402
import interior_check as IC  # noqa: E402
import layout_shuffles as LS  # noqa: E402
from decompose import REFS, ref_words  # noqa: E402
from timing import laid_in  # noqa: E402

K = 9
IC.CONFIGS = [SW.cfg('study selector: left 3 + 8 lines above', left=3, depth=8), SW.cfg('lines above only (8)', depth=8)]


def size_matched_shuffle(lines, unit, rng):
    """Words permuted inside each unit among words of the same character length (as layout_shuffles.words_in_units, for any text)."""
    groups = defaultdict(list)
    for l, ws in enumerate(lines):
        for k, w in enumerate(ws):
            groups[(unit[l], len(w))].append((l, k))
    out = [list(ws) for ws in lines]
    for slots in groups.values():
        words = [lines[l][k] for l, k in slots]
        for (l, k), j in zip(slots, rng.permutation(len(slots))):
            out[l][k] = words[j]
    return out


def main():
    ms = D.manuscript()
    app = CC.load_study_app('legacy')
    frames = CC.line_frames(app, ms)
    page_sizes = [sum(len(ms['lines'][l]['words']) for l in range(p['start_line'], p['end_line'])) for p in ms['pages']]
    par = LS.paragraph_of_line(ms)
    letters = lambda w: list(w)  # noqa: E731
    results = {}
    for key in CC.PROSE:
        words = ref_words(REFS[key])
        if len(words) < sum(page_sizes) + 10:
            continue
        lines = laid_in(ms, words, page_sizes)
        syn = [list(ws) for ws in lines]
        observed = IC.analyse(ms, syn, CC.synthetic_geometry(syn, frames, ms), 300, comp_fn=letters)
        rng = np.random.default_rng(1028)
        shuffles = []
        for k in range(K):
            sh = size_matched_shuffle(lines, par, rng)
            placed, geom, _ = LS.typeset(ms, frames, sh)
            shuffles.append(IC.analyse(ms, placed, geom, 0, comp_fn=letters))
            print(key, 'shuffle', k + 1, file=sys.stderr, flush=True)
        results[key] = dict(observed=observed, shuffles=shuffles)
        print(key, 'done', file=sys.stderr, flush=True)
    (HERE / 'prose_shuffle_check.json').write_text(json.dumps(results, indent=1, default=float), encoding='utf-8')

    print(f'Prose texts re-typeset into the manuscript\'s frames against {K} size-matched paragraph shuffles of themselves, interior words only')
    print('(not first or last in the line, study pool >= 15); within-bifolium quintile contrast of word impact, inside exact length x pool-size')
    print('tertile (joint control), with the raw value for reference. rank = shuffles the observed text exceeds.')
    for meas in ('components', 'h2'):
        print(f'\n== {meas}')
        for c in IC.CONFIGS:
            print(f"  -- {c['name']}")
            print(f"     {'text':26s} {'observed raw':>13s} {'shuffles raw (mean, range)':>30s} {'observed joint':>24s} {'shuffles joint (mean, range)':>30s} {'rank':>6s}")
            for key, r in results.items():
                o = r['observed'][c['name']]['interior-1'][meas]
                raw = np.array([s[c['name']]['interior-1'][meas]['raw']['diff'] for s in r['shuffles']], float)
                jt = np.array([s[c['name']]['interior-1'][meas]['length_pool']['diff'] for s in r['shuffles']], float)
                print(f"     {key:26s} {o['raw']['diff']:+13.3f} {raw.mean():+.3f} ({raw.min():+.3f}..{raw.max():+.3f})".ljust(72)
                      + f"{o['length_pool']['diff']:+.3f} [{o['length_pool']['ci'][0]:+.3f},{o['length_pool']['ci'][1]:+.3f}]".rjust(24)
                      + f" {jt.mean():+.3f} ({jt.min():+.3f}..{jt.max():+.3f})".rjust(30) + f" {int((jt < o['length_pool']['diff']).sum())}/{len(jt)}".rjust(7))


if __name__ == '__main__':
    main()
