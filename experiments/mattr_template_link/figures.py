"""Figures for the template-availability study. Validated light palette (dataviz reference instance):
ink #0b0b0b manuscript, blue #2a78d6 Timm, aqua #1baf7a far 0, orange #eb6834 buffer, violet #6250d6 pool,
grey #8a8984 references / hooks-only. Thin marks, direct labels, legends for multi-series panels."""
import json
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
import data as D

INK = '#0b0b0b'; SEC = '#52514e'; MUTED = '#8a8984'; GRID = '#e6e5e1'; SURF = '#fcfcfb'
COL = dict(manuscript=INK, timm='#2a78d6', far0='#1baf7a', noinnov_far0='#7fb9a0', buffer='#eb6834', pool='#6250d6', timm_spatial='#0f4c9a', noinnov_spatial='#3f8f78', far0_spatial='#0d7a52')
LABEL = dict(manuscript='Manuscript', timm='Original Timm\n(layout only)', far0='Governed,\npage window only', noinnov_far0='Hooks on page window,\nno innovator',
             buffer='Governed, 100-form\nrunning memory', pool='Governed, 2,000-\ntoken pool', timm_spatial='Original Timm,\nsources in view', noinnov_spatial='Hooks on words in view,\nno innovator', far0_spatial='Governed + innovator,\nwords in view')
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.edgecolor': GRID, 'axes.labelcolor': SEC, 'xtick.color': SEC,
                     'ytick.color': SEC, 'text.color': INK, 'axes.spines.top': False, 'axes.spines.right': False, 'figure.facecolor': SURF,
                     'axes.facecolor': SURF, 'savefig.facecolor': SURF})


def fig_scales(scales, groups, ms):
    keys = ['manuscript', 'timm', 'far0', 'noinnov_far0', 'buffer', 'pool']
    refs = [k for k in scales if k.startswith('ref_')]
    w = {g: scales['manuscript'][g]['tokens'] for g in groups}
    def comps(res):
        ww = np.array([w[g] for g in groups], float)
        return [float(np.average([res[g][c] for g in groups], weights=ww)) for c in ('bifolium_level', 'page_level', 'within_page')]
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.2), gridspec_kw=dict(width_ratios=[1.1, 1]))
    ax = axes[0]
    rows = [(LABEL[k].replace('\n', ' '), comps(scales[k]), COL[k]) for k in keys]
    rows.append(('Latin medical prose, 5 texts (mean)', list(np.mean([comps(scales[k]) for k in refs if k.startswith('ref_la')], axis=0)), MUTED))
    rows.append(('German / Italian prose, 3 texts (mean)', list(np.mean([comps(scales[k]) for k in refs if not k.startswith('ref_la')], axis=0)), MUTED))
    y = np.arange(len(rows))[::-1]
    hatches = [None, '////', '....']; alphas = [1.0, 0.65, 0.35]
    names = ['bifolium level', 'page level', 'inside the page']
    for i, (name, c, col) in enumerate(rows):
        left = 0
        for j, v in enumerate(c):
            ax.barh(y[i], v, left=left, color=col, alpha=alphas[j], edgecolor=SURF, linewidth=1.5, height=0.62, hatch=hatches[j])
            left += v
        ax.text(left + 0.002, y[i], f'{left:.3f}', va='center', ha='left', fontsize=9, color=SEC)
    ax.set_yticks(y); ax.set_yticklabels([r[0] for r in rows], fontsize=9)
    ax.set_xlabel('Loss of local diversity against the group\'s shuffled bag (MATTR100 units)')
    ax.set_xlim(0, 0.14); ax.grid(axis='x', color=GRID, linewidth=0.8); ax.set_axisbelow(True)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(facecolor=SEC, alpha=alphas[j], hatch=hatches[j], edgecolor=SURF, label=names[j]) for j in range(3)],
              loc='lower right', frameon=False, fontsize=9, title='Where the loss sits', title_fontsize=9)
    ax.set_title('Where each text loses local diversity (route mean)', loc='left', fontsize=11, color=INK)
    # right: along the groups, manuscript and Timm: group bag G and actual page MATTR A
    ax = axes[1]
    x = np.arange(len(groups))
    for k, lab in (('manuscript', 'Manuscript'), ('timm', 'Original Timm (layout only)')):
        G = [scales[k][g]['G'] for g in groups]; A = [scales[k][g]['A'] for g in groups]
        ax.plot(x, G, color=COL[k], linewidth=1.6, linestyle=(0, (3, 2)), marker='o', markersize=4.5, markerfacecolor=SURF, markeredgewidth=1.4, label=f'{lab}: shuffled group bag')
        ax.plot(x, A, color=COL[k], linewidth=2, marker='o', markersize=5.5, label=f'{lab}: actual page MATTR100')
        ax.fill_between(x, A, G, color=COL[k], alpha=0.12, linewidth=0)
    ax.set_xticks(x); ax.set_xticklabels(D.group_labels(groups), fontsize=7.5); ax.set_xlabel('Golf group along Path 1 (section at the start of each stretch)')
    ax.set_ylabel('MATTR100'); ax.set_ylim(0.6, 0.92); ax.grid(axis='y', color=GRID, linewidth=0.8); ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=8.5, loc='lower left')
    ax.set_title('The manuscript\'s MATTR follows its vocabulary; Timm\'s follows his page', loc='left', fontsize=11, color=INK)
    ax.annotate('shaded = local\nconcentration', xy=(x[-1], (scales['timm']['4a']['A'] + scales['timm']['4a']['G']) / 2), xytext=(x[-1] - 2.6, 0.655),
                fontsize=8.5, color=SEC, arrowprops=dict(arrowstyle='-', color=MUTED, lw=0.8))
    fig.tight_layout()
    fig.savefig(D.HERE / 'scales.png', dpi=160); fig.savefig(D.HERE / 'scales.svg'); plt.close(fig)


