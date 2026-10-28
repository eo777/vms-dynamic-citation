"""Render the spatial-method figure using a capture of the actual app.

Rebuild with: python summary_figures/build_method.py
The saved app capture supplies the source-window panel. No new run is needed.
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle
from PIL import Image

HERE = Path(__file__).resolve().parent
INK = '#222a2b'
MUTED = '#596365'
TEAL = '#177b79'
TEAL_LIGHT = '#e9f4f1'
ORANGE = '#b95e2e'
CORAL_LIGHT = '#faeee7'
GREY = '#e1e5e4'
LINE = '#dce3e1'


def label(fig, x, y, text, size=12, color=INK, weight='normal', **kwargs):
    return fig.text(x, y, text, fontsize=size, color=color, weight=weight,
                    ha='left', va='top', linespacing=1.4, **kwargs)


def step(fig, x, y, number, title):
    label(fig, x, y, str(number), 14, TEAL, 'bold')
    label(fig, x + .028, y, title, 16, INK, 'bold')


def pill(fig, xy, width, height, color):
    fig.add_artist(FancyBboxPatch(xy, width, height,
                   boxstyle='round,pad=0.009,rounding_size=0.009',
                   transform=fig.transFigure, facecolor=color, edgecolor='none'))


def main():
    ex = json.loads((HERE / 'method_example.json').read_text(encoding='utf-8'))
    target = ex['target']
    context = ex['repeat_context']
    repeats = sum(context[s:s + 100].count(ex['word']) > 1 for s in range(100))
    assert repeats == ex['repeat_windows'] == 83
    assert len(ex['sources']) == 40 and target not in ex['sources']
    assert all(i < target for i in ex['sources'])
    assert ex['example_units'] == ['ch', 'e', 'd', 'y']

    plt.rcParams.update({'font.family': 'DejaVu Sans', 'svg.fonttype': 'none'})
    fig = plt.figure(figsize=(12.8, 10.3), facecolor='white')
    label(fig, .045, .967, 'Does a less diverse window go with more repetition?', 21, weight='bold')
    label(fig, .045, .925, 'Two measurements for each word, using its recorded position on the page.', 12.5, MUTED)

    step(fig, .045, .867, 1, 'Measure its source window')
    label(fig, .045, .830, 'Earlier words above and just to the left.', 12, MUTED)
    step(fig, .585, .867, 2, 'Measure its repetition')
    label(fig, .585, .830, 'Slide a 100-word window across the same word.', 12, MUTED)

    # Actual heatmap app, expanded f78r, token 31343 selected. The capture shows
    # 40 source words / 20.3 effective pairs, matching the frozen study example.
    # Crop only the page graphic; preserve its labels, colors and selection.
    capture = Image.open(HERE / 'f78r_otedy_app_full.jpg')
    page_crop = capture.crop((270, 300, 830, 610))
    page_crop.save(HERE / 'f78r_otedy_app.png')
    ax = fig.add_axes([.045, .495, .475, .31])
    ax.imshow(page_crop)
    ax.axis('off')

    label(fig, .045, .482, 'Outlined otedy: target. Other labeled boxes: its sources.', 10.8, MUTED)
    label(fig, .045, .453, '8 lines up, 45° half-angle; 3 word widths left.', 11.3, MUTED)
    label(fig, .045, .426, 'At most 100 sources; nearer words count more.', 11.3, MUTED)
    label(fig, .045, .389, 'Component diversity', 13, weight='bold')
    label(fig, .045, .359, 'Example: chedy → ch·e, e·d, d·y', 12.5, TEAL, 'bold')
    label(fig, .045, .328, 'More varied, more evenly used pairs → higher diversity.', 11.2, MUTED)

    # Three genuine 100-word windows containing the same target occurrence.
    wx = fig.add_axes([.585, .565, .37, .21])
    offsets = [i - 99 for i, w in enumerate(context) if w == ex['word']]
    for row, start in enumerate([-99, -17, 0]):
        y = 2 - row
        wx.add_patch(Rectangle((start, y - .20), 100, .40, facecolor='#eef1f0',
                               edgecolor='#c7cfcd', lw=.85))
        occurrences = [v for v in offsets if start <= v < start + 100]
        for pos in occurrences:
            wx.plot(pos + .5, y, 's', color=ORANGE if pos == 0 else '#ddad8e',
                    markersize=10, markeredgecolor='white', markeredgewidth=.6, zorder=5)
        wx.text(111, y, 'repeat' if len(occurrences) > 1 else 'single', fontsize=11,
                va='center', color=ORANGE if len(occurrences) > 1 else MUTED)
    wx.plot([.5, .5], [-.39, 2.45], color=ORANGE, lw=.8, linestyle=(0, (2, 3)), zorder=4)
    wx.text(.5, 2.57, 'selected otedy', fontsize=11, color=ORANGE,
            ha='center', va='bottom', weight='bold')
    wx.text(-99, -.57, 'earlier text', fontsize=10.4, color=MUTED, va='top')
    wx.text(99, -.57, 'later text', fontsize=10.4, color=MUTED, va='top', ha='right')
    wx.set_xlim(-104, 146)
    wx.set_ylim(-.78, 3)
    wx.axis('off')
    label(fig, .585, .545, 'Each bar is 100 words. Colored squares are otedy.', 10.5, MUTED)
    label(fig, .585, .518, 'Three of the 100 containing windows are shown.', 10.5, MUTED)
    label(fig, .585, .462, '83 / 100 = 0.83', 26, ORANGE, 'bold')
    label(fig, .585, .411, '83 windows contain another otedy.', 12.2)
    label(fig, .585, .378, 'Its repeat score is 0.83.', 12.2)
    label(fig, .585, .336, 'Real example: otedy on f78r (Bio).', 10.5, MUTED)

    fig.add_artist(plt.Line2D([.045, .955], [.285, .285], transform=fig.transFigure,
                             color=LINE, lw=1))
    step(fig, .045, .267, 3, 'Compare words with less and more diverse source windows')
    label(fig, .045, .229, 'Within each bifolium, compare the lowest and highest fifths of source diversity.', 11.6)
    label(fig, .045, .200, 'Do this separately for small, medium and large source pools, then average.', 11.6, MUTED)
    pill(fig, (.054, .091), .292, .069, CORAL_LIGHT)
    pill(fig, (.415, .091), .292, .069, TEAL_LIGHT)
    label(fig, .068, .149, 'LEAST DIVERSE FIFTH', 10.5, ORANGE, 'bold')
    label(fig, .068, .123, 'average repeat score', 12.3)
    label(fig, .429, .149, 'MOST DIVERSE FIFTH', 10.5, TEAL, 'bold')
    label(fig, .429, .123, 'average repeat score', 12.3)
    label(fig, .367, .145, '−', 24)
    label(fig, .729, .145, '=', 24)
    label(fig, .786, .152, f"+{ex['manuscript_contrast']:.3f}", 25, INK, 'bold')
    label(fig, .786, .112, 'manuscript contrast', 10.2, MUTED)
    label(fig, .045, .052, 'Positive contrast: more repetition when the nearby components are less diverse.', 12, weight='bold')

    for extension in ['png', 'svg']:
        fig.savefig(HERE / f'method_spatial.{extension}', dpi=160, facecolor='white')
    plt.close(fig)
    print('Wrote method_spatial.png and method_spatial.svg')


if __name__ == '__main__':
    main()
