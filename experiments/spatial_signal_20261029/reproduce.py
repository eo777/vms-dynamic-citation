"""Portable reproduction: input checks, fixed-seed runs, independent validation.
No network access, model generation, absolute source paths or internal logs needed.
"""
from pathlib import Path
import argparse,concurrent.futures,gzip,hashlib,json,math,platform,shutil,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parent
SRC=ROOT/'src'
sys.path.insert(0,str(SRC))
sys.path.insert(0,str(SRC/'source_snapshot'))
import numpy as np
import scipy
import component_check as CC
import validate_aggregate as VA
import summary_math as SM

def read(p):return json.loads(p.read_text(encoding='utf8'))
def write(p,d):p.write_text(json.dumps(d,indent=2,ensure_ascii=True),encoding='utf8')
def same(a,b,path='value',tol=1e-10):
 if isinstance(a,dict):
  assert isinstance(b,dict) and set(a)==set(b),path+' keys'
  for k in a:same(a[k],b[k],path+'.'+k,tol)
 elif isinstance(a,list):
  assert isinstance(b,list) and len(a)==len(b),path+' length'
  for i,(x,y) in enumerate(zip(a,b)):same(x,y,path+f'[{i}]',tol)
 elif isinstance(a,(float,int)) and not isinstance(a,bool):
  assert isinstance(b,(float,int)) and math.isfinite(a) and math.isfinite(b) and abs(a-b)<=tol,(path,a,b)
 else:assert a==b,(path,a,b)

def verify_files():
 manifest=read(ROOT/'input_manifest.json')
 if (ROOT/'kit_manifest.json').exists():manifest.update(read(ROOT/'kit_manifest.json')['files'])
 for rel,meta in manifest.items():
  p=ROOT/rel
  assert p.is_file(),f'Missing frozen input/code: {rel}'
  assert hashlib.sha256(p.read_bytes()).hexdigest()==meta['sha256'],f'Changed frozen input/code: {rel}'
 return len(manifest)

def call(args):
 r=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf8',errors='replace')
 if r.returncode:raise RuntimeError('Command failed: '+' '.join(map(str,args))+'\n'+r.stdout[-5000:]+'\n'+r.stderr[-5000:])

def outcomes(prepared,result,kind,B):
 d=read(prepared);refs=read(result.with_name(result.stem+'-reference-checks.json'));ids=result.with_name(result.stem+'-ids.json')
 call(['node',str(SRC/'replay_ids.js'),str(prepared),str(ids),kind,str(B)])
 targets=sorted(set(i for s in d['specs'].values() for c in s['cells'] for i in c['ix']))
 checks=[]
 for entry,reference in zip(read(ids),refs):
  assert entry['draw']==reference['draw']
  words=entry['ids'];n=len(words)
  y=CC.outcomes(words,np.zeros(n,int),np.full(n,n,int))['app_impact']
  err=float(np.max(np.abs(y[targets]-np.array(reference['impact'])[targets])))
  assert err<1e-12,('independent outcome mismatch',entry['draw'],err)
  checks.append({'draw':entry['draw'],'targets':len(targets),'maximum_error':err})
 return checks

def compare_summary(actual,expected):
 for family in ['tests','past','future']:
  aa=actual[family];ee=expected[family]
  if family=='tests':pairs=[(aa[spec][metric],ee[spec][metric]) for spec in ee for metric in ee[spec]]
  else:pairs=[(aa[m],ee[m]) for m in ee]
  for a,e in pairs:
   fields=[k for k in e if not k.startswith('holm_')]
   same({k:a[k] for k in fields},{k:e[k] for k in fields},family)
 same(actual['strata'],expected['strata'],'strata')
 same(actual['regions'],expected['regions'],'regions')

