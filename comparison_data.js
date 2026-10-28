"use strict";
// Statistics and brief excerpts only. No experimental page replays are loaded or created.
const SC=(()=>{
 const index=()=>SG.load('data/comparison_index.json.gz?v=7cd4eabfeb');
 const pack=key=>SG.load(`data/comparison_runs/${key}.json.gz${window.SG_RELEASE?.build?'?v='+window.SG_RELEASE.build:''}`);
 const combine=(old,extra)=>{const map=new Map(old.map(r=>[r.id,r]));for(const r of extra)map.set(r.id,{...map.get(r.id),...r});return [...map.values()];};
 async function statistics(){
  const [S,C]=await Promise.all([SG.load('data/stats.json.gz?v=865efeb4d6'),index()]);
  S.runs=combine(S.runs,C.runs);S.comparison=C;
  const chosen=SG.visibleRuns(S.runs),keys=[...new Set(['observed',...C.runs.find(r=>r.id==='timm').seeds,...chosen.flatMap(r=>r.seeds)])];
  await Promise.all(keys.map(async key=>{
   const P=await pack(key);S.streams[key]={...S.streams[key],...P.stream};
   // Aggregate the same within-interval pairs used by Comparison. Rounding
   // recovers integer counts from the six-decimal exported rates.
   const pairTotal=SG.sum(P.series.pairs);
   S.streams[key].profile.interval_repeat_rate=SG.sum(P.series.repeat.map((v,i)=>Math.round(v*P.series.pairs[i])))/pairTotal;
   if(P.effects)S.effects.runs[key]=P.effects;S.tv_by_node[key]=P.series.word_tv;
   S.mae_by_node[key]=P.series.component.map(v=>v/100);
   for(const w of [50,100,200]){S.mattr_by_node[w]??={};S.mattr_by_node[w][key]=P.series[w===100?'mattr':'mattr'+w];}
  }));
  return S;
 }
 function mechanisms(r){
  const m=r.mechanisms||{};
  const pressure=[m.source_pressure?'source choice':'',m.acceptance_pressure?'acceptance':'',m.morpher_pressure?'morpher':''].filter(Boolean).join(' + ');
  const policies={native:'native page window',page:'current page',spread:'current + preceding page',sheet:'turnable sheet',face:'exposed sheet face'};
  const supply=[policies[m.source_policy]||m.source_policy,m.memory_forms?`${m.memory_forms} remembered forms`:'',m.pool_tokens?`last ${m.pool_tokens} tokens`:'',m.fixed_list?`${m.fixed_list}-form fixed list (${m.fixed_list_select||'recent'})`:'',m.far_probability?`${SG.pct(m.far_probability,0)} far access`:'',m.previous_chance!=null?`${SG.pct(m.previous_chance,0)} preceding-page access`:'',m.startup_carry?'startup carry':'',m.motif_tokens?`${m.motif_tokens}-token motifs`:'',m.local_recency?'recent-form avoidance':''].filter(Boolean).join(' · ');
  const alphabet=m.candidate_alphabet==='visible_uniform'?'uniform visible':m.proposal_kernel==='editor'&&m.candidate_alphabet==='visible'?'donor-sampled visible':m.candidate_alphabet;
  const grammar={native:'native transition checks',learned:'native + manuscript transition threshold',local:'native + stripped-donor transitions (pilot)',page:'native + complete visible-word transitions',memory:'native + remembered glyph transitions'}[m.candidate_legality];
  const variant=m.proposal_kernel?`${m.proposal_kernel} kernel · ${alphabet} units · ${grammar} · ${m.novelty_feedback==='deficit'?'deficit feedback':SG.pct(m.attempt_rate,0)+' fixed attempts'} · ${m.require_unseen?'globally unseen candidates only':'no global novelty test'}${m.proposal_kernel==='wide'?' · manuscript rarity filter '+(m.candidate_rarity===false?'off':'on'):''}${m.native_output===false?' · native morph output replaced by copy':''}`:'';
  return {pressure:pressure||'off',supply:supply+(variant?' · '+variant:''),innovator:m.novelty_feedback==='deficit'?'deficit feedback (hybrid)':m.slot_innovator?'on':'off',editor:m.proposal_kernel?`${m.proposal_kernel} proposals`:m.bounded_editor?`${SG.pct(m.bounded_editor,0)} attempts`:'off'};
 }
 function mechanismTable(runs){return `<div class="table-wrap"><table><thead><tr><th>Method</th><th>Aesthetic governor</th><th>Slot innovator</th><th>Bounded editor</th><th>Source supply / memory</th><th>Completed seeds</th></tr></thead><tbody>${runs.map(r=>{const m=mechanisms(r);return `<tr><td>${SG.runName(r,r.short)}</td><td>${SG.esc(m.pressure)}</td><td>${m.innovator}</td><td>${m.editor}</td><td>${SG.esc(m.supply)}</td><td>${r.seeds.length}${r.failures?.length?` · ${r.failures.length} stalled`:''}</td></tr>`;}).join('')}</tbody></table></div>`;}
 function mechanismNote(){return '<p class="chart-note">The governor expresses preferences for component patterns. The slot innovator and <a href="modifications.html#editor">bounded editor</a> are separate ways of proposing new forms. “Innovator off” does not mean “mutation off”: the controlled copying variants replace the native morpher output but retain their custom edits and final validity checks. See the <a href="modifications.html#controlled-mechanisms">controlled mechanism experiments</a>. Bifolia are evaluation intervals, not preference targets supplied by identity; same-bifolium variants use the physical mapping only to restrict access to already written words. Summary-only methods retain scalar histories, without detailed distributions or page replay logs.</p>';}
 return {index,pack,combine,statistics,mechanisms,mechanismTable,mechanismNote};
})();
