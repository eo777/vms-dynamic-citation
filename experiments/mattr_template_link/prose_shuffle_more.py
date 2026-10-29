"""T24b. More shuffles for the two cleanest prose texts (28 October): the Rhazes text beat its nine shuffles and the Galen text did
not; with five texts and nine shuffles each, one text above its range is within chance. Here Rhazes and Galen are each compared with
30 size-matched paragraph shuffles on the interior cut, lines above only, joint control (components and H2).
Run from anywhere: python prose_shuffle_more.py > prose_shuffle_more.log
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
import interior_check as IC  # noqa: E402
import layout_shuffles as LS  # noqa: E402
from prose_shuffle_check import size_matched_shuffle  # noqa: E402
from decompose import REFS, ref_words  # noqa: E402
from timing import laid_in  # noqa: E402

K = 30
TEXTS = ('la_rhazes_almansor', 'la_galen_simplicium')
IC.CONFIGS = [SW.cfg('lines above only (8)', depth=8)]


def main():
    ms = D.manuscript()
    app = CC.load_study_app('legacy')
    frames = CC.line_frames(app, ms)
    page_sizes = [sum(len(ms['lines'][l]['words']) for l in range(p['start_line'], p['end_line'])) for p in ms['pages']]
    par = LS.paragraph_of_line(ms)
    letters = lambda w: list(w)  # noqa: E731
    results = {}
    for key in TEXTS:
        lines = laid_in(ms, ref_words(REFS[key]), page_sizes)
        syn = [list(ws) for ws in lines]
        observed = IC.analyse(ms, syn, CC.synthetic_geometry(syn, frames, ms), 500, comp_fn=letters)
        rng = np.random.default_rng(2028)
        shuffles = []
        for k in range(K):
            sh = size_matched_shuffle(lines, par, rng)
            placed, geom, _ = LS.typeset(ms, frames, sh)
            shuffles.append(IC.analyse(ms, placed, geom, 0, comp_fn=letters))
            print(key, 'shuffle', k + 1, file=sys.stderr, flush=True)
        results[key] = dict(observed=observed, shuffles=shuffles)
    (HERE / 'prose_shuffle_more.json').write_text(json.dumps(results, indent=1, default=float), encoding='utf-8')
    cfg = IC.CONFIGS[0]['name']
    print(f'{K} size-matched paragraph shuffles, interior words, lines above only, joint control (inside exact length x pool-size tertile):')
    for key, r in results.items():
        for meas in ('components', 'h2'):
            o = r['observed'][cfg]['interior-1'][meas]['length_pool']
            v = np.array([s[cfg]['interior-1'][meas]['length_pool']['diff'] for s in r['shuffles']], float)
            above = int((v < o['diff']).sum())
            print(f"  {key:24s} {meas:10s} observed {o['diff']:+.3f} [{o['ci'][0]:+.3f},{o['ci'][1]:+.3f}]  shuffles mean {v.mean():+.3f}, range {v.min():+.3f}..{v.max():+.3f}, "
                  f"observed above {above}/{len(v)} (one-sided p = {(len(v) - above + 1) / (len(v) + 1):.3f})")


if __name__ == '__main__':
    main()
