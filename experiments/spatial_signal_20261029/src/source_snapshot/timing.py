"""T6. Timing. Do the generators fall where the manuscript falls, beyond what the shared page layout
imposes on both?

Replicates the model_feedback anchor rule (per page, the line start with the largest fall from MATTR50 of
the preceding 100 tokens to MATTR50 of the following 100, history retained across pages) and adds the
baselines that the earlier counts lacked:
  * page-matched floor: how often the stream declines at ANY eligible line of the same page;
  * layout coupling: the stream's decline rate at anchors selected by another generator family (shared
    layout, different mechanism) and by sibling seeds (same mechanism, the ceiling);
  * the reverse direction: how often the manuscript declines at generator-selected anchors;
  * references laid into the manuscript's lines (no layout response) and manuscript shuffles.
Then a continuous version: the line-level fall/rise series correlated between texts, raw and after
removing the paragraph-structure covariates that both texts share; the seed-to-seed residual is the
calibration for whether the covariates capture the layout response.
Also: where concentration is shared (section-wide) versus local (page-specific), and the within-paragraph
novelty profile of two natural texts that have their own paragraph structure.
"""
from collections import Counter, defaultdict
import json
import re
import sys
import unicodedata

import numpy as np

sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
import data as D
from decompose import REFS, ref_words

rng = np.random.default_rng(5)
BIO = '4a'


# ----------------------------------------------------------------------------- line-level fall series
def line_deltas(words, tok, nlines):
    """For each line start t0: MATTR50(next 100) - MATTR50(prior 100); NaN where a block is unavailable."""
    N = len(words)
    d50 = D.trailing_distinct(words, 50)
    cs = np.concatenate([[0.0], np.cumsum(np.nan_to_num(d50))])
    bm = lambda a, b: (cs[b] - cs[a]) / (b - a)
    lines, starts = np.unique(tok['line'], return_index=True)
    delta = np.full(nlines, np.nan); prior = np.full(nlines, np.nan); nxt = np.full(nlines, np.nan)
    for li, t0 in zip(lines, starts):
        if t0 >= 100 and t0 + 100 <= N:
            prior[li] = bm(t0 - 51, t0); nxt[li] = bm(t0 + 49, t0 + 100); delta[li] = nxt[li] - prior[li]
    return delta, prior, nxt


def line_covariates(ms, tok):
    """Layout covariates of every line start, identical for all line-aligned texts."""
    nlines = len(ms['lines'])
    lines, starts = np.unique(tok['line'], return_index=True)
    opening = (tok['since_par'] == 0).astype(int)
    co = np.concatenate([[0], np.cumsum(opening)])
    N = len(tok['words'])
    cov = dict(first=np.zeros(nlines, int), open_prior=np.full(nlines, -1), open_next=np.full(nlines, -1),
               since_par=np.full(nlines, -1), since_page=np.full(nlines, -1), linelen=np.zeros(nlines, int),
               line_chars=np.zeros(nlines, int), page=np.array([L['page'] for L in ms['lines']]),
               group=np.array([L['group'] for L in ms['lines']]))
    for li, t0 in zip(lines, starts):
        cov['first'][li] = int(ms['lines'][li]['first'])
        cov['open_prior'][li] = co[t0] - co[max(0, t0 - 100)]
        cov['open_next'][li] = co[min(N, t0 + 100)] - co[t0]
        cov['since_par'][li] = tok['since_par'][t0]; cov['since_page'][li] = tok['since_page'][t0]
        cov['linelen'][li] = len(ms['lines'][li]['words']); cov['line_chars'][li] = ms['lines'][li]['chars']
    return cov


def design(cov, idx):
    """One-hot layout design matrix for the lines idx."""
    cols = [np.ones(len(idx))]
    cols.append(cov['first'][idx])
    for k in (1, 2):
        cols.append((np.minimum(cov['open_prior'][idx], 2) == k).astype(float))
        cols.append((np.minimum(cov['open_next'][idx], 2) == k).astype(float))
    for lo, hi in [(1, 20), (20, 50), (50, 100), (100, 10 ** 6)]:
        cols.append(((cov['since_par'][idx] >= lo) & (cov['since_par'][idx] < hi)).astype(float))
    for lo, hi in [(1, 50), (50, 150), (150, 10 ** 6)]:
        cols.append(((cov['since_page'][idx] >= lo) & (cov['since_page'][idx] < hi)).astype(float))
    ll = cov['linelen'][idx]
    for lo, hi in [(0, 6), (6, 9), (9, 12), (12, 100)]:
        cols.append(((ll >= lo) & (ll < hi)).astype(float))
    cols.append(cov['line_chars'][idx] / 50.0)
    return np.column_stack(cols)


