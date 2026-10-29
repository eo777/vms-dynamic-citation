"""T16. Geometry sweep: where does the spatial association come from? (28 October, user's request)

The study selector pools the three words to the left of N on its line and a cone 8 line spacings deep with a 45-degree
half-angle above it, weighted by inverse squared distance. This script maps the signal instead of cutting it once: the
same-line reach varied with the full cone (left 0, 1, 2, 3, 5), the depth varied with the study reach (0 to 8 lines), the
study selector and its mirror with UNIFORM weights (so the same-line words count by number, not by distance), pools of the
other lines only (depths 2 to 8 above and below, half-angles 15 to 89 degrees, cones whose apex is displaced 1 or 3 word
widths left or right of N), and same-line-only pools (left or right 1 to 5 words). Every shape is scored on one cohort
with two predictors (component diversity, which the study's rules leave undefined for pools under five pair-bearing words,
and word diversity, defined for any pool) and two outcomes (the study word impact, a twin anywhere in the 100-token
windows; repeat_out, a twin within 99 tokens outside the pool), as within-bifolium quintile contrasts of the lowest minus
the highest diversity fifth and at fixed pool size (tertiles).
Texts: the manuscript (recorded rectangles), and the rearrangements of layout_shuffles.py, every one re-typeset into the
manuscript's own line frames (the manuscript itself with synthetic boxes; words permuted among words of the same length
inside paragraphs and inside pages; the words of each line permuted; each line reversed; each line rotated by its index so
columns become diagonals; whole lines permuted inside paragraphs and inside pages with the letter size fitted to the slot),
and the first seed of three copiers (Original Timm with his page draw, Original Timm and the no-innovator run with their
words from the view; synthetic rectangles). shuffle_layout_check.py reports the typesetting of the rearrangements.
Run from anywhere: python sweep_check.py > sweep_check.log
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
import direction_check as DC  # noqa: E402
import layout_shuffles as LS  # noqa: E402

NODE_SCRIPT = HERE / 'sweep_measure.js'
rng = np.random.default_rng(28102026)
PREDICTORS = ('components', 'worddiv')
OUTCOMES = ('impact', 'repeat_out')


def cfg(name, dir='up', left=0, right=0, depth=0, angle=45, offset=0, weight='distance', metric='centre'):
    return dict(name=name, dir=dir, left=left, right=right, depth=depth, angle=angle, offset=offset, weight=weight, metric=metric)


CONFIGS = [
    cfg('study selector: left 3 + 8 lines above, 45', left=3, depth=8),
    cfg('mirror: right 3 + 8 lines below, 45', dir='down', right=3, depth=8),
    cfg('study selector, UNIFORM weights', left=3, depth=8, weight='uniform'),
    cfg('mirror, UNIFORM weights', dir='down', right=3, depth=8, weight='uniform'),
    cfg('left 0 + 8 lines above (other lines only)', depth=8),
    cfg('left 1 + 8 lines above', left=1, depth=8),
    cfg('left 2 + 8 lines above', left=2, depth=8),
    cfg('left 5 + 8 lines above', left=5, depth=8),
    cfg('left 3 + 0 lines (same line only)', left=3),
    cfg('left 3 + 1 line above', left=3, depth=1),
    cfg('left 3 + 2 lines above', left=3, depth=2),
    cfg('left 3 + 3 lines above', left=3, depth=3),
    cfg('left 3 + 5 lines above', left=3, depth=5),
    *[cfg(f'same line only: left {k}', left=k) for k in (1, 2, 5)],
    *[cfg(f'same line only: right {k}', dir='down', right=k) for k in (1, 2, 3, 5)],
    *[cfg(f'lines above only: depth {dd}, 45', depth=dd) for dd in (2, 3, 5)],
    *[cfg(f'lines below only: depth {dd}, 45', dir='down', depth=dd) for dd in (3, 8)],
    *[cfg(f'lines above only: depth 8, angle {a}', depth=8, angle=a) for a in (15, 30, 60, 89)],
    *[cfg(f'lines above only: depth 3, 45, apex {o:+d} words', depth=3, offset=o) for o in (-3, -1, 1, 3)],
    *[cfg(f'lines above only: depth 8, 45, apex {o:+d} words', depth=8, offset=o) for o in (-3, 3)],
]

LABELS = {'manuscript': 'MS rec', 'manuscript (synthetic boxes)': 'MS syn', 'words shuffled in paragraphs (size-matched)': 'w-par',
          'words shuffled in pages (size-matched)': 'w-page', 'words shuffled in bifolia (size-matched)': 'w-bif',
          'words shuffled in whole manuscript (size-matched)': 'w-all', 'words shuffled in paragraphs (any length, fitted letter size)': 'w-par-any',
          'words shuffled in lines': 'w-line', 'lines reversed': 'rev',
          'lines rotated (diagonal)': 'rot', 'lines shuffled in paragraphs (fitted letter size)': 'l-par',
          'lines shuffled in pages (fitted letter size)': 'l-page', 'Timm page draw s1': 'Timm pg', 'Timm in view s1': 'Timm view',
          'no-innov in view s1': 'noinn view'}


def measure(inp):
    with tempfile.TemporaryDirectory() as td:
        pin, pout = Path(td) / 'in.json', Path(td) / 'out.json'
        pin.write_text(json.dumps(inp), encoding='utf-8')
        r = subprocess.run(['node', str(NODE_SCRIPT), str(pin), str(pout)], capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(r.stderr)
        out = json.loads(pout.read_text(encoding='utf-8'))
    res = {}
    for name, v in out.items():
        res[name] = dict(components=np.array([np.nan if x is None else x for x in v['components']], float),
                         worddiv=np.array([np.nan if x is None else x for x in v['worddiv']], float),
                         n=np.array(v['n'], float), repeat_out=np.array(v['repeat_out'], float))
    return res


def contrast_ci(metric, y, bif, mask, reps):
    rows = DC.rows_by_bifolium(metric, y, bif, mask)
    if len(rows) < 3:
        return dict(diff=float('nan'), ci=[float('nan'), float('nan')])
    v = np.array(list(rows.values()), float)
    diff = DC.contrast(v)
    ci = [float('nan'), float('nan')]
    if reps:
        draw = rng.integers(0, len(v), (reps, len(v)))
        s = v[draw].sum(1)
        ok = (s[:, 1] > 0) & (s[:, 3] > 0)
        bs = s[ok, 0] / s[ok, 1] - s[ok, 2] / s[ok, 3]
        ci = [float(x) for x in np.quantile(bs, [.025, .975])]
    return dict(diff=float(diff), ci=ci)


def analyse(ms, line_words, geometry, reps):
    inp = CC.make_input(ms, line_words, geometry, CC.zattera)
    inp['configs'] = CONFIGS
    M = measure(inp)
    node, group, bstart, bend = CC.token_meta(ms, line_words)
    out = CC.outcomes(inp['words'], bstart, bend)
    base = out['full'] & np.isfinite(M[CONFIGS[0]['name']]['components'])
    res = dict(cohort=int(base.sum()), configs={})
    for c in CONFIGS:
        m = M[c['name']]
        ys = dict(impact=out['app_impact'], repeat_out=m['repeat_out'])
        r = {}
        for pred in PREDICTORS:
            mask = base & np.isfinite(m[pred])
            rp = dict(n=int(mask.sum()), pool=float(np.nanmean(m['n'][mask])) if mask.any() else float('nan'))
            for o in OUTCOMES:
                rp[o] = contrast_ci(m[pred], ys[o], node, mask, reps)
                rp[o + '_pool'] = DC.stratified(m[pred], m['n'], ys[o], node, mask, DC.tertile_edges(m['n'], mask)) if mask.sum() >= 100 else float('nan')
            r[pred] = rp
        res['configs'][c['name']] = r
    return res


def main():
    ms = D.manuscript()
    app = CC.load_study_app('legacy')
    ms_lines = [L['words'] for L in ms['lines']]
    frames = CC.line_frames(app, ms)
    results = {}
    if '--print' in sys.argv:
        results = json.loads((HERE / 'sweep_check.json').read_text(encoding='utf-8'))
    else:
        def run(name, lines, geometry, reps=0):
            results[name] = analyse(ms, lines, geometry, reps)
            print(f'{name} done, cohort {results[name]["cohort"]}', file=sys.stderr, flush=True)
        run('manuscript', ms_lines, app['geometry'], reps=500)
        for name, v in LS.variants(ms, frames).items():
            run(name, v['lines'], v['geometry'])
        for key, label in (('timm', 'Timm page draw s1'), ('timm_spatial', 'Timm in view s1'), ('noinnov_spatial', 'no-innov in view s1')):
            lines = D.read_stream(D.STREAMS[key][1][0])
            run(label, lines, CC.synthetic_geometry(lines, frames, ms))
        (HERE / 'sweep_check.json').write_text(json.dumps(results, indent=1, default=float), encoding='utf-8')

    texts = list(results)
    W = 44
    print('Geometry sweep: within-bifolium quintile contrast (lowest minus highest diversity fifth) for pool shapes; cohort = tokens with the')
    print('study selector valid and the 100 containing windows inside the bifolium; a pool shape\'s row uses the tokens where its predictor is')
    print('defined (component diversity needs five pair-bearing words in the pool; word diversity any pool). MS rec with a 95% interval.')
    print('Columns: ' + '; '.join(f'{LABELS.get(t, t)} = {t}' for t in texts))
    tables = [('components', 'impact', False, 'A. component diversity -> study word impact'),
              ('worddiv', 'impact', False, 'B. word diversity -> study word impact'),
              ('components', 'repeat_out', False, 'C. component diversity -> repeat outside the pool'),
              ('worddiv', 'repeat_out', False, 'D. word diversity -> repeat outside the pool'),
              ('components', 'impact', True, 'E. component diversity -> word impact, at fixed pool size'),
              ('worddiv', 'impact', True, 'F. word diversity -> word impact, at fixed pool size'),
              ('worddiv', 'repeat_out', True, 'G. word diversity -> repeat outside the pool, at fixed pool size')]
    for pred, o, pooled, title in tables:
        print(f'\n== {title}')
        print(f"  {'pool shape':{W}s} {'n':>6s} {'pool':>5s} {'MS rec':>24s} " + ' '.join(f'{LABELS.get(t, t):>10s}' for t in texts[1:]))
        for c in CONFIGS:
            nm = c['name']
            cells = []
            for t in texts:
                r = results[t]['configs'][nm][pred]
                v = r[o + '_pool'] if pooled else r[o]['diff']
                if t == 'manuscript':
                    cells.append((f'{v:+.3f}' if pooled else f"{v:+.3f} [{r[o]['ci'][0]:+.3f},{r[o]['ci'][1]:+.3f}]").rjust(24))
                else:
                    cells.append(f'{v:+.3f}'.rjust(10))
            r0 = results['manuscript']['configs'][nm][pred]
            print(f"  {nm:{W}s} {r0['n']:6d} {r0['pool']:5.1f} " + ' '.join(cells))


if __name__ == '__main__':
    main()
