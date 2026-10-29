"""T21. Which part of the window carries the residual? Pool shapes under the joint length x pool-size control (28 October,
user's observation that in the page's examples the low diversity comes from the words above, not from the words to the left).

The geometry sweep scored the other-lines-only pools raw and at fixed pool size, before the joint control had shown how far pool
size reverses the sign. Here the pool shapes are scored as in residual_check.py (components, H2, word diversity; raw, inside exact
length, inside exact length x pool-size tertile) on the manuscript (recorded and synthetic rectangles) and the first seed of
three copiers: the study selector; the same with no same-line reach (other lines only); lines above only at depths 2, 3 and 5;
one same-line word plus the lines above; the mirror and the lines below only. Run from anywhere: python shape_residual_check.py > shape_residual_check.log
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

CONFIGS = [
    SW.cfg('study selector: left 3 + 8 lines above', left=3, depth=8),
    SW.cfg('other lines only: 8 lines above', depth=8),
    SW.cfg('other lines only: 5 lines above', depth=5),
    SW.cfg('other lines only: 3 lines above', depth=3),
    SW.cfg('other lines only: 2 lines above', depth=2),
    SW.cfg('left 1 + 8 lines above', left=1, depth=8),
    SW.cfg('mirror: right 3 + 8 lines below', dir='down', right=3, depth=8),
    SW.cfg('other lines only: 8 lines below', dir='down', depth=8),
]


def analyse(ms, line_words, geometry, reps):
    inp = CC.make_input(ms, line_words, geometry, CC.zattera)
    inp['configs'] = CONFIGS
    M = SW.measure(inp)
    node, group, bstart, bend = CC.token_meta(ms, line_words)
    out = CC.outcomes(inp['words'], bstart, bend)
    y = out['app_impact']
    length = np.array([len(w) for w in inp['words']])
    res = {}
    for c in CONFIGS:
        m = M[c['name']]
        base = out['full'] & np.isfinite(m['components']) & np.isfinite(m['h2']) & np.isfinite(m['worddiv'])
        q = np.nanpercentile(m['n'][base], [33, 67])
        tert = np.digitize(m['n'], q)
        strata_len = np.clip(length, 2, 9)
        r = dict(n=int(base.sum()), pool=float(np.nanmean(m['n'][base])))
        for meas in RC.MEASURES:
            r[meas] = dict(raw=RC.contrast_strata(m[meas], y, node, np.zeros(len(y), int), base, reps, min_cell=25),
                           length=RC.contrast_strata(m[meas], y, node, strata_len, base, reps),
                           length_pool=RC.contrast_strata(m[meas], y, node, strata_len * 10 + tert, base, reps))
        res[c['name']] = r
    return res


def main():
    ms = D.manuscript()
    app = CC.load_study_app('legacy')
    ms_lines = [L['words'] for L in ms['lines']]
    frames = CC.line_frames(app, ms)
    results = {}
    if '--print' in sys.argv:
        results = json.loads((HERE / 'shape_residual_check.json').read_text(encoding='utf-8'))
    else:
        results['manuscript (recorded boxes)'] = analyse(ms, ms_lines, app['geometry'], 1000)
        print('manuscript done', file=sys.stderr, flush=True)
        syn = [list(ws) for ws in ms_lines]
        results['manuscript (synthetic boxes)'] = analyse(ms, syn, CC.synthetic_geometry(syn, frames, ms), 500)
        for key, label in (('timm', 'Original Timm, page draw (seed 1)'), ('timm_spatial', 'Original Timm, words in view (seed 1)'), ('noinnov_spatial', 'no-innovator, words in view (seed 1)')):
            L0 = D.read_stream(D.STREAMS[key][1][0])
            results[label] = analyse(ms, L0, CC.synthetic_geometry(L0, frames, ms), 300)
            print(label, 'done', file=sys.stderr, flush=True)
        (HERE / 'shape_residual_check.json').write_text(json.dumps(results, indent=1, default=float), encoding='utf-8')

    def fmt(r):
        return f"{r['diff']:+.3f} [{r['ci'][0]:+.3f},{r['ci'][1]:+.3f}]" if np.isfinite(r['ci'][0]) else f"{r['diff']:+.3f}"
    print('Pool shapes under the joint control: within-bifolium quintile contrast of word impact, quintiles formed inside bifolium x exact word')
    print('length x pool-size tertile (and raw, and inside length only, for reference).')
    for meas in RC.MEASURES:
        print(f'\n== {meas}')
        for name, r in results.items():
            print(f'  -- {name}')
            print(f"     {'pool shape':40s} {'n':>6s} {'pool':>5s} {'raw':>24s} {'inside length':>24s} {'inside length x pool size':>26s}")
            for c in CONFIGS:
                v = r[c['name']]
                print(f"     {c['name']:40s} {v['n']:6d} {v['pool']:5.1f} {fmt(v[meas]['raw']):>24s} {fmt(v[meas]['length']):>24s} {fmt(v[meas]['length_pool']):>26s}")


if __name__ == '__main__':
    main()
