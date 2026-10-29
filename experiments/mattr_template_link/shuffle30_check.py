"""T25. Thirty shuffles, two interior definitions (28 October). prose_shuffle_more.py showed that the Rhazes text's interior
association moved from +0.033 to +0.012 when the interior cohort was defined by the lines-above pool (15 words or more) instead of
the study selector's pool, and sat at the median of 30 shuffles. The manuscript's margin over its 19 shuffles was +0.004, so it
needs the same check. For one text (argument: manuscript, la_rhazes_almansor or la_galen_simplicium) this script scores the
lines-above-only pool under the joint control on two interior cohorts, A (study selector pool >= 15, as interior_check.py) and
B (lines-above pool >= 15, as prose_shuffle_more.py), both without the first and last word of each line, against 30
size-matched paragraph shuffles re-typeset into the frames. Run from anywhere: python shuffle30_check.py <text> > shuffle30_<text>.log
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
import layout_shuffles as LS  # noqa: E402
from prose_shuffle_check import size_matched_shuffle  # noqa: E402
from decompose import REFS, ref_words  # noqa: E402
from timing import laid_in  # noqa: E402

K = 30
CONFIGS = [SW.cfg('study selector: left 3 + 8 lines above', left=3, depth=8), SW.cfg('lines above only (8)', depth=8)]


def analyse(ms, line_words, geometry, reps, comp_fn):
    inp = CC.make_input(ms, line_words, geometry, comp_fn)
    inp['configs'] = CONFIGS
    M = SW.measure(inp)
    node, group, bstart, bend = CC.token_meta(ms, line_words)
    out = CC.outcomes(inp['words'], bstart, bend)
    y = out['app_impact']
    length = np.array([len(w) for w in inp['words']])
    pos = np.concatenate([np.arange(len(ws)) for ws in line_words])
    ln = np.concatenate([np.full(len(ws), len(ws)) for ws in line_words])
    inner = (pos > 0) & (pos < ln - 1)
    study, above = M[CONFIGS[0]['name']], M[CONFIGS[1]['name']]
    cohorts = {'A: study pool >= 15': inner & (study['n'] >= 15), 'B: above pool >= 15': inner & (above['n'] >= 15)}
    res = {}
    for cname, cm in cohorts.items():
        res[cname] = {}
        for c in CONFIGS:
            m = M[c['name']]
            base = out['full'] & cm & np.isfinite(m['components']) & np.isfinite(m['h2']) & np.isfinite(m['worddiv'])
            q = np.nanpercentile(m['n'][base], [33, 67])
            strata = np.clip(length, 2, 9) * 10 + np.digitize(m['n'], q)
            res[cname][c['name']] = dict(n=int(base.sum()), **{meas: RC.contrast_strata(m[meas], y, node, strata, base, reps) for meas in RC.MEASURES})
    return res


def main():
    key = sys.argv[1]
    ms = D.manuscript()
    app = CC.load_study_app('legacy')
    frames = CC.line_frames(app, ms)
    par = LS.paragraph_of_line(ms)
    if key == 'manuscript':
        lines = [list(L['words']) for L in ms['lines']]
        comp_fn = CC.zattera
        observed = {'recorded boxes': analyse(ms, lines, app['geometry'], 500, comp_fn)}
    else:
        page_sizes = [sum(len(ms['lines'][l]['words']) for l in range(p['start_line'], p['end_line'])) for p in ms['pages']]
        lines = laid_in(ms, ref_words(REFS[key]), page_sizes)
        comp_fn = lambda w: list(w)  # noqa: E731
        observed = {}
    syn = [list(ws) for ws in lines]
    observed['synthetic boxes'] = analyse(ms, syn, CC.synthetic_geometry(syn, frames, ms), 500, comp_fn)
    rng = np.random.default_rng(3028)
    shuffles = []
    for k in range(K):
        sh = size_matched_shuffle(lines, par, rng)
        placed, geom, _ = LS.typeset(ms, frames, sh)
        shuffles.append(analyse(ms, placed, geom, 0, comp_fn))
        print(key, 'shuffle', k + 1, file=sys.stderr, flush=True)
    (HERE / f'shuffle30_{key}.json').write_text(json.dumps(dict(observed=observed, shuffles=shuffles), indent=1, default=float), encoding='utf-8')
    print(f'{key}: lines-above-only and study-selector pools under the joint control (inside exact length x pool-size tertile), interior words,')
    print(f'two interior definitions, against {K} size-matched paragraph shuffles re-typeset into the frames.')
    for cname in observed['synthetic boxes']:
        print(f'\n== cohort {cname}')
        for c in CONFIGS:
            print(f"  -- {c['name']}")
            for meas in ('components', 'h2'):
                v = np.array([s[cname][c['name']][meas]['diff'] for s in shuffles], float)
                for geo, o in observed.items():
                    r = o[cname][c['name']]
                    above = int((v < r[meas]['diff']).sum())
                    print(f"     {meas:10s} {geo:16s} n={r['n']:6d} observed {r[meas]['diff']:+.3f} [{r[meas]['ci'][0]:+.3f},{r[meas]['ci'][1]:+.3f}]  "
                          f"shuffles mean {v.mean():+.3f}, range {v.min():+.3f}..{v.max():+.3f}, above {above}/{len(v)} (p = {(len(v) - above + 1) / (len(v) + 1):.3f})")


if __name__ == '__main__':
    main()
