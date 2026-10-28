"""Shared loaders for the template-availability study (26 Oct 2026).

Manuscript text: the study transcription of the dynamic self-citation work
(tokens.json, 4,130 paragraph-text lines, 34,977 tokens) in Path 1 order, the same
rows every generated stream is line-aligned to. Physical structure (leaf, side,
bifolium, partner leaf) from team Golf's physical_map.csv. No EVA parsing is done
here: words are taken as the study's token strings.
"""
from collections import Counter, defaultdict
import csv
import gzip
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]   # the research workspace root when run in place; the repository root when run from the published kit


# Golf 2.1 group -> the traditional section its pages belong to (share of the group's tokens; physical_map.csv section letter,
# Herbal split by Currier language). 1a Herbal A 94% (one text-only page); 1b, 1.5a Herbal A 100%; 2a Pharma 73%, Herbal A 15%,
# Astro 9%, Cosmo 3%; 5a Cosmo; 6 Stars 94%; 3b Herbal B 84% (one text-only page); 3a Herbal B 100%; 3c Stars 81%, text-only
# pages 14%, Cosmo 5%; 4c Stars 100%; 4a Bio 92% (one text-only page).
GROUP_SECTION = {'1a': 'Herbal A', '1b': 'Herbal A', '1.5a': 'Herbal A', '2a': 'Pharma, Astro', '5a': 'Cosmo', '6': 'Stars',
                 '3b': 'Herbal B', '3a': 'Herbal B', '3c': 'Stars', '4c': 'Stars', '4a': 'Bio'}


def group_label(g, sep='\n'):
    """'3c' -> '3c\nStars': the Golf code with the traditional section name of its pages."""
    return g + sep + GROUP_SECTION[g] if g in GROUP_SECTION else g


def group_labels(groups, sep='\n'):
    """Tick labels for groups in order: the code on every tick, the section name under the first group of each stretch of one section."""
    out, prev = [], None
    for g in groups:
        name = GROUP_SECTION.get(g)
        out.append(g + sep + name.replace(', ', sep) if name and name != prev else g)
        prev = name
    return out


def src(rel):
    """A workspace-relative input, found in the first of: a data/ folder beside the scripts (the published kit's copies),
    the research workspace, the repository's reproduction kit (reproduce/, same layout), the repository root (the
    governor app's own files, which the workspace keeps under apps/selfcitation_governor/)."""
    rel = rel.replace('\\', '/')
    app = 'apps/selfcitation_governor/'
    candidates = [HERE / 'data' / rel, ROOT / rel, ROOT / 'reproduce' / rel]
    if rel.startswith(app):
        candidates.append(ROOT / rel[len(app):] if rel != app.rstrip('/') else ROOT)
    elif rel == app.rstrip('/'):
        candidates.append(ROOT)
    for c in candidates:
        if c.exists():
            return c
    return ROOT / rel


HERE = Path(__file__).resolve().parent
ASSET = src('packages/voynich_gradients/src/voynich_gradients/assets/positional_path1.json.gz')
TOKENS = src('solve/botanical_enrichment/echo7/preservation_model_20261014/data/tokens.json')
PHYS = src('solve/botanical_enrichment/team_golf/data/physical_map.csv')
GOV = src('research/dynamic_selfcitation_20261024/governed/runs')
AUDIT = src('research/timm_geometry_audit_20261026')

