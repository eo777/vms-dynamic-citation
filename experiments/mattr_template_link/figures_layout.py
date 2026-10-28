"""Figure for sections 7 and 8: natural-language and bigram texts in the manuscript's layout, the bag/clustering split
of the fall into Bio, and the spatial statistic at fixed pool size. Palette: the study's validated light palette
(figures.py) with green #008300 for the bigram chains (validated adjacent set blue, aqua, orange, violet, green) and
neutral grey #8a8984 for natural prose; identity is also carried by line style, marker fill and direct labels."""
import json
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import numpy as np

sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
import data as D
from figures import INK, SEC, MUTED, GRID, SURF, COL

BIGRAM = '#008300'
SHOW = ['1a', '1b', '1.5a', '2a', '3b', '3a', '3c', '4c', '4a']


def mean(per, path):
    vals = []
    for r in per:
        v = r
        for k in path:
            v = v[k]
        vals.append(v)
    return float(np.mean(vals))


def main():
    R = json.loads((D.HERE / 'layout_controls.json').read_text(encoding='utf-8'))
    S = json.loads((D.HERE / 'component_strata.json').read_text(encoding='utf-8'))
    N = json.loads((D.HERE / 'native_layout.json').read_text(encoding='utf-8'))
    prose_box = [k for k in R if k.startswith('prose_box_')]
    prose_line = [k for k in R if k.startswith('prose_line_')]

    fig = plt.figure(figsize=(12, 15.5))
    gs = fig.add_gridspec(3, 1, height_ratios=[1.25, 1.0, 1.2], hspace=0.5)
    ax = fig.add_subplot(gs[0])
    axb = fig.add_subplot(gs[1])
    axc = fig.add_subplot(gs[2])

    # ---- A: MATTR100 along the route
    x = np.arange(len(SHOW))
    ax.axvspan(SHOW.index('3c') - 0.5, SHOW.index('4a') + 0.5, color=GRID, alpha=0.55, linewidth=0, zorder=0)
    ax.text(SHOW.index('3c') - 0.42, 0.915, 'Stars → Bio layout', fontsize=9, color=SEC, va='top')
    lo = [min(mean(R[k], ['route', 'groups', g, 'mattr100']) for k in prose_box + prose_line) for g in SHOW]
    hi = [max(mean(R[k], ['route', 'groups', g, 'mattr100']) for k in prose_box + prose_line) for g in SHOW]
    ax.fill_between(x, lo, hi, color=MUTED, alpha=0.16, linewidth=0, label='natural prose, 5 texts × 2 reflows (range of the ten)')
    series = [('manuscript', 'Manuscript', INK, '-', 2.4, True),
              ('timm', 'Original Timm (layout only)', COL['timm'], '-', 2.0, True),
              ('far0', 'Far 0 (page window)', COL['far0'], '-', 2.0, True),
              ('bigram_whole', 'Bigram chain, whole manuscript', BIGRAM, (0, (3, 2)), 1.8, False),
              ('bigram_currier', 'Bigram chains, Currier A and B separately', BIGRAM, (0, (5, 2, 1, 2)), 1.8, True),
              ('bigram_section', 'Bigram chains, each section separately', BIGRAM, '-', 1.8, True)]
    bag = [mean(R['manuscript'], ['route', 'groups', g, 'bag100']) for g in SHOW]
    ax.plot(x, bag, color=INK, linestyle=(0, (2, 2)), linewidth=1.4, label="Manuscript, shuffled-bag expectation (bag100)", zorder=2)
    ends = [(bag[-1], 'Manuscript, shuffled-bag expectation', INK)]
    for key, lab, col, ls, lw, filled in series:
        y = [mean(R[key], ['route', 'groups', g, 'mattr100']) for g in SHOW]
        ax.plot(x, y, color=col, linestyle=ls, linewidth=lw, marker='o', markersize=4.5, markerfacecolor=col if filled else SURF,
                markeredgewidth=1.4, label=lab, zorder=3)
        ends.append((y[-1], lab, col))
    ends.append(((lo[-1] + hi[-1]) / 2, 'natural prose (range of ten reflows)', SEC))
    ends.sort()
    ys = [e[0] for e in ends]
    for i in range(1, len(ys)):
        if ys[i] - ys[i - 1] < 0.024:
            ys[i] = ys[i - 1] + 0.024
    for (y0, lab, col), yy in zip(ends, ys):
        ax.annotate(lab, xy=(x[-1] + 0.06, y0), xytext=(x[-1] + 0.3, yy), fontsize=8.5, color=col, va='center',
                    arrowprops=dict(arrowstyle='-', color=GRID, lw=0.8))
    ax.set_xticks(x)
    ax.set_xticklabels(D.group_labels(SHOW), fontsize=9)
    ax.set_xlim(-0.5, len(SHOW) + 2.9)
    ax.set_ylim(0.6, 0.93)
    ax.set_xlabel('Golf 2.1 group along Path 1 (route order); the section is named at the start of each stretch')
    ax.set_ylabel("MATTR100 of the group's text")
    ax.grid(axis='y', color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=8.5, loc='upper center', bbox_to_anchor=(0.5, -0.19), ncol=3)
    ax.set_title("A. Texts laid into the manuscript's lines: the manuscript falls with its own shuffled word bag, not where the page copiers fall",
                 loc='left', fontsize=11, color=INK)

    # ---- B: the fall 3c -> 4a split into bag and clustering parts
    rows = [('manuscript', 'Manuscript', INK), ('timm', 'Original Timm', COL['timm']), ('far0', 'Far 0', COL['far0']),
            ('noinnov_far0', 'No-innovator far 0', COL['noinnov_far0']), ('timm_spatial', 'Original Timm, sources in view', COL['timm_spatial']),
            ('noinnov_spatial', 'No-innovator far 0, sources in view', COL['noinnov_spatial']), ('far0_spatial', 'Far 0 with innovator, sources in view', COL['far0_spatial']),
            ('buffer', '100-form memory', COL['buffer']), ('pool', '2,000-token pool', COL['pool']),
            ('prose', 'Natural prose (10 reflows)', MUTED), ('bigram_whole', 'Bigram chain, whole manuscript', BIGRAM),
            ('bigram_currier', 'Bigram chains, Currier A / B', BIGRAM), ('bigram_section', 'Bigram chains, by section', BIGRAM)]
    yb = np.arange(len(rows))[::-1]
    for yy, (key, lab, col) in zip(yb, rows):
        if key == 'prose':
            vals = [mean(R[k], ['route', 'steps', '3c->4a', 'actual']) for k in prose_box + prose_line]
            axb.plot(vals, [yy] * len(vals), linestyle='none', marker='o', markersize=5, color=MUTED, markerfacecolor=SURF, markeredgewidth=1.3)
            axb.text(max(vals) + 0.006, yy, f'{min(vals):+.3f} to {max(vals):+.3f}: no fall', va='center', fontsize=8.5, color=SEC)
            continue
        bag = mean(R[key], ['route', 'steps', '3c->4a', 'bag'])
        clu = mean(R[key], ['route', 'steps', '3c->4a', 'clustering'])
        axb.barh(yy, bag, left=0, color=col, height=0.6, edgecolor=SURF, linewidth=1.2)
        if (clu < 0) == (bag < 0):
            axb.barh(yy, clu, left=bag, color=col, height=0.6, edgecolor=SURF, linewidth=1.2, hatch='////', alpha=0.55)
            leftmost = min(0, bag + clu)
        else:
            axb.barh(yy, clu, left=0, color=col, height=0.6, edgecolor=SURF, linewidth=1.2, hatch='////', alpha=0.55)
            leftmost = min(0, bag, clu)
        total = bag + clu
        axb.text(leftmost - 0.004, yy, f'{total:+.3f}', va='center', ha='right', fontsize=8.5, color=SEC)
    axb.axvline(0, color=MUTED, linewidth=1)
    axb.set_yticks(yb)
    axb.set_yticklabels([r[1] for r in rows], fontsize=9)
    axb.set_xlim(-0.19, 0.12)
    axb.set_xticks([-0.15, -0.10, -0.05, 0, 0.05, 0.10])
    axb.set_xlabel('change in MATTR100 from Stars (3c) to Bio (4a)')
    axb.grid(axis='x', color=GRID, linewidth=0.8)
    axb.set_axisbelow(True)
    axb.legend(handles=[Patch(facecolor=SEC, edgecolor=SURF, label='bag change (which words are used)'),
                        Patch(facecolor=SEC, alpha=0.55, hatch='////', edgecolor=SURF, label='clustering change (repeats beyond the bag)')],
               frameon=False, fontsize=8.5, loc='upper center', bbox_to_anchor=(0.5, -0.16), ncol=2)
    axb.set_title('B. The fall into Bio: composition in the manuscript, clustering in every page copier', loc='left', fontsize=11, color=INK)

    # ---- C: the spatial statistic at fixed pool size
    gn = N['gart_native_lines']
    gb = N['gart_one_word_per_box']
    crow = [(S['manuscript, recorded boxes'], 'Manuscript', INK, True),
            (S['manuscript shuffled within paragraphs'], 'Manuscript, words shuffled inside paragraphs', INK, False),
            (S['manuscript shuffled within pages'], 'Manuscript, words shuffled inside pages', INK, False),
            (S['timm (synthetic boxes)'], 'Original Timm', COL['timm'], True), (S['timm_spatial (synthetic boxes)'], 'Original Timm, sources in view', COL['timm_spatial'], True),
            (S['noinnov_spatial (synthetic boxes)'], 'No-innovator far 0, sources in view', COL['noinnov_spatial'], True),
            (S['far0_spatial (synthetic boxes)'], 'Far 0 with innovator, sources in view', COL['far0_spatial'], True), (S['far0 (synthetic boxes)'], 'Far 0', COL['far0'], True),
            (S['buffer (synthetic boxes)'], '100-form memory', COL['buffer'], True), (S['pool (synthetic boxes)'], '2,000-token pool', COL['pool'], True),
            (S['bigram whole (recorded boxes)'], 'Bigram chain, whole manuscript', BIGRAM, False),
            (S['bigram by Currier language (recorded boxes)'], 'Bigram chains, Currier A / B', BIGRAM, False),
            (S['bigram by section (recorded boxes)'], 'Bigram chains, by section', BIGRAM, False),
            (dict(worddiv_by_pool_size=gn[0]['spatial']['all']['worddiv_by_pool_size'], worddiv_by_pool_size_mean=mean(gn, ['spatial', 'all', 'worddiv_by_pool_size_mean'])),
             'Natural prose (Gart 1487), its own printed lines', MUTED, True),
            (dict(worddiv_by_pool_size=gb[0]['spatial']['all']['worddiv_by_pool_size'], worddiv_by_pool_size_mean=gb[0]['spatial']['all']['worddiv_by_pool_size_mean']),
             'Natural prose (Gart 1487), one word per manuscript box', MUTED, False),
            (S['Galen, box reflow, recorded boxes'], 'Natural prose (Galen), one word per manuscript box', MUTED, False),
            (S['Galen, box reflow, synthetic boxes'], 'Natural prose (Galen), same boxes sized to its own words', MUTED, True)]
    yc = np.arange(len(crow))[::-1]
    for yy, (r, lab, col, filled) in zip(yc, crow):
        parts = r['worddiv_by_pool_size']
        m = r['worddiv_by_pool_size_mean']
        axc.plot(parts, [yy] * 3, linestyle='none', marker='|', markersize=9, color=col, markeredgewidth=1.2, alpha=0.6)
        axc.plot([m], [yy], linestyle='none', marker='o', markersize=8, color=col, markerfacecolor=col if filled else SURF, markeredgewidth=1.6)
        axc.text(0.265, yy, f'{m:+.3f}', va='center', ha='right', fontsize=8.5, color=SEC)
    axc.axvline(0, color=MUTED, linewidth=1)
    axc.set_yticks(yc)
    axc.set_yticklabels([r[1] for r in crow], fontsize=8.5)
    axc.set_xlim(-0.08, 0.27)
    axc.set_xticks([-0.05, 0, 0.05, 0.10, 0.15, 0.20])
    axc.set_xlabel('word impact: lowest minus highest word-diversity quintile of the words in view (mean inside pool-size tertiles; ticks = the three tertiles)')
    axc.grid(axis='x', color=GRID, linewidth=0.8)
    axc.set_axisbelow(True)
    axc.legend(handles=[Line2D([], [], marker='o', color=SEC, linestyle='none', markersize=7, label='text in its own order and geometry'),
                        Line2D([], [], marker='o', color=SEC, markerfacecolor=SURF, linestyle='none', markersize=7, label='shuffled, stationary, or geometry not its own')],
               frameon=False, fontsize=8.5, loc='upper center', bbox_to_anchor=(0.5, -0.2), ncol=2)
    axc.set_title("C. The spatial statistic at fixed pool size: an order effect inside paragraphs; the printed herbal's value is a word-length artefact (section 8)", loc='left', fontsize=11, color=INK)

    fig.savefig(D.HERE / 'layout_controls.png', dpi=160, bbox_inches='tight')
    fig.savefig(D.HERE / 'layout_controls.svg', bbox_inches='tight')
    plt.close(fig)
    print('wrote layout_controls.png / .svg')


if __name__ == '__main__':
    main()
