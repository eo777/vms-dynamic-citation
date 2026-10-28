"""Verify the saved rerun, its current dependencies and optionally a detached rerun.

The verification output is a compact dependency manifest, not a replacement for
rerunning run.py. Input hashes are checked before this manifest is written.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import platform
import subprocess

import numpy as np

HERE=Path(__file__).resolve().parent
STUDY=HERE.parent
sys.path.insert(0,str(STUDY))
import data as D
import geometry_inputs as G
from run import PINNED_INPUT


def resolve(key):
    key=key.replace('\\','/')
    # The original metrics remain immutable. Verify their exact input and runner
    # snapshots after the live app and CLI acquired a newer geometry version.
    if key=='apps/selfcitation_governor/data/mattr_heatmap/words.json.gz':
        return PINNED_INPUT
    if key=='research/mattr_template_link_20261026/alignment_rerun_20261028/run.py':
        return HERE/'inputs/run_v1.py'
    prefix='research/mattr_template_link_20261026/'
    return STUDY/key[len(prefix):] if key.startswith(prefix) else D.src(key)


def paired_delta(a,b):
    aa=a['metrics']['worddiv']['stratified']['bifolium_rows']
    bb=b['metrics']['worddiv']['stratified']['bifolium_rows']
    nodes=sorted(set().union(*(set(r) for r in aa+bb)))
    draw=np.random.default_rng(28102026).integers(0,len(nodes),(2000,len(nodes)))
    estimates=[]
    for rr in (aa,bb):
        v=np.array([[r.get(n,[0,0,0,0]) for n in nodes] for r in rr])
        s=v[:,draw,:].sum(axis=2)
        with np.errstate(divide='ignore',invalid='ignore'):
            estimates.append(np.mean(s[:,:,0]/s[:,:,1]-s[:,:,2]/s[:,:,3],axis=0))
    return dict(diff=b['metrics']['worddiv']['stratified']['diff']-a['metrics']['worddiv']['stratified']['diff'],
                ci95=np.nanquantile(estimates[1]-estimates[0],[.025,.975]).tolist())


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compare',type=Path,help='Compare an independently rebuilt run.py --permutations 0 JSON')
    args=parser.parse_args()
    metrics=json.loads((HERE/'metrics.json').read_text(encoding='utf8'))
    calibration=json.loads((HERE/'calibration.json').read_text(encoding='utf8'))
    heldout=json.loads((HERE/'heldout.json').read_text(encoding='utf8'))
    manifest={}
    for key,expected in metrics['input_sha256'].items():
        path=resolve(key)
        actual=hashlib.sha256(path.read_bytes()).hexdigest()
        assert actual==expected,(key,'input changed since rerun')
        manifest[key]=actual
    app=G.load_app('strict', path=PINNED_INPUT)
    review=app['spatialReview']
    tokens=review['tokens']
    assert len(tokens)==len(app['words'])==34977
    assert len({t['id'] for t in tokens})==len(tokens)
    for line in app['lines']:
        for i in range(line['start'],line['end']):
            t=tokens[i]
            assert (t['page'],t['locus'],t['text'])==(line['page'],line['locus'],app['words'][i])
            g=review['groups'].get(t['group'])
            if g:
                assert t['id'] in g['tokens'] and i in g['positions']
                parts=g['parts']
                union=([min(b[0] for b in parts),min(b[1] for b in parts),
                        max(b[2] for b in parts),max(b[3] for b in parts)] if parts else None)
                assert g['box']==union
            if t['strict']:
                assert g and len(g['parts'])==1 and len(g['tokens'])==1
                assert app['geometry'][i]==g['box']
            else:
                assert app['geometry'][i] is None
    for policy,arm in metrics['arms'].items():
        version=G.load_app('strict' if policy=='strict_live' else policy, path=PINNED_INPUT)
        assert arm['provenance']==version['geometry_provenance'],policy
        assert arm['located']==sum(b is not None for b in version['geometry'])
        assert all(b is None or (b[2]>b[0] and b[3]>b[1]) for b in version['geometry'])
        for control in arm['permutations'].values():
            assert len(control['values'])==metrics['settings']['permutations']==99
            p=(1+sum(v>=arm['actual']['metrics']['worddiv']['stratified']['diff'] for v in control['values']))/100
            assert p==control['one_sided_p']
    assert max(metrics['verification'].values())<1e-11
    assert len(calibration['verification'])==13
    assert max(v['max_contrast_error'] for v in calibration['verification'].values())<1e-10
    assert heldout['verification']['legacy_max_improvement_error']<1e-8
    # Corrected assignments change only 29 paragraph-text token rectangles; all
    # canonical words and line boundaries are invariant. Whole-MS review is broader.
    legacy=G.load_app('legacy', path=PINNED_INPUT)
    corrected=G.load_app('corrected', path=PINNED_INPUT)
    changed=[i for i,(a,b) in enumerate(zip(legacy['geometry'],corrected['geometry'])) if a!=b]
    assert legacy['words']==corrected['words']==app['words']
    assert legacy['lines']==corrected['lines']==app['lines']
    caches=0
    obsolete=[]
    import gzip
    for cache in (STUDY/'heatmap_variants').glob('*/data/mattr_heatmap/words.json.gz'):
        if cache.parts[-4] not in calibration['verification']:
            obsolete.append(cache.parts[-4])
            continue
        b=json.load(gzip.open(cache,'rt',encoding='utf8'))
        G.validate_variant(b,legacy)
        caches+=1
    comparison=None
    if args.compare:
        other=json.loads(args.compare.read_text(encoding='utf8'))
        for policy,arm in other['arms'].items():
            for key in ('actual','matched','historical_controls','pool_summary','provenance'):
                assert arm[key]==metrics['arms'][policy][key],(policy,key,'detached mismatch')
        comparison=dict(arms=len(other['arms']),exact=True)
    for path in [*HERE.glob('*.py'),*HERE.glob('*.js'),HERE/'metrics.json',HERE/'calibration.json',HERE/'heldout.json',
                 STUDY/'heatmap_variants.py',STUDY/'mechanism_check.py',STUDY/'compare_site.py',
                 D.src('research/timm_geometry_audit_20261026/component_impact_20261027/analyze.py'),
                 D.src('research/timm_geometry_audit_20261026/component_impact_20261027/unadjusted_metrics.json'),
                 D.src('research/dynamic_selfcitation_20261024/governed/page_geometry.py')]:
        manifest[str(path.relative_to(D.ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
    result=dict(passed=True,canonical_tokens=len(tokens),located_strict=sum(t['strict'] for t in tokens),
        runtime=dict(python=platform.python_version(),numpy=np.__version__,
                     node=subprocess.check_output(['node','--version'],text=True).strip()),
        assignment_only_changed_rectangles=len(changed),assignment_only_changed_ids=[tokens[i]['id'] for i in changed],
        validated_legacy_caches=caches,detached_reproduction=comparison,
        unused_unvalidated_legacy_caches=obsolete,
        paired_differences={name:{cohort:paired_delta(metrics['arms'][before][cohort],metrics['arms'][after][cohort])
                                 for cohort in ('actual','matched')}
                            for name,before,after in [('assignment_repairs','legacy','corrected'),
                                ('cleaned_assignment_repairs','legacy_clean','corrected_clean'),
                                ('strict_policy','legacy','strict'),('app_pitch','strict','strict_live')]},
        sha256=manifest)
    (HERE/'verification.json').write_text(json.dumps(result,indent=1)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('sha256','assignment_only_changed_ids')},indent=1))


if __name__=='__main__':
    main()