def fig_visibility(vis):
    keys = ['manuscript', 'timm', 'far0', 'noinnov_far0', 'buffer', 'pool']
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.8), gridspec_kw=dict(width_ratios=[1.25, 1]))
    ax = axes[0]
    y = np.arange(len(keys))[::-1]
    classes = [('same-face', 'previous page on the same face (visible)', 'o'), ('flip', 'previous page on the other face (hidden)', 's'),
               ('cross-sheet', 'previous page on another sheet', '^')]
    for k, yy in zip(keys, y):
        r = vis[k]
        wi = r['within_1_50']['by_class']['flip']['mean']
        ax.plot([wi * 1000], [yy], marker='|', markersize=16, color=COL[k], markeredgewidth=2.2, linestyle='none')
        for cls, lab, mk in classes:
            v = r['cross_1_50']['by_class'][cls]
            ax.errorbar(v['mean'] * 1000, yy + (0.18 if cls == 'same-face' else -0.18 if cls == 'flip' else 0), xerr=1.96 * v['se'] * 1000,
                        fmt=mk, color=COL[k], markersize=7, markerfacecolor=SURF if cls != 'same-face' else COL[k], markeredgewidth=1.5, capsize=0, elinewidth=1.2)
    ax.set_yticks(y); ax.set_yticklabels([LABEL[k].replace('\n', ' ') for k in keys], fontsize=9)
    ax.set_xlabel('Repeats per 1,000 word pairs, lags 1 to 50 (mean, 95% CI)')
    ax.grid(axis='x', color=GRID, linewidth=0.8); ax.set_axisbelow(True); ax.set_xlim(0, 26)
    from matplotlib.lines import Line2D
    handles = [Line2D([], [], marker='o', color=SEC, linestyle='none', markersize=7, label=classes[0][1]),
               Line2D([], [], marker='s', color=SEC, markerfacecolor=SURF, linestyle='none', markersize=7, label=classes[1][1]),
               Line2D([], [], marker='^', color=SEC, markerfacecolor=SURF, linestyle='none', markersize=7, label=classes[2][1]),
               Line2D([], [], marker='|', color=SEC, linestyle='none', markersize=14, markeredgewidth=2, label='pairs inside the page, same lags')]
    ax.legend(handles=handles, frameon=False, fontsize=8.5, loc='lower right')
    ax.set_title('Re-use of the previous page\'s words at the start of a page', loc='left', fontsize=11, color=INK)
    ax = axes[1]
    for k, yy in zip(keys, y):
        t = vis[k]['cross_1_50']['paired_same_face_vs_flip']
        ax.errorbar(t['mean_diff'] * 1000, yy, xerr=[[(t['mean_diff'] - t['ci95'][0]) * 1000], [(t['ci95'][1] - t['mean_diff']) * 1000]], fmt='o', color=COL[k],
                    markersize=8, capsize=3, elinewidth=1.6)
        ax.text(3.6, yy, f"p = {t['perm_p_two_sided']:.2f}  ({t['positive_bifolia']}+ / {t['negative_bifolia']}- bifolia)", va='center', fontsize=8.5, color=SEC)
    ax.axvline(0, color=MUTED, linewidth=1)
    ax.set_yticks(y); ax.set_yticklabels([''] * len(keys))
    ax.set_xlim(-3.5, 9); ax.set_xlabel('Same face minus flip, per 1,000 pairs (95% CI over bifolia)')
    ax.grid(axis='x', color=GRID, linewidth=0.8); ax.set_axisbelow(True)
    ax.set_title('Does seeing the previous page add re-use? No', loc='left', fontsize=11, color=INK)
    fig.tight_layout()
    fig.savefig(D.HERE / 'visibility.png', dpi=160); fig.savefig(D.HERE / 'visibility.svg'); plt.close(fig)


