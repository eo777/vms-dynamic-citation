"""Static graphic for two pages, f75r (Bio, bifolium M:75-84) and f116r (Stars, bifolium T:103-116), across every text
version, coloured by the glyph H2 and by the component diversity of the words in view with the app's palette on its dark
surface. One colour range per measure, shared by all columns (the union of the 5th-95th percentile ranges over the
Voynichese and the German texts), so a colour means the same thing in every panel of a row. H2 is in bits and component
diversity an effective number of unit pairs, over Zattera units for the Voynichese columns and over letters for Gart 1487;
the German panels are therefore read for their within-page pattern, not against the Voynichese columns' level.
Data from compare_data.json.gz (compare_site.py), scores by the app's own selector."""
import gzip
import json
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, Normalize
from matplotlib.patches import Rectangle
import numpy as np

sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
import data as D

PAGES = ('f75r', 'f116r')
MEAS = (('h2', 'glyph H2', 'Glyph H2 of the words in view, bits (Zattera units for the Voynichese columns, letters for Gart 1487)'),
        ('components', 'component diversity', 'Component diversity of the words in view, effective unit pairs (Zattera pairs for the Voynichese columns, letter pairs for Gart 1487)'))
DARK, INKL, SECL, GRIDL = '#141413', '#f0efec', '#c3c2b7', '#3a3936'
SHORT = {'manuscript': 'Manuscript', 'timm': 'Original Timm\n(self-citation)', 'noinnov_far0': 'Far 0, no innovator\n(page-window copier)',
         'timm_spatial': 'Original Timm,\nsources in view', 'noinnov_spatial': 'Far 0, no innovator,\nsources in view', 'far0_spatial': 'Far 0 with innovator,\nsources in view',
         'bigram_whole': 'Markov chain,\nwhole manuscript', 'bigram_currier': 'Markov chains,\nCurrier A / B', 'bigram_section': 'Markov chains,\nby section',
         'gart_own_lines': 'Gart 1487,\nown lines', 'gart_character_budget': 'Gart 1487,\nbudget fill', 'gart_one_word_per_box': 'Gart 1487,\none per box'}


def main():
    data = json.loads(gzip.decompress((D.HERE / 'heatmap_variants/compare_data.json.gz').read_bytes()).decode('utf8'))
    pal = ListedColormap(data['palette'])
    V = [v for v in data['variants'] if v['key'] != 'manuscript_clean']
    cells = [(p, mm) for p in PAGES for mm in MEAS]            # rows: f75r H2, f75r components, f116r H2, f116r components
    fig, axes = plt.subplots(len(cells), len(V), figsize=(1.3 * len(V) + 1.5, 1.78 * len(cells) + 1.05), facecolor=DARK)
    plt.rcParams['font.family'] = 'DejaVu Sans'
    dom = data['shared_domains']
    norms = {m: Normalize(min(dom['v'][m][0], dom['l'][m][0]), max(dom['v'][m][1], dom['l'][m][1])) for m, _, _ in MEAS}
    for r, (folio, (m, mshort, _)) in enumerate(cells):
        for c, v in enumerate(V):
            ax = axes[r, c]
            ax.set_facecolor(DARK)
            pf = data['pages'][folio]
            x0, y0, w, h = [float(t) for t in pf['viewBox'].split()]
            ax.set_xlim(x0, x0 + w)
            ax.set_ylim(y0 + h, y0)
            ax.set_aspect('equal')
            ax.set_xticks([])
            ax.set_yticks([])
            for sp in ax.spines.values():
                sp.set_edgecolor(GRIDL)
            pg = v['pages'].get(folio)
            vals = []
            if pg:
                norm = norms[m]
                for (bx, by, bw, bh), val in zip(pg['boxes'], pg[m]):
                    if val is None:
                        ax.add_patch(Rectangle((bx, by), bw, bh, facecolor='none', edgecolor=GRIDL, linewidth=0.5))
                    else:
                        ax.add_patch(Rectangle((bx, by), bw, bh, facecolor=pal(norm(val)), edgecolor='none'))
                        vals.append(val)
            if r == 0:
                ax.set_title(SHORT.get(v['key'], v['key']), fontsize=7.2, color=INKL)
            ax.text(0.03, 0.02, (f"mean {np.mean(vals):.1f}" if m == 'components' else f"mean {np.mean(vals):.2f}") if vals else 'no boxes',
                    transform=ax.transAxes, fontsize=6.5, color=SECL, va='bottom')
        axes[r, 0].set_ylabel(f"{folio}\n{mshort}", fontsize=8, color=INKL, rotation=0, ha='right', va='center', labelpad=8)
    fig.suptitle('f75r (Bio) and f116r (Stars) under every text version, coloured by the score of the words in view (app selector and palette)',
                 x=0.02, ha='left', fontsize=8.5, color=INKL)
    for k, (m, _, mlabel) in enumerate(MEAS):
        cax = fig.add_axes([0.11 + k * 0.46, 0.065, 0.36, 0.012])
        sm = plt.cm.ScalarMappable(norm=norms[m], cmap=pal)
        cb = fig.colorbar(sm, cax=cax, orientation='horizontal')
        cb.ax.tick_params(labelsize=6.5, colors=SECL, length=2)
        cb.outline.set_edgecolor(GRIDL)
        cb.set_label(mlabel, fontsize=6.6, color=SECL, labelpad=2)
    fig.subplots_adjust(left=0.1, right=0.995, top=0.9, bottom=0.12, wspace=0.06, hspace=0.1)
    fig.savefig(D.HERE / 'pages_f75r_f116r.png', dpi=120, facecolor=DARK)
    fig.savefig(D.HERE / 'pages_f75r_f116r.svg', facecolor=DARK)
    plt.close(fig)
    print('wrote pages_f75r_f116r.png / .svg')


if __name__ == '__main__':
    main()
