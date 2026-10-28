"""Each historical text's own MATTR route (27 October 2026, user's question: the natural-language band of route_mattr.png
hides whether the texts rise into Stars and fall into Bio as the manuscript does, or fluctuate on their own).

For the five comparison texts in both reflows (one word per manuscript box; each line filled to its character budget) the
MATTR100 of every Golf 2.1 group is drawn as its own line (route_mattr_prose.png), and per series the steps 3b->3a,
3a->3c (into Stars), 3c->4c, 4c->4a and 3c->4a (into Bio) are tabulated against the manuscript's, with the Spearman
correlation of the series with the manuscript's profile, the agreement between the two reflows of one text, and the
share of all prose steps as large as the manuscript's two. Data: layout_controls.json."""
import json
import sys
from itertools import combinations
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from figures import INK, SEC, GRID, SURF   # noqa: E402
import data as D  # noqa: E402

SHOW = ['1a', '1b', '1.5a', '2a', '3b', '3a', '3c', '4c', '4a']
STEPS = [('3b', '3a'), ('3a', '3c'), ('3c', '4c'), ('4c', '4a'), ('3c', '4a')]
TEXTS = [('la_galen_simplicium', 'Galen, De simplicium'), ('la_dioscorides_longob', 'Dioscorides (Longobard)'), ('la_rhazes_almansor', 'Rhazes, Almansor'),
         ('la_hildegard_physica', 'Hildegard, Physica'), ('de_gart_augsburg1487', 'Gart der Gesundheit 1487')]
COLORS = ['#1f5fb8', '#e0893a', '#6a3fb0', '#20a39e', '#9b2457']     # one hue per text, fixed order (validated, CVD dE 17)
REFLOWS = [('box', 'one word per manuscript box', '-'), ('line', 'each line filled to its character budget', (0, (4, 2)))]
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 7.5})


def spearman(a, b):
    ra, rb = np.argsort(np.argsort(a)), np.argsort(np.argsort(b))
    return float(np.corrcoef(ra, rb)[0, 1])


def series(R, key):
    return np.array([np.mean([r['route']['groups'][g]['mattr100'] for r in R[key]]) for g in SHOW])