def residualize(y, X):
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return y - X @ beta


# ----------------------------------------------------------------------------- texts
def laid_in(ms, words, page_sizes):
    """Cut a word list into the manuscript's lines (same page and line sizes)."""
    total = sum(page_sizes)
    start = int(rng.integers(0, len(words) - total)); seq = words[start:start + total]
    out = []; at = 0
    for p, sz in zip(ms['pages'], page_sizes):
        pt = seq[at:at + sz]; at += sz; k = 0
        for l in range(p['start_line'], p['end_line']):
            n = len(ms['lines'][l]['words']); out.append(pt[k:k + n]); k += n
    return out


def shuffled_within(ms, tok, unit):
    """Manuscript words permuted within each unit (paragraph or page), line lengths kept."""
    words = np.array(tok['words'], dtype=object)
    for u in np.unique(unit):
        m = np.where(unit == u)[0]; words[m] = words[rng.permutation(m)]
    out = []; at = 0
    for L in ms['lines']:
        n = len(L['words']); out.append(list(words[at:at + n])); at += n
    return out


def all_texts(ms):
    """{name: [line-lists]} for the manuscript, every stream seed, references and shuffles."""
    texts = {'manuscript': [[L['words'] for L in ms['lines']]]}
    for key, (label, srcs) in D.STREAMS.items():
        texts[key] = [D.read_stream(s) for s in srcs]
    page_sizes = [sum(len(ms['lines'][l]['words']) for l in range(p['start_line'], p['end_line'])) for p in ms['pages']]
    for key in ('la_galen_simplicium', 'la_dioscorides_longob', 'la_rhazes_almansor', 'la_hildegard_physica', 'de_gart_augsburg1487'):
        words = ref_words(REFS[key])
        if len(words) >= sum(page_sizes) + 10:
            texts['ref_' + key] = [laid_in(ms, words, page_sizes)]
    tok = D.tokenize(ms)
    par_id = np.cumsum(tok['since_par'] == 0)
    texts['ms_shuffled_in_paragraph'] = [shuffled_within(ms, tok, par_id) for _ in range(3)]
    texts['ms_shuffled_in_page'] = [shuffled_within(ms, tok, tok['page']) for _ in range(3)]
    return texts


# ----------------------------------------------------------------------------- anchors
def page_anchors(delta, cov, pages):
    """{page: line index of the largest fall} over lines with a valid delta."""
    out = {}
    for p in pages:
        idx = np.where((cov['page'] == p) & ~np.isnan(delta))[0]
        if len(idx):
            out[p] = int(idx[np.argmin(delta[idx])])
    return out


def decline_rate_at(delta, lines):
    v = delta[list(lines)]; v = v[~np.isnan(v)]
    return float((v < 0).mean()) if len(v) else float('nan'), float(v.mean()) if len(v) else float('nan')


def page_floor(delta, cov, pages):
    """Mean over the pages of the share of eligible lines where the text declines."""
    rates = []
    for p in pages:
        v = delta[(cov['page'] == p) & ~np.isnan(delta)]
        if len(v):
            rates.append(float((v < 0).mean()))
    return float(np.mean(rates)) if rates else float('nan')


