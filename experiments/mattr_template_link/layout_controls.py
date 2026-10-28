"""T14. Natural-language and n-gram texts in the manuscript's own layout (27 October, user's test).

If a natural-language text reflowed into the manuscript's lines, pages and word boxes shows no MATTR collapse in the
Bio layout while the self-citation generators do, the layout-driven account of the Bio fall is harder to dismiss; a
Markov (word-bigram) text in the same layout is the second control. Every text here is laid into the manuscript's
4,130 lines in Path 1 order, wrapping where the manuscript wraps, so the spatial selector of the component-impact
study (component_measure.js, the other study's own code) can be run on all of them with the same geometry:
  manuscript           recorded word rectangles
  self-citation        Original Timm (layout only), far 0, no-innovator far 0 (page window), 100-form memory,
                       2,000-token pool: the saved streams, synthetic rectangles laid by character position
  natural prose, box   one word per manuscript word box (same word count per line; recorded rectangles)
  natural prose, line  each line filled to the manuscript line's character budget (word counts differ; synthetic
                       rectangles); wraps at the same places
  bigram, whole        word-bigram chain trained on the whole manuscript (stationary along the route), one word
                       per box, recorded rectangles
  bigram, Currier      one bigram chain for Currier A pages and one for Currier B pages
  bigram, section      one bigram chain per section (Herbal, Bio, Stars, Pharma, ...)
                       (no chain consults position, line, page or geometry; words are laid into the layout afterwards)
Measures per text and Golf group: MATTR100 of the group's text in route order, the exact shuffled-bag expectation
(bag100), their gap (clustering beyond the bag); the two late steps 3c -> 4c -> 4a split into bag and clustering
parts; and the spatial-cone statistic of section 7 (lowest-against-highest diversity quintile of the words in view,
difference in word impact) for all bifolia, 3c and Bio.
"""
from collections import Counter, defaultdict
import gzip
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import data as D
import component_check as CC
from decompose import REFS, ref_words
from timing import laid_in

rng = np.random.default_rng(20261027)
GROUPS = ['1a', '1b', '1.5a', '2a', '5a', '6', '3b', '3a', '3c', '4c', '4a']
PROSE = ('la_galen_simplicium', 'la_dioscorides_longob', 'la_rhazes_almansor', 'la_hildegard_physica', 'de_gart_augsburg1487')
SEEDS = 2
BIGRAM_SEEDS = 3


def fill_by_chars(ms, words):
    """Lay words into the manuscript's lines, each line filled to its own character budget (at least one word)."""
    need = sum(L['chars'] for L in ms['lines']) // 4 + 10  # generous bound on the words consumed
    start = int(rng.integers(0, max(1, len(words) - need)))
    seq = words[start:]
    out = []
    at = 0
    for L in ms['lines']:
        cap = L['chars']
        line = [seq[at]]
        used = len(seq[at])
        at += 1
        while at < len(seq) and used + 1 + len(seq[at]) <= cap:
            line.append(seq[at])
            used += 1 + len(seq[at])
            at += 1
        out.append(line)
    if at >= len(seq):
        raise ValueError('text too short for the character-budget fill')
    return out


class Bigram:
    """Interpolated word-bigram sampler: P(w | prev) = (c(prev, w) + a p1(w)) / (c(prev) + a)."""

    def __init__(self, words, a=1.0):
        self.a = a
        self.uni = Counter(words)
        self.vocab = np.array(list(self.uni), dtype=object)
        self.p1 = np.array([self.uni[w] for w in self.vocab], dtype=float)
        self.p1 /= self.p1.sum()
        self.index = {w: i for i, w in enumerate(self.vocab)}
        self.big = defaultdict(Counter)
        for x, y in zip(words[:-1], words[1:]):
            self.big[x][y] += 1
        self.cache = {}
        self.prev = None

    def dist(self, prev):
        if prev not in self.cache:
            c = self.big.get(prev)
            if not c:
                self.cache[prev] = self.p1
            else:
                p = self.a * self.p1.copy()
                for w, k in c.items():
                    p[self.index[w]] += k
                self.cache[prev] = p / p.sum()
        return self.cache[prev]

    def draw(self, n):
        out = []
        for _ in range(n):
            w = self.vocab[rng.choice(len(self.vocab), p=self.dist(self.prev))]
            out.append(w)
            self.prev = w
        return out


