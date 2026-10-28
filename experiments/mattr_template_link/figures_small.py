"""Small figures, one message each (replacing the oversized composites):
  method_mattr.png        what MATTR100, bag100 and the clustering gap are (text with a drawn window)
  route_mattr.png         MATTR100 by group for every text laid into the manuscript's lines
  route_bifolia.png       the same bifolium by bifolium along Path 1, with a zoom on the 3b -> 3a -> 3c -> 4c -> 4a chain
  fall_split.png          the fall from Stars to Bio split into bag change and clustering change
  method_spatial.png      a capture of the governor app (f78r, word otedy selected, spatial sources, component diversity); not drawn here
  contrast_all.png        the pool-size-stratified contrast, all targets, three measures on one chart
  contrast_by_length.png  the same for short and long targets (dumbbells), three measures on one chart
  contrast_by_section.png the contrast inside each section (Herbal A, Herbal B, Pharma, Stars, Bio, text-only pages), six panels
  contrast_by_group.png   the contrast inside each Golf 2.1 group (1a ... 4a), nine panels; *_components_h2 versions omit word diversity
  coupling.png            MATTR against the pool scores, token level and page means, three measures on one chart
Colour marks the CLASS of text only: manuscript black, self-citation generators blue, Markov chains green, natural
language orange (validated palette slots 1, 6, 2). Marker shape marks the pool measure (circle word diversity, square
component diversity, triangle glyph H2); line style separates texts inside a class in the route figures."""
import json
import sys
import textwrap

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle, Polygon
import numpy as np

sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
import data as D
from figures import INK, SEC, MUTED, GRID, SURF
plt.rcParams.update({'font.size': 7.5, 'axes.titlesize': 9, 'axes.labelsize': 7.5, 'xtick.labelsize': 7, 'ytick.labelsize': 7, 'legend.fontsize': 7})

C_MS, C_GEN, C_MARKOV, C_NAT = INK, '#2a78d6', '#008300', '#eb6834'
CLASS_NAMES = {C_MS: 'manuscript', C_GEN: 'self-citation generator', C_MARKOV: 'Markov chain', C_NAT: 'natural language (German, 1487)'}
SHOW = ['1a', '1b', '1.5a', '2a', '3b', '3a', '3c', '4c', '4a']
MEASURES = (('worddiv', 'word diversity'), ('components', 'component diversity'), ('h2', 'glyph H2'))
MARK = {'worddiv': 'o', 'components': 's', 'h2': '^'}
XLABEL_CONTRAST = ('difference between two repeat rates: words whose pool in view is least diverse  minus  words whose pool is most diverse\n'
                   '\u25c4 negative: fewer repeats after a less diverse pool            positive: more repeats after a less diverse pool \u25ba')
SUBTITLE_ALL = ('Each word gets a repeat score: the share of the 100-word windows containing it in which its spelling occurs again (0 = never repeated nearby, 1 = always).\n'
                'Within each bifolium the words are sorted by how diverse the words in view above and to their left are, and split into fifths.\n'
                'Marker = mean repeat score of the fifth with the LEAST diverse pool minus the mean of the fifth with the MOST diverse pool (averaged over pool-size tertiles and bifolia).')
SUBTITLE_LEN = ('The same statistic computed inside two word-length classes: targets of three letters or fewer (open markers) and six or more (filled).\n'
                'Marker = mean repeat score after the least diverse pool minus after the most diverse pool, within the class.')
OFF = {'worddiv': 0.27, 'components': 0.0, 'h2': -0.27}
# rows with class headers (key None)
ROWS = [(None, 'MANUSCRIPT', C_MS), ('manuscript', 'as written', C_MS), ('manuscript_shuffled_paragraphs', 'words shuffled inside paragraphs', C_MS),
        ('manuscript_shuffled_pages', 'words shuffled inside pages', C_MS),
        (None, 'SELF-CITATION GENERATORS', C_GEN), ('timm', 'Original Timm', C_GEN), ('noinnov_far0', 'Far 0 without innovator (page-window copier)', C_GEN),
        ('timm_spatial', 'Original Timm, sources from the words in view', C_GEN), ('noinnov_spatial', 'Far 0 without innovator, sources from the words in view', C_GEN),
        ('far0_spatial', 'Far 0 with innovator, sources from the words in view', C_GEN),
        (None, 'MARKOV CHAINS', C_MARKOV), ('bigram_whole', 'Markov chain, whole manuscript', C_MARKOV), ('bigram_currier', 'Markov chains, Currier A / B', C_MARKOV),
        ('bigram_section', 'Markov chains, by section', C_MARKOV),
        (None, 'NATURAL LANGUAGE (GART 1487)', C_NAT), ('gart_own_lines', 'its own printed lines', C_NAT), ('gart_character_budget', 'character-budget fill', C_NAT),
        ('gart_one_word_per_box', 'one word per manuscript box', C_NAT)]