def main():
    R = json.loads((HERE / 'layout_controls.json').read_text(encoding='utf-8'))
    ms = series(R, 'manuscript')
    prose = {(t, rf): series(R, f'prose_{rf}_{t}') for t, _ in TEXTS for rf, _, _ in REFLOWS}
    x = np.arange(len(SHOW))
    fig, ax = plt.subplots(figsize=(7.6, 4.6), facecolor=SURF)
    ax.axvspan(SHOW.index('3c') - 0.5, SHOW.index('4a') + 0.5, color=GRID, alpha=0.55, linewidth=0, zorder=0)
    ax.text(SHOW.index('3c') - 0.42, 0.925, 'Stars -> Bio layout', fontsize=7.6, color=SEC, va='top')
    ends = []
    for (t, label), col in zip(TEXTS, COLORS):
        for rf, _, ls in REFLOWS:
            y = prose[(t, rf)]
            ax.plot(x, y, color=col, linestyle=ls, linewidth=1.4, marker='o', markersize=2.6, zorder=3)
        ends.append((float(np.mean([prose[(t, rf)][-1] for rf, _, _ in REFLOWS])), label, col))
    ax.plot(x, ms, color=INK, linewidth=2.2, marker='o', markersize=3.4, zorder=4)
    ends.append((float(ms[-1]), 'Manuscript', INK))
    ends.sort()
    ys = [e[0] for e in ends]
    for i in range(1, len(ys)):
        if ys[i] - ys[i - 1] < 0.024:
            ys[i] = ys[i - 1] + 0.024
    for (y0, lab, col), yy in zip(ends, ys):
        ax.annotate(lab, xy=(x[-1] + 0.06, y0), xytext=(x[-1] + 0.32, yy), fontsize=7.2, color=INK, va='center', arrowprops=dict(arrowstyle='-', color=GRID, lw=0.8))
    ax.set_xticks(x)
    ax.set_xticklabels(D.group_labels(SHOW), fontsize=7.6)
    ax.set_xlim(-0.5, len(SHOW) + 2.9)
    ax.set_ylim(0.62, 0.94)
    ax.set_xlabel('Golf 2.1 group along Path 1 (route order); the section is named at the start of each stretch')
    ax.set_ylabel("MATTR100 of the group's text")
    ax.grid(axis='y', color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ax.spines.values():
        s.set_color(GRID)
    handles = [Line2D([], [], color=INK, linewidth=2.2, label='Manuscript')] + \
              [Line2D([], [], color=SEC, linestyle=ls, linewidth=1.4, label=f'historical text, {desc}') for _, desc, ls in REFLOWS]
    ax.legend(handles=handles, frameon=False, fontsize=7, loc='upper center', bbox_to_anchor=(0.5, -0.2), ncol=3)
    ax.set_title("MATTR100 by group: each historical text on its own, laid into the manuscript's lines", loc='left', fontsize=7.8, color=INK)
    fig.tight_layout()
    for ext in ('png', 'svg'):
        fig.savefig(HERE / f'route_mattr_prose.{ext}', dpi=150, facecolor=SURF)
    plt.close(fig)

    # the table
    def step(y, a, b):
        return float(y[SHOW.index(b)] - y[SHOW.index(a)])
    rows = []
    for t, label in TEXTS:
        for rf, desc, _ in REFLOWS:
            y = prose[(t, rf)]
            rows.append(dict(text=label, reflow=rf, steps={f'{a}->{b}': step(y, a, b) for a, b in STEPS}, spearman_ms=spearman(y, ms),
                             mean_abs_step=float(np.mean(np.abs(np.diff(y))))))
    ms_steps = {f'{a}->{b}': step(ms, a, b) for a, b in STEPS}
    print('| Text | Reflow | 3b->3a | 3a->3c (into Stars) | 3c->4c | 4c->4a | 3c->4a (into Bio) | mean |step| over the route | Spearman with the manuscript (9 groups) |')
    print('|---|---|---:|---:|---:|---:|---:|---:|---:|')
    print(f"| Manuscript | | " + ' | '.join(f"{ms_steps[k]:+.3f}" for k in ms_steps) + f" | {np.mean(np.abs(np.diff(ms))):.3f} | 1 |")
    for r in rows:
        print(f"| {r['text']} | {dict(REFLOWS and [(a, b) for a, b, _ in REFLOWS])[r['reflow']]} | " + ' | '.join(f"{r['steps'][k]:+.3f}" for k in ms_steps) +
              f" | {r['mean_abs_step']:.3f} | {r['spearman_ms']:+.2f} |")
    up = sum(1 for r in rows if r['steps']['3a->3c'] > 0)
    down = sum(1 for r in rows if r['steps']['3c->4a'] < 0)
    both = sum(1 for r in rows if r['steps']['3a->3c'] > 0 and r['steps']['3c->4a'] < 0)
    all_steps = np.array([abs(np.diff(prose[k])) for k in prose]).ravel()
    reflow_r = {label: float(np.corrcoef(prose[(t, 'box')], prose[(t, 'line')])[0, 1]) for t, label in TEXTS}
    cross = [float(np.corrcoef(prose[a], prose[b])[0, 1]) for a, b in combinations(prose, 2) if a[0] != b[0]]
    summary = dict(series=len(rows), rise_into_stars=up, fall_into_bio=down, both=both,
                   mean_prose_step_into_stars=float(np.mean([r['steps']['3a->3c'] for r in rows])), mean_prose_step_into_bio=float(np.mean([r['steps']['3c->4a'] for r in rows])),
                   manuscript_steps=ms_steps, prose_steps_at_least_bio_fall=int((all_steps >= abs(ms_steps['3c->4a'])).sum()), prose_steps_total=int(all_steps.size),
                   prose_steps_at_least_stars_rise=int((all_steps >= abs(ms_steps['3a->3c'])).sum()), prose_mean_abs_step=float(all_steps.mean()),
                   manuscript_mean_abs_step=float(np.mean(np.abs(np.diff(ms)))), reflow_agreement_r=reflow_r, cross_text_r_mean=float(np.mean(cross)),
                   cross_text_r_range=[float(min(cross)), float(max(cross))], spearman_ms_mean=float(np.mean([r['spearman_ms'] for r in rows])))
    print()
    print(f"Of {len(rows)} historical series, {up} rise into Stars (3a->3c; mean step {summary['mean_prose_step_into_stars']:+.3f} against the manuscript's {ms_steps['3a->3c']:+.3f}) "
          f"and {down} fall into Bio (3c->4a; mean {summary['mean_prose_step_into_bio']:+.3f} against {ms_steps['3c->4a']:+.3f}); {both} do both.")
    print(f"Prose steps between consecutive groups: mean |step| {all_steps.mean():.3f} (manuscript {summary['manuscript_mean_abs_step']:.3f}); "
          f"{summary['prose_steps_at_least_bio_fall']} of {all_steps.size} are as large as the manuscript's fall into Bio, {summary['prose_steps_at_least_stars_rise']} as large as its rise into Stars.")
    print('Agreement of the two reflows of one text (r over the 9 groups): ' + ', '.join(f'{k} {v:+.2f}' for k, v in reflow_r.items()) +
          f"; between different texts mean r {summary['cross_text_r_mean']:+.2f} (range {summary['cross_text_r_range'][0]:+.2f} to {summary['cross_text_r_range'][1]:+.2f}); "
          f"with the manuscript mean Spearman {summary['spearman_ms_mean']:+.2f}.")
    (HERE / 'prose_route.json').write_text(json.dumps(dict(rows=rows, summary=summary), indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
