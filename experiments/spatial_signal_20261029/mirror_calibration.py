"""Reproduce a known-copier calibration of the original full mirror statistic.
This is the older within-bifolium contrast, NOT the new jointly controlled H2 test.
It checks whether an approximately 2.5 upstream/downstream ratio is universal.
"""
import json,subprocess,sys,tempfile
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'/'source_snapshot'))
import data as D,component_check as CC

def contrast(x,y,bif,mask):
 sums=np.zeros(4)
 for b in np.unique(bif[mask]):
  ix=mask&(bif==b)&np.isfinite(x)&np.isfinite(y)
  if ix.sum()<25:continue
  a,v=x[ix],y[ix];lo,hi=np.quantile(a,[.2,.8]);L,H=v[a<=lo],v[a>=hi]
  sums += [L.sum(),len(L),H.sum(),len(H)]
 return float(sums[0]/sums[1]-sums[2]/sums[3])

def main():
 expected=json.loads((ROOT/'expected_mirror_calibration.json').read_text(encoding='utf8'))
 ms=D.manuscript();app=CC.load_study_app('legacy');frames=CC.line_frames(app,ms)
 found={}
 for key in expected:
  if key=='manuscript':lines=[list(l['words']) for l in ms['lines']];geom=app['geometry']
  else:
   lines=D.read_stream(D.src('research/dynamic_selfcitation_20261024/governed/runs/p_noinnov_spatial_s2/generated_text.txt'))
   geom=CC.synthetic_geometry(lines,frames,ms)
  inp=CC.make_input(ms,lines,geom,CC.zattera)
  with tempfile.TemporaryDirectory() as folder:
   folder=Path(folder);pin=folder/'input.json';out=folder/'out.json';pin.write_text(json.dumps(inp),encoding='utf8')
   subprocess.run(['node',str(ROOT/'src'/'source_snapshot'/'direction_measure.js'),str(pin),str(out)],check=True)
   M={k:np.array([np.nan if x is None else x for x in v]) for k,v in json.loads(out.read_text(encoding='utf8')).items()}
  node,group,start,end=CC.token_meta(ms,lines);Y=CC.outcomes(inp['words'],start,end);mask=Y['full'].copy()
  for direction in ['up','dn']:
   for m in ['components','h2','worddiv']:mask &= np.isfinite(M[direction+'_'+m])
  found[key]={}
  for metric in ['components','h2','worddiv']:
   up=contrast(M['up_'+metric],Y['app_impact'],node,mask);dn=contrast(M['dn_'+metric],Y['app_impact'],node,mask)
   row={'up':up,'dn':dn,'diff':up-dn};found[key][metric]=row
   for name,value in row.items():assert abs(value-expected[key][metric][name])<1e-12,(key,metric,name,value)
  print(key,json.dumps(found[key]),flush=True)
 print('PASS: the saved spatial copier has an approximately symmetric component contrast. This is a calibration counterexample, not a new adjusted directional test.',flush=True)
if __name__=='__main__':main()
