"use strict";
// Pure ranking functions: the population stays fixed when chart visibility changes.
const ComparisonMath=(()=>{
 function percentile(value,values){
  const a=values.filter(Number.isFinite);if(!Number.isFinite(value)||!a.length)return null;
  if(value===0)return 0; // An exact manuscript match is never coloured as a shortfall.
  if(a.length===1)return value<a[0]?0:value>a[0]?1:.5;
  const less=a.filter(x=>x<value-1e-9).length,equal=a.filter(x=>Math.abs(x-value)<=1e-9).length;
  return Math.max(0,Math.min(1,(less+(equal?((equal-1)/2):0))/(a.length-1)));
 }
 function ranking(C,scope='all',weights={},includeWords=false){
  const wordMetrics=C.metrics.filter(m=>m.family==='Word entropy');
  const eligible=run=>run.rank_eligible&&(!includeWords||wordMetrics.every(m=>run.metric_seed_count?.[m.key]===run.seeds.length));
  const familiesUsed=includeWords?[...C.families,'Word entropy']:C.families;
  const population=C.runs.filter(eligible),byMetric={};
  for(const m of C.metrics)byMetric[m.key]=population.map(r=>r.errors[scope][m.key]);
  const rows=C.runs.map(run=>{
   const metrics={},families={};
   for(const m of C.metrics)metrics[m.key]=percentile(run.errors[scope][m.key],byMetric[m.key]);
   for(const f of familiesUsed){const v=C.metrics.filter(m=>(m.rank||(includeWords&&m.family==='Word entropy'))&&m.family===f).map(m=>metrics[m.key]).filter(Number.isFinite);families[f]=v.length?v.reduce((a,b)=>a+b,0)/v.length:null;}
   let total=0,denom=0;for(const f of familiesUsed){const w=weights[f]??1;if(w>0&&Number.isFinite(families[f])){total+=families[f]*w;denom+=w;}}
   return {run,metrics,families,score:eligible(run)&&denom?100*total/denom:null,rank:null};
  }).sort((a,b)=>(a.score??Infinity)-(b.score??Infinity)||a.run.label.localeCompare(b.run.label));
  rows.forEach((r,i)=>{if(r.score!=null)r.rank=i&&Math.abs(r.score-rows[i-1].score)<1e-9?rows[i-1].rank:i+1;});
  return rows;
 }
 function inScope(node,scope){return scope==='all'||(scope==='nonbio'&&node.group!=='4a')||node.group===scope;}
 function weighted(values,nodes,scope='all'){let s=0,n=0;values.forEach((v,i)=>{if(inScope(nodes[i],scope)&&Number.isFinite(v)){s+=v*nodes[i].N;n+=nodes[i].N;}});return n?s/n:null;}
 if(typeof module!=='undefined')module.exports={percentile,ranking,weighted,inScope};
 return {percentile,ranking,weighted,inScope};
})();
