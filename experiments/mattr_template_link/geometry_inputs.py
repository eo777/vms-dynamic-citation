"""Explicit geometry versions for historical reproduction and the alignment rerun.

The 27 October scripts reproduce their frozen results with ``legacy``. The
28 October rerun explicitly selects corrected/reviewed policies. Never infer a
historical input from whichever geometry the interactive app currently defaults to.
"""
import gzip
import hashlib
import json

import numpy as np
import data as D

POLICIES = ('legacy', 'legacy_clean', 'corrected', 'corrected_clean', 'sensitivity', 'strict')


def digest(value):
    return hashlib.sha256(json.dumps(value, separators=(',', ':'), ensure_ascii=True).encode()).hexdigest()


def clean_geometry(geometry, lines):
    """The 27 October page-relative size exclusion, applied exactly once."""
    pages = {}
    for line in lines:
        pages.setdefault(line['page'], []).extend(range(line['start'], line['end']))
    result = list(geometry)
    for indices in pages.values():
        boxes = [geometry[i] for i in indices if geometry[i] is not None]
        if not boxes:
            continue
        width = np.median([b[2] - b[0] for b in boxes])
        height = np.median([b[3] - b[1] for b in boxes])
        for i in indices:
            b = geometry[i]
            if b and (b[2] - b[0] > 6 * width or b[3] - b[1] > 2.5 * height):
                result[i] = None
    return result


def load_app(policy='legacy', path=None):
    if policy not in POLICIES:
        raise ValueError(policy)
    path = path or D.src('apps/selfcitation_governor/data/mattr_heatmap/words.json.gz')
    with gzip.open(path, 'rt', encoding='utf8') as handle:
        app = json.load(handle)
    review = app.get('spatialReview')
    if policy.startswith('legacy'):
        if review and 'legacyGeometry' not in app:
            raise ValueError('Reviewed bundle lacks the historical geometry')
        geometry = app.get('legacyGeometry', app['geometry'])
    else:
        if not review:
            raise ValueError('Corrected geometry requires a schema-3 reviewed bundle')
        assert len(review['tokens']) == len(app['words'])
        assert [t['text'] for t in review['tokens']] == app['words']
        if policy.startswith('corrected'):
            # Diagnostic assignment-only arm, NOT a claim of unique word geometry:
            # retain ambiguous original unions, change only reviewed associations.
            geometry = [review['groups'][t['group']]['box'] if t['group'] else None
                        for t in review['tokens']]
            # The old renderer omitted zero-area XML placeholders. Do not
            # accidentally restore those while isolating assignment corrections.
            geometry = [b if b and b[2] > b[0] and b[3] > b[1] else None for b in geometry]
        else:
            geometry = review['geometry'] if policy == 'strict' else review['sensitivityGeometry']
    if policy.endswith('_clean'):
        geometry = clean_geometry(geometry, app['lines'])
    app = dict(app, geometry=geometry)
    # Historical frame code must not apply today's strict token mask to legacy boxes.
    if policy.startswith(('legacy', 'corrected')):
        app.pop('spatialReview', None)
    elif policy == 'sensitivity':
        app['spatialReview'] = dict(review, tokens=[dict(t, strict=g is not None)
                                                  for t, g in zip(review['tokens'], geometry)])
    app['geometry_provenance'] = dict(policy=policy, words_sha256=digest(app['words']),
                                    geometry_sha256=digest(geometry),
                                    review_version=review['version'] if review else None)
    return app


def validate_variant(bundle, app):
    """Fail closed on a stale/mixed cache; old unversioned caches must be rebuilt."""
    if bundle.get('input_geometry_provenance') != app['geometry_provenance']:
        raise ValueError('Stale heatmap variant: rerun heatmap_variants.py before consuming it')
