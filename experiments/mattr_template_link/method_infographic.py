"""method_spatial.png: an annotated infographic built from three captures of the governor app (27 October, user's request):
the f78r page as the app draws it, the same page after the word otedy is clicked (cone, left reach, lit sources), and the
app's readout bar. The captures were taken in Chrome from http://127.0.0.1:8765/heatmap.html#scope=4a&window=100&
direction=spatial&colors=components&left=3&depth=8&angle=45&weight=distance with the page isolated and the svg at 520 px;
their paths and the geometry below (CSS pixels of that view) are recorded here so the figure can be rebuilt from new captures."""
import sys
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image

HERE = Path(__file__).resolve().parent
CAP = HERE / 'captures'                              # the three Chrome captures, kept with the study
BEFORE = CAP / 'f78r_before_click.png'               # page region, CSS x 306-845, y 211-945, no selection
AFTER = CAP / 'f78r_otedy_clicked.png'               # same region, token 31343 (otedy) selected
STATUS = CAP / 'readout_bar.png'                     # readout bar, CSS x 138-1604, y 49-190
OX, OY = 306, 211                                    # CSS origin of the page captures
TARGET = (522, 429, 549, 441)                        # CSS box of the clicked word
APEX = (535.3, 435.0)
CONE_TOP_Y, CONE_LEFT_X, CONE_RIGHT_X = 337.0, 437.3, 633.3
REACH_X = 450.7
INK, SEC, LIGHT, ACCENT = '#1f1f1d', '#5a5955', '#f0efec', '#f2c27b'
CIRCLED = '①②③④⑤'


def px(x, y):
    return x - OX, y - OY


def callout(ax, k, at, mark, color=ACCENT):
    """Numbered marker at `mark` (image px) with a short leader to `at`."""
    ax.annotate('', xy=at, xytext=mark, arrowprops=dict(arrowstyle='-', color=color, lw=0.9), annotation_clip=False)
    ax.text(mark[0], mark[1], str(k), fontsize=6.4, color=INK, ha='center', va='center', weight='bold',
            bbox=dict(boxstyle='circle,pad=0.25', fc=color, ec='none'), clip_on=False)


def para(fig, x, y, text, width, size=6.9, color=SEC, lead=0.0215):
    wrapped = textwrap.fill(text, width)
    fig.text(x, y, wrapped, fontsize=size, color=color, va='top', linespacing=1.35)
    return y - lead * (wrapped.count('\n') + 1)


