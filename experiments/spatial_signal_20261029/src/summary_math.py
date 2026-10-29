import json,hashlib
from pathlib import Path
import numpy as np
from scipy.stats import beta

def test(values):
 a=np.asarray(values,float);observed=a[0];null=a[1:];B=len(null);k=int(np.sum(null>=observed-1e-12))
 return {'observed':float(observed),'null_mean':float(null.mean()),'excess':float(observed-null.mean()),'null_sd':float(null.std(ddof=1)),'null_95':np.quantile(null,[.025,.975]).tolist(),'exceedances':k,'permutations':B,'p':(k+1)/(B+1),'mc_tail_95':[0. if k==0 else float(beta.ppf(.025,k,B-k+1)),1. if k==B else float(beta.ppf(.975,k+1,B-k))]}

def holm(items,key):
 ordered=sorted(items,key=lambda r:r['p']);prior=0
 for rank,r in enumerate(ordered):prior=max(prior,min(1,(len(items)-rank)*r['p']));r[key]=prior

def summary(d,directory):
 P=Path(directory)
 assert d['completed']==d['permutations']
 assert d['plan_sha256']==hashlib.sha256((P/'plan.json').read_bytes()).hexdigest()
 tag=d['case']['id']+'__'+d['geometry']+'-'+d['nullKind']
 aggregate_checks=json.loads((P/(tag+'-aggregate-validation.json')).read_text())
 assert {x['draw'] for x in aggregate_checks}=={0,1,d['permutations']}
 assert all(x['max_difference']<1e-10 and not x['differences'] for x in aggregate_checks)
 v=d['validation'];assert v['outcome_max_error']<1e-12
 assert all(x is not None and x<1e-9 for x in v['permutation_max_errors'])
 for vals in v['observed'].values():assert all(x is not None and x<1e-9 for x in vals['max_errors'])
 draws=d['draws'];r={'case':d['case'],'geometry':d['geometry'],'null':d['nullKind'],'B':d['permutations'],'seconds':d['seconds'],'validation':v,'pool_validation':d['pool_validation'],'agent_observed_validation':d['agent_observed_validation'],'guarantee':d['guarantee'],'strata':d['strata'],'tests':{}}
 r['aggregate_validation']=aggregate_checks
 stats=np.array([x['stats'] for x in draws]);assert np.isfinite(stats).all()
 for j,name in enumerate(d['specNames']):r['tests'][name]={m:test(stats[:,j,k]) for k,m in enumerate(d['metrics'])}
 weights=np.array(d['weights']);active=weights>0;w=weights[active]
 obs=np.array(d['observedBifs'])[:,active];nullmean=np.array(d['nullBifSums'])[:,active]/d['permutations']
 rng=np.random.default_rng(642029);sel=rng.integers(0,len(w),(20000,len(w)));den=w[sel].sum(1)
 for m,name in enumerate(d['metrics']):
  t=r['tests']['full_all'][name]
  t['bif_bootstrap_observed_95']=np.quantile(obs[m,sel].sum(1)/den,[.025,.975]).tolist()
  t['bif_bootstrap_excess_95']=np.quantile((obs[m]-nullmean[m])[sel].sum(1)/den,[.025,.975]).tolist()
  t['bifolia_positive_observed']=int(np.sum(obs[m]>0));t['bifolia_positive_excess']=int(np.sum(obs[m]-nullmean[m]>0));t['bifolia_total']=len(w)
 r['past']={m:test([x['past'][i] for x in draws]) for i,m in enumerate(d['metrics'])}
 r['future']={m:test([x['future'][i] for x in draws]) for i,m in enumerate(d['metrics'])}
 r['regions']={}
 for region,n in d['regions'].items():
  if not n:continue
  r['regions'][region]={'n':n,'fraction_of_primary':n/weights.sum(),'tests':{m:test([x['regions'][region][i] for x in draws]) for i,m in enumerate(d['metrics'])}}
 r['bifolium_sufficient']={'names':d['bifNames'],'groups':d['bifGroup'],'weights':d['weights'],'observed':d['observedBifs'],'null_mean':(np.array(d['nullBifSums'])/d['permutations']).tolist()}
 return r