def fig_route(dec, ms):
    nodes = ms['nodes']; ids = [n['id'] for n in nodes]; groups = [n['group'] for n in nodes]
    x = np.arange(len(ids))
    fig, axes = plt.subplots(2, 1, figsize=(13, 7.2), sharex=True, gridspec_kw=dict(height_ratios=[1.2, 1]))
    # group bands
    bounds = []; start = 0
    for i in range(1, len(groups) + 1):
        if i == len(groups) or groups[i] != groups[start]:
            bounds.append((start, i - 1, groups[start])); start = i
    for ax in axes:
        for j, (a, b, g) in enumerate(bounds):
            if j % 2 == 0:
                ax.axvspan(a - 0.5, b + 0.5, color='#f1f0ec', zorder=0, linewidth=0)
    ax = axes[0]
    m = dec['streams']['manuscript']['nodes']
    A = [m[i]['mattr100'] for i in ids]; B = [m[i]['bag100'] for i in ids]
    ax.fill_between(x, A, B, color=INK, alpha=0.15, linewidth=0, label='clustering gap (bag minus actual)')
    ax.plot(x, B, color=INK, linewidth=1.5, linestyle=(0, (3, 2)), label='expected after shuffling the bifolium\'s words')
    ax.plot(x, A, color=INK, linewidth=2, marker='o', markersize=4, label='actual MATTR100')
    t = dec['streams']['timm']['nodes']
    ax.plot(x, [t[i]['mattr100'] for i in ids], color=COL['timm'], linewidth=1.6, marker='o', markersize=3.5, label='Original Timm, actual (5 seeds)')
    ax.plot(x, [t[i]['bag100'] for i in ids], color=COL['timm'], linewidth=1.3, linestyle=(0, (3, 2)), label='Original Timm, shuffled')
    for a, b, g in bounds:
        ax.text((a + b) / 2, 0.905, g, ha='center', va='bottom', fontsize=8.5, color=SEC)
    ax.set_ylim(0.55, 0.93); ax.set_ylabel('MATTR100 within the bifolium'); ax.grid(axis='y', color=GRID, linewidth=0.8); ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=8.5, ncol=3, loc='lower left')
    ax.set_title('Manuscript: every fall of MATTR is a fall of the shuffled-bag expectation; Timm: the gap carries his', loc='left', fontsize=11, color=INK)
    ax = axes[1]
    for k in ('timm', 'far0', 'buffer', 'pool'):
        s = dec['streams'][k]['nodes']
        ax.plot(x, [s[i]['gap'] for i in ids], color=COL[k], linewidth=1.6, marker='o', markersize=3.5, label=LABEL[k].replace('\n', ' '))
    ax.plot(x, [m[i]['gap'] for i in ids], color=INK, linewidth=2.2, marker='o', markersize=4, label='Manuscript')
    refs = dec['references']
    lo = min(r['gap_mean'] for r in refs.values()); hi = max(r['gap_mean'] for r in refs.values())
    ax.axhspan(lo, hi, color=MUTED, alpha=0.18, linewidth=0, label='natural-language reference means (range of 8 texts)')
    ax.set_ylim(-0.03, 0.17); ax.set_ylabel('Clustering gap'); ax.grid(axis='y', color=GRID, linewidth=0.8); ax.set_axisbelow(True)
    ax.set_xticks(x); ax.set_xticklabels(ids, rotation=90, fontsize=7.5); ax.set_xlabel('Bifolium along Path 1')
    ax.legend(frameon=False, fontsize=8.5, ncol=3, loc='upper left')
    ax.set_title('Local clustering beyond the bifolium\'s own word bag', loc='left', fontsize=11, color=INK)
    fig.tight_layout()
    fig.savefig(D.HERE / 'route.png', dpi=160); fig.savefig(D.HERE / 'route.svg'); plt.close(fig)


def main():
    ms = D.manuscript()
    scales = json.load(open(D.HERE / 'scales.json', encoding='utf-8'))
    groups = list(dict.fromkeys(n['group'] for n in ms['nodes']))
    fig_scales(scales, groups, ms)
    fig_visibility(json.load(open(D.HERE / 'visibility.json', encoding='utf-8')))
    fig_route(json.load(open(D.HERE / 'decompose.json', encoding='utf-8')), ms)
    print('figures written')


if __name__ == '__main__':
    main()
