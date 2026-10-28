"""Static diversity profiles across the four pages of individual bifolia.

Uses retained manuscript words. No ordering between bifolia is assumed.
"""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
sys.path.insert(0, str(STUDY))
import data as D

INK, BIO, STARS, MUTED = '#243231', '#ad5b32', '#177b79', '#607169'
PAIRS = {'Bio': [(75, 84), (76, 83), (77, 82), (78, 81), (79, 80)],
         'Stars': [(103, 116), (104, 115), (105, 114), (106, 113), (107, 112), (108, 111)]}
X = np.array([0, .7, 1.7, 2.4, 3.4, 4.1, 5.1, 5.8])


def extract(lines=None, ms=None, allow_overlap=False):
    ms = D.manuscript() if ms is None else ms
    lines = [line['words'] for line in ms['lines']] if lines is None else lines
    assert len(lines) == len(ms['lines'])
    words = defaultdict(list)
    for line, text in zip(ms['lines'], lines):
        words[line['folio']].extend(text)
    result = {}
    for section, pairs in PAIRS.items():
        result[section] = []
        for a, b in pairs:
            folios = [f'f{leaf}{side}' for leaf in (a, b) for side in ('r', 'v')]
            profile, page_rows = [], []
            for folio in folios:
                w = words[folio]
                if not w:
                    profile.extend([None, None])
                    page_rows.append({'folio': folio, 'words': 0, 'first100': None, 'last100': None})
                    continue
                assert len(w) >= 100
                if not allow_overlap:
                    assert len(w) >= 200  # manuscript endpoint samples do not overlap
                start, end = len(set(w[:100])), len(set(w[-100:]))
                curve = D.trailing_distinct(w)
                assert abs(curve[99] * 100 - start) < 1e-10
                assert abs(curve[-1] * 100 - end) < 1e-10
                profile.extend([start, end])
                page_rows.append({'folio': folio, 'words': len(w), 'first100': start, 'last100': end,
                                  'mattr100': D.mattr(w), 'samples_overlap': len(w) < 200})
            result[section].append({'bifolium': f'{a}|{b}', 'pages': page_rows, 'profile': profile,
                                    'complete': all(x is not None for x in profile)})
    return result


def stats(rows):
    complete = [r for r in rows if r['complete']]
    values = np.array([r['profile'] for r in complete], dtype=float)
    changes = values[:, [2, 4, 6]] - values[:, [1, 3, 5]]
    return {'complete_bifolia': len(complete), 'mean_profile': values.mean(axis=0).tolist(),
            'boundary_change_mean_distinct_forms': float(changes.mean()),
            'rising_boundaries': int((changes > 0).sum()), 'boundaries': int(changes.size),
            'first_to_last_change': float(np.mean(values[:, -1] - values[:, 0]))}


def base(ax, small=False):
    for page in [0, 2]:
        ax.axvspan(X[page*2]-.2, X[page*2+1]+.2, color='#f0f3ec', zorder=0)
    ax.set_ylim(40, 100)
    ax.set_xlim(-.25, 6.05)
    ax.set_yticks([40, 50, 60, 70, 80, 90, 100])
    ax.grid(axis='y', color='#dce4de', lw=.65)
    ax.set_axisbelow(True)
    ax.tick_params(axis='both', length=0, pad=6, colors=MUTED, labelsize=8 if small else 10)
    for edge in ['left', 'top', 'right']:
        ax.spines[edge].set_visible(False)
    ax.spines['bottom'].set_color('#cad5cc')


def profile(ax, values, color, alpha=1, lw=2, markers=True):
    values = np.array([np.nan if v is None else v for v in values], dtype=float)
    for p in range(4):
        a, b = p*2, p*2+2
        ax.plot(X[a:b], values[a:b], color=color, alpha=alpha, lw=lw)
        if markers:
            ax.plot(X[a], values[a], 'o', color=color, mfc='white', ms=5, mew=1.3, zorder=5)
            ax.plot(X[a+1], values[a+1], 'o', color=color, ms=4.5, zorder=5)
        if p:
            ax.plot(X[a-1:a+1], values[a-1:a+1], color=color, alpha=alpha, lw=lw, ls=':')


def save(fig, name):
    fig.savefig(HERE / f'{name}.png', dpi=180, facecolor='white')
    fig.savefig(HERE / f'{name}.svg', facecolor='white')
    plt.close(fig)


