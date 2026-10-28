"""Reproduce the geometry sensitivity of the MATTR source-diversity finding.

No cached heatmap variants or image assets are read. Every pool is rebuilt from
the selected geometry. Historical scripts/results remain the 27 October record.
Default: 99 paired paragraph + 99 paired page shuffles per arm, seed 28102026.
Peak additional disk <100 MB, retained metrics/provenance <10 MB; no model arrays.
"""
import argparse
from collections import defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

import numpy as np

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
sys.path.insert(0, str(STUDY))
import data as D
import component_check as CC
import geometry_inputs as G
import timing
import mattr_vs_components as MC

POLICIES = (*G.POLICIES, 'strict_live')
METRICS = ('worddiv', 'components', 'h2')


def arrays(value):
    return {k: np.array([np.nan if x is None else x for x in v], dtype=float)
            for k, v in value.items()}


class Scorer:
    def __init__(self, inp, policy):
        self.tmp = tempfile.TemporaryDirectory()
        pin = Path(self.tmp.name) / 'input.json'
        pin.write_text(json.dumps(inp), encoding='utf8')
        self.selector = D.src('apps/selfcitation_governor/heatmap_sources.js') if policy == 'strict_live' else STUDY / 'component_source_math.js'
        self.process = subprocess.Popen(['node', str(HERE/'measure.js'), str(pin), str(self.selector),
                                         'live' if policy == 'strict_live' else 'frozen'],
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, encoding='utf8')
        self.meta = json.loads(self.process.stdout.readline())
        self.measures = arrays(self.meta.pop('measures'))
        self.ids = {w: i for i,w in enumerate(self.meta.pop('vocabulary'))}

    def score(self, words):
        self.process.stdin.write(json.dumps([self.ids[w] for w in words])+'\n')
        self.process.stdin.flush()
        out = arrays(json.loads(self.process.stdout.readline()))
        out['n'] = self.measures['n']
        out['components'] = np.where(out.pop('valid'), 1., np.nan)
        return out

    def close(self):
        self.process.stdin.close()
        self.process.wait(timeout=30)
        self.tmp.cleanup()
        if self.process.returncode:
            raise RuntimeError('Scorer failed')


def rows(metric, outcome, node, mask):
    result = {}
    for b in np.unique(node[mask]):
        m = mask & (node == b) & np.isfinite(metric) & np.isfinite(outcome)
        if m.sum() < 25:
            continue
        x,y = metric[m],outcome[m]
        lo,hi = np.quantile(x,[.2,.8])
        a,c = y[x<=lo],y[x>=hi]
        result[b] = [float(a.sum()),len(a),float(c.sum()),len(c)]
    return result


def diff(v):
    s = np.asarray(list(v.values())).sum(axis=0)
    return float(s[0]/s[1]-s[2]/s[3]) if np.size(s)==4 and s[1] and s[3] else np.nan


def stratified(metric, outcome, meas, node, mask, bootstrap=0):
    if not mask.any():
        return dict(diff=np.nan, n=0, tertiles=[], rows=[])
    q = np.percentile(meas['n'][mask],[33,67])
    rr = [rows(metric,outcome,node,mask & (meas['n']>a) & (meas['n']<=b))
          for a,b in ((-1,q[0]),(q[0],q[1]),(q[1],1e9))]
    result = dict(diff=float(np.mean([diff(r) for r in rr])), n=int(mask.sum()),
                  tertiles=[float(x) for x in q], by_tertile=[diff(r) for r in rr])
    if bootstrap:
        # Draw the SAME bifolia across the three strata, preserving covariance.
        nodes = sorted(set().union(*(set(r) for r in rr)))
        v = np.array([[r.get(b,[0,0,0,0]) for b in nodes] for r in rr])
        draw = np.random.default_rng(28102026).integers(0,len(nodes),(bootstrap,len(nodes)))
        s = v[:,draw,:].sum(axis=2)
        with np.errstate(invalid='ignore', divide='ignore'):
            bs = np.mean(s[:,:,0]/s[:,:,1]-s[:,:,2]/s[:,:,3],axis=0)
        result['ci95'] = np.nanquantile(bs,[.025,.975]).tolist()
        result['bifolia'] = len(nodes)
        result['bifolium_rows'] = rr
    return result


