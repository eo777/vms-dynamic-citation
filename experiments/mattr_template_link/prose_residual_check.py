"""T20. Does natural prose show the residual association under the joint controls? (28 October, user's question)

residual_check.py found that under quintiles formed inside bifolium x exact word length x pool-size tertile the manuscript keeps a
positive association between the diversity of the words in view and the next word's chance of being a repeat (components +0.026,
H2 +0.035). Natural prose had only been scored with the raw statistic (section 7, item 5; section 8), which the length effect
dominates. Here the five historical texts are cut into the manuscript's lines with the recorded rectangles (oversized boxes
removed), as in component_check.py, with letters as units and letter pairs as components, and scored exactly as the manuscript
in residual_check.py: raw, inside exact length, inside exact length x pool-size tertile, for component diversity, H2 and word
diversity, under the study selector and its width-neutral form. Run from anywhere: python prose_residual_check.py > prose_residual_check.log
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import data as D  # noqa: E402
import component_check as CC  # noqa: E402
import sweep_check as SW  # noqa: E402
import residual_check as RC  # noqa: E402
from decompose import REFS, ref_words  # noqa: E402
from timing import laid_in  # noqa: E402


def analyse(ms, line_words, geometry, comp_fn, reps):
    inp = CC.make_input(ms, line_words, geometry, comp_fn)
    inp['configs'] = list(RC.SELECTORS.values())
    M = SW.measure(inp)
    node, group, bstart, bend = CC.token_meta(ms, line_words)
    out = CC.outcomes(inp['words'], bstart, bend)
    y = out['app_impact']
    length = np.array([len(w) for w in inp['words']])
    res = {}
    for sel, c in RC.SELECTORS.items():
        m = M[c['name']]
        base = out['full'] & np.isfinite(m['components']) & np.isfinite(m['h2']) & np.isfinite(m['worddiv'])
        q = np.nanpercentile(m['n'][base], [33, 67])
        tert = np.digitize(m['n'], q)
        strata_len = np.clip(length, 2, 9)
        r = dict(n=int(base.sum()), mean_impact=float(np.nanmean(y[base])))
        for meas in RC.MEASURES:
            r[meas] = dict(raw=RC.contrast_strata(m[meas], y, node, np.zeros(len(y), int), base, reps, min_cell=25),
                           length=RC.contrast_strata(m[meas], y, node, strata_len, base, reps),
                           length_pool=RC.contrast_strata(m[meas], y, node, strata_len * 10 + tert, base, reps))
        res[sel] = r
    return res


def main():
    ms = D.manuscript()
    app = CC.load_study_app('legacy')
    flags = CC.oversized_flags(app, ms)
    clean = [None if flags[i] else g for i, g in enumerate(app['geometry'])]
    page_sizes = [sum(len(ms['lines'][l]['words']) for l in range(p['start_line'], p['end_line'])) for p in ms['pages']]
    frames = CC.line_frames(app, ms)
    results = {}
    for key in CC.PROSE:
        words = ref_words(REFS[key])
        if len(words) < sum(page_sizes) + 10:
            continue
        lines = laid_in(ms, words, page_sizes)
        results[key + ' (recorded boxes)'] = analyse(ms, lines, clean, lambda w: list(w), reps=500)
        # the same text re-typeset into the frames at the line's letter size (the recorded boxes belong to the manuscript's
        # words and misfit the prose words, the flaw of the old shuffles); carry-over changes the line lists in place
        syn = [list(ws) for ws in lines]
        geom = CC.synthetic_geometry(syn, frames, ms)
        results[key + ' (re-typeset)'] = analyse(ms, syn, geom, lambda w: list(w), reps=500)
        print(key, 'done', file=sys.stderr, flush=True)
    (HERE / 'prose_residual_check.json').write_text(json.dumps(results, indent=1, default=float), encoding='utf-8')

    def fmt(r):
        return f"{r['diff']:+.3f} [{r['ci'][0]:+.3f},{r['ci'][1]:+.3f}]" if np.isfinite(r['ci'][0]) else f"{r['diff']:+.3f}"
    print('Natural prose in the manuscript\'s lines (recorded rectangles, letters as units): within-bifolium quintile contrast of word impact;')
    print('raw, inside exact word length, inside exact length x pool-size tertile. Manuscript values from residual_check.log for comparison:')
    print('study selector components +0.034 / -0.009 / +0.026, H2 +0.027 / +0.001 / +0.035, word diversity +0.020 / -0.029 / +0.013.')
    for sel, c in RC.SELECTORS.items():
        print(f"\n== {c['name']}")
        for meas in RC.MEASURES:
            print(f"  -- {meas}")
            print(f"     {'text':42s} {'n':>6s} {'mean impact':>11s} {'raw':>24s} {'inside length':>24s} {'inside length x pool size':>26s}")
            for key, r in results.items():
                v = r[sel]
                print(f"     {key:42s} {v['n']:6d} {v['mean_impact']:11.3f} {fmt(v[meas]['raw']):>24s} {fmt(v[meas]['length']):>24s} {fmt(v[meas]['length_pool']):>26s}")


if __name__ == '__main__':
    main()
