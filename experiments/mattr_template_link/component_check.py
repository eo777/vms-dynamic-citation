"""T13. The spatial component-diversity association, calibrated (27 October).

The component-impact study (research/timm_geometry_audit_20261026/component_impact_20261027) finds that word N is
slightly more often a repeat when the words physically above and to the left of it (a cone of 8 line spacings,
45 degrees, 3 word widths to the left, same page, earlier tokens only) contain fewer distinct glyph-unit pairs
(component diversity) or have lower conditional glyph entropy (H2): within-bifolium lowest-against-highest
quintile difference +0.038 MATTR points of word impact over the manuscript, held-out error reduction under 1
percent. This script asks what that association is worth as evidence of copying from the page in view, by
measuring the same statistic, with the other study's own selector and formulas (component_measure.js), on
  (a) the manuscript (recorded word rectangles, as in the other study; and synthetic rectangles laid along each
      line by character position, to validate the proxy used for the generators),
  (b) the saved generators that do copy from the page window (Original Timm, far 0, no-innovator far 0) and the
      governed streams with other supplies (100-form memory, 2,000-token pool), laid into the manuscript's lines
      with synthetic rectangles,
  (c) natural prose cut into the same lines (letters as units, letter pairs as components), with the recorded
      rectangles,
and by placing the spatial cone beside two geometry-free neighbourhoods: the preceding 99 tokens in reading
order (which cross page boundaries and need no sight) and the following 99 tokens (which cannot have been
copied from). Outcomes are the other study's: app word impact (share of the 100-token windows containing N in
which another copy of N's spelling occurs), arrival burden (1 - 1/copies of N's spelling in N and the 99 tokens
before it), repeat100 (N's spelling occurs among the preceding 99 tokens), and a mirror-image departure burden
(N and the 99 tokens after it). Quintiles are formed within bifolium; the cohort is the tokens whose 100
containing windows lie inside their bifolium and whose component score is valid.
"""
from collections import Counter
import gzip
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import data as D
from geometry_inputs import load_app as load_study_app
from decompose import REFS, ref_words
from timing import laid_in

sys.path.insert(0, str(D.src('packages/voynich_gradients/src')))
from voynich_gradients.glyph_units import units as glyph_units

APP = D.src('apps/selfcitation_governor/data/mattr_heatmap/words.json.gz')
OTHER = D.src('research/timm_geometry_audit_20261026/component_impact_20261027/derived.json.gz')
NODE_SCRIPT = HERE / 'component_measure.js'
rng = np.random.default_rng(27102026)
REGIONS = {'all': None, '3c': {'3c'}, '4a': {'4a'}, 'Herbal A': {'1a', '1b', '1.5a', '2a'}}
PREDICTORS = ['components', 'h2', 'worddiv', 'back_components', 'fwd_components', 'n']
OUTCOMES = ['app_impact', 'arrival', 'repeat100', 'departure']
PROSE = ('la_galen_simplicium', 'la_dioscorides_longob', 'la_rhazes_almansor', 'la_hildegard_physica', 'de_gart_augsburg1487')


def zattera(word):
    return [u.text for u in glyph_units(word, 'zattera')]


# The frame rule (oversized boxes excluded, drawing gaps as segments, vertical gaps shared by neighbouring lines) and the
# placement rule are one implementation, shared with the generator's spatial source mode (27 October 2026):
# research/dynamic_selfcitation_20261024/governed/page_geometry.py (reproduce/... in the published kit).
sys.path.insert(0, str(D.src('research/dynamic_selfcitation_20261024/governed')))
from page_geometry import oversized_flags, line_frames, line_profile, place_in_slot, vertical_gaps  # noqa: E402,F401


