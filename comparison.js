"use strict";
(async()=>{
 const {$,esc,fmt,int,pct,signed,finite,mean,sum,lineChart,legend,hash,setHash}=SG;
 const DESCRIPTIONS={
  component:'Mean absolute difference in component-carrier rates per 10,000 tokens, against the manuscript itself. The same common constructions are used for every method; lower is closer.',
  length:'Mean word length in combined glyph units. A shift toward very short forms can accompany repetition, but length alone does not diagnose collapse.',
  mattr:'Mean distinct-word share in sliding 100-token windows inside each interval. Local reuse can lower this even when the total vocabulary is large.',
  types:'Distinct spellings within this interval per 1,000 tokens. Interval budgets are identical across methods; this is separate from whole-manuscript vocabulary size.',
  top10:'Share of tokens accounted for by the ten most common forms in each interval. High concentration can reveal a few forms dominating the output.',
  clustering:'Expected distinct share of a random 100-token sample from the interval’s bag, minus its actual MATTR. A positive gap indicates local clustering beyond the bag’s vocabulary concentration.',
  births:'First appearances in the entire stream, counted in this interval per 1,000 tokens. Novelty is judged against the manuscript curve: excess is also a mismatch.',
  cumulative:'Distinct spellings seen from the beginning of the stream to the end of each interval. The final point is the full-text vocabulary size; growth shape matters as well as its endpoint.',
  h1:'Shannon entropy of EVA symbols, including spaces. This describes the balance of symbol frequencies, not word-level diversity.',
  h2:'Conditional entropy of the next EVA symbol given its predecessor, including spaces between words. Low manuscript H2 means strong local symbol constraints. This is not the entropy of whole words or a test of word order.',
  h1_slot:'Symbol entropy with ch, sh, benched gallows and e/i runs combined into units, plus spaces. Compare it with EVA H1 to check that segmentation is not driving the conclusion.',
  h2_slot:'Next-unit conditional entropy with combined units and spaces. It checks the same local constraints under a second segmentation.',
  word_h1:'Empirical entropy of word spellings within each interval. This measures the word-frequency distribution, not glyph composition. Available streams are scored exactly; missing historical metrics are not treated as zero.',
  word_h2:'Empirical conditional entropy of the next word given its predecessor, using within-line pairs. Singleton and rare predecessor contexts bias this downward. Compare with the matched shuffle and repeated-context coverage; this is not an estimated semantic entropy rate.',
  word_order_gain:'Mean H2 of 32 shuffled texts minus actual word H2. Each shuffle preserves each line’s vocabulary, first word and last word. Positive values mean more adjacency predictability than this matched null. This diagnostic does not prove semantic information. Included only when the optional word-entropy ranking is enabled.',
  pair_excess:'Repeated occurrences of the same nonidentical word pair, above a shuffled-order baseline. Sixteen shuffles preserve each line’s vocabulary and first/last words. Values are collisions per 10,000 within-line pairs; this diagnostic is not a formal significance test.',
  repeat:'Share of within-line adjacent pairs with identical spellings. This is kept separate from the reuse of nonidentical pairs.',
  degenerate:'Share of token positions whose last 50 words contain fewer than 25 distinct forms (D50 < 0.5). Only full windows count; windows continue across interval boundaries. This threshold flags unusually concentrated output, not a proved generator loop.',
  minimum:'Lowest full 50-token rolling distinct share reached in the interval. A very low minimum reveals a local failure that an interval mean can conceal.',
  short:'Share of tokens spelled o, y, or qo. These forms dominated the previously identified far0 cycles; a high share is descriptive evidence, not a failure criterion on its own.',
  word_tv:'Total variation distance from the manuscript’s word distribution in each interval. Shown diagnostically, but excluded from the default rank: generating the exact same spellings is a stronger demand than matching structure.',
  component_fit:'Component-carrier error against the fitted target, per 10,000 tokens. Excluded from the rank because the target is itself an approximation; closeness to it is not the same as closeness to the manuscript.'
 };
 const OVERLAYS={diversity:'Local diversity / recurrence',novelty:'First appearances',forms:'Concentration of forms',short:'Short forms: o / y / qo',length:'Word length',h1:'H1: symbol-frequency mismatch',h2:'H2: rare symbol transitions',pairs:'Repeated adjacent pairs',component:'Component carriers'};
 const metricOverlay=k=>({births:'novelty',cumulative:'novelty',h1:'h1',h1_slot:'h1',h2:'h2',h2_slot:'h2',word_h1:'forms',word_h2:'pairs',word_order_gain:'pairs',pair_excess:'pairs',repeat:'pairs',short:'short',length:'length',component:'component',component_fit:'component',top10:'forms',word_tv:'forms'}[k]||'diversity');
 try{
  const C=await SC.index();SG.themeRuns(C.runs);const runById=new Map(C.runs.map(r=>[r.id,r]));
  const h=hash(),valid=id=>runById.has(id),defaults=['timm','governed','far0','noinnov_far0','exp_sheet_base','exp_motif96'].filter(valid);
  let weights={};try{weights=JSON.parse(h.weights||'{}');}catch(e){}
  weights=Object.fromEntries(C.families.map(f=>[f,[0,.5,1,2,3].includes(+weights[f])?+weights[f]:1]));
  const state={scope:['nonbio',...C.groups].includes(h.scope)?h.scope:'all',metric:C.metrics.some(m=>m.key===h.metric)?h.metric:'mattr',view:h.view==='difference'?'difference':'actual',
   plot:(h.plot||h.runs||defaults.join(',')).split(',').filter(valid),run:valid(h.run)?h.run:'governed',base:valid(h.base)?h.base:'timm',
   node:Math.max(0,Math.min(C.nodes.length-1,Number.parseInt(h.node)||0)),window:h.window==='low'?'low':'middle',overlay:h.overlay in OVERLAYS?h.overlay:'diversity',gallery:h.gallery==='1',component:h.component||'',paired:h.paired!=='0',wordrank:h.wordrank==='1',weights};
  if(!state.plot.length)state.plot=defaults;
  if(!valid(state.run))state.run=C.runs[0].id;if(!valid(state.base))state.base=C.runs[0].id;
  const shareState=()=>({runs:SG.visibleRuns(C.runs).map(r=>r.id).join(','),scope:state.scope,metric:state.metric,view:state.view,plot:state.plot.join(','),run:state.run,base:state.base,node:state.node,window:state.window,overlay:state.overlay,gallery:state.gallery?'1':'0',component:state.component,paired:state.paired?'1':'0',wordrank:state.wordrank?'1':'0',weights:JSON.stringify(state.weights)});
  const save=()=>setHash({...shareState(),section:hash().section});
  const head=(id,title)=>`<div class="section-head"><h2>${title}</h2>${SG.shareControls(id)}</div>`;
  const runOptions=selected=>C.runs.map(r=>`<option value="${r.id}"${r.id===selected?' selected':''}>${esc(r.label)}${r.failures.length?' [incomplete]':''}</option>`).join('');
  const metricOptions=C.metrics.map(m=>`<option value="${m.key}"${m.key===state.metric?' selected':''}>${esc(m.label)}</option>`).join('');
  $('main').innerHTML=`<div class="context"><span><b>${C.runs.length}</b> methods · <b>${sum(C.runs.map(r=>r.seeds.length))}</b> completed streams</span><span><b>${sum(C.runs.map(r=>r.failures.length))}</b> prior failed attempts</span><span><b>${C.metrics.length}</b> diagnostics · <b>50</b> matched intervals · <b>34,977</b> tokens</span><span>No new page logs</span></div>
  ${C.completed?'':'<p class="error">The export is still being assembled. Rankings are provisional until all methods have been loaded.</p>'}
  <p class="chart-note"><a href="modifications.html#controlled-mechanisms">Read the controlled mechanism study</a> · <a href="modifications.html#word-entropy-study">How to interpret word H1/H2 and the shuffle comparison</a></p>
  <section class="panel" id="summary">${head('summary','Ranked comparison against the manuscript')}
   <div class="toolbar"><label class="ctl">Region <select id="scope"><option value="all">Whole manuscript</option><option value="nonbio"${state.scope==='nonbio'?' selected':''}>All except biological (4a)</option>${C.groups.map(g=>`<option value="${g}"${g===state.scope?' selected':''}>${esc(g)}${g==='4a'?' · biological':''}</option>`).join('')}</select></label><span class="small muted">Lower error score = closer. All methods remain in the ranking population.</span></div>
   <details class="method"><summary>Ranking method and adjustable weights</summary><p>For each statistic, compute token-weighted absolute error across matching bifolium intervals, separately for each seed, then average seeds. Convert errors to relative ranks among completed methods, average within each family, and give the six families equal weight by default. This prevents four entropy measurements from counting four times as much as a single family. Colours and scores describe relative fit, not statistical significance, historical plausibility, or absolute adequacy.</p><p>The two configurations with stalled attempts are unranked; their successful seed is still shown. Seed counts differ, so small rank differences should not be treated as decisive. Word identity and fitted-target error are displayed but excluded. Changing the plotted methods does not change anyone’s score.</p><div class="weights">${C.families.map((f,i)=>`<label>${esc(f)}<select data-weight="${i}">${[0,.5,1,2,3].map(v=>`<option value="${v}"${state.weights[f]===v?' selected':''}>${v}×</option>`).join('')}</select></label>`).join('')}</div><button type="button" id="resetWeights">Equal weights</button></details>
   <label class="ctl"><input type="checkbox" id="wordrank"${state.wordrank?' checked':''}> Include word entropy in ranking (only methods scored on every completed seed)</label>
   <p class="chart-note">Word H1/H2 and shuffle-adjusted order are available for retained texts, selected exact replays and the new controlled experiments. A dash means unscored, never zero. The option above adds word entropy as one equally weighted family and excludes incomplete word-statistic coverage from ranks. Summary-only methods retain every previously scored interval statistic; detailed distributions are kept for the focus set.</p>
   <div class="scale-note"><span>Closer</span><i class="error-scale"></i><span>Farther · cells show error percentile, 0–100</span></div><div class="rank-feedback" id="rankFeedback" aria-live="polite">Select a cell to inspect its raw error and profile. Select a method to inspect its text or retention status.</div><div id="rankTable"></div>
  </section>
  <section class="panel" id="profiles">${head('profiles','Every statistic through the manuscript')}
   <div class="toolbar"><label class="ctl">Measure <select id="metric">${metricOptions}</select></label><label class="ctl">Display <select id="view"><option value="actual">Actual values</option><option value="difference"${state.view==='difference'?' selected':''}>Difference from manuscript</option></select></label><button type="button" id="plotTop">Plot top five</button><button type="button" id="plotDefaults">Main comparisons</button></div>
   <details class="method"><summary>Choose methods for profiles and the text gallery</summary><p>All completed methods are available here. The global Runs menu controls Charts and Innovation.</p><div class="plot-options">${C.runs.map(r=>`<label><input type="checkbox" data-plot="${r.id}"${state.plot.includes(r.id)?' checked':''}>${SG.runName(r,r.short)}</label>`).join('')}</div></details>
   <div id="profileLegend"></div><div id="mainProfile"></div><p class="metric-description" id="metricDescription"></p><p class="chart-note">Bands show the full range across available completed seeds, not confidence intervals. Intervals share token budgets; their labels are manuscript bifolia. Region selection filters the ranking, profiles, and A/B error comparison. Cumulative vocabulary still starts at the beginning of the manuscript. Entropies are estimated separately within each bifolium; their average need not equal entropy measured on a whole pooled region.</p>
   <div class="profile-grid" id="profileGrid"></div>
  </section>
  <section class="panel" id="examples">${head('examples','See the differences in the text')}
   <div class="toolbar"><label class="ctl">Method <select id="exampleRun">${runOptions(state.run)}</select></label><label class="ctl">Bifolium <select id="node">${C.nodes.map((n,i)=>`<option value="${i}"${i===state.node?' selected':''}>${esc(n.id)} · ${esc(n.group)}</option>`).join('')}</select></label><label class="ctl">Sample <select id="window"><option value="middle">Fixed central 100 tokens</option><option value="low"${state.window==='low'?' selected':''}>Near lowest diversity</option></select></label><label class="ctl">Highlight <select id="overlay">${Object.entries(OVERLAYS).map(([k,l])=>`<option value="${k}"${k===state.overlay?' selected':''}>${esc(l)}</option>`).join('')}</select></label><label class="ctl"><input type="checkbox" id="gallery"${state.gallery?' checked':''}> Show all plotted methods</label></div>
   <div id="componentControl"></div><p id="exampleContext" class="chart-note"></p><div class="overlay-key" id="overlayKey"></div><div class="text-pair" id="textPair"><p class="loading">Loading excerpts…</p></div><div id="textMetrics"></div>
  </section>
  <section class="panel" id="failures">${head('failures','Where a method loses diversity')}
   <p class="metric-description">D50 is the distinct-form share among the last 50 tokens. The manuscript’s minimum is ${fmt(C.observed.degeneracy.min,2)}, with ${int(C.observed.degeneracy.levels['0.5'].tokens)} positions below 0.5. The table counts full windows only. Means across seeds describe frequency; the minimum shows the worst point in any completed seed.</p><div id="failureTable"></div><p class="chart-note">“Inspect” opens the main completed seed’s lowest-diversity interval; the worst point over all seeds can be lower. A long low-diversity stretch is evidence of repetitive output. It does not establish the internal cause without a trace. Failed attempts are reported separately and are never silently treated as successful runs.</p>
  </section>
  <section class="panel" id="mechanisms">${head('mechanisms','Enabled mechanisms and their effects')}
   ${SC.mechanismNote()}<div class="toolbar"><label class="ctl">Method A <select id="methodA">${runOptions(state.base)}</select></label><label class="ctl">Method B <select id="methodB">${runOptions(state.run)}</select></label><button type="button" data-pair="noinnov_memory,governed">Memory: innovator off / on</button><button type="button" data-pair="exp_native_ops_null,exp_native_ops">Operation pressure off / on</button><button type="button" data-pair="exp_spread_native,exp_spread_edit_tokens">Two pages: editor off / on</button></div><div id="effectComparison"></div>
   <label class="ctl"><input type="checkbox" id="paired"${state.paired?' checked':''}> Use matching seed numbers for A/B effects where available</label><details class="method" open><summary>All methods: mechanism matrix</summary><div class="mechanism-matrix">${SC.mechanismTable(C.runs)}</div></details>
  </section>`;
  SG.bindShares($('main'),shareState);
  for(const a of document.querySelectorAll('.comparison-jumps a'))a.addEventListener('click',e=>{e.preventDefault();const section=new URLSearchParams(a.hash.slice(1)).get('section');setHash({...shareState(),section});SG.restoreSection();});
  const metric=k=>C.metrics.find(m=>m.key===k),indices=()=>C.nodes.map((n,i)=>i).filter(i=>ComparisonMath.inScope(C.nodes[i],state.scope));
  const scopeLabel=()=>state.scope==='all'?'whole manuscript':state.scope==='nonbio'?'all except biological (4a)':'group '+state.scope;
  const shortMetric={component:'Comp.',length:'Length',mattr:'MATTR',types:'Types',top10:'Top 10',clustering:'Bag gap',births:'New',cumulative:'Cumul.',h1:'H1 EVA',h2:'H2 EVA',h1_slot:'H1 unit',h2_slot:'H2 unit',word_h1:'H1 word †',word_h2:'H2 word †',word_order_gain:'Order †',pair_excess:'Pairs',repeat:'Ident.',degenerate:'D < .5',minimum:'Min. D',short:'o/y/qo',word_tv:'TV †',component_fit:'Fit †'};
  let ranking=[],exampleVersion=0;
  function renderRanking(){
   ranking=ComparisonMath.ranking(C,state.scope,state.weights,state.wordrank);
   const families=[...new Set(C.metrics.map(m=>m.family))];
   for(const k of ['word_h1','word_h2','word_order_gain'])shortMetric[k]=({word_h1:'H1 word',word_h2:'H2 word',word_order_gain:'Order'})[k]+(state.wordrank?'':' †');
   $('rankTable').innerHTML=`<div class="table-wrap rank-wrap"><table class="rank-table"><thead><tr><th class="method-cell" rowspan="2">Method · completed seeds</th><th class="rank-score" rowspan="2">Overall<br>error score</th>${families.map(f=>`<th class="family-col" colspan="${C.metrics.filter(m=>m.family===f).length}">${esc(f)}</th>`).join('')}</tr><tr>${C.metrics.map(m=>`<th class="metric-col" title="${esc(m.label+' · '+m.unit)}${m.rank?'':' · unranked diagnostic'}"><button type="button" aria-label="${esc(m.label)}" data-metric="${m.key}">${esc(shortMetric[m.key])}</button></th>`).join('')}</tr></thead><tbody>${ranking.map(row=>{const r=row.run,m=r.mechanisms;return `<tr class="${r.id===state.run?'selected':''}"><td class="method-cell"><span class="rank-number">${row.rank??'—'}</span><button type="button" class="rank-method" data-run="${r.id}">${SG.runName(r,r.short)}</button><div class="rank-sub">${r.seeds.length} seed${r.seeds.length===1?'':'s'} · governor ${m.governor?'on':'off'} · innovator ${m.slot_innovator?'on':'off'}${m.bounded_editor?' · editor on':''}${r.failures.length?' · incomplete':''}</div></td><td class="rank-score">${row.score==null?'Unranked':fmt(row.score,1)}${row.score==null?'':`<div class="score-track"><i style="width:${row.score}%"></i></div>`}</td>${C.metrics.map(m=>{const p=row.metrics[m.key],e=r.errors[state.scope][m.key],d=r.signed[state.scope][m.key];return `<td class="rank-cell${m.rank?'':' diagnostic'}"><button type="button" data-cell="${r.id}|${m.key}" style="--strength:${finite(p)?Math.round(p*64):0}%" title="${esc(`${r.label}: ${m.label}. Mean absolute error ${fmt(e,m.digits)} ${m.unit}; signed difference ${signed(d,m.digits)}. Click to inspect.`)}">${finite(p)?fmt(p*100,0):'—'}</button></td>`;}).join('')}</tr>`;}).join('')}</tbody></table></div>`;
   C.metrics.forEach((m,i)=>{if(m.family!=='Word entropy')return;const th=$('rankTable').querySelectorAll('thead tr')[1].children[i];th.title=m.label+' · '+m.unit+(state.wordrank?' · included in ranking':' · unranked diagnostic');for(const td of $('rankTable').querySelectorAll(`tbody tr td:nth-child(${i+3})`))td.classList.toggle('diagnostic',!state.wordrank);});
  }
  function series(k){
   const idx=indices(),obs=C.observed.series[k],delta=state.view==='difference';
   const out=[{label:delta?'Manuscript (zero)':'Manuscript',color:'var(--obs)',width:2.6,dots:idx.length===1,values:idx.map(i=>delta?0:obs[i])}];
   for(const id of state.plot){const r=runById.get(id);if(!r||!r.series[k].some(finite))continue;const n=r.metric_seed_count?.[k]??r.seeds.length;out.push({label:r.short+(n!==r.seeds.length?` (${n} scored seed${n===1?'':'s'})`:''),color:r.color,dash:r.dash,dots:idx.length===1,values:idx.map(i=>finite(r.series[k][i])?r.series[k][i]-(delta?obs[i]:0):null),band:n>1?r.bands[k].map(b=>idx.map(i=>finite(b[i])?b[i]-(delta?obs[i]:0):null)):null});}
   return out;
  }
  function plot(k,height=210,width=900){const idx=indices(),m=metric(k);return lineChart(series(k),idx.map(i=>C.nodes[i].id),{groups:idx.map(i=>C.nodes[i].group),height,width,zero:false,title:m.label,tipDigits:m.digits,digits:m.digits>2?2:m.digits});}
  function renderProfiles(){
   $('metric').value=state.metric;$('view').value=state.view;
   document.querySelectorAll('[data-plot]').forEach(el=>{el.checked=state.plot.includes(el.dataset.plot);});
   $('profileLegend').innerHTML=legend(series(state.metric));$('mainProfile').innerHTML=plot(state.metric,300);
   const missing=state.plot.filter(id=>!runById.get(id).series[state.metric].some(finite));
   $('metricDescription').textContent=DESCRIPTIONS[state.metric]+' Units: '+metric(state.metric).unit+'.'+(missing.length?' Not scored for '+missing.map(id=>runById.get(id).short).join(', ')+'.':'');
   $('profileGrid').innerHTML=C.metrics.map(m=>`<article class="profile-card" id="profile-${m.key}"><h3><span>${esc(m.label)}</span><span class="card-tools"><button type="button" data-focus="${m.key}">Enlarge</button><button type="button" data-profile-share="${m.key}">Copy link</button></span></h3>${legend(series(m.key))}${plot(m.key,180)}<p class="chart-note">${esc(m.unit)} · ${esc(scopeLabel())}${state.view==='difference'?' · difference from MS':''}${m.rank?'':' · diagnostic, unranked'}</p></article>`).join('');
   if(state.wordrank)for(const k of ['word_h1','word_h2','word_order_gain']){const el=$('profile-'+k).querySelector('.chart-note');el.textContent=el.textContent.replace(' · diagnostic, unranked',' · included in word-entropy ranking');}
  }
  function renderFailures(){
   const rows=[...C.runs].sort((a,b)=>b.failures.length-a.failures.length||b.degeneracy.share-a.degeneracy.share);
   $('failureTable').innerHTML=`<div class="table-wrap"><table class="failure-table"><thead><tr><th>Method</th><th class="num">Minimum D50<br>worst seed</th><th class="num">Positions &lt; 0.5<br>seed mean</th><th class="num">Share</th><th class="num">Stretches<br>seed mean</th><th class="num">Longest stretch<br>seed mean</th><th>Completion / example</th></tr></thead><tbody><tr><td>Manuscript</td><td class="num">${fmt(C.observed.degeneracy.min,2)}</td><td class="num">0</td><td class="num">0%</td><td class="num">0</td><td class="num">0</td><td>Observed reference</td></tr>${rows.map(r=>{const d=r.degeneracy;return `<tr><td>${SG.runName(r,r.short)}</td><td class="num">${fmt(d.minimum,2)}</td><td class="num">${fmt(d.tokens,1)}</td><td class="num">${pct(d.share,2)}</td><td class="num">${fmt(d.stretches,1)}</td><td class="num">${fmt(d.longest,1)}</td><td>${r.failures.map(f=>`<div class="stalled">Seed ${f.seed} stalled${f.tokens!=null?` after ${int(f.tokens)} tokens`:''}: ${esc(f.reason)}</div>`).join('')}<button type="button" data-inspect="${r.id}">Inspect main seed</button></td></tr>`;}).join('')}</tbody></table></div>`;
  }
  const overlayNotes={
   diversity:'Amber underline: spelling occurred in the preceding 50 tokens. Pink background: the full rolling window contains fewer than 25 distinct forms. Hover for the exact D50. These historical flags use the full stream, not just the excerpt. MATTR, distinct forms and clustering are summarized below.',
   novelty:'Green: this token is the first appearance of its spelling anywhere in its own stream. Existing forms are uncoloured. This reveals where novelty is occurring; more green is not automatically closer to the manuscript.',
   forms:'Darker amber marks forms that recur often within this 100-token excerpt. Hover for the excerpt count. The table below measures concentration and vocabulary over the complete interval.',
   short:'Red backgrounds mark the exact spellings o, y, and qo, which dominated the original far0 failures. Other short forms are left uncoloured.',
   length:'Redder backgrounds mark shorter words, with unit length on hover. Units combine ch, sh, benched gallows and e/i runs. Both short-form excess and overlong forms can be mismatches.',
   h1:'Blue symbols are underrepresented, red symbols overrepresented in the selected generated interval compared with the manuscript interval. The same frequency-ratio colouring is applied to both excerpts. These are raw EVA symbols; H1 and combined-unit H1 are distribution-level statistics, shown below.',
   h2:'Redder symbols follow transitions that are rarer under the manuscript interval’s EVA transition model (0.5 pseudocount per possible next symbol). Hover for transition surprisal. This illustrates local constraints; it is not a per-word H2 contribution, nor the difference between the two H2 scores. Spaces participate in the model.',
   pairs:'Amber backgrounds mark tokens belonging to a nonidentical adjacent pair repeated within this excerpt; pink marks an identical adjacent pair. Line breaks are respected. The full-interval shuffle-adjusted reuse score below is a separate measurement, with chance controlled for.',
   component:'Highlighted words carry the selected component, using the same matcher as the governor. Blue means the generated interval has too few carriers, red means too many, relative to the manuscript per 10,000 tokens. This is an observed rate mismatch, not a replay of internal pressure.'
  };
  function excerptHTML(sample,P,O,feature){
   const counts=new Map();sample.words.forEach(w=>counts.set(w,(counts.get(w)||0)+1));const breaks=new Set(sample.breaks),pairCounts=new Map(),pairFlags=new Map();
   for(let i=1;i<sample.words.length;i++)if(!breaks.has(i)){const k=sample.words[i-1]+' '+sample.words[i];pairCounts.set(k,(pairCounts.get(k)||0)+1);}
   for(let i=1;i<sample.words.length;i++)if(!breaks.has(i)){const same=sample.words[i-1]===sample.words[i],count=pairCounts.get(sample.words[i-1]+' '+sample.words[i]);if(same||count>1){pairFlags.set(i,{same,count});pairFlags.set(i-1,{same,count});}}
   const gp=P.glyphs[state.node],go=O.glyphs[state.node],alphabet=new Set([...Object.keys(gp),...Object.keys(go)]),ng=sum(Object.values(gp)),no=sum(Object.values(go)),tr=O.transitions[state.node],rows={};
   for(const [k,n] of Object.entries(tr)){const a=k.split('\u0001')[0];rows[a]=(rows[a]||0)+n;}
   const matches=feature?feature.matcher:null;let html='',line=1;
   const begin=()=>`<div class="line"><span class="ln">${line++}</span><span class="words">`;
   html+=begin();
   sample.words.forEach((w,i)=>{
    if(breaks.has(i))html+='</span></div>'+begin();
    let cls='tok written',style='',body=esc(w),tip=`Token ${int(sample.start+i+1)} · ${esc(w)}`;
    if(state.overlay==='diversity'){if(sample.recent[i])cls+=' recent';if(sample.d50[i]!=null&&sample.d50[i]<.5)cls+=' o-dg';tip+=`<br>D50 ${fmt(sample.d50[i],2)} · ${sample.recent[i]?'seen':'not seen'} in preceding 50`;}
    if(state.overlay==='novelty'){if(sample.new[i])cls+=' o-new';tip+='<br>'+(sample.new[i]?'First appearance in this stream':'Already appeared earlier');}
    if(state.overlay==='forms'){style=`background:color-mix(in srgb,var(--hapax) ${Math.min(55,(counts.get(w)-1)*7)}%,transparent)`;tip+=`<br>${counts.get(w)} appearances in this excerpt`;}
    if(state.overlay==='short'&&['o','y','qo'].includes(w))cls+=' short';
    if(state.overlay==='length'){const n=SG.units(w).length;style=`background:color-mix(in srgb,var(--dv-red) ${Math.max(0,7-n)*7}%,transparent)`;tip+=`<br>${n} combined glyph units`;}
    if(state.overlay==='pairs'&&pairFlags.has(i)){const p=pairFlags.get(i);cls+=p.same?' o-dg':'';if(!p.same)style='background:color-mix(in srgb,var(--hapax) 25%,transparent)';tip+=`<br>${p.same?'Identical adjacent words':'Member of a repeated pair'} · pair count ${p.count} in excerpt`;}
    if(state.overlay==='component'&&feature&&matches.X(w).includes(feature.index)){const color=feature.generated>=feature.observed?'var(--dv-red)':'var(--dv-blue)';style=`background:color-mix(in srgb,${color} 26%,transparent)`;tip+=`<br>Carrier of ${esc(feature.name)} · MS ${fmt(feature.observed,1)}, generated ${fmt(feature.generated,1)} / 10k`;}
    if(state.overlay==='h1'||state.overlay==='h2'){
     let previous=' ';body=SG.rawUnits(w).map(g=>{
      let strength,color,gtip;
      if(state.overlay==='h1'){const pg=((gp[g]||0)+.5)/(ng+.5*alphabet.size),po=((go[g]||0)+.5)/(no+.5*alphabet.size),z=Math.log2(pg/po);strength=Math.min(60,Math.abs(z)*25);color=z>=0?'var(--dv-red)':'var(--dv-blue)';gtip=`${esc(g)} · log₂ frequency ratio ${signed(z,2)}`;}
      else{const p=((tr[previous+'\u0001'+g]||0)+.5)/((rows[previous]||0)+.5*alphabet.size),bits=-Math.log2(p);strength=Math.min(65,Math.max(0,bits-1)*10);color='var(--dv-red)';gtip=`${previous===' '?'space':esc(previous)} → ${esc(g)} · manuscript-model surprisal ${fmt(bits,2)} bits`;}
      previous=g;return `<span class="glyph" style="--glyph-bg:color-mix(in srgb,${color} ${strength}%,transparent)" title="${esc(gtip.replaceAll('&gt;','>'))}">${esc(g)}</span>`;
     }).join('');
    }
    html+=`<span class="${cls}" style="${style}" data-tip="${esc(tip)}">${body}</span>`;
   });return html+'</span></div>';
  }
  async function renderExamples(){
   const version=++exampleVersion,r=runById.get(state.run),chosen=(state.gallery?[...new Set([state.run,...state.plot])].map(id=>runById.get(id)):[r]).filter(r=>r.detail_available!==false);
   $('exampleRun').value=state.run;$('methodB').value=state.run;$('node').value=state.node;$('window').value=state.window;$('overlay').value=state.overlay;$('gallery').checked=state.gallery;
   if(r.detail_available===false){
    $('componentControl').innerHTML='';$('overlayKey').textContent='';$('exampleContext').textContent='Summary-only retention';
    $('textPair').innerHTML=`<p class="chart-note">${esc(r.label)} retains its scalar interval metrics, seed summaries and innovation profiles. Detailed glyph, component and bigram distributions and annotated excerpts are not retained for this method. Use the profiles above to inspect its results.</p>`;
    $('textMetrics').innerHTML='';return;
   }
   try{
    const [O,...packs]=await Promise.all([SC.pack('observed'),...chosen.map(rr=>SC.pack(rr.main))]);if(version!==exampleVersion)return;
    const primary=packs[0],node=C.nodes[state.node];let feature=null;
    if(state.overlay==='component'){
     const model=await SG.load('data/model.json.gz?v=9e59dfb205');if(version!==exampleVersion)return;
     const features=primary.features[state.node],f=features.find(x=>String(x.index)===state.component)||features[0];state.component=String(f.index);feature={...f,matcher:SG.matcher(model.features),column:model.common.indexOf(f.index)};
     $('componentControl').innerHTML=`<label class="ctl">Largest component mismatches <select id="component">${features.map(x=>`<option value="${x.index}"${x.index===f.index?' selected':''}>${esc(x.name)} · ${signed(x.generated-x.observed,1)} / 10k</option>`).join('')}</select></label>`;
     $('component').onchange=()=>{state.component=$('component').value;save();renderExamples();};
    }else $('componentControl').innerHTML='';
    $('overlayKey').textContent=overlayNotes[state.overlay];
    $('exampleContext').textContent=`${node.id} · group ${node.group} · manuscript pages ${node.pages.join(', ')} · ${int(node.N)} tokens in the matched interval. ${state.window==='low'?'Each excerpt is deliberately centred near its own lowest D50, not selected as a typical passage.':'Each excerpt uses the same central token-budget position.'} Original line breaks are retained; line numbers below are relative to the excerpt. Metrics use the full interval.`;
    const card=(P,rr)=>{const sample=P.samples[state.node][state.window],s=P.series,ms=rr?SC.mechanisms(rr):null,colourPack=rr?P:primary,ownFeature=feature?{...feature,generated:100*colourPack.effects[feature.column][state.node]}:null;return `<article class="excerpt"><h3>${rr?SG.runName(rr):'Manuscript'}</h3><p class="sample-note">${rr?`Main completed seed ${P.seed} · governor ${rr.mechanisms.governor?'on':'off'} · slot innovator ${ms.innovator} · editor ${ms.editor}`:'Observed text'}<br>Stream tokens ${int(sample.start+1)}–${int(sample.start+sample.words.length)}</p><div class="text">${excerptHTML(sample,colourPack,O,ownFeature)}</div><p class="chart-note">MATTR ${fmt(s.mattr[state.node],3)} · distinct ${int(s.distinct[state.node])} · H2 ${fmt(s.h2[state.node],3)} · minimum D50 ${fmt(s.minimum[state.node],2)}</p></article>`;};
    $('textPair').innerHTML=card(O,null)+packs.map((P,i)=>card(P,chosen[i])).join('');SG.attachTips($('textPair'));
    $('textMetrics').innerHTML=`<details class="method" open><summary>All interval metrics: manuscript and ${esc(r.short)} (main completed seed ${primary.seed})</summary><div class="table-wrap"><table class="metric-readout"><thead><tr><th>Measure</th><th class="num">Manuscript</th><th class="num">Generated</th><th class="num">Difference</th><th>Unit</th></tr></thead><tbody>${C.metrics.map(m=>{const o=O.series[m.key][state.node],g=primary.series[m.key]?.[state.node];return `<tr><td><button type="button" data-text-metric="${m.key}">${esc(m.label)}</button></td><td class="num">${fmt(o,m.digits)}</td><td class="num">${fmt(g,m.digits)}</td><td class="num">${signed(g-o,m.digits)}</td><td>${esc(m.unit)}</td></tr>`;}).join('')}</tbody></table></div><p class="chart-note">Profile charts average available seeds; this table refers to the actual seed displayed. Entropy and distribution metrics belong to a text distribution, not to a single highlighted word. Choose a measure to see its description and associated overlay.</p></details>`;
   }catch(e){if(version===exampleVersion)SG.error($('textPair'),e);}
  }
  function renderEffects(){
   const a=runById.get(state.base),b=runById.get(state.run);$('methodA').value=a.id;$('methodB').value=b.id;
   const am=SC.mechanisms(a),bm=SC.mechanisms(b),names={pressure:'Governor pressure',innovator:'Slot innovator',editor:'Bounded editor',supply:'Source supply / memory'};
   const changes=Object.keys(names).filter(k=>am[k]!==bm[k]).map(k=>`${names[k]}: ${am[k]} → ${bm[k]}`);
   const commonSeeds=Object.keys(a.seed_errors||{}).filter(s=>b.seed_errors?.[s]),paired=state.paired&&commonSeeds.length>0;
   const error=(r,k)=>paired?mean(commonSeeds.filter(s=>finite(a.seed_errors[s][state.scope][k])&&finite(b.seed_errors[s][state.scope][k])).map(s=>r.seed_errors[s][state.scope][k])):r.errors[state.scope][k];
   const settingKeys=[...new Set([...Object.keys(a.settings||{}),...Object.keys(b.settings||{})])].filter(k=>JSON.stringify(a.settings?.[k])!==JSON.stringify(b.settings?.[k]));
   $('effectComparison').innerHTML=`<div class="mechanism-change"><b>${esc(a.short)} → ${esc(b.short)}</b>${changes.length?`<ul>${changes.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`:'<p>The displayed mechanism switches match; operation details or parameter values may still differ.</p>'}<p>Differences below are observed configuration effects. When several settings change, they cannot be attributed to the innovator or governor alone. There is no complete governor × innovator factorial experiment in this catalog.</p><p>${paired?`Matching seed numbers: ${commonSeeds.join(', ')}. Same seeds do not imply identical random draws after changing the algorithm.`:'All available completed seeds. No pairing is applied.'}</p>${settingKeys.length?`<details><summary>Exact changed settings</summary><ul>${settingKeys.map(k=>`<li><code>${esc(k)}</code>: ${esc(JSON.stringify(a.settings?.[k])??'default')} → ${esc(JSON.stringify(b.settings?.[k])??'default')}</li>`).join('')}</ul></details>`:''}</div><div class="table-wrap"><table><thead><tr><th>Mean absolute error against MS · ${esc(state.scope)}</th><th class="num">${SG.runName(a,a.short)}</th><th class="num">${SG.runName(b,b.short)}</th><th class="num">B − A error</th><th>Result</th></tr></thead><tbody>${C.metrics.map(m=>{const av=error(a,m.key),bv=error(b,m.key),d=finite(av)&&finite(bv)?bv-av:NaN;return `<tr><td>${esc(m.label)} <span class="muted small">${esc(m.unit)}</span></td><td class="num">${fmt(av,m.digits)}</td><td class="num">${fmt(bv,m.digits)}</td><td class="num">${signed(d,m.digits)}</td><td>${!finite(d)?'Not scored for both methods':Math.abs(d)<.5*10**(-m.digits)?'similar at shown precision':d<0?'B closer':'A closer'}</td></tr>`;}).join('')}</tbody></table></div>`;
  }
  function selectMetric(key){state.metric=key;state.overlay=metricOverlay(key);renderProfiles();renderExamples();save();}
  function selectRun(id){state.run=id;renderRanking();renderEffects();renderExamples();save();}
  $('wordrank').onchange=()=>{state.wordrank=$('wordrank').checked;renderRanking();renderProfiles();save();};
  $('scope').onchange=()=>{state.scope=$('scope').value;if(!ComparisonMath.inScope(C.nodes[state.node],state.scope)){state.node=C.nodes.findIndex(n=>ComparisonMath.inScope(n,state.scope));renderExamples();}renderRanking();renderProfiles();renderEffects();save();};
  $('metric').onchange=()=>selectMetric($('metric').value);$('view').onchange=()=>{state.view=$('view').value;renderProfiles();save();};
  $('plotTop').onclick=()=>{state.plot=ranking.filter(r=>r.rank!=null).slice(0,5).map(r=>r.run.id);renderProfiles();if(state.gallery)renderExamples();save();};
  $('plotDefaults').onclick=()=>{state.plot=defaults;renderProfiles();if(state.gallery)renderExamples();save();};
  document.querySelectorAll('[data-plot]').forEach(el=>{el.onchange=()=>{state.plot=[...document.querySelectorAll('[data-plot]:checked')].map(x=>x.dataset.plot);renderProfiles();if(state.gallery)renderExamples();save();};});
  document.querySelectorAll('[data-weight]').forEach(el=>{el.onchange=()=>{state.weights[C.families[+el.dataset.weight]]=+el.value;renderRanking();save();};});
  $('resetWeights').onclick=()=>{C.families.forEach(f=>{state.weights[f]=1;});document.querySelectorAll('[data-weight]').forEach(el=>{el.value='1';});renderRanking();save();};
  $('exampleRun').onchange=()=>selectRun($('exampleRun').value);$('methodB').onchange=()=>selectRun($('methodB').value);
  $('methodA').onchange=()=>{state.base=$('methodA').value;renderEffects();save();};
  $('paired').onchange=()=>{state.paired=$('paired').checked;renderEffects();save();};
  for(const key of ['node','window','overlay'])$(key).onchange=()=>{state[key]=key==='node'?+$(key).value:$(key).value;renderExamples();save();};
  $('gallery').onchange=()=>{state.gallery=$('gallery').checked;renderExamples();save();};
  $('main').addEventListener('click',async e=>{
   const b=e.target.closest('button');if(!b)return;
   if(b.dataset.cell){const [id,key]=b.dataset.cell.split('|'),r=runById.get(id),m=metric(key);state.run=id;state.metric=key;state.overlay=metricOverlay(key);if(!state.plot.includes(id))state.plot.push(id);$('rankFeedback').textContent=`${r.label} · ${m.label}: absolute error ${fmt(r.errors[state.scope][key],m.digits)} ${m.unit}; signed deviation ${signed(r.signed[state.scope][key],m.digits)}. ${DESCRIPTIONS[key]}`;renderRanking();renderProfiles();renderEffects();renderExamples();save();}
   if(b.dataset.run){selectRun(b.dataset.run);$('examples').scrollIntoView({block:'start'});}
   if(b.dataset.metric){selectMetric(b.dataset.metric);$('profiles').scrollIntoView({block:'start'});}
   if(b.dataset.textMetric){selectMetric(b.dataset.textMetric);$('metricDescription').scrollIntoView({block:'center'});}
   if(b.dataset.focus){const k=b.dataset.focus;SG.openOverlay(esc(metric(k).label),`${legend(series(k))}${plot(k,480,1200)}<p>${esc(DESCRIPTIONS[k])}</p>`);}
   if(b.dataset.profileShare){const u=new URL(location.href);u.hash=new URLSearchParams({...shareState(),metric:b.dataset.profileShare,section:'profile-'+b.dataset.profileShare}).toString();try{await navigator.clipboard.writeText(u.href);b.textContent='Copied';setTimeout(()=>{b.textContent='Copy link';},1800);}catch(err){SG.openOverlay('Direct link',`<input class="share-url" readonly value="${esc(u.href)}">`);document.querySelector('.share-url').select();}}
   if(b.dataset.inspect){const r=runById.get(b.dataset.inspect),p=await SC.pack(r.main);state.run=r.id;state.node=p.series.minimum.indexOf(Math.min(...p.series.minimum));state.window='low';state.overlay='diversity';state.gallery=false;renderRanking();renderEffects();await renderExamples();setHash({...shareState(),section:'examples'});$('examples').scrollIntoView({block:'start'});}
   if(b.dataset.pair){const [a,bb]=b.dataset.pair.split(',');if(!valid(a)||!valid(bb))return;state.base=a;state.run=bb;state.plot=[a,bb];renderRanking();renderProfiles();renderEffects();renderExamples();save();}
  });
  $('mechanisms').insertAdjacentHTML('beforeend','<details class="method"><summary>Data and interpretation</summary><p>These are descriptive fits to the manuscript used to develop the methods, not independent predictive validation. The <a href="validation.html">Validation page</a> contains the separate held-out analyses. Ranking depends on the selected statistics and weights.</p><p><a href="data/comparison_index.json.gz?v=7cd4eabfeb" download>Download summary metrics and settings (gzip JSON)</a>. Individual statistics packs contain the distributions behind the overlays and two short excerpts per interval. Completed replays were required to reproduce the previously recorded text hashes; no experimental page or decision trace was retained.</p></details>');
  renderRanking();renderProfiles();renderFailures();renderEffects();await renderExamples();SG.restoreSection();
  addEventListener('hashchange',()=>SG.restoreSection());
 }catch(e){SG.error($('main'),e);}
})();