def average_chart(data, summary):
    fig, axes = plt.subplots(1, 2, figsize=(12.8, 5.5), sharey=True)
    fig.subplots_adjust(left=.075, right=.975, top=.74, bottom=.27, wspace=.12)
    fig.text(.075, .95, 'Does word diversity recover between the four pages of a bifolium?', fontsize=16, weight='bold', color=INK)
    fig.text(.075, .88, 'Distinct word forms in the first and last 100 words of each page', fontsize=11, color=MUTED)
    for ax, section, color in zip(axes, ['Bio', 'Stars'], [BIO, STARS]):
        base(ax)
        for row in data[section]:
            if row['complete']:
                profile(ax, row['profile'], color, alpha=.18, lw=1, markers=False)
        profile(ax, summary[section]['mean_profile'], color, lw=2.7)
        ax.set_title(f'{section} · average of 5 bifolia', loc='left', fontsize=13, weight='bold', color=color, pad=13)
        ax.set_xticks(X, ['Start', 'End'] * 4, fontsize=9)
        for p in range(4):
            ax.text((X[p*2]+X[p*2+1])/2, -.18, f'Page {p+1}', transform=ax.get_xaxis_transform(), ha='center', color=INK, fontsize=10)
        r = summary[section]
        ax.text(.02, .03, f"Mean change at a new page: {r['boundary_change_mean_distinct_forms']:+.1f} distinct forms",
                transform=ax.transAxes, fontsize=10, color=color)
    axes[0].set_ylabel('Distinct word forms / 100 words', color=MUTED, fontsize=10)
    fig.legend(handles=[Line2D([], [], color=MUTED, marker='o', mfc='white', ls='none', label='First 100 words'),
                        Line2D([], [], color=MUTED, marker='o', ls='none', label='Last 100 words'),
                        Line2D([], [], color=MUTED, ls=':', label='Change to the next page')],
               loc='lower center', bbox_to_anchor=(.51, .095), ncol=3, frameon=False, fontsize=9)
    fig.text(.075, .055, 'Bold lines: equal-weight averages. Faint lines: individual bifolia. Page order within each: first leaf r/v, second leaf r/v.', fontsize=9, color=MUTED)
    fig.text(.075, .018, 'Stars 103|116 is shown separately below but excluded from the average because f116v has no study text.', fontsize=9, color=MUTED)
    save(fig, 'bio_within_bifolium')


def individual_chart(data):
    fig, axes = plt.subplots(2, 6, figsize=(14.5, 7.0), sharey=True)
    fig.subplots_adjust(left=.055, right=.985, top=.79, bottom=.18, hspace=.63, wspace=.16)
    fig.text(.055, .955, 'Word diversity across each bifolium’s four pages', fontsize=19, weight='bold', color=INK)
    fig.text(.055, .90, 'Each panel is a separate bifolium; circles show the first and last 100 words of each page.', fontsize=11, color=MUTED)
    for row_index, (section, color) in enumerate([('Bio', BIO), ('Stars', STARS)]):
        for ax, row in zip(axes[row_index], data[section]):
            base(ax, small=True)
            profile(ax, row['profile'], color, lw=1.7)
            ax.set_title(f"{section} · {row['bifolium']}", loc='left', fontsize=10, weight='bold', color=color, pad=10)
            ax.set_xticks([(X[p*2]+X[p*2+1])/2 for p in range(4)], [p['folio'] for p in row['pages']], rotation=50, ha='right', fontsize=8)
            if not row['complete']:
                ax.text(5.45, 57, 'No study\ntext', ha='center', fontsize=7, color=MUTED)
        axes[row_index, 0].set_ylabel('Distinct forms / 100 words', fontsize=9, color=MUTED)
    key = axes[0, 5]
    key.axis('off')
    key.text(.05, .9, 'How to read a page', fontsize=11, weight='bold', color=INK, transform=key.transAxes)
    key.plot([.13, .72], [.60, .45], color=MUTED, lw=2, transform=key.transAxes)
    key.plot(.13, .60, 'o', color=MUTED, mfc='white', ms=6, transform=key.transAxes)
    key.plot(.72, .45, 'o', color=MUTED, ms=5, transform=key.transAxes)
    key.text(.02, .70, 'First 100', fontsize=9, color=MUTED, transform=key.transAxes)
    key.text(.55, .27, 'Last 100', fontsize=9, color=MUTED, transform=key.transAxes)
    key.text(.05, .05, 'Dotted: next page', fontsize=9, color=MUTED, transform=key.transAxes)
    fig.text(.055, .075, 'Order within each bifolium: first leaf recto, first leaf verso, second leaf recto, second leaf verso.', fontsize=10, color=MUTED)
    fig.text(.055, .035, 'All five Bio bifolia and all six Stars bifolia are shown. f116v has no paragraph text in the study transcription.', fontsize=9, color=MUTED)
    save(fig, 'bio_individual_bifolia')


def main():
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'svg.fonttype': 'none'})
    data = extract()
    summary = {s: stats(rows) for s, rows in data.items()}
    assert summary['Bio']['complete_bifolia'] == summary['Stars']['complete_bifolia'] == 5
    average_chart(data, summary)
    individual_chart(data)
    payload = {'metric': 'Number of distinct forms in each page’s first and last 100 words.',
               'page_order': 'First leaf recto, first leaf verso, second leaf recto, second leaf verso.',
               'mean_method': 'Equal weight for each complete four-page bifolium; no transitions between bifolia.',
               'source_sha256': hashlib.sha256(D.TOKENS.read_bytes()).hexdigest(),
               'bifolia': data, 'summary': summary,
               'validation': {'scored_pages': 43, 'endpoint_counts_verified': True, 'endpoint_windows_do_not_overlap': True}}
    (HERE / 'bio_within_bifolium.json').write_text(json.dumps(payload, indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
