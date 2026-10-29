"""T26. Thirty shuffles, geometry-matched (28 October, after a second external review of shuffle30_check.py).

Corrections made here. (1) shuffle30_check.py compared the manuscript's recorded-box scores with shuffles re-typeset into synthetic
boxes; those p-values do not test the recorded statistic. Here every size-matched paragraph shuffle is scored in BOTH geometries:
with the recorded rectangles kept (a same-length word takes the slot's recorded box, so the layout is unchanged) and re-typeset
into the frames; recorded observed values are compared with recorded shuffles and synthetic with synthetic. (2) The copiers were
compared without a baseline of their own; here each copier text is shuffled the same way (synthetic boxes), so excesses over
the shuffle baseline can be compared. (3) The two Rhazes runs scored different passages (the prose cut starts at a random
offset); here the passage start is an explicit argument, and both passages (566 and 16,785) can be run.
Scored: the study selector and the lines above only, components, H2 and word diversity, quintiles inside bifolium x exact length x
pool-size tertile, on interior words under definition A (study pool >= 15) and B (lines-above pool >= 15), both without the first
and last word of a line. Usage: python shuffle30b_check.py manuscript | timm | timm_spatial | noinnov_spatial | <prose key> --start N
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

K = 30
CONFIGS = [SW.cfg('study selector: left 3 + 8 lines above', left=3, depth=8), SW.cfg('lines above only (8)', depth=8)]


def cut_at(ms, words, page_sizes, start):
    """timing.laid_in with an explicit start."""
    total = sum(page_sizes)
    seq = words[start:start + total]
    out, at = [], 0
    for p, sz in zip(ms['pages'], page_sizes):
        pt = seq[at:at + sz]
        at += sz
        k = 0
        for l in range(p['start_line'], p['end_line']):
            n = len(ms['lines'][l]['words'])
            out.append(pt[k:k + n])
            k += n
    return out


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
    cohorts = {'A': inner & (study['n'] >= 15), 'B': inner & (above['n'] >= 15)}
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
    start = int(sys.argv[sys.argv.index('--start') + 1]) if '--start' in sys.argv else None
    ms = D.manuscript()
    app = CC.load_study_app('legacy')
    frames = CC.line_frames(app, ms)
    par = LS.paragraph_of_line(ms)
    recorded_geometry = None
    if key == 'manuscript':
        lines = [list(L['words']) for L in ms['lines']]
        comp_fn = CC.zattera
        recorded_geometry = app['geometry']
    elif key in D.STREAMS:
        lines = D.read_stream(D.STREAMS[key][1][0])
        comp_fn = CC.zattera
    else:
        page_sizes = [sum(len(ms['lines'][l]['words']) for l in range(p['start_line'], p['end_line'])) for p in ms['pages']]
        lines = cut_at(ms, ref_words(REFS[key]), page_sizes, start)
        comp_fn = lambda w: list(w)  # noqa: E731
        flags = CC.oversized_flags(app, ms)
        recorded_geometry = [None if flags[i] else g for i, g in enumerate(app['geometry'])]
    label = key + (f' (start {start})' if start is not None else '')
    observed = {}
    if recorded_geometry is not None:
        observed['recorded'] = analyse(ms, lines, recorded_geometry, 500, comp_fn)
    syn = [list(ws) for ws in lines]
    observed['synthetic'] = analyse(ms, syn, CC.synthetic_geometry(syn, frames, ms), 500, comp_fn)
    rng = np.random.default_rng(4028)
    shuffles = {'recorded': [], 'synthetic': []}
    for k in range(K):
        sh = size_matched_shuffle(lines, par, rng)
        if recorded_geometry is not None:
            shuffles['recorded'].append(analyse(ms, sh, recorded_geometry, 0, comp_fn))
        placed, geom, _ = LS.typeset(ms, frames, sh)
        shuffles['synthetic'].append(analyse(ms, placed, geom, 0, comp_fn))
        print(label, 'shuffle', k + 1, file=sys.stderr, flush=True)
    tag = key + (f'_start{start}' if start is not None else '')
    (HERE / f'shuffle30b_{tag}.json').write_text(json.dumps(dict(observed=observed, shuffles=shuffles), indent=1, default=float), encoding='utf-8')
    print(f'{label}: {K} size-matched paragraph shuffles scored in the SAME geometry as the observed text (recorded boxes kept, or re-typeset);')
    print('quintiles inside bifolium x exact length x pool-size tertile; interior A (study pool >= 15) and B (lines-above pool >= 15).')
    for geo, obs in observed.items():
        print(f'\n== {geo} geometry')
        for cname in ('A', 'B'):
            for c in CONFIGS:
                for meas in ('components', 'h2', 'worddiv'):
                    r = obs[cname][c['name']][meas]
                    v = np.array([s[cname][c['name']][meas]['diff'] for s in shuffles[geo]], float)
                    above = int((v < r['diff']).sum())
                    print(f"  {cname} {c['name']:38s} {meas:10s} observed {r['diff']:+.3f} [{r['ci'][0]:+.3f},{r['ci'][1]:+.3f}]  shuffles {v.mean():+.3f} ({v.min():+.3f}..{v.max():+.3f})  "
                          f"excess {r['diff'] - v.mean():+.3f}  above {above}/{len(v)} (p = {(len(v) - above + 1) / (len(v) + 1):.3f})")


if __name__ == '__main__':
    main()
