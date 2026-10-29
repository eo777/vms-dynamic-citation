"""Layout check for the rearranged manuscripts (28 October, user's requirement): does a shuffled text keep the page's
geometry? For every variant of layout_shuffles.py: the words that did not fit their slot and were carried to the next
(or below the page), words left without a box, boxes that overlap another box on the same page (intersection over the
smaller box above 0.2), and the share of words that actually moved. For comparison, the same counts for the manuscript's
recorded rectangles and for the OLD method (words shuffled inside paragraphs but kept in the recorded rectangles of the
slots they land in): there the box width no longer fits the word, measured as the recorded width over the word's own
width at the line's letter size. Renders f75r and f33v for every variant (layout_check_f75r.png, layout_check_f33v.png).
Run from anywhere: python shuffle_layout_check.py > shuffle_layout_check.log
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import data as D  # noqa: E402
import component_check as CC  # noqa: E402
import layout_shuffles as LS  # noqa: E402
from timing import shuffled_within  # noqa: E402

PAGES = ('f75r', 'f33v')


def overlaps(geometry, line_words, ms, threshold=0.2):
    """Pairs of boxes on the same page whose intersection exceeds `threshold` of the smaller box."""
    starts = np.cumsum([0] + [len(ws) for ws in line_words])
    total = 0
    for p in ms['pages']:
        idx = [i for l in range(p['start_line'], p['end_line']) for i in range(starts[l], starts[l + 1]) if geometry[i]]
        if len(idx) < 2:
            continue
        b = np.array([geometry[i] for i in idx], float)
        x0 = np.maximum(b[:, None, 0], b[None, :, 0])
        y0 = np.maximum(b[:, None, 1], b[None, :, 1])
        x1 = np.minimum(b[:, None, 2], b[None, :, 2])
        y1 = np.minimum(b[:, None, 3], b[None, :, 3])
        inter = np.clip(x1 - x0, 0, None) * np.clip(y1 - y0, 0, None)
        area = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
        smaller = np.minimum(area[:, None], area[None, :])
        ratio = np.where(smaller > 0, inter / np.maximum(smaller, 1e-9), 0)
        total += int((np.triu(ratio, 1) > threshold).sum())
    return total


def width_error(ms, frames, line_words, geometry):
    """Recorded box width over the word's width at the line's letter size; returns median |log ratio| and the share off by 1.5x."""
    ratios = []
    i = 0
    for l, ws in enumerate(line_words):
        fr = frames[l]
        cw = sum(b - a for a, b in fr[4]) / max(ms['lines'][l]['chars'], 1) if fr else None
        for w in ws:
            g = geometry[i]
            i += 1
            if g and cw and len(w):
                ratios.append((g[2] - g[0]) / (len(w) * cw))
    r = np.log(np.array(ratios))
    return float(np.median(np.abs(r))), float((np.abs(r) > np.log(1.5)).mean()), len(ratios)


def draw_page(ax, ms, folio, line_words, geometry, frames, title):
    starts = np.cumsum([0] + [len(ws) for ws in line_words])
    p = [q for q in ms['pages'] if q['folio'] == folio][0]
    xs, ys = [], []
    for l in range(p['start_line'], p['end_line']):
        fr = frames[l]
        if fr:
            for a, b in fr[4]:
                ax.plot([a, b], [fr[1], fr[1]], color='#dddddd', linewidth=0.6)
        for i in range(starts[l], starts[l + 1]):
            g = geometry[i]
            if not g:
                continue
            ax.add_patch(Rectangle((g[0], g[1]), g[2] - g[0], g[3] - g[1], facecolor='none', edgecolor='#4477aa', linewidth=0.5))
            ax.text((g[0] + g[2]) / 2, (g[1] + g[3]) / 2, line_words[l][i - starts[l]], ha='center', va='center', fontsize=4.2, color='#222222')
            xs += [g[0], g[2]]
            ys += [g[1], g[3]]
    if xs:
        ax.set_xlim(min(xs) - 20, max(xs) + 20)
        ax.set_ylim(max(ys) + 20, min(ys) - 20)
    ax.set_aspect('equal')
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(title, fontsize=8, loc='left')


def main():
    ms = D.manuscript()
    app = CC.load_study_app('legacy')
    frames = CC.line_frames(app, ms)
    ms_lines = [L['words'] for L in ms['lines']]
    ntok = sum(len(ws) for ws in ms_lines)
    V = LS.variants(ms, frames)
    rows = []
    rec_err = width_error(ms, frames, ms_lines, app['geometry'])
    rows.append(('manuscript (recorded boxes)', 0, sum(1 for g in app['geometry'] if not g), overlaps(app['geometry'], ms_lines, ms), None, rec_err))
    tok = D.tokenize(ms)
    old = shuffled_within(ms, tok, np.cumsum(tok['since_par'] == 0))
    old_err = width_error(ms, frames, old, app['geometry'])
    rows.append(('OLD: words shuffled in paragraphs, recorded boxes kept', 0, sum(1 for g in app['geometry'] if not g), overlaps(app['geometry'], old, ms),
                 sum(a != b for A, B in zip(old, ms_lines) for a, b in zip(A, B)), old_err))
    nlines = len(ms['lines'])
    sizes = {}
    for name, v in V.items():
        lines, geom = v['lines'], v['geometry']
        # a word-level variant moves words (share of tokens); a line-level one moves lines (share of lines)
        moved = None if v['moved'] is None else (v['moved'] / nlines if 'lines shuffled' in name else v['moved'] / ntok)
        rows.append((name, v['carried'], sum(1 for g in geom if not g), overlaps(geom, lines, ms), moved, width_error(ms, frames, lines, geom)))
        if v['cw_ratio'] is not None:
            r = np.log(v['cw_ratio'])
            sizes[name] = (float(np.median(np.abs(r))), float((np.abs(r) > np.log(1.5)).mean()), float((np.abs(r) > np.log(2)).mean()))
    rows[1] = rows[1][:4] + (rows[1][4] / ntok,) + rows[1][5:]
    print(f'{ntok} tokens, {nlines} lines, {len(ms["pages"])} pages. Overlap = pairs of boxes on one page with intersection over the smaller box above 0.2.')
    print('carried = words that did not fit their slot and continued on the next line (or below the page); for the fitted-letter-size variants')
    print('nothing is carried, the slot\'s letter size is scaled to its new line instead (see the letter-size table). moved = share of words')
    print('(word-level variants) or of lines (line-level variants) that changed place.')
    print(f"{'variant':52s} {'carried':>8s} {'no box':>7s} {'overlaps':>9s} {'moved':>7s}  {'box width / word width: median |log|, share off by 1.5x':>58s}")
    for name, carried, nobox, ov, moved, err in rows:
        mv = f'{moved:6.1%}' if moved is not None else '     -'
        print(f'{name:52s} {carried:8d} {nobox:7d} {ov:9d} {mv:>7s}  {err[0]:.3f}, {err[1]:.1%} (of {err[2]} boxed words)')
    print('\nletter size of a slot over the manuscript\'s on that line (fitted variants): median |log|, share beyond 1.5x, beyond 2x')
    for name, (med, s15, s2) in sizes.items():
        print(f'  {name:52s} {med:.3f}, {s15:.1%}, {s2:.1%}')
    json.dump(dict(rows={r[0]: dict(carried=int(r[1]), no_box=int(r[2]), overlaps=int(r[3]), moved=r[4], width_median_abslog=r[5][0], width_off_1p5=r[5][1]) for r in rows},
                   letter_size=sizes), open(HERE / 'shuffle_layout_check.json', 'w', encoding='utf-8'), indent=1)
    panels = [('manuscript (recorded boxes)', ms_lines, app['geometry'])] + [(n, v['lines'], v['geometry']) for n, v in V.items()]
    starts = np.cumsum([0] + [len(ws) for ws in ms_lines])
    for folio in PAGES:
        p = [q for q in ms['pages'] if q['folio'] == folio][0]
        boxes = [app['geometry'][i] for l in range(p['start_line'], p['end_line']) for i in range(starts[l], starts[l + 1]) if app['geometry'][i]]
        w = max(b[2] for b in boxes) - min(b[0] for b in boxes)
        h = max(b[3] for b in boxes) - min(b[1] for b in boxes)
        cols = 2
        rws = int(np.ceil(len(panels) / cols))
        pw = 10.0
        fig, axes = plt.subplots(rws, cols, figsize=(cols * pw, rws * (pw * h / w + 0.5)))
        for ax, (name, lines, geom) in zip(axes.flat, panels):
            draw_page(ax, ms, folio, lines, geom, frames, f'{folio}: {name}')
        for ax in axes.flat[len(panels):]:
            ax.axis('off')
        fig.suptitle(f'{folio}: every rearrangement re-typeset into the recorded line frames (grey: frame segments; blue: word boxes)', fontsize=10)
        fig.tight_layout()
        fig.savefig(HERE / f'layout_check_{folio}.png', dpi=160)
        plt.close(fig)
        print(f'wrote layout_check_{folio}.png')


if __name__ == '__main__':
    main()
