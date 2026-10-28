"""Plot the spatial repeat contrast by page illustration section.

Default: redraw from the compact saved JSON. --recompute: rescore the same
legacy-geometry inputs as the Golf chart, verify its published point estimates,
and regroup targets by the physical map's section field (without Currier splits).
No text is generated. Temporary per-token measurements are discarded by measure().
"""
import argparse
import gzip
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
import figures_small as F

OUTPUT = HERE / 'illustration_contrasts.json'
SECTIONS = [('H', 'Herbal'), ('P', 'Pharma'), ('S', 'Stars'),
            ('B', 'Bio'), ('T', 'Text-only pages'), ('C', 'Cosmological'),
            ('A', 'Astrological')]
MEASURES = [('components', 'component diversity'), ('h2', 'glyph H2')]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def contrast(measure, outcome, node, mask):
    """Original point estimate: pool low/high sums across eligible bifolia."""
    rows = []
    for bifolium in np.unique(node[mask]):
        keep = mask & (node == bifolium) & np.isfinite(measure) & np.isfinite(outcome)
        if keep.sum() < 25:
            continue
        x, y = measure[keep], outcome[keep]
        lo, hi = np.quantile(x, [.2, .8])
        low, high = y[x <= lo], y[x >= hi]
        rows.append([float(low.sum()), len(low), float(high.sum()), len(high)])
    if not rows:
        return {'contrast': None, 'bifolia': 0}
    total = np.array(rows).sum(axis=0)
    return {'contrast': float(total[0] / total[1] - total[2] / total[3]),
            'bifolia': len(rows)}


def section_stats(meas, outcome, node, mask):
    result = {'n': int(mask.sum())}
    if not mask.any():
        return dict(result, pool_size_cutoffs=[], **{
            metric: {'contrast': None, 'bands': []} for metric, _ in MEASURES})
    cutoffs = np.percentile(meas['n'][mask], [33, 67])
    result['pool_size_cutoffs'] = cutoffs.tolist()
    bands = [mask & (meas['n'] > a) & (meas['n'] <= b)
             for a, b in [(-1, cutoffs[0]), (cutoffs[0], cutoffs[1]), (cutoffs[1], 1e9)]]
    for metric, _ in MEASURES:
        parts = [contrast(meas[metric], outcome, node, band) for band in bands]
        values = [part['contrast'] for part in parts]
        result[metric] = {'contrast': float(np.mean(values)) if None not in values else None,
                          'bands': parts}
    return result