STREAMS = {
    # key: (label, [text sources])  sources are either run folders (generated_text.txt) or json.gz with 'lines'
    'timm': ('Original Timm (layout only)', [GOV / 'm_timm/generated_text.txt'] +
             [AUDIT / f'history_prediction/records/model{s}_source.json.gz' for s in (2, 3, 4, 5)]),
    'far0': ('Governed, page window only (far 0)', [GOV / f'm_far0{s}/generated_text.txt' for s in ('', '_s2', '_s3')]),
    'noinnov_far0': ('Hooks on page window, no innovator (far 0)', [GOV / f'n_noinnov_far0{s}/generated_text.txt' for s in ('', '_s2', '_s3')]),
    # 27 October, user's request: the same two innovator-free copiers with their page draws taken from the words physically in view
    # on the recorded page geometry (governor.py --spatial: the app's cone and left reach over the recorded rectangles, distance weights)
    'timm_spatial': ('Original Timm, sources from the words in view (spatial)', [GOV / f'p_timm_spatial{s}/generated_text.txt' for s in ('', '_s2', '_s3')]),
    'noinnov_spatial': ('Hooks on the words in view, no innovator (spatial, far 0)', [GOV / f'p_noinnov_spatial{s}/generated_text.txt' for s in ('', '_s2', '_s3')]),
    # the far-0 configuration with the innovator, brought back at the user's request in its spatial form (replaces m_far0 in the figures)
    'far0_spatial': ('Governed + innovator, sources from the words in view (spatial, far 0)', [GOV / f'p_far0_spatial{s}/generated_text.txt' for s in ('', '_s2', '_s3')]),
    'buffer': ('Governed + innovator, 100-form memory', [GOV / f'n_final{s}/generated_text.txt' for s in ('', '_s2', '_s3')]),
    'pool': ('Governed + innovator, 2,000-token pool', [GOV / f'm_final{s}/generated_text.txt' for s in ('', '_s2', '_s3')]),
}


def read_lines_txt(p):
    return [l.split() for l in Path(p).read_text(encoding='utf-8-sig').splitlines()
            if l.strip() and not l.startswith('#')]


def read_stream(p):
    p = Path(p)
    if p.suffix == '.gz':
        return json.loads(gzip.decompress(p.read_bytes()))['lines'][:4130]
    return read_lines_txt(p)[:4130]


