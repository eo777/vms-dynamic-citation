"""Check complete observed contrasts against independent NumPy quantiles on source-library scores."""
import json,sys
from pathlib import Path
import numpy as np
P=Path(__file__).resolve().parent
def check(prepared,result,references=None,impact=None,draw=0):
 d=json.loads(prepared.read_text());r=json.loads(result.read_text());y=np.array(d['referenceImpact'] if impact is None else impact);largest=0;details=[]
 refs=d['references'] if references is None else references
 for name,s in d['specs'].items():
  j=r['specNames'].index(name)
  for k,m in enumerate(r['metrics']):
   x=np.array([np.nan if v is None else v for v in refs[s['shape']][m]])
   x=np.floor(x*1e10+0.5)/1e10
   numerator=den=ls=ln=hs=hn=xx=xy=yy=0
   for c in s['cells']:
    ix=np.array(c['ix']);a,b=x[ix],y[ix]
    if s['mode']=='residual':
     dx=a-a.mean();dy=b-b.mean();xx+=sum(dx*dx);xy+=sum(dx*dy);yy+=sum(dy*dy);continue
    lo,hi=np.quantile(a,[.2,.8]);L,H=b[a<=lo],b[a>=hi]
    numerator+=len(ix)*(L.mean()-H.mean());den+=len(ix);ls+=L.sum();ln+=len(L);hs+=H.sum();hn+=len(H)
   val=-xy/np.sqrt(xx*yy) if s['mode']=='residual' else ls/ln-hs/hn if s['mode']=='pooled' else numerator/den
   assert np.isfinite(val), (name,m,draw)
   err=abs(val-r['draws'][draw]['stats'][j][k]);largest=max(largest,err)
   if err>1e-10:details.append({'spec':name,'metric':m,'source':float(val),'fast':r['draws'][draw]['stats'][j][k],'difference':float(err)})
 return {'dataset':prepared.name,'draw':draw,'max_difference':float(largest),'differences':details}
if __name__=='__main__':
 prepared=Path(sys.argv[1]);result=Path(sys.argv[2])
 checks=[check(prepared,result)]
 for entry in json.loads(result.with_name(result.stem+'-reference-checks.json').read_text()):
  checks.append(check(prepared,result,entry['references'],entry['impact'],entry['draw']))
 dest=result.with_name(result.stem+'-aggregate-validation.json')
 dest.write_text(json.dumps(checks,indent=2));print(json.dumps(checks,indent=2))
 assert all(c['max_difference']<1e-10 for c in checks), 'Aggregate validation failed'