def coincidence(deltas, cov, pages, strong_threshold=-0.10):
    """Anchor coincidence table for one set of pages (manuscript-selected and generator-selected)."""
    ms_delta = deltas['manuscript'][0]
    anchors = page_anchors(ms_delta, cov, pages)
    strong = [p for p, li in anchors.items() if ms_delta[li] <= strong_threshold]
    res = dict(pages=len(anchors), strong_pages=len(strong), strong_folios=[ms_cov_folio(cov, li) for li in [anchors[p] for p in strong]],
               manuscript_anchor_delta_mean=float(np.mean([ms_delta[anchors[p]] for p in strong])) if strong else None,
               streams={})
    strong_lines = [anchors[p] for p in strong]
    for key, seeds in deltas.items():
        if key == 'manuscript':
            continue
        rates = []; means = []; floors = []
        for d in seeds:
            r, m = decline_rate_at(d, strong_lines); rates.append(r); means.append(m); floors.append(page_floor(d, cov, strong))
        row = dict(declines_at_manuscript_anchors=float(np.mean(rates)), mean_delta_at_manuscript_anchors=float(np.mean(means)),
                   page_floor=float(np.mean(floors)), n_anchors=len(strong_lines))
        # anchors selected by sibling seeds (same mechanism) and by other families (shared layout only)
        sib = []
        for i, d in enumerate(seeds):
            for j, d2 in enumerate(seeds):
                if i != j:
                    a = page_anchors(d2, cov, strong); sib.append(decline_rate_at(d, [a[p] for p in strong])[0])
        row['declines_at_sibling_anchors'] = float(np.mean(sib)) if sib else None
        oth = []
        for k2, seeds2 in deltas.items():
            if k2 in ('manuscript', key) or k2.startswith('ref_') or k2.startswith('ms_'):
                continue
            a = page_anchors(seeds2[0], cov, strong)
            for d in seeds:
                oth.append(decline_rate_at(d, [a[p] for p in strong])[0])
        row['declines_at_other_family_anchors'] = float(np.mean(oth)) if oth else None
        # reverse: does the manuscript decline where this stream falls hardest?
        rev = []
        for d in seeds:
            a = page_anchors(d, cov, strong); rev.append(decline_rate_at(ms_delta, [a[p] for p in strong])[0])
        row['manuscript_declines_at_stream_anchors'] = float(np.mean(rev))
        res['streams'][key] = row
    res['manuscript_page_floor'] = page_floor(ms_delta, cov, strong)
    return res


def ms_cov_folio(cov, li):
    return int(li)


# ----------------------------------------------------------------------------- structure of anchors
def anchor_structure(deltas, cov, pages):
    """Share of page-minimum anchors whose prior block holds a paragraph opening and whose next block
    is paragraph body only (open_prior >= 1 and open_next == 0), against the base rate of such lines."""
    elig = np.where(np.isin(cov['page'], pages) & ~np.isnan(deltas['manuscript'][0]))[0]
    body = (cov['open_prior'] >= 1) & (cov['open_next'] == 0)
    out = dict(base_rate=float(body[elig].mean()))
    for key, seeds in deltas.items():
        vals = []
        for d in seeds:
            a = page_anchors(d, cov, pages); vals.append(float(np.mean([body[li] for li in a.values()])))
        out[key] = float(np.mean(vals))
    # mean fall by class for each text (eligible lines)
    cls = {'opening in prior, body next': body, 'opening in next block': cov['open_next'] >= 1,
           'no opening in either': (cov['open_prior'] == 0) & (cov['open_next'] == 0)}
    out['mean_delta_by_class'] = {}
    for key, seeds in deltas.items():
        out['mean_delta_by_class'][key] = {c: float(np.mean([np.nanmean(d[elig][m[elig]]) for d in seeds])) for c, m in cls.items()}
    out['class_shares'] = {c: float(m[elig].mean()) for c, m in cls.items()}
    return out


# ----------------------------------------------------------------------------- continuous version
def correlations(deltas, cov, pages):
    idx = np.where(np.isin(cov['page'], pages))[0]
    valid = np.ones(len(idx), bool)
    for seeds in deltas.values():
        for d in seeds:
            valid &= ~np.isnan(d[idx])
    idx = idx[valid]
    X = design(cov, idx)
    raw = {k: [d[idx] for d in seeds] for k, seeds in deltas.items()}
    res_ = {k: [residualize(v, X) for v in vs] for k, vs in raw.items()}
    r2 = {}
    for k, vs in raw.items():
        v = vs[0]; r2[k] = float(1 - np.var(res_[k][0]) / np.var(v))
    def pair(a, b, store):
        vals = [np.corrcoef(x, y)[0, 1] for x in store[a] for y in store[b] if x is not y]
        return float(np.mean(vals))
    out = dict(n_lines=int(len(idx)), layout_r2=r2, pairs={})
    keys = [k for k in deltas if k != 'manuscript']
    for k in keys:
        out['pairs'][f'manuscript~{k}'] = dict(raw=pair('manuscript', k, raw), residual=pair('manuscript', k, res_))
    for k in ('timm', 'far0', 'noinnov_far0', 'timm_spatial', 'noinnov_spatial', 'far0_spatial', 'buffer', 'pool'):
        if len(deltas[k]) > 1:
            out['pairs'][f'{k}~{k} (seeds)'] = dict(raw=pair(k, k, raw), residual=pair(k, k, res_))
    for a, b in (('timm', 'far0'), ('timm', 'buffer'), ('far0', 'buffer'), ('timm', 'pool'), ('timm', 'timm_spatial'), ('noinnov_far0', 'noinnov_spatial'), ('far0', 'far0_spatial')):
        out['pairs'][f'{a}~{b}'] = dict(raw=pair(a, b, raw), residual=pair(a, b, res_))
    return out


