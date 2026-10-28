"""Redraw the MATTR routes without pooling the natural-language controls.

Uses the frozen layout_controls.json; does not generate new text or source pools.
Optional --verify-streams recomputes group MATTR from the saved manuscript and
copying streams and checks the baseline run settings. Outputs stay below 2 MB.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
GROUPS = ['1a', '1b', '1.5a', '2a', '3b', '3a', '3c', '4c', '4a']
LABELS = ['1a', '1b', '1.5a', '2a', '3b', '3a', '3c\nStars', '4c\nStars', '4a\nBio']
TEXTS = [('la_galen_simplicium', 'Galen · De simplicium'),
         ('la_dioscorides_longob', 'Dioscorides · Longobard version'),
         ('la_rhazes_almansor', 'Rhazes · Almansor'),
         ('la_hildegard_physica', 'Hildegard · Physica'),
         ('de_gart_augsburg1487', 'Gart der Gesundheit · 1487')]
INK, MUTED, GRID = '#243231', '#5d6d68', '#dce4de'
BLUE, TEAL, ORANGE = '#2678bc', '#177b79', '#b96530'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def routes(data):
    result = {}
    for key, rows in data.items():
        samples = np.array([[row['route']['groups'][g]['mattr100'] for g in GROUPS] for row in rows])
        mean = samples.mean(axis=0)
        result[key] = dict(n_streams=len(rows), values=mean.tolist(),
                           minimum=samples.min(axis=0).tolist(), maximum=samples.max(axis=0).tolist(),
                           into_stars=float(mean[6]-mean[5]), stars_to_bio=float(mean[8]-mean[6]),
                           first_stars_step=float(mean[7]-mean[6]), final_bio_step=float(mean[8]-mean[7]))
    return result


def verify_streams(data):
    sys.path.insert(0, str(STUDY))
    import data as D
    ms = D.manuscript()
    checked, settings = [], {}
    for key in ['manuscript', 'timm', 'timm_spatial', 'noinnov_far0', 'noinnov_spatial', 'far0_spatial']:
        sources = [None] if key == 'manuscript' else D.STREAMS[key][1][:len(data[key])]
        for seed_index, source in enumerate(sources):
            lines = [row['words'] for row in ms['lines']] if source is None else D.read_stream(source)
            assert len(lines) == len(ms['lines']) == 4130
            by_group = {}
            for row, words in zip(ms['lines'], lines):
                by_group.setdefault(row['group'], []).extend(words)
            errors = [abs(D.mattr(words)-data[key][seed_index]['route']['groups'][g]['mattr100'])
                      for g, words in by_group.items()]
            assert max(errors) < 1e-12, (key, seed_index, max(errors))
            checked.append(dict(series=key, seed_index=seed_index, max_absolute_error=max(errors),
                                input_sha256=digest(source) if source else digest(D.TOKENS)))
    for key in ['timm', 'timm_spatial']:
        path = D.STREAMS[key][1][0].parent / 'run.json'
        args = json.loads(path.read_text())['args']
        wanted = dict(beta_c=0.0, beta_m=0.0, retry=0, far=0.0, innovate=False, match_pages=True)
        for k, value in wanted.items():
            assert args[k] == value, (key, k, args[k])
        settings[key] = dict(**wanted, spatial=args.get('spatial', False), run_json_sha256=digest(path))
    return dict(streams=checked, baseline_settings=settings,
                note='Recomputed saved sequences, with no model regeneration. Baseline settings checked on seed 1.')


def setup(ax, ylim=(.63, .92), small=False):
    ax.set_facecolor('#fffefb')
    ax.axvspan(5.5, 8.45, color='#edf0e9', zorder=0)
    ax.set_xlim(-.25, 8.25)
    ax.set_ylim(*ylim)
    ax.set_xticks(np.arange(9), LABELS if not small else GROUPS)
    ax.tick_params(axis='both', length=0, labelsize=9.5 if not small else 9, pad=7)
    ax.grid(axis='y', color=GRID, linewidth=.7)
    ax.set_axisbelow(True)
    for side in ['top', 'right']:
        ax.spines[side].set_visible(False)
    for side in ['left', 'bottom']:
        ax.spines[side].set_color(GRID)
    ax.set_xlabel('Golf group in Path 1 order', fontsize=10, labelpad=10)


def line(ax, route, key, label, color, style='-', width=2, range_=False):
    row = route[key]
    x = np.arange(9)
    if range_:
        ax.fill_between(x, row['minimum'], row['maximum'], color=color, alpha=.09, linewidth=0)
    return ax.plot(x, row['values'], label=label, color=color, ls=style, lw=width,
                   marker='o', ms=3.8, zorder=5 if key == 'manuscript' else 3)[0]


def save(fig, name):
    fig.savefig(HERE / f'{name}.png', dpi=165, facecolor='#fffefb')
    fig.savefig(HERE / f'{name}.svg', facecolor='#fffefb')
    plt.close(fig)


def model_chart(route):
    fig, axes = plt.subplots(1, 2, figsize=(12.6, 5.7), sharey=True)
    fig.subplots_adjust(left=.065, right=.985, bottom=.33, top=.81, wspace=.10)
    for ax in axes:
        setup(ax)
        line(ax, route, 'manuscript', 'Manuscript', INK, width=2.5)
    axes[0].set_title('Original Timm · fixed copying and mutation settings', loc='left', fontsize=12, pad=17)
    line(axes[0], route, 'timm', 'Original page-source draw', BLUE, range_=True)
    line(axes[0], route, 'timm_spatial', 'Sources from the spatial window', TEAL, '--', range_=True)
    axes[1].set_title('Markov controls · no use of page geometry', loc='left', fontsize=12, pad=17)
    for key, label, color, style in [('bigram_whole', 'Whole-manuscript training', '#367b43', '-'),
                                    ('bigram_currier', 'Separate Currier A/B training', '#74952f', '--'),
                                    ('bigram_section', 'Separate section training', '#1e6251', ':')]:
        line(axes[1], route, key, label, color, style)
    axes[0].set_ylabel('MATTR100', labelpad=10)
    for ax in axes:
        ax.legend(loc='upper left', bbox_to_anchor=(ax.get_position().x0, .18),
                  bbox_transform=fig.transFigure, frameon=False, fontsize=9.2, handlelength=2.6)
    fig.text(.065, .955, 'The late rise and fall appear under fixed copying rules', fontsize=16, weight='bold', color=INK)
    fig.text(.065, .905, 'The shaded stretch is Stars → Bio. Compare the direction of change as well as the level.', fontsize=11, color=MUTED)
    fig.text(.065, .025, 'Copying curves: mean of two saved seeds; faint bands show their range. Markov curves: mean of three seeds.', fontsize=9, color=MUTED)
    save(fig, 'mattr_swings_models')


def prose_chart(route):
    fig, axes = plt.subplots(2, 3, figsize=(12.6, 7.6), sharex=True, sharey=True)
    fig.subplots_adjust(left=.065, right=.98, bottom=.085, top=.84, wspace=.16, hspace=.48)
    colors = ['#1f5fb8', '#c27430', '#7650aa', '#177b79', '#a52f64']
    for ax, (key, name), color in zip(axes.ravel(), TEXTS, colors):
        setup(ax, (.63, .94), small=True)
        line(ax, route, 'manuscript', 'Manuscript', INK, width=1.9)
        line(ax, route, 'prose_box_'+key, 'One word per manuscript box', color, width=1.8)
        line(ax, route, 'prose_line_'+key, 'Fill each line’s character budget', color, '--', width=1.8)
        ax.set_title(name, loc='left', fontsize=11, pad=12)
        ax.tick_params(labelbottom=True)
        ax.set_xlabel('')
        a = route['prose_box_'+key]['stars_to_bio']
        b = route['prose_line_'+key]['stars_to_bio']
        ax.text(.02, .04, f'Stars → Bio: {a:+.3f} / {b:+.3f}', transform=ax.transAxes, fontsize=9, color=color)
    axes[0, 0].set_ylabel('MATTR100')
    axes[1, 0].set_ylabel('MATTR100')
    key = axes[1, 2]
    key.axis('off')
    key.legend(handles=[Line2D([], [], color=INK, lw=2, label='Manuscript'),
                        Line2D([], [], color=MUTED, lw=2, label='One word per manuscript box'),
                        Line2D([], [], color=MUTED, lw=2, ls='--', label='Fill each line’s character budget')],
               loc='upper left', frameon=False, fontsize=10, handlelength=2.7, labelspacing=1.0)
    key.text(.02, .41, 'Shaded: 3c and 4c (Stars), then 4a (Bio).\nThe black reference is identical in every panel.',
             transform=key.transAxes, fontsize=10, color=MUTED, linespacing=1.6)
    key.text(.02, .14, 'Manuscript Stars → Bio: −0.128\nIndividual prose curves: −0.010 to +0.036',
             transform=key.transAxes, fontsize=10, color=INK, linespacing=1.6)
    fig.text(.065, .96, 'The historical texts do not share the same late fall', fontsize=16, weight='bold', color=INK)
    fig.text(.065, .915, 'Five historical texts laid into the same manuscript pages, each shown with two reflow methods.', fontsize=11, color=MUTED)
    fig.text(.065, .025, 'Golf groups in Path 1 order. Each value is MATTR100 of the continuous text assigned to that group.', fontsize=10, color=MUTED)
    save(fig, 'mattr_swings_prose')


def governed_chart(route):
    fig, ax = plt.subplots(figsize=(10.3, 5.0))
    fig.subplots_adjust(left=.09, right=.97, top=.81, bottom=.27)
    setup(ax, (.55, .90))
    line(ax, route, 'manuscript', 'Manuscript', INK, width=2.5)
    for key, label, color, style in [('noinnov_far0', 'Far 0, no innovator · page draw', BLUE, '-'),
                                    ('noinnov_spatial', 'Far 0, no innovator · spatial draw', TEAL, '--'),
                                    ('far0_spatial', 'Far 0, with innovator · spatial draw', '#7650aa', ':')]:
        line(ax, route, key, label, color, style, range_=True)
    ax.set_ylabel('MATTR100')
    ax.legend(loc='upper left', bbox_to_anchor=(0, -.30), frameon=False, ncol=2, fontsize=9)
    fig.text(.09, .95, 'The governed variants also rise into Stars and fall into Bio', fontsize=14, weight='bold', color=INK)
    fig.text(.09, .89, 'These runs use fitted composition targets; the fixed-rule test is Original Timm above.', fontsize=10, color=MUTED)
    save(fig, 'mattr_swings_governed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-streams', action='store_true')
    args = parser.parse_args()
    source = STUDY / 'layout_controls.json'
    data = json.loads(source.read_text(encoding='utf-8'))
    route = routes(data)
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'text.color': INK,
                         'axes.labelcolor': MUTED, 'xtick.color': MUTED, 'ytick.color': MUTED,
                         'svg.fonttype': 'none'})
    model_chart(route)
    prose_chart(route)
    governed_chart(route)
    output = dict(source='layout_controls.json', source_sha256=digest(source), groups=GROUPS, routes=route,
                  statistic='MATTR100 of each group concatenated in Path 1 order; windows wholly within that group.',
                  prediction_scope='Regional rise/fall under fixed copying rules, not a claim of a full trajectory fit.')
    if args.verify_streams:
        output['verification'] = verify_streams(data)
    else:
        previous = HERE / 'mattr_swings.json'
        if previous.exists():
            old = json.loads(previous.read_text())
            if old.get('source_sha256') == output['source_sha256'] and 'verification' in old:
                output['verification'] = old['verification']
    (HERE / 'mattr_swings.json').write_text(json.dumps(output, indent=2)+'\n', encoding='utf-8')
    for key in ['manuscript', 'timm', 'timm_spatial', 'bigram_whole', 'bigram_currier', 'bigram_section']:
        row = route[key]
        print(f'{key}: into Stars {row["into_stars"]:+.6f}; Stars to Bio {row["stars_to_bio"]:+.6f}')
    print('Built three figures and compact metrics; no new model runs.')


if __name__ == '__main__':
    main()
