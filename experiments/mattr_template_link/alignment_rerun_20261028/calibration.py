"""Rebuild every T17 comparison layout in memory, then remeasure it.

Checks old results and old saved variants before migrating cache provenance.
Saved generator WORDS are rescored, not regenerated; new generator trajectories
are a different experiment. No images, plots, or new variant HTML are written.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
import data as D
import geometry_inputs as G
import heatmap_variants as HV
import component_check as CC
import mechanism_check as MK
import timing
from run import Scorer, PINNED_INPUT


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--migrate-cache',action='store_true',help='Stamp old caches only after exact rebuilt content verification')
    args=parser.parse_args()
    old=json.loads((HERE.parent/'mechanism_check.json').read_text(encoding='utf8'))
    result=dict(arms={},verification={},inputs={})
    for policy in ('legacy','corrected','strict_live'):
        ms=D.manuscript()
        app=G.load_app('strict' if policy=='strict_live' else policy, path=PINNED_INPUT)
        timing.rng=np.random.default_rng(5)
        variants=HV.build_texts(ms,app)
        label_like={(L['folio'],L['locus']) for L in ms['lines'] if __import__('native_layout').label_like_slot(L)}
        sec={p['folio']:f"{p['section']}/{p['currier']}" for p in ms['pages']}
        grp={L['node']:L['group'] for L in ms['lines']}
        arm=result['arms'][policy]={}
        for key,label,lines,geom,comp,mode in variants:
            inp=CC.make_input(ms,lines,HV.rounded(geom),comp)
            scorer=Scorer(inp,policy)
            try:
                original=CC.measure
                CC.measure=lambda _:scorer.measures
                r=MK.analyse(inp,label_like,sec,grp)
            finally:
                CC.measure=original
                scorer.close()
            arm[key]=dict(stats=r,words_sha256=G.digest(inp['words']),geometry_sha256=G.digest(inp['geometry']),
                          input_geometry_provenance=app['geometry_provenance'])
            if policy=='legacy':
                # Exact floating arithmetic aside, every historical contrast must reproduce.
                errors=[abs(r[m][s]-old[key][m][s]) for m in ('worddiv','components','h2')
                        for s in ('all','short','long','no_label_targets')]
                assert max(errors)<1e-10,(key,max(errors))
                check=result['verification'][key]=dict(max_contrast_error=max(errors))
                cache=HERE.parent/'heatmap_variants'/key/'data/mattr_heatmap/words.json.gz'
                if cache.exists():
                    b=json.load(gzip.open(cache,'rt',encoding='utf8'))
                    for field in ('words','lines','geometry','components'):
                        assert b[field]==inp[field],(key,field,'stale cache')
                    check['cached_content_exact']=True
                    if args.migrate_cache:
                        b['input_geometry_provenance']=app['geometry_provenance']
                        cache.write_bytes(gzip.compress(json.dumps(b,separators=(',',':')).encode(),mtime=0))
            print(policy,key,'worddiv',r['worddiv']['all'],flush=True)
        (HERE/'calibration.json').write_text(json.dumps(result,indent=1)+'\n',encoding='utf8')
    paths=[HERE/'calibration.py',HERE/'run.py',HERE/'measure.js',HERE.parent/'heatmap_variants.py',
           HERE.parent/'mechanism_check.py',HERE.parent/'geometry_inputs.py',
           D.src('research/dynamic_selfcitation_20261024/governed/page_geometry.py')]
    for _,sources in D.STREAMS.values():
        paths.extend(sources[:1])
    paths.append(__import__('native_layout').GART)
    for path in paths:
        p=Path(path)
        result['inputs'][p.relative_to(D.ROOT).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
    (HERE/'calibration.json').write_text(json.dumps(result,indent=1)+'\n',encoding='utf8')


if __name__=='__main__':
    main()
