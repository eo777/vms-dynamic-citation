"""T17. What the spatial association is made of, per text and per measure (27 October).

For every text the pool-size-stratified quintile contrast of word impact (section 7 statistic, averaged inside
pool-size tertiles) is computed for three pool measures, word diversity, component diversity and H2, over all
targets and separately for targets of three letters or fewer and of six or more. In German prose nearly half the
tokens are words of three letters or fewer and those are the repeats, so an instrument whose pool depends on word
length can produce a contrast between length classes without any within-class association.
Texts: the nine app-page variants (bundles written by heatmap_variants.py) plus, built here with the same rules,
the manuscript with its words shuffled inside paragraphs and inside pages (recorded boxes), and Original Timm, the
100-form memory stream and the 2,000-token pool stream (first seed, synthetic rectangles). Also reported: the
Spearman correlation of the target's length with its impact, the share of short targets, and the contrast with
the 56 label-like slots excluded as targets.
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
from timing import shuffled_within

OUT = HERE / 'heatmap_variants'
VARIANTS = ('manuscript', 'manuscript_clean', 'timm', 'noinnov_far0', 'timm_spatial', 'noinnov_spatial', 'far0_spatial', 'bigram_whole', 'bigram_currier', 'bigram_section', 'gart_one_word_per_box', 'gart_character_budget', 'gart_own_lines')


def spearman(a, b):
    return float(np.corrcoef(np.argsort(np.argsort(a)), np.argsort(np.argsort(b)))[0, 1])


SECTIONS = (('Herbal A', 'H/A'), ('Herbal B', 'H/B'), ('Pharma', 'P/A'), ('Stars', 'S/B'), ('Bio', 'B/B'), ('Text-only pages', 'T/B'))   # section letter / Currier language


GROUPS = ('1a', '1b', '1.5a', '2a', '3b', '3a', '3c', '4c', '4a')


def analyse(inp, label_like, sec_of=None, grp_of=None):
    meas = CC.measure(inp)
    words = inp['words']
    n = len(words)
    node = np.empty(n, dtype=object)
    sec = np.empty(n, dtype=object)
    grp = np.empty(n, dtype=object)
    in_label = np.zeros(n, dtype=bool)
    for L in inp['lines']:
        node[L['start']:L['end']] = L['bifolium']
        sec[L['start']:L['end']] = sec_of.get(L['page']) if sec_of else None
        grp[L['start']:L['end']] = grp_of.get(L['bifolium']) if grp_of else None
        if (L['page'], L['locus']) in label_like:
            in_label[L['start']:L['end']] = True
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
    out = CC.outcomes(words, bstart, bend)
    base = out['full'] & np.isfinite(meas['components']) & np.isfinite(meas['worddiv']) & np.isfinite(meas['h2'])
    wl = np.array([len(w) for w in words], float)

    def strata(mask, metric):
        q = np.nanpercentile(meas['n'][mask], [33, 67])
        parts = []
        for a, b in ((-1, q[0]), (q[0], q[1]), (q[1], 1e9)):
            mm = mask & (meas['n'] > a) & (meas['n'] <= b)
            parts.append(CC.quintile_contrast(metric, out['app_impact'], node, mm, reps=100)['diff'])
        return float(np.mean(parts))

    r = dict(r_len_impact=spearman(wl[base], out['app_impact'][base]), share_short=float((wl[base] <= 3).mean()), tokens=int(base.sum()),
             label_targets=int((base & in_label).sum()))
    for name, metric in (('worddiv', meas['worddiv']), ('components', meas['components']), ('h2', meas['h2'])):
        r[name] = dict(all=strata(base, metric), short=strata(base & (wl <= 3), metric), long=strata(base & (wl >= 6), metric), no_label_targets=strata(base & ~in_label, metric))
    # by section (27 October, user's request): the same pool-size-stratified contrast inside each section x Currier group
    r['sections'] = {}
    for sname, key in SECTIONS:
        m = base & (sec == key)
        r['sections'][sname] = dict(n=int(m.sum()), **{name: strata(m, metric) for name, metric in (('worddiv', meas['worddiv']), ('components', meas['components']), ('h2', meas['h2']))})
    # by Golf 2.1 group (27 October, user's request)
    r['groups'] = {}
    for g in GROUPS:
        m = base & (grp == g)
        r['groups'][g] = dict(n=int(m.sum()), **{name: strata(m, metric) for name, metric in (('worddiv', meas['worddiv']), ('components', meas['components']), ('h2', meas['h2']))})
    return r


def main():
    from native_layout import label_like_slot
    ms = D.manuscript()
    app = json.load(gzip.open(CC.APP, 'rt', encoding='utf8'))
    frames = CC.line_frames(app, ms)
    label_like = {(L['folio'], L['locus']) for L in ms['lines'] if label_like_slot(L)}
    sec_of = {p['folio']: f"{p['section']}/{p['currier']}" for p in ms['pages']}
    grp_of = {L['node']: L['group'] for L in ms['lines']}
    texts = []
    for key in VARIANTS:
        b = json.load(gzip.open(OUT / key / 'data/mattr_heatmap/words.json.gz', 'rt', encoding='utf8'))
        texts.append((key, dict(words=b['words'], lines=b['lines'], geometry=b['geometry'], components=b['components'])))
    tok = D.tokenize(ms)
    par_id = np.cumsum(tok['since_par'] == 0)
    texts.append(('manuscript_shuffled_paragraphs', CC.make_input(ms, shuffled_within(ms, tok, par_id), app['geometry'], CC.zattera)))
    texts.append(('manuscript_shuffled_pages', CC.make_input(ms, shuffled_within(ms, tok, tok['page']), app['geometry'], CC.zattera)))
    # the innovator-active runs (far 0 with innovator, 100-form memory, 2,000-token pool) are no longer measured (27 October, user's direction)
    res = {}
    print(f'label-like manuscript lines (at most 2 words and 12 characters): {len(label_like)} of {len(ms["lines"])}')
    print(f"{'text':32s} | len~impact | short share | word diversity all/short/long | components all/short/long | H2 all/short/long | word diversity, label slots excluded")
    for key, inp in texts:
        r = analyse(inp, label_like, sec_of, grp_of)
        res[key] = r
        f = lambda m: f"{r[m]['all']:+.3f} / {r[m]['short']:+.3f} / {r[m]['long']:+.3f}"
        print(f"{key:32s} | {r['r_len_impact']:+.2f} | {r['share_short']:.2f} | {f('worddiv')} | {f('components')} | {f('h2')} | {r['worddiv']['no_label_targets']:+.3f} ({r['label_targets']} excluded)", flush=True)
        print('    by Golf group (n; word diversity / components / H2): ' + '; '.join(f"{g} ({v['n']}; {v['worddiv']:+.3f} / {v['components']:+.3f} / {v['h2']:+.3f})" for g, v in r['groups'].items()), flush=True)
        print('    by section (n; word diversity / components / H2): ' + '; '.join(f"{sn} ({v['n']}; {v['worddiv']:+.3f} / {v['components']:+.3f} / {v['h2']:+.3f})" for sn, v in r['sections'].items()), flush=True)
    (HERE / 'mechanism_check.json').write_text(json.dumps(res, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
