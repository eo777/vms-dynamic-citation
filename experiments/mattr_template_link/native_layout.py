"""T16. A natural text in its own line structure (27 October, user's request; construction corrected twice after inspection).

The reflows of section 8 force natural prose into the manuscript's line wraps. Here a natural text keeps its own
physical lines: the Augsburg 1487 Gart der Gesundheit OCR preserves the printed lines (median 5 words and 31
characters). Each printed line is placed in one manuscript line slot in Path 1 order: it starts where the manuscript
line starts, runs its own length at the page's character width (so a short printed line is physically short), keeps
the manuscript line's drawing gaps (a word that no longer fits before a drawing continues after it) and follows the
recorded line's drift and height (oversized recorded rectangles excluded). Nothing is re-wrapped except OCR lines
longer than 1.6 times the median, which are broken at word boundaries; OCR fragments (a single token of one or two
letters, 404 of 28,092 lines) are dropped. Earlier versions had slots stretched by oversized boxes, kept the OCR
fragments, ignored the drawing gaps and sat on straight bands; the user found each on the verification pages. The
same text is also laid one word per manuscript box (recorded rectangles, oversized ones removed in the app pages)
and filled to the manuscript's character budget (synthetic rectangles), as in section 8, for comparison. Measures:
MATTR100 by group with bag and clustering parts; the spatial statistic (components = letter pairs, word diversity)
overall and inside pool-size tertiles.
"""
import gzip
import json
import re
import sys
import unicodedata
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import data as D
import component_check as CC
import layout_controls as LC
from decompose import REFS, ref_words
from timing import laid_in

rng = np.random.default_rng(1487)
GART = REFS['de_gart_augsburg1487']
letters = lambda w: list(w)


def native_lines(path, wrap_factor=1.6):
    """The text's own printed lines: OCR fragments dropped, over-long OCR lines broken at word boundaries."""
    text = unicodedata.normalize('NFKC', path.read_text(encoding='utf-8', errors='ignore').lower())
    raw = []
    for line in text.splitlines():
        ws = re.findall(r"[^\W\d_]+", line)
        if not ws or (len(ws) == 1 and len(ws[0]) <= 2):
            continue
        raw.append(ws)
    med = np.median([sum(len(w) for w in ws) + len(ws) - 1 for ws in raw])
    limit = int(wrap_factor * med)
    out = []
    for ws in raw:
        if sum(len(w) for w in ws) + len(ws) - 1 <= limit:
            out.append(ws)
            continue
        cur = []
        used = 0
        for w in ws:
            if cur and used + 1 + len(w) > med:
                out.append(cur)
                cur = []
                used = 0
            cur.append(w)
            used += len(w) + (1 if used else 0)
        if cur:
            out.append(cur)
    return out


def page_block(ms, frames, p):
    """Left margin, first line centre, pitch, box height and character width of a page from its robust line frames."""
    fr = [frames[l] for l in range(p['start_line'], p['end_line']) if frames[l] is not None]
    chars = [ms['lines'][l]['chars'] for l in range(p['start_line'], p['end_line']) if frames[l] is not None]
    if not fr:
        return None
    left = float(np.percentile([f[0] for f in fr], 10))
    centres = sorted((f[1] + f[3]) / 2 for f in fr)
    gaps = [b - a for a, b in zip(centres, centres[1:]) if b - a > 0]
    height = float(np.median([f[3] - f[1] for f in fr]))
    pitch = float(np.median(gaps)) if gaps else height * 1.6
    cw = float(np.median([(f[2] - f[0]) / c for f, c in zip(fr, chars) if c > 0]))
    return dict(left=left, top=centres[0], pitch=pitch, height=height, cw=cw)


def native_layout(ms, app, lines, start=None):
    """Place the text's own lines into the manuscript's line slots: each printed line starts where the manuscript
    line starts, runs its own length at the page's character width, keeps the manuscript line's drawing gaps,
    follows the recorded line's drift and height, and when it does not fit the slot continues at the start of the
    next slot (nothing is written beyond a line's margin); label-like slots take nothing."""
    frames = CC.line_frames(app, ms)
    label_like = [label_like_slot(L) for L in ms['lines']]
    need = len(ms['lines']) - sum(label_like)
    if start is None:
        start = int(rng.integers(0, len(lines) - need))
    cw_page = {}
    for p in ms['pages']:
        blk = page_block(ms, frames, p)
        cw_page[p['index']] = blk['cw'] if blk else 6.0
    chosen, geometry = CC.fill_slots(ms, frames, lines[start:start + need], 'lines', cw_page=cw_page, skip=label_like)
    return chosen, geometry, start


def label_like_slot(L, max_words=2, max_chars=12):
    """A manuscript line of at most two words and twelve characters: the single words written beside the drawings,
    which the study transcription carries as paragraph text (for example f84v lines 42 to 51, f75r 47 to 53)."""
    return len(L['words']) <= max_words and L['chars'] <= max_chars


