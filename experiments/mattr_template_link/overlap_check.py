"""T15. Overlap test for the spatial component-diversity association (28 October, user's request).

In the study selector the heaviest weights fall on the three words to the left of N on its own line and on the words right
above, and the word-impact outcome counts a twin of N anywhere in the 100-token windows around it, the same line included.
So predictor and outcome can read the same handful of words: a line written from few forms gives both a monotonous view and
a repeat. This script removes that overlap in two steps and asks what is left.
  (1) The cone has no same-line reach (overlap_measure.js: left 0): it holds words on other lines only, 8 line spacings
      deep, 45 degrees, tokens before N (and its mirror below N, tokens after N).
  (2) N counts as a repeat only against words OUTSIDE the cone: another token of N's spelling within 99 tokens before or
      after N whose index is not in N's cone ("repeat outside cone"); a stricter column also ignores twins on N's own line
      ("repeat outside cone and line"). The study's word impact is kept as a reference column.
Within-bifolium quintile contrasts (lowest minus highest component-diversity fifth) on the cohort where both cones are valid and
the 100 containing windows lie inside the bifolium; the paired difference above minus below with a bifolium-resampling
interval; the pool-size-stratified version (tertiles of the cone's own size). Texts: the manuscript (recorded rectangles),
the manuscript shuffled inside its paragraphs, and the five copiers of direction_check.py, every seed, synthetic rectangles.
If the association survives (1) and (2), the lines above N carry information about N beyond N's own line; if it collapses, it
was the overlap, and says nothing about what was in view. Run from anywhere: python overlap_check.py > overlap_check.log
"""
import json
import subprocess
import sys
import tempfile
from bisect import bisect_left, bisect_right
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import data as D  # noqa: E402
import component_check as CC  # noqa: E402
import direction_check as DC  # noqa: E402
from timing import shuffled_within  # noqa: E402

NODE_SCRIPT = HERE / 'overlap_measure.js'
rng = np.random.default_rng(28102026)
REGIONS = DC.REGIONS
COPIERS = DC.COPIERS
OUTCOMES = ('app_impact', 'repeat_out', 'repeat_out_line')