def main(out=HERE / 'method_spatial.png'):
    before, after, status = (Image.open(p).convert('RGB') for p in (BEFORE, AFTER, STATUS))
    status = status.crop((0, 0, 1180, status.height))           # controls, readout and pair chips; the restore button is cut
    plt.rcParams['font.family'] = 'DejaVu Sans'
    fig = plt.figure(figsize=(13, 8.6), facecolor='white')
    fig.text(0.015, 0.978, 'How the spatial statistic is built, shown on the governor app itself', fontsize=10.5, color=INK, va='top', weight='bold')
    para(fig, 0.015, 0.948, 'Page f78r (Bio) in the app\'s MATTR heatmap, Direction = Spatial sources, Colors = Component diversity, source cap 100, distance weight. Every text in this study '
                            '(manuscript, generators, Markov chains, reflowed prose) is laid into these lines and boxes and scored by the same selector.', 190, size=7.2)

    # panel 1: the page before the click
    ax1 = fig.add_axes([0.015, 0.345, 0.27, 0.555])
    ax1.imshow(before)
    ax1.axis('off')
    ax1.set_title('1 · A manuscript page as the app draws it (f78r)', loc='left', fontsize=8.4, color=INK, pad=4)
    callout(ax1, 1, (335, 168), (375, 150))
    callout(ax1, 2, (330, 485), (390, 470))
    callout(ax1, 3, (280, 120), (330, 92))
    callout(ax1, 4, (400, 196), (440, 230))
    y = 0.325
    y = para(fig, 0.015, y, '① red: the words in view for this word are of low diversity, few distinct unit pairs among them.', 66)
    y = para(fig, 0.015, y, '② teal: high diversity in view.', 66)
    y = para(fig, 0.015, y, '③ ④ grey or white: not scored (fewer than five contributing words, fewer than three effective sources, or an incomplete 100-word window).', 66)
    y = para(fig, 0.015, y, 'Each rectangle is one word\'s recorded box; the blank regions are the page\'s drawings. Colour is the score of the words in view for that word, not of the word itself.', 66)

    # panel 2: after the click
    ax2 = fig.add_axes([0.30, 0.345, 0.27, 0.555])
    ax2.imshow(after)
    ax2.axis('off')
    ax2.set_title('2 · Click a word: what is "in view" for it', loc='left', fontsize=8.4, color=INK, pad=4)
    tx0, ty0, tx1, ty1 = TARGET
    tcx, tcy = px((tx0 + tx1) / 2, (ty0 + ty1) / 2)
    callout(ax2, 1, (tcx + 12, tcy + 5), (300, 268))
    cx, cy = px(CONE_RIGHT_X - 25, CONE_TOP_Y + 2)
    callout(ax2, 2, (cx, cy), (375, 110))
    rx, ry = px(REACH_X + 8, APEX[1] + 2)
    callout(ax2, 3, (rx, ry), (110, 262))
    sx, sy = px(CONE_LEFT_X + 70, CONE_TOP_Y + 45)
    callout(ax2, 4, (sx, sy), (85, 150))
    y = 0.325
    y = para(fig, 0.30, y, '① the clicked word, otedy (line 12 of f78r): the target whose repeat score is predicted.', 66)
    y = para(fig, 0.30, y, '② the cone: 8 line spacings up, 45° half-angle; every box it touches on this page is a source.', 66)
    y = para(fig, 0.30, y, '③ the left reach: 3 median word widths on the same line.', 66)
    y = para(fig, 0.30, y, '④ lit boxes: the 40 source words, brighter = nearer (distance weight); everything else is dimmed. Only earlier words count, above or to the left; at most 100 sources.', 66)

    # readout bar
    ax3 = fig.add_axes([0.015, 0.03, 0.555, 0.095])
    ax3.imshow(status)
    ax3.axis('off')
    ax3.set_title('the app\'s readout for the clicked word', loc='left', fontsize=7.6, color=INK, pad=3)
    para(fig, 0.585, 0.125, 'Score of otedy: 20.3 effective within-word unit pairs among its 40 sources (10.1 effective sources after distance weighting); the chips are the weighted pair shares. '
                            'The study\'s own per-token table lists the same token, 31343, with components 20.319 and pool 40.', 84, size=6.8)

    # panel 3: from one word to the statistic
    x0 = 0.60
    fig.text(x0, 0.905, '3 · From one word to the statistic', fontsize=8.4, color=INK, va='top')
    blocks = [
        ('Pool score of a word N', 'The diversity of N\'s sources, by the app\'s selector: component diversity (effective number of within-word unit pairs, as in the readout), '
                                   'glyph H2 (conditional entropy of the sources\' units) or word diversity (1 − Σ p(spelling)²). These are the three marker shapes of the contrast charts.'),
        ('Repeat score of N', 'The share of the 100-word windows containing N in which N\'s spelling occurs again (0 = never repeated nearby, 1 = always); the "word impact" of the component-impact study.'),
        ('The contrast', 'Within each bifolium the scored words are sorted by pool score and split into fifths. Contrast = mean repeat score of the fifth with the LEAST diverse pool minus the mean of the fifth '
                         'with the MOST diverse pool, averaged over pool-size tertiles (small, middle, large pools) and over bifolia. Positive: a word that follows a less diverse pool is more often a repeat. '
                         'This number is the horizontal axis of the contrast charts.'),
        ('Why pool size is held fixed', 'Pool diversity rises with the number of words in the cone, and pool size itself predicts repetition (small pools sit at the tops of pages), so the contrast is taken inside pool-size tertiles.'),
        ('The same for every text', 'Generated streams and reflowed prose are written into the manuscript\'s own lines (boxes by character position inside each line\'s recorded extent) and scored by the same code, so the charts compare like with like.'),
    ]
    y = 0.872
    for head, body in blocks:
        fig.text(x0, y, head, fontsize=7.5, color=INK, va='top', weight='bold')
        y -= 0.027
        y = para(fig, x0, y, body, 88) - 0.018
    fig.savefig(out, dpi=140, facecolor='white')
    plt.close(fig)
    print('wrote', Path(out).name)


if __name__ == '__main__':
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / 'method_spatial.png')