def bigram_whole(ms):
    model = Bigram([w for L in ms['lines'] for w in L['words']])
    return [model.draw(len(L['words'])) for L in ms['lines']]


def bigram_by(ms, class_of):
    """One bigram model per class of lines (class_of(line) -> label), each generating the lines of its class; the
    chains never consult position, line, page or geometry."""
    classes = {}
    for L in ms['lines']:
        classes.setdefault(class_of(L), []).extend(L['words'])
    models = {c: Bigram(ws) for c, ws in classes.items()}
    return [models[class_of(L)].draw(len(L['words'])) for L in ms['lines']]


def currier_of(ms):
    """Currier language of a line's page from the physical map; pages without a label take their Golf side."""
    a_side = {'1a', '1b', '1.5a', '2a'}

    def f(L):
        c = ms['pages'][L['page']]['currier']
        return c if c in ('A', 'B') else ('A' if L['group'] in a_side else 'B')
    return f


def section_of_line(ms):
    """Section letter of a line's page from the physical map (H, B, S, P, C, T, A, ...)."""
    return lambda L: ms['pages'][L['page']]['section']


MARKOV = (('bigram_whole', None), ('bigram_currier', 'currier'), ('bigram_section', 'section'))


def markov_text(ms, kind):
    if kind is None:
        return bigram_whole(ms)
    return bigram_by(ms, currier_of(ms) if kind == 'currier' else section_of_line(ms))


def group_table(ms, line_words):
    words_by = defaultdict(list)
    for L, ws in zip(ms['lines'], line_words):
        words_by[L['group']] += list(ws)
    out = {}
    for g in GROUPS:
        ws = words_by[g]
        m = D.mattr(ws)
        b = D.bag_mattr(ws)
        out[g] = dict(tokens=len(ws), mattr100=m, bag100=b, gap=b - m)
    steps = {}
    for a, b in (('3c', '4c'), ('4c', '4a'), ('3c', '4a')):
        steps[f'{a}->{b}'] = dict(actual=out[b]['mattr100'] - out[a]['mattr100'], bag=out[b]['bag100'] - out[a]['bag100'],
                                  clustering=(out[a]['gap'] - out[b]['gap']))
    # per bifolium (Path 1 order), for the route figure by bifolium
    by_node = defaultdict(list)
    for L, ws in zip(ms['lines'], line_words):
        by_node[L['node']] += list(ws)
    nodes = {}
    for n in ms['nodes']:
        ws = by_node[n['id']]
        m = D.mattr(ws)
        b = D.bag_mattr(ws)
        nodes[n['id']] = dict(group=n['group'], tokens=len(ws), mattr100=m, bag100=b, gap=b - m)
    return dict(groups=out, steps=steps, nodes=nodes)


def spatial(ms, line_words, geometry, comp_fn):
    inp = CC.make_input(ms, line_words, geometry, comp_fn)
    meas = CC.measure(inp)
    node, group, bstart, bend = CC.token_meta(ms, line_words)
    out = CC.outcomes(inp['words'], bstart, bend)
    base = out['full'] & np.isfinite(meas['components'])
    res = {}
    for name, gs in (('all', None), ('3c', {'3c'}), ('4a', {'4a'})):
        mask = base if gs is None else base & np.isin(group, list(gs))
        res[name] = {p: CC.quintile_contrast(meas[p], out['app_impact'], node, mask, reps=1000) for p in ('components', 'worddiv')}
        res[name]['lobo_components'] = CC.lobo_linear(meas['components'], out['app_impact'], node, mask)
        res[name]['mean_impact'] = float(np.nanmean(out['app_impact'][mask]))
    return res


