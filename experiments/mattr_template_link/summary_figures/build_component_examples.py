"""Build the page-context and component-diversity figures from app screenshots."""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Rectangle
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
INK = '#222a2b'
MUTED = '#596365'
TEAL = '#177b79'
ORANGE = '#b95e2e'


def text(fig, x, y, value, size=12, color=INK, weight='normal', **kwargs):
    return fig.text(x, y, value, fontsize=size, color=color, weight=weight,
                    ha='left', va='top', linespacing=1.45, **kwargs)


def capture(name):
    meta = json.loads((HERE / f'{name}_capture.json').read_text(encoding='utf-8'))
    image = Image.open(HERE / f'{name}_app.jpg')
    rect = meta['image'] if meta.get('fullPageView') else meta['crop']
    sx = image.width / meta['viewport']['width']
    sy = image.height / meta['viewport']['height']
    bounds = tuple(round(v) for v in (rect['left'] * sx, rect['top'] * sy,
                                     rect['right'] * sx, rect['bottom'] * sy))
    assert 0 <= bounds[0] < bounds[2] <= image.width
    assert 0 <= bounds[1] < bounds[3] <= image.height
    cropped = image.crop(bounds)
    cropped.save(HERE / f'{name}.png')
    return cropped


def save(fig, stem):
    fig.savefig(HERE / f'{stem}.png', dpi=160, facecolor='white')
    plt.close(fig)


def main():
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'svg.fonttype': 'none'})
    data = json.loads((HERE / 'component_examples.json').read_text(encoding='utf-8'))
    high, low = data['examples']
    assert (high['target'], low['target']) == (32564, 32673)
    assert (round(high['score']['components'], 1), round(low['score']['components'], 1)) == (22.1, 13.6)
    page, higher, lower = (capture(name) for name in ('f75r_page', 'f75r_high', 'f75r_low'))

    # Whole-page orientation first. Only A/B callouts are added to this capture.
    fig = plt.figure(figsize=(8.5, 12.8), facecolor='white')
    text(fig, .055, .965, 'Component diversity on f75r', 23, weight='bold')
    text(fig, .055, .928, 'Each box is colored by the diversity of its source window.', 12, MUTED)
    ax = fig.add_axes([.04, .205, .92, .695])
    ax.imshow(page, extent=(0, 636, 900, 0))
    for case, letter, color, label_x in [(high, 'A', TEAL, 676), (low, 'B', ORANGE, -31)]:
        x0, y0, x1, y1 = case['display_box']
        cy = (y0 + y1) / 2
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False,
                               edgecolor=color, lw=2.2))
        ax.annotate('', xy=(x1 if letter == 'A' else x0, cy),
                    xytext=(label_x - 15 if letter == 'A' else label_x + 15, cy),
                    arrowprops={'arrowstyle': '-', 'color': color, 'lw': 1.8})
        ax.text(label_x, cy, letter, ha='center', va='center', color='white',
                fontsize=14, weight='bold',
                bbox={'boxstyle': 'circle,pad=.28', 'facecolor': color, 'edgecolor': color})
    ax.set_xlim(-55, 700)
    ax.set_ylim(900, 0)
    ax.set_aspect('equal')
    ax.axis('off')
    domain = json.loads((HERE / 'f75r_page_capture.json').read_text(encoding='utf-8'))['colorDomain']
    lo, hi = domain['low'], domain['high']
    bar = fig.add_axes([.17, .166, .66, .014])
    bar.imshow(np.linspace(lo, hi, 501)[None, :], aspect='auto',
               extent=(lo, hi, 0, 1), cmap=ListedColormap(data['palette']))
    bar.set_yticks([])
    ticks = np.linspace(lo, hi, 5)
    bar.set_xticks(ticks, [f'{v:.1f}' for v in ticks], fontsize=9.5)
    bar.tick_params(axis='x', length=0, pad=6, colors=MUTED)
    for spine in bar.spines.values():
        spine.set_visible(False)
    text(fig, .17, .201, 'Component diversity · effective pairs', 10.8, MUTED)
    text(fig, .075, .103, 'A  Higher component diversity: 22.1', 12.5, TEAL, 'bold')
    text(fig, .075, .075, 'B  Lower component diversity: 13.6', 12.5, ORANGE, 'bold')
    text(fig, .075, .037, 'Image and word coordinates: The Voynichese Project.', 9.5, MUTED)
    save(fig, 'f75r_page_context')

    # The panels are browser captures, including the page image, native boxes,
    # word labels, cone and left-reach indicator. No source window is redrawn.
    fig = plt.figure(figsize=(12.8, 7.5), facecolor='white')
    text(fig, .045, .965, 'One spelling, two source windows', 22, weight='bold')
    text(fig, .045, .911, 'Two qokeedy occurrences on f75r. Each score describes the surrounding source window.', 12.3, MUTED)
    for x, label, score, color, shot in [
        (.045, 'A  Higher component diversity', high['score']['components'], TEAL, higher),
        (.525, 'B  Lower component diversity', low['score']['components'], ORANGE, lower),
    ]:
        text(fig, x, .832, label, 15, color, 'bold')
        text(fig, x, .785, f'{score:.1f} effective pairs', 20, color, 'bold')
        ax = fig.add_axes([x, .325, .43, .425])
        ax.imshow(shot)
        ax.axis('off')
    text(fig, .045, .295, 'lor, sain, checthy and other forms\nsupply a wider mix of glyph pairs.', 12)
    text(fig, .525, .295, 'Repeated qokeedy / qokedy forms\nkeep reusing q·o, o·k and d·y.', 12)
    fig.add_artist(plt.Line2D([.045, .955], [.175, .175], transform=fig.transFigure,
                             color='#dce3e1', lw=1))
    text(fig, .045, .151, 'Both windows: 8 line spacings up · 45° half-angle · 3 word widths left.', 12.3)
    text(fig, .045, .110, 'The qokeedy at the point of each cone is the target word.', 11.5, MUTED)
    text(fig, .045, .056, 'A higher score means a wider, more evenly used mix of adjacent glyph pairs.', 12.2, weight='bold')
    save(fig, 'component_diversity_examples')
    print('Built full-page context and both component-diversity examples.')


if __name__ == '__main__':
    main()
