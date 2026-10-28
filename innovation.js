"use strict";
(async()=>{
const {$,esc,fmt,int,pct,signed,finite,mean,load,lineChart,legend,cmpRows,attachTips,error}=SG;
const SLOTS=['page-first','paragraph-first','paragraph-line','line-first','line-final','interior'];
try{
 const S=await SC.statistics();
 const runs=SG.visibleRuns(S.runs),obs=S.streams.observed.profile;
 const seeds=id=>runs.find(r=>r.id===id).seeds.map(s=>S.streams[s]);
 const prof=id=>seeds(id).map(s=>s.profile);
 const agg=(arr)=>{const f=arr.filter(finite);return f.length?{m:mean(f),lo:Math.min(...f),hi:Math.max(...f)}:null;};
 const rng=(id,get)=>agg(prof(id).map(get));
 const show=(a,d=1,suffix='')=>a?(a.lo===a.hi?fmt(a.m,d)+suffix:`${fmt(a.m,d)}${suffix} <span class="muted small" title="half the spread of the seeds: ${fmt(a.lo,d)}–${fmt(a.hi,d)}">±${fmt((a.hi-a.lo)/2,d)}</span>`):'—';
 const main=$('main');let html='';
 html+=`<section class="panel" id="mechanisms"><h2>What is enabled</h2>${SC.mechanismTable(runs)}${SC.mechanismNote()}<p><a href="comparison.html">Compare all methods, rankings, entropy, and highlighted text examples.</a></p></section>`;
 // ---- A. headline metrics
 const M=[['Distinct forms',p=>p.types,0,''],['First appearances per 1,000, first 10,000 tokens',p=>p.new_per_1000_first10k,0,''],['First appearances per 1,000, last 10,000 scored tokens',p=>p.new_per_1000_last10k,0,''],
  ['New forms reused within 1,000 tokens',p=>100*p.reused_within_1000,1,'%'],['Manuscript hapaxes reproduced',p=>p.hapax_reproduced,0,''],['Tokens with a spelling absent from the manuscript',p=>100*(p.unseen_token_share||0),1,'%'],['Identical adjacent words within lines and bifolia',p=>100*p.interval_repeat_rate,2,'%'],['Words in degenerate stretches (rolling diversity below 0.5)',p=>100*(p.degenerate_share||0),2,'%'],['Lines touched by a degenerate stretch',p=>p.degenerate_lines||0,0,'']];
 html+=`<section class="panel"><h2>Headline</h2><div class="table-wrap"><table><thead><tr><th>Measure</th><th class="num">Observed</th>${runs.map(r=>`<th class="num">${SG.runName(r,r.short)}</th>`).join('')}</tr></thead><tbody>${M.map(([l,g,d,s])=>`<tr><td>${esc(l)}</td><td class="num">${l.startsWith('Tokens with')?'0%':fmt(g(obs),d)+s}</td>${runs.map(r=>`<td class="num">${show(rng(r.id,g),d,s)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>
 <p class="chart-note">Hapaxes: of the manuscript's ${int(obs.hapax_total)} once-only spellings, how many appear in the run's scored text. Each column averages its available completed seeds; ranges are shown when there is more than one. Reuse follow-up ends at token 34,977 for every stream, so late births have less follow-up. Line histograms use complete lines within that same budget.</p></section>`;
 // ---- B. first appearances along the path
 const labels=S.nodes,groups=S.node_groups;
 const series=[{label:'Observed',color:'var(--obs)',values:obs.new_by_node,width:2.4}];
 for(const r of runs){const P=prof(r.id);const vals=labels.map((_,i)=>mean(P.map(p=>p.new_by_node[i])));const s={label:r.label,color:r.color,values:vals};if(P.length>1)s.band=[labels.map((_,i)=>Math.min(...P.map(p=>p.new_by_node[i]))),labels.map((_,i)=>Math.max(...P.map(p=>p.new_by_node[i])))];series.push(s);}
 html+=`<section class="panel"><div class="row" style="justify-content:space-between"><h2>First appearances per 1,000 tokens, by bifolium</h2>${legend(series)}</div>${lineChart(series,labels,{groups,height:260,title:'First appearances per 1,000 tokens by bifolium',tipDigits:0})}<p class="chart-note">A first appearance is a spelling not seen earlier in the same text. The observed curve is also the innovator's novelty target (scaled per slot).</p></section>`;
 // ---- C. slots
 const slotRows=(get,format)=>SLOTS.map(sl=>({label:sl,obs:get(obs.slots[sl]),values:runs.map(r=>{const a=rng(r.id,p=>get(p.slots[sl]));return {v:a?a.m:NaN,color:r.color,label:r.label+(a&&a.lo!==a.hi?` (${format(a.lo)}–${format(a.hi)})`:'')};})}));
 html+=`<section class="panel"><h2>By slot <span class="n">position of the word on its line</span></h2><div class="grid3">
  <div><h3>Share of tokens that are first appearances</h3>${cmpRows(slotRows(x=>100*x.rate,v=>fmt(v,0)+'%'),{format:v=>fmt(v,0)+'%'})}</div>
  <div><h3>Mean length of new forms, units</h3>${cmpRows(slotRows(x=>x.mean_units,v=>fmt(v,2)),{format:v=>fmt(v,2)})}</div>
  <div><h3>New forms that start with a gallows (k t p f)</h3>${cmpRows(slotRows(x=>100*x.gallows_initial,v=>fmt(v,0)+'%'),{format:v=>fmt(v,0)+'%'})}</div></div>
  <p class="chart-note">Tick: observed. Slots: page-first and paragraph-first are the first word of a page or paragraph; paragraph-line, the rest of a paragraph's first line; line-final, the last word of a line. Units are Zattera's slot alphabet (ch, sh, benched gallows and e/i runs count as one).</p></section>`;
 // ---- D. shape
 const shapeRows=[['Mean length, units',p=>p.shape.mean_units,v=>fmt(v,2)],['Six units or more',p=>100*p.shape.ge6,v=>fmt(v,0)+'%'],['A word-final unit inside the word',p=>100*p.shape.interior_final_unit,v=>fmt(v,0)+'%'],
  ['l- or r-initial',p=>100*p.shape.l_or_r_initial,v=>fmt(v,1)+'%'],['Gallows-initial',p=>100*p.shape.gallows_initial,v=>fmt(v,0)+'%'],['Two earlier words joined',p=>100*p.shape.join_share,v=>fmt(v,0)+'%'],['… of which one part is a single unit',p=>100*p.shape.join_one_unit_share,v=>fmt(v,0)+'%'],
  ['Spelling absent from the manuscript',p=>100*p.unseen_type_share,v=>fmt(v,0)+'%'],['p- or f-initial at paragraph starts (all tokens)',p=>100*(p.slots['paragraph-first'].pf_initial??NaN),v=>fmt(v,0)+'%'],['p- or f-initial at page starts (all tokens)',p=>100*(p.slots['page-first'].pf_initial??NaN),v=>fmt(v,0)+'%']];
 html+=`<section class="panel"><h2>Shape of the new forms</h2><div class="table-wrap"><table><thead><tr><th></th><th class="num">Observed</th>${runs.map(r=>`<th class="num">${SG.runName(r,r.short)}</th>`).join('')}</tr></thead><tbody>${shapeRows.map(([l,g,f])=>`<tr><td>${esc(l)}</td><td class="num">${l.startsWith('Spelling absent')?'0%':f(g(obs))}</td>${runs.map(r=>{const a=rng(r.id,g);return `<td class="num">${a?(a.lo===a.hi?f(a.m):`${f(a.m)} <span class="muted small">(${f(a.lo)}–${f(a.hi)})</span>`):'—'}</td>`;}).join('')}</tr>`).join('')}</tbody></table></div>
 <p class="chart-note">Over the distinct new forms of the scored text. A join is a new form that splits into two spellings both seen earlier.</p></section>`;
 // ---- E. word length distribution
 const lens=[...Array(12).keys()].map(i=>String(i+1));lens[11]='12+';
 const lenSeries=[{label:'Observed',color:'var(--obs)',values:obs.length_distribution.map(v=>100*v/obs.tokens),width:2.4},...runs.map(r=>{const P=prof(r.id);return {label:r.label,color:r.color,values:lens.map((_,i)=>mean(P.map(p=>100*p.length_distribution[i]/p.tokens)))};})];
 html+=`<section class="panel"><div class="row" style="justify-content:space-between"><h2>Word length, units <span class="n">share of tokens</span></h2>${legend(lenSeries)}</div>${lineChart(lenSeries,lens,{height:200,unit:'%',title:'Word length distribution',tipDigits:1,ticks:12})}</section>`;
 // ---- F. innovator and decisions
 for(const r of runs){
  const dec=S.streams[r.seeds[0]].decisions;if(!dec)continue;
  const I=dec.innovator,types=Object.entries(dec.by_type).sort((a,b)=>Object.values(b[1]).reduce((x,y)=>x+y,0)-Object.values(a[1]).reduce((x,y)=>x+y,0));
  const total=k=>Object.values(k).reduce((x,y)=>x+y,0);
  html+=`<section class="panel"><h2>${SG.runName(r)} <span class="n">decisions of the main run (seed 1)</span></h2>`;
  if(I.fired){
   html+=`<div class="metrics"><div class="metric"><div class="v">${int(I.fired)}</div><div class="l">innovator firings</div><div class="d">${int(I.reached_text)} reached the text (${pct(I.reached_text/I.fired,0)})</div></div><div class="metric"><div class="v">${int(I.candidates_quantiles[2])}</div><div class="l">legal candidates per firing, median</div><div class="d">10–90%: ${int(I.candidates_quantiles[0])}–${int(I.candidates_quantiles[4])}</div></div><div class="metric"><div class="v">${signed(I.gain_quantiles[2],2)}</div><div class="l">pressure gain of the chosen word, median</div><div class="d">10–90%: ${signed(I.gain_quantiles[0],2)} to ${signed(I.gain_quantiles[4],2)}</div></div></div>
   <div class="grid2"><div><h3>Firings by slot</h3>${cmpRows(SLOTS.filter(s=>I.by_slot[s]).map(s=>({label:s,values:[{v:I.by_slot[s],color:r.color,label:'firings'}]})),{format:v=>int(v)})}</div><div><h3>Firings by branch</h3>${cmpRows(Object.entries(I.by_branch).sort((a,b)=>b[1]-a[1]).map(([k,v])=>({label:{edit:'edit one unit',concat:'join with an adjacent word',prefixword:'join with a one-unit word',extend2:'extend by two units'}[k]||k,values:[{v,color:r.color,label:'firings'}]})),{format:v=>int(v)})}</div></div>`;
  }
  html+=`<h3 style="margin-top:12px">Proposals by operation</h3><div class="table-wrap"><table><thead><tr><th>Operation</th><th class="num">Proposals</th>${dec.delta_quantiles&&Object.keys(dec.delta_quantiles).length?'<th class="num">Accepted</th><th class="num">Rejected, retried</th><th class="num">Rejected, copy kept</th><th class="num">Acceptance of changed proposals</th>':'<th class="num">Accepted (no governor)</th>'}</tr></thead><tbody>${types.map(([ty,k])=>{const n=total(k),A=k.A||0,Rr=k.R||0,K=k.K||0;return `<tr><td class="mono">${esc(ty.toLowerCase())}</td><td class="num">${int(n)}</td>${k.T!=null?`<td class="num">${int(k.T)}</td>`:`<td class="num">${int(A)}</td><td class="num">${int(Rr)}</td><td class="num">${int(K)}</td><td class="num">${pct(A/Math.max(1,n),0)}</td>`}</tr>`;}).join('')}</tbody></table></div>`;
  if(dec.delta_quantiles&&dec.delta_quantiles.A)html+=`<details class="chart-note"><summary>Quantiles</summary><p>Δ of changed proposals (proposal value minus source value), 10/25/50/75/90% quantiles: accepted ${dec.delta_quantiles.A.map(v=>signed(v,2)).join(' · ')}; rejected ${(dec.delta_quantiles.R||[]).map(v=>signed(v,2)).join(' · ')}. Unchanged copies are accepted without a draw.</p></details>`;
  const modes=Object.entries(dec.modes).sort((a,b)=>b[1]-a[1]);html+=`<details class="chart-note"><summary>Proposal sources</summary><p>Source of the proposals: ${modes.map(([m,v])=>`${esc({LOCALY:'page window or far supply',PARAGRAPH_INITIAL:'paragraph-initial archive',RANDOM:'random',SUGGESTION:'suggestion'}[m]||m)} ${pct(v/total(dec.modes),0)}`).join(', ')}.</p></details>`;
  if(dec.by_node&&dec.by_node.some(x=>x.N||x.R)){
   const keys=[['A','accepted','var(--new)'],['R','rejected, retried','var(--neg)'],['K','copy kept','var(--muted)'],['N','innovated','var(--inn)']].filter(([k])=>dec.by_node.some(x=>x[k]));
   const ser=keys.map(([k,l,c])=>({label:l,color:c,values:dec.by_node.map((x,i)=>100*(x[k]||0)/Math.max(1,Object.values(x).reduce((a,b)=>a+b,0)))}));
   html+=`<div class="row" style="justify-content:space-between;margin-top:10px"><h3>Decisions by bifolium <span class="muted small">share of proposals</span></h3>${legend(ser)}</div>${lineChart(ser,labels,{groups,height:200,unit:'%',title:'Decisions by bifolium',tipDigits:0})}`;
  }
  html+='</section>';
 }
 // ---- low-diversity stretches: cumulative words below a level of rolling diversity (distinct forms among the last 50 words)
 if(obs.diversity){
  const LV=[['0.5','below 0.5 (degenerate)'],['0.6','below 0.6']];
  const dv=p=>p.diversity||{min:null,levels:{}};
  const cell=(id,get,d,s)=>show(rng(id,p=>get(dv(p))),d,s);
  const rowsHtml=[['Observed',fmt(dv(obs).min,2),...LV.flatMap(([l])=>[`${int(dv(obs).levels[l].tokens)} <span class="muted small">(${fmt(100*dv(obs).levels[l].share,2)}%)</span>`,int(dv(obs).levels[l].stretches)])],
   ...runs.map(r=>[SG.runName(r),cell(r.id,x=>x.min,2,''),...LV.flatMap(([l])=>[cell(r.id,x=>x.levels[l]?x.levels[l].tokens:NaN,0,''),cell(r.id,x=>x.levels[l]?x.levels[l].stretches:NaN,0,'')])])];
  html+=`<section class="panel" id="diversity"><div class="row" style="justify-content:space-between"><h2>Low-diversity stretches <span class="n">distinct forms among the last 50 words</span></h2><label class="ctl">level <select id="divLevel">${LV.map(([v,l])=>`<option value="${v}">${l}</option>`).join('')}</select></label></div><div id="divChart"></div>
   <div class="table-wrap" style="margin-top:10px"><table><thead><tr><th>Stream</th><th class="num">Lowest point</th><th class="num">Words below 0.5</th><th class="num">Stretches</th><th class="num">Words below 0.6</th><th class="num">Stretches</th></tr></thead><tbody>${rowsHtml.map(r=>`<tr><td>${r[0]}</td>${r.slice(1).map(c=>`<td class="num">${c}</td>`).join('')}</tr>`).join('')}</tbody></table></div>
   <p class="chart-note">A stretch is a run of words whose rolling diversity stays below the level; the count is its onsets. The manuscript never falls below 0.5; its two stretches below 0.6 are the qokeedy / qokedy lines of f75r. Cycles of a few short forms (o, y, qo) at page starts are what drives the far-0 run below 0.5 (RESULTS section 35).</p></section>`;
 }
 main.innerHTML=html;attachTips(main);
 for(const [i,el] of [...main.querySelectorAll('section')].entries()){el.id||=(['mechanisms','headline','births','slots','shape'][i]||'innovation-'+i);el.querySelector('h2')?.insertAdjacentHTML('beforeend',SG.shareControls(el.id));}
 SG.bindShares(main,()=>({runs:runs.map(r=>r.id).join(','),level:$('divLevel')?.value||'0.5'}));
 if(['0.5','0.6'].includes(SG.hash().level)&&$('divLevel'))$('divLevel').value=SG.hash().level;
 if(obs.diversity){
  const dv=p=>p.diversity||{levels:{}};
  const renderDiv=()=>{const l=$('divLevel').value;const ser=[{label:'Observed',color:'var(--obs)',values:dv(obs).levels[l].cum,width:2.4},...runs.map(r=>{const P=prof(r.id).map(p=>(dv(p).levels[l]||{}).cum||labels.map(()=>0));const s={label:r.label,color:r.color,values:labels.map((_,k)=>mean(P.map(p=>p[k])))};if(P.length>1)s.band=[labels.map((_,k)=>Math.min(...P.map(p=>p[k]))),labels.map((_,k)=>Math.max(...P.map(p=>p[k])))];return s;})];
   $('divChart').innerHTML=`<div class="row" style="justify-content:space-between"><h3>Cumulative words in stretches below ${esc(l)}, along the route</h3>${legend(ser)}</div>${lineChart(ser,labels,{groups,height:240,title:'Cumulative words in low-diversity stretches',tipDigits:0})}`;attachTips($('divChart'));};
  $('divLevel').addEventListener('change',renderDiv);renderDiv();
 }
 SG.restoreSection();
}catch(e){error($('main'),e);}
})();
