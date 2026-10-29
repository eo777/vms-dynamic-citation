"""T19. Residual association after length AND pool size, for all three measures, against repeated shuffles (28 October, after an
external review of item 9: length_class_check.py controlled N's length but not pool size, scored component diversity only, and
every rearrangement was one realization).

For the study selector (centre distance) and its width-neutral form (gap distance), each of component diversity, H2 and word
diversity is scored against word impact as the within-bifolium quintile contrast (lowest minus highest fifth), (a) raw, (b) with
the quintiles formed inside bifolium x exact word length, (c) inside bifolium x exact length x pool-size tertile. Texts: the
manuscript (recorded and synthetic rectangles), the first seed of three copiers, and K size-matched paragraph shuffles of the
manuscript re-typeset into its frames (layout_shuffles.words_in_units), reported as the shuffle mean, range and the manuscript's
rank among them. Intervals for the manuscript resample bifolia. Run from anywhere: python residual_check.py > residual_check.log
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

K = 19
rng = np.random.default_rng(28102026)
MEASURES = ('components', 'h2', 'worddiv')
SELECTORS = {'centre': SW.cfg('study selector (centre distance)', left=3, depth=8),
             'gap': SW.cfg('study selector, width-neutral (gap distance)', left=3, depth=8, metric='edge')}


def contrast_strata(metric, y, bif, strata, mask, reps=0, min_cell=20):
    """Quintiles formed inside bifolium x stratum; cells under min_cell tokens dropped; pooled contrast, bifolium-resampled CI."""
    rows = {}
    covered = 0
    for b in np.unique(bif[mask]):
        acc = np.zeros(4)
        mb = mask & (bif == b) & np.isfinite(metric) & np.isfinite(y)
        for s in np.unique(strata[mb]):
            m = mb & (strata == s)
            if m.sum() < min_cell:
                continue
            x, yy = metric[m], y[m]
            lo, hi = np.quantile(x, [.2, .8])
            L, H = yy[x <= lo], yy[x >= hi]
            acc += [L.sum(), len(L), H.sum(), len(H)]
            covered += int(m.sum())
        if acc[1] > 0 and acc[3] > 0:
            rows[b] = acc
    if len(rows) < 3:
        return dict(diff=float('nan'), ci=[float('nan')] * 2, covered=covered)
    v = np.array(list(rows.values()), float)
    r = dict(diff=float(DC.contrast(v)), ci=[float('nan')] * 2, covered=covered)
    if reps:
        draw = rng.integers(0, len(v), (reps, len(v)))
        s = v[draw].sum(1)
        ok = (s[:, 1] > 0) & (s[:, 3] > 0)
        bs = s[ok, 0] / s[ok, 1] - s[ok, 2] / s[ok, 3]
        r['ci'] = [float(q) for q in np.quantile(bs, [.025, .975])]
    return r


def analyse(ms, line_words, geometry, reps=0):
    inp = CC.make_input(ms, line_words, geometry, CC.zattera)
    inp['configs'] = list(SELECTORS.values())
    M = SW.measure(inp)
    node, group, bstart, bend = CC.token_meta(ms, line_words)
    out = CC.outcomes(inp['words'], bstart, bend)
    y = out['app_impact']
    length = np.array([len(w) for w in inp['words']])
    res = {}
    for sel, c in SELECTORS.items():
        m = M[c['name']]
        base = out['full'] & np.isfinite(m['components']) & np.isfinite(m['h2']) & np.isfinite(m['worddiv'])
        q = np.nanpercentile(m['n'][base], [33, 67])
        tert = np.digitize(m['n'], q)
        strata_len = np.clip(length, 2, 9)
        strata_both = strata_len * 10 + tert
        r = dict(n=int(base.sum()))
        for meas in MEASURES:
            r[meas] = dict(raw=contrast_strata(m[meas], y, node, np.zeros(len(y), int), base, reps, min_cell=25),
                           length=contrast_strata(m[meas], y, node, strata_len, base, reps),
                           length_pool=contrast_strata(m[meas], y, node, strata_both, base, reps))
        res[sel] = r
    return res


def main():
    ms = D.manuscript()
    app = CC.load_study_app('legacy')
    ms_lines = [L['words'] for L in ms['lines']]
    frames = CC.line_frames(app, ms)
    results = {'texts': {}, 'shuffles': []}
    if '--print' in sys.argv:
        results = json.loads((HERE / 'residual_check.json').read_text(encoding='utf-8'))
    else:
        def run(name, lines, geometry, reps=1000):
            results['texts'][name] = analyse(ms, lines, geometry, reps)
            print(name, 'done', file=sys.stderr, flush=True)
        run('manuscript (recorded boxes)', ms_lines, app['geometry'])
        syn = [list(ws) for ws in ms_lines]
        run('manuscript (synthetic boxes)', syn, CC.synthetic_geometry(syn, frames, ms))
        for key, label in (('timm', 'Original Timm, page draw (seed 1)'), ('timm_spatial', 'Original Timm, words in view (seed 1)'), ('noinnov_spatial', 'no-innovator, words in view (seed 1)')):
            L0 = D.read_stream(D.STREAMS[key][1][0])
            run(label, L0, CC.synthetic_geometry(L0, frames, ms), reps=300)
        srng = np.random.default_rng(1028)
        par = LS.paragraph_of_line(ms)
        for k in range(K):
            lines, _ = LS.words_in_units(ms, par, srng)
            placed, geom, _ = LS.typeset(ms, frames, lines)
            results['shuffles'].append(analyse(ms, placed, geom, reps=0))
            print(f'shuffle {k + 1}/{K} done', file=sys.stderr, flush=True)
        (HERE / 'residual_check.json').write_text(json.dumps(results, indent=1, default=float), encoding='utf-8')

    def fmt(r, ci=True):
        if ci and np.isfinite(r['ci'][0]):
            return f"{r['diff']:+.3f} [{r['ci'][0]:+.3f},{r['ci'][1]:+.3f}]"
        return f"{r['diff']:+.3f}"

    print(f'Within-bifolium quintile contrast of word impact (lowest minus highest fifth of the pool measure); raw, inside exact word length,')
    print(f'inside exact length x pool-size tertile; {K} size-matched paragraph shuffles re-typeset into the frames (mean, min..max; rank = how many')
    print('shuffles the manuscript with synthetic boxes exceeds).')
    for sel, c in SELECTORS.items():
        print(f"\n== {c['name']}")
        for meas in MEASURES:
            print(f"  -- {meas}")
            print(f"     {'text':44s} {'raw':>24s} {'inside length':>24s} {'inside length x pool size':>26s}")
            for name, r in results['texts'].items():
                v = r[sel][meas]
                print(f"     {name:44s} {fmt(v['raw']):>24s} {fmt(v['length']):>24s} {fmt(v['length_pool']):>26s}")
            sh = results['shuffles']
            if sh:
                cols = []
                for part in ('raw', 'length', 'length_pool'):
                    vals = np.array([s[sel][meas][part]['diff'] for s in sh], float)
                    msv = results['texts']['manuscript (synthetic boxes)'][sel][meas][part]['diff']
                    rank = int((vals < msv).sum())
                    cols.append(f"{vals.mean():+.3f} ({vals.min():+.3f}..{vals.max():+.3f}) rank {rank}/{len(vals)}")
                print(f"     {'shuffles (' + str(len(sh)) + ')':44s} " + ' | '.join(cols))


if __name__ == '__main__':
    main()
