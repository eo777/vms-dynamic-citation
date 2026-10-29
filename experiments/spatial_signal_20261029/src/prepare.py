import sys,json,hashlib,subprocess
from pathlib import Path
import numpy as np
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;O=P.parent/'runs';sys.path.insert(0,str(P/'source_snapshot'))
import data as D
import component_check as CC
import layout_shuffles as LS
from decompose import REFS,ref_words

def groups_of(unit,length):
 g={}
 for i,k in enumerate(zip(unit,length)):g.setdefault(k,[]).append(i)
 return [v for v in g.values() if len(v)>1]

def cellset(bif,length,n,base,bands=3,mincell=25,clip=False,pooled=False,cuts=None):
 if bands=='exact':bins=n.astype(int);edges=[]
 else:
  edges=np.percentile(n[base],[33,67] if bands==3 else [20,40,60,80]) if cuts is None else cuts
  bins=np.digitize(n,edges,right=not clip)
 ln=np.clip(length,2,9) if clip else length
 eligible=base.copy()
 if not clip:eligible&=(ln>=2)&(ln<=9)
 cells=[]
 for b in np.unique(bif[eligible]):
  mb=eligible&(bif==b)
  for l in np.unique(ln[mb]):
   ml=mb&(ln==l)
   for k in np.unique(bins[ml]):
    ix=np.flatnonzero(ml&(bins==k))
    if len(ix)>=mincell:cells.append({'b':int(b),'ix':ix.tolist()})
 mask=np.zeros(len(base),bool)
 for c in cells:mask[c['ix']]=True
 return {'mode':'pooled' if pooled else 'weighted','cells':cells,'n':int(mask.sum()),'bifolia':len(set(c['b'] for c in cells)),'cuts':np.asarray(edges).tolist()},mask

