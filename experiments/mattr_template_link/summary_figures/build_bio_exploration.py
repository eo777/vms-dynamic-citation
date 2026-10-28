"""Build static Bio figures from retained aggregate results.

No generation or fitted model run; no player or word-level data.
Run from any directory: python summary_figures/build_bio_exploration.py
"""
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent

INK, TEAL, RUST = '#243231', '#177b79', '#b45c34'
GREY = '#64736c'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11,
                     'text.color': INK, 'axes.labelcolor': GREY,
                     'xtick.color': GREY, 'ytick.color': GREY,
                     'svg.fonttype': 'none', 'axes.spines.top': False,
                     'axes.spines.right': False})


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def finish(fig, stem):
    fig.savefig(HERE / (stem + '.png'), dpi=180, facecolor='white')
    fig.savefig(HERE / (stem + '.svg'), facecolor='white')
    plt.close(fig)


def axes_style(ax):
    ax.set_axisbelow(True)
    ax.grid(axis='y', color='#e2e7e3', linewidth=.8)
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_color('#cbd5ce')
    ax.yaxis.set_major_formatter(PercentFormatter(1, decimals=0))
    ax.tick_params(axis='both', length=0, pad=8)


def figures(depth, page):
    bins = ['1-10', '10-20', '20-40', '40-80', '80-160']
    fig, axs = plt.subplots(1, 2, figsize=(11.8, 4.9), sharey=True)
    fig.subplots_adjust(left=.08, right=.98, top=.77, bottom=.22, wspace=.15)
    fig.text(.08, .95, 'Bio paragraphs start with fewer new words than Stars paragraphs', fontsize=16, weight='bold')
    fig.text(.08, .88, 'New-word rate: percentage absent from the preceding 100 words', fontsize=11, color=GREY)
    for ax, model, title in zip(axs, ['manuscript', 'timm'], ['Manuscript', 'Original Timm · mean of 3 runs']):
        axes_style(ax)
        ax.axvspan(-.18, .18, color='#f2f5f0', zorder=0)
        for group, color, label in [('3c', TEAL, 'Earlier Stars (3c)'), ('4a', RUST, 'Bio (4a)')]:
            values = [depth[model][group][b] for b in bins]
            ax.plot(range(5), values, '-o', color=color, lw=2.5, ms=6, label=label)
            ax.annotate(f'{values[0]:.1%}', (0, values[0]), xytext=(9, 8 if group == '3c' else -20), textcoords='offset points', color=color, weight='bold')
        gap = depth[model]['3c']['1-10'] - depth[model]['4a']['1-10']
        ax.set_title(title, loc='left', fontsize=13, pad=15, color=INK)
        ax.set_xticks(range(5), ['1–9', '10–19', '20–39', '40–79', '80–159'])
        ax.set_xlabel('Words after the paragraph’s first word', labelpad=12)
        ax.set_ylim(.45, .88)
        ax.set_xlim(-.35, 4.25)
        ax.text(.97, .95, f'Opening difference: {gap * 100:.1f} points', transform=ax.transAxes, ha='right', va='top', fontsize=10, color=GREY)
    axs[0].legend(frameon=False, loc='lower left', fontsize=10)
    fig.text(.08, .035, 'Saved paragraph-depth results; group labels follow the study’s Path 1 grouping. The opening token itself is excluded.', fontsize=9, color=GREY)
    finish(fig, 'bio_paragraph_recovery')

    fig, ax = plt.subplots(figsize=(11.8, 4.9))
    fig.subplots_adjust(left=.08, right=.8, top=.77, bottom=.30)
    fig.text(.08, .95, 'Bio’s new-word rate rises at page starts, then falls back', fontsize=16, weight='bold')
    fig.text(.08, .88, 'New-word rate: percentage absent from the preceding 100 words · manuscript', fontsize=11, color=GREY)
    axes_style(ax)
    keys = ['prev_last_50', '0-10', '10-30', '30-60', '60-100', '100-1000000']
    for key, name, color, dy in [('H', 'Herbal', '#738568', 0), ('S', 'Stars', TEAL, 0), ('B', 'Bio', RUST, 0)]:
        vals = [page['manuscript'][key][b] for b in keys]
        ax.plot([0], vals[:1], 'o', color=color, ms=7)
        ax.plot(range(1, 6), vals[1:], '-o', color=color, lw=2.5, ms=6)
        ax.text(5.12, vals[-1], f'{name}  {vals[-1]:.1%}', va='center', color=color, weight='bold')
    ax.axvline(.5, color='#c4cdc6', ls='--')
    ax.text(.53, .87, 'new page', fontsize=10, color=GREY)
    for x, key, offset in [(0, keys[0], (0, -22)), (1, keys[1], (0, 12)), (4, keys[4], (0, -22))]:
        val = page['manuscript']['B'][key]
        ax.annotate(f'{val:.1%}', (x, val), xytext=offset, textcoords='offset points', ha='center', color=RUST, weight='bold')
    ax.set_xticks(range(6), ['Page ends\nlast 50', '1–9', '10–29', '30–59', '60–99', '100+'])
    ax.set_xlabel('Words after the new page’s first word', labelpad=12)
    ax.set_ylim(.48, .9)
    ax.set_xlim(-.3, 5.1)
    fig.text(.08, .07, 'Illustration sections: Herbal 128 pages · Stars 25 · Bio 19. First word excluded; word-weighted bin means.', fontsize=9, color=GREY)
    fig.text(.08, .025, 'Page ends are a separate section-wide reference, not paired estimates for the immediately preceding page.', fontsize=9, color=GREY)
    finish(fig, 'bio_page_recovery')

def main():
    depth = read(STUDY / 'shuffle_check.json')['depth_rates']
    page = read(STUDY / 'pagestart.json')['page_start']
    figures(depth, page)
    payload = {'sources': {name: hashlib.sha256((STUDY / name).read_bytes()).hexdigest()
                           for name in ['shuffle_check.json', 'pagestart.json']}}
    payload['aggregates'] = {'depth': {k: depth[k] for k in ['manuscript', 'timm']},
                             'page': {k: page[k] for k in ['manuscript', 'timm']}}
    (HERE / 'bio_exploration.json').write_text(json.dumps(payload, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print('Built 2 static Bio figures from saved aggregate results.')


if __name__ == '__main__':
    main()
