"""T14. Direction test for the spatial component-diversity association (28 October; proposed by a reader's Claude).

A copier can only copy what is already written. If the association of section 7 (N is more often a repeat when the
words in view above and to the left of it are less diverse) came from copying off the page, the cone ABOVE N (earlier
text) should predict N's repetition better than the mirror cone BELOW it (later text: the same reach to the right on
N's line and the same cone below). Local bursts of repetition predict both alike. direction_measure.js keeps the
study's selector unchanged and adds its mirror image (same reach, depth, angle, weights and cap; tokens after N only).

On the cohort where both cones are valid (and the 100 containing windows lie inside the bifolium) this script gives,
for each text and region: the within-bifolium quintile contrast of word impact (lowest minus highest diversity
quintile) on each cone's component diversity, H2 and word diversity; the paired difference above minus below with a
bifolium-resampling interval (the two contrasts are read on the same tokens, so their difference needs a paired
interval); the pool-size-stratified contrasts (tertiles of the cone's own size); and two line-position controls,
since a symmetric vertical association could also come from the line-position registers (a cone at a line's start
holds the starts of the lines above): targets interior to their line only, and the contrast averaged inside thirds of
the line, quintiles formed inside each third.

Texts: the manuscript (recorded rectangles; synthetic rectangles; shuffled inside its paragraphs on the recorded
rectangles) and the copiers, each seed with synthetic rectangles: Original Timm and the no-innovator far 0 run with
Timm's page draw, the same two with their draws from the words in view (spatial), and the far 0 configuration with the
innovator in its spatial form. Run from anywhere: python direction_check.py > direction_check.log
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import data as D  # noqa: E402
import component_check as CC  # noqa: E402
from timing import shuffled_within  # noqa: E402

NODE_SCRIPT = HERE / 'direction_measure.js'
rng = np.random.default_rng(28102026)
REGIONS = {'all': None, 'Herbal A': {'1a', '1b', '1.5a', '2a'}, 'Herbal B': {'3b', '3a'}, 'Stars': {'3c', '4c'}, 'Bio': {'4a'}}
MEASURES = ('components', 'h2', 'worddiv')
COPIERS = ('timm', 'noinnov_far0', 'timm_spatial', 'noinnov_spatial', 'far0_spatial')
POS_EDGES = ((-1.0, 1 / 3), (1 / 3, 2 / 3), (2 / 3, 1.5))


def measure(inp):
    with tempfile.TemporaryDirectory() as td:
        pin, pout = Path(td) / 'in.json', Path(td) / 'out.json'
        pin.write_text(json.dumps(inp), encoding='utf-8')
        r = subprocess.run(['node', str(NODE_SCRIPT), str(pin), str(pout)], capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(r.stderr)
        out = json.loads(pout.read_text(encoding='utf-8'))
    return {k: np.array([np.nan if v is None else v for v in vals], dtype=float) for k, vals in out.items()}


def rows_by_bifolium(metric, y, bif, mask):
    """Per bifolium with at least 25 valid tokens: [sum of y in the lowest quintile, its count, sum in the highest, its count]."""
    rows = {}
    for b in np.unique(bif[mask]):
        m = mask & (bif == b) & np.isfinite(metric) & np.isfinite(y)
        if m.sum() < 25:
            continue
        x, yy = metric[m], y[m]
        lo, hi = np.quantile(x, [.2, .8])
        L, H = yy[x <= lo], yy[x >= hi]
        rows[b] = [L.sum(), len(L), H.sum(), len(H)]
    return rows


def contrast(v):
    t = v.sum(0)
    return t[0] / t[1] - t[2] / t[3]


def paired(metric_up, metric_dn, y, bif, mask, reps=2000):
    """Both contrasts on the same tokens and bifolia, and their difference, with one bifolium resampling for all three."""
    ru, rd = rows_by_bifolium(metric_up, y, bif, mask), rows_by_bifolium(metric_dn, y, bif, mask)
    common = sorted(set(ru) & set(rd), key=str)
    nan2 = [float('nan'), float('nan')]
    if len(common) < 3:
        return dict(up=float('nan'), dn=float('nan'), diff=float('nan'), ci_up=nan2, ci_dn=nan2, ci_diff=nan2, bifolia=len(common))
    U = np.array([ru[b] for b in common], float)
    Dn = np.array([rd[b] for b in common], float)
    up, dn = contrast(U), contrast(Dn)
    draw = rng.integers(0, len(common), (reps, len(common)))
    su, sd = U[draw].sum(1), Dn[draw].sum(1)
    ok = (su[:, 1] > 0) & (su[:, 3] > 0) & (sd[:, 1] > 0) & (sd[:, 3] > 0)
    cu = su[ok, 0] / su[ok, 1] - su[ok, 2] / su[ok, 3]
    cd = sd[ok, 0] / sd[ok, 1] - sd[ok, 2] / sd[ok, 3]
    q = lambda a: [float(v) for v in np.quantile(a, [.025, .975])]  # noqa: E731
    return dict(up=float(up), dn=float(dn), diff=float(up - dn), ci_up=q(cu), ci_dn=q(cd), ci_diff=q(cu - cd), bifolia=len(common))


def stratified(metric, size, y, bif, mask, edges):
    """Mean over strata of `size` of the within-bifolium contrast, quintiles formed inside each stratum."""
    parts = []
    for a, b in edges:
        mm = mask & (size > a) & (size <= b)
        rows = rows_by_bifolium(metric, y, bif, mm)
        if len(rows) >= 3:
            parts.append(contrast(np.array(list(rows.values()), float)))
    return float(np.mean(parts)) if parts else float('nan')


def tertile_edges(size, mask):
    q = np.nanpercentile(size[mask], [33, 67])
    return ((-1, q[0]), (q[0], q[1]), (q[1], 1e9))


def analyse(ms, line_words, geometry):
    inp = CC.make_input(ms, line_words, geometry, CC.zattera)
    M = measure(inp)
    node, group, bstart, bend = CC.token_meta(ms, line_words)
    out = CC.outcomes(inp['words'], bstart, bend)
    y = out['app_impact']
    pos = np.concatenate([np.arange(len(ws)) for ws in line_words])
    ln = np.concatenate([np.full(len(ws), len(ws)) for ws in line_words])
    interior = (pos > 0) & (pos < ln - 1)
    rel = np.where(ln > 1, pos / np.maximum(ln - 1, 1), 0.5)
    base = out['full']
    for k in ('up_components', 'up_h2', 'up_worddiv', 'dn_components', 'dn_h2', 'dn_worddiv'):
        base &= np.isfinite(M[k])
    res = dict(tokens=len(inp['words']), cohort=int(base.sum()), mean_impact=float(np.nanmean(y[base])),
               cohort_up_only=int((out['full'] & np.isfinite(M['up_components'])).sum()), regions={})
    for rname, groups in REGIONS.items():
        mask = base if groups is None else base & np.isin(group, list(groups))
        r = dict(n=int(mask.sum()), pool_up=float(np.nanmean(M['up_n'][mask])), pool_dn=float(np.nanmean(M['dn_n'][mask])))
        for m in MEASURES:
            r[m] = paired(M['up_' + m], M['dn_' + m], y, node, mask)
            r[m + '_pool'] = dict(up=stratified(M['up_' + m], M['up_n'], y, node, mask, tertile_edges(M['up_n'], mask)),
                                  dn=stratified(M['dn_' + m], M['dn_n'], y, node, mask, tertile_edges(M['dn_n'], mask)))
        r['components_interior'] = paired(M['up_components'], M['dn_components'], y, node, mask & interior, reps=1000)
        r['components_position'] = dict(up=stratified(M['up_components'], rel, y, node, mask, POS_EDGES),
                                        dn=stratified(M['dn_components'], rel, y, node, mask, POS_EDGES))
        r['worddiv_position'] = dict(up=stratified(M['up_worddiv'], rel, y, node, mask, POS_EDGES),
                                     dn=stratified(M['dn_worddiv'], rel, y, node, mask, POS_EDGES))
        res['regions'][rname] = r
    return res


def agg(per, path):
    vals = []
    for r in per:
        v = r
        for k in path:
            v = v[k]
        vals.append(v)
    return float(np.mean(vals)), float(min(vals)), float(max(vals))


def main():
    ms = D.manuscript()
    app = CC.load_study_app('legacy')
    ms_lines = [L['words'] for L in ms['lines']]
    assert app['words'] == [w for ws in ms_lines for w in ws]
    frames = CC.line_frames(app, ms)
    results = {}

    def run(name, lines, geometry):
        results.setdefault(name, []).append(analyse(ms, lines, geometry))
        print(f'{name} done ({len(results[name])}), cohort {results[name][-1]["cohort"]}', file=sys.stderr, flush=True)

    if '--print' in sys.argv:  # re-print the tables from the saved measurements
        results = json.loads((HERE / 'direction_check.json').read_text(encoding='utf-8'))
    else:
        run('manuscript', ms_lines, app['geometry'])
        syn = [list(ws) for ws in ms_lines]
        run('manuscript_synthetic', syn, CC.synthetic_geometry(syn, frames, ms))
        tok = D.tokenize(ms)
        par = np.cumsum(tok['since_par'] == 0)
        run('manuscript_shuffled_paragraphs', shuffled_within(ms, tok, par), app['geometry'])
        for key in COPIERS:
            for s in D.STREAMS[key][1][:3]:
                lines = D.read_stream(s)
                run(key, lines, CC.synthetic_geometry(lines, frames, ms))
        (HERE / 'direction_check.json').write_text(json.dumps(results, indent=1, default=float), encoding='utf-8')

    names = list(results)
    labels = {'manuscript': 'manuscript (recorded boxes)', 'manuscript_synthetic': 'manuscript (synthetic boxes)',
              'manuscript_shuffled_paragraphs': 'manuscript shuffled in paragraphs', 'timm': 'Original Timm, page draw',
              'noinnov_far0': 'no-innovator far 0, page draw', 'timm_spatial': 'Original Timm, words in view',
              'noinnov_spatial': 'no-innovator far 0, words in view', 'far0_spatial': 'far 0 + innovator, words in view'}

    def cell(name, path, ci_path=None):
        per = results[name]
        m, lo, hi = agg(per, path)
        if len(per) == 1:
            if ci_path:
                ci = per[0]
                for k in ci_path:
                    ci = ci[k]
                return f'{m:+.3f} [{ci[0]:+.3f},{ci[1]:+.3f}]'
            return f'{m:+.3f}'
        return f'{m:+.3f} [{lo:+.3f},{hi:+.3f}]'

    print('Direction test: within-bifolium quintile contrast of word impact (lowest minus highest diversity quintile) on the cone ABOVE N')
    print('(the study selector: left 3, depth 8, 45 degrees, earlier tokens) and on its MIRROR below N (right 3, depth 8 below, later tokens),')
    print('cohort = tokens with both cones valid and the 100 containing windows inside the bifolium. Manuscript rows: 95% bifolium-resampling')
    print('intervals (the difference above minus below is paired). Copier rows: mean over seeds [min, max].')
    for region in REGIONS:
        print(f'\n== region {region}')
        print(f"  {'text':36s} {'n':>6s} {'pool up/dn':>11s}  {'components above':>26s}  {'components below':>26s}  {'above minus below':>26s}  "
              f"{'H2 above':>10s} {'H2 below':>10s}  {'word div above':>14s} {'word div below':>14s}")
        for name in names:
            R = ['regions', region]
            print(f"  {labels.get(name, name):36s} {agg(results[name], R + ['n'])[0]:6.0f} "
                  f"{agg(results[name], R + ['pool_up'])[0]:5.0f}/{agg(results[name], R + ['pool_dn'])[0]:<5.0f}  "
                  f"{cell(name, R + ['components', 'up'], R + ['components', 'ci_up']):>26s}  "
                  f"{cell(name, R + ['components', 'dn'], R + ['components', 'ci_dn']):>26s}  "
                  f"{cell(name, R + ['components', 'diff'], R + ['components', 'ci_diff']):>26s}  "
                  f"{agg(results[name], R + ['h2', 'up'])[0]:+10.3f} {agg(results[name], R + ['h2', 'dn'])[0]:+10.3f}  "
                  f"{agg(results[name], R + ['worddiv', 'up'])[0]:+14.3f} {agg(results[name], R + ['worddiv', 'dn'])[0]:+14.3f}")
    print('\n== region all, controls (mean over seeds): pool-size-stratified contrasts (tertiles of each cone\'s own size); line-position controls')
    print(f"  {'text':36s}  {'comp. pool-strat up/dn':>24s}  {'word div pool-strat up/dn':>26s}  {'comp. interior targets up/dn':>30s}  "
          f"{'comp. in line thirds up/dn':>28s}  {'word div in line thirds up/dn':>30s}")
    for name in names:
        R = ['regions', 'all']
        f = lambda p: agg(results[name], R + p)[0]  # noqa: E731
        inter = results[name][0]['regions']['all']['components_interior']
        ci = f" [{inter['ci_up'][0]:+.3f},{inter['ci_up'][1]:+.3f}] / [{inter['ci_dn'][0]:+.3f},{inter['ci_dn'][1]:+.3f}]" if len(results[name]) == 1 else ''
        print(f"  {labels.get(name, name):36s}  {f(['components_pool', 'up']):+11.3f} /{f(['components_pool', 'dn']):+11.3f}  "
              f"{f(['worddiv_pool', 'up']):+12.3f} /{f(['worddiv_pool', 'dn']):+12.3f}  "
              f"{f(['components_interior', 'up']):+14.3f} /{f(['components_interior', 'dn']):+14.3f}  "
              f"{f(['components_position', 'up']):+13.3f} /{f(['components_position', 'dn']):+13.3f}  "
              f"{f(['worddiv_position', 'up']):+14.3f} /{f(['worddiv_position', 'dn']):+14.3f}{ci}")
    print(f"\ncohorts (region all): " + '; '.join(f"{labels.get(n, n)} {agg(results[n], ['cohort'])[0]:.0f} of {agg(results[n], ['cohort_up_only'])[0]:.0f} with the cone above valid" for n in names))


if __name__ == '__main__':
    main()
