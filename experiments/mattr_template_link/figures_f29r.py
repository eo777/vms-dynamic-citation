"""f29r_layout.png: the page the user checked the layouts on (27 October). Left: the manuscript's recorded word rectangles
(the app's data), with the plant's stem running down the text as a white column. Middle: the spatial Timm run laid into
the page under the isolated-gap rule alone (a gap counts as a drawing only when wider than twice the page's median word
width), which wrote across the stem on lines 3 to 8. Right: the same text under the current rule, which also splits at
vertical gaps shared by neighbouring lines (page_geometry.vertical_gaps); the stem is left empty. Every synthetic layout
of the study and the generator's own view of the page use the right-hand rule."""
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import data as D
import component_check as CC
import page_geometry as PG

FOLIO = 'f29r'
INK, SEC, GRID = '#1f1f1d', '#5a5955', '#e6e5e1'
C_MS, C_GEN, C_GAP = '#8a8984', '#2a78d6', '#e0453a'


def boxes_of(ms, app, p):
    return [(app['geometry'][i], ms['lines'][l]['locus']) for l in range(p['start_line'], p['end_line']) for i in range(app['lines'][l]['start'], app['lines'][l]['end']) if app['geometry'][i]]


def draw(ax, boxes, color, title, gaps=None, frames=None, ms=None, p=None):
    for b, _ in boxes:
        ax.add_patch(Rectangle((b[0], b[1]), b[2] - b[0], b[3] - b[1], facecolor=color, alpha=0.55, edgecolor=color, linewidth=0.6))
    if gaps and frames:
        for l in range(p['start_line'], p['end_line']):
            fr = frames[l]
            for x0, x1 in gaps.get(l, []):
                ax.add_patch(Rectangle((x0, fr[1]), x1 - x0, fr[3] - fr[1], facecolor=C_GAP, alpha=0.18, edgecolor='none'))
    ax.set_title(title, loc='left', fontsize=8.2, color=INK)
    ax.set_aspect('equal')
    for s in ax.spines.values():
        s.set_color(GRID)
    ax.tick_params(labelsize=6.5, colors=SEC)


def main():
    ms = D.manuscript()
    app = CC.app_words() if hasattr(CC, 'app_words') else PG.app_words()
    p = next(q for q in ms['pages'] if q['folio'] == FOLIO)
    rec = boxes_of(ms, app, p)
    flags = PG.oversized_flags(app, ms)
    gaps = PG.vertical_gaps(app, ms, flags)
    frames_now = CC.line_frames(app, ms)
    saved = PG.vertical_gaps
    PG.vertical_gaps = lambda *a, **k: {}           # the rule before 27 October: isolated gaps only
    frames_old = PG.line_frames(app, ms)
    PG.vertical_gaps = saved
    stream = D.read_stream(D.STREAMS['timm_spatial'][1][0])
    lines_old = [list(l) for l in stream]
    geom_old = CC.synthetic_geometry(lines_old, frames_old, ms)
    lines_new = [list(l) for l in stream]
    geom_new = CC.synthetic_geometry(lines_new, frames_now, ms)

    def page_boxes(lines, geom):
        out = []
        k = 0
        for l, ws in enumerate(lines):
            for _ in ws:
                if p['start_line'] <= l < p['end_line'] and geom[k] is not None:
                    out.append((geom[k], ms['lines'][l]['locus']))
                k += 1
        return out
    xs = [b[0] for b, _ in rec] + [b[2] for b, _ in rec]
    ys = [b[1] for b, _ in rec] + [b[3] for b, _ in rec]
    plt.rcParams['font.family'] = 'DejaVu Sans'
    fig, axes = plt.subplots(1, 3, figsize=(12.6, 3.6), facecolor='white')
    draw(axes[0], rec, C_MS, f'{FOLIO}: recorded word rectangles (the app\'s data)')
    draw(axes[1], page_boxes(lines_old, geom_old), C_GEN, 'spatial Timm run, isolated-gap rule only (before)')
    draw(axes[2], page_boxes(lines_new, geom_new), C_GEN, 'spatial Timm run, with the vertical-gap rule (now)', gaps, frames_now, ms, p)
    for ax in axes:
        ax.set_xlim(min(xs) - 15, max(xs) + 15)
        ax.set_ylim(max(ys) + 15, min(ys) - 15)
    fig.text(0.01, 0.015, 'Red band: the vertical gap found by the rule (gaps wider than half the page\'s median word width that overlap on neighbouring lines). '
                          'Words that do not fit a line\'s segments carry over to the next line, as in every synthetic layout of this study.', fontsize=7, color=SEC)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(HERE / 'f29r_layout.png', dpi=150, facecolor='white')
    # the stem column: x 531-629 between the top of line 3 and the bottom of line 8 (recorded frames); boxes in the page's
    # overflow row below its lowest line are counted apart
    cut = [l for l in range(p['start_line'], p['end_line']) if l in gaps]
    y0, y1 = min(frames_now[l][1] for l in cut), max(frames_now[l][3] for l in cut)
    x0, x1 = min(a for l in cut for a, _ in gaps[l]), max(b for l in cut for _, b in gaps[l])
    bottom = max(frames_now[l][3] for l in range(p['start_line'], p['end_line']) if frames_now[l])

    centres = {l: (frames_now[l][1] + frames_now[l][3]) / 2 for l in range(p['start_line'], p['end_line']) if frames_now[l]}

    def crossing(bx):
        """Boxes that overlap the stem gap of the line they sit on (the line whose recorded centre is nearest the box)."""
        inside = 0
        for b, _ in bx:
            cy = (b[1] + b[3]) / 2
            if cy >= bottom:
                continue
            l = min(centres, key=lambda k: abs(centres[k] - cy))
            if any(b[0] < g1 - 1e-6 and b[2] > g0 + 1e-6 for g0, g1 in gaps.get(l, [])):
                inside += 1
        below = sum(1 for b, _ in bx if b[1] >= bottom)
        return inside, below
    (c_old, o_old), (c_new, o_new) = crossing(page_boxes(lines_old, geom_old)), crossing(page_boxes(lines_new, geom_new))
    print(f'{FOLIO}: synthetic boxes inside the stem column (x {x0:.0f}-{x1:.0f}, lines {ms["lines"][cut[0]]["locus"]}-{ms["lines"][cut[-1]]["locus"]}): '
          f'before {c_old}, now {c_new}; boxes in the overflow row below the page: before {o_old}, now {o_new}; wrote f29r_layout.png')


if __name__ == '__main__':
    main()