def fill_slots(ms, frames, slot_words, mode, cw_page=None, skip=None):
    """Lay words into the manuscript's line slots page by page, within the recorded text segments, with carry-over:
    words that do not fit a slot continue at the start of the next slot of the same page (as a scribe fills the
    next line), and words left at the end of a page go to extra lines below the page's lowest recorded line, at the
    page's pitch and in its widest line's segments, so nothing is written beyond a line's margin.
      mode 'fixed': slot_words[l] are the words that belong to slot l (a generator's or a budget-filled line); the
                    carry from the previous slot is placed first; character width = the slot's recorded text width
                    over the manuscript line's characters (the manuscript's letter size on that line).
      mode 'lines': slot_words is a sequence of printed lines; a slot takes the carry if there is one, otherwise the
                    next printed line; character width = cw_page[page index].
    skip: per-slot flags of slots that take nothing (label-like slots); the carry passes over them.
    Returns (words per slot, geometry in that order)."""
    n = len(ms['lines'])
    out_words = [[] for _ in range(n)]
    out_geom = [[] for _ in range(n)]
    supply = iter(slot_words) if mode == 'lines' else None
    for p in ms['pages']:
        slots = list(range(p['start_line'], p['end_line']))
        centres = [(frames[l][1] + frames[l][3]) / 2 for l in slots if frames[l] is not None]
        gaps = [b - a for a, b in zip(centres, centres[1:]) if b - a > 0]
        pitch = float(np.median(gaps)) if gaps else 30.0
        carry = []
        last_framed = None
        last_cw = None
        widest = None      # (slot, total segment width, cw): the page's widest recorded line
        lowest = None      # the slot whose recorded line lies lowest on the page
        for l in slots:
            if skip is not None and skip[l]:
                continue
            fr = frames[l]
            if mode == 'lines':
                words = carry if carry else list(next(supply, []))
            else:
                words = carry + list(slot_words[l])
            carry = []
            if fr is None or not words:
                out_words[l] = words
                out_geom[l] = [None] * len(words)
                continue
            cw = cw_page[p['index']] if mode == 'lines' else sum(b - a for a, b in fr[4]) / max(ms['lines'][l]['chars'], 1)
            placed, boxes = place_in_slot(words, fr, cw)
            out_words[l] = words[:placed]
            out_geom[l] = boxes
            carry = words[placed:]
            last_framed, last_cw = l, cw
            width = sum(b - a for a, b in fr[4])
            if widest is None or width > widest[1]:
                widest = (l, width, cw)
            if lowest is None or fr[3] > frames[lowest][3]:
                lowest = l
        k = 0
        while carry and last_framed is not None:
            # overflow lines go below the page's lowest recorded line, in the widest line's segments at its letter size
            # (27 October correction: they were stacked under the last slot in transcription order, which on pages whose
            # short lines beside a drawing are transcribed last put them in a column down the page, f75r among them)
            k += 1
            wl, _, wcw = widest
            shift = frames[lowest][3] - frames[wl][3] + k * pitch
            placed, boxes = place_in_slot(carry, frames[wl], wcw, yshift=shift)
            out_words[last_framed] += carry[:placed]
            out_geom[last_framed] += boxes
            carry = carry[placed:]
        if carry:
            l = slots[-1]
            out_words[l] += carry
            out_geom[l] += [None] * len(carry)
    return out_words, [g for gs in out_geom for g in gs]


def synthetic_geometry(line_words, frames, ms):
    """Boxes for a text given line by line (a generator's or a budget-filled reflow): words stay inside each manuscript
    line's recorded text segments, follow the line's drift and height, and are written at the manuscript's letter
    size on that line; words that do not fit carry over to the next slot. The per-slot word lists in `line_words`
    are updated IN PLACE to the carried-over assignment, so the caller's line structure matches the geometry."""
    new_words, geom = fill_slots(ms, frames, line_words, 'fixed')
    for l in range(len(line_words)):
        line_words[l][:] = new_words[l]
    return geom


def make_input(ms, line_words, geometry, comp_fn):
    words = []
    lines = []
    for L, ws in zip(ms['lines'], line_words):
        lines.append(dict(page=L['folio'], locus=L['locus'], bifolium=L['node'], start=len(words), end=len(words) + len(ws)))
        words += list(ws)
    assert len(geometry) == len(words)
    return dict(words=words, lines=lines, geometry=geometry, components={w: comp_fn(w) for w in set(words)})


