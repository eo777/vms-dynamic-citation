'use strict';
const fs=require('fs'),path=require('path');
const [input,output,barg,nullKind='paragraph']=process.argv.slice(2),B=Number(barg),d=JSON.parse(fs.readFileSync(input,'utf8'));
const N=d.wordIds.length,K=d.words.length,original=Int32Array.from(d.wordIds),ids=Int32Array.from(original),groups=nullKind==='line'?d.lineGroups:d.groups;
const metrics=['components','h2','worddiv'],shapes=Object.keys(d.pools),specNames=Object.keys(d.specs);
const specs=specNames.map(name=>({...d.specs[name],name,cells:d.specs[name].cells.map(c=>({b:c.b,ix:Int32Array.from(c.ix)}))}));
const targets={},pools={},scores={};
for(const shape of shapes){
 targets[shape]=Int32Array.from([...new Set(specs.filter(s=>s.shape===shape).flatMap(s=>s.cells.flatMap(c=>Array.from(c.ix))))].sort((a,b)=>a-b));
 pools[shape]=d.pools[shape].map(([i,w])=>({i:Int32Array.from(i),w:Float64Array.from(w)}));
 scores[shape]=metrics.map(()=>new Float64Array(N));
}
const allTargets=Int32Array.from([...new Set(shapes.flatMap(s=>Array.from(targets[s])))].sort((a,b)=>a-b));
const last=new Int32Array(K),prev=new Int32Array(N),next=new Int32Array(N),impact=new Float64Array(N),past=new Float64Array(N),future=new Float64Array(N);
const pair=new Float64Array(d.pairLeft.length),left=new Float64Array(d.unitCount),types=new Float64Array(K),touchedP=new Int32Array(pair.length),touchedL=new Int32Array(left.length),touchedT=new Int32Array(K);
const fi=d.features.map(a=>Int32Array.from(a.map(x=>x[0]))),fv=d.features.map(a=>Float64Array.from(a.map(x=>x[1])));
let state=(nullKind==='line'?742028:642028)>>>0;
function random(){state=(state+0x6D2B79F5)>>>0;let t=state;t=Math.imul(t^(t>>>15),t|1);t^=t+Math.imul(t^(t>>>7),t|61);return ((t^(t>>>14))>>>0)/4294967296;}
function shuffle(){ids.set(original);for(const g of groups)for(let j=g.length-1;j>0;j--){const k=Math.floor(random()*(j+1)),a=g[j],b=g[k],tmp=ids[a];ids[a]=ids[b];ids[b]=tmp;}}
function measure(){
 for(const shape of shapes){const sc=scores[shape];
  for(const target of targets[shape]){
   let np=0,nl=0,nt=0,mass=0,total=0;const p=pools[shape][target];
   for(let q=0;q<p.i.length;q++){
    const id=ids[p.i[q]],ix=fi[id],v=fv[id],w=p.w[q];total+=w;if(types[id]===0)touchedT[nt++]=id;types[id]+=w;
    for(let k=0;k<ix.length;k++){const j=ix[k],l=d.pairLeft[j],add=w*v[k];if(pair[j]===0)touchedP[np++]=j;if(left[l]===0)touchedL[nl++]=l;pair[j]+=add;left[l]+=add;mass+=add;}
   }
   let hp=0,hl=0,col=0;
   for(let k=0;k<np;k++){const j=touchedP[k],v=pair[j];hp+=v*Math.log2(v);pair[j]=0;}
   for(let k=0;k<nl;k++){const j=touchedL[k],v=left[j];hl+=v*Math.log2(v);left[j]=0;}
   for(let k=0;k<nt;k++){const j=touchedT[k];col+=types[j]*types[j];types[j]=0;}
   sc[0][target]=Math.round(2**(Math.log2(mass)-hp/mass)*1e10)/1e10;sc[1][target]=Math.round(Math.max(0,(hl-hp)/mass)*1e10)/1e10;sc[2][target]=Math.round(Math.max(0,1-col/(total*total))*1e10)/1e10;
  }
 }
}
function outcomes(){
 last.fill(-1);next.fill(N);
 for(let i=0;i<N;i++){const p=last[ids[i]];prev[i]=p;if(p>=0)next[p]=i;last[ids[i]]=i;}
 for(const i of allTargets){const unique=Math.max(0,Math.min(i,next[i]-100)-Math.max(i-99,prev[i]+1)+1);impact[i]=(100-unique)/100;past[i]=prev[i]>=0&&i-prev[i]<=99?1:0;future[i]=next[i]<N&&next[i]-i<=99?1:0;}
}
function qtile(a,p){const z=(a.length-1)*p,j=Math.floor(z),v=z-j,lo=a[j],hi=a[Math.min(j+1,a.length-1)];return v>=.5?hi-(hi-lo)*(1-v):lo+(hi-lo)*v;}
const weights=new Float64Array(d.bifNames.length);for(const c of d.specs.full_all.cells)weights[c.b]+=c.ix.length;
function contrast(spec){
 const values=[],primary=spec.name==='full_all',bifs=primary?metrics.map(()=>new Float64Array(weights.length)):null,ps=[],fu=[];
 for(let m=0;m<3;m++){
  const x=scores[spec.shape][m];let numerator=0,denominator=0,ls=0,ln=0,hs=0,hn=0,pastSum=0,futureSum=0,xx=0,xy=0,yy=0;
  for(const c of spec.cells){
   if(spec.mode==='residual'){
    let mx=0,my=0;for(const i of c.ix){mx+=x[i];my+=impact[i];}mx/=c.ix.length;my/=c.ix.length;
    for(const i of c.ix){const dx=x[i]-mx,dy=impact[i]-my;xx+=dx*dx;xy+=dx*dy;yy+=dy*dy;}continue;
   }
   const sorted=Float64Array.from(c.ix,i=>x[i]);sorted.sort();const lo=qtile(sorted,.2),hi=qtile(sorted,.8);
   let l=0,h=0,nl=0,nh=0,pl=0,ph=0,fl=0,fh=0;
   for(const i of c.ix){
    if(x[i]<=lo){l+=impact[i];nl++;if(primary){pl+=past[i];fl+=future[i];}}
    if(x[i]>=hi){h+=impact[i];nh++;if(primary){ph+=past[i];fh+=future[i];}}
   }
   const n=c.ix.length,v=n*(l/nl-h/nh);numerator+=v;denominator+=n;ls+=l;ln+=nl;hs+=h;hn+=nh;
   if(primary){bifs[m][c.b]+=v;pastSum+=n*(pl/nl-ph/nh);futureSum+=n*(fl/nl-fh/nh);}
  }
  values.push(spec.mode==='residual'?-xy/Math.sqrt(xx*yy):spec.mode==='pooled'?ls/ln-hs/hn:numerator/denominator);
  if(primary){ps.push(pastSum/denominator);fu.push(futureSum/denominator);}
 }
 return {values,bifs,past:ps,future:fu};
}
measure();outcomes();const validation={observed:{},permutation_checks:0,permutation_max_errors:[0,0,0],outcome_max_error:0};
for(const s of shapes){const errs=[0,0,0];for(let m=0;m<3;m++)for(const i of targets[s])errs[m]=Math.max(errs[m],Math.abs(scores[s][m][i]-d.references[s][metrics[m]][i]));if(Math.max(...errs)>1e-9)throw Error('Observed score mismatch '+s+' '+errs);validation.observed[s]={targets:targets[s].length,max_errors:errs};}
for(const i of allTargets)validation.outcome_max_error=Math.max(validation.outcome_max_error,Math.abs(impact[i]-d.referenceImpact[i]));if(validation.outcome_max_error>1e-12)throw Error('Outcome mismatch');
const S=require(path.join(__dirname,'source_snapshot','component_source_math.js'));
const aggregateReferences=[];
function validateDraw(b){
 const ctx={data:{words:Array.from(ids)},tokenFeatures:Array.from(ids,id=>({pairs:d.features[id],mono:[]})),unitNames:new Array(d.unitCount),pairNames:new Array(pair.length),pairLeft:d.pairLeft,baseline:new Float64Array(pair.length).fill(1)};
 const fullRefs=Object.fromEntries(shapes.map(s=>[s,Object.fromEntries(metrics.map(m=>[m,new Array(N).fill(null)]))]));
 for(const s of shapes)for(let k=0;k<targets[s].length;k++){
  const i=targets[s][k],p=pools[s][i],ref=S.measure(ctx,{indices:Array.from(p.i),weights:Array.from(p.w),available:p.i.length});
  for(let m=0;m<3;m++){validation.permutation_max_errors[m]=Math.max(validation.permutation_max_errors[m],Math.abs(ref[metrics[m]]-scores[s][m][i]));fullRefs[s][metrics[m]][i]=ref[metrics[m]];}
 }
 for(let k=0;k<40;k++){
  const i=allTargets[Math.floor(k*allTargets.length/40)];let repeats=0;
  for(let a=i-99;a<=i;a++){let count=0;for(let j=a;j<a+100;j++)if(ids[j]===ids[i])count++;if(count>1)repeats++;}
  validation.outcome_max_error=Math.max(validation.outcome_max_error,Math.abs(repeats/100-impact[i]));
 }
 validation.permutation_checks+=shapes.reduce((a,s)=>a+targets[s].length,0);
 aggregateReferences.push({draw:b,references:fullRefs,impact:Array.from(impact)});
 fs.writeFileSync(output.replace('.json','-reference-checks.json'),JSON.stringify(aggregateReferences));
 if(Math.max(...validation.permutation_max_errors)>1e-9||validation.outcome_max_error>1e-12)throw Error('Shuffled validation failed');
}
const regionDefs={'Stars':['3c','4c'],'Bio':['4a'],'Herbal_A':['1a','1b','1.5a'],'Herbal_B':['3a','3b']};
const regions=Object.fromEntries(Object.entries(regionDefs).map(([name,groups])=>[name,Array.from(weights,(_,i)=>i).filter(i=>groups.includes(d.bifGroup[String(i)])&&weights[i]>0)]));
regions.without_Stars=Array.from(weights,(_,i)=>i).filter(i=>!regionDefs.Stars.includes(d.bifGroup[String(i)])&&weights[i]>0);
const regionWeights=Object.fromEntries(Object.entries(regions).map(([k,ix])=>[k,ix.reduce((s,i)=>s+weights[i],0)]));
const result={case:d.case,geometry:d.geometry,nullKind,permutations:B,seed:nullKind==='line'?742028:642028,plan_sha256:d.plan_sha256,pool_validation:d.pool_validation,agent_observed_validation:d.agent_observed_validation,validation,guarantee:d.guarantee,specNames,metrics,strata:Object.fromEntries(specs.map(s=>[s.name,{shape:s.shape,mode:s.mode,n:s.n,bifolia:s.bifolia,cuts:s.cuts,cells:s.cells.length}])),bifNames:d.bifNames,bifGroup:d.bifGroup,weights:Array.from(weights),regions:regionWeights,nullBifSums:metrics.map(()=>new Array(weights.length).fill(0)),draws:[]};
const begin=Date.now();
for(let b=0;b<=B;b++){
 if(b){shuffle();measure();outcomes();}
 if(b===1||b===B)validateDraw(b);
 let primary;const stats=specs.map(s=>{const r=contrast(s);if(s.name==='full_all')primary=r;return r.values;});
 const regionScores=Object.fromEntries(Object.entries(regions).map(([name,ix])=>[name,metrics.map((_,m)=>ix.reduce((sum,i)=>sum+primary.bifs[m][i],0)/regionWeights[name])]));
 if(b===0)result.observedBifs=primary.bifs.map(a=>Array.from(a));
 else for(let m=0;m<3;m++)for(let i=0;i<weights.length;i++)result.nullBifSums[m][i]+=primary.bifs[m][i];
 result.draws.push({stats,past:primary.past,future:primary.future,regions:regionScores});
 if(b===0||b%100===0||b===B){result.completed=b;result.seconds=(Date.now()-begin)/1000;fs.writeFileSync(output,JSON.stringify(result));console.log(JSON.stringify({case:d.case.id,geometry:d.geometry,null:nullKind,completed:b,total:B,seconds:result.seconds}));}
}
