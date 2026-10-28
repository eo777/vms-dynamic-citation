"""T8. Are a text's within-page falls depth-progressive (they develop as a paragraph goes on, as recycling
does) or paragraph-compositional (they mark a change of word bag between paragraphs)? Shuffle each text
inside its own paragraphs and ask how many of its own Bio anchors survive, and how much of its body-line
fall survives. Manuscript against every stream, same procedure. Also the novelty rate by paragraph depth
per group, to show where Timm's regional fall lives."""
import json
import sys

import numpy as np

sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
import data as D
from timing import line_deltas, line_covariates, page_anchors, decline_rate_at, shuffled_within, BIO

rng = np.random.default_rng(21)
DEPTH = [(0, 1), (1, 10), (10, 20), (20, 40), (40, 80), (80, 160), (160, 10 ** 6)]


def deltas_for(ms, lines, nlines):
    t = D.tokenize(ms, lines)
    return line_deltas(t['words'], t, nlines)[0], t


def survival(ms, lines, cov, pages, reps=3):
    nlines = len(ms['lines'])
    d, t = deltas_for(ms, lines, nlines)
    anchors = page_anchors(d, cov, pages)
    strong = [li for li in anchors.values() if d[li] <= -0.10]
    body = (cov['open_prior'] >= 1) & (cov['open_next'] == 0)
    elig = np.where(np.isin(cov['page'], pages) & ~np.isnan(d))[0]
    raw_body = float(np.nanmean(d[elig][body[elig]]))
    par_id = np.cumsum(t['since_par'] == 0)
    keep = []; rev = []; body_sh = []
    for _ in range(reps):
        sh = shuffled_within(ms, t, par_id)
        ds, _ = deltas_for(ms, sh, nlines)
        keep.append(decline_rate_at(ds, strong)[0])
        a2 = page_anchors(ds, cov, pages); s2 = [li for li in a2.values() if ds[li] <= -0.10]
        rev.append(decline_rate_at(d, s2)[0] if s2 else np.nan)
        body_sh.append(float(np.nanmean(ds[elig][body[elig]])))
    return dict(strong_anchors=len(strong), shuffle_falls_at_own_anchors=float(np.mean(keep)), text_falls_at_shuffle_anchors=float(np.nanmean(rev)),
                body_fall_raw=raw_body, body_fall_shuffled=float(np.mean(body_sh)))


def depth_rates(ms, lines, groups=('3c', '4c', BIO)):
    t = D.tokenize(ms, lines); fresh = D.fresh_indicator(t['words'])
    g = np.array([ms['lines'][l]['group'] for l in t['line']])
    out = {}
    for grp in groups:
        m = g == grp
        out[grp] = {f'{a}-{b}': float(fresh[m & (t['since_par'] >= a) & (t['since_par'] < b)].mean()) for a, b in DEPTH}
        out[grp]['share'] = {f'{a}-{b}': float(((t['since_par'][m] >= a) & (t['since_par'][m] < b)).mean()) for a, b in DEPTH}
    return out


def main():
    ms = D.manuscript(); tok = D.tokenize(ms); cov = line_covariates(ms, tok)
    bio = [p['index'] for p in ms['pages'] if p['group'] == BIO]
    texts = {'manuscript': [[L['words'] for L in ms['lines']]]}
    for key, (label, srcs) in D.STREAMS.items():
        texts[key] = [D.read_stream(s) for s in srcs[:3]]
    res = dict(survival={}, depth_rates={})
    for key, variants in texts.items():
        per = [survival(ms, lines, cov, bio) for lines in variants]
        res['survival'][key] = {k: float(np.mean([p[k] for p in per])) for k in per[0]}
        dr = [depth_rates(ms, lines) for lines in variants]
        res['depth_rates'][key] = {g: {k: (float(np.mean([x[g][k] for x in dr])) if k != 'share' else dr[0][g]['share']) for k in dr[0][g]} for g in dr[0]}
    (D.HERE / 'shuffle_check.json').write_text(json.dumps(res, indent=1), encoding='utf-8')
    print('== Bio anchors (own text, fall <= -0.10) surviving a shuffle inside paragraphs; body-line mean fall raw vs shuffled')
    print(f"{'text':14s} {'anchors':>8s} {'shuffle falls there':>20s} {'text falls at shuffle anchors':>30s} {'body fall raw':>14s} {'shuffled':>9s}")
    for key, r in res['survival'].items():
        print(f"{key:14s} {r['strong_anchors']:8.1f} {r['shuffle_falls_at_own_anchors']:20.2f} {r['text_falls_at_shuffle_anchors']:30.2f} {r['body_fall_raw']:+14.3f} {r['body_fall_shuffled']:+9.3f}")
    print('\n== novelty rate by paragraph depth (tokens since paragraph start), by group; token shares of the depth bins in brackets')
    for key, r in res['depth_rates'].items():
        for g, row in r.items():
            print(f"{key:14s} {g:3s} " + ' '.join(f"{k}:{v:.3f}" for k, v in row.items() if k != 'share') + '   [' + ' '.join(f"{v:.2f}" for v in row['share'].values()) + ']')


if __name__ == '__main__':
    main()