def measure(inp):
    with tempfile.TemporaryDirectory() as td:
        pin = Path(td) / 'in.json'
        pout = Path(td) / 'out.json'
        pin.write_text(json.dumps(inp), encoding='utf-8')
        r = subprocess.run(['node', str(NODE_SCRIPT), str(pin), str(pout)], capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(r.stderr)
        out = json.loads(pout.read_text(encoding='utf-8'))
    return {k: np.array([np.nan if v is None else v for v in vals], dtype=float) for k, vals in out.items()}


def occurrence_arrays(words):
    n = len(words)
    prev = np.full(n, -1)
    nxt = np.full(n, n)
    last = {}
    for i, w in enumerate(words):
        j = last.get(w)
        if j is not None:
            prev[i] = j
            nxt[j] = i
        last[w] = i
    return prev, nxt


def outcomes(words, bstart, bend):
    """The other study's outcomes for token N (same formulas as its prepare.js / wordImpact), plus a forward mirror."""
    n = len(words)
    prev, nxt = occurrence_arrays(words)
    idx = np.arange(n)
    repeat100 = ((idx - prev <= 99) & (prev >= 0)).astype(float)
    arrival = np.zeros(n)
    counts = Counter()
    for i in range(n):
        counts[words[i]] += 1
        if i >= 100:
            counts[words[i - 100]] -= 1
        arrival[i] = 1 - 1 / counts[words[i]]
    departure = np.zeros(n)
    counts = Counter()
    for i in range(n - 1, -1, -1):
        counts[words[i]] += 1
        if i + 100 < n:
            counts[words[i + 100]] -= 1
        departure[i] = 1 - 1 / counts[words[i]]
    lo = np.maximum(0, idx - 99)
    hi = np.minimum(idx, n - 100)
    count = np.maximum(0, hi - lo + 1)
    unique = np.maximum(0, np.minimum(hi, nxt - 100) - np.maximum(lo, prev + 1) + 1)
    app = np.where(count > 0, (count - unique) / np.maximum(count, 1), np.nan)
    full = (idx - bstart >= 99) & (bend - idx >= 100)
    return dict(app_impact=app, arrival=arrival, repeat100=repeat100, departure=departure, full=full)


def token_meta(ms, line_words):
    node = []
    group = []
    for L, ws in zip(ms['lines'], line_words):
        node += [L['node']] * len(ws)
        group += [L['group']] * len(ws)
    node = np.array(node, dtype=object)
    group = np.array(group, dtype=object)
    n = len(node)
    bstart = np.zeros(n, dtype=int)
    bend = np.zeros(n, dtype=int)
    i = 0
    while i < n:
        j = i
        while j < n and node[j] == node[i]:
            j += 1
        bstart[i:j] = i
        bend[i:j] = j
        i = j
    return node, group, bstart, bend


def quintile_contrast(metric, outcome, bif, mask, reps=2000):
    rows = []
    for b in np.unique(bif[mask]):
        m = mask & (bif == b) & np.isfinite(metric) & np.isfinite(outcome)
        if m.sum() < 25:
            continue
        x = metric[m]
        y = outcome[m]
        lo, hi = np.quantile(x, [.2, .8])
        L = y[x <= lo]
        H = y[x >= hi]
        rows.append([L.sum(), len(L), H.sum(), len(H)])
    if not rows:
        return dict(diff=np.nan, ci=[np.nan, np.nan], bifolia=0)
    v = np.array(rows, dtype=float)
    t = v.sum(0)
    diff = t[0] / t[1] - t[2] / t[3]
    ci = [np.nan, np.nan]
    if len(v) >= 3:
        draw = rng.integers(0, len(v), (reps, len(v)))
        s = v[draw].sum(1)
        ok = (s[:, 1] > 0) & (s[:, 3] > 0)
        bs = s[ok, 0] / s[ok, 1] - s[ok, 2] / s[ok, 3]
        ci = list(np.quantile(bs, [.025, .975]))
    return dict(diff=float(diff), ci=[float(c) for c in ci], bifolia=len(v), low=float(t[0] / t[1]), high=float(t[2] / t[3]))


def lobo_linear(metric, outcome, bif, mask):
    """Leave-one-bifolium-out percent reduction of squared error from a straight line in the metric, against the
    training mean."""
    m = mask & np.isfinite(metric) & np.isfinite(outcome)
    x = metric[m]
    y = outcome[m]
    g = bif[m]
    base = err = 0.0
    for b in np.unique(g):
        tr = g != b
        te = ~tr
        if tr.sum() < 50 or te.sum() == 0:
            continue
        X = np.column_stack([np.ones(tr.sum()), x[tr]])
        beta = np.linalg.lstsq(X, y[tr], rcond=None)[0]
        base += ((y[te] - y[tr].mean()) ** 2).sum()
        err += ((y[te] - (beta[0] + beta[1] * x[te])) ** 2).sum()
    return float(100 * (base - err) / base) if base else np.nan


def joint_within(meas, out, bif, mask):
    """Within-bifolium standardized regression of app impact on log2 spatial components and log2 preceding-99
    components together (both demeaned by bifolium)."""
    x1 = np.log2(meas['components'])
    x2 = np.log2(meas['back_components'])
    y = out['app_impact']
    m = mask & np.isfinite(x1) & np.isfinite(x2) & np.isfinite(y)
    cols = []
    for v in (x1, x2, y):
        z = v[m].copy()
        for b in np.unique(bif[m]):
            mm = bif[m] == b
            z[mm] -= z[mm].mean()
        cols.append(z / (z.std() or 1))
    X = np.column_stack([cols[0], cols[1]])
    beta = np.linalg.lstsq(X, cols[2], rcond=None)[0]
    return dict(spatial=float(beta[0]), preceding99=float(beta[1]), r_spatial=float(np.corrcoef(cols[0], cols[2])[0, 1]),
                r_preceding99=float(np.corrcoef(cols[1], cols[2])[0, 1]), r_between=float(np.corrcoef(cols[0], cols[1])[0, 1]), n=int(m.sum()))


def analyse(ms, line_words, geometry, comp_fn):
    inp = make_input(ms, line_words, geometry, comp_fn)
    meas = measure(inp)
    node, group, bstart, bend = token_meta(ms, line_words)
    out = outcomes(inp['words'], bstart, bend)
    base_mask = out['full'] & np.isfinite(meas['components'])
    res = dict(tokens=len(inp['words']), valid_components=int(np.isfinite(meas['components']).sum()), cohort=int(base_mask.sum()),
               mean_app_impact=float(np.nanmean(out['app_impact'][base_mask])), mean_components=float(np.nanmean(meas['components'][base_mask])),
               regions={})
    for name, groups in REGIONS.items():
        mask = base_mask if groups is None else base_mask & np.isin(group, list(groups))
        r = dict(n=int(mask.sum()), contrasts={}, lobo={}, joint=joint_within(meas, out, node, mask))
        for p in PREDICTORS:
            for o in OUTCOMES:
                r['contrasts'][f'{p}->{o}'] = quintile_contrast(meas[p], out[o], node, mask)
        for p in ('components', 'h2', 'worddiv', 'back_components', 'fwd_components'):
            for o in ('app_impact', 'arrival'):
                r['lobo'][f'{p}->{o}'] = lobo_linear(meas[p], out[o], node, mask)
        res['regions'][name] = r
    return res, meas, out, inp


def check_against_other(meas, out, inp):
    """The manuscript with recorded rectangles must reproduce the other study's per-token table."""
    raw = json.load(gzip.open(OTHER, 'rt', encoding='utf8'))
    rows = raw['rows']
    assert [r['word'] for r in rows] == inp['words']
    theirs = {k: np.array([np.nan if r[k] is None else r[k] for r in rows], dtype=float) for k in ('components', 'h2', 'app_impact', 'arrival_burden', 'repeat100', 'prior_components')}
    def maxdiff(a, b):
        m = np.isfinite(a) & np.isfinite(b)
        return dict(max_abs_diff=float(np.max(np.abs(a[m] - b[m]))), both_valid=int(m.sum()), only_mine=int((np.isfinite(a) & ~np.isfinite(b)).sum()), only_theirs=int((~np.isfinite(a) & np.isfinite(b)).sum()))
    return dict(components=maxdiff(meas['components'], theirs['components']), h2=maxdiff(meas['h2'], theirs['h2']),
                back_components_vs_prior_components=maxdiff(meas['back_components'], theirs['prior_components']),
                app_impact=maxdiff(out['app_impact'], theirs['app_impact']), arrival=maxdiff(out['arrival'], theirs['arrival_burden']),
                repeat100=maxdiff(out['repeat100'], theirs['repeat100']))


def main():
    ms = D.manuscript()
    app = load_study_app('legacy')
    ms_lines = [L['words'] for L in ms['lines']]
    assert app['words'] == [w for ws in ms_lines for w in ws]
    for w, parts in app['components'].items():
        assert zattera(w) == parts, w
    frames = line_frames(app, ms)
    flags = oversized_flags(app, ms)
    clean = [None if flags[i] else g for i, g in enumerate(app['geometry'])]
    page_sizes = [sum(len(ms['lines'][l]['words']) for l in range(p['start_line'], p['end_line'])) for p in ms['pages']]

    results = dict(texts={})
    res, meas, out, inp = analyse(ms, ms_lines, app['geometry'], zattera)
    results['check_against_other_study'] = check_against_other(meas, out, inp)
    results['texts']['manuscript'] = [res]
    print('manuscript done; agreement with the other study:', json.dumps(results['check_against_other_study']), flush=True)
    res_syn, *_ = analyse(ms, ms_lines, synthetic_geometry(ms_lines, frames, ms), zattera)
    results['texts']['manuscript_synthetic'] = [res_syn]
    print('manuscript with synthetic rectangles done', flush=True)
    for key, (label, srcs) in D.STREAMS.items():
        per = []
        for s in srcs[:3]:
            lines = D.read_stream(s)
            r, *_ = analyse(ms, lines, synthetic_geometry(lines, frames, ms), zattera)
            per.append(r)
            print(key, 'seed done', flush=True)
        results['texts'][key] = per
    for key in PROSE:
        words = ref_words(REFS[key])
        if len(words) >= sum(page_sizes) + 10:
            lines = laid_in(ms, words, page_sizes)
            r, *_ = analyse(ms, lines, clean, lambda w: list(w))
            results['texts']['ref_' + key] = [r]
            print(key, 'done', flush=True)
    (HERE / 'component_check.json').write_text(json.dumps(results, indent=1, default=float), encoding='utf-8')

    def agg(per, path):
        vals = []
        for r in per:
            v = r
            for k in path:
                v = v[k]
            vals.append(v)
        return float(np.mean(vals)), float(min(vals)), float(max(vals))

    for region in REGIONS:
        print(f"\n== region {region}: within-bifolium quintile contrast (lowest minus highest diversity quintile) of the outcome; mean over seeds [min, max]; manuscript with 95% CI")
        print(f"  {'text':24s} {'cohort':>7s} {'mean impact':>11s} " + ' '.join(f"{p + '->' + o:>28s}" for p in ('components', 'h2', 'worddiv', 'back_components', 'fwd_components') for o in ('app_impact', 'arrival', 'departure')))
        for key, per in results['texts'].items():
            cells = []
            for p in ('components', 'h2', 'worddiv', 'back_components', 'fwd_components'):
                for o in ('app_impact', 'arrival', 'departure'):
                    m, lo, hi = agg(per, ['regions', region, 'contrasts', f'{p}->{o}', 'diff'])
                    if len(per) == 1 and key.startswith('manuscript'):
                        ci = per[0]['regions'][region]['contrasts'][f'{p}->{o}']['ci']
                        cells.append(f"{m:+.3f} [{ci[0]:+.3f},{ci[1]:+.3f}]".rjust(28))
                    else:
                        cells.append(f"{m:+.3f} [{lo:+.3f},{hi:+.3f}]".rjust(28))
            n = agg(per, ['regions', region, 'n'])[0]
            mi = agg(per, ['mean_app_impact'])[0]
            print(f"  {key:24s} {n:7.0f} {mi:11.3f} " + ' '.join(cells))
        print(f"\n  held-out (leave-one-bifolium-out) linear error reduction, percent: components / h2 / worddiv / back_components / fwd_components -> app_impact | arrival")
        for key, per in results['texts'].items():
            cells = []
            for o in ('app_impact', 'arrival'):
                cells.append(' / '.join(f"{agg(per, ['regions', region, 'lobo', f'{p}->{o}'])[0]:+.2f}" for p in ('components', 'h2', 'worddiv', 'back_components', 'fwd_components')))
            j = per[0]['regions'][region]['joint']
            print(f"  {key:24s} " + ' | '.join(cells) + f"   joint within-bifolium std. coefficients: spatial {agg(per, ['regions', region, 'joint', 'spatial'])[0]:+.3f}, preceding-99 {agg(per, ['regions', region, 'joint', 'preceding99'])[0]:+.3f} (r between {agg(per, ['regions', region, 'joint', 'r_between'])[0]:+.2f})")
    print('\n== pool size as predictor (n -> app_impact), region all:', {k: round(agg(v, ['regions', 'all', 'contrasts', 'n->app_impact', 'diff'])[0], 3) for k, v in results['texts'].items()})


if __name__ == '__main__':
    main()
