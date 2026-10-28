"use strict";
(async()=>{
 const {$,esc}=SG,root=document.querySelector('.reconstruction');
 const controls={sheet:$('reconSheet'),view:$('reconView'),page:$('reconPage'),mode:$('reconMode'),color:$('reconColor'),filter:$('reconFilter'),search:$('reconSearch'),step:$('reconStep'),written:$('reconWritten'),focus:$('reconFocus')};
 const routeColors={seed:'#a4aaa9',copy:'#7eaf99',glyph1:'#b1cca4',block:'#8cbcc6',splice:'#9caed0',assembly:'#b7a2cb',glyph2:'#dabd73',introduction:'#cf887a'};
 const routeNames={seed:'Supplied seed',copy:'Exact copy',glyph1:'One glyph edit',block:'Block replacement',splice:'Two-fragment splice',assembly:'Part assembly',glyph2:'Two glyph edits',introduction:'Unexplained introduction'};
 let data,study,geo,copy,byId,bySheet,selected,inspecting=true,clock=null,visibleRows=[];
 const m=r=>controls.mode.value==='primed'&&r.primed?r.primed:r.primary;
 const record=()=>byId.get(selected),sheetRows=()=>bySheet.get(controls.sheet.value)||[];
 const number=x=>x==null||!Number.isFinite(x)?'—':String(x);
 function where(p){const line=data.lines[geo.lineOf[p]];return line.page+':'+line.locus;}
 function matches(r){
  if(controls.search.value&&!data.words[r.position].includes(controls.search.value.trim()))return false;
  const v=m(r);
  switch(controls.filter.value){
   case 'unresolved':return !r.seed&&v.chosen.kind==='introduction';
   case 'pageclose':return !r.seed&&(r.pageDistance==null||r.pageDistance>1);
   case 'pageexact':return !r.seed&&!r.pageExact;
   case 'cone':return !r.seed&&r.cone.route==='introduction';
   case 'unique':return !r.seed&&v.nearest===1;
   case 'pf':return r.pf;
   case 'rare':return !!r.rare.length;
   case 'strict':return !r.strict;
   default:return true;
  }
 }
 function fill(r){
  if(controls.color.value==='distance')return SG_COPY.distanceColor(r.cone.distance??NaN);
  if(controls.color.value==='page')return SG_COPY.distanceColor(r.pageDistance??NaN);
  if(controls.color.value==='grammar')return r.strict?'#8ebaa4':'#d7aa8a';
  return routeColors[m(r).chosen.kind];
 }
 function legend(){
  const keys=controls.color.value==='route'?Object.entries(routeNames).map(([k,v])=>[routeColors[k],v]):controls.color.value==='grammar'?[['#8ebaa4','Strict grammar accepts'],['#d7aa8a','Strict grammar rejects']]:[0,1,2,3,4,5].map(d=>[SG_COPY.distanceColor(d),d===0?'0 · exact copy':d===5?'5+ glyph edits':d+' glyph edit'+(d>1?'s':'')]);
  keys.push(['var(--line2)','No usable source geometry / empty pool']);
  $('reconLegend').innerHTML=keys.map(([c,l])=>'<span class="recon-key"><i style="background:'+c+'"></i>'+esc(l)+'</span>').join('')+'<span class="recon-key">Outline: selected word · pink: proposed parent · teal: cone source</span>';
 }
 function stop(){if(clock)clearInterval(clock);clock=null;$('reconPlay').textContent='Play';$('reconPlay').setAttribute('aria-pressed','false');}
 function pageOptions(){
  const previous=controls.page.value,sheet=study.sheets.find(s=>s.id===controls.sheet.value);
  controls.page.replaceChildren(...sheet.pages.map(p=>new Option(p,p)));
  if(sheet.pages.includes(previous))controls.page.value=previous;
 }
 function save(){SG.setHash({...SG.hash(),sheet:controls.sheet.value,view:controls.view.value,page:controls.page.value,word:inspecting?selected:null,cursor:inspecting?null:selected,sequence:controls.mode.value,color:controls.color.value,filter:controls.filter.value,focus:controls.focus.checked?'1':'0'});}
 function clearSelection(){
  if(!inspecting)return;
  stop();inspecting=false;controls.focus.checked=false;render();save();
 }
 function toggleWord(pos){if(inspecting&&pos===selected)clearSelection();else choose(pos);}
 function choose(pos,pause=true){
  if(!byId.has(pos))return;
  if(pause)stop();const r=byId.get(pos);
  if(r.sheet!==controls.sheet.value){controls.sheet.value=r.sheet;pageOptions();}
  selected=pos;inspecting=true;controls.page.value=r.page;controls.focus.checked=true;render();save();
 }
 function move(delta,pause=true){const rr=sheetRows(),i=record().step,next=rr[i+delta];if(next)choose(next.position,pause);else stop();}
 function pageSvg(page,rows,pool,parents){
  const mapped=rows.filter(r=>geo.geometry[r.position]);if(!mapped.length)return '<p class="chart-note">No usable word rectangles.</p>';
  const boxes=mapped.map(r=>geo.geometry[r.position]),x0=Math.min(...boxes.map(b=>b[0]))-8,y0=Math.min(...boxes.map(b=>b[1]))-8,x1=Math.max(...boxes.map(b=>b[2]))+8,y1=Math.max(...boxes.map(b=>b[3]))+8;
  const selectedRow=record(),source=new Set(pool.indices),point=inspecting&&selectedRow.page===page?geo.centers[selected]:null;
  let cone='';
  if(point){const g=geo.pages.get(page),h=8*g.pitch,w=h;cone='M '+point.x+' '+point.y+' L '+(point.x-w)+' '+(point.y-h)+' L '+(point.x+w)+' '+(point.y-h)+' Z M '+point.x+' '+point.y+' L '+(point.x-3*g.wordWidth)+' '+point.y;}
  return '<svg viewBox="'+[x0,y0,x1-x0,y1-y0].join(' ')+'" aria-label="'+esc(page)+' recorded word layout">'+(cone?'<path class="recon-cone-fill" d="'+cone+'"/>':'')+mapped.map(r=>{
   const p=r.position,b=geo.geometry[p],w=b[2]-b[0],h=b[3]-b[1],cls=['recon-word',inspecting&&p===selected?'selected':'',parents.has(p)?'parent':'',source.has(p)?'source':'',matches(r)?'':'filtered',controls.written.checked&&r.step>selectedRow.step?'future':''].join(' ');
   return '<g class="'+cls+'" data-position="'+p+'" role="button" tabindex="'+(p===selected||r===mapped[0]?'0':'-1')+'" aria-label="'+esc(data.words[p]+' · '+page+':'+r.locus+' · '+routeNames[m(r).chosen.kind])+'"><title>'+esc(data.words[p]+' · '+routeNames[m(r).chosen.kind]+' · page distance '+number(r.pageDistance))+'</title><rect x="'+b[0]+'" y="'+b[1]+'" width="'+w+'" height="'+h+'" rx="2" fill="'+fill(r)+'"/><text x="'+(b[0]+2)+'" y="'+(b[1]+h*.72)+'" font-size="'+Math.min(18,h*.67)+'" textLength="'+Math.max(2,w-4)+'" lengthAdjust="spacingAndGlyphs">'+esc(data.words[p])+'</text></g>';
  }).join('')+(cone?'<path class="recon-cone" d="'+cone+'"/>':'')+'</svg>';
 }
 function operation(r){
  const c=m(r).chosen;
  if(c.kind==='seed')return 'This word is supplied in the first seed line of the bifolium.';
  if(c.kind==='copy')return 'Copy the complete spelling from an earlier word.';
  if(c.kind==='introduction')return 'No construction was found in this source window under the declared operation menu. The sequence introduces this observed word explicitly.';
  if(c.kind==='splice')return 'Take '+c.cut+' prefix units from the first parent and '+c.suffix_length+' suffix units from the second.';
  if(c.kind==='assembly')return 'Assemble '+c.family+' parts: '+c.parts.map(x=>x||'∅').join(' | ')+'.';
  if(c.kind==='block')return 'Replace '+c.family+' part '+(c.index+1)+': '+(c.parts[c.index]||'∅')+' → '+(c.replacement||'∅')+'.';
  const work=data.components[c.sources[0]].slice(),steps=[];
  for(const [op,i,v] of c.steps){const before=work[i];if(op==='delete'){steps.push('Delete '+before+' at unit '+(i+1));work.splice(i,1);}else if(op==='replace'){steps.push(before+' → '+v+' at unit '+(i+1));work[i]=v;}else{steps.push('Insert '+v+' at unit '+(i+1));work.splice(i,0,v);}}
  return steps.join('; ')+'.';
 }
 function details(r,pool){
  const v=m(r),c=v.chosen,local=SG_COPY.measure(copy,selected,pool,true);
  const facts=[['Construction pool',v.pool+' occurrences / '+v.types+' spellings'],['Minimum whole-word distance',number(v.distance)],['Nearest alternatives',v.nearest+' spellings / '+v.nearestOccurrences+' occurrences'],['Sources within one edit',v.within1+' spellings'],['Block / splice pairs',v.blocks+' / '+v.splices],['Aligned-part assignments',v.assemblies],['Earlier page: exact source',r.pageExact?'Yes':'No'],['Earlier page: minimum distance',number(r.pageDistance)],['Page nearest spellings',r.pageNearest],['Broad twelve-slot parser',r.broad],['Strict grammar',r.strict?'Accepted':'Rejected']];
  const parentList=c.parents.map((p,i)=>{
   const same=byId.get(p)?.sheet===r.sheet,label=data.words[p]+' · '+where(p),canJump=byId.has(p);
   return '<div>'+(canJump?'<button type="button" data-parent="'+p+'">'+esc(label)+'</button>':'<b>'+esc(label)+'</b>')+'<span class="recon-chip">'+(same?(data.lines[geo.lineOf[p]].page===r.page?'Same page':'Earlier page'):'External startup priming')+'</span>'+(c.parent_distance?' <span class="chart-note">distance '+c.parent_distance[i]+'</span>':'')+'</div>';
  }).join('');
  $('reconDetails').innerHTML='<h2>'+esc(data.words[selected])+'</h2><p class="chart-note">'+esc(where(selected))+' · word '+(r.step+1)+' on '+esc(r.sheet)+'</p><span class="recon-chip">'+routeNames[c.kind]+'</span><span class="recon-chip">'+(r.first?'First appearance on sheet':'Previously seen on sheet')+'</span>'+(r.pf?'<span class="recon-chip">p/f family</span>':'')+(r.rare.length?'<span class="recon-chip">Rare: '+esc(r.rare.join(', '))+'</span>':'')+'<p class="recon-note">'+esc(operation(r))+'</p><h3>Proposed parents</h3><div class="parents">'+(parentList||'<p class="chart-note">'+(r.seed?'Supplied seed; no parent needed.':'No supported parent.')+'</p>')+'</div><h3>Sources and alternatives</h3><table>'+facts.map(([a,b])=>'<tr><th>'+a+'</th><td>'+esc(b)+'</td></tr>').join('')+'</table><p class="chart-note">Counts refer to the construction pool, including its page reserve. Different operation families overlap; these are not probabilities.</p><h3>Inside the selected cone</h3><p class="chart-note">'+pool.indices.length+' earlier words · '+local.distinct+' spellings · minimum distance '+number(local.minedit)+'. Sources below are ordered by distance, then geometry weight.</p><div class="recon-sources">'+local.sources.map(x=>'<button type="button" data-parent="'+x.positions[0]+'">'+esc(x.word)+' · d='+x.distance+' · ×'+x.positions.length+'</button> ').join('')+'</div>';
  if(!geo.centers[selected])$('reconDetails').insertAdjacentHTML('beforeend','<p class="recon-note">This word has no usable recorded rectangle. Its local cone is empty; the word remains in the text and page history.</p>');
 }
 function render(){
  const rr=sheetRows(),r=record(),sheet=study.sheets.find(x=>x.id===r.sheet),pool=inspecting?SG_SOURCES.sourcePool(geo,selected,100):{indices:[],weights:[]},parents=new Set(inspecting?m(r).chosen.parents:[]);
  visibleRows=controls.view.value==='page'?rr.filter(x=>x.page===controls.page.value):rr;
  const pages=controls.view.value==='page'?[controls.page.value]:sheet.pages;
  $('reconPages').classList.toggle('single',controls.view.value==='page');
  controls.focus.disabled=!inspecting;
  $('reconPages').classList.toggle('recon-focus',inspecting&&controls.focus.checked);
  $('reconPages').innerHTML=pages.map(p=>{const rows=rr.filter(x=>x.page===p);return '<figure><figcaption>'+p+' · '+rows.length+' words</figcaption>'+pageSvg(p,rows,pool,parents)+'</figure>';}).join('');
  const missing=visibleRows.filter(x=>!geo.geometry[x.position]);
  $('reconMissing').innerHTML=missing.length?'Words without usable rectangles: '+missing.map(x=>'<button type="button" data-parent="'+x.position+'">'+esc(data.words[x.position]+' · '+where(x.position))+'</button>').join(' '):'';
  controls.step.max=rr.length-1;controls.step.value=r.step;
  $('reconProgress').textContent=(r.step+1)+' / '+rr.length+' · '+r.page+':'+r.locus;
  const scored=rr.filter(x=>!x.seed),unknown=scored.filter(x=>m(x).chosen.kind==='introduction').length;
  $('reconSummary').textContent=rr.length+' words in singulion order · '+unknown+' / '+scored.length+' unexplained after seed lines · '+visibleRows.filter(matches).length+' highlighted in this view. '+(controls.mode.value==='primed'?'Startup reserve: '+study.priming[r.sheet].page+'.':'No external startup reserve.');
  legend();
  if(inspecting)details(r,pool);
  else $('reconDetails').innerHTML='<h2>No word selected</h2><p class="chart-note">Select a word to inspect its source window, proposed parents and edit alternatives.</p>';
 }
 function restoreHash(){
  const h=SG.hash();controls.sheet.value=bySheet.has(h.sheet)?h.sheet:study.sheets[0].id;pageOptions();
  controls.view.value=h.view==='page'?'page':'bifolium';controls.mode.value=h.sequence==='primary'?'primary':'primed';
  controls.color.value=['route','distance','page','grammar'].includes(h.color)?h.color:'route';
  controls.filter.value=[...controls.filter.options].some(o=>o.value===h.filter)?h.filter:'all';
  inspecting=h.word!=null||h.cursor==null;
  controls.focus.checked=inspecting&&(h.focus==='1'||(h.focus!=='0'&&h.word!=null));
  const row=byId.get(Number(h.word??h.cursor));
  selected=row&&row.sheet===controls.sheet.value?row.position:(sheetRows().find(x=>x.page===h.page&&!x.seed)||sheetRows().find(x=>!x.seed)||sheetRows()[0]).position;
  controls.page.value=record().page;render();
 }
 try{
  [data,study]=await Promise.all([SG.load('data/mattr_heatmap/words.json.gz?v=270f5d56c6'),SG.load('data/reconstruction.json.gz?v=ff21803488')]);
  geo=SG_SOURCES.prepare(data);copy=SG_COPY.prepare(data);byId=new Map(study.rows.map(r=>[r.position,r]));bySheet=new Map(study.sheets.map(s=>[s.id,study.rows.filter(r=>r.sheet===s.id)]));
  controls.sheet.replaceChildren(...study.sheets.map(s=>new Option(s.id+' · '+s.pages.join(' '),s.id)));
  restoreHash();root.removeAttribute('aria-busy');
  controls.sheet.onchange=()=>{stop();pageOptions();choose(sheetRows().find(x=>!x.seed).position);};
  controls.page.onchange=()=>choose(sheetRows().find(r=>r.page===controls.page.value).position);
  for(const x of [controls.view,controls.mode,controls.color,controls.filter,controls.written,controls.focus])x.onchange=()=>{stop();render();save();};
  controls.search.oninput=()=>render();controls.step.oninput=()=>choose(sheetRows()[Number(controls.step.value)].position);
  $('reconFind').onclick=()=>{const rr=sheetRows(),at=record().step;for(let k=1;k<=rr.length;k++){const r=rr[(at+k)%rr.length];if(matches(r)){choose(r.position);return;}}$('reconProgress').textContent='No matching word on this sheet';};
  $('reconPrev').onclick=()=>move(-1);$('reconNext').onclick=()=>move(1);
  $('reconPlay').onclick=()=>{if(clock){stop();return;}if(record().step===sheetRows().length-1)choose(sheetRows()[0].position);controls.written.checked=true;clock=setInterval(()=>move(1,false),650);$('reconPlay').textContent='Pause';$('reconPlay').setAttribute('aria-pressed','true');render();};
  root.addEventListener('click',e=>{const item=e.target.closest('[data-position],[data-parent]');if(item)toggleWord(Number(item.dataset.position??item.dataset.parent));});
  document.addEventListener('click',e=>{
   if(!e.target.closest('[data-position],[data-parent],button,a,input,select,textarea,label,summary,.recon-controls,.recon-replay,.recon-inspector,.recon-method,.site-nav'))clearSelection();
  });
  root.addEventListener('keydown',e=>{const item=e.target.closest('[data-position]');if(!item)return;if(e.key==='Enter'||e.key===' '){e.preventDefault();toggleWord(Number(item.dataset.position));}if(e.key==='ArrowRight'||e.key==='ArrowLeft'){e.preventDefault();move(e.key==='ArrowRight'?1:-1);}});
  document.addEventListener('keydown',e=>{if(e.key==='Escape')clearSelection();});
  document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();});window.addEventListener('pagehide',stop);window.addEventListener('hashchange',()=>{stop();restoreHash();});
 }catch(error){stop();root.removeAttribute('aria-busy');$('reconProgress').textContent='Could not load the reconstruction. Reload to retry.';SG.error($('reconDetails'),error);console.error(error);}
})();