def main():
    ms = D.manuscript()
    app = json.load(gzip.open(CC.APP, 'rt', encoding='utf8'))
    ms_lines = [L['words'] for L in ms['lines']]
    frames = CC.line_frames(app, ms)
    flags = CC.oversized_flags(app, ms)
    clean = [None if flags[i] else g for i, g in enumerate(app['geometry'])]
    page_sizes = [sum(len(ms['lines'][l]['words']) for l in range(p['start_line'], p['end_line'])) for p in ms['pages']]
    letters = lambda w: list(w)

    texts = {'manuscript': [(ms_lines, app['geometry'], CC.zattera)]}
    for key, (label, srcs) in D.STREAMS.items():
        texts[key] = []
        for s in srcs[:SEEDS]:
            lines = D.read_stream(s)
            texts[key].append((lines, CC.synthetic_geometry(lines, frames, ms), CC.zattera))
    for key in PROSE:
        words = ref_words(REFS[key])
        if len(words) >= sum(page_sizes) + 10:
            lines = laid_in(ms, words, page_sizes)
            texts['prose_box_' + key] = [(lines, clean, letters)]
            lines2 = fill_by_chars(ms, words)
            texts['prose_line_' + key] = [(lines2, CC.synthetic_geometry(lines2, frames, ms), letters)]
    for name, kind in MARKOV:
        texts[name] = []
        for _ in range(BIGRAM_SEEDS):
            texts[name].append((markov_text(ms, kind), clean, CC.zattera))

    results = {}
    for key, variants in texts.items():
        per = []
        for lines, geom, comp in variants:
            per.append(dict(tokens=sum(len(l) for l in lines), route=group_table(ms, lines), spatial=spatial(ms, lines, geom, comp)))
        results[key] = per
        print(key, 'done', flush=True)
    (HERE / 'layout_controls.json').write_text(json.dumps(results, indent=1, default=float), encoding='utf-8')

    def mean(per, path):
        vals = []
        for r in per:
            v = r
            for k in path:
                v = v[k]
            vals.append(v)
        return float(np.mean(vals))

    print('\n== MATTR100 by Golf group along Path 1 (route order), mean over seeds; bag100 in brackets for 3c, 4c, 4a')
    print(f"  {'text':36s} " + ' '.join(f"{g:>6s}" for g in GROUPS) + '   3c/4c/4a bag100')
    for key, per in results.items():
        row = ' '.join(f"{mean(per, ['route', 'groups', g, 'mattr100']):6.3f}" for g in GROUPS)
        bags = ' '.join(f"{mean(per, ['route', 'groups', g, 'bag100']):.3f}" for g in ('3c', '4c', '4a'))
        print(f"  {key:36s} {row}   [{bags}]")
    print('\n== late steps: actual change = bag change + clustering change (positive clustering = more repeats beyond the bag)')
    print(f"  {'text':36s} " + ' '.join(f"{s:>30s}" for s in ('3c->4c', '4c->4a', '3c->4a')))
    for key, per in results.items():
        cells = []
        for s in ('3c->4c', '4c->4a', '3c->4a'):
            cells.append(f"{mean(per, ['route', 'steps', s, 'actual']):+.3f} = {mean(per, ['route', 'steps', s, 'bag']):+.3f} {mean(per, ['route', 'steps', s, 'clustering']):+.3f}".rjust(30))
        print(f"  {key:36s} " + ' '.join(cells))
    print('\n== gap (bag100 - mattr100) by group: clustering beyond the bag')
    print(f"  {'text':36s} " + ' '.join(f"{g:>6s}" for g in GROUPS))
    for key, per in results.items():
        print(f"  {key:36s} " + ' '.join(f"{mean(per, ['route', 'groups', g, 'gap']):+6.3f}" for g in GROUPS))
    print('\n== spatial cone (section 7 statistic): lowest minus highest diversity quintile, word impact; components | word diversity; all / 3c / Bio; LOBO components, all')
    for key, per in results.items():
        cells = []
        for region in ('all', '3c', '4a'):
            cells.append(f"{mean(per, ['spatial', region, 'components', 'diff']):+.3f} | {mean(per, ['spatial', region, 'worddiv', 'diff']):+.3f}")
        print(f"  {key:36s} " + '   '.join(cells) + f"   LOBO {mean(per, ['spatial', 'all', 'lobo_components']):+.2f}%  mean impact {mean(per, ['spatial', 'all', 'mean_impact']):.3f}")


if __name__ == '__main__':
    main()
