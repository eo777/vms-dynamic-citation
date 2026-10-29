"""T17. The association inside exact word-length classes (28 October). The geometry sweep (sweep_check.py) found that the
manuscript's association survives a size-matched shuffle of the whole text and a shuffle of word lengths inside paragraphs,
and vanishes with uniform weights or without the same-line reach. That fits an instrument effect of N's own length: with
inverse-square distance weights, a short N has the centre of its left neighbour closer, so that word dominates the weighted
pool and its component diversity falls; and short words are the frequent ones, so they are repeats more often. If so, the
association must vanish once N's length is held fixed. Here the study selector's component diversity is scored against word
impact with the quintiles formed inside each bifolium AND each exact word length (2 to 9 letters; pooled over lengths), on
the manuscript (recorded and synthetic rectangles), the size-matched whole-manuscript shuffle, and the first seed of
three copiers. Also: the pool weight carried by the left neighbour by N's length, and the raw contrast for comparison.
Run from anywhere: python length_class_check.py > length_class_check.log
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

rng = np.random.default_rng(28102026)


def contrast_within(metric, y, bif, length, mask, reps=1000):
    """Lowest minus highest quintile of `metric`, quintiles formed inside bifolium x exact length, pooled; bifolium-resampled CI."""
    rows = {}
    for b in np.unique(bif[mask]):
        acc = np.zeros(4)
        for ln in range(2, 10):
            m = mask & (bif == b) & (length == ln) & np.isfinite(metric) & np.isfinite(y)
            if m.sum() < 25:
                continue
            x, yy = metric[m], y[m]
            lo, hi = np.quantile(x, [.2, .8])
            L, H = yy[x <= lo], yy[x >= hi]
            acc += [L.sum(), len(L), H.sum(), len(H)]
        if acc[1] > 0 and acc[3] > 0:
            rows[b] = acc
    v = np.array(list(rows.values()), float)
    diff = DC.contrast(v)
    draw = rng.integers(0, len(v), (reps, len(v)))
    s = v[draw].sum(1)
    ok = (s[:, 1] > 0) & (s[:, 3] > 0)
    bs = s[ok, 0] / s[ok, 1] - s[ok, 2] / s[ok, 3]
    return float(diff), [float(q) for q in np.quantile(bs, [.025, .975])], len(rows)


def analyse(ms, line_words, geometry):
    inp = CC.make_input(ms, line_words, geometry, CC.zattera)
    M = CC.measure(inp)
    node, group, bstart, bend = CC.token_meta(ms, line_words)
    out = CC.outcomes(inp['words'], bstart, bend)
    length = np.array([len(w) for w in inp['words']])
    base = out['full'] & np.isfinite(M['components'])
    raw = DC.rows_by_bifolium(M['components'], out['app_impact'], node, base)
    raw_c = DC.contrast(np.array(list(raw.values()), float))
    within, ci, nb = contrast_within(M['components'], out['app_impact'], node, length, base)
    by_len = {}
    for ln in range(2, 10):
        m = base & (length == ln)
        rows = DC.rows_by_bifolium(M['components'], out['app_impact'], node, m)
        by_len[ln] = (DC.contrast(np.array(list(rows.values()), float)) if len(rows) >= 3 else float('nan'), int(m.sum()), float(out['app_impact'][m].mean()) if m.any() else float('nan'), float(np.nanmean(M['components'][m])) if m.any() else float('nan'))
    return dict(n=int(base.sum()), raw=raw_c, within=within, within_ci=ci, bifolia=nb, by_len=by_len)


def main():
    ms = D.manuscript()
    app = CC.load_study_app('legacy')
    ms_lines = [L['words'] for L in ms['lines']]
    frames = CC.line_frames(app, ms)
    texts = [('manuscript (recorded boxes)', ms_lines, app['geometry'])]
    syn = [list(ws) for ws in ms_lines]
    texts.append(('manuscript (synthetic boxes)', syn, CC.synthetic_geometry(syn, frames, ms)))
    srng = np.random.default_rng(1028)
    lines, _ = LS.words_in_units(ms, np.zeros(len(ms['lines']), int), srng)
    placed, geom, _ = LS.typeset(ms, frames, lines)
    texts.append(('words shuffled in whole manuscript (size-matched)', placed, geom))
    for key, label in (('timm', 'Original Timm, page draw (seed 1)'), ('timm_spatial', 'Original Timm, words in view (seed 1)'), ('noinnov_spatial', 'no-innovator, words in view (seed 1)')):
        L0 = D.read_stream(D.STREAMS[key][1][0])
        texts.append((label, L0, CC.synthetic_geometry(L0, frames, ms)))
    results = {}
    print('Study selector (left 3 + 8 lines above, 45 degrees, distance weights), component diversity -> word impact, lowest minus highest quintile:')
    print(f"  {'text':52s} {'n':>6s} {'raw (within bifolium)':>22s} {'within bifolium x exact length':>32s}")
    for name, lines, geometry in texts:
        r = analyse(ms, lines, geometry)
        results[name] = r
        print(f"  {name:52s} {r['n']:6d} {r['raw']:+22.3f} {r['within']:+.3f} [{r['within_ci'][0]:+.3f},{r['within_ci'][1]:+.3f}] ({r['bifolia']} bifolia)".replace('] (', ']  ('), flush=True)
    print('\nBy exact length of N (manuscript, recorded boxes): contrast within bifolium, tokens, mean word impact, mean pool component diversity')
    for ln, (c, n, imp, comp) in results['manuscript (recorded boxes)']['by_len'].items():
        print(f"  length {ln}: {c:+.3f}  n={n:5d}  impact {imp:.3f}  pool diversity {comp:.2f}")
    print('\nBy exact length of N (Original Timm, words in view): contrast within bifolium, tokens, mean word impact, mean pool component diversity')
    for ln, (c, n, imp, comp) in results['Original Timm, words in view (seed 1)']['by_len'].items():
        print(f"  length {ln}: {c:+.3f}  n={n:5d}  impact {imp:.3f}  pool diversity {comp:.2f}")
    (HERE / 'length_class_check.json').write_text(json.dumps(results, indent=1, default=float), encoding='utf-8')


if __name__ == '__main__':
    main()