# ----------------------------------------------------------------------------- shared vs local concentration
def concentration(ms, lines, groups=('3c', '4c', BIO)):
    page_words = defaultdict(list)
    for L, ws in zip(ms['lines'], lines):
        page_words[L['page']] += ws
    out = {}
    for g in groups:
        pages = [p['index'] for p in ms['pages'] if p['group'] == g and len(page_words[p['index']]) >= 150]
        gbag = Counter(); [gbag.update(page_words[p]) for p in pages]
        top_g = set(w for w, _ in gbag.most_common(50))
        cov_g = []; cov_own = []; tops = {}; vecs = {}
        for p in pages:
            c = Counter(page_words[p]); n = sum(c.values())
            cov_g.append(sum(c[w] for w in top_g) / n)
            cov_own.append(sum(v for _, v in c.most_common(50)) / n)
            tops[p] = set(w for w, _ in c.most_common(20)); vecs[p] = c
        jac = []; cos = []
        for i, a in enumerate(pages):
            for b in pages[i + 1:]:
                jac.append(len(tops[a] & tops[b]) / len(tops[a] | tops[b]))
                ka = vecs[a]; kb = vecs[b]; dot = sum(ka[w] * kb[w] for w in ka if w in kb)
                cos.append(dot / np.sqrt(sum(v * v for v in ka.values()) * sum(v * v for v in kb.values())))
        out[g] = dict(pages=len(pages), group_top50_coverage=float(np.mean(cov_g)), own_top50_coverage=float(np.mean(cov_own)),
                      shared_share=float(np.mean(cov_g) / np.mean(cov_own)), top20_jaccard=float(np.mean(jac)), page_cosine=float(np.mean(cos)),
                      group_types=len(gbag), group_tokens=sum(gbag.values()))
    return out


# ----------------------------------------------------------------------------- natural texts with their own paragraphs
def own_paragraph_profile(path, limit=40000):
    text = unicodedata.normalize('NFKC', path.read_text(encoding='utf-8', errors='ignore').lower())
    paras = [re.findall(r"[^\W\d_]+", p) for p in re.split(r'\n\s*\n', text) if p.strip()]
    words = []; since = []
    for p in paras:
        for k, w in enumerate(p):
            words.append(w); since.append(k)
        if len(words) >= limit:
            break
    words = words[:limit]; since = np.array(since[:limit])
    fresh = D.fresh_indicator(words)
    bins = [(0, 1), (1, 5), (5, 10), (10, 20), (20, 40), (40, 80), (80, 10000)]
    prof = {f'{a}-{b}': float(fresh[(since >= a) & (since < b)].mean()) for a, b in bins}
    return dict(paragraphs=len(paras), median_paragraph_words=float(np.median([len(p) for p in paras])), profile=prof, tokens=len(words))