def run_case(case,geo,args,expected,checkpoints):
 kinds=[('paragraph',case['draws'])]+([('line',999)] if case['line_null'] else [])
 tag=case['id']+'__'+geo;out=[]
 print('Preparing '+tag,flush=True)
 # Only new temporary arrays are removed; compact draws and validated results survive.
 with tempfile.TemporaryDirectory(prefix=tag+'-',dir=args.output) as tmp:
  tmp=Path(tmp);shutil.copyfile(SRC/'plan.json',tmp/'plan.json')
  call([sys.executable,str(SRC/'prepare.py'),case['id'],geo,str(tmp)])
  prepared=tmp/(tag+'-prepared.json')
  for kind,total in kinds:
   B=19 if args.smoke else total;key=tag+'-'+kind;result=tmp/(key+'.json')
   call(['node',str(SRC/'run.js'),str(prepared),str(result),str(B),kind])
   r=read(result);assert r['completed']==B and r['permutations']==B
   expected_points=checkpoints[key]
   same(r['specNames'],expected_points['specNames'],'specNames')
   same(r['strata'],expected_points['strata'],'strata')
   for b in [0,1,19]+([] if args.smoke else [B]):same(r['draws'][b],expected_points['draws'][str(b)],key+f' draw {b}')
   aggregate=[VA.check(prepared,result)]
   for e in read(result.with_name(result.stem+'-reference-checks.json')):aggregate.append(VA.check(prepared,result,e['references'],e['impact'],e['draw']))
   assert all(c['max_difference']<1e-10 and not c['differences'] for c in aggregate),aggregate
   write(result.with_name(result.stem+'-aggregate-validation.json'),aggregate)
   outcome_checks=outcomes(prepared,result,kind,B)
   summary=SM.summary(r,tmp)
   if not args.smoke:compare_summary(summary,expected[key])
   retained={k:summary[k] for k in ['case','geometry','null','B','strata','tests','regions','past','future']}
   retained['verification']={'checkpoints_match':True,'all_statistics_match_full_reference':not args.smoke,'aggregate_max_error':max(c['max_difference'] for c in aggregate),'outcomes':outcome_checks}
   write(args.output/(key+'.json'),retained)
   with result.open('rb') as source,gzip.open(args.output/(key+'-draws.json.gz'),'wb') as dest:shutil.copyfileobj(source,dest)
   out.append((key,retained));print('PASS '+key+f' ({B} shuffles'+('; smoke check only)' if args.smoke else ')'),flush=True)
 return out

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--suite',choices=['manuscript','rhazes','all'],default='manuscript')
 p.add_argument('--smoke',action='store_true',help='19-draw exact checkpoint/independent-score check, not inference')
 p.add_argument('--verify-only',action='store_true',help='Verify bundled input/code hashes without running shuffles')
 p.add_argument('--jobs',type=int,default=2)
 p.add_argument('--output',type=Path)
 args=p.parse_args();assert 1<=args.jobs<=4,'Use 1 to 4 jobs.'
 count=verify_files();print(f'Frozen files verified: {count}',flush=True)
 if args.verify_only:return
 args.output=(args.output or ROOT/'runs'/('smoke' if args.smoke else 'full')).resolve();args.output.mkdir(parents=True,exist_ok=True)
 assert args.output!=ROOT and args.output!=SRC and args.output!=ROOT/'inputs'
 plan=read(SRC/'plan.json');expected=read(ROOT/'expected_results.json');checkpoints=read(ROOT/'expected_checkpoints.json')
 cases=[c for c in plan['cases'] if args.suite=='all' or args.suite=='manuscript' and c['id']=='manuscript' or args.suite=='rhazes' and c['id'] in ['la_rhazes_almansor','rhazes_start16785']]
 results={}
 with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as ex:
  tasks=[ex.submit(run_case,c,g,args,expected,checkpoints) for c in cases for g in c['geometries']]
  for f in concurrent.futures.as_completed(tasks):results.update(f.result())
 if not args.smoke:
  def adjust(keys,specs,label):
   if not all(k in results for k in keys):return
   tests=[results[k]['tests'][sp][m] for k in keys for sp in specs for m in ['components','h2']]
   SM.holm(tests,label)
   for k in keys:
    for sp in specs:
     for m in ['components','h2']:same(results[k]['tests'][sp][m][label],expected[k]['tests'][sp][m][label],label)
  adjust(['manuscript__'+g+'-paragraph' for g in ['recorded','synthetic']],['full_all'],'holm_primary4')
  adjust(['manuscript__'+g+'-line' for g in ['recorded','synthetic']],['full_all'],'holm_manuscript_line4')
  hist=[c['id']+'__'+g+'-paragraph' for c in plan['cases'] if c['kind']=='prose' for g in c['geometries']]
  adjust(hist,['full_all'],'holm_historical_full24');adjust(hist,['above_A','above_B'],'holm_historical_above48')
 write(args.output/'results.json',{'smoke_only':args.smoke,'runtime':{'python':sys.version,'numpy':np.__version__,'scipy':scipy.__version__,'platform':platform.platform(),'node':subprocess.check_output(['node','--version'],text=True).strip()},'results':results})
 print('All requested runs passed. '+('Smoke output is not a significance test.' if args.smoke else 'Full statistics match the frozen reference.'),flush=True)

if __name__=='__main__':main()
