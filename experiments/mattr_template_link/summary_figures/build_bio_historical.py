"""Historical-text comparisons for individual bifolia, matching retained reflows.

Recreates deterministic text placement only, verifies against the saved study,
and retains compact endpoint counts. No model or spatial calculation is run.
"""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
sys.path.insert(0, str(STUDY))
import data as D
import layout_controls as LC
import timing as T
from decompose import REFS, ref_words
import build_bio_bifolium as B
from build_mattr_swings import TEXTS

BOX, BUDGET = '#286db1', '#9960a6'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def controls(ms):
    saved = json.loads((STUDY / 'layout_controls.json').read_text(encoding='utf-8'))
    T.rng = np.random.default_rng(5)
    LC.rng = np.random.default_rng(20261027)
    sizes = [sum(len(ms['lines'][i]['words']) for i in range(p['start_line'], p['end_line'])) for p in ms['pages']]
    output = {}
    assert [key for key, _ in TEXTS] == list(LC.PROSE)
    for key, title in TEXTS:
        words = ref_words(REFS[key])
        assert len(words) >= sum(sizes) + 10
        variants = [('box', T.laid_in(ms, words, sizes)), ('line', LC.fill_by_chars(ms, words))]
        item = {'title': title, 'source_sha256': digest(REFS[key]), 'reflows': {}}
        for mode, lines in variants:
            groups, nodes = defaultdict(list), defaultdict(list)
            for row, ws in zip(ms['lines'], lines):
                groups[row['group']].extend(ws)
                nodes[row['node']].extend(ws)
            gold = saved[f'prose_{mode}_{key}'][0]['route']
            errors = [abs(D.mattr(ws) - gold['groups'][g]['mattr100']) for g, ws in groups.items()]
            errors += [abs(D.mattr(ws) - gold['nodes'][g]['mattr100']) for g, ws in nodes.items()]
            assert max(errors) < 1e-12, (key, mode, max(errors))
            data = B.extract(lines=lines, ms=ms, allow_overlap=True)
            overlap = {p['folio']: p['words'] for rows in data.values() for r in rows for p in r['pages'] if p.get('samples_overlap')}
            item['reflows'][mode] = {
                'bifolia': data,
                'summary': {s: B.stats(rows) for s, rows in data.items()},
                'overlapping_samples': overlap,
                'verification': {'route_estimates_checked': len(errors), 'max_absolute_error': max(errors)},
                'placed_text_sha256': hashlib.sha256(json.dumps(lines, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest(),
            }
        output[key] = item
    return output


def chart(key, control, manuscript, ymin):
    fig, axes = plt.subplots(2, 6, figsize=(14.5, 7.4), sharey=True)
    fig.subplots_adjust(left=.055, right=.985, top=.79, bottom=.20, hspace=.63, wspace=.16)
    fig.text(.055, .955, control['title'] + ' in the manuscript’s page layouts', fontsize=17, weight='bold', color=B.INK)
    fig.text(.055, .90, 'Distinct forms in the first and last 100 words of each page · manuscript shown in black', fontsize=11, color=B.MUTED)
    overlapping = control['reflows']['line']['overlapping_samples']
    for row_index, (section, color) in enumerate([('Bio', B.BIO), ('Stars', B.STARS)]):
        for index, (ax, row) in enumerate(zip(axes[row_index], manuscript[section])):
            B.base(ax, small=True)
            ax.set_ylim(ymin, 100)
            ax.set_yticks(np.arange(ymin, 101, 10))
            B.profile(ax, row['profile'], B.INK, alpha=.8, lw=1.5)
            for mode, hue in [('box', BOX), ('line', BUDGET)]:
                comparison = control['reflows'][mode]['bifolia'][section][index]
                assert comparison['bifolium'] == row['bifolium']
                B.profile(ax, comparison['profile'], hue, lw=1.5)
            ax.set_title(f"{section} · {row['bifolium']}", loc='left', fontsize=10, weight='bold', color=color, pad=10)
            ax.set_xticks([(B.X[p*2]+B.X[p*2+1])/2 for p in range(4)],
                          [p['folio'] + ('*' if p['folio'] in overlapping else '') for p in row['pages']],
                          rotation=50, ha='right', fontsize=8)
            if not row['complete']:
                ax.text(5.45, ymin+7, 'No study\ntext', ha='center', fontsize=7, color=B.MUTED)
        axes[row_index, 0].set_ylabel('Distinct forms / 100 words', fontsize=9, color=B.MUTED)
    legend = axes[0, 5]
    legend.axis('off')
    legend.text(.02, .96, 'Text / placement', fontsize=11, weight='bold', color=B.INK, transform=legend.transAxes)
    for y, label, color in [(.79, 'Manuscript', B.INK), (.63, 'Historical: one word\nper manuscript box', BOX),
                             (.39, 'Historical: fill line’s\ncharacter budget', BUDGET)]:
        legend.plot([.02, .20], [y, y], color=color, lw=2, transform=legend.transAxes)
        legend.text(.25, y, label, va='center', fontsize=9, color=color, transform=legend.transAxes)
    legend.text(.02, .14, '○ First 100   ● Last 100', fontsize=9, color=B.MUTED, transform=legend.transAxes)
    legend.text(.02, .02, 'Dotted: next page', fontsize=9, color=B.MUTED, transform=legend.transAxes)
    fig.text(.055, .10, 'The same historical sequences and reflows as the earlier MATTR comparisons; each text retains its own word order.', fontsize=9, color=B.MUTED)
    fig.text(.055, .065, 'Each panel is one bifolium. Page order: first leaf r/v, second leaf r/v. Solid: within page; dotted: next page.', fontsize=9, color=B.MUTED)
    note = ('* First/last 100-word samples overlap in the character-budget control on ' +
            ', '.join(f'{folio} ({n} words)' for folio, n in overlapping.items()) + '.') if overlapping else 'First/last 100-word samples do not overlap on any scored page.'
    fig.text(.055, .03, note + ' f116v has no assigned text.', fontsize=9, color=B.MUTED)
    B.save(fig, 'bio_historical_' + key)


def main():
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'svg.fonttype': 'none'})
    ms = D.manuscript()
    manuscript = B.extract(ms=ms)
    data = controls(ms)
    minimum = min(v for c in data.values() for r in c['reflows'].values() for rows in r['bifolia'].values()
                  for row in rows for v in row['profile'] if v is not None)
    ymin = min(50, int(minimum // 10) * 10)
    for key, control in data.items():
        chart(key, control, manuscript, ymin)
    payload = {'metric': 'Distinct forms in the first and last 100 words of each assigned page.',
               'saved_comparison_sha256': digest(STUDY / 'layout_controls.json'),
               'manuscript_sha256': digest(D.TOKENS),
               'historical_texts': data, 'minimum_endpoint_count': minimum, 'chart_y_min': ymin,
               'note': 'Deterministic placement reproduces every saved group and bifolium MATTR value; charts join only pages within a bifolium.'}
    (HERE / 'bio_historical_controls.json').write_text(json.dumps(payload, indent=2), encoding='utf-8')
    checked = sum(r['verification']['route_estimates_checked'] for c in data.values() for r in c['reflows'].values())
    print(f'Built five historical comparisons; {checked} saved MATTR values verified; minimum endpoint count {minimum}.')
    for key, item in data.items():
        print(key, {mode: r['overlapping_samples'] for mode, r in item['reflows'].items()})


if __name__ == '__main__':
    main()
