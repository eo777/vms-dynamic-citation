"""T15. What the spatial-cone statistic responds to (27 October).

The section 7 statistic (lowest-against-highest quintile of the diversity of the words in view, difference in word
impact) is taken apart on controls that isolate its inputs:
  - pool size: word diversity rises with the number of words the cone holds (Spearman +0.8 in every text), and pool
    size itself predicts repetition (small pools at the top of a page carry fewer repeats in the manuscript), so the
    contrast is also computed inside pool-size tertiles;
  - order against bag: the manuscript with its words shuffled inside each paragraph, and inside each page, under
    the recorded rectangles (same word counts per line); an association that survives the paragraph shuffle is a
    property of which words a paragraph uses, one that vanishes is a property of their order;
  - geometry: natural prose in the one-word-per-box reflow under the recorded rectangles (geometry unrelated to the
    prose words) and under synthetic rectangles proportional to the prose words' lengths;
  - controls with no layout dependence: the whole-manuscript and the by-group bigram chains of layout_controls.py.
Outcome: word impact, as in section 7. Quintiles within bifolium; cohort as in section 7; 200 bootstrap draws.
"""
import gzip
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import data as D
import component_check as CC
import layout_controls as LC
from decompose import REFS, ref_words
from timing import shuffled_within

LC.rng = np.random.default_rng(15)
letters = lambda w: list(w)


def main():
    ms = D.manuscript()
    app = json.load(gzip.open(CC.APP, 'rt', encoding='utf8'))
    frames = CC.line_frames(app, ms)
    flags = CC.oversized_flags(app, ms)
    clean = [None if flags[i] else g for i, g in enumerate(app['geometry'])]
    tok = D.tokenize(ms)
    ms_lines = [L['words'] for L in ms['lines']]
    par_id = np.cumsum(tok['since_par'] == 0)
    texts = [('manuscript, recorded boxes', ms_lines, app['geometry'], CC.zattera),
             ('manuscript shuffled within paragraphs', shuffled_within(ms, tok, par_id), app['geometry'], CC.zattera),
             ('manuscript shuffled within pages', shuffled_within(ms, tok, tok['page']), app['geometry'], CC.zattera)]
    for key in ('timm', 'noinnov_far0', 'timm_spatial', 'noinnov_spatial', 'far0_spatial', 'far0', 'buffer', 'pool'):    # noinnov_far0 and the two spatial-source copiers added 27 October
        lines = D.read_stream(D.STREAMS[key][1][0])
        texts.append((key + ' (synthetic boxes)', lines, CC.synthetic_geometry(lines, frames, ms), CC.zattera))
    texts.append(('bigram whole (recorded boxes)', LC.bigram_whole(ms), clean, CC.zattera))
    texts.append(('bigram by Currier language (recorded boxes)', LC.markov_text(ms, 'currier'), clean, CC.zattera))
    texts.append(('bigram by section (recorded boxes)', LC.markov_text(ms, 'section'), clean, CC.zattera))
    words = ref_words(REFS['la_galen_simplicium'])
    box = []
    at = 1000
    for L in ms['lines']:
        n = len(L['words'])
        box.append(words[at:at + n])
        at += n
    texts.append(('Galen, box reflow, recorded boxes', box, clean, letters))
    texts.append(('Galen, box reflow, synthetic boxes', box, CC.synthetic_geometry(box, frames, ms), letters))

    res = {}
    print(f"{'text':40s} {'worddiv':>8s} {'comp':>8s} {'pool n':>8s} | word diversity inside pool-size tertiles (small, mid, large) = mean | components inside tertiles = mean | Bio, word diversity inside tertiles = mean")
    for label, lines, geom, comp in texts:
        inp = CC.make_input(ms, lines, geom, comp)
        meas = CC.measure(inp)
        node, group, bstart, bend = CC.token_meta(ms, lines)
        out = CC.outcomes(inp['words'], bstart, bend)
        base = out['full'] & np.isfinite(meas['components'])

        def strata(metric, mask):
            q = np.nanpercentile(meas['n'][mask], [33, 67])
            parts = []
            for lo, hi in ((-1, q[0]), (q[0], q[1]), (q[1], 1e9)):
                m = mask & (meas['n'] > lo) & (meas['n'] <= hi)
                parts.append(CC.quintile_contrast(metric, out['app_impact'], node, m, reps=200)['diff'])
            return parts

        wd = CC.quintile_contrast(meas['worddiv'], out['app_impact'], node, base, reps=200)['diff']
        cp = CC.quintile_contrast(meas['components'], out['app_impact'], node, base, reps=200)['diff']
        nn = CC.quintile_contrast(meas['n'], out['app_impact'], node, base, reps=200)['diff']
        sw = strata(meas['worddiv'], base)
        sc = strata(meas['components'], base)
        sb = strata(meas['worddiv'], base & (group == '4a'))
        res[label] = dict(worddiv=wd, components=cp, pool_size=nn, worddiv_by_pool_size=sw, components_by_pool_size=sc, bio_worddiv_by_pool_size=sb,
                          worddiv_by_pool_size_mean=float(np.mean(sw)), components_by_pool_size_mean=float(np.mean(sc)), bio_worddiv_by_pool_size_mean=float(np.mean(sb)))
        print(f"{label:40s} {wd:+8.3f} {cp:+8.3f} {nn:+8.3f} | " + ' '.join(f'{v:+.3f}' for v in sw) + f" = {np.mean(sw):+.3f} | " + ' '.join(f'{v:+.3f}' for v in sc) + f" = {np.mean(sc):+.3f} | " + ' '.join(f'{v:+.3f}' for v in sb) + f" = {np.mean(sb):+.3f}", flush=True)
    (HERE / 'component_strata.json').write_text(json.dumps(res, indent=1, default=float), encoding='utf-8')


if __name__ == '__main__':
    main()
