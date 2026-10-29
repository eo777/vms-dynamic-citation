"""T18. A width-neutral distance for the selector (28 October, user's point: nearer words should count more, so distance
weights are the right design; the uniform-weight row of the sweep is a diagnostic, not a replacement).

The study selector measures the distance to a same-line word centre to centre, so a short N has its neighbour's centre closer
and gives it more weight than a long N would: the pool's weighted diversity then carries N's own length (section 7, item 9).
Here the same-line distance is the GAP between the two boxes in word widths, plus one, so an adjacent word has distance 1
whatever the lengths of N and the neighbour; the cone, the reach, the inverse-square weights and the cap are unchanged.
Scored: component diversity -> word impact, raw (quintiles within bifolium) and inside exact word-length classes (quintiles
within bifolium x length), for the study selector and its width-neutral form, above and below, on the manuscript (recorded
rectangles), the size-matched whole-manuscript shuffle and the first seed of three copiers.
Run from anywhere: python width_neutral_check.py > width_neutral_check.log
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import data as D  # noqa: E402
import component_check as CC  # noqa: E402
import direction_check as DC  # noqa: E402
import layout_shuffles as LS  # noqa: E402
import sweep_check as SW  # noqa: E402
from length_class_check import contrast_within  # noqa: E402

CONFIGS = [
    SW.cfg('study selector (centre distance)', left=3, depth=8),
    SW.cfg('study selector, width-neutral (gap distance)', left=3, depth=8, metric='edge'),
    SW.cfg('mirror (centre distance)', dir='down', right=3, depth=8),
    SW.cfg('mirror, width-neutral (gap distance)', dir='down', right=3, depth=8, metric='edge'),
]


def analyse(ms, line_words, geometry):
    inp = CC.make_input(ms, line_words, geometry, CC.zattera)
    inp['configs'] = CONFIGS
    M = SW.measure(inp)
    node, group, bstart, bend = CC.token_meta(ms, line_words)
    out = CC.outcomes(inp['words'], bstart, bend)
    length = np.array([len(w) for w in inp['words']])
    res = {}
    for c in CONFIGS:
        m = M[c['name']]
        base = out['full'] & np.isfinite(m['components'])
        rows = DC.rows_by_bifolium(m['components'], out['app_impact'], node, base)
        raw = DC.contrast(np.array(list(rows.values()), float))
        within, ci, nb = contrast_within(m['components'], out['app_impact'], node, length, base)
        # how much the pool's diversity depends on N's own length: Spearman-like, the mean pool diversity for 2- and 8-letter targets
        d2 = float(np.nanmean(m['components'][base & (length == 2)]))
        d8 = float(np.nanmean(m['components'][base & (length == 8)]))
        res[c['name']] = dict(n=int(base.sum()), raw=raw, within=within, within_ci=ci, div_len2=d2, div_len8=d8)
    return res


def main():
    ms = D.manuscript()
    app = CC.load_study_app('legacy')
    ms_lines = [L['words'] for L in ms['lines']]
    frames = CC.line_frames(app, ms)
    texts = [('manuscript (recorded boxes)', ms_lines, app['geometry'])]
    srng = np.random.default_rng(1028)
    lines, _ = LS.words_in_units(ms, np.zeros(len(ms['lines']), int), srng)
    placed, geom, _ = LS.typeset(ms, frames, lines)
    texts.append(('words shuffled in whole manuscript (size-matched)', placed, geom))
    for key, label in (('timm', 'Original Timm, page draw (seed 1)'), ('timm_spatial', 'Original Timm, words in view (seed 1)'), ('noinnov_spatial', 'no-innovator, words in view (seed 1)')):
        L0 = D.read_stream(D.STREAMS[key][1][0])
        texts.append((label, L0, CC.synthetic_geometry(L0, frames, ms)))
    results = {}
    print('Component diversity -> word impact, lowest minus highest quintile; "within length" = quintiles inside bifolium x exact word length.')
    print('pool diversity for 2-letter / 8-letter targets shows how far the pool measure carries N\'s own length.')
    for name, lines, geometry in texts:
        r = analyse(ms, lines, geometry)
        results[name] = r
        print(f'\n{name} (n = {r[CONFIGS[0]["name"]]["n"]})')
        print(f"  {'selector':46s} {'raw':>8s} {'within length':>26s} {'pool div. len 2 / len 8':>24s}")
        for c in CONFIGS:
            v = r[c['name']]
            print(f"  {c['name']:46s} {v['raw']:+8.3f} {v['within']:+.3f} [{v['within_ci'][0]:+.3f},{v['within_ci'][1]:+.3f}]".ljust(84)
                  + f"{v['div_len2']:8.2f} / {v['div_len8']:.2f}", flush=True)
    (HERE / 'width_neutral_check.json').write_text(json.dumps(results, indent=1, default=float), encoding='utf-8')


if __name__ == '__main__':
    main()
