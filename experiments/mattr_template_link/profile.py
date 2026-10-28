"""T1. Where in the layout does local novelty fall, in the manuscript and in the generators?

fresh_i = 1 when token i did not occur among the previous 100 tokens (the increments of D100, so
the mean fresh rate of a stretch is its MATTR100 up to edge effects). Event studies at page starts
(by transition class), at paragraph starts inside pages, by line position, by line width and by the
space left in the line; manuscript against every stream (seed means). Values are rates of fresh
tokens, so a dip is a stretch of local repetition.
"""
from collections import defaultdict
import json
import sys

import numpy as np

sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
import data as D

OFFS = 120   # tokens after a page start
PAR_OFFS = 40


def event_means(fresh, tok, ms, trans):
    page = tok['page']; sp = tok['since_page']; spar = tok['since_par']
    cls_of_page = {t['index']: t['cls'] for t in trans}
    out = {}
    # page starts by class (offset from first token of the page), and the 60 tokens before the boundary
    for cls in ('same-face', 'flip', 'cross-sheet', 'all'):
        pages = [p for p, c in cls_of_page.items() if cls == 'all' or c == cls]
        after = np.full((len(pages), OFFS), np.nan); before = np.full((len(pages), 60), np.nan)
        for k, p in enumerate(pages):
            idx = np.where(page == p)[0]
            m = min(OFFS, len(idx)); after[k, :m] = fresh[idx[:m]]
            prev = np.where(page == p - 1)[0]
            m = min(60, len(prev)); before[k, 60 - m:] = fresh[prev[-m:]]
        out[f'page_start_{cls}'] = dict(n=len(pages), after=np.nanmean(after, axis=0).tolist(), before=np.nanmean(before, axis=0).tolist(),
                                        first50=float(np.nanmean(after[:, :50])), last50_prev=float(np.nanmean(before[:, 10:])))
    # paragraph starts that are not page starts
    first_lines = [li for li, L in enumerate(ms['lines']) if L['first'] and li != ms['pages'][L['page']]['start_line']]
    after = np.full((len(first_lines), PAR_OFFS), np.nan); before = np.full((len(first_lines), 40), np.nan)
    for k, li in enumerate(first_lines):
        idx = np.where(tok['line'] >= li)[0]
        start = idx[0]
        m = min(PAR_OFFS, len(tok['words']) - start); after[k, :m] = fresh[start:start + m]
        # previous tokens on the same page only
        lo = max(0, start - 40)
        seg = fresh[lo:start]; same = page[lo:start] == page[start]
        seg = np.where(same, seg, np.nan)
        before[k, 40 - len(seg):] = seg
    out['paragraph_start'] = dict(n=len(first_lines), after=np.nanmean(after, axis=0).tolist(), before=np.nanmean(before, axis=0).tolist(),
                                  first10=float(np.nanmean(after[:, :10])), prev20=float(np.nanmean(before[:, 20:])))
    # line position
    pos = tok['pos']; ll = tok['linelen']
    first = pos == 0; last = pos == ll - 1; inter = ~first & ~last
    out['line_position'] = dict(first=float(fresh[first & ~tok['first_line']].mean()), interior=float(fresh[inter].mean()), last=float(fresh[last & (ll > 1)].mean()),
                                paragraph_first_word=float(fresh[first & tok['first_line']].mean()))
    # space left in the line before writing the word (chars) for interior/last words
    left = tok['line_chars'] - tok['chars_before']
    bins = [(0, 10), (10, 20), (20, 35), (35, 60), (60, 1000)]
    out['space_left'] = {f'{a}-{b}': float(fresh[(left >= a) & (left < b) & ~first].mean()) for a, b in bins}
    # line width terciles within group: fresh rate for interior words
    out['line_width'] = {}
    for g in sorted(set(L['group'] for L in ms['lines'])):
        gm = np.array([ms['lines'][l]['group'] == g for l in tok['line']])
        lc = tok['line_chars'][gm]; f = fresh[gm]
        q = np.quantile(lc, [1 / 3, 2 / 3])
        out['line_width'][g] = dict(short=float(f[lc <= q[0]].mean()), mid=float(f[(lc > q[0]) & (lc <= q[1])].mean()), long=float(f[lc > q[1]].mean()),
                                    cuts=q.tolist())
    # tokens since paragraph start, binned, within-page only
    out['since_par'] = {f'{a}-{b}': float(fresh[(spar >= a) & (spar < b)].mean()) for a, b in [(0, 1), (1, 5), (5, 10), (10, 20), (20, 40), (40, 80), (80, 10000)]}
    out['since_page'] = {f'{a}-{b}': float(fresh[(sp >= a) & (sp < b)].mean()) for a, b in [(0, 1), (1, 5), (5, 10), (10, 20), (20, 40), (40, 80), (80, 160), (160, 10000)]}
    return out


