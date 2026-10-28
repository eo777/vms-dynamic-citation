"""Heatmap-style page renderings for section 8: one manuscript page (f78r, Bio) as laid out by each text, every word
box coloured by its source component score (the component-impact study's measure: effective number of glyph-unit
pair types among the words in view; letter pairs for the natural text). Two colour domains (Voynich units; letters),
each the 5th to 95th percentile of log2 score over its three panels, on the dataviz reference sequential blue ramp.
Boxes with no valid score are outlined in grey; oversized recorded rectangles (wider than 6 or taller than 2.5 times
the page median, a geometry defect of the source data, 21 and 188 boxes manuscript-wide) are drawn as dashed
outlines so the page stays legible."""
import gzip
import json
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.patches import Rectangle
import numpy as np

sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
import data as D
import component_check as CC
import layout_controls as LC
import native_layout as NL
from decompose import REFS, ref_words
from timing import laid_in
from figures import INK, SEC, MUTED, GRID, SURF

PAGE = 'f78r'
RAMP = ['#cde2fb', '#b7d3f6', '#9ec5f4', '#86b6ef', '#6da7ec', '#5598e7', '#3987e5', '#2a78d6', '#256abf', '#1c5cab', '#184f95', '#104281', '#0d366b']
CMAP = LinearSegmentedColormap.from_list('blue_seq', RAMP)


