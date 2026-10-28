"use strict";
// Static page geometry. Recompute only when controls change; clicks touch one window.
(() => {
 const atlas=document.querySelector('.heatmap-atlas'),selector=document.getElementById('scope');
 const size=document.getElementById('windowSize'),direction=document.getElementById('windowDirection'),colors=document.getElementById('colorMode');
 const leftReach=document.getElementById('leftReach'),aboveDepth=document.getElementById('aboveDepth'),coneAngle=document.getElementById('coneAngle'),sourceWeight=document.getElementById('sourceWeight');
 const editLimit=document.getElementById('editLimit'),candidateUnit=document.getElementById('candidateUnit');
 const rows=[...atlas.querySelectorAll('.bifolio')],pharma=new Set(['S:100-101','S:99-102','O:88-89']);
 const scopes=new Set([...selector.options].map(o=>o.value));
 const summary=document.getElementById('windowSummary'),restoreButton=document.getElementById('restoreHeatmap');
 const calculation=document.getElementById('calculationStatus'),calculationProgress=document.getElementById('calculationProgress'),calculationStage=document.getElementById('calculationStage');
 const caption=atlas.querySelector('.caption'),shared=document.getElementById('sharedChoice'),choose=document.getElementById('boxWord');
 const tokenBoxes=new Map(),entries=[],byBox=new WeakMap();
 let data=null,rolling=null,impact=null,selected=-1,origin=null,marked=[],revision=0,sizeTimer=null;
 let width=100,mode='backward',colorMode='mattr',computedWidth=0,computedMode='';
 let sourceCtx=null,sourceStats=null,sourceKey='',colorDomains={},sourceOptions={left:3,depth:8,angle:45,weight:'distance'};
 let copyCtx=null,editRadius=1,countUnit='Types';
 const copyView=()=>['minedit','candidates'].includes(colorMode);
 const spatial=()=>mode==='spatial',components=()=>['components','h1','h2','js'].includes(colorMode),advanced=()=>spatial()||components();
 for(const box of atlas.querySelectorAll('rect[data-token-indices]')){
  const entry={box,indices:box.dataset.tokenIndices.split(',').map(Number),title:box.querySelector('title')};
  entries.push(entry);byBox.set(box,entry);
  for(const i of entry.indices){if(!tokenBoxes.has(i))tokenBoxes.set(i,[]);tokenBoxes.get(i).push(box);}
 }
 function inScope(row){
  const v=selector.value,g=row.dataset.group,id=row.querySelector('h2').textContent;
  return v==='all'||v===g||(v==='late'&&['3b','3a','3c','4c','4a'].includes(g))
   ||(v==='decline'&&['3c','4c','4a'].includes(g))||(v==='early'&&['3b','3a'].includes(g))||(v==='pharma'&&pharma.has(id));
 }
 function visibility(context=new Set()){
  for(const row of rows){
   const extra=!inScope(row)&&context.has(row.querySelector('h2').textContent);
   row.hidden=!(inScope(row)||extra);row.classList.toggle('window-context',extra);
  }
 }
 function anchored(box,change){
  const before=box?.getBoundingClientRect();change();
  const after=box?.getBoundingClientRect();
  if(before?.height&&after?.height&&Math.abs(after.top-before.top)>.5)window.scrollBy({top:after.top-before.top,behavior:'instant'});
 }
 function paintColor(value){
  if(!Number.isFinite(value))return 'var(--line2)';
  return data.palette[Math.max(0,Math.min(500,Math.floor((value-.5)*1002)))];
 }
 function boxScore(indices){
  const scores=indices.map(i=>rolling.scores[i]).filter(Number.isFinite);
  return scores.length?scores.reduce((a,b)=>a+b,0)/scores.length:NaN;
 }
 const attribution=()=>colorMode==='impact'||colorMode==='change';
 const contribColors=()=>colorMode==='mattr'||colorMode==='overlay';
 // copies of a spelling in the selected window: grey once, then yellow, orange, orange-red, red for 2, 3, 4, 5+
 const copiesFill=count=>'var(--copies-'+Math.max(1,Math.min(5,count))+')';
 const contribList=document.getElementById('contribList');let contribWord=null;
 const pp=value=>(value>0?'+':value<0?'−':'')+(Math.abs(value)*100).toFixed(2)+' pp';
 function impactText(pos){
  const n=impact.windows[pos];
  return n?impact.affected[pos]+'/'+n+' containing windows affected · '+pp(impact.gain[pos])+' mean gain if this occurrence were a new spelling':'No full window contains this word';
 }
 function changeText(pos){
  if(!Number.isFinite(impact.change[pos]))return 'No previous full window to compare';
  return pp(impact.enter[pos]/width)+' arriving − '+(impact.leave[pos]*100/width).toFixed(2)+' pp leaving ('+data.words[pos-width]+') = '+pp(impact.change[pos])+' net';
 }
 function paintAttribution(){
  for(const entry of entries){
   let fill;
   if(advanced()){
    const values=entry.indices.map(i=>sourceStats?.[i]?.[metric().key]).filter(Number.isFinite);
    fill=advancedColor(values.length?values.reduce((a,b)=>a+b,0)/values.length:NaN);
   }else if(colorMode==='impact'){
    const values=entry.indices.map(i=>impact.windows[i]?impact.affected[i]/impact.windows[i]:NaN).filter(Number.isFinite);
    const value=values.length?values.reduce((a,b)=>a+b,0)/values.length:NaN;
    // The existing low-diversity colors, reversed: more repeat impact is warmer.
    fill=Number.isFinite(value)?paintColor(.9-.4*value):'var(--line2)';
   }else if(colorMode==='change'){
    const values=entry.indices.map(i=>impact.change[i]).filter(Number.isFinite);
    const value=values.length?values.reduce((a,b)=>a+b,0)/values.length:NaN;
    fill=!Number.isFinite(value)?'var(--line2)':value>1e-12?'var(--heat-single)':value<-1e-12?'var(--heat-repeat)':'var(--heat-neutral)';
   }else fill=paintColor(boxScore(entry.indices));
   entry.box.setAttribute('fill',fill);
  }
  if(advanced())for(const row of rows){
   const range=data.ranges.get(row.querySelector('h2').textContent),values=sourceStats.slice(range.start,range.end).map(s=>s[metric().key]).filter(Number.isFinite);
   const mean=values.length?values.reduce((a,b)=>a+b,0)/values.length:NaN;
   row.querySelector('header>strong').textContent=Number.isFinite(mean)?mean.toFixed(metric().key==='components'?1:3):'—';
   row.querySelector('header>span:not(.group)').textContent='mean '+metric().label;
   const bar=row.querySelector('.bar i');bar.style.width=Number.isFinite(mean)?100*metricScale(mean)+'%':'0%';bar.style.background=advancedColor(mean);
  }
 }
 function metric(){return ({minedit:{key:'minedit',label:'minimum glyph edits'},candidates:{key:'candidate'+countUnit+editRadius,label:'candidate '+(countUnit==='Types'?'spellings':'occurrences')+' ≤'+editRadius+' edits'},components:{key:'components',label:'effective pairs'},h1:{key:'h1',label:'glyph H1 · bits'},h2:{key:'h2',label:'glyph H2 · bits'},js:{key:'js',label:'JS distance'}})[colorMode]||{key:'worddiv',label:'source diversity'};}
 function metricScale(value){return copyView()?Math.min(1,value/(colorMode==='minedit'?5:10)):components()?SG_SOURCES.colorFraction(value,colorDomains[colorMode]||{low:0,high:1}):Math.max(0,Math.min(1,value));}
 function metricTicks(){
  if(copyView())return colorMode==='minedit'?['0 · copy','1','2','3','4','5+']:['0','2','5','8','10+'];
  if(!components())return ['0','.25','.50','.75','1'];
  const d=colorDomains[colorMode],digits=colorMode==='components'?1:2;if(!d?.count)return ['No scored words'];
  if(d.constant)return [d.low.toFixed(digits)+' · no variation'];
  return Array.from({length:5},(_,i)=>(i===0?'≤':i===4?'≥':'')+(d.low+(d.high-d.low)*i/4).toFixed(digits));
 }
 function advancedColor(value){if(colorMode==='minedit')return SG_COPY.distanceColor(value);return Number.isFinite(value)?paintColor(.5+.5*(colorMode==='js'?1-metricScale(value):metricScale(value))):'var(--line2)';}
 function sourceText(s){
  if(!s)return 'Calculating…';
  if(copyView())return !s.n?'No eligible earlier source with usable geometry':s.minedit+' minimum glyph edits · '+s.nearestTypes+' nearest spelling'+(s.nearestTypes===1?'':'s')+' ('+s.nearestOccurrences+' occurrences) · '+s['candidateTypes'+editRadius]+' spellings / '+s['candidateOccurrences'+editRadius]+' occurrences within '+editRadius+' edits · '+s.n+' words in cone';
  const value=s[metric().key],score=Number.isFinite(value)?value.toFixed(metric().key==='components'?1:3)+' '+metric().label:'too few contributing sources';
  return score+' · '+s.n+(spatial()?' source words':' words')+' · '+s.ess.toFixed(1)+' effective sources';
 }
 function setLegend(ticks,reverse=false){
  document.querySelector('#heatmapLegend .ticks').replaceChildren(...ticks.map(text=>{const s=document.createElement('span');s.textContent=text;return s;}));
  document.querySelector('#heatmapLegend .spectrum').style.background=reverse?'linear-gradient(90deg,#185965,#4e9c92,#a1c5ad,#ead6a1,#e9aa6c,#d56b43,#a83c35)':'';
 }
 function markRepeat(box,flags){
  const count=flags.filter(Boolean).length;
  box.classList.toggle('repeat-word',count===flags.length);
  box.classList.toggle('mixed-word',count>0&&count<flags.length);
 }
 function restoreEntry(box){
  const entry=byBox.get(box);markRepeat(box,entry.indices.map(i=>rolling.repeated[i]));
  box.classList.remove('window-member','window-selected','window-related');box.removeAttribute('aria-pressed');box.style.fill='';box.style.opacity='';
  entry.title.textContent=normalTitle(entry);
 }
 function clearMarks(){if(rolling)for(const box of marked)restoreEntry(box);marked=[];for(const g of atlas.querySelectorAll('.source-guide'))g.remove();}
 function normalTitle(entry){
  if(advanced())return entry.indices.map(i=>data.words[i]+' · '+sourceText(sourceStats?.[i])).join(' / ')+(entry.indices.length>1?' · shared box: mean of valid word scores':'');
  if(attribution())return entry.indices.map(i=>data.words[i]+' · '+(colorMode==='impact'?impactText(i):changeText(i))).join(' / ')+
   (entry.indices.length>1?' · shared box: color averages its word values':'');
  const value=boxScore(entry.indices);
  return entry.indices.map(i=>data.words[i]).join(' / ')+' · D'+width+': '+(Number.isFinite(value)?value.toFixed(3):'incomplete window')+
   (entry.indices.length>1?' · shared rectangle: mean of available full windows':'');
 }
 function instructions(){
  document.getElementById('copySettings').hidden=!copyView();
  document.getElementById('sourceSettings').hidden=!spatial();document.getElementById('sizeLabel').textContent=spatial()?'Source cap':'Window';
  size.setAttribute('aria-label',spatial()?'Source cap words':'Window words');
  colors.querySelector('option[value="mattr"]').textContent=spatial()?'Source word diversity':'MATTR';
  for(const option of colors.options)option.disabled=spatial()&&['repeat','overlay','impact','change'].includes(option.value);
  if(advanced()){
   direction.disabled=copyView();direction.title=copyView()?'Copy/edit overlays use earlier words in the spatial cone.':'';
   caption.textContent=spatial()?'Earlier words only: left on this line and above on the same page. Above-line word rectangles that intersect the cone are included, even if their centers lie outside it. Source cap '+width+'; no backfilling from other pages. The outlined target is excluded from its source pool.':'Components of the chosen '+width+'-word '+mode+' window. ';
   caption.textContent+=' '+(colorMode==='js'?'JS distance shows a difference from the whole manuscript, including later text; it is not a diversity or prediction score.':colorMode==='h2'?'H2 measures uncertainty of the next glyph unit given the current one.':colorMode==='h1'?'H1 measures diversity of individual glyph units.':colorMode==='components'?'Component diversity is the effective number of within-word glyph-pair types.':'Source word diversity is the chance that two weighted draws have different spellings; it is not MATTR.');
   caption.textContent+=' Click to inspect '+(spatial()?'the weighted sources':'the components')+'. Row means average valid target scores.'+(components()?' Gray: fewer than 5 contributing words, fewer than 3 effective contributing sources, or an incomplete window.':'');
   for(const id of ['repeatLegend','impactLegend','changeLegend'])document.getElementById(id).hidden=true;
   document.getElementById('heatmapLegend').hidden=false;setLegend(metricTicks(),colorMode==='js');
   if(components()&&colorDomains[colorMode]?.constant)document.querySelector('#heatmapLegend .spectrum').style.background=advancedColor(colorDomains[colorMode].low);
   document.getElementById('legendLabel').textContent=metric().label+(components()?' · linear · full-path '+(colorDomains[colorMode]?.trimmed?'5–95%':'range'):'')+(colorMode==='js'?' · warm = further':' · warm = lower');
   if(copyView()){
    caption.textContent='Raw Zattera glyph-unit distance to earlier words in the cleaned source cone; initial gallows are preserved. The target is excluded. '+(colorMode==='minedit'?'Color shows the smallest whole-word distance.':'Color counts '+(countUnit==='Types'?'distinct source spellings':'source occurrences')+' within '+editRadius+' edits.')+' Gray means no usable source pool. Click a target to show source spellings inside its cone and their distances. These are generic edits, not native morpher operations or evidence of copying.';
    document.getElementById('legendLabel').textContent=metric().label+(colorMode==='minedit'?' · warm = more edits':' · warm = fewer candidates');
    if(colorMode==='minedit')document.querySelector('#heatmapLegend .spectrum').style.background='linear-gradient(90deg,'+[0,1,2,3,4,5].map(SG_COPY.distanceColor).join(',')+')';
   }
   atlas.dataset.colors=colorMode;document.querySelector('.window-status').classList.toggle('idle',selected<0);return;
  }
  setLegend(['.50','.60','.70','.80','.90','1.00']);
  const before=mode==='backward'?width-1:mode==='forward'?0:Math.floor((width-1)/2),after=width-1-before;
  const span=before+' before + this word + '+after+' after';
  caption.textContent='Window: '+span+'. Follows Path 1 across pages and bifolia. Click a word to isolate its window; click it again or press Escape to restore. '+
   (colorMode==='mattr'&&selected>=0?'Words in the window are colored by how often their spelling occurs in it: each adds 1/(its copies) of a distinct form, and the score is the mean of those shares.':colorMode==='mattr'?'Colors show local diversity.':selected<0?'Repetition marks whether each word recurs within its own window.':'Repetition marks all occurrences of spellings repeated within the selected window.')+
   ' Gray means unscored text or an incomplete window.';
  if(colorMode==='impact')caption.textContent='Each word is scored across every full '+width+'-word window containing it. Color shows how often replacing this one occurrence with a new spelling would increase diversity; direction does not apply. Click to highlight the full affected neighborhood; amber outlines mark other occurrences of the same spelling.';
  if(colorMode==='change')caption.textContent='Change when this word arrives: the gain from an added spelling minus the loss from the word leaving the backward '+width+'-word window. Click to inspect both effects; amber outlines the leaving word. Forward and centered alignment do not apply.';
  if(attribution())caption.textContent+=' Row means still show MATTR'+width+'. Click again or press Escape to restore the full map.';
  direction.disabled=attribution();direction.title=attribution()?'This view attributes the effect to the word itself; direction does not apply.':'';
  document.getElementById('legendLabel').textContent='Distinct forms / '+width+' words · '+direction.selectedOptions[0].textContent+(colorMode==='overlay'?' · red outline: repeated spelling':'');
  document.getElementById('heatmapLegend').hidden=!['mattr','overlay'].includes(colorMode)||selected>=0;
  document.getElementById('repeatLegend').hidden=colorMode!=='repeat';
  document.getElementById('impactLegend').hidden=colorMode!=='impact';
  if(data)document.querySelector('.impact-spectrum').style.background='linear-gradient(90deg,'+[0,.25,.5,.75,1].map(f=>paintColor(.9-.4*f)).join(',')+')';
  document.getElementById('changeLegend').hidden=colorMode!=='change';
  document.getElementById('lossKey').textContent='−'+(100/width).toFixed(2)+' pp';
  document.getElementById('gainKey').textContent='+'+(100/width).toFixed(2)+' pp';
  document.querySelector('#repeatLegend .single-key').hidden=colorMode==='overlay';
  document.querySelector('#repeatLegend .repeat-key').textContent=colorMode==='overlay'?'Red outline: repeated spelling':'Repeated spelling';
  atlas.dataset.colors=colorMode;
  document.querySelector('.window-status').classList.toggle('idle',selected<0);
 }
 function restore(focus=false){
  const box=origin;
  anchored(box,()=>{
   clearMarks();selected=-1;atlas.classList.remove('window-mode');restoreButton.hidden=true;shared.hidden=true;contribList.hidden=true;contribWord=null;
   visibility();instructions();summary.textContent='Click any word to highlight its calculation window on the pages.';
  });
  if(focus&&box&&!box.closest('.bifolio').hidden)box.focus({preventScroll:true});
 }
 function location(i){const line=data.lines[data.lineOf[i]];return line.page+' · line '+line.locus;}
 function select(box,pos,toggle=true){
  if(!data||!rolling||atlas.hasAttribute('aria-busy'))return;
  if(advanced()){selectAdvanced(box,pos,toggle);return;}
  const indices=byBox.get(box).indices;
  if(toggle&&indices.includes(selected)){restore();return;}
  const svg=box.closest('svg');svg.querySelector('[tabindex="0"]')?.setAttribute('tabindex','-1');box.setAttribute('tabindex','0');
  const w=SG_HEATMAP.windowAt(data.words,pos,width,colorMode==='change'?'backward':mode),context=new Set(),active=new Map();
  const area=colorMode==='impact'?SG_HEATMAP.impactBounds(pos,width,data.words.length):colorMode==='change'?{start:Math.max(0,pos-width),end:pos+1}:w;
  let mapped=0;
  for(let i=area.start;i<area.end;i++){
   context.add(data.lines[data.lineOf[i]].bifolium);
   const matches=tokenBoxes.get(i)||[];if(matches.length)mapped++;
   for(const b of matches){if(!active.has(b))active.set(b,[]);active.get(b).push(i);}
  }
  anchored(box,()=>{
   clearMarks();selected=pos;origin=box;atlas.classList.add('window-mode');visibility(context);
   restoreButton.hidden=false;shared.hidden=indices.length<2;
   choose.replaceChildren(...indices.map(i=>new Option(data.words[i]+' · word '+(i+1),i,false,i===pos)));
   summary.textContent=data.words[pos]+' · '+w.unique+' distinct / '+w.size+' words'+(w.score===null?' · incomplete window; no score':' = '+w.score.toFixed(3));
   if(colorMode==='impact')summary.textContent=data.words[pos]+' · '+impactText(pos);
   if(colorMode==='change')summary.textContent=data.words[pos]+' · '+changeText(pos);
   instructions();
   caption.textContent=location(area.start)+' → '+location(area.end-1)+'. '+caption.textContent+
    (mapped<area.end-area.start?' '+(area.end-area.start-mapped)+' context tokens lack drawable coordinates; they still count in the score.':'')+
    (rows.some(r=>r.classList.contains('window-context'))?' Adjacent bifolia are temporarily shown to include the full window.':'');
   marked=[...active.keys()];renderContrib(w,active);
   for(const [b,ids] of active){
    b.classList.add('window-member');markRepeat(b,ids.map(i=>w.counts.get(data.words[i])>1));
    if(contribColors())b.style.fill=copiesFill(Math.max(...ids.map(i=>w.counts.get(data.words[i]))));
    const isSelected=ids.includes(pos);b.classList.toggle('window-selected',isSelected);
    if(isSelected)b.setAttribute('aria-pressed','true');
    b.classList.toggle('window-related',colorMode==='impact'?ids.some(i=>i!==pos&&data.words[i]===data.words[pos]):colorMode==='change'&&ids.includes(pos-width));
    byBox.get(b).title.textContent=attribution()?normalTitle(byBox.get(b)):ids.map(i=>{const c=w.counts.get(data.words[i]);return data.words[i]+': '+c+' in this window · adds 1/'+c+' of a distinct form'+(c>1?' · its '+c+' copies cost '+pp(-(c-1)/width):'');}).join(' / ')+
     (ids.length<byBox.get(b).indices.length?' · box also contains text outside this window':'');
   }
  });
 }
 function drawSourceGuide(box,pos){
  const point=sourceCtx.centers[pos];if(!point)return;
  const page=sourceCtx.pages.get(data.lines[sourceCtx.lineOf[pos]].page),depth=sourceOptions.depth*page.pitch,spread=depth*Math.tan(sourceOptions.angle*Math.PI/180);
  const ns='http://www.w3.org/2000/svg',g=document.createElementNS(ns,'g'),cone=document.createElementNS(ns,'path'),left=document.createElementNS(ns,'path');
  g.setAttribute('class','source-guide');g.setAttribute('aria-hidden','true');
  cone.setAttribute('d',`M ${point.x} ${point.y} L ${point.x-spread} ${point.y-depth} L ${point.x+spread} ${point.y-depth} Z`);
  left.setAttribute('d',`M ${point.x} ${point.y} L ${point.x-sourceOptions.left*page.wordWidth} ${point.y}`);
  g.append(cone,left);box.closest('svg').prepend(g);
 }
 function drawSourceWords(active,pos,distances){
  const ns='http://www.w3.org/2000/svg',groups=new Map();
  for(const [box,ids] of active){
   if(ids.every(i=>!sourceCtx.centers[i]))continue;
   const svg=box.closest('svg');if(!groups.has(svg)){const g=document.createElementNS(ns,'g');g.setAttribute('class','source-guide source-words');svg.append(g);groups.set(svg,g);}
   const text=document.createElementNS(ns,'text'),x=Number(box.getAttribute('x')),y=Number(box.getAttribute('y')),w=Number(box.getAttribute('width')),h=Number(box.getAttribute('height'));
   text.textContent=ids.map(i=>data.words[i]).join('/');text.setAttribute('x',x+2);text.setAttribute('y',y+h*.72);text.setAttribute('font-size',Math.min(18,h*.65));text.setAttribute('textLength',Math.max(2,w-4));text.setAttribute('lengthAdjust','spacingAndGlyphs');
   groups.get(svg).append(text);
  }
 }
 function selectAdvanced(box,pos,toggle){
  if(atlas.hasAttribute('aria-busy')||!sourceStats)return;
  const indices=byBox.get(box).indices;if(toggle&&indices.includes(selected)){restore();return;}
  const pool=spatial()?SG_SOURCES.sourcePool(sourceCtx,pos,width,sourceOptions):SG_SOURCES.windowPool(sourceCtx,pos,width,mode);
  const stat=copyView()?SG_COPY.measure(copyCtx,pos,pool,true):SG_SOURCES.measure(sourceCtx,pool,true),active=new Map(),context=new Set(),raw=new Map(pool.indices.map((i,k)=>[i,pool.weights[k]]));
  const distances=new Map(copyView()?stat.items.map(x=>[x.position,x.distance]):[]);
  const mass=pool.weights.reduce((a,b)=>a+b,0),maxWeight=Math.max(0,...pool.weights);
  for(const i of new Set([...pool.indices,pos])){
   context.add(data.lines[data.lineOf[i]].bifolium);
   for(const b of tokenBoxes.get(i)||[]){if(!active.has(b))active.set(b,[]);active.get(b).push(i);}
  }
  const svg=box.closest('svg');svg.querySelector('[tabindex="0"]')?.setAttribute('tabindex','-1');box.setAttribute('tabindex','0');
  anchored(box,()=>{
   clearMarks();selected=pos;origin=box;atlas.classList.add('window-mode');visibility(context);marked=[...active.keys()];
   restoreButton.hidden=false;shared.hidden=indices.length<2;
   choose.replaceChildren(...indices.map(i=>new Option(data.words[i]+' · word '+(i+1),i,false,i===pos)));
   summary.textContent=data.words[pos]+' · '+(pool.missingTarget?'No recorded coordinates for this target':sourceText(stat))+(spatial()&&pool.available>stat.n?' · capped from '+pool.available+' eligible words':'');
   instructions();
   if(spatial()&&!copyView()){
    caption.textContent+=' Highlighted sources vary in brightness with their relative draw weight; hover for probabilities. Settings define a geometric proxy, not Timm’s exact probability law.';
    setLegend(['0','25%','50%','75%','100%']);
    document.querySelector('#heatmapLegend .spectrum').style.background='linear-gradient(90deg,var(--surface),var(--heat-single))';
    document.getElementById('legendLabel').textContent='Source weight relative to strongest · target score shown below';
   }
   if(spatial()){drawSourceGuide(box,pos);drawSourceWords(active,pos,distances);}
   if(copyView()){setLegend(['0 · copy','1','2','3','4','5+']);document.querySelector('#heatmapLegend .spectrum').style.background='linear-gradient(90deg,'+[0,1,2,3,4,5].map(SG_COPY.distanceColor).join(',')+')';document.getElementById('legendLabel').textContent='Selected cone: distance from each source to '+data.words[pos];}
   for(const [b,ids] of active){
    b.classList.add('window-member');const isSelected=ids.includes(pos);b.classList.toggle('window-selected',isSelected);
    if(isSelected)b.setAttribute('aria-pressed','true');
    if(spatial()&&!isSelected){b.style.fill=copyView()?SG_COPY.distanceColor(Math.min(...ids.map(i=>distances.get(i)??Infinity))):'var(--heat-single)';b.style.opacity=copyView()?'1':String(.25+.75*Math.max(...ids.map(i=>raw.get(i)||0))/maxWeight);}
    byBox.get(b).title.textContent=ids.map(i=>data.words[i]+(spatial()?(i===pos?' · target; excluded from source pool':(copyView()?' · '+distances.get(i)+' glyph edits':'')+' · '+(100*(raw.get(i)||0)/mass).toFixed(2)+'% geometry weight'):' · '+sourceText(sourceStats[i]))).join(' / ');
   }
   if(copyView()){
    const near=stat.sources.filter(s=>s.distance<=editRadius),shown=(near.length?near:stat.sources.filter(s=>s.distance===stat.minedit)).slice(0,20);
    contribList.innerHTML='<span class="contrib-head">'+(near.length?'Candidates within '+editRadius+' edits':'No candidate within '+editRadius+' edits; nearest sources')+':</span>'+shown.map(s=>'<button type="button" data-copyword="'+SG.esc(s.word)+'" aria-pressed="false"><b>'+SG.esc(s.word)+'</b> · d='+s.distance+' · ×'+s.positions.length+'</button>').join('')+(near.length>20?'<span class="more">+'+(near.length-20)+' spellings</span>':'');
    contribList.hidden=!stat.n;let focus=null;
    for(const btn of contribList.querySelectorAll('button'))btn.onclick=()=>{focus=focus===btn.dataset.copyword?null:btn.dataset.copyword;for(const x of contribList.querySelectorAll('button'))x.setAttribute('aria-pressed',String(x.dataset.copyword===focus));for(const [b,ids] of active)b.classList.toggle('window-related',!!focus&&ids.some(i=>raw.has(i)&&data.words[i]===focus));};
    return;
   }
   const kind=colorMode==='h1'?'mono':colorMode==='mattr'?'word':'pairs';
   const top=kind==='word'?stat.types.slice(0,8).map(x=>({name:x.word,p:x.p})):kind==='mono'?stat.topUnits:stat.topPairs;
   contribList.innerHTML='<span class="contrib-head">'+(kind==='word'?'Weighted source spellings':kind==='mono'?'Weighted glyph units':'Weighted within-word pairs')+':</span>'+top.map(x=>'<button type="button" data-component="'+SG.esc(x.name)+'" aria-pressed="false" title="Click to outline source words containing this component"><b>'+SG.esc(x.name)+'</b> '+(100*x.p).toFixed(1)+'%</button>').join('');
   contribList.hidden=!top.length;let activeName=null;
   for(const btn of contribList.querySelectorAll('button'))btn.addEventListener('click',()=>{
    activeName=activeName===btn.dataset.component?null:btn.dataset.component;
    for(const other of contribList.querySelectorAll('button'))other.setAttribute('aria-pressed',String(other.dataset.component===activeName));
    for(const [b,ids] of active)b.classList.toggle('window-related',!!activeName&&ids.some(i=>raw.has(i)&&(kind==='word'?data.words[i]===activeName:sourceCtx.tokenFeatures[i][kind].some(([id])=>(kind==='mono'?sourceCtx.unitNames:sourceCtx.pairNames)[id]===activeName))));
   });
  });
 }
 // The selected window's repeated spellings, ranked by the forms they cost; a chip outlines that spelling's copies
 function renderContrib(w,active){
  if(attribution()){contribList.hidden=true;return;}
  const C=SG_HEATMAP.contributions(w),top=C.spellings.slice(0,12),esc=SG.esc;
  if(!C.spellings.some(s=>s.word===contribWord))contribWord=null;
  const swatch=(c,label)=>'<span class="ck"><i style="background:'+copiesFill(c)+'"></i>'+label+'</span>';
  contribList.innerHTML='<span class="contrib-head">'+w.unique+' distinct of '+w.size+' · repeats cost '+C.lost+' form'+(C.lost===1?'':'s')+(C.lost?' ('+pp(-C.lost/width)+')':'')+(C.spellings.length?':':'')+'</span>'+
   top.map(s=>'<button type="button" data-word="'+esc(s.word)+'" aria-pressed="'+(s.word===contribWord)+'" title="'+esc(s.word)+': '+s.count+' copies in this window, costing '+s.lost+' form'+(s.lost===1?'':'s')+' ('+pp(-s.lost/width)+'), '+Math.round(100*s.share)+'% of the window’s repetition. Click to outline its copies."><b>'+esc(s.word)+'</b> ×'+s.count+' <small>'+pp(-s.lost/width)+'</small></button>').join('')+
   (C.spellings.length>top.length?'<span class="more">+'+(C.spellings.length-top.length)+' more repeated</span>':'')+
   (contribColors()?'<span class="contrib-key">'+swatch(1,'once')+swatch(2,'×2')+swatch(3,'×3')+swatch(4,'×4')+swatch(5,'×5+')+'</span>':'');
  contribList.hidden=false;
  const outline=()=>{for(const [b,ids] of active)b.classList.toggle('window-related',!!contribWord&&ids.some(i=>data.words[i]===contribWord));};
  for(const btn of contribList.querySelectorAll('button[data-word]'))btn.addEventListener('click',()=>{
   contribWord=contribWord===btn.dataset.word?null:btn.dataset.word;
   for(const x of contribList.querySelectorAll('button[data-word]'))x.setAttribute('aria-pressed',String(x.dataset.word===contribWord));outline();});
  queueMicrotask(outline);
 }
 function saveHash(){SG.setHash({...SG.hash(),scope:selector.value,window:width,direction:mode,colors:colorMode,left:sourceOptions.left,depth:sourceOptions.depth,angle:sourceOptions.angle,weight:sourceOptions.weight,edits:editRadius,count:countUnit});}
 function readControls(){
  const raw=Number(size.value);
  width=Number.isFinite(raw)?Math.max(2,Math.min(1000,Math.round(raw))):100;
  size.value=width;mode=direction.value;colorMode=colors.value;
  if(copyView()){mode='spatial';direction.value=mode;}
  editRadius=Math.max(0,Math.min(3,Number(editLimit.value)||0));countUnit=candidateUnit.value==='Occurrences'?'Occurrences':'Types';
  if(spatial()&&['repeat','overlay','impact','change'].includes(colorMode)){colorMode='mattr';colors.value=colorMode;}
  const clamp=(control,lo,hi,fallback)=>{const n=Number(control.value),v=control.value!==''&&Number.isFinite(n)?Math.max(lo,Math.min(hi,n)):fallback;control.value=v;return v;};
  sourceOptions={left:clamp(leftReach,0,20,3),depth:clamp(aboveDepth,1,100,8),angle:clamp(coneAngle,0,85,45),weight:sourceWeight.value};
 }
 function recolor(){
  rolling=SG_HEATMAP.series(data.words,width,spatial()?'backward':mode);
  if(computedWidth!==width||!impact)impact=SG_HEATMAP.wordImpact(data.words,width);
  computedWidth=width;computedMode=mode;
  for(const entry of entries){
   entry.box.setAttribute('fill',paintColor(boxScore(entry.indices)));
   markRepeat(entry.box,entry.indices.map(i=>rolling.repeated[i]));
   // An incomplete window has no comparable score or repetition color.
   entry.box.classList.toggle('incomplete',entry.indices.every(i=>!Number.isFinite(rolling.scores[i])));
  }
  for(const row of rows){
   const range=data.ranges.get(row.querySelector('h2').textContent),mean=SG_HEATMAP.meanWithin(rolling.scores,range.start,range.end,width,mode);
   row.querySelector('header>strong').textContent=mean===null?'—':mean.toFixed(3);
   row.querySelector('header>span:not(.group)').textContent='mean MATTR'+width;
   const bar=row.querySelector('.bar i');bar.style.width=mean===null?'0%':Math.max(0,(mean-.5)*200)+'%';bar.style.background=paintColor(mean===null?NaN:mean);
  }
 }
 function setBusy(stage,percent=null){
  calculation.hidden=!stage;
  if(!stage){atlas.removeAttribute('aria-busy');return;}
  atlas.setAttribute('aria-busy','true');calculation.title=stage+(percent===null?'':' · '+percent+'%');
  const announcement=stage+(percent===null?'':' · '+Math.floor(percent/10)*10+'%');
  if(calculationStage.textContent!==announcement)calculationStage.textContent=announcement;
  const progress=percent===null?'':percent+'%';if(calculationProgress.textContent!==progress)calculationProgress.textContent=progress;
 }
 async function update(){
  clearTimeout(sizeTimer);
  if(!data)return;
  const ticket=++revision;
  readControls();setBusy('Updating colors');
  try{
  // Let the controls paint before the single, linear pass over the manuscript.
  await new Promise(requestAnimationFrame);if(ticket!==revision)return;
  if(advanced()){
   const key=JSON.stringify([width,mode,sourceOptions,copyView()]);
   if(key!==sourceKey){
    const stage='Calculating '+(spatial()?'spatial source pools':'component distributions');setBusy(stage,0);
    const progress=(done,total)=>{if(ticket===revision)setBusy(stage,Math.floor(100*done/total));};
    const result=copyView()?await SG_COPY.series(copyCtx,sourceCtx,width,sourceOptions,()=>ticket===revision,progress):await SG_SOURCES.series(sourceCtx,width,mode,sourceOptions,()=>ticket===revision,progress);
    if(!result||ticket!==revision)return;sourceStats=result;sourceKey=key;
    colorDomains=Object.fromEntries(['components','h1','h2','js'].map(key=>[key,SG_SOURCES.colorDomain(result.map(s=>s[key]))]));
   }
  }
  if(!rolling||computedWidth!==width||computedMode!==mode)recolor();
  // Leaving a component metric must also restore the original bifolium labels.
  if(!advanced())for(const row of rows){
   const range=data.ranges.get(row.querySelector('h2').textContent),mean=SG_HEATMAP.meanWithin(rolling.scores,range.start,range.end,width,mode);
   row.querySelector('header>strong').textContent=mean===null?'—':mean.toFixed(3);row.querySelector('header>span:not(.group)').textContent='mean MATTR'+width;
   const bar=row.querySelector('.bar i');bar.style.width=mean===null?'0%':Math.max(0,(mean-.5)*200)+'%';bar.style.background=paintColor(mean===null?NaN:mean);
  }
  paintAttribution();
  setBusy(null);
  if(selected>=0)select(origin,selected,false);else{instructions();summary.textContent='Click any word to highlight its calculation window on the pages.';}
  saveHash();
  }catch(error){
   if(ticket===revision){summary.textContent='Could not calculate this view. Change a control or reload to retry.';document.querySelector('.window-status').classList.remove('idle');console.error(error);}
  }finally{if(ticket===revision)setBusy(null);}
 }
 function fromHash(){
  const h=SG.hash();selector.value=scopes.has(h.scope)?h.scope:'late';size.value=h.window||100;
  direction.value=['backward','forward','centered','spatial'].includes(h.direction)?h.direction:'backward';
  colors.value=['mattr','repeat','overlay','impact','change','components','h1','h2','js','minedit','candidates'].includes(h.colors)?h.colors:'mattr';
  editLimit.value=['0','1','2','3'].includes(h.edits)?h.edits:'1';candidateUnit.value=h.count==='Occurrences'?'Occurrences':'Types';
  leftReach.value=h.left??3;aboveDepth.value=h.depth??8;coneAngle.value=h.angle??45;sourceWeight.value=h.weight==='uniform'?'uniform':'distance';
 }
 atlas.addEventListener('click',e=>{const box=e.target.closest('rect[data-token-indices]');if(box)select(box,byBox.get(box).indices[0]);});
 atlas.addEventListener('pointerover',e=>{const entry=byBox.get(e.target);if(data&&rolling&&entry&&!entry.box.classList.contains('window-member'))entry.title.textContent=normalTitle(entry);});
 atlas.addEventListener('focusin',e=>{const entry=byBox.get(e.target);if(data&&rolling&&entry&&!entry.box.classList.contains('window-member'))entry.title.textContent=normalTitle(entry);});
 atlas.addEventListener('keydown',e=>{
  const box=e.target.closest('rect[data-token-indices]');if(!box)return;
  if(e.key==='Enter'||e.key===' '){e.preventDefault();select(box,byBox.get(box).indices[0]);}
  else if(['ArrowLeft','ArrowRight','Home','End'].includes(e.key)){
   e.preventDefault();const siblings=[...box.closest('svg').querySelectorAll('rect[data-token-indices]:not(.invalid-geometry)')],i=siblings.indexOf(box);
   const j=e.key==='Home'?0:e.key==='End'?siblings.length-1:Math.max(0,Math.min(siblings.length-1,i+(e.key==='ArrowRight'?1:-1)));
   box.setAttribute('tabindex','-1');siblings[j].setAttribute('tabindex','0');siblings[j].focus({preventScroll:true});
   if(selected>=0)select(siblings[j],byBox.get(siblings[j]).indices[0],false);
  }
 });
 choose.addEventListener('change',()=>select(origin,Number(choose.value),false));
 restoreButton.addEventListener('click',()=>restore(true));
 document.addEventListener('keydown',e=>{if(e.key==='Escape'&&selected>=0){e.preventDefault();restore(true);}});
 for(const control of [size,direction,colors,leftReach,aboveDepth,coneAngle,sourceWeight,editLimit,candidateUnit])control.addEventListener('change',update);
 size.addEventListener('input',()=>{
  clearTimeout(sizeTimer);
  if(size.value!==''&&size.validity.valid)sizeTimer=setTimeout(update,180);
 });
 size.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();update();}});
 selector.addEventListener('change',()=>{restore();saveHash();});
 window.addEventListener('hashchange',()=>{fromHash();if(data){restore();update();}else visibility();});
 fromHash();visibility();summary.textContent='Loading manuscript windows…';setBusy('Loading manuscript');
 SG.load('data/mattr_heatmap/words.json.gz?v=270f5d56c6').then(d=>{
  const lineOf=new Uint16Array(d.words.length),ranges=new Map();
  d.lines.forEach((line,i)=>{
   lineOf.fill(i,line.start,line.end);
   if(!ranges.has(line.bifolium))ranges.set(line.bifolium,{start:line.start,end:line.end});
   else ranges.get(line.bifolium).end=line.end;
  });
  data={...d,lineOf,ranges};sourceCtx=SG_SOURCES.prepare(data);copyCtx=SG_COPY.prepare(data);
  for(const entry of entries)if(entry.indices.every(i=>sourceCtx.excluded.has(i))){entry.box.classList.add('invalid-geometry');entry.box.setAttribute('tabindex','-1');}
  update();
 }).catch(()=>{setBusy(null);summary.textContent='Could not load the manuscript windows. Reload the page to retry.';document.querySelector('.window-status').classList.remove('idle');});
})();
