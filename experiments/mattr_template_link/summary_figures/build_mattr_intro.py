"""Draw the manuscript-only opening figure from the verified bifolium values."""
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

import build_bifolium_mattr as B
import build_mattr_swings as G

HERE = Path(__file__).resolve().parent


def main():
    source = HERE / 'mattr_bifolia.json'
    saved = json.loads(source.read_text(encoding='utf-8'))
    raw = json.loads((HERE.parent / 'layout_controls.json').read_text(encoding='utf-8'))
    original = raw['manuscript'][0]['route']['nodes']
    values = saved['routes']['manuscript']['values']
    assert saved['bifolia'] == list(original)
    assert values == [original[node]['mattr100'] for node in saved['bifolia']]
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11, 'svg.fonttype': 'none'})
    fig, ax = plt.subplots(figsize=(12.6, 5.3))
    fig.subplots_adjust(left=.075, right=.98, top=.69, bottom=.20)
    for index, (a, b, name) in enumerate(B.stretches(saved['section_names'], 0, len(values))):
        if index % 2 == 1:
            ax.axvspan(a - .5, b - .5, color='#edf0e9', zorder=0)
        angle = 65 if b - a < 2 else 0
        ax.text((a + b - 1) / 2, 1.035, name.replace('Pharma / Astro', 'Pharma /\nAstro'),
                transform=ax.get_xaxis_transform(), ha='left' if angle else 'center', va='bottom',
                fontsize=9.5, rotation=angle, color=G.MUTED)
    ax.plot(np.arange(len(values)), values, color=G.INK, linewidth=2.2, marker='o', markersize=4)
    ax.set_xlim(-.5, len(values) - .5)
    ax.set_ylim(.55, .95)
    ticks = [0, 9, 19, 29, 39, 49]
    ax.set_xticks(ticks, [str(i + 1) for i in ticks])
    ax.set_xlabel('Bifolium position in Path 1 order', color=G.MUTED, labelpad=10)
    ax.set_ylabel('MATTR100', color=G.INK, labelpad=10)
    ax.grid(axis='y', color=G.GRID, linewidth=.8)
    ax.set_axisbelow(True)
    ax.set_facecolor('#fffefb')
    ax.tick_params(axis='both', length=0, colors=G.MUTED, pad=6)
    for side in ('top', 'right'):
        ax.spines[side].set_visible(False)
    for side in ('left', 'bottom'):
        ax.spines[side].set_color(G.GRID)
    fig.text(.075, .955, 'Voynich word diversity rises and falls across the manuscript',
             fontsize=17, weight='bold', color=G.INK)
    fig.text(.075, .89, 'Higher MATTR = more distinct words. Lower MATTR = more repetition.',
             fontsize=11, color=G.MUTED)
    fig.text(.075, .035, 'Each point is one bifolium. Section names describe the main content of each stretch.',
             fontsize=10, color=G.MUTED)
    for ext in ('png', 'svg'):
        fig.savefig(HERE / f'mattr_manuscript_intro.{ext}', dpi=165, facecolor='#fffefb')
    plt.close(fig)
    (HERE / 'mattr_manuscript_intro.json').write_text(json.dumps({
        'source': source.name, 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'bifolia': saved['bifolia'], 'section_names': saved['section_names'], 'mattr100': values,
        'verification': 'All 50 values exactly match layout_controls.json; no model runs.',
        'inspiration': 'https://www.voynich.ninja/thread-6244.html',
        'inspiration_post': 'Koen G, 25 October 2026, Relation between word types and vocabulary density.',
    }, indent=2) + '\n', encoding='utf-8')
    print('Built manuscript-only MATTR figure; all 50 saved values matched.')


if __name__ == '__main__':
    main()
