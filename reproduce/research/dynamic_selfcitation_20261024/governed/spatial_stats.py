"""Where the spatial draw takes its sources (27 October 2026): per --spatial run, the share of tokens inside the
manuscript's 4,130 lines whose source came from the words in view, the pool sizes, and the line distance from the
word written to its source (0 = the same line, to the left; 1 = the line directly above), against the distribution
Timm's own draw implies on the same pages (a line uniform among the page's lines so far but its first two, so the
line directly above gets 1/max(1, m-2) of the draws on the page's m-th line, and all of them on its last line).

python spatial_stats.py runs/p_timm_spatial ...   -> spatial_stats.json and a markdown table
"""
import gzip
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import page_geometry as PG


def timm_expected(ms):
    """Timm's own line choice, by the manuscript's page structure (tokens weighted as the manuscript's lines)."""
    above = tokens = 0.0
    dist = Counter()
    for p in ms['pages']:
        slots = list(range(p['start_line'], p['end_line']))
        n = len(slots)
        for m, l in enumerate(slots, start=1):
            w = len(ms['lines'][l]['words'])
            tokens += w
            draws = 1 if m == n else max(1, m - 2)   # the page-final line sees linesInPage reset to 0
            for k in range(draws):
                dist[min(k + 1, 4)] += w / draws
            above += w / draws
    return above / tokens, {k: v / tokens for k, v in sorted(dist.items())}


def main():
    geo = PG.PageGeometry()
    ms = geo.ms
    n_lines = len(ms['lines'])
    rows = []
    for r in sys.argv[1:]:
        run = Path(r)
        pools = json.load(gzip.open(run / 'spatial.json.gz', 'rt', encoding='utf-8'))
        lines = [l.split() for l in (run / 'generated_text.txt').read_text(encoding='utf-8-sig').splitlines() if l.strip() and not l.startswith('#')]
        in_ms = sum(len(l) for l in lines[:n_lines])
        used = [p for p in pools[:in_ms] if p]
        dist = Counter(min(p[4] - p[3], 4) for p in used if len(p) >= 5)
        total = sum(dist.values()) or 1
        rows.append(dict(run=run.name, tokens_in_manuscript=in_ms, spatial_share=len(used) / in_ms, mean_pool=float(np.mean([p[0] for p in used])),
                         mean_in_view=float(np.mean([p[1] for p in used])), line_distance={str(k): v / total for k, v in sorted(dist.items())}))
    above, tdist = timm_expected(ms)
    out = dict(runs=rows, timm_own_draw=dict(directly_above=above, line_distance={str(k): v for k, v in tdist.items()}))
    (HERE / 'spatial_stats.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    print('| Run | Tokens in the manuscript\'s lines | Source from the words in view | Mean pool (in view) | Same line, left | Line above | 2 above | 3 above | 4 or more above |')
    print('|---|---:|---:|---:|---:|---:|---:|---:|---:|')
    for r in rows:
        d = r['line_distance']
        print(f"| {r['run']} | {r['tokens_in_manuscript']:,} | {100 * r['spatial_share']:.0f}% | {r['mean_pool']:.1f} ({r['mean_in_view']:.1f}) | " +
              ' | '.join(f"{100 * d.get(str(k), 0):.0f}%" for k in range(5)) + ' |')
    print(f"| Timm's own draw (implied by the page structure) | {sum(len(L['words']) for L in ms['lines']):,} | 0% | | 0% | " +
          ' | '.join(f"{100 * tdist.get(k, 0):.0f}%" for k in range(1, 5)) + ' |')


if __name__ == '__main__':
    main()