def recompute():
    import data as D
    import component_check as CC
    from geometry_inputs import digest as value_digest, validate_variant
    from timing import shuffled_within

    manuscript = D.manuscript()
    page_sections = {p['folio']: p['section'] for p in manuscript['pages']}
    page_currier = {p['folio']: p['currier'] for p in manuscript['pages']}
    groups = {line['node']: line['group'] for line in manuscript['lines']}
    legacy_sections = [('Herbal A', 'H/A'), ('Herbal B', 'H/B'), ('Pharma', 'P/A'),
                       ('Stars', 'S/B'), ('Bio', 'B/B'), ('Text-only pages', 'T/B')]
    manuscript_path = STUDY / 'heatmap_variants/manuscript/data/mattr_heatmap/words.json.gz'
    with gzip.open(manuscript_path, 'rt', encoding='utf-8') as handle:
        app = json.load(handle)
    app['geometry_provenance'] = app['input_geometry_provenance']
    assert app['geometry_provenance']['policy'] == 'legacy'
    assert value_digest(app['words']) == app['geometry_provenance']['words_sha256']
    assert value_digest(app['geometry']) == app['geometry_provenance']['geometry_sha256']
    assert app['words'] == [w for line in manuscript['lines'] for w in line['words']]
    frozen = json.loads((STUDY / 'mechanism_check.json').read_text(encoding='utf-8'))
    tok = D.tokenize(manuscript)
    shuffles = {
        'manuscript_shuffled_paragraphs': shuffled_within(manuscript, tok, np.cumsum(tok['since_par'] == 0)),
        'manuscript_shuffled_pages': shuffled_within(manuscript, tok, tok['page']),
    }
    result = {
        'grouping': 'physical_map.csv section; all Currier labels combined; target page determines section',
        'geometry_policy': 'legacy, matching the existing Golf chart',
        'statistic': 'lowest-minus-highest source-diversity quintile repeat-score contrast within bifolium; '
                     'pooled target sums within each source-pool-size band; equal mean of three bands',
        'minimum_targets_per_bifolium_per_band': 25,
        'physical_map_sha256': digest(D.PHYS),
        'comparison_json_sha256': digest(STUDY / 'mechanism_check.json'),
        'source_math_sha256': digest(STUDY / 'component_source_math.js'),
        'sections': [{'code': code, 'name': name,
                      'pages': [p['folio'] for p in manuscript['pages'] if p['section'] == code],
                      'manuscript_tokens': sum(len(l['words']) for l in manuscript['lines']
                                               if page_sections[l['folio']] == code)}
                     for code, name in SECTIONS],
        'texts': {},
    }
    errors = []
    missing_matches = 0
    for key, _, _ in F.ROWS:
        if key is None:
            continue
        if key in shuffles:
            inp = CC.make_input(manuscript, shuffles[key], app['geometry'], CC.zattera)
            provenance = app['geometry_provenance']
        else:
            path = STUDY / 'heatmap_variants' / key / 'data/mattr_heatmap/words.json.gz'
            with gzip.open(path, 'rt', encoding='utf-8') as handle:
                inp = json.load(handle)
            validate_variant(inp, app)
            provenance = dict(inp['input_geometry_provenance'], bundle_sha256=digest(path))
        meas = CC.measure(inp)
        count = len(inp['words'])
        node, section, old_section, group = [np.empty(count, dtype=object) for _ in range(4)]
        for line in inp['lines']:
            ix = slice(line['start'], line['end'])
            node[ix] = line['bifolium']
            section[ix] = page_sections[line['page']]
            old_section[ix] = page_sections[line['page']] + '/' + page_currier[line['page']]
            group[ix] = groups[line['bifolium']]
        starts, ends = np.zeros(count, int), np.zeros(count, int)
        for bifolium in np.unique(node):
            indices = np.flatnonzero(node == bifolium)
            assert indices[-1] - indices[0] + 1 == len(indices)
            starts[indices], ends[indices] = indices[0], indices[-1] + 1
        outcomes = CC.outcomes(inp['words'], starts, ends)
        base = outcomes['full'] & np.isfinite(meas['components']) & np.isfinite(meas['h2']) & np.isfinite(meas['worddiv'])
        # Reproduce all nine Golf groups and six old section/Currier estimates.
        for field, masks in [('groups', [(g, group == g) for g in F.GROUP_PANELS]),
                             ('sections', [(name, old_section == code) for name, code in legacy_sections])]:
            for name, mask in masks:
                got = section_stats(meas, outcomes['app_impact'], node, base & mask)
                expected = frozen[key][field][name]
                assert got['n'] == expected['n'], (key, field, name, got['n'], expected['n'])
                for metric, _ in MEASURES:
                    if got[metric]['contrast'] is None:
                        assert not np.isfinite(expected[metric]), (key, field, name, metric, expected[metric])
                        missing_matches += 1
                        continue
                    error = abs(got[metric]['contrast'] - expected[metric])
                    assert error < 1e-12, (key, field, name, metric, error)
                    errors.append(error)
        result['texts'][key] = {
            'input': provenance,
            'sections': {code: section_stats(meas, outcomes['app_impact'], node, base & (section == code))
                         for code, _ in SECTIONS},
        }
        print(f'{key}: matched saved Golf/section estimates; illustration sections calculated', flush=True)
    result['verification'] = {'compared_estimates': len(errors), 'maximum_absolute_difference': max(errors),
                              'matching_unavailable_estimates': missing_matches, 'counts_match': True}
    OUTPUT.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    return result


