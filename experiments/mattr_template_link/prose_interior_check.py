"""T23. Natural prose on the interior cohorts of interior_check.py (28 October): the five historical texts cut into the manuscript's
lines (letters as units), recorded rectangles and re-typeset, scored on all words and on interior words (not first or last in the
line, study pool of 15 words or more) for the study selector, the lines above only, the lines below only and the mirror; raw,
inside exact length, inside exact length x pool-size tertile. Run from anywhere: python prose_interior_check.py > prose_interior_check.log
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import data as D  # noqa: E402
import component_check as CC  # noqa: E402
import interior_check as IC  # noqa: E402
import residual_check as RC  # noqa: E402
from decompose import REFS, ref_words  # noqa: E402
from timing import laid_in  # noqa: E402


def main():
    ms = D.manuscript()
    app = CC.load_study_app('legacy')
    flags = CC.oversized_flags(app, ms)
    clean = [None if flags[i] else g for i, g in enumerate(app['geometry'])]
    frames = CC.line_frames(app, ms)
    page_sizes = [sum(len(ms['lines'][l]['words']) for l in range(p['start_line'], p['end_line'])) for p in ms['pages']]
    results = {}
    for key in CC.PROSE:
        words = ref_words(REFS[key])
        if len(words) < sum(page_sizes) + 10:
            continue
        lines = laid_in(ms, words, page_sizes)
        results[key + ' (recorded)'] = IC.analyse(ms, lines, clean, 300, comp_fn=lambda w: list(w))
        syn = [list(ws) for ws in lines]
        geom = CC.synthetic_geometry(syn, frames, ms)
        results[key + ' (re-typeset)'] = IC.analyse(ms, syn, geom, 300, comp_fn=lambda w: list(w))
        print(key, 'done', file=sys.stderr, flush=True)
    (HERE / 'prose_interior_check.json').write_text(json.dumps(results, indent=1, default=float), encoding='utf-8')

    def fmt(r):
        return f"{r['diff']:+.3f} [{r['ci'][0]:+.3f},{r['ci'][1]:+.3f}]" if np.isfinite(r['ci'][0]) else f"{r['diff']:+.3f}"
    print('Natural prose, all words and interior words (not first or last in the line, study pool >= 15): within-bifolium quintile contrast')
    print('of word impact; raw, inside exact length, inside exact length x pool-size tertile.')
    for meas in RC.MEASURES:
        print(f'\n== {meas}')
        for c in IC.CONFIGS:
            print(f"  -- {c['name']}")
            print(f"     {'text':44s} {'cohort':>10s} {'n':>6s} {'raw':>24s} {'inside length':>24s} {'inside length x pool':>26s}")
            for name, r in results.items():
                for cname in ('all', 'interior-1'):
                    v = r[c['name']][cname]
                    print(f"     {name:44s} {cname:>10s} {v['n']:6d} {fmt(v[meas]['raw']):>24s} {fmt(v[meas]['length']):>24s} {fmt(v[meas]['length_pool']):>26s}")


if __name__ == '__main__':
    main()