def measure(inp):
    with tempfile.TemporaryDirectory() as td:
        pin, pout = Path(td) / 'in.json', Path(td) / 'out.json'
        pin.write_text(json.dumps(inp), encoding='utf-8')
        r = subprocess.run(['node', str(NODE_SCRIPT), str(pin), str(pout)], capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(r.stderr)
        out = json.loads(pout.read_text(encoding='utf-8'))
    M = {k: np.array([np.nan if v is None else v for v in vals], dtype=float) for k, vals in out.items() if not k.endswith('_idx')}
    M['up_idx'], M['dn_idx'] = out['up_idx'], out['dn_idx']
    return M


def repeat_outside(words, line_of, cone_idx, exclude_line):
    """1 if another token of N's spelling lies within 99 tokens before or after N, outside N's cone (and, if asked, off N's line)."""
    positions = defaultdict(list)
    for i, w in enumerate(words):
        positions[w].append(i)
    out = np.zeros(len(words))
    for i, w in enumerate(words):
        P = positions[w]
        if len(P) == 1:
            continue
        cone = set(cone_idx[i]) if cone_idx[i] else set()
        for j in P[bisect_left(P, i - 99):bisect_right(P, i + 99)]:
            if j == i or j in cone or (exclude_line and line_of[j] == line_of[i]):
                continue
            out[i] = 1.0
            break
    return out


def paired2(metric_up, y_up, metric_dn, y_dn, bif, mask, reps=2000):
    """DC.paired with a separate outcome for each cone (each outcome excludes its own cone's words)."""
    ru, rd = DC.rows_by_bifolium(metric_up, y_up, bif, mask), DC.rows_by_bifolium(metric_dn, y_dn, bif, mask)
    common = sorted(set(ru) & set(rd), key=str)
    nan2 = [float('nan'), float('nan')]
    if len(common) < 3:
        return dict(up=float('nan'), dn=float('nan'), diff=float('nan'), ci_up=nan2, ci_dn=nan2, ci_diff=nan2, bifolia=len(common))
    U = np.array([ru[b] for b in common], float)
    Dn = np.array([rd[b] for b in common], float)
    up, dn = DC.contrast(U), DC.contrast(Dn)
    draw = rng.integers(0, len(common), (reps, len(common)))
    su, sd = U[draw].sum(1), Dn[draw].sum(1)
    ok = (su[:, 1] > 0) & (su[:, 3] > 0) & (sd[:, 1] > 0) & (sd[:, 3] > 0)
    cu = su[ok, 0] / su[ok, 1] - su[ok, 2] / su[ok, 3]
    cd = sd[ok, 0] / sd[ok, 1] - sd[ok, 2] / sd[ok, 3]
    q = lambda a: [float(v) for v in np.quantile(a, [.025, .975])]  # noqa: E731
    return dict(up=float(up), dn=float(dn), diff=float(up - dn), ci_up=q(cu), ci_dn=q(cd), ci_diff=q(cu - cd), bifolia=len(common))


def analyse(ms, line_words, geometry):
    inp = CC.make_input(ms, line_words, geometry, CC.zattera)
    M = measure(inp)
    words = inp['words']
    node, group, bstart, bend = CC.token_meta(ms, line_words)
    out = CC.outcomes(words, bstart, bend)
    line_of = np.concatenate([np.full(len(ws), k) for k, ws in enumerate(line_words)])
    y = {'up': {'app_impact': out['app_impact'], 'repeat_out': repeat_outside(words, line_of, M['up_idx'], False),
                'repeat_out_line': repeat_outside(words, line_of, M['up_idx'], True)},
         'dn': {'app_impact': out['app_impact'], 'repeat_out': repeat_outside(words, line_of, M['dn_idx'], False),
                'repeat_out_line': repeat_outside(words, line_of, M['dn_idx'], True)}}
    base = out['full'] & np.isfinite(M['up_components']) & np.isfinite(M['dn_components'])
    res = dict(tokens=len(words), cohort=int(base.sum()), regions={},
               mean=dict((o, float(np.nanmean(y['up'][o][base]))) for o in OUTCOMES))
    for rname, groups in REGIONS.items():
        mask = base if groups is None else base & np.isin(group, list(groups))
        r = dict(n=int(mask.sum()), pool_up=float(np.nanmean(M['up_n'][mask])), pool_dn=float(np.nanmean(M['dn_n'][mask])))
        for o in OUTCOMES:
            r[o] = paired2(M['up_components'], y['up'][o], M['dn_components'], y['dn'][o], node, mask)
            r[o + '_pool'] = dict(up=DC.stratified(M['up_components'], M['up_n'], y['up'][o], node, mask, DC.tertile_edges(M['up_n'], mask)),
                                  dn=DC.stratified(M['dn_components'], M['dn_n'], y['dn'][o], node, mask, DC.tertile_edges(M['dn_n'], mask)))
        r['worddiv_repeat_out'] = paired2(M['up_worddiv'], y['up']['repeat_out'], M['dn_worddiv'], y['dn']['repeat_out'], node, mask, reps=500)
        res['regions'][rname] = r
    return res


def main():
    ms = D.manuscript()
    app = CC.load_study_app('legacy')
    ms_lines = [L['words'] for L in ms['lines']]
    frames = CC.line_frames(app, ms)
    results = {}

    def run(name, lines, geometry):
        results.setdefault(name, []).append(analyse(ms, lines, geometry))
        print(f'{name} done ({len(results[name])}), cohort {results[name][-1]["cohort"]}', file=sys.stderr, flush=True)

    if '--print' in sys.argv:
        results = json.loads((HERE / 'overlap_check.json').read_text(encoding='utf-8'))
    else:
        run('manuscript', ms_lines, app['geometry'])
        tok = D.tokenize(ms)
        run('manuscript_shuffled_paragraphs', shuffled_within(ms, tok, np.cumsum(tok['since_par'] == 0)), app['geometry'])
        for key in COPIERS:
            for s in D.STREAMS[key][1][:3]:
                lines = D.read_stream(s)
                run(key, lines, CC.synthetic_geometry(lines, frames, ms))
        (HERE / 'overlap_check.json').write_text(json.dumps(results, indent=1, default=float), encoding='utf-8')

    labels = {'manuscript': 'manuscript (recorded boxes)', 'manuscript_shuffled_paragraphs': 'manuscript shuffled in paragraphs',
              'timm': 'Original Timm, page draw', 'noinnov_far0': 'no-innovator far 0, page draw', 'timm_spatial': 'Original Timm, words in view',
              'noinnov_spatial': 'no-innovator far 0, words in view', 'far0_spatial': 'far 0 + innovator, words in view'}

    def cell(name, path, ci_path):
        per = results[name]
        m, lo, hi = DC.agg(per, path)
        if len(per) == 1:
            ci = per[0]
            for k in ci_path:
                ci = ci[k]
            return f'{m:+.3f} [{ci[0]:+.3f},{ci[1]:+.3f}]'
        return f'{m:+.3f} [{lo:+.3f},{hi:+.3f}]'

    print('Overlap test: the cone WITHOUT same-line reach (words on other lines only; depth 8, 45 degrees) above N and mirrored below N;')
    print('within-bifolium quintile contrast (lowest minus highest component-diversity fifth) of three outcomes: the study word impact (twins')
    print('anywhere in the 100-token windows), repeat outside cone (a twin within 99 tokens not in the cone), repeat outside cone and line (also')
    print('not on N\'s line). Manuscript rows: 95% bifolium-resampling intervals; copier rows: mean over seeds [min, max].')
    for region in ('all', 'Herbal A', 'Herbal B', 'Stars', 'Bio'):
        print(f'\n== region {region}')
        print(f"  {'text':34s} {'n':>6s} {'pool':>5s} | {'word impact, above':>22s} {'below':>22s} | {'repeat outside cone, above':>26s} {'below':>22s} "
              f"{'above minus below':>22s} | {'outside cone+line, above':>24s} {'below':>22s}")
        for name in results:
            R = ['regions', region]
            print(f"  {labels.get(name, name):34s} {DC.agg(results[name], R + ['n'])[0]:6.0f} {DC.agg(results[name], R + ['pool_up'])[0]:5.0f} | "
                  f"{cell(name, R + ['app_impact', 'up'], R + ['app_impact', 'ci_up']):>22s} {cell(name, R + ['app_impact', 'dn'], R + ['app_impact', 'ci_dn']):>22s} | "
                  f"{cell(name, R + ['repeat_out', 'up'], R + ['repeat_out', 'ci_up']):>26s} {cell(name, R + ['repeat_out', 'dn'], R + ['repeat_out', 'ci_dn']):>22s} "
                  f"{cell(name, R + ['repeat_out', 'diff'], R + ['repeat_out', 'ci_diff']):>22s} | "
                  f"{cell(name, R + ['repeat_out_line', 'up'], R + ['repeat_out_line', 'ci_up']):>24s} {cell(name, R + ['repeat_out_line', 'dn'], R + ['repeat_out_line', 'ci_dn']):>22s}")
    print('\n== region all: pool-size-stratified contrasts (tertiles of the cone\'s own size), above / below; word diversity -> repeat outside cone; mean outcomes')
    for name in results:
        R = ['regions', 'all']
        f = lambda p: DC.agg(results[name], R + p)[0]  # noqa: E731
        mean = results[name][0]['mean']
        print(f"  {labels.get(name, name):34s} word impact {f(['app_impact_pool', 'up']):+.3f} / {f(['app_impact_pool', 'dn']):+.3f}; "
              f"repeat outside cone {f(['repeat_out_pool', 'up']):+.3f} / {f(['repeat_out_pool', 'dn']):+.3f}; "
              f"outside cone+line {f(['repeat_out_line_pool', 'up']):+.3f} / {f(['repeat_out_line_pool', 'dn']):+.3f}; "
              f"word div -> repeat outside cone {f(['worddiv_repeat_out', 'up']):+.3f} / {f(['worddiv_repeat_out', 'dn']):+.3f}; "
              f"means: impact {mean['app_impact']:.3f}, repeat outside cone {mean['repeat_out']:.3f}, outside cone+line {mean['repeat_out_line']:.3f}")


if __name__ == '__main__':
    main()