def prep(case,geometry):
 tag=case['id']+'__'+geometry
 plan=json.loads((P/'plan.json').read_text());ms=D.manuscript();app=CC.load_study_app('legacy');frames=CC.line_frames(app,ms)
 if case['kind']=='manuscript':raw=[list(l['words']) for l in ms['lines']];units=CC.zattera
 elif case['kind']=='copier':raw=D.read_stream(D.STREAMS[case['key']][1][0]);units=CC.zattera
 else:
  seq=ref_words(REFS[case['key']])[case['start']:case['start']+case['tokens']]
  assert len(seq)==case['tokens'] and hashlib.sha256(json.dumps(seq).encode()).hexdigest()==case['token_sha256']
  raw=[];at=0
  for l in ms['lines']:n=len(l['words']);raw.append(seq[at:at+n]);at+=n
  units=list
 seq=[w for ws in raw for w in ws];length=np.array([len(w) for w in seq]);par=np.repeat(LS.paragraph_of_line(ms),[len(w) for w in raw]);line=np.repeat(np.arange(len(raw)),[len(w) for w in raw])
 grouping=groups_of(par,length);linegroup=groups_of(line,length)
 placed=[x[:] for x in raw]
 if geometry=='synthetic':geom=CC.synthetic_geometry(placed,frames,ms)
 else:
  geom=app['geometry']
  if case['kind']=='prose':flags=CC.oversized_flags(app,ms);geom=[None if flags[i] else g for i,g in enumerate(geom)]
 assert [w for ws in placed for w in ws]==seq
 inp=CC.make_input(ms,placed,geom,units);inp['cursor']=case['cursor']
 pin=O/(tag+'-input.json');pex=O/(tag+'-export.json');pin.write_text(json.dumps(inp),encoding='utf8')
 subprocess.run(['node',str(P/'export.js'),str(pin),str(pex)],check=True)
 d=json.loads(pex.read_text(encoding='utf8'));pin.unlink();pex.unlink()
 ids=np.array(d['wordIds']);pair=np.array([bool(x) for x in d['features']]);certain=pair[ids].copy()
 for ix in grouping:certain[ix]=np.all(certain[ix])
 node,group,start,end=CC.token_meta(ms,placed);out=CC.outcomes(seq,start,end)
 names=sorted(set(node));lookup={n:i for i,n in enumerate(names)};bif=np.array([lookup[n] for n in node]);bifgroup={str(lookup[n]):str(group[np.flatnonzero(node==n)[0]]) for n in names}
 ns={};valid={};guarantee={}
 for shape,pools in d['pools'].items():
  ns[shape]=np.array([len(p[0]) for p in pools]);v=np.zeros(len(ids),bool)
  for i,(ix,w) in enumerate(pools):
   ix=np.array(ix,int);w=np.array(w,float);g=certain[ix];den=np.sum(w*w)
   v[i]=g.sum()>=5 and den>0 and np.sum(w[g])**2/den>=3
  valid[shape]=out['full']&v
  refs=np.array([np.nan if v is None else v for v in d['references'][shape]['h2']]);assert np.isfinite(refs[valid[shape]]).all()
  guarantee[shape]={'base':int(valid[shape].sum()),'original_valid':int((out['full']&np.isfinite(refs)).sum())}
 pos=np.concatenate([np.arange(len(w)) for w in placed]);ln=np.concatenate([np.full(len(w),len(w)) for w in placed]);inner=(pos>0)&(pos<ln-1)
 A=inner&(ns['full']>=15);B=inner&(ns['above']>=15);specs={}
 def add(name,shape,mask,bands=3,mincell=25,agent=False):
  v,_=cellset(bif,length,ns[shape],valid[shape]&mask,bands,mincell,agent,agent)
  v['shape']=shape;specs[name]=v
 allmask=np.ones(len(ids),bool)
 for name,shape,mask in [('full_all','full',allmask),('full_A','full',A),('full_B','full',B),('above_A','above',A),('above_B','above',B),('below_B','below',B)]:add(name,shape,mask)
 add('full_five','full',allmask,bands=5)
 add('full_exact_residual','full',allmask,bands='exact',mincell=2);specs['full_exact_residual']['mode']='residual'
 for name,shape,mask in [('agent_full_all','full',allmask),('agent_full_A','full',A),('agent_above_A','above',A),('agent_above_B','above',B)]:add(name,shape,mask,mincell=20,agent=True)
 if case['cursor']:
  common=valid['full']&valid['cursor'];cuts={s:np.percentile(ns[s][common],[33,67]) for s in ['full','cursor']}
  for _ in range(100):
   sets={s:cellset(bif,length,ns[s],common,cuts=cuts[s]) for s in ['full','cursor']};new=sets['full'][1]&sets['cursor'][1]
   if np.array_equal(new,common):break
   common=new
  else:raise RuntimeError('Cohort convergence')
  for s in ['full','cursor']:specs['common_'+s]={**sets[s][0],'shape':s}
  common=valid['full'];cuts3=np.percentile(ns['full'][common],[33,67]);cuts5=np.percentile(ns['full'][common],[20,40,60,80])
  for _ in range(100):
   c3,m3=cellset(bif,length,ns['full'],common,cuts=cuts3);c5,m5=cellset(bif,length,ns['full'],common,bands=5,cuts=cuts5);new=m3&m5
   if np.array_equal(new,common):break
   common=new
  for s,v in [('matched_three',c3),('matched_five',c5)]:specs[s]={**v,'shape':'full'}
 # Check that this synthetic setup does not change with the permitted substitutions.
 if geometry=='synthetic':
  trial=seq[:];rng=np.random.default_rng(642028)
  for ix in grouping:
   vals=[seq[i] for i in ix]
   for i,j in zip(ix,rng.permutation(len(ix))):trial[i]=vals[j]
  ls=[];at=0
  for ws in raw:ls.append(trial[at:at+len(ws)]);at+=len(ws)
  assert CC.synthetic_geometry(ls,frames,ms)==geom
 d.update({'case':case,'geometry':geometry,'groups':grouping,'lineGroups':linegroup,'bifNames':names,'bifGroup':bifgroup,'specs':specs,'referenceImpact':out['app_impact'].tolist(),'guarantee':guarantee,'geometry_sha256':hashlib.sha256(json.dumps(geom).encode()).hexdigest(),'token_sha256':hashlib.sha256(json.dumps(seq).encode()).hexdigest(),'plan_sha256':hashlib.sha256((P/'plan.json').read_bytes()).hexdigest()})
 d['agent_observed_validation']={'checked':0,'max_error':0}
 dest=O/(tag+'-prepared.json');dest.write_text(json.dumps(d,separators=(',',':')),encoding='utf8')
 meta={k:d[k] for k in ['case','geometry','guarantee','geometry_sha256','token_sha256','plan_sha256','agent_observed_validation','pool_validation']};meta['strata']={k:{kk:vv for kk,vv in v.items() if kk!='cells'} for k,v in specs.items()};meta['prepared_sha256']=hashlib.sha256(dest.read_bytes()).hexdigest()
 (O/(tag+'-metadata.json')).write_text(json.dumps(meta,indent=2));return dest,meta

if __name__=='__main__':
 O=Path(sys.argv[3]) if len(sys.argv)>3 else O;O.mkdir(parents=True,exist_ok=True)
 plan=json.loads((P/'plan.json').read_text());case=next(c for c in plan['cases'] if c['id']==sys.argv[1]);dest,meta=prep(case,sys.argv[2]);print(dest,meta['guarantee'],meta['agent_observed_validation'],flush=True)