SERIES = [('manuscript', 'Manuscript, MATTR100', C_MS, '-', 2.0, True), ('timm', 'Original Timm', C_GEN, '-', 1.8, True),
          ('noinnov_far0', 'Far 0 without innovator', C_GEN, (0, (4, 2)), 1.8, False), ('bigram_whole', 'Markov chain, whole manuscript', C_MARKOV, (0, (2, 2)), 1.6, False),
          ('bigram_currier', 'Markov chains, Currier A / B', C_MARKOV, (0, (5, 2, 1, 2)), 1.6, True), ('bigram_section', 'Markov chains, by section', C_MARKOV, '-', 1.6, True)]
# the four innovator-free copiers: Timm's own page draw against the draw from the words in view (route_mattr_spatial)
SERIES_SPATIAL = [('manuscript', 'Manuscript, MATTR100', C_MS, '-', 2.0, True), ('timm', 'Original Timm (his own page draw)', C_GEN, '-', 1.8, True),
                  ('timm_spatial', 'Original Timm, sources from the words in view', C_GEN, (0, (1, 1.6)), 2.0, True),
                  ('noinnov_far0', 'Far 0 without innovator (page window)', C_GEN, (0, (4, 2)), 1.8, False),
                  ('noinnov_spatial', 'Far 0 without innovator, sources from the words in view', C_GEN, (0, (4, 2, 1, 2)), 1.8, False),
                  ('far0_spatial', 'Far 0 with innovator, sources from the words in view', C_GEN, (0, (2, 1.5)), 1.6, False)]


def mean(per, path):
    vals = []
    for r in per:
        v = r
        for k in path:
            v = v[k]
        vals.append(v)
    return float(np.mean(vals))


def note(fig, text, y=0.01, width=130):
    return  # explanations are in RESULTS.md, not in the image


def save(fig, name):
    import time
    for ext, kw in (('png', dict(dpi=150)), ('svg', {})):
        for attempt in range(4):       # a viewer holding the file open makes Windows refuse the write for a moment
            try:
                fig.savefig(D.HERE / f'{name}.{ext}', bbox_inches='tight', **kw)
                break
            except OSError as e:
                if attempt == 3:
                    print(f'could not write {name}.{ext}: {e}')
                else:
                    time.sleep(1.5)
    plt.close(fig)


def style_headers(ax):
    for lbl in ax.get_yticklabels():
        if lbl.get_text().isupper():
            lbl.set_fontweight('bold')
            lbl.set_fontsize(8.5)
            lbl.set_color(INK)


def measure_legend(ax, extra=(), loc='upper right'):
    handles = [Line2D([], [], marker=MARK[m], color=SEC, linestyle='none', markersize=5.2, label=lab) for m, lab in MEASURES] + list(extra)
    ax.legend(handles=handles, frameon=False, fontsize=7.3, loc=loc)


# ---------------------------------------------------------------- method figures
def method_mattr():
    fig, ax = plt.subplots(figsize=(8, 2.4))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 8)
    ax.axis('off')
    rng = np.random.default_rng(3)
    words = rng.choice(['daiin', 'chol', 'shedy', 'qokeedy', 'ol', 'chedy', 'dar', 'okaiin', 'sol', 'cthy'], size=22, p=[.18, .14, .12, .1, .1, .08, .08, .08, .06, .06])
    seen = set()
    for i, w in enumerate(words):
        rep = w in seen
        seen.add(w)
        ax.add_patch(Rectangle((2 + i * 4.3, 5.4), 3.9, 1.5, facecolor=C_GEN if rep else SURF, edgecolor=SEC, linewidth=0.8))
        ax.text(3.95 + i * 4.3, 6.15, w, ha='center', va='center', fontsize=5.6, color=SURF if rep else INK)
    ax.annotate('', xy=(2, 7.4), xytext=(2 + 22 * 4.3, 7.4), arrowprops=dict(arrowstyle='<->', color=SEC, lw=0.9))
    ax.text(2 + 11 * 4.3, 7.6, 'one window of 100 consecutive tokens (22 drawn); blue = a spelling already seen in the window', ha='center', fontsize=7.3, color=SEC)
    lines = ['MATTR100 of a text  =  mean over all its 100-token windows of  (distinct spellings in the window) / 100.',
             'bag100  =  the same mean expected if the text\'s words were shuffled at random (exact value for its word bag).',
             'gap  =  bag100 − MATTR100:  repeats sitting closer together than a shuffle would put them (clustering).',
             'A step between two groups splits exactly into a bag change (bag100 moves: different words in use) and a clustering change (the gap moves).']
    for k, t in enumerate(lines):
        ax.text(2, 4.3 - k * 1.05, t, fontsize=7.8, color=INK)
    ax.text(2, 0.1, 'Every text in the route figures occupies the manuscript\'s own lines and pages in Path 1 order, so the layout is the same for all; only the words differ.', fontsize=7.3, color=SEC)
    ax.set_title('What is measured: MATTR100, its shuffled-bag expectation, and the gap between them', loc='left', fontsize=7.8, color=INK)
    save(fig, 'method_mattr')