# ----------------------------------------------------------------------------- main
def main():
    ms = D.manuscript(); nlines = len(ms['lines'])
    tok = D.tokenize(ms); cov = line_covariates(ms, tok)
    texts = all_texts(ms)
    deltas = {}
    for key, variants in texts.items():
        deltas[key] = []
        for lines in variants:
            t = D.tokenize(ms, lines)
            deltas[key].append(line_deltas(t['words'], t, nlines)[0])
    bio_pages = [p['index'] for p in ms['pages'] if p['group'] == BIO]
    all_pages = [p['index'] for p in ms['pages']]
    results = dict(
        anchors_bio=coincidence(deltas, cov, bio_pages),
        anchors_all=coincidence(deltas, cov, all_pages),
        structure_bio=anchor_structure(deltas, cov, bio_pages),
        correlation_bio=correlations(deltas, cov, bio_pages),
        correlation_all=correlations(deltas, cov, all_pages),
        concentration={'manuscript': concentration(ms, texts['manuscript'][0])},
        own_paragraph_profiles={k: own_paragraph_profile(REFS[k]) for k in ('la_hildegard_physica', 'de_gart_augsburg1487')},
    )
    results['anchors_bio']['strong_folios'] = [ms['lines'][li]['folio'] for li in results['anchors_bio']['strong_folios']]
    results['anchors_all']['strong_folios'] = [ms['lines'][li]['folio'] for li in results['anchors_all']['strong_folios']]
    for key in ('timm', 'far0', 'noinnov_far0', 'timm_spatial', 'noinnov_spatial', 'far0_spatial', 'buffer', 'pool'):
        per = [concentration(ms, lines) for lines in texts[key]]
        results['concentration'][key] = {g: {k: float(np.mean([p[g][k] for p in per])) for k in per[0][g]} for g in per[0]}
    for key in texts:
        if key.startswith('ref_'):
            results['concentration'][key] = concentration(ms, texts[key][0])
    (D.HERE / 'timing.json').write_text(json.dumps(results, indent=1), encoding='utf-8')

    # ---- print
    for scope in ('anchors_bio', 'anchors_all'):
        a = results[scope]
        print(f"\n== {scope}: {a['pages']} pages, {a['strong_pages']} with a manuscript fall <= -0.10 (mean {a['manuscript_anchor_delta_mean']:+.3f}); manuscript page floor {a['manuscript_page_floor']:.2f}")
        print(f"{'stream':26s} {'at MS anchors':>14s} {'page floor':>11s} {'other fam.':>11s} {'siblings':>9s} {'MS at stream anchors':>21s} {'mean d at MS anchors':>21s}")
        for k, r in a['streams'].items():
            sib = f"{r['declines_at_sibling_anchors']:.2f}" if r['declines_at_sibling_anchors'] is not None else '   -'
            oth = f"{r['declines_at_other_family_anchors']:.2f}" if r['declines_at_other_family_anchors'] is not None else '   -'
            print(f"{k:26s} {r['declines_at_manuscript_anchors']:14.2f} {r['page_floor']:11.2f} {oth:>11s} {sib:>9s} {r['manuscript_declines_at_stream_anchors']:21.2f} {r['mean_delta_at_manuscript_anchors']:+21.3f}")
    s = results['structure_bio']
    print(f"\n== Bio anchors of the 'opening in prior block, body only in next' type; base rate of such lines {s['base_rate']:.2f}")
    for k in deltas:
        print(f"  {k:26s} {s[k]:.2f}")
    print("  mean fall by line class (Bio, eligible lines); class shares", {c: round(v, 2) for c, v in s['class_shares'].items()})
    for k, row in s['mean_delta_by_class'].items():
        print(f"  {k:26s} " + '  '.join(f"{c}: {v:+.3f}" for c, v in row.items()))
    for scope in ('correlation_bio', 'correlation_all'):
        c = results[scope]
        print(f"\n== {scope}: {c['n_lines']} lines; layout R^2 of the fall series: " + ', '.join(f"{k} {v:.2f}" for k, v in c['layout_r2'].items() if not k.startswith('ms_')))
        for k, v in c['pairs'].items():
            print(f"  {k:40s} raw {v['raw']:+.3f}  residual {v['residual']:+.3f}")
    print("\n== shared vs local concentration (pages >= 150 tokens): coverage of a page by the GROUP's top-50 forms vs by its OWN top-50; top-20 Jaccard and cosine between pages")
    for k, res in results['concentration'].items():
        print(k)
        for g, r in res.items():
            print(f"  {g:3s} pages {r['pages']:3.0f} group-top50 {r['group_top50_coverage']:.3f} own-top50 {r['own_top50_coverage']:.3f} shared {r['shared_share']:.2f} jaccard {r['top20_jaccard']:.2f} cosine {r['page_cosine']:.2f}")
    print("\n== natural texts with their own paragraphs: fresh rate by tokens since paragraph start")
    for k, r in results['own_paragraph_profiles'].items():
        print(f"  {k:24s} paragraphs {r['paragraphs']} median {r['median_paragraph_words']:.0f} words: " + ' '.join(f"{a}:{b:.3f}" for a, b in r['profile'].items()))


if __name__ == '__main__':
    main()