def plot(result):
    # Astrological pages cannot support every pool-size band in the manuscript.
    panels = [(code, name) for code, name in SECTIONS if code != 'A']
    assert all(result['texts']['manuscript']['sections']['A'][m]['contrast'] is None for m, _ in MEASURES)
    plt.rcParams.update({'font.size': 10, 'svg.fonttype': 'none'})
    fig, axes = plt.subplots(2, 3, figsize=(16, 11.6), sharey=True)
    ys = np.arange(len(F.ROWS))[::-1]
    values = [item['contrast'] for text in result['texts'].values()
              for code, _ in panels for metric, _ in MEASURES
              if (item := text['sections'][code][metric])['contrast'] is not None]
    low, high = min(-.1, min(values)) - .025, max(.15, max(values)) + .025
    for index, ((code, title), ax) in enumerate(zip(panels, axes.flat)):
        for y, (key, label, color) in zip(ys, F.ROWS):
            if key is None:
                if y != ys[0]:
                    ax.axhline(y + .5, color=F.GRID, linewidth=.8)
                continue
            record = result['texts'][key]['sections'][code]
            a, b = [record[m]['contrast'] for m, _ in MEASURES]
            if a is not None and b is not None:
                ax.plot([a, b], [y, y], color=color, alpha=.45, linewidth=1)
            for (metric, _), value, offset in zip(MEASURES, [a, b], [.18, -.18]):
                if value is not None:
                    ax.plot(value, y + offset, marker=F.MARK[metric], color=color, markersize=5, linestyle='none')
                else:
                    ax.text(.98, y, 'n/a', transform=ax.get_yaxis_transform(), ha='right', va='center', fontsize=7, color=F.MUTED)
        ax.axvline(0, color=F.MUTED, linewidth=1)
        ax.set_xlim(low, high)
        ax.set_ylim(-.65, len(F.ROWS) - .4)
        ax.set_yticks(ys)
        ax.set_yticklabels([row[1] for row in F.ROWS], fontsize=9)
        if index % 3 == 0:
            F.style_headers(ax)
        n = result['texts']['manuscript']['sections'][code]['n']
        ax.set_title(f'{title}\n{n:,} manuscript words scored', loc='left', fontsize=11, pad=11)
        ax.tick_params(axis='x', labelsize=9)
        if index >= 3:
            ax.set_xlabel('repeat rate after the least diverse pool\nminus after the most diverse pool', fontsize=9)
    fig.suptitle('Are words with a less diverse pool in view more often repeats?', x=.02, y=.99,
                 ha='left', fontsize=15, color=F.INK)
    fig.text(.02, .955, 'By manuscript / illustration section. Each page uses its own section label; all Herbal pages are combined.\n'
             'Same controls and calculation as the Golf chart: compare the lowest and highest fifths within bifolia, then average the three pool-size bands.',
             fontsize=9.5, color=F.SEC, va='top')
    fig.legend(handles=[Line2D([], [], marker=F.MARK[m], color=F.SEC, linestyle='none', markersize=6, label=label)
                        for m, label in MEASURES], loc='lower center', bbox_to_anchor=(.65, .044), frameon=False, ncol=2, fontsize=10)
    fig.text(.02, .025, 'Cosmological: 172 scored manuscript words. Astrological: 75; too few qualifying targets for all three pool-size bands, so no panel.',
             fontsize=9, color=F.SEC)
    fig.subplots_adjust(left=.285, right=.99, top=.865, bottom=.12, wspace=.13, hspace=.30)
    for extension in ['png', 'svg']:
        path = HERE / f'contrast_by_illustration_components_h2.{extension}'
        fig.savefig(path, dpi=160, bbox_inches='tight')
        if extension == 'svg':
            path.write_text('\n'.join(line.rstrip() for line in path.read_text(encoding='utf-8').splitlines()) + '\n', encoding='utf-8')
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recompute', action='store_true')
    args = parser.parse_args()
    result = recompute() if args.recompute else json.loads(OUTPUT.read_text(encoding='utf-8'))
    plot(result)
    print('Wrote illustration-section chart and compact metrics.')


if __name__ == '__main__':
    main()