def summarize(inp, meas, ms, common=None, bootstrap=2000):
    node,group,bs,be = CC.token_meta(ms,[inp['words'][l['start']:l['end']] for l in inp['lines']])
    out = CC.outcomes(inp['words'],bs,be)
    base = out['full'] & np.isfinite(meas['components']) & np.isfinite(meas['worddiv'])
    if common is not None:
        base &= common
    page = np.empty(len(node),dtype=object)
    section = np.empty(len(node),dtype=object)
    sec = {p['folio']:f"{p['section']}/{p['currier']}" for p in ms['pages']}
    for line in inp['lines']:
        page[line['start']:line['end']] = line['page']
        section[line['start']:line['end']] = sec[line['page']]
    result = dict(cohort=int(base.sum()), metrics={}, regions={})
    for key in METRICS:
        result['metrics'][key] = dict(
            stratified=stratified(meas[key],out['app_impact'],meas,node,base,bootstrap),
            unstratified=CC.quintile_contrast(meas[key],out['app_impact'],node,base,reps=max(bootstrap,1)),
            lobo_error_reduction_percent=CC.lobo_linear(meas[key],out['app_impact'],node,base))
    for name,mask in [('Bio',section=='B/B'),('Stars',section=='S/B'),('3c',group=='3c'),('4a',group=='4a')]:
        result['regions'][name] = {key:stratified(meas[key],out['app_impact'],meas,node,base&mask,bootstrap)
                                   for key in METRICS}
    result['repeat99'] = stratified(meas['worddiv'],out['repeat100'],meas,node,base,bootstrap)
    result['repeat_source'] = stratified(meas['worddiv'],meas['repeat_source'],meas,node,base,bootstrap)
    mattr = D.trailing_distinct(inp['words'],100)
    m = np.isfinite(mattr)&np.isfinite(meas['components'])
    if common is not None:
        m &= common
    pp = [[mattr[m&(page==p)].mean(),*[meas[k][m&(page==p)].mean() for k in METRICS]]
          for p in np.unique(page[m]) if (m&(page==p)).sum()>=100]
    pp = np.asarray(pp)
    result['mattr_correlations'] = {key:dict(token=MC.spearman(mattr[m],meas[key][m]),
        within_page=MC.spearman(MC.demean(mattr[m],page[m]),MC.demean(meas[key][m],page[m])),
        page_means=MC.spearman(pp[:,0],pp[:,j+1])) for j,key in enumerate(METRICS)}
    return result,base,out,node


