"""Bifolium MATTR views for the report, from the frozen route measurements.

No models or spatial pools are generated. A default run draws four charts and
saves compact values; --verify-streams also recomputes saved copying sequences.
"""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np

import build_mattr_swings as G

HERE = Path(__file__).resolve().parent
NAMES = {'1a': 'Herbal A', '1b': 'Herbal A', '1.5a': 'Herbal A',
         '2a': 'Pharma / Astro', '5a': 'Cosmological', '6': 'Stars',
         '3b': 'Herbal B', '3a': 'Herbal B', '3c': 'Stars', '4c': 'Stars', '4a': 'Bio'}
COLORS = ['#1f5fb8', '#c27430', '#7650aa', '#177b79', '#a52f64']
MODEL_LINES = [('timm', 'Original Timm · page-source draw', G.BLUE, '-'),
               ('timm_spatial', 'Original Timm · spatial sources', G.TEAL, '--')]
MARKOV_LINES = [('bigram_whole', 'Whole-manuscript training', '#367b43', '-'),
                ('bigram_currier', 'Separate Currier A/B training', '#74952f', '--'),
                ('bigram_section', 'Separate section training', '#1e6251', ':')]


def extract(data):
    original = data['manuscript'][0]['route']['nodes']
    ids = list(original)
    groups = [original[node]['group'] for node in ids]
    assert len(ids) == 50 and groups[30] == '3b'
    series = {}
    for key, rows in data.items():
        assert all(list(row['route']['nodes']) == ids for row in rows)
        values = np.array([[row['route']['nodes'][node]['mattr100'] for node in ids] for row in rows])
        assert np.isfinite(values).all()
        series[key] = {'n_streams': len(rows), 'values': values.mean(axis=0).tolist(),
                       'minimum': values.min(axis=0).tolist(), 'maximum': values.max(axis=0).tolist()}
    return {'bifolia': ids, 'groups': groups, 'section_names': [NAMES[group] for group in groups],
            'routes': series}


def stretches(labels, start, end):
    first = start
    for i in range(start + 1, end + 1):
        if i == end or labels[i] != labels[first]:
            yield first, i, labels[first]
            first = i


def setup(ax, data, start, *, small=False):
    end = len(data['bifolia'])
    for index, (a, b, name) in enumerate(stretches(data['section_names'], start, end)):
        if index % 2 == 1:
            ax.axvspan(a - .5, b - .5, color='#edf0e9', zorder=0)
        angle = 70 if b - a < 2 else 0
        size = 7 if small else 9
        label = name.replace('Pharma / Astro', 'Pharma /\nAstro') if small else name
        ax.text((a + b - 1) / 2, 1.025, label, transform=ax.get_xaxis_transform(),
                ha='left' if angle else 'center', va='bottom', fontsize=size,
                rotation=angle, color=G.MUTED, clip_on=False)
    ax.set_xlim(start - .5, end - .5)
    ax.set_ylim(.55, .95)
    # Leaf pairs identify physical bifolia; illustration names identify stretches.
    ticks = list(range(start, end, 2 if small and start == 0 else 1))
    ax.set_xticks(ticks, [data['bifolia'][i].split(':', 1)[1].replace('-', '–') for i in ticks],
                  rotation=90, fontsize=7 if small else 8)
    ax.tick_params(axis='both', length=0, pad=5)
    ax.grid(axis='y', color=G.GRID, linewidth=.7)
    ax.set_axisbelow(True)
    ax.set_facecolor('#fffefb')
    for side in ['top', 'right']:
        ax.spines[side].set_visible(False)
    for side in ['left', 'bottom']:
        ax.spines[side].set_color(G.GRID)


def line(ax, data, key, label, color, style='-', start=0, band=False):
    row = data['routes'][key]
    x = np.arange(start, len(data['bifolia']))
    if band:
        ax.fill_between(x, row['minimum'][start:], row['maximum'][start:], color=color, alpha=.08, linewidth=0)
    return ax.plot(x, row['values'][start:], color=color, ls=style, lw=2.1 if key == 'manuscript' else 1.8,
                   marker='o', ms=3.1, label=label, zorder=5 if key == 'manuscript' else 3)[0]


def save(fig, name):
    fig.savefig(HERE / f'{name}.png', dpi=165, facecolor='#fffefb')
    svg = HERE / f'{name}.svg'
    fig.savefig(svg, facecolor='#fffefb')
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text(encoding='utf-8').splitlines()) + '\n', encoding='utf-8')
    plt.close(fig)