def method_spatial():
    fig = plt.figure(figsize=(8.6, 4.5))
    ax = fig.add_axes([0.01, 0.12, 0.5, 0.78])
    pitch, bh = 6.0, 4.4
    ax.set_aspect('equal')
    ax.set_xlim(-1, 56)
    ax.set_ylim(-2, 7 * pitch + 3)
    ax.axis('off')
    rng = np.random.default_rng(11)
    rows = []
    for r in range(7):
        xs = []
        xpos = 1 + rng.uniform(0, 1.5)
        while xpos < 50:
            w = rng.uniform(3.5, 7.5)
            xs.append((xpos, w))
            xpos += w + 1.0
        rows.append(xs)
    row_y = lambda r: (6 - r) * pitch
    target_row, target_idx = 5, 3
    tx0, tw = rows[target_row][target_idx]
    tcx = tx0 + tw / 2
    apex = (tcx, row_y(target_row) + bh / 2)
    depth = 5 * pitch + 0.5    # five rows drawn; the real cone is 8 line spacings deep
    ax.add_patch(Polygon([apex, (tcx - depth, apex[1] + depth), (tcx + depth, apex[1] + depth)], closed=True, facecolor=C_GEN, alpha=0.10,
                         edgecolor=C_GEN, linewidth=1.0, linestyle=(0, (3, 2))))
    reach = 3 * 5.5
    ax.plot([tcx - reach, tcx], [apex[1], apex[1]], color=C_GEN, linewidth=1.3, linestyle=(0, (3, 2)))
    for r, xs in enumerate(rows):
        for i, (x0, w) in enumerate(xs):
            y = row_y(r)
            cx = x0 + w / 2
            if r == target_row and i == target_idx:
                face, edge = INK, INK
            elif r < target_row:
                dy = (y + bh / 2) - apex[1]
                in_cone = 0 < dy <= depth and (abs(cx - tcx) - w / 2) <= dy
                face, edge = (C_GEN, C_GEN) if in_cone else (SURF, MUTED)
            elif r == target_row and i < target_idx and (tcx - cx) <= reach:
                face, edge = C_GEN, C_GEN
            else:
                face, edge = SURF, MUTED
            ax.add_patch(Rectangle((x0, y), w, bh, facecolor=face, edgecolor=edge, linewidth=0.8, alpha=0.9 if face == C_GEN else 1))
    ax.text(tcx, row_y(target_row) - 1.0, 'N', ha='center', va='top', fontsize=7.3, color=INK, fontweight='bold')
    ax.text(27, 7 * pitch + 1.5, 'cone: 8 line spacings up, 45° half-angle (5 drawn)', fontsize=7.3, color=C_GEN, ha='center', va='bottom')
    ax.text(tcx - reach - 0.5, row_y(target_row) + bh + 0.5, '3 word widths to the left', fontsize=7, color=C_GEN, ha='left', va='bottom')
    fig.text(0.02, 0.03, textwrap.fill('blue: the pool of N, earlier words on the same page whose box meets the cone or the left reach (at most 100, weighted by closeness). '
                                       'white: not in the pool. The words below N are not yet written.', 85), fontsize=7.2, color=SEC, va='bottom')
    steps = [('1', 'Pool of N: the blue words.'),
             ('2', 'Three scores of the pool. Word diversity = 1 − Σ p(spelling)². Component diversity = 2 ^ entropy of the within-word unit pairs. Glyph H2 = conditional entropy of the next unit. (Zattera units for Voynich text, letters for German.)'),
             ('3', 'Is N a repeat? Its repeat share = the share of the 100-token windows containing N in which N\'s spelling occurs again (0 to 1; the app calls this word impact).'),
             ('4', 'Contrast: inside each bifolium, split the words into quintiles of the pool score; mean repeat share of the lowest quintile minus the highest; pool over bifolia. Done inside three pool-size tertiles and averaged, because pool size itself predicts repetition.'),
             ('5', 'Length split: the same contrast for targets of 3 letters or fewer and of 6 or more. An association found only between the two classes is a word-length effect, not a within-class one.')]
    y = 0.90
    for num, t in steps:
        wrapped = textwrap.fill(t, 66)
        fig.text(0.545, y, num, fontsize=7.3, color=C_GEN, fontweight='bold', va='top')
        fig.text(0.57, y, wrapped, fontsize=7.6, color=INK, va='top', linespacing=1.3)
        y -= 0.034 * (wrapped.count('\n') + 1) + 0.04
    fig.suptitle('How the spatial statistic is built, for every word N of a text laid into the manuscript\'s pages', x=0.02, ha='left', fontsize=7.8, color=INK)
    save(fig, 'method_spatial_schematic')


