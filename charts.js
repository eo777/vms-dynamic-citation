"use strict";
(async()=>{
const {$,esc,fmt,int,pct,signed,finite,mean,sum,load,lineChart,legend,cmpRows,heatmap,attachTips,hash,setHash,error}=SG;
try{
 const S=await SC.statistics(),requested=SG.visibleRuns(S.runs),archived=requested.filter(r=>r.detail_available===false);
 const detailed=requested.filter(r=>r.detail_available!==false),runs=detailed.length?detailed:[S.runs.find(r=>r.id==='timm')],labels=S.nodes,groups=S.node_groups,N=S.N;
 const seedsOf=id=>S.runs.find(r=>r.id===id).seeds;
 const st=h=>{const o=hash();return o[h];};
 const state={kind:'all',q:'',shown:12,group:'overall',run:'governed',words:'overall'};
 for(const k of ['kind','q','group','run','words'])if(st(k))state[k]=st(k);
 state.shown=Math.max(12,Math.min(S.effects.names.length,Number.parseInt(st('shown'))||12));
 if(!runs.some(r=>r.id===state.run))state.run=runs[0].id;
 const main=$('main');
 const section=(id,title,body,note='')=>`<section class="panel" id="${id}"><h2>${title}</h2>${body}${note?`<p class="chart-note">${note}</p>`:''}</section>`;
 const seedSeries=(id,get,label)=>{const P=seedsOf(id).map(get);const r=S.runs.find(r=>r.id===id);const s={label:label||r.label,color:r.color,values:labels.map((_,i)=>mean(P.map(p=>p[i])))};if(P.length>1)s.band=[labels.map((_,i)=>Math.min(...P.map(p=>p[i]))),labels.map((_,i)=>Math.max(...P.map(p=>p[i])))];return s;};
 // ---- 1. distance per bifolium
 const tvSer=[...requested.map(r=>seedSeries(r.id,s=>S.tv_by_node[s])),{label:'Fitted model, i.i.d. sample',color:'var(--iid)',values:S.tv_by_node['fitted i.i.d. sample'],dash:true}];
 const maeSer=[...requested.map(r=>seedSeries(r.id,s=>S.mae_by_node[s])),{label:'Fitted model, expected',color:'var(--fit)',values:S.mae_by_node['fitted (expected)'],dash:true},{label:'Fitted model, i.i.d. sample',color:'var(--iid)',values:S.mae_by_node['fitted i.i.d. sample'],dash:true}];
 const wmean=v=>sum(v.map((x,i)=>x*N[i]))/sum(N);
 let html=section('distance','Distance to the manuscript, by bifolium',`<div class="grid2"><div><div class="row" style="justify-content:space-between"><h3>Word distribution, total variation</h3>${legend(tvSer)}</div>${lineChart(tvSer,labels,{groups,height:230,title:'Word total variation by bifolium',tipDigits:3})}<details class="chart-note"><summary>Means</summary><p>Token-weighted means: ${tvSer.map(s=>`${esc(s.label)} ${fmt(wmean(s.values),3)}`).join(' · ')}. 0 = the bifolium's own bag of words; the i.i.d. sample is what a perfect sampler of the model reaches, sampling noise included.</p></details></div>
  <div><div class="row" style="justify-content:space-between"><h3>Construction shares, mean absolute error (pp)</h3>${legend(maeSer)}</div>${lineChart(maeSer,labels,{groups,height:230,title:'Construction share error by bifolium',tipDigits:2})}<details class="chart-note"><summary>Means</summary><p>Over the ${S.effects.names.length} constructions with at least 100 manuscript tokens. Means: ${maeSer.map(s=>`${esc(s.label)} ${fmt(wmean(s.values),2)}`).join(' · ')}.</p></details></div></div>`);
 html=section('methods','Selected mechanisms',SC.mechanismTable(requested)+SC.mechanismNote()+`<p><a href="comparison.html">Open the ranked comparison, all-statistics profiles, and annotated examples.</a></p>${archived.length?`<p class="chart-note">Summary-only methods selected: ${archived.map(r=>esc(r.short)).join(', ')}. Their scalar curves remain here, on Comparison and on Innovation. Detailed distributions were retired to keep storage and future rescoring bounded.${detailed.length?' Distribution charts use the selected focus methods.':' Distribution charts use Timm as the detailed reference.'}</p>`:''}`)+html;
 const cm=S.comparison;
 html+=section('word-entropy','Word H1, H2 and order beyond the vocabulary',`<div class="grid2">${['word_h1','word_h2','word_order_gain'].map(k=>{const m=cm.metrics.find(x=>x.key===k),available=requested.filter(r=>cm.runs.find(x=>x.id===r.id).metric_seed_count?.[k]>0),ser=[{label:'Manuscript',color:'var(--obs)',values:cm.observed.series[k]},...available.map(r=>{const rr=cm.runs.find(x=>x.id===r.id);return {label:r.label+' ('+rr.metric_seed_count[k]+' seeds)',color:r.color,values:rr.series[k],band:rr.metric_seed_count[k]>1?rr.bands[k]:null};})];return `<div><h3>${esc(m.label)}</h3>${legend(ser)}${lineChart(ser,labels,{groups,zero:false,height:220,title:m.label,tipDigits:4})}</div>`;}).join('')}</div>`,'H1 describes spelling frequencies. H2 is empirical uncertainty of the next word given the preceding word, using within-line pairs. Rare contexts bias raw H2 downward. Order gain = shuffled H2 minus actual H2; 32 shuffles preserve each line’s vocabulary and endpoints. This is evidence about adjacency, not a test of semantic content. Missing historical results were not regenerated automatically; Comparison displays them as unscored.');
 html+=section('entropy','H1 and H2, by bifolium',`<div class="grid2">${['h1','h2','h1_slot','h2_slot'].map(k=>{const m=cm.metrics.find(x=>x.key===k),ser=[{label:'Manuscript',color:'var(--obs)',values:cm.observed.series[k]},...requested.map(r=>{const rr=cm.runs.find(x=>x.id===r.id);return {label:r.label,color:r.color,values:rr.series[k],band:r.seeds.length>1?rr.bands[k]:null};})];return `<div><h3>${esc(m.label)}</h3>${legend(ser)}${lineChart(ser,labels,{groups,zero:false,height:220,title:m.label,tipDigits:3})}</div>`;}).join('')}</div>`,'H1 measures symbol diversity; H2 is the uncertainty of the next symbol given the previous one. Spaces are included. The combined alphabet treats ch, sh, benched gallows and e/i runs as units. These measures are separate from lexical diversity and adjacent-word structure.');
 // ---- 1b. vocabulary richness per bifolium (MATTR)
 const MW=Object.keys(S.mattr_by_node||{});
 const mser=w=>[{label:'Observed',color:'var(--obs)',values:S.mattr_by_node[w].observed,width:2.4},...requested.map(r=>seedSeries(r.id,s=>S.mattr_by_node[w][s])),{label:'Fitted model, i.i.d. sample',color:'var(--iid)',values:S.mattr_by_node[w]['fitted i.i.d. sample'],dash:true}];
 if(MW.length)html+=`<section class="panel" id="mattr"><h2>Vocabulary richness by bifolium <span class="n">moving-average type-token ratio</span></h2><div class="toolbar"><label class="ctl">window <select id="mattrWin">${MW.map(w=>`<option value="${w}"${w==='100'?' selected':''}>${w} tokens</option>`).join('')}</select></label><span class="ctl small muted">mean share of distinct words over every window of that length inside the bifolium's text; a bifolium shorter than the window counts as one window</span></div><div id="mattrChart"></div></section>`;
 // ---- 2. constructions
 const E=S.effects,kinds=[...new Set(E.kinds)];
 html+=`<section class="panel" id="constructions"><h2>Construction shares along the path <span class="n">${int(E.names.length)} constructions with at least 100 tokens</span></h2>
  <div class="toolbar"><label class="ctl">search <input type="search" id="q" placeholder="e.g. edy, qok, eo" style="width:160px"></label><label class="ctl">kind <select id="kind"><option value="all">all</option>${kinds.map(k=>`<option value="${k}">${esc(k)}</option>`).join('')}</select></label><span class="ctl small muted" id="count"></span></div>
  <div class="legend" id="effLegend"></div><div class="cards" id="effCards" style="margin-top:10px"></div><div class="row" style="margin-top:10px"><button type="button" id="more">Show 12 more</button></div></section>`;
 // ---- 3. words
 html+=`<section class="panel" id="words"><h2>Word counts <span class="n">per 10,000 tokens</span></h2><div class="toolbar"><label class="ctl">group <select id="wgroup"><option value="overall">whole text</option>${S.groups.map(g=>`<option value="${g}">${esc(g)}</option>`).join('')}</select></label><span class="ctl small muted">the 60 most frequent observed words in the selection; tick = observed</span></div><div id="wordRows"></div></section>`;
 // ---- 4. zipf + growth
 const ranks=[];for(let r=1;r<=3000;r*=1.12)ranks.push(Math.round(r));const rk=[...new Set(ranks)];
 const zipf=name=>{const c=Object.values(S.streams[name].counts).sort((a,b)=>b-a);return rk.map(r=>c[r-1]?Math.log10(c[r-1]):NaN);};
 const zSer=[{label:'Observed',color:'var(--obs)',values:zipf('observed'),width:2.4},...runs.map(r=>({label:r.label,color:r.color,values:zipf(r.main)}))];
 const gSer=[{label:'Observed (bags in path order)',color:'var(--obs)',values:S.streams.observed.growth,width:2.4},...requested.map(r=>seedSeriesX(r.id,s=>S.streams[s].growth))];
 function seedSeriesX(id,get){const P=seedsOf(id).map(get);const r=S.runs.find(r=>r.id===id);const n=P[0].length;const s={label:r.label,color:r.color,values:[...Array(n).keys()].map(i=>mean(P.map(p=>p[i])))};if(P.length>1)s.band=[[...Array(n).keys()].map(i=>Math.min(...P.map(p=>p[i]))),[...Array(n).keys()].map(i=>Math.max(...P.map(p=>p[i])))];return s;}
 const gLabels=S.streams.observed.growth.map((_,i)=>int(i*500));
 html+=section('zipf','Rank–frequency and vocabulary growth',`<div class="grid2"><div><div class="row" style="justify-content:space-between"><h3>log₁₀ count against rank</h3>${legend(zSer)}</div>${lineChart(zSer,rk.map(String),{height:230,zero:false,title:'Rank-frequency',tipDigits:2,ticks:9})}<p class="chart-note">Ranks are log-spaced along the axis.</p></div><div><div class="row" style="justify-content:space-between"><h3>Distinct forms after n tokens</h3>${legend(gSer)}</div>${lineChart(gSer,gLabels,{height:230,title:'Vocabulary growth',tipDigits:0,ticks:8})}</div></div>`);
 // ---- 5. unit bigrams
 html+=`<section class="panel" id="bigrams"><h2>Glyph-unit bigrams inside words</h2><div class="toolbar"><label class="ctl">run <select id="bgRun">${runs.map(r=>`<option value="${r.id}" ${r.id===state.run?'selected':''}>${esc(r.label)}</option>`).join('')}</select></label><label class="ctl">group <select id="bgroup"><option value="overall">whole text</option>${S.groups.map(g=>`<option value="${g}">${esc(g)}</option>`).join('')}</select></label><span class="ctl small muted">cell = log₂(generated ÷ observed) of the transition's share of all transitions; red more than observed, blue less; blank under 5 observed and generated</span></div><div class="grid2"><div class="heat" id="bgHeat"></div><div id="bgTable"></div></div></section>`;
 // ---- 6. word bigrams
 html+=`<section class="panel" id="wordbigrams"><h2>Adjacent word pairs <span class="n">per 10,000 pairs; the 50 most frequent observed</span></h2><div id="wbRows"></div><details class="chart-note"><summary>Repeat rates</summary><p>Repeated word (the same spelling twice in a row): observed ${pct(S.streams.observed.profile.interval_repeat_rate,2)}${runs.map(r=>`, ${esc(r.short)} ${pct(mean(seedsOf(r.id).map(s=>S.streams[s].profile.interval_repeat_rate)),2)}`).join('')}. These rates use the Comparison intervals: pairs crossing a line or bifolium boundary are excluded.</p></details></section>`;
 main.innerHTML=html;
 for(const el of main.querySelectorAll('section[id]'))el.querySelector('h2')?.insertAdjacentHTML('beforeend',SG.shareControls(el.id));
 SG.bindShares(main,()=>({...state,mw:$('mattrWin')?.value,runs:requested.map(r=>r.id).join(',')}));
 $('kind').value=state.kind;$('q').value=state.q;$('wgroup').value=state.words;$('bgroup').value=state.group;$('bgRun').value=state.run;
 if(MW.includes(st('mw')))$('mattrWin').value=st('mw');
 function renderMattr(){if(!MW.length)return;const w=$('mattrWin').value,ser=mser(w);$('mattrChart').innerHTML=`<div class="row" style="justify-content:space-between"><h3>Window of ${esc(w)} tokens</h3>${legend(ser)}</div>${lineChart(ser,labels,{groups,height:240,title:'MATTR by bifolium',tipDigits:3,zero:false})}<details class="chart-note"><summary>Means</summary><p>Token-weighted means: ${ser.map(s=>`${esc(s.label)} ${fmt(wmean(s.values),3)}`).join(' · ')}. Run texts are aligned to the bifolia by cumulative token count.</p></details>`;}
 if(MW.length){$('mattrWin').addEventListener('change',renderMattr);renderMattr();}
 // ---- constructions behaviour
 const effSeries=i=>{const ser=[{label:'Observed',color:'var(--obs)',values:E.observed[i],width:2.4},{label:'Fitted target',color:'var(--fit)',values:E.fitted[i],dash:true}];
  for(const r of runs){const P=seedsOf(r.id).map(s=>E.runs[s][i]);const s={label:r.label,color:r.color,values:labels.map((_,k)=>mean(P.map(p=>p[k])))};if(P.length>1)s.band=[labels.map((_,k)=>Math.min(...P.map(p=>p[k]))),labels.map((_,k)=>Math.max(...P.map(p=>p[k])))];ser.push(s);}return ser;};
 $('effLegend').innerHTML=legend(effSeries(0)).replace(/^<div class="legend">|<\/div>$/g,'');
 $('effCards').addEventListener('click',e=>{const b=e.target.closest('[data-enlarge]');if(!b)return;const i=+b.dataset.enlarge,ser=effSeries(i);
  SG.openOverlay(`<code>${esc(E.names[i])}</code> <span class="muted small">${esc(E.kinds[i])} · ${int(E.tokens[i])} tokens · % of tokens carrying the construction</span>`,`${legend(ser)}${lineChart(ser,labels,{groups,height:480,width:1200,unit:'%',title:E.names[i],tipDigits:2,left:50})}`);});
 function renderEff(){
  const q=state.q.trim().toLowerCase();const idx=E.names.map((n,i)=>i).filter(i=>(state.kind==='all'||E.kinds[i]===state.kind)&&(!q||E.names[i].toLowerCase().includes(q)));
  $('count').textContent=`${int(idx.length)} shown of ${int(E.names.length)}`.replace('shown',`match, ${Math.min(state.shown,idx.length)} shown`);
  $('effCards').innerHTML=idx.slice(0,state.shown).map(i=>`<div class="card"><h3><code>${esc(E.names[i])}</code> <span class="muted small">${esc(E.kinds[i])} · ${int(E.tokens[i])} tokens</span>${SG.enlargeButton(i)}</h3>${lineChart(effSeries(i),labels,{groups,height:170,unit:'%',title:E.names[i],tipDigits:2,left:44})}</div>`).join('')||'<p class="empty">No construction matches.</p>';
  $('more').style.display=idx.length>state.shown?'':'none';
 }
 $('q').addEventListener('input',()=>{state.q=$('q').value;state.shown=12;renderEff();});
 $('kind').addEventListener('change',()=>{state.kind=$('kind').value;state.shown=12;renderEff();});
 $('more').addEventListener('click',()=>{state.shown+=12;renderEff();});
 if(st('q')){state.q=st('q');$('q').value=state.q;}
 renderEff();
 // ---- words behaviour
 function renderWords(){
  const g=state.words;const get=name=>g==='overall'?S.streams[name].counts:(S.streams[name].group_counts[g]||{});
  const tot=name=>g==='overall'?S.streams[name].profile.tokens:sum(S.N.map((n,i)=>groups[i]===g?n:0));
  const obs=get('observed'),to=tot('observed');const top=Object.entries(obs).sort((a,b)=>b[1]-a[1]).slice(0,60);
  const rows=top.map(([w,c])=>({label:w,obs:1e4*c/to,values:runs.map(r=>{const v=mean(seedsOf(r.id).map(s=>1e4*(get(s)[w]||0)/tot(s)));return {v,color:r.color,label:r.label};})}));
  $('wordRows').innerHTML=`<div class="grid2"><div>${cmpRows(rows.slice(0,30),{format:v=>fmt(v,0)})}</div><div>${cmpRows(rows.slice(30),{format:v=>fmt(v,0)})}</div></div>`;attachTips($('wordRows'));
 }
 $('wgroup').addEventListener('change',()=>{state.words=$('wgroup').value;renderWords();});renderWords();
 // ---- unit bigrams behaviour
 const A=S.alphabet,rows=['^',...A],cols=[...A,'$'];
 function renderBigrams(){
  const g=state.group;const mat=name=>g==='overall'?S.streams[name].unit_bigrams.overall:(S.streams[name].unit_bigrams.groups[g]||null);
  const O=mat('observed'),G=mat(runs.find(r=>r.id===state.run).main);
  if(!O||!G){$('bgHeat').innerHTML='<p class="empty">No data for this group.</p>';return;}
  const n=A.length;const idx=i=>i===0?n:i-1;const jdx=j=>j===n?n:j;   // matrix rows: units 0..n-1 then ^ at n; cols: units then $ at n
  const tO=sum(O.flat()),tG=sum(G.flat());const cells=[];const M=rows.map((r,i)=>cols.map((c,j)=>{const o=O[idx(i)][jdx(j)],gg=G[idx(i)][jdx(j)];if(o<5&&gg<5)return null;const so=o/tO,sg=gg/tG,z=Math.log2((sg+1e-6)/(so+1e-6));cells.push({r,c,o,g:gg,so,sg,z});return {n:1,z,tip:`observed ${int(o)} (${fmt(1e4*so,1)}‱), generated ${int(gg)} (${fmt(1e4*sg,1)}‱), log₂ ratio ${signed(z,2)}`};}));
  $('bgHeat').innerHTML=heatmap(M,rows,cols,{cell:19,left:40,top:28,limit:2,title:'Unit bigram log ratio'});attachTips($('bgHeat'));
  cells.sort((a,b)=>Math.abs(b.sg-b.so)-Math.abs(a.sg-a.so));
  $('bgTable').innerHTML=`<h3>Largest differences in share</h3><div class="table-wrap"><table><thead><tr><th>Transition</th><th class="num">Observed ‱</th><th class="num">Generated ‱</th><th class="num">log₂ ratio</th></tr></thead><tbody>${cells.slice(0,18).map(c=>`<tr><td class="mono">${esc(c.r)} → ${esc(c.c)}</td><td class="num">${fmt(1e4*c.so,1)}</td><td class="num">${fmt(1e4*c.sg,1)}</td><td class="num">${signed(c.z,2)}</td></tr>`).join('')}</tbody></table></div>`;
 }
 $('bgRun').addEventListener('change',()=>{state.run=$('bgRun').value;renderBigrams();});
 $('bgroup').addEventListener('change',()=>{state.group=$('bgroup').value;renderBigrams();});renderBigrams();
 // ---- word bigrams
 {const obs=S.streams.observed.word_bigrams,to=S.streams.observed.word_bigram_total||sum(Object.values(obs));const top=Object.entries(obs).sort((a,b)=>b[1]-a[1]).slice(0,50);
  const rows=top.map(([w,c])=>({label:`${w} ×${c}`,obs:1e4*c/to,values:runs.map(r=>{const v=mean(seedsOf(r.id).map(s=>{const wb=S.streams[s].word_bigrams;return 1e4*(wb[w]||0)/Math.max(1,S.streams[s].word_bigram_total||sum(Object.values(wb)));}));return {v,color:r.color,label:r.label};})}));
  $('wbRows').innerHTML=`<div class="grid2"><div>${cmpRows(rows.slice(0,25),{format:v=>fmt(v,0)})}</div><div>${cmpRows(rows.slice(25),{format:v=>fmt(v,0)})}</div></div><p class="chart-note">Shares are per 10,000 word pairs of each stream; the pairs shown are the manuscript’s 50 most frequent, with their true counts in every stream.</p>`;attachTips($('wbRows'));}
 SG.restoreSection();
}catch(e){error($('main'),e);}
})();