def shuffle(words, units, rng):
    result = np.array(words,dtype=object)
    for indices in units:
        result[indices] = result[rng.permutation(indices)]
    return result.tolist()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--permutations',type=int,default=99)
    parser.add_argument('--policies',nargs='+',choices=POLICIES,default=list(POLICIES))
    parser.add_argument('--output',type=Path,default=HERE/'metrics.json')
    args = parser.parse_args()
    started = time.time()
    ms = D.manuscript()
    tok = D.tokenize(ms)
    words = list(tok['words'])
    baseline = json.loads((STUDY/'mechanism_check.json').read_text(encoding='utf8'))
    groups = {'paragraph':np.cumsum(tok['since_par']==0),'page':tok['page']}
    units = {k:[np.where(v==u)[0] for u in np.unique(v)] for k,v in groups.items()}
    # Exact historical two controls: timing.py RNG=5, paragraph then page.
    timing.rng = np.random.default_rng(5)
    historical = {k:[w for line in timing.shuffled_within(ms,tok,v) for w in line] for k,v in groups.items()}
    apps,inputs,scorers,measures = {},{},{},{}
    result = dict(settings=dict(policies=args.policies,permutations=args.permutations,seed=28102026,
        window=100,left=3,depth=8,angle=45,weight='distance',bootstrap_bifolia=2000,
        outcome='Token N replacement impact, in MATTR percentage points; not future-window diversity',
        shuffle='Fixed slot geometry/eligibility; spellings shuffled inside paragraph/page; paired permutations across arms'),
        arms={},verification={})
    try:
        for policy in args.policies:
            app = apps[policy] = G.load_app('strict' if policy=='strict_live' else policy)
            assert app['words']==words
            inp = inputs[policy] = dict(words=words,lines=app['lines'],geometry=app['geometry'],components=app['components'])
            scorer = scorers[policy] = Scorer(inp,policy)
            measures[policy] = scorer.measures
            print(policy,'pools built',scorer.meta['edges'],flush=True)
        common = np.logical_and.reduce([np.isfinite(m['components']) for m in measures.values()])
        for policy in args.policies:
            scorer,inp,meas = scorers[policy],inputs[policy],measures[policy]
            actual,base,out,node = summarize(inp,meas,ms)
            matched,*_ = summarize(inp,meas,ms,common)
            arm = result['arms'][policy] = dict(provenance=apps[policy]['geometry_provenance'],
                located=sum(g is not None for g in inp['geometry']),pool_summary=scorer.meta,
                actual=actual,matched=matched,historical_controls={},permutations={})
            for kind,ws in historical.items():
                mm = scorer.score(ws)
                control_out = CC.outcomes(ws,*CC.token_meta(ms,[ws[l['start']:l['end']] for l in inp['lines']])[2:])
                mask = control_out['full']&np.isfinite(mm['components'])
                arm['historical_controls'][kind] = stratified(mm['worddiv'],control_out['app_impact'],mm,node,mask,2000)
            if policy in ('legacy','legacy_clean'):
                key = 'manuscript' if policy=='legacy' else 'manuscript_clean'
                delta = actual['metrics']['worddiv']['stratified']['diff']-baseline[key]['worddiv']['all']
                assert abs(delta)<1e-12,(policy,delta)
                result['verification'][policy+'_historical_worddiv_abs_error'] = abs(delta)
                if policy=='legacy':
                    for kind,suffix in [('paragraph','paragraphs'),('page','pages')]:
                        delta = arm['historical_controls'][kind]['diff']-baseline['manuscript_shuffled_'+suffix]['worddiv']['all']
                        assert abs(delta)<1e-12,(kind,delta)
                        result['verification']['historical_'+kind+'_abs_error'] = abs(delta)
                    old = json.load(gzip.open(CC.OTHER,'rt',encoding='utf8'))['rows']
                    for key in ('components','h2'):
                        oldv=np.array([np.nan if r[key] is None else r[key] for r in old])
                        assert np.array_equal(np.isfinite(oldv),np.isfinite(meas[key]))
                        error=float(np.nanmax(np.abs(oldv-meas[key])))
                        assert error<1e-11
                        result['verification']['historical_'+key+'_max_error']=error
            print(policy,'worddiv',actual['metrics']['worddiv']['stratified']['diff'],
                  'controls',{k:v['diff'] for k,v in arm['historical_controls'].items()},flush=True)
            for kind,uu in units.items():
                rng = np.random.default_rng(28102026+(kind=='page'))
                values = []
                for rep in range(args.permutations):
                    ws=shuffle(words,uu,rng)
                    mm=scorer.score(ws)
                    control_out=CC.outcomes(ws,*CC.token_meta(ms,[ws[l['start']:l['end']] for l in inp['lines']])[2:])
                    mask=control_out['full']&np.isfinite(mm['components'])
                    values.append(stratified(mm['worddiv'],control_out['app_impact'],mm,node,mask)['diff'])
                observed=actual['metrics']['worddiv']['stratified']['diff']
                arm['permutations'][kind]=dict(values=values,mean=float(np.mean(values)) if values else None,
                    ci95=np.quantile(values,[.025,.975]).tolist() if values else None,
                    one_sided_p=(1+sum(v>=observed for v in values))/(1+len(values)) if values else None)
                print(policy,kind,'permutations complete',flush=True)
            scorer.close()
            scorers.pop(policy)
            args.output.write_text(json.dumps(result,indent=1,allow_nan=True)+'\n',encoding='utf8')
        paths=[CC.APP,D.TOKENS,D.PHYS,D.ASSET,CC.OTHER,STUDY/'mechanism_check.json',
               STUDY/'component_source_math.js',D.src('apps/selfcitation_governor/heatmap_sources.js'),
               STUDY/'geometry_inputs.py',STUDY/'component_check.py',STUDY/'data.py',STUDY/'timing.py',
               STUDY/'mattr_vs_components.py',HERE/'measure.js',Path(__file__)]
        result['input_sha256']={str(p.relative_to(D.ROOT)) if p.is_relative_to(D.ROOT) else str(p):
            hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
        result['elapsed_seconds']=time.time()-started
        args.output.write_text(json.dumps(result,indent=1,allow_nan=True)+'\n',encoding='utf8')
        print('saved',args.output,'seconds',round(time.time()-started),flush=True)
    finally:
        for scorer in scorers.values():
            scorer.close()


if __name__=='__main__':
    main()