def main():
    ms = D.manuscript()
    app = CC.load_study_app('legacy')
    frames = CC.line_frames(app, ms)
    flags = CC.oversized_flags(app, ms)
    clean = [None if flags[i] else g for i, g in enumerate(app['geometry'])]
    page_sizes = [sum(len(ms['lines'][l]['words']) for l in range(p['start_line'], p['end_line'])) for p in ms['pages']]
    pidx = next(p['index'] for p in ms['pages'] if p['folio'] == PAGE)
    LC.rng = np.random.default_rng(78)
    NL.rng = np.random.default_rng(78)
    ms_lines = [L['words'] for L in ms['lines']]
    far0 = D.read_stream(D.STREAMS['far0'][1][0])
    gart_words = ref_words(REFS['de_gart_augsburg1487'])
    gart_box = laid_in(ms, gart_words, page_sizes)
    gart_line = LC.fill_by_chars(ms, gart_words)
    gart_native, gart_native_geom, start = NL.native_layout(ms, app, NL.native_lines(NL.GART))
    letters = lambda w: list(w)
    panels = [('Manuscript', 'recorded word boxes', ms_lines, app['geometry'], CC.zattera, 'v'),
              ('Far 0, page-window copier', 'boxes by character position', far0, CC.synthetic_geometry(far0, frames, ms), CC.zattera, 'v'),
              ('Word-bigram chain of the whole manuscript', 'generated without the layout, laid into the manuscript boxes', LC.bigram_whole(ms), clean, CC.zattera, 'v'),
              ('Gart der Gesundheit 1487', 'one word per manuscript box', gart_box, app['geometry'], letters, 'l'),
              ('Gart 1487', "filled to each line's character budget, boxes by position", gart_line, CC.synthetic_geometry(gart_line, frames, ms), letters, 'l'),
              ('Gart 1487', 'its own printed lines, one per manuscript line', gart_native, gart_native_geom, letters, 'l')]
    data = []
    for name, sub, lines, geom, comp, kind in panels:
        inp = CC.make_input(ms, lines, geom, comp)
        meas = CC.measure(inp)
        page_of = np.concatenate([[L['page']] * len(ws) for L, ws in zip(ms['lines'], lines)])
        idx = np.where(page_of == pidx)[0]
        words = [inp['words'][i] for i in idx]
        boxes = [inp['geometry'][i] for i in idx]
        data.append(dict(name=name, sub=sub, kind=kind, words=words, boxes=boxes, score=meas['components'][idx], mattr=D.mattr(words), n=len(words)))
    norms = {}
    for kind in ('v', 'l'):
        v = np.log2(np.concatenate([d['score'][np.isfinite(d['score'])] for d in data if d['kind'] == kind]))
        lo, hi = np.percentile(v, [5, 95])
        norms[kind] = Normalize(vmin=lo, vmax=hi, clip=True)
    mb = [b for b in data[0]['boxes'] if b]
    medw = np.median([b[2] - b[0] for b in mb])
    medh = np.median([b[3] - b[1] for b in mb])
    ok = [b for b in mb if b[2] - b[0] <= 6 * medw and b[3] - b[1] <= 2.5 * medh]
    x0 = min(b[0] for b in ok) - 20
    x1 = max(b[2] for b in ok) + 20
    y0 = min(b[1] for b in ok) - 20
    y1 = max(b[3] for b in ok) + 20

    fig, axes = plt.subplots(2, 3, figsize=(17, 13))
    for ax, d in zip(axes.ravel(), data):
        norm = norms[d['kind']]
        for w, b, s in zip(d['words'], d['boxes'], d['score']):
            if not b:
                continue
            oversized = (b[2] - b[0] > 6 * medw) or (b[3] - b[1] > 2.5 * medh)
            if oversized:
                ax.add_patch(Rectangle((b[0], b[1]), b[2] - b[0], b[3] - b[1], facecolor='none', edgecolor=MUTED, linewidth=0.7, linestyle=(0, (3, 2))))
                ax.text(b[2] - 4, b[3] - 6, f'{w}: oversized recorded box (dashed)', fontsize=5, color=SEC, va='bottom', ha='right')
                continue
            if np.isfinite(s):
                face = CMAP(norm(np.log2(s)))
                ax.add_patch(Rectangle((b[0], b[1]), b[2] - b[0], b[3] - b[1], facecolor=face, edgecolor=SURF, linewidth=0.6))
                dark = norm(np.log2(s)) > 0.55
            else:
                ax.add_patch(Rectangle((b[0], b[1]), b[2] - b[0], b[3] - b[1], facecolor='none', edgecolor=MUTED, linewidth=0.6))
                dark = False
            ax.text((b[0] + b[2]) / 2, (b[1] + b[3]) / 2, w, ha='center', va='center', fontsize=4.2, color=SURF if dark else INK, clip_on=True)
        ax.set_xlim(x0, x1)
        ax.set_ylim(y1, y0)
        ax.set_aspect('equal')
        ax.set_xticks([])
        ax.set_yticks([])
        for sp in ax.spines.values():
            sp.set_edgecolor(GRID)
        valid = d['score'][np.isfinite(d['score'])]
        ax.set_title(f"{d['name']}\n{d['sub']}\n{d['n']} words · MATTR100 {d['mattr']:.3f} · mean score {np.mean(valid):.1f}", loc='left', fontsize=9.5, color=INK)
    fig.suptitle(f'Page {PAGE} (Bio, group 4a) under each layout; every word box coloured by the source component score of the words in view above and to the left of it',
                 x=0.02, ha='left', fontsize=12, color=INK)
    for k, (kind, label, left) in enumerate((('v', 'Voynich texts: effective number of glyph-unit pair types among the words in view', 0.08),
                                             ('l', 'Gart 1487: effective number of letter-pair types among the words in view', 0.56))):
        cax = fig.add_axes([left, 0.045, 0.36, 0.013])
        sm = plt.cm.ScalarMappable(norm=norms[kind], cmap=CMAP)
        cb = fig.colorbar(sm, cax=cax, orientation='horizontal')
        ticks = np.linspace(norms[kind].vmin, norms[kind].vmax, 5)
        cb.set_ticks(ticks)
        cb.set_ticklabels([f'{2 ** t:.0f}' for t in ticks])
        cb.outline.set_edgecolor(GRID)
        cb.set_label(label + ' (5th to 95th percentile; grey outline: no valid score)', fontsize=8.5, color=SEC)
    fig.subplots_adjust(left=0.02, right=0.98, top=0.88, bottom=0.1, wspace=0.08, hspace=0.26)
    fig.savefig(D.HERE / 'page_examples.png', dpi=170)
    fig.savefig(D.HERE / 'page_examples.svg')
    plt.close(fig)
    print('wrote page_examples.png / .svg; native start line', start)


if __name__ == '__main__':
    main()
