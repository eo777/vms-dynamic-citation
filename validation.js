"use strict";
// Validation: the held-out tests (bifolia, pages) with per-bifolium comparisons, and the pressure-scaling series.
(async()=>{
const {$,esc,fmt,int,mean,load,lineChart,legend,groupVar,error}=SG;
try{
 const [V,S]=await Promise.all([load('data/validation.json.gz?v=1c2fbd438a'),load('data/stats.json.gz?v=865efeb4d6')]);
 const main=$('main');const labels=V.nodes,groups=V.groups,N=V.N;
 const wmean=v=>{let s=0,w=0;v.forEach((x,i)=>{if(x!=null&&isFinite(x)){s+=x*N[i];w+=N[i];}});return w?s/w:NaN;};
 const avg=a=>a.length?mean(a):NaN;
 const govRun=S.runs.find(r=>r.id==='governed'),timmRun=S.runs.find(r=>r.id==='timm'),far0Run=SG.visibleRuns(S.runs).find(r=>r.id==='far0');
 const seedBand=(get)=>{const P=govRun.seeds.map(get);const s={values:labels.map((_,i)=>mean(P.map(p=>p[i])))};if(P.length>1)s.band=[labels.map((_,i)=>Math.min(...P.map(p=>p[i]))),labels.map((_,i)=>Math.max(...P.map(p=>p[i])))];return s;};
 const B=V.bifolia,P=B.per_node;
 const scoreTable=(rows,order,title,note)=>{
  const r=order.filter(k=>rows[k]);
  return `<h3>${esc(title)}</h3><div class="table-wrap"><table><thead><tr><th>Row</th><th class="num">Word TV</th><th class="num">Construction error, pp (316 common)</th><th class="num">pp (544 active)</th><th>per fold (TV)</th></tr></thead><tbody>${r.map(k=>{const v=rows[k];const held=k.includes('held');return `<tr${held?' style="font-weight:600"':''}><td>${esc(k)}${held?' <span class="muted small">never saw the scored text</span>':''}</td><td class="num">${fmt(avg(v.tv),3)}</td><td class="num">${fmt(avg(v.mae),2)}</td><td class="num">${fmt(avg(v.mae_active),2)}</td><td class="mono small muted">${v.tv.map(x=>fmt(x,3)).join(' · ')}</td></tr>`;}).join('')}</tbody></table></div>${note?`<p class="chart-note">${note}</p>`:''}`;
 };
 const ORDER=['Full fit, expected values','Full fit, i.i.d. sample','Held fit, expected values','Timm','Transformer + Timm','Governed, held targets','Governed, full-fit targets'].concat(far0Run?['Far 0, held targets','Far 0, full-fit targets']:[]);
 let html=`<section class="panel explain" id="what"><h2>What was held out</h2>
 <p>The pressures come from a model fitted to the same manuscript the runs are compared with. A held-out test refits the model without part of the manuscript, runs the governor on those targets, and scores only the part the targets never saw.</p>
 <ul><li><b>Bifolia.</b> Every fourth bifolium along the route is withheld (${B.held_nodes.map(h=>h.length).join(', ')} bifolia per fold, interleaved, so a held bifolium is predicted from its neighbours through the model's gradual term and its group's steps). The model is refitted on the other bifolia's pages only, with its vocabulary and prior from those pages, and the final configuration is run once per fold. In the charts below, every bifolium's held-out value comes from the run, and the fit, that never saw it.</li>
 <li><b>Pages.</b> The earlier test of the study: every fourth page within each bifolium withheld, four folds, scored on the held pages. It was run with the configuration before the innovator was added.</li>
 <li><b>Scaling.</b> The same configuration with both pressure temperatures scaled from 0 (Timm's program unchanged) to 2.</li>
 <li><b>Far 0.</b> While the far-0 run is shown (menu toggle), the same held-bifolia test for that configuration (no far supply, repeat coin, share cap) appears in its own colour.</li></ul></section>`;
 html+=`<section class="panel" id="scores"><h2>Scores on the held text <span class="n">means over four folds</span></h2>
 ${scoreTable(B.scores,ORDER,'Held bifolia','Training pages per fold: '+(B.training_pages||[]).filter(Boolean).join(', ')+' of 207. The held fit\'s own expected values lose more to the withheld bifolia than the generator run on its targets does.')}
 ${scoreTable(V.pages.scores,ORDER,'Held pages',esc(V.pages.note))}</section>`;
 // per-bifolium charts
 const gov=govRun.color,timm=timmRun.color,far0=far0Run&&far0Run.color;
 const far0Ser=(key,w)=>far0Run&&P[key].far0_full?[{label:'Far 0, full-fit targets',color:far0,values:P[key].far0_full},...(P[key].far0_held?[{label:'Far 0, targets never saw this bifolium',color:far0,values:P[key].far0_held,dash:true,width:w||2}]:[])]:[];
 const tvFull=seedBand(s=>S.tv_by_node[s]),maeFull=seedBand(s=>S.mae_by_node[s]);
 const tvSer=[{label:'Timm',color:timm,values:P.tv.timm},{label:'Governed, full-fit targets (3 seeds)',color:gov,...tvFull},{label:'Governed, targets never saw this bifolium',color:gov,values:P.tv.governed_held,dash:true,width:2.2},
  ...far0Ser('tv'),{label:'Full fit, expected',color:'var(--fit)',values:P.tv.full_fit_expected},{label:'Held fit, expected (never saw this bifolium)',color:'var(--fit)',values:P.tv.held_fit_expected,dash:true},{label:'Full fit, i.i.d. sample',color:'var(--iid)',values:P.tv.iid,dash:true}];
 const maeSer=[{label:'Timm',color:timm,values:P.mae.timm},{label:'Governed, full-fit targets (3 seeds)',color:gov,...maeFull},{label:'Governed, targets never saw this bifolium',color:gov,values:P.mae.governed_held,dash:true,width:2.2},
  ...far0Ser('mae'),{label:'Full fit, expected',color:'var(--fit)',values:P.mae.full_fit_expected},{label:'Held fit, expected (never saw this bifolium)',color:'var(--fit)',values:P.mae.held_fit_expected,dash:true},{label:'Full fit, i.i.d. sample',color:'var(--iid)',values:P.mae.iid,dash:true}];
 html+=`<section class="panel" id="bynode"><h2>By bifolium <span class="n">solid: targets from the full fit · dashed: targets that never saw the bifolium</span></h2>
 <div class="grid2"><div><div class="row" style="justify-content:space-between"><h3>Word distribution, total variation</h3>${legend(tvSer)}</div>${lineChart(tvSer,labels,{groups,height:240,title:'Word total variation by bifolium',tipDigits:3})}<details class="chart-note"><summary>Means</summary><p>Token-weighted means: ${tvSer.map(s=>`${esc(s.label)} ${fmt(wmean(s.values),3)}`).join(' · ')}.</p></details></div>
 <div><div class="row" style="justify-content:space-between"><h3>Construction shares, mean absolute error (pp)</h3>${legend(maeSer)}</div>${lineChart(maeSer,labels,{groups,height:240,title:'Construction share error by bifolium',tipDigits:2})}<details class="chart-note"><summary>Means</summary><p>Means: ${maeSer.map(s=>`${esc(s.label)} ${fmt(wmean(s.values),2)}`).join(' · ')}.</p></details></div></div></section>`;
 // construction trajectories
 const E=P.effects;const effSer=i=>[{label:'Observed',color:'var(--obs)',values:E.observed[i],width:2.2},{label:'Full fit, expected',color:'var(--fit)',values:E.fitted[i]},{label:'Held fit, expected',color:'var(--fit)',values:E.held_fit[i],dash:true},
  {label:'Timm',color:timm,values:E.timm[i]},{label:'Governed, full-fit targets',color:gov,values:E.governed_full[i]},...(E.governed_held?[{label:'Governed, held targets',color:gov,values:E.governed_held[i],dash:true,width:2.2}]:[]),
  ...(far0Run&&E.far0_full?[{label:'Far 0, full-fit targets',color:far0,values:E.far0_full[i]}]:[]),...(far0Run&&E.far0_held?[{label:'Far 0, held targets',color:far0,values:E.far0_held[i],dash:true,width:2}]:[])];
 html+=`<section class="panel" id="constructions"><h2>Key constructions by bifolium <span class="n">% of tokens carrying the construction</span></h2><div class="legend">${legend(effSer(0))}</div>
 <div class="cards" id="valCards" style="margin-top:10px">${E.names.map((n,i)=>`<div class="card"><h3>${esc(n)}${SG.enlargeButton(i)}</h3>${lineChart(effSer(i),labels,{groups,height:170,title:n,tipDigits:1})}</div>`).join('')}</div>
 <p class="chart-note">Dashed series are the ones that never saw the bifolium they are drawn at: the held fit's expected share, and the governed run driven by that fit. Where the dashed Governed line follows the dashed grey one, the generator reproduces what its targets ask for; where both miss the Observed line, the model could not predict the bifolium from its neighbours.</p></section>`;
 // scaling
 const sc=V.scaling,so=V.scaling_observed;const xl=sc.map(r=>r.label);
 const scTv=[{label:'Word TV',color:gov,values:sc.map(r=>r.tv)}],scMae=[{label:'Construction error, pp',color:gov,values:sc.map(r=>r.mae)}];
 html+=`<section class="panel" id="scaling"><h2>Scaling the pressures <span class="n">final configuration, both temperatures together, seed 1</span></h2>
 <div class="grid2"><div>${lineChart(scTv,xl,{height:200,title:'Word TV by temperature',tipDigits:3})}</div><div>${lineChart(scMae,xl,{height:200,title:'Construction error by temperature',tipDigits:2})}</div></div>
 <div class="table-wrap" style="margin-top:10px"><table><thead><tr><th>Temperature</th><th class="num">Word TV</th><th class="num">Construction error, pp</th><th class="num">Distinct forms</th><th class="num">New per 1,000, first 10k</th><th class="num">4a prefix:qok %</th><th class="num">2a eo %</th><th class="num">4a suffix:edy %</th></tr></thead><tbody>
 ${sc.map(r=>`<tr><td>${esc(r.label)}</td><td class="num">${fmt(r.tv,3)}</td><td class="num">${fmt(r.mae,2)}</td><td class="num">${int(r.forms)}</td><td class="num">${fmt(r.new_first,0)}</td><td class="num">${fmt(r.qok_4a,1)}</td><td class="num">${fmt(r.eo_2a,1)}</td><td class="num">${fmt(r.edy_4a,1)}</td></tr>`).join('')}
 <tr><td>Observed</td><td class="num">0</td><td class="num">0</td><td class="num">${int(so.forms)}</td><td class="num">${fmt(so.new_first,0)}</td><td class="num">${fmt(so.qok_4a,1)}</td><td class="num">${fmt(so.eo_2a,1)}</td><td class="num">${fmt(so.edy_4a,1)}</td></tr></tbody></table></div>
 <p class="chart-note">The response is smooth and monotone; a quarter of the pressure removes most of Timm's construction error. The innovator's targets do not depend on the pressures, so the vocabulary size holds at every temperature.</p></section>`;
 main.innerHTML=html;
 $('valCards').addEventListener('click',e=>{const b=e.target.closest('[data-enlarge]');if(!b)return;const i=+b.dataset.enlarge,ser=effSer(i);SG.openOverlay(`${esc(E.names[i])} <span class="muted small">% of tokens carrying the construction</span>`,`${legend(ser)}${lineChart(ser,labels,{groups,height:480,width:1200,title:E.names[i],tipDigits:1})}`);});
}catch(e){error($('main'),e);}
})();