def physical():
    rows = {}
    with open(PHYS, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            leaf = int(r['leaf']); partner = int(r['partner_leaf'])
            a, b = min(leaf, partner), max(leaf, partner)
            side = r['side']
            # a flat bifolium: inner face = A verso | B recto ; outer face = B verso | A recto
            face = 'inner' if (leaf == a and side == 'v') or (leaf == b and side == 'r') else 'outer'
            rows[r['folio']] = dict(leaf=leaf, side=side, panel=r['panel'], quire=r['quire'], bifolium=r['bifolium'],
                                    bif_pos=int(r['bif_pos']), partner=partner, A=a, B=b, face=face,
                                    section=r['section'], currier=r['currier'], hand=r['hand'])
    return rows


def manuscript():
    """Return dict with pages, lines, tokens arrays (numpy) in Path 1 order."""
    a = json.load(gzip.open(ASSET, 'rt', encoding='utf-8'))
    nodes = a['nodes']
    by = defaultdict(list)
    for line in json.loads(TOKENS.read_text(encoding='utf-8'))['lines']:
        by[line['folio']].append(line)
    phys = physical()
    pages, lines = [], []
    for node in nodes:
        for order, p in enumerate(node['pages']):
            start_line = len(lines)
            for i, line in enumerate(by[p]):
                final = i == len(by[p]) - 1
                lines.append(dict(folio=p, locus=line['locus'], words=line['words'], first=bool(line['first']),
                                  final=final, chars=len(' '.join(line['words'])), node=node['id'], group=node['group'],
                                  page=len(pages)))
            pages.append(dict(index=len(pages), folio=p, node=node['id'], group=node['group'], order_in_node=order,
                              start_line=start_line, end_line=len(lines), **phys[p]))
    return dict(nodes=nodes, pages=pages, lines=lines)


def tokenize(ms, stream_lines=None):
    """Flatten a line-aligned text (the manuscript's own when stream_lines is None) into token arrays."""
    lines = ms['lines']
    words = []; page = []; line_ix = []; pos = []; linelen = []; first_line = []; since_page = []; since_par = []
    chars_before = []; line_chars = []
    sp = 0; spar = 0; last_page = -1
    for li, L in enumerate(lines):
        ws = stream_lines[li] if stream_lines is not None else L['words']
        if L['page'] != last_page:
            sp = 0; last_page = L['page']
        if L['first']:
            spar = 0
        cb = 0
        for k, w in enumerate(ws):
            words.append(w); page.append(L['page']); line_ix.append(li); pos.append(k); linelen.append(len(ws))
            first_line.append(L['first']); since_page.append(sp); since_par.append(spar)
            chars_before.append(cb); line_chars.append(len(' '.join(ws)))
            cb += len(w) + 1; sp += 1; spar += 1
    arr = lambda x: np.asarray(x)
    return dict(words=words, page=arr(page), line=arr(line_ix), pos=arr(pos), linelen=arr(linelen),
                first_line=arr(first_line), since_page=arr(since_page), since_par=arr(since_par),
                chars_before=arr(chars_before), line_chars=arr(line_chars))


def fresh_indicator(words, w=100):
    """1 if the word did not occur among the previous w tokens (the increments of D100)."""
    last = {}
    out = np.zeros(len(words), dtype=np.int8)
    for i, x in enumerate(words):
        j = last.get(x)
        out[i] = 1 if (j is None or i - j > w) else 0
        last[x] = i
    return out


def trailing_distinct(words, w=100):
    """D_w at every position: distinct among tokens [i-w+1, i]; NaN before w tokens exist."""
    counts = Counter(); out = np.full(len(words), np.nan)
    for i, x in enumerate(words):
        counts[x] += 1
        if i >= w:
            old = words[i - w]; counts[old] -= 1
            if not counts[old]:
                del counts[old]
        if i >= w - 1:
            out[i] = len(counts) / w
    return out


def mattr(words, w=100):
    n = len(words)
    if n == 0:
        return float('nan')
    if n <= w:
        return len(set(words)) / n
    c = Counter(words[:w]); total = len(c)
    for i in range(w, n):
        old = words[i - w]; c[old] -= 1
        if not c[old]:
            del c[old]
        c[words[i]] += 1
        total += len(c)
    return total / (w * (n - w + 1))


def bag_mattr(words, w=100):
    """Exact expected MATTR_w of a uniform random permutation of the bag (hypergeometric)."""
    c = np.array(list(Counter(words).values()), dtype=float)
    n = len(words); w = min(n, w)
    if n == 0:
        return float('nan')
    sure = n - c < w
    remaining = c[~sure]
    logs = np.log1p(-remaining[:, None] / (n - np.arange(w))).sum(axis=1)
    return float((sure.sum() + (-np.expm1(logs)).sum()) / w)


def iid_mattr(probs, w=100):
    """Expected distinct share of w i.i.d. draws from a distribution."""
    p = np.asarray(list(probs), dtype=float)
    return float((1 - (1 - p) ** w).sum() / w)


def transitions(ms):
    """Consecutive page pairs in Path 1 order with their physical relation."""
    out = []
    P = ms['pages']
    for k in range(1, len(P)):
        a, b = P[k - 1], P[k]
        if a['bifolium'] != b['bifolium']:
            cls = 'cross-sheet'
        elif a['face'] == b['face']:
            cls = 'same-face'
        else:
            cls = 'flip'
        out.append(dict(index=k, prev=a['folio'], cur=b['folio'], cls=cls, group=b['group'], node=b['node'],
                        direction=f"{a['side']}>{b['side']}", same_leaf=a['leaf'] == b['leaf'],
                        prev_face=a['face'], cur_face=b['face']))
    return out


if __name__ == '__main__':
    ms = manuscript()
    tok = tokenize(ms)
    print(len(ms['pages']), 'pages', len(ms['lines']), 'lines', len(tok['words']), 'tokens')
    tr = transitions(ms)
    print(Counter(t['cls'] for t in tr))
    print(Counter((t['cls'], t['direction']) for t in tr))
    for t in tr[:12]:
        print(t)
    for key, (label, srcs) in STREAMS.items():
        for s in srcs:
            L = read_stream(s)
            assert len(L) == 4130, (s, len(L))
            n = sum(len(l) for l in L)
            print(key, Path(s).parent.name if Path(s).suffix == '.txt' else Path(s).name, len(L), 'lines', n, 'tokens')
