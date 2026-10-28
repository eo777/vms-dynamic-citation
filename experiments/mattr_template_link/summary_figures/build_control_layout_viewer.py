"""Prepare f75r in the actual heatmap viewer with the frozen control bundles.

Only the displayed page and app shell are refreshed. Words and coordinates are
copied unchanged; no model runs, text reflow or spatial scoring are performed here.
The current app's Show words / Boxes controls render the labels in the browser.
"""
import gzip
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
sys.path.insert(0, str(STUDY))
import heatmap_variants as H

CASES = [
    ('manuscript', 'Voynich manuscript', 'Recorded word positions'),
    ('gart_one_word_per_box', 'Gart 1487', 'One word per manuscript box'),
    ('gart_character_budget', 'Gart 1487', 'Fill each line’s character budget'),
    ('gart_own_lines', 'Gart 1487', 'Keep the printed text’s own lines'),
    ('bigram_whole', 'Markov control', 'Whole-manuscript word bigrams'),
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    output = HERE / 'control_layout_viewer'
    shell = output / 'shell'
    shell.mkdir(parents=True, exist_ok=True)
    template = (H.APP / 'heatmap.html').read_text(encoding='utf-8')
    # Keep the actual app markup and controls, with one sheet and one page.
    template = re.sub(r'<section class="bifolio".*?</section>',
                      lambda m: m[0] if '<h2>M:75-84</h2>' in m[0] else '', template, flags=re.S)
    template = re.sub(r'<figure\b.*?</figure>',
                      lambda m: m[0] if '<figcaption>f75r</figcaption>' in m[0] else '', template, flags=re.S)
    assert template.count('<figure') == 1
    source_files = {}
    for name in H.SHELL:
        shutil.copyfile(H.APP / name, shell / name)
        source_files[name] = sha(shell / name)
    entries = []
    for key, title, subtitle in CASES:
        source = STUDY / 'heatmap_variants' / key / 'data/mattr_heatmap/words.json.gz'
        with gzip.open(source, 'rt', encoding='utf-8') as stream:
            bundle = json.load(stream)
        # page_html validates its rectangle count against the passed geometry.
        # Mask other pages only in the renderer input, not in the data bundle.
        indices = [i for line in bundle['lines'] if line['page'] == 'f75r'
                   for i in range(line['start'], line['end'])]
        visible = set(indices)
        renderer = dict(bundle, geometry=[box if i in visible else None
                                         for i, box in enumerate(bundle['geometry'])])
        target = output / key
        (target / 'data/mattr_heatmap').mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target / 'data/mattr_heatmap/words.json.gz')
        document = H.page_html(template, key, f'{title} · {subtitle}', renderer, [case[0] for case in CASES])
        (target / 'heatmap.html').write_text(document, encoding='utf-8')
        entries.append(dict(key=key, title=title, subtitle=subtitle, page='f75r',
                            tokens=len(indices), boxes=sum(bundle['geometry'][i] is not None for i in indices),
                            bundle_sha256=sha(source),
                            input_geometry_provenance=bundle.get('input_geometry_provenance'),
                            url=f'http://127.0.0.1:8767/summary_figures/control_layout_viewer/{key}/heatmap.html'
                                '#scope=all&expanded=f75r&words=1&boxes=hidden&colors=mattr'))
        print(key, entries[-1]['tokens'], 'words;', entries[-1]['boxes'], 'boxes')
    (HERE / 'control_layout_inputs.json').write_text(json.dumps(dict(
        page='f75r', app_files=source_files, cases=entries,
        note='Frozen words and coordinates displayed by unchanged current heatmap app scripts; image overlay off.'),
        indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