# ---------------------------------------------------------------- MATTR along the route
def class_legend_handles(prose_label):
    return [Line2D([], [], color=C_MS, linewidth=2.4, label='Manuscript, MATTR100'), Line2D([], [], color=C_MS, linewidth=1.4, linestyle=(0, (2, 2)), label='Manuscript, bag100 (shuffled-bag expectation)'),
            Line2D([], [], color=C_GEN, linewidth=1.8, marker='o', markersize=4, label='Original Timm (self-citation)'),
            Line2D([], [], color=C_GEN, linewidth=1.8, linestyle=(0, (4, 2)), marker='o', markerfacecolor=SURF, markersize=4, label='Far 0 without innovator (page-window copier)'),
            Line2D([], [], color=C_MARKOV, linewidth=1.6, linestyle=(0, (2, 2)), marker='o', markerfacecolor=SURF, markersize=4, label='Markov chain, whole manuscript'),
            Line2D([], [], color=C_MARKOV, linewidth=1.6, linestyle=(0, (5, 2, 1, 2)), marker='o', markersize=4, label='Markov chains, Currier A / B'),
            Line2D([], [], color=C_MARKOV, linewidth=1.6, marker='o', markersize=4, label='Markov chains, by section'),
            Patch(facecolor=C_NAT, alpha=0.18, label=prose_label)]


