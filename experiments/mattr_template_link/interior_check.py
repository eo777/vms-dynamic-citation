"""T22. Interior words only (28 October, user's point: words at the edges of the text, the first word of a line, the top lines
of a page, words beside a drawing, have truncated windows and so low measured diversity whatever the text, which shows on the
control pages too; the pool-size tertiles are a weak proxy for that, and the edge noise may be what the tests read instead of
the stronger interior structure).

Edges are defined explicitly and removed as targets. interior-1: not the first or last word of its line, and the study selector's
pool holds at least 15 words. interior-2: interior-1 and not in the first two lines of the page. On each cohort the study
selector, the lines above only, the lines below only and the mirror are scored as in residual_check.py (components, H2, word
diversity; raw, inside exact length, inside exact length x pool-size tertile) on the manuscript (recorded and synthetic
rectangles), the first seed of three copiers, and 19 size-matched paragraph shuffles re-typeset into the frames (mean, range,
rank of the manuscript with synthetic boxes). Run from anywhere: python interior_check.py > interior_check.log
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

K = 19
CONFIGS = [
    SW.cfg('study selector: left 3 + 8 lines above', left=3, depth=8),
    SW.cfg('lines above only (8)', depth=8),
    SW.cfg('lines below only (8)', dir='down', depth=8),
    SW.cfg('mirror: right 3 + 8 lines below', dir='down', right=3, depth=8),
]
COHORTS = ('all', 'interior-1', 'interior-2')


def analyse(ms, line_words, geometry, reps, comp_fn=CC.zattera):
    inp = CC.make_input(ms, line_words, geometry, comp_fn)
    inp['configs'] = CONFIGS
    M = SW.measure(inp)
    node, group, bstart, bend = CC.token_meta(ms, line_words)
    out = CC.outcomes(inp['words'], bstart, bend)
    y = out['app_impact']
    length = np.array([len(w) for w in inp['words']])
    pos = np.concatenate([np.arange(len(ws)) for ws in line_words])
    ln = np.concatenate([np.full(len(ws), len(ws)) for ws in line_words])
    line_in_page = np.concatenate([np.full(len(ws), l - ms['pages'][ms['lines'][l]['page']]['start_line']) for l, ws in enumerate(line_words)])
    study = M[CONFIGS[0]['name']]
    interior1 = (pos > 0) & (pos < ln - 1) & (study['n'] >= 15)
    interior2 = interior1 & (line_in_page >= 2)
    cohorts = {'all': np.ones(len(y), bool), 'interior-1': interior1, 'interior-2': interior2}
    res = {}
    for c in CONFIGS:
        m = M[c['name']]
        valid = out['full'] & np.isfinite(m['components']) & np.isfinite(m['h2']) & np.isfinite(m['worddiv'])
        res[c['name']] = {}
        for cname, cm in cohorts.items():
            base = valid & cm
            q = np.nanpercentile(m['n'][base], [33, 67])
            tert = np.digitize(m['n'], q)
            strata_len = np.clip(length, 2, 9)
            r = dict(n=int(base.sum()), pool=float(np.nanmean(m['n'][base])))
            for meas in RC.MEASURES:
                r[meas] = dict(raw=RC.contrast_strata(m[meas], y, node, np.zeros(len(y), int), base, reps, min_cell=25),
                               length=RC.contrast_strata(m[meas], y, node, strata_len, base, reps),
                               length_pool=RC.contrast_strata(m[meas], y, node, strata_len * 10 + tert, base, reps))
            res[c['name']][cname] = r
    return res


def main():
    ms = D.manuscript()
    app = CC.load_study_app('legacy')
    ms_lines = [L['words'] for L in ms['lines']]
    frames = CC.line_frames(app, ms)
    results = {'texts': {}, 'shuffles': []}
    if '--print' in sys.argv:
        results = json.loads((HERE / 'interior_check.json').read_text(encoding='utf-8'))
    else:
        results['texts']['manuscript (recorded boxes)'] = analyse(ms, ms_lines, app['geometry'], 1000)
        print('manuscript done', file=sys.stderr, flush=True)
        syn = [list(ws) for ws in ms_lines]
        results['texts']['manuscript (synthetic boxes)'] = analyse(ms, syn, CC.synthetic_geometry(syn, frames, ms), 500)
        for key, label in (('timm', 'Original Timm, page draw (seed 1)'), ('timm_spatial', 'Original Timm, words in view (seed 1)'), ('noinnov_spatial', 'no-innovator, words in view (seed 1)')):
            L0 = D.read_stream(D.STREAMS[key][1][0])
            results['texts'][label] = analyse(ms, L0, CC.synthetic_geometry(L0, frames, ms), 300)
            print(label, 'done', file=sys.stderr, flush=True)
        srng = np.random.default_rng(1028)
        par = LS.paragraph_of_line(ms)
        for k in range(K):
            lines, _ = LS.words_in_units(ms, par, srng)
            placed, geom, _ = LS.typeset(ms, frames, lines)
            results['shuffles'].append(analyse(ms, placed, geom, 0))
            print(f'shuffle {k + 1}/{K} done', file=sys.stderr, flush=True)
        (HERE / 'interior_check.json').write_text(json.dumps(results, indent=1, default=float), encoding='utf-8')

    def fmt(r):
        return f"{r['diff']:+.3f} [{r['ci'][0]:+.3f},{r['ci'][1]:+.3f}]" if np.isfinite(r['ci'][0]) else f"{r['diff']:+.3f}"
    first = results['texts']['manuscript (recorded boxes)'][CONFIGS[0]['name']]
    print('Interior words only. interior-1 = not first or last in the line and study pool >= 15 words; interior-2 = interior-1 and not in the')
    print(f"first two lines of the page. Manuscript cohorts (study selector): all {first['all']['n']}, interior-1 {first['interior-1']['n']}, interior-2 {first['interior-2']['n']} targets.")
    print('Within-bifolium quintile contrast of word impact: raw, inside exact length, inside exact length x pool-size tertile.')
    for meas in RC.MEASURES:
        print(f'\n== {meas}')
        for c in CONFIGS:
            print(f"  -- {c['name']}")
            print(f"     {'text':40s} {'cohort':>10s} {'n':>6s} {'raw':>24s} {'inside length':>24s} {'inside length x pool':>26s}")
            for name, r in results['texts'].items():
                for cname in COHORTS:
                    v = r[c['name']][cname]
                    print(f"     {name:40s} {cname:>10s} {v['n']:6d} {fmt(v[meas]['raw']):>24s} {fmt(v[meas]['length']):>24s} {fmt(v[meas]['length_pool']):>26s}")
            sh = results['shuffles']
            if sh:
                for cname in COHORTS:
                    cols = []
                    for part in ('raw', 'length', 'length_pool'):
                        vals = np.array([s[c['name']][cname][meas][part]['diff'] for s in sh], float)
                        msv = results['texts']['manuscript (synthetic boxes)'][c['name']][cname][meas][part]['diff']
                        cols.append(f"{vals.mean():+.3f} ({vals.min():+.3f}..{vals.max():+.3f}) rank {int((vals < msv).sum())}/{len(vals)}")
                    print(f"     {'shuffles (' + str(len(sh)) + ')':40s} {cname:>10s}        " + ' | '.join(cols))


if __name__ == '__main__':
    main()