def pair_chart(data, markov=False):
    fig, axes = plt.subplots(2, 1, figsize=(12.6, 9.2), sharey=True)
    fig.subplots_adjust(left=.07, right=.98, top=.80, bottom=.19, hspace=.65)
    specs = MARKOV_LINES if markov else MODEL_LINES
    for ax, start in zip(axes, [0, 30]):
        setup(ax, data, start)
        line(ax, data, 'manuscript', 'Manuscript', G.INK, start=start)
        for key, label, color, style in specs:
            line(ax, data, key, label, color, style, start=start, band=not markov)
        ax.set_ylabel('MATTR100', fontsize=10)
    axes[1].set_xlabel('Bifolium leaf pair · Path 1 order', fontsize=10)
    title = 'Markov controls, bifolium by bifolium' if markov else 'The rise and fall extend across multiple bifolia'
    fig.text(.07, .955, title, fontsize=17, weight='bold', color=G.INK)
    fig.text(.07, .915, 'All 50 bifolia above; Herbal B → Stars → Bio enlarged below. Each point is one bifolium.',
             fontsize=10.5, color=G.MUTED)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='lower center', bbox_to_anchor=(.53, .05), frameon=False,
               ncol=2 if markov else 3, fontsize=9.5, handlelength=2.6)
    note = ('Markov curves average three saved seeds.' if markov else
            'Original Timm: fixed copying and mutation settings, two saved seeds; faint bands show their range.')
    fig.text(.07, .012, note, fontsize=9, color=G.MUTED)
    save(fig, 'mattr_bifolia_markov' if markov else 'mattr_bifolia_models')


def prose_chart(data, full=False):
    start = 0 if full else 30
    fig, axes = plt.subplots(3, 2, figsize=(12.6, 13.8 if full else 10.8), sharey=True)
    fig.subplots_adjust(left=.065, right=.98, top=.81 if full else .86, bottom=.095,
                        wspace=.16, hspace=1.10 if full else .65)
    for ax, (key, name), color in zip(axes.flat, G.TEXTS, COLORS):
        setup(ax, data, start, small=True)
        line(ax, data, 'manuscript', 'Manuscript', G.INK, start=start)
        line(ax, data, 'prose_box_' + key, 'One word per manuscript box', color, start=start)
        line(ax, data, 'prose_line_' + key, 'Fill each line’s character budget', color, '--', start=start)
        ax.set_title(name, loc='left', fontsize=11, pad=70 if full else 33)
    for row in axes:
        row[0].set_ylabel('MATTR100', fontsize=10)
    key = axes[2, 1]
    key.axis('off')
    key.legend(handles=[Line2D([], [], color=G.INK, lw=2.1, label='Manuscript'),
                        Line2D([], [], color=G.MUTED, lw=1.8, label='One word per manuscript box'),
                        Line2D([], [], color=G.MUTED, lw=1.8, ls='--', label='Fill each line’s character budget')],
               loc='upper left', frameon=False, fontsize=10, handlelength=2.6, labelspacing=1)
    key.text(.02, .32, 'Same bifolia and MATTR scale in every panel.\nThe manuscript is the black reference throughout.',
             transform=key.transAxes, color=G.MUTED, fontsize=10, linespacing=1.6)
    key.text(.02, .02, 'Each historical text is shown separately,\nwith both reflow methods.',
             transform=key.transAxes, color=G.INK, fontsize=10, linespacing=1.6)
    fig.text(.065, .965, 'Historical texts across the same bifolia', fontsize=17, weight='bold', color=G.INK)
    fig.text(.065, .925, 'All 50 bifolia in Path 1 order.' if full else
             'The Herbal B → Stars → Bio stretch, with every bifolium shown.', fontsize=11, color=G.MUTED)
    fig.text(.065, .025, 'Horizontal axis: bifolium leaf pair, in Path 1 order. Section names describe the main content of each route stretch.',
             fontsize=9.5, color=G.MUTED)
    save(fig, 'mattr_bifolia_prose_all' if full else 'mattr_bifolia_prose')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-streams', action='store_true')
    args = parser.parse_args()
    source = HERE.parent / 'layout_controls.json'
    raw = json.loads(source.read_text(encoding='utf-8'))
    data = extract(raw)
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'text.color': G.INK,
                         'axes.labelcolor': G.MUTED, 'xtick.color': G.MUTED, 'ytick.color': G.MUTED,
                         'svg.fonttype': 'none'})
    pair_chart(data)
    pair_chart(data, markov=True)
    prose_chart(data)
    prose_chart(data, full=True)
    data.update(source='layout_controls.json', source_sha256=G.digest(source),
                statistic='MATTR100 of each bifolium in Path 1 order; windows wholly within that bifolium.',
                labels='Section names describe the dominant content of route stretches; mixed bifolia retain their original text.')
    output = HERE / 'mattr_bifolia.json'
    if args.verify_streams:
        data['verification'] = G.verify_streams(raw)
    elif output.exists():
        old = json.loads(output.read_text(encoding='utf-8'))
        if old.get('source_sha256') == data['source_sha256'] and 'verification' in old:
            data['verification'] = old['verification']
    output.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print('Built four bifolium charts and compact values. No model runs.')


if __name__ == '__main__':
    main()