def route_mattr(R, series=SERIES, name='route_mattr'):
    prose = [k for k in R if k.startswith('prose_')]
    fig, ax = plt.subplots(figsize=(7.6, 4.6))
    x = np.arange(len(SHOW))
    ax.axvspan(SHOW.index('3c') - 0.5, SHOW.index('4a') + 0.5, color=GRID, alpha=0.55, linewidth=0, zorder=0)
    ax.text(SHOW.index('3c') - 0.42, 0.915, 'Stars → Bio layout', fontsize=7.6, color=SEC, va='top')
    lo = [min(mean(R[k], ['route', 'groups', g, 'mattr100']) for k in prose) for g in SHOW]
    hi = [max(mean(R[k], ['route', 'groups', g, 'mattr100']) for k in prose) for g in SHOW]
    ax.fill_between(x, lo, hi, color=C_NAT, alpha=0.18, linewidth=0)
    bag = [mean(R['manuscript'], ['route', 'groups', g, 'bag100']) for g in SHOW]
    ax.plot(x, bag, color=C_MS, linestyle=(0, (2, 2)), linewidth=1.4, zorder=2)
    ends = [(bag[-1], 'Manuscript, bag100', C_MS), ((lo[-1] + hi[-1]) / 2, 'natural language (range)', C_NAT)]
    for key, lab, col, ls, lw, filled in series:
        y = [mean(R[key], ['route', 'groups', g, 'mattr100']) for g in SHOW]
        ax.plot(x, y, color=col, linestyle=ls, linewidth=lw, marker='o', markersize=3, markerfacecolor=col if filled else SURF, markeredgewidth=1.4, zorder=3)
        ends.append((y[-1], lab, col))
    ends.sort()
    ys = [e[0] for e in ends]
    for i in range(1, len(ys)):
        if ys[i] - ys[i - 1] < 0.026:
            ys[i] = ys[i - 1] + 0.026
    for (y0, lab, col), yy in zip(ends, ys):
        ax.annotate(lab, xy=(x[-1] + 0.06, y0), xytext=(x[-1] + 0.3, yy), fontsize=7.3, color=col, va='center', arrowprops=dict(arrowstyle='-', color=GRID, lw=0.8))
    ax.set_xticks(x)
    ax.set_xticklabels(D.group_labels(SHOW), fontsize=7.6)
    ax.set_xlim(-0.5, len(SHOW) + 2.6)
    ax.set_ylim(0.6, 0.93)
    ax.set_xlabel('Golf 2.1 group along Path 1 (route order); the section is named at the start of each stretch')
    ax.set_ylabel("MATTR100 of the group's text")
    ax.grid(axis='y', color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    if series is SERIES:
        handles = class_legend_handles('natural language, 5 texts × 2 reflows (range)')
        title = "MATTR100 by group, every text laid into the manuscript's lines"
    else:
        from matplotlib.patches import Patch
        handles = [Line2D([], [], color=col, linestyle=ls, linewidth=lw, marker='o', markersize=3, markerfacecolor=col if filled else SURF, label=lab) for key, lab, col, ls, lw, filled in series]
        handles += [Line2D([], [], color=C_MS, linestyle=(0, (2, 2)), linewidth=1.4, label='Manuscript, bag100 (shuffled-bag expectation)'), Patch(facecolor=C_NAT, alpha=0.18, label='natural language, 5 texts × 2 reflows (range)')]
        title = "MATTR100 by group: the copiers with Timm's page draw and with the draw from the words in view"
    ax.legend(handles=handles, frameon=False, fontsize=7.0, loc='upper center', bbox_to_anchor=(0.5, -0.2), ncol=3)
    ax.set_title(title, loc='left', fontsize=7.8, color=INK)
    note(fig, 'Black = manuscript, blue = self-citation generators, green = Markov chains (no layout), orange = natural language. Natural prose and the whole-manuscript and Currier chains '
              'cannot respond to the layout and stay flat into Bio. The page copiers fall into Bio. The manuscript falls too, and stays 0.02 to 0.05 below its own bag100 throughout, as the section chain does.',
         y=-0.21, width=140)
    save(fig, name)


def route_bifolia(R, ms):
    nodes = ms['nodes']
    ids = [n['id'] for n in nodes]
    groups = [n['group'] for n in nodes]
    prose = [k for k in R if k.startswith('prose_')]
    if 'nodes' not in R['manuscript'][0]['route']:
        print('route data has no per-bifolium values yet; run layout_controls.py first')
        return

    def series(key, field='mattr100'):
        return np.array([mean(R[key], ['route', 'nodes', i, field]) for i in ids])
    lo = np.min([series(k) for k in prose], axis=0)
    hi = np.max([series(k) for k in prose], axis=0)
    first_3b = groups.index('3b')
    fig, axes = plt.subplots(2, 1, figsize=(8.4, 6.6), gridspec_kw=dict(height_ratios=[1, 1.15], hspace=0.45))
    for ax, (a, b) in zip(axes, ((0, len(ids)), (first_3b, len(ids)))):
        x = np.arange(a, b)
        start = a
        for i in range(a + 1, b + 1):
            if i == b or groups[i] != groups[start]:
                if groups[start] in ('1b', '2a', '6', '3a', '4c'):
                    ax.axvspan(start - 0.5, i - 0.5, color=GRID, alpha=0.45, linewidth=0, zorder=0)
                ax.text((start + i - 1) / 2, 0.935, groups[start], ha='center', va='top', fontsize=7.3, color=SEC)
                start = i
        ax.fill_between(x, lo[a:b], hi[a:b], color=C_NAT, alpha=0.18, linewidth=0)
        ax.plot(x, series('manuscript', 'bag100')[a:b], color=C_MS, linestyle=(0, (2, 2)), linewidth=1.3, zorder=2)
        for key, lab, col, ls, lw, filled in SERIES:
            ax.plot(x, series(key)[a:b], color=col, linestyle=ls, linewidth=lw, marker='o', markersize=3, markerfacecolor=col if filled else SURF, markeredgewidth=1.2, zorder=3)
        ax.set_xlim(a - 0.6, b - 0.4)
        ax.set_ylim(0.55, 0.95)
        ax.grid(axis='y', color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
        ax.set_ylabel("MATTR100 of the bifolium's text")
    axes[0].set_xticks(np.arange(0, len(ids), 2))
    axes[0].set_xticklabels([ids[i] for i in range(0, len(ids), 2)], rotation=90, fontsize=5.6)
    axes[0].set_title('All 50 bifolia in Path 1 order (shaded bands alternate the Golf groups)', loc='left', fontsize=7.6, color=INK)
    axes[1].set_xticks(np.arange(first_3b, len(ids)))
    axes[1].set_xticklabels(ids[first_3b:], rotation=90, fontsize=7)
    axes[1].set_title('The 3b → 3a (Herbal B) → 3c → 4c (Stars) → 4a (Bio) chain', loc='left', fontsize=7.6, color=INK)
    axes[1].set_xlabel('bifolium (Path 1 order)')
    axes[1].legend(handles=class_legend_handles('natural language, 10 reflows (range)'), frameon=False, fontsize=7.2, loc='upper center', bbox_to_anchor=(0.5, -0.32), ncol=4)
    fig.suptitle("MATTR100 bifolium by bifolium: every text laid into the manuscript's lines", x=0.02, ha='left', fontsize=9.5, color=INK)
    note(fig, 'Black = manuscript, blue = self-citation generators, green = Markov chains, orange = natural language. Each point is one bifolium\'s text in route order. The manuscript and its bag100 '
              'move together bifolium by bifolium, inside the chain as elsewhere; the page copiers move with the layout; the whole-manuscript and Currier chains and natural prose stay flat.',
         y=-0.03, width=160)
    save(fig, 'route_bifolia')


def fall_split(R):
    prose = [k for k in R if k.startswith('prose_')]
    rows = [(None, 'MANUSCRIPT', C_MS), ('manuscript', 'as written', C_MS), (None, 'SELF-CITATION GENERATORS', C_GEN), ('timm', 'Original Timm', C_GEN),
            ('noinnov_far0', 'Far 0 without innovator', C_GEN),
            ('timm_spatial', 'Original Timm, sources from the words in view', C_GEN), ('noinnov_spatial', 'Far 0 without innovator, sources from the words in view', C_GEN),
            ('far0_spatial', 'Far 0 with innovator, sources from the words in view', C_GEN),
            (None, 'MARKOV CHAINS', C_MARKOV), ('bigram_whole', 'Markov chain, whole manuscript', C_MARKOV), ('bigram_currier', 'Markov chains, Currier A / B', C_MARKOV),
            ('bigram_section', 'Markov chains, by section', C_MARKOV), (None, 'NATURAL LANGUAGE', C_NAT), ('prose', '5 texts × 2 reflows', C_NAT)]
    fig, ax = plt.subplots(figsize=(7, 4.3))
    yb = np.arange(len(rows))[::-1]
    for yy, (key, lab, col) in zip(yb, rows):
        if key is None:
            continue
        if key == 'prose':
            vals = [mean(R[k], ['route', 'steps', '3c->4a', 'actual']) for k in prose]
            ax.plot(vals, [yy] * len(vals), linestyle='none', marker='o', markersize=5, color=C_NAT, markerfacecolor=SURF, markeredgewidth=1.3)
            ax.text(max(vals) + 0.006, yy, 'no fall', va='center', fontsize=7.3, color=SEC)
            continue
        b = mean(R[key], ['route', 'steps', '3c->4a', 'bag'])
        c = mean(R[key], ['route', 'steps', '3c->4a', 'clustering'])
        ax.barh(yy, b, left=0, color=col, height=0.6, edgecolor=SURF, linewidth=1.2)
        if (c < 0) == (b < 0):
            ax.barh(yy, c, left=b, color=col, height=0.6, edgecolor=SURF, linewidth=1.2, hatch='////', alpha=0.55)
            leftmost = min(0, b + c)
        else:
            ax.barh(yy, c, left=0, color=col, height=0.6, edgecolor=SURF, linewidth=1.2, hatch='////', alpha=0.55)
            leftmost = min(0, b, c)
        ax.text(leftmost - 0.004, yy, f'{b + c:+.3f}', va='center', ha='right', fontsize=7.3, color=SEC)
    ax.axvline(0, color=MUTED, linewidth=1)
    ax.set_yticks(yb)
    ax.set_yticklabels([r[1] for r in rows], fontsize=7.6)
    style_headers(ax)
    ax.set_xlim(-0.18, 0.08)
    ax.set_xticks([-0.15, -0.10, -0.05, 0, 0.05])
    ax.set_xlabel('change in MATTR100 from Stars (3c) to Bio (4a)')
    ax.grid(axis='x', color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.legend(handles=[Patch(facecolor=SEC, edgecolor=SURF, label='bag change (different words in use)'),
                       Patch(facecolor=SEC, alpha=0.55, hatch='////', edgecolor=SURF, label='clustering change (same words, arranged more closely)')],
              frameon=False, fontsize=7.3, loc='lower left')
    ax.set_title('The fall from Stars to Bio: bag change against clustering change', loc='left', fontsize=7.8, color=INK)
    note(fig, 'The manuscript\'s fall is 92 percent bag change; every page copier\'s is mostly clustering; the section chain falls like the manuscript with no clustering at all; '
              'natural language and the whole-manuscript and Currier chains do not fall.', y=-0.06, width=140)
    save(fig, 'fall_split')


# ---------------------------------------------------------------- the spatial statistic, one chart each
def rows_axes(rows, figsize):
    fig, ax = plt.subplots(figsize=figsize)
    yc = np.arange(len(rows))[::-1]
    for yy, (key, lab, col) in zip(yc, rows):
        if key is None and yy != yc[0]:
            ax.axhline(yy + 0.5, color=GRID, linewidth=0.8)
    ax.axvline(0, color=MUTED, linewidth=1)
    ax.set_yticks(yc)
    ax.set_yticklabels([r[1] for r in rows], fontsize=7.6)
    style_headers(ax)
    ax.set_ylim(-0.6, len(rows) - 0.4)
    ax.grid(axis='x', color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    return fig, ax, yc


def contrast_all(M, measures=MEASURES, suffix=''):
    fig, ax, yc = rows_axes(ROWS, (7.2, 5.2))
    off = offsets(measures)
    for yy, (key, lab, col) in zip(yc, ROWS):
        r = M.get(key) if key else None
        if r is None:
            continue
        vals = [r[m]['all'] for m, _ in measures]
        ax.plot([min(vals), max(vals)], [yy, yy], color=col, linewidth=1.0, alpha=0.5)
        for (m, _), v in zip(measures, vals):
            ax.plot([v], [yy + off[m]], marker=MARK[m], markersize=5, color=col, linestyle='none')
    ax.set_xlim(-0.1, 0.16)
    ax.set_xticks([-0.1, -0.05, 0, 0.05, 0.1, 0.15])
    ax.set_xlabel(XLABEL_CONTRAST, linespacing=1.5)
    ax.legend(handles=[Line2D([], [], marker=MARK[m], color=SEC, linestyle='none', markersize=5.2, label=lab) for m, lab in measures], frameon=False, fontsize=7.3, loc='lower right')
    ax.set_title('Are words with a less diverse pool in view more often repeats?' + ('' if len(measures) == 3 else ' (component diversity and glyph H2)'), loc='left', fontsize=7.8, color=INK, pad=34)
    ax.text(0, 1.012, SUBTITLE_ALL, transform=ax.transAxes, va='bottom', ha='left', fontsize=6.4, color=SEC, linespacing=1.4)
    save(fig, 'contrast_all' + suffix)


def contrast_by_length(M):
    fig, ax, yc = rows_axes(ROWS, (7.2, 5.5))
    for yy, (key, lab, col) in zip(yc, ROWS):
        r = M.get(key) if key else None
        if r is None:
            continue
        for m, _ in MEASURES:
            a, b = r[m]['short'], r[m]['long']
            y = yy + OFF[m]
            ax.plot([a, b], [y, y], color=col, linewidth=1.0, alpha=0.6)
            ax.plot([a], [y], marker=MARK[m], markersize=4.8, color=col, markerfacecolor=SURF, markeredgewidth=1.4, linestyle='none')
            ax.plot([b], [y], marker=MARK[m], markersize=4.8, color=col, linestyle='none')
    ax.set_xlim(-0.12, 0.18)
    ax.set_xticks([-0.1, -0.05, 0, 0.05, 0.1, 0.15])
    ax.set_xlabel(XLABEL_CONTRAST, linespacing=1.5)
    measure_legend(ax, extra=[Line2D([], [], marker='o', color=SEC, markerfacecolor=SURF, linestyle='none', markersize=5.2, label='open: targets of 3 letters or fewer'),
                              Line2D([], [], marker='o', color=SEC, linestyle='none', markersize=5.2, label='filled: targets of 6 letters or more')], loc='lower right')
    ax.set_title('The same, inside word-length classes: short (open) against long (filled) targets', loc='left', fontsize=7.8, color=INK, pad=25)
    ax.text(0, 1.012, SUBTITLE_LEN, transform=ax.transAxes, va='bottom', ha='left', fontsize=6.4, color=SEC, linespacing=1.4)
    note(fig, 'A dumbbell per measure: open end = targets of three letters or fewer, filled end = six or more (shape = score; colour = class of text). The manuscript\'s association survives in both '
              'classes on every measure, as do the self-citation generators\'. The German text\'s vanishes or reverses inside the classes: its all-target value came from between them (nearly half '
              'its tokens are words of three letters or fewer, and those are the repeats). The Markov chains have no association in any class.', y=-0.1, width=150)
    save(fig, 'contrast_by_length')


SECTION_PANELS = ('Herbal A', 'Herbal B', 'Pharma', 'Stars', 'Bio', 'Text-only pages')
GROUP_PANELS = ('1a', '1b', '1.5a', '2a', '3b', '3a', '3c', '4c', '4a')
MEASURES_CH = (('components', 'component diversity'), ('h2', 'glyph H2'))


def offsets(measures):
    return {m: o for (m, _), o in zip(measures, ([0.27, 0.0, -0.27] if len(measures) == 3 else [0.18, -0.18]))}


def contrast_panels(M, field, panels, grid, figsize, measures, name, title, subtitle, panel_title):
    """One panel per section or Golf group: the pool-size-stratified contrast for every text, the chosen pool scores as marker shapes."""
    fig, axes = plt.subplots(*grid, figsize=figsize, sharey=True)
    yc = np.arange(len(ROWS))[::-1]
    off = offsets(measures)
    allv = [v[m] for r in M.values() if field in r for v in r[field].values() for m, _ in measures if np.isfinite(v[m])]
    lo, hi = min(min(allv), -0.05) - 0.02, max(max(allv), 0.15) + 0.02
    ncol = grid[1]
    for k, (pn, ax) in enumerate(zip(panels, axes.flat)):
        for yy, (key, lab, col) in zip(yc, ROWS):
            if key is None and yy != yc[0]:
                ax.axhline(yy + 0.5, color=GRID, linewidth=0.8)
            r = M.get(key) if key else None
            if r is None or field not in r:
                continue
            v = r[field][pn]
            vals = [v[m] for m, _ in measures]
            ax.plot([min(vals), max(vals)], [yy, yy], color=col, linewidth=1.0, alpha=0.5)
            for (m, _), x in zip(measures, vals):
                ax.plot([x], [yy + off[m]], marker=MARK[m], markersize=4.4, color=col, linestyle='none')
        ax.axvline(0, color=MUTED, linewidth=1)
        ax.set_xlim(lo, hi)
        ax.set_yticks(yc)
        ax.set_yticklabels([r[1] for r in ROWS], fontsize=7)
        if k % ncol == 0:
            style_headers(ax)
        ax.set_title(panel_title(pn, M['manuscript'][field][pn]['n']), loc='left', fontsize=7.4, color=INK)
        ax.tick_params(axis='x', labelsize=6.5)
        if k >= len(panels) - ncol:
            ax.set_xlabel('repeat rate after the least diverse pool\nminus after the most diverse pool', fontsize=6.8)
    for ax in list(axes.flat)[len(panels):]:
        ax.axis('off')
    fig.legend(handles=[Line2D([], [], marker=MARK[m], color=SEC, linestyle='none', markersize=5.2, label=lab) for m, lab in measures],
               frameon=False, fontsize=7.3, loc='lower center', ncol=3, bbox_to_anchor=(0.6, 0.0))
    fig.suptitle(title + ('' if len(measures) == 3 else ' (component diversity and glyph H2)'), x=0.01, ha='left', fontsize=8.2, color=INK, y=0.995)
    fig.text(0.01, 0.972, subtitle, fontsize=6.4, color=SEC, ha='left', va='top')
    fig.subplots_adjust(left=0.2, right=0.99, top=0.92, bottom=0.07, wspace=0.08, hspace=0.24)
    save(fig, name)


def contrast_by_section(M, measures=MEASURES, suffix=''):
    contrast_panels(M, 'sections', SECTION_PANELS, (2, 3), (11, 8.4), measures, 'contrast_by_section' + suffix,
                    'Are words with a less diverse pool in view more often repeats? Section by section',
                    'Marker = mean repeat score of the fifth of words with the LEAST diverse pool in view minus the fifth with the MOST diverse pool, inside the section\n'
                    '(averaged over pool-size tertiles and bifolia; shape = pool score, colour = class of text). Sections with 2,000 manuscript words or more; Herbal split by Currier language.',
                    lambda pn, n: f'{pn} ({n:,} manuscript words scored)')


def contrast_by_group(M, measures=MEASURES, suffix=''):
    contrast_panels(M, 'groups', GROUP_PANELS, (3, 3), (11, 11.4), measures, 'contrast_by_group' + suffix,
                    'Are words with a less diverse pool in view more often repeats? Golf 2.1 group by group',
                    'Marker = mean repeat score of the fifth of words with the LEAST diverse pool in view minus the fifth with the MOST diverse pool, inside the group\n'
                    '(averaged over pool-size tertiles and bifolia; shape = pool score, colour = class of text). Groups in Path 1 order; n = manuscript words scored.',
                    lambda pn, n: f'Group {pn}, {D.GROUP_SECTION[pn]} ({n:,} manuscript words scored)')

def coupling(Cp):
    rows = [r for r in ROWS if (r[0] is None or r[0] in Cp) and r[0] not in ('manuscript_shuffled_paragraphs', 'manuscript_shuffled_pages')]   # shuffles couple as the manuscript does; table only (user)
    rows = [r for i, r in enumerate(rows) if not (r[0] is None and (i + 1 >= len(rows) or rows[i + 1][0] is None))]
    fig, ax, yc = rows_axes(rows, (7.2, 3.9))
    for yy, (key, lab, col) in zip(yc, rows):
        if key is None:
            continue
        for m, _ in MEASURES:
            a, b = Cp[key]['token'][m], Cp[key]['page_means'][m]
            y = yy + OFF[m]
            ax.plot([a, b], [y, y], color=col, linewidth=1.0, alpha=0.6)
            ax.plot([a], [y], marker=MARK[m], markersize=4.8, color=col, linestyle='none')
            ax.plot([b], [y], marker=MARK[m], markersize=4.8, color=col, markerfacecolor=SURF, markeredgewidth=1.4, linestyle='none')
    ax.set_xlim(-0.25, 0.85)
    ax.set_xlabel('Spearman correlation of the MATTR colour with the pool score')
    measure_legend(ax, extra=[Line2D([], [], marker='o', color=SEC, linestyle='none', markersize=5.2, label='filled: token level'),
                              Line2D([], [], marker='o', color=SEC, markerfacecolor=SURF, linestyle='none', markersize=5.2, label='open: between page means')], loc='lower right')
    ax.set_title('Does MATTR track the diversity of the words in view?', loc='left', fontsize=7.8, color=INK)
    note(fig, 'Shape = score, colour = class of text. In the manuscript all three pool scores track MATTR, mostly between pages (H2 +0.72). The whole-manuscript and Currier chains barely couple; '
              'the section chain, which copies nothing and sees no page, couples like the manuscript; the German text does not under any layout. The coupling comes with section-level '
              'composition and the Voynichese unit system, not with a page in view.', y=-0.12, width=150)
    save(fig, 'coupling')


def main():
    R = json.loads((D.HERE / 'layout_controls.json').read_text(encoding='utf-8'))
    M = json.loads((D.HERE / 'mechanism_check.json').read_text(encoding='utf-8'))
    Cp = json.loads((D.HERE / 'mattr_vs_components.json').read_text(encoding='utf-8'))
    ms = D.manuscript()
    method_mattr()
    # method_spatial() withdrawn 27 October: method_spatial.png is now a capture of the app itself (see RESULTS, section 8)
    route_mattr(R)
    route_mattr(R, SERIES_SPATIAL, 'route_mattr_spatial')
    route_bifolia(R, ms)
    fall_split(R)
    contrast_all(M)
    contrast_by_length(M)
    contrast_all(M, MEASURES_CH, '_components_h2')
    if 'sections' in M['manuscript']:
        contrast_by_section(M)
    if 'groups' in M['manuscript']:
        contrast_by_group(M)
        contrast_by_group(M, MEASURES_CH, '_components_h2')
    coupling(Cp)
    print('wrote the small figures')


if __name__ == '__main__':
    main()