def recoveries(d100, tok, ms, low=0.65, high=0.80):
    """Troughs of D100 below `low`: tokens until D100 is back above `high`, and whether a paragraph opening falls inside."""
    n = len(d100); i = 0; events = []
    first_tokens = set(np.where((tok['pos'] == 0) & tok['first_line'])[0].tolist())
    page_first = set(ms['pages'][p]['start_line'] for p in range(len(ms['pages'])))
    while i < n:
        if np.isfinite(d100[i]) and d100[i] < low:
            j = i
            while j < n and not (np.isfinite(d100[j]) and d100[j] >= high):
                j += 1
            depth = float(np.nanmin(d100[i:j])) if j > i else float(d100[i])
            par_inside = any(k in first_tokens for k in range(i, min(j, n)))
            events.append(dict(start=int(i), end=int(j), length=int(j - i), depth=depth, page=int(tok['page'][i]), folio=ms['pages'][int(tok['page'][i])]['folio'],
                               paragraph_opening_inside=bool(par_inside)))
            i = j + 1
        else:
            i += 1
    return events


def main():
    ms = D.manuscript(); trans = D.transitions(ms)
    results = {}
    texts = {'manuscript': [None]}
    for key, (label, srcs) in D.STREAMS.items():
        texts[key] = srcs
    for key, srcs in texts.items():
        acc = []; ev_all = []
        for s in srcs:
            tok = D.tokenize(ms, None if s is None else D.read_stream(s))
            fresh = D.fresh_indicator(tok['words'])
            d100 = D.trailing_distinct(tok['words'])
            acc.append(event_means(fresh, tok, ms, trans))
            ev_all.append(recoveries(d100, tok, ms))
        # average across seeds (lists elementwise)
        def avg(objs):
            if isinstance(objs[0], dict):
                return {k: avg([o[k] for o in objs]) for k in objs[0]}
            if isinstance(objs[0], list):
                return np.nanmean(np.array(objs, dtype=float), axis=0).tolist()
            return float(np.nanmean([o for o in objs]))
        res = avg(acc)
        res['label'] = key if key == 'manuscript' else D.STREAMS[key][0]
        res['troughs'] = dict(count_per_seed=float(np.mean([len(e) for e in ev_all])),
                              mean_length=float(np.mean([x['length'] for e in ev_all for x in e])) if any(ev_all) else None,
                              median_length=float(np.median([x['length'] for e in ev_all for x in e])) if any(ev_all) else None,
                              share_with_paragraph_opening=float(np.mean([x['paragraph_opening_inside'] for e in ev_all for x in e])) if any(ev_all) else None,
                              tokens_below_low_per_seed=float(np.mean([sum(x['length'] for x in e) for e in ev_all])))
        if key == 'manuscript':
            res['trough_events'] = ev_all[0]
        results[key] = res
        ps = res['page_start_all']
        print(f"{key:13s} page start: prev-page last 50 {ps['last50_prev']:.3f} -> first 50 {ps['first50']:.3f} | same-face {res['page_start_same-face']['first50']:.3f} flip {res['page_start_flip']['first50']:.3f} cross {res['page_start_cross-sheet']['first50']:.3f} | "
              f"par start prev20 {res['paragraph_start']['prev20']:.3f} -> first10 {res['paragraph_start']['first10']:.3f} | line first/int/last {res['line_position']['first']:.3f}/{res['line_position']['interior']:.3f}/{res['line_position']['last']:.3f} | "
              f"troughs/seed {res['troughs']['count_per_seed']:.1f} median len {res['troughs']['median_length']} par-inside {res['troughs']['share_with_paragraph_opening']}")
    (D.HERE / 'profile.json').write_text(json.dumps(results, indent=1, default=float), encoding='utf-8')


if __name__ == '__main__':
    main()