def strata(meas, out, node, metric, mask, reps=200):
    q = np.nanpercentile(meas['n'][mask], [33, 67])
    parts = []
    for lo, hi in ((-1, q[0]), (q[0], q[1]), (q[1], 1e9)):
        m = mask & (meas['n'] > lo) & (meas['n'] <= hi)
        parts.append(CC.quintile_contrast(metric, out['app_impact'], node, m, reps=reps)['diff'])
    return parts


def analyse(ms, lines, geometry):
    inp = CC.make_input(ms, lines, geometry, letters)
    meas = CC.measure(inp)
    node, group, bstart, bend = CC.token_meta(ms, lines)
    out = CC.outcomes(inp['words'], bstart, bend)
    base = out['full'] & np.isfinite(meas['components'])
    wl = np.array([len(w) for w in inp['words']], float)
    res = dict(tokens=len(inp['words']), words_per_line=float(np.mean([len(l) for l in lines])), route=LC.group_table(ms, lines), spatial={})
    for region, gs in (('all', None), ('4a', {'4a'})):
        mask = base if gs is None else base & (group == '4a')
        r = {p: CC.quintile_contrast(meas[p], out['app_impact'], node, mask, reps=300)['diff'] for p in ('components', 'worddiv', 'n')}
        sw = strata(meas, out, node, meas['worddiv'], mask)
        sc = strata(meas, out, node, meas['components'], mask)
        r.update(worddiv_by_pool_size=sw, worddiv_by_pool_size_mean=float(np.mean(sw)), components_by_pool_size=sc, components_by_pool_size_mean=float(np.mean(sc)),
                 worddiv_strata_short=float(np.mean(strata(meas, out, node, meas['worddiv'], mask & (wl <= 3)))),
                 worddiv_strata_long=float(np.mean(strata(meas, out, node, meas['worddiv'], mask & (wl >= 6)))),
                 lobo_components=CC.lobo_linear(meas['components'], out['app_impact'], node, mask), mean_impact=float(np.nanmean(out['app_impact'][mask])))
        res['spatial'][region] = r
    return res


def main():
    ms = D.manuscript()
    app = json.load(gzip.open(CC.APP, 'rt', encoding='utf8'))
    frames = CC.line_frames(app, ms)
    page_sizes = [sum(len(ms['lines'][l]['words']) for l in range(p['start_line'], p['end_line'])) for p in ms['pages']]
    lines = native_lines(GART)
    print('OCR lines kept', len(lines), 'words/line', round(float(np.mean([len(l) for l in lines])), 2))
    results = {}
    for seed in range(3):
        chosen, geom, start = native_layout(ms, app, lines)
        results.setdefault('gart_native_lines', []).append(dict(start=start, **analyse(ms, chosen, geom)))
        print('native seed', seed, 'done', flush=True)
    words = ref_words(GART)
    box = laid_in(ms, words, page_sizes)
    results['gart_one_word_per_box'] = [analyse(ms, box, app['geometry'])]
    line = LC.fill_by_chars(ms, words)
    results['gart_character_budget'] = [analyse(ms, line, CC.synthetic_geometry(line, frames, ms))]
    (HERE / 'native_layout.json').write_text(json.dumps(results, indent=1, default=float), encoding='utf-8')

    def mean(per, path):
        vals = []
        for r in per:
            v = r
            for k in path:
                v = v[k]
            vals.append(v)
        return float(np.mean(vals))
    print(f"\n{'Gart der Gesundheit 1487':30s} {'words/line':>10s} {'3c':>6s} {'4c':>6s} {'4a':>6s} {'3c->4a actual = bag + clust':>30s} | spatial all: components, worddiv, pool n | worddiv inside pool-size tertiles (mean) | short / long targets | Bio strata mean")
    for key, per in results.items():
        g = ['route', 'groups']
        print(f"{key:30s} {mean(per, ['words_per_line']):10.2f} {mean(per, g + ['3c', 'mattr100']):6.3f} {mean(per, g + ['4c', 'mattr100']):6.3f} {mean(per, g + ['4a', 'mattr100']):6.3f} "
              f"{mean(per, ['route', 'steps', '3c->4a', 'actual']):+.3f} = {mean(per, ['route', 'steps', '3c->4a', 'bag']):+.3f} {mean(per, ['route', 'steps', '3c->4a', 'clustering']):+.3f}".ljust(100)
              + f" | {mean(per, ['spatial', 'all', 'components']):+.3f} {mean(per, ['spatial', 'all', 'worddiv']):+.3f} {mean(per, ['spatial', 'all', 'n']):+.3f} | "
              + ' '.join(f"{v:+.3f}" for v in per[0]['spatial']['all']['worddiv_by_pool_size']) + f" ({mean(per, ['spatial', 'all', 'worddiv_by_pool_size_mean']):+.3f}) | "
              + f"{mean(per, ['spatial', 'all', 'worddiv_strata_short']):+.3f} / {mean(per, ['spatial', 'all', 'worddiv_strata_long']):+.3f} | {mean(per, ['spatial', '4a', 'worddiv_by_pool_size_mean']):+.3f}")


if __name__ == '__main__':
    main()
