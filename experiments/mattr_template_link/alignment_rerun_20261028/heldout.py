"""Rerun the original grouped five-fold impact prediction on updated predictors.

Reuses analyze.py (ridge 10, five-knot splines, train-only fitting, bifolium folds).
Text outcomes and nonspatial history are unchanged. Retains aggregate scores only.
"""
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
import data as D
import geometry_inputs as G
from run import Scorer, PINNED_INPUT


def main():
    source=D.src('research/timm_geometry_audit_20261026/component_impact_20261027/analyze.py')
    spec=importlib.util.spec_from_file_location('original_impact_analysis',source)
    A=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(A)
    # The packaged source and its original derived table may have different roots.
    A.HERE=D.src('research/timm_geometry_audit_20261026/component_impact_20261027/derived.json.gz').parent
    _,original,_=A.prepare()
    baseline=json.loads(D.src('research/timm_geometry_audit_20261026/component_impact_20261027/unadjusted_metrics.json').read_text(encoding='utf8'))
    A.TIERS={'global':[], 'section':[]}
    A.CANDIDATES={k:v for k,v in A.CANDIDATES.items() if not k.startswith('relative_')}
    result={'arms':{},'verification':{}}
    for policy in ('legacy','corrected','strict','strict_live'):
        app=G.load_app('strict' if policy=='strict_live' else policy, path=PINNED_INPUT)
        inp={k:app[k] for k in ('words','lines','geometry','components')}
        scorer=Scorer(inp,policy)
        try:
            data=original.copy()
            for key in ('components','h1','h2','worddiv','n','pair_ess'):
                data[key]=scorer.measures[key]
        finally:
            scorer.close()
        mask=data.full_impact_support&data[['components','h1','h2','prior_ttr','prior_red','worddiv','log_prior_components']].notna().all(axis=1)
        data=data[mask].copy().reset_index(drop=True)
        A.RNG=np.random.default_rng(2026102702)
        cv=A.cv(data)
        result['arms'][policy]={'n':len(data),'folds':cv['folds'],'scores':cv['scores'],'warnings':cv['warnings']}
        if policy=='legacy':
            errors=[]
            for region,rr in baseline['full_cv']['scores'].items():
                for outcome,oo in rr['outcomes'].items():
                    for name,stats in oo.items():
                        errors.append(abs(stats['improvement_percent']-cv['scores'][region]['outcomes'][outcome][name]['improvement_percent']))
            assert max(errors)<1e-8,max(errors)
            result['verification']['legacy_max_improvement_error']=max(errors)
        print(policy,len(data),{k:v['improvement_percent'] for k,v in cv['scores']['all']['outcomes']['app_impact'].items()},flush=True)
        (HERE/'heldout.json').write_text(json.dumps(A.clean(result),indent=1)+'\n',encoding='utf8')


if __name__=='__main__':
    main()
