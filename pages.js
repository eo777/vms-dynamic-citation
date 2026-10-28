"use strict";
// Page browser: a scrubber over the whole text, generated pages with highlights, the step-by-step replay of how each word
// was made, and the results of the bifolium the page falls on.
(async()=>{
const {$,esc,fmt,int,pct,signed,finite,load,units,matcher,snapshot,valueAt,showTip,hideTip,attachTips,groupVar,hash,setHash,diffWord,error}=SG;
const LPP=29,T=34977;
const state={run:'governed',page:0,node:null,sel:null,cursor:null,steps:[],playing:false,timer:null,openLog:null,tab:'step',presOpen:false,presRows:null,wordOpen:new Set(),
 overlays:{new:true,inn:true,far:true,dg:true,copy:false,type:false,hx:false,ab:false,pres:false}};
const D={manifest:null,model:null,M:null,runs:{}};
const V=window.SG_RELEASE&&window.SG_RELEASE.build?'?v='+window.SG_RELEASE.build:'';   // published copies: cache-bust the per-page files
// [key, label, description, sample classes]: the sample is a word styled as the highlight draws it
const OVERLAYS=[['new','New forms','first appearance in this text','o-new'],['inn','Innovator','word made by the slot innovator','o-inn'],['far','Far source','source drawn by the governor\'s far rule from the running memory of the 100 most recently used words (in the pool run, from the last 2,000 words) instead of by Timm\'s window draw; the word drawn may itself stand on this page','o-far'],['dg','Degenerate stretch','word inside a stretch where the last 50 words hold fewer than 25 distinct forms (rolling diversity below 0.5); the manuscript never falls below 0.56','o-dg'],['copy','Unchanged copies','source copied without change','o-copy'],
 ['type','Operation','R replace · A add · D delete · C combine · S split · T shortened','o-ty-COMBINE'],['hx','Manuscript hapax','spelling that occurs once in the manuscript','o-hx'],['ab','Absent from manuscript','spelling the manuscript does not contain','o-ab'],
 ['pres','Pressure value','sum of the word\'s construction pressures at its line start: blue wanted, red surplus','o-pres']];
const MODE={LOCALY:'page window',PARAGRAPH_INITIAL:'paragraph-initial archive',RANDOM:'random (no lines yet)',SUGGESTION:'Timm suggestion',FORCE:'forced suggestion','':'—'};
const TYPE={REPLACE:'R',ADD:'A',DELETE:'D',COMBINE:'C',SPLIT:'S',SHORTEN:'T',INITIAL:'I'};
const SL=SG_STEPLOG,FP=()=>R().text.first_pos;
const LOOP_GUARD='Timm\'s loop guard: after more than a hundred draws at one position his generator takes a forced suggestion instead of the chooser\'s draw.';
const BRANCH={concat:'join',prefixword:'one-unit join',extend2:'extend',edit:'edit'};
const SLOT_DEF={'page-first':'first word of a page','paragraph-first':'first word of a paragraph-initial line','line-first':'first word of any other line','line-final':'12 or fewer characters left in the line','paragraph-line':'inside a paragraph-initial line','interior':'any other word'};
const SRC_CHIP={PARAGRAPH_INITIAL:'archive',SUGGESTION:'suggestion',FORCE:'forced',RANDOM:'random'};
const OUTCOME={A:['A','accepted'],C:['A','copy'],T:['A','passed'],R:['R','rejected'],K:['K','copy kept'],N:['N','innovated'],X:['X','refused'],G:['X','repeat']};

// ---------------------------------------------------------------- data
async function init(){
 D.manifest=await load('data/manifest.json?v=614812a7ea');D.manifest.runs=D.manifest.runs.filter(r=>!r.stats_only);D.model=await load('data/model.json.gz?v=9e59dfb205');D.M=matcher(D.model.features);
 for(const r of D.manifest.runs)D.runs[r.id]={cfg:r,text:null,nodes:null,pages:{},args:D.manifest.seed_runs.find(s=>s.seed_run===r.run).args};
 const pageTables=t=>{if(!t.page_starts){const n=Math.ceil(t.lines.length/LPP);t.page_starts=[...Array(n+1).keys()].map(k=>Math.min(k*LPP,t.lines.length));t.pages=n;}t.page_of=new Array(t.lines.length);for(let k=0;k+1<t.page_starts.length;k++)for(let l=t.page_starts[k];l<t.page_starts[k+1];l++)t.page_of[l]=k;};
 await Promise.all(D.manifest.runs.map(async r=>{const R=D.runs[r.id];[R.text,R.nodes]=await Promise.all([load(`data/${r.id}/text.json.gz${V}`),load(`data/${r.id}/nodes.json.gz${V}`)]);pageTables(R.text);}));
 const h=hash();if(D.runs[h.run])state.run=h.run;
 D.visible=SG.visibleRuns(D.manifest.runs);
 if(!D.visible.length){document.querySelector('main').innerHTML='<section class="panel"><h2>These methods have statistics only</h2><p>The selected methods have no page replay. Open <a href="comparison.html">Comparison</a> for their charts and short text examples, or choose an existing replay from the Runs menu.</p></section>';return;}
 if(!D.visible.some(r=>r.id===state.run))state.run=(D.visible.find(r=>r.id==='governed')||D.visible[0]).id;if(h.page!=null)state.page=Math.max(0,Math.min(R().text.pages-1,+h.page||0));if(h.node!=null&&finite(+h.node))state.node=+h.node;
 renderRunSeg();renderOverlayChips();renderPageOptions();renderTimeline();bindTabs();
 await showPage(state.page,h.node!=null);
 if(state.node==null)state.node=nodeOfPos(pageRange(state.page)[0]);
 renderNodeResults();
 if(h.pos!=null&&finite(+h.pos)){const [a,b]=pageRange(state.page);if(+h.pos>=a&&+h.pos<b)select(+h.pos);}
 bind();
 // the scrubber is drawn at its pixel width; the side panels stick below the deck
 let w=0;new ResizeObserver(()=>{const nw=$('timeline').clientWidth;if(nw&&nw!==w){w=nw;renderTimeline();}document.body.style.setProperty('--deck-h',$('deck').offsetHeight+'px');}).observe($('deck'));
}
const R=()=>D.runs[state.run];
const lineOfPos=(pos,R_=R())=>{const f=R_.text.first_pos;let lo=0,hi=f.length-1;while(lo<hi){const m=(lo+hi+1)>>1;if(f[m]<=pos)lo=m;else hi=m-1;}return lo;};
const pageRange=(k,R_=R())=>{const f=R_.text.first_pos,ps=R_.text.page_starts,a=f[ps[k]],b=ps[k+1]<f.length?f[ps[k+1]]:R_.text.tokens;return [a,b];};
const nodeOfPos=pos=>{const n=D.model.nodes.findIndex(n=>pos>=n.start&&pos<n.end);return n<0?D.model.nodes.length:n;};
const pagesOfNode=(s,R_=R())=>{const out=[];const [a,b]=s>=D.model.nodes.length?[T,R_.text.tokens]:[D.model.nodes[s].start,D.model.nodes[s].end];for(let k=0;k<R_.text.pages;k++){const [x,y]=pageRange(k,R_);if(y>a&&x<b)out.push(k);}return out;};
const nodeLabel=s=>s>=D.model.nodes.length?'beyond the manuscript’s length':`${D.model.nodes[s].id} · ${D.model.nodes[s].group}`;
const posLabel=(pos,R_=R())=>{const ln=lineOfPos(pos,R_);return {ln,page:R_.text.page_of[ln],idx:pos-R_.text.first_pos[ln],word:R_.text.lines[ln][pos-R_.text.first_pos[ln]]};};
async function pageData(k){const R_=R();if(!R_.pages[k]){const pg=await load(`data/${state.run}/pages/${k}.json.gz${V}`);decodeSnaps(pg);R_.pages[k]=pg;}return R_.pages[k];}
// snapshots come per line as int8 deltas from the previous stored line ('D') or absolute ('A'); decoded once into pressures
function decodeSnaps(pg){
 if(!pg.snaps_delta||pg._snaps)return;const abs={};let prev=null;
 for(const l of Object.keys(pg.snaps).map(Number).sort((a,b)=>a-b)){const s=pg.snaps[l],arr=SG.snapshotInts(s.slice(1));let cur=arr;
  if(s[0]==='D'&&prev){cur=new Int16Array(arr.length);for(let i=0;i<arr.length;i++)cur[i]=prev[i]+arr[i];}
  abs[l]=Float32Array.from(cur,x=>x*0.025);prev=cur;}
 pg._snaps=abs;
}

// ---------------------------------------------------------------- run switch, highlights
function renderRunSeg(){
 $('runSeg').innerHTML=D.visible.map(r=>`<button type="button" role="radio" aria-checked="${r.id===state.run}" data-run="${r.id}" class="${r.id===state.run?'on':''}" style="--c:${r.color}" title="${esc(r.label)}"><i class="dot"></i>${esc(r.short)}</button>`).join('');
 $('runSeg').querySelectorAll('button').forEach(b=>b.addEventListener('click',async()=>{if(b.dataset.run===state.run)return;stop();state.run=b.dataset.run;state.sel=null;renderRunSeg();renderPageOptions();await showPage(Math.min(state.page,R().text.pages-1),false);}));
}
const sample=(k,cls)=>`<span class="tok written sample ${cls}"${k==='pres'?' style="--pbg:color-mix(in srgb,var(--want) 40%,transparent)"':''}>chol${k==='type'?'<sup>C</sup>':''}</span>`;
function renderOverlayChips(){
 $('overlays').innerHTML=OVERLAYS.map(([k,l,d,cls])=>`<label class="mk"><input type="checkbox" data-ov="${k}" ${state.overlays[k]?'checked':''}>${sample(k,cls)}<span><b>${esc(l)}</b><small>${esc(d)}</small></span></label>`).join('');
 $('overlays').querySelectorAll('input').forEach(c=>c.addEventListener('change',()=>{state.overlays[c.dataset.ov]=c.checked;renderKey();renderText();}));
 const menu=$('marksMenu');document.addEventListener('click',e=>{if(!menu.contains(e.target))menu.removeAttribute('open');});
 renderKey();
}
// the legend under the text: the highlights switched on, then the replay marks
function renderKey(){
 const on=OVERLAYS.filter(([k])=>state.overlays[k]);$('marksCount').textContent=on.length;
 $('hlKey').innerHTML=on.length?on.map(([k,l,d,cls])=>`<span title="${esc(d)}">${sample(k,cls)}${esc(l)}</span>`).join(''):'<span class="muted">none</span>';
 $('keyrow').innerHTML=`<span><i class="sw pool"></i>source window (shade = selection probability)</span><span><i class="sw pick"></i>chosen source</span><span><i class="sw partner"></i>join partner</span><span><i class="sw cur"></i>word being written</span><span>¶ paragraph start</span>`;
}

// ---------------------------------------------------------------- page and bifolium dropdowns (folio names)
// the 207 paragraph pages carry their folio; the generated pages after them only a number
const folioOf=(k,R_=R())=>(R_.text.page_ids&&R_.text.page_ids[k])||`p.${k+1}`;
function renderPageOptions(){
 const R_=R(),nodes=D.model.nodes;
 $('pageSel').innerHTML=[...Array(R_.text.pages).keys()].map(k=>`<option value="${k}">${esc(folioOf(k,R_))}</option>`).join('');
 // bifolia grouped by Golf's groups along the path; pages past the manuscript's length last
 let html='',g=null;
 nodes.forEach((n,i)=>{if(n.group!==g){if(g!=null)html+='</optgroup>';g=n.group;html+=`<optgroup label="${esc(g)}">`;}html+=`<option value="${i}">${esc(n.id)}</option>`;});
 $('nodeSel').innerHTML=html+`</optgroup><optgroup label="past the manuscript’s length"><option value="${nodes.length}">beyond</option></optgroup>`;
}

// ---------------------------------------------------------------- scrubber: one slot per page of the run, the bifolia (placed by token count) and their groups as bands
const SC={H:48,ty:17,th:24};
let drag=null,dragTimer=null;
// a token position as a fractional page index of the shown run
function pageAtToken(tok,R_=R()){const f=R_.text.first_pos,ps=R_.text.page_starts;let lo=0,hi=R_.text.pages-1;while(lo<hi){const m=(lo+hi+1)>>1;if(f[ps[m]]<=tok)lo=m;else hi=m-1;}const [a,b]=pageRange(lo,R_);return lo+Math.max(0,Math.min(1,(tok-a)/Math.max(1,b-a)));}
function scrubGeom(){const W=Math.max(320,$('timeline').clientWidth||1000),n=R().text.pages;return {W,n,X:p=>1+(W-2)*p/n,P:x=>Math.max(0,Math.min(n-1,Math.floor((x-1)/(W-2)*n)))};}
const nodesOfPage=k=>{const [a,b]=pageRange(k);return [...new Set([...Array(Math.max(1,b-a)).keys()].map(i=>nodeOfPos(a+i)))];};
function renderTimeline(){
 const nodes=D.model.nodes,{W,n,X}=scrubGeom(),{H,ty,th}=SC;
 const nb=nodes.map(nd=>[pageAtToken(nd.start),pageAtToken(nd.end)]),end=nb[nb.length-1][1];
 let svg=`<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" aria-hidden="true"><defs><pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="6" class="hatch"/></pattern></defs>`;
 let g0=0;
 for(let s=1;s<=nodes.length;s++){if(s===nodes.length||nodes[s].group!==nodes[g0].group){const x1=X(nb[g0][0]),x2=X(nb[s-1][1]);
  svg+=`<rect x="${x1}" y="${ty}" width="${Math.max(0,x2-x1)}" height="${th}" fill="${groupVar(nodes[g0].group)}"/>`;
  if(g0>0)svg+=`<line class="gsep" x1="${x1}" x2="${x1}" y1="${ty}" y2="${ty+th}"/>`;
  if(x2-x1>22)svg+=`<text class="glabel" x="${(x1+x2)/2}" y="${ty+th/2+4}" text-anchor="middle">${esc(nodes[g0].group)}</text>`;g0=s;}}
 for(let s=1;s<nodes.length;s++)if(nodes[s].group===nodes[s-1].group){const x=X(nb[s][0]);svg+=`<line class="bsep" x1="${x}" x2="${x}" y1="${ty}" y2="${ty+5}"/><line class="bsep" x1="${x}" x2="${x}" y1="${ty+th-5}" y2="${ty+th}"/>`;}
 const xb=X(end),xe=X(n);
 if(xe-xb>1){svg+=`<rect x="${xb}" y="${ty}" width="${xe-xb}" height="${th}" fill="url(#hatch)" class="beyond"/>`;if(xe-xb>60)svg+=`<text class="glabel dim" x="${(xb+xe)/2}" y="${ty+th/2+4}" text-anchor="middle">beyond</text>`;}
 if(state.node!=null){const [a,b]=state.node<nodes.length?nb[state.node]:[end,n];svg+=`<rect class="nodesel" x="${X(a)}" y="${ty+th+3}" width="${Math.max(3,X(b)-X(a))}" height="3" rx="1.5"><title>Bifolium shown below</title></rect>`;}
 svg+=`<rect class="frame" x="${X(0)}" y="${ty}" width="${X(n)-X(0)}" height="${th}" rx="4"/><line class="ghost" id="scrubGhost" x1="0" x2="0" y1="${ty}" y2="${ty+th}" style="display:none"/>`;
 $('timeline').innerHTML=svg+'<g id="scrubHandle"></g></svg>';
 renderHandle();
}
function renderHandle(){
 const g=document.getElementById('scrubHandle');if(!g)return;
 const R_=R(),{W,X}=scrubGeom(),{ty,th}=SC,k=drag?drag.k:state.page,x1=X(k),x2=X(k+1),cx=(x1+x2)/2,lab=folioOf(k,R_),lw=12+6.4*lab.length,lx=Math.max(0,Math.min(W-lw,cx-lw/2));
 const tw=Math.max(10,x2-x1);
 g.innerHTML=`<rect class="thumb" x="${cx-tw/2}" y="${ty-3}" width="${tw}" height="${th+6}" rx="3"/><line class="grip" x1="${cx-1.5}" x2="${cx-1.5}" y1="${ty+7}" y2="${ty+th-7}"/><line class="grip" x1="${cx+1.5}" x2="${cx+1.5}" y1="${ty+7}" y2="${ty+th-7}"/><rect class="knob" x="${lx}" y="0" width="${lw}" height="14" rx="7"/><text class="knobtext" x="${lx+lw/2}" y="10.5" text-anchor="middle">${lab}</text>`;
 const t=$('timeline');t.setAttribute('aria-valuemax',R_.text.pages);t.setAttribute('aria-valuenow',k+1);t.setAttribute('aria-valuetext',`page ${k+1} of ${R_.text.pages}${R_.text.page_ids?', '+R_.text.page_ids[k]:''}`);
}
function scrubTip(k){
 const R_=R(),nodes=D.model.nodes,s=nodesOfPage(k)[0],folio=R_.text.page_ids&&R_.text.page_ids[k];
 let tip=`<b>Page ${k+1}${folio?` · ${esc(folio)}`:''}</b><div>${esc(nodeLabel(s))}${s<nodes.length?` · ${int(nodes[s].N)} tokens`:''}</div>`;
 if(s<nodes.length)tip+=D.visible.map(r=>{const x=D.runs[r.id].nodes[s];return `<div><span style="color:${r.color}">■</span> ${esc(r.short)}: word distance ${fmt(x.tv,2)}, new forms ${int(x.new)}${x.deg?`, degenerate ${int(x.deg)}`:''}</div>`;}).join('');
 return tip+'<div class="tipsub">Click or drag to go there</div>';
}
function scrubTo(k){renderHandle();$('pageSel').value=k;clearTimeout(dragTimer);dragTimer=setTimeout(()=>{if(drag&&drag.k===k&&k!==state.page)showPage(k);},110);}
function bindScrub(){
 const tl=$('timeline'),at=e=>scrubGeom().P(e.clientX-tl.getBoundingClientRect().left);
 tl.addEventListener('pointerdown',e=>{if(e.button!==0)return;e.preventDefault();tl.setPointerCapture(e.pointerId);tl.focus({preventScroll:true});hideTip();drag={k:at(e)};scrubTo(drag.k);});
 const ghost=x=>{const g=document.getElementById('scrubGhost');if(!g)return;if(x==null){g.style.display='none';return;}g.setAttribute('x1',x);g.setAttribute('x2',x);g.style.display='';};
 tl.addEventListener('pointermove',e=>{const k=at(e);if(drag){if(k!==drag.k){drag.k=k;scrubTo(k);}return;}const {X}=scrubGeom();ghost(X(k+.5));showTip(scrubTip(k),e.clientX,e.clientY);});
 const done=e=>{if(!drag)return;const k=e.type==='pointerup'?at(e):drag.k;drag=null;clearTimeout(dragTimer);if(k!==state.page)showPage(k);else renderHandle();};
 tl.addEventListener('pointerup',done);tl.addEventListener('pointercancel',done);tl.addEventListener('pointerleave',()=>{if(!drag){hideTip();ghost(null);}});
 tl.addEventListener('keydown',e=>{const n=R().text.pages,d={ArrowLeft:-1,ArrowRight:1,ArrowDown:-1,ArrowUp:1,PageUp:-10,PageDown:10}[e.key];
  const to=d!=null?state.page+d:e.key==='Home'?0:e.key==='End'?n-1:null;if(to==null)return;e.preventDefault();e.stopPropagation();showPage(Math.max(0,Math.min(n-1,to)));});
}

// ---------------------------------------------------------------- the bifolium the page falls on
function renderNodeResults(){
 const s=state.node;if(s==null){$('nodeResults').innerHTML='';return;}
 const nodes=D.model.nodes,R_=R(),pages=pagesOfNode(s),here=nodesOfPage(state.page);
 $('nodeTitle').innerHTML=s<nodes.length?`Bifolium ${esc(nodes[s].id)} <span class="muted">· ${esc(nodes[s].group)} · manuscript pages ${esc(nodes[s].pages.join(', '))} · ${int(nodes[s].N)} tokens</span>`:'Beyond the manuscript’s length';
 $('nodePick').innerHTML=(here.length>1?`<span class="small muted">Page ${state.page+1} spans</span><span class="seg">${here.map(x=>`<button type="button" class="${x===s?'on':''}" data-node="${x}">${esc(x<nodes.length?nodes[x].id:'beyond')}</button>`).join('')}</span>`:'')
  +`<span class="small muted">Its generated pages</span><span class="pagebtns">${pages.map(k=>`<button type="button" class="${k===state.page?'on':''}" data-page="${k}" title="page ${k+1}">${esc(folioOf(k))}</button>`).join('')}</span>`;
 $('nodePick').querySelectorAll('[data-page]').forEach(b=>b.addEventListener('click',()=>showPage(+b.dataset.page)));
 $('nodePick').querySelectorAll('[data-node]').forEach(b=>b.addEventListener('click',()=>{state.node=+b.dataset.node;$('nodeSel').value=state.node;renderTimeline();renderNodeResults();save();}));
 if(s>=nodes.length){$('nodeResults').innerHTML=`<p class="small muted" style="margin:4px 0 0">Tokens past the manuscript's 34,977 are not scored; the targets stay at the last bifolium's.</p>`;return;}
 const nr=R_.nodes[s],others=D.visible.filter(r=>r.id!==state.run).map(r=>({r,nr:D.runs[r.id].nodes[s]}));
 const metric=(v,l,d)=>`<div class="metric"><div class="v">${v}</div><div class="l">${l}</div>${d?`<div class="d">${d}</div>`:''}</div>`;
 const cmp=(k,f)=>others.map(o=>`${esc(o.r.short)} ${f(o.nr[k],o.nr)}`).join(' · ');
 let html=`<div class="metrics">${metric(fmt(nr.tv,3),'word distance (TV) to the manuscript bifolium',cmp('tv',v=>fmt(v,3)))}${metric(fmt(nr.mae,2)+' pp','construction share error (316 common)',cmp('mae',v=>fmt(v,2)+' pp'))}${metric(int(1000*nr.new/nr.tokens),'first appearances per 1,000',cmp('new',(v,o)=>int(1000*v/o.tokens)))}${nr.deg?metric(int(nr.deg),'words in degenerate stretches (rolling diversity below 0.5)',cmp('deg',v=>int(v||0))):''}${metric(int(nr.inn),'innovator words',state.run==='timm'?'no innovator in this run':cmp('inn',v=>int(v)))}${metric(pct(nr.absent/nr.tokens),'tokens with a spelling absent from the manuscript',cmp('absent',(v,o)=>pct(v/o.tokens)))}${metric(int(nr.hapax),'tokens that are manuscript hapaxes',cmp('hapax',v=>int(v)))}</div>`;
 // constructions furthest from the target, folded
 const common=D.model.common,F=D.model.features;
 const rows=common.map((j,i)=>({j,name:F[j].name,gen:nr.gen[i],target:nr.target[i],obs:nr.obs[i],d:nr.gen[i]-nr.target[i]})).sort((a,b)=>Math.abs(b.d)-Math.abs(a.d)).slice(0,10);
 const max=Math.max(...rows.flatMap(r=>[r.gen,r.target,r.obs]))||1;
 html+=`<details class="sub" id="consFold"${state.consOpen?' open':''}><summary>Constructions furthest from their target <span class="muted small">% of tokens: generated · fitted target · observed</span></summary><div class="cmp cons">${rows.map(r=>`<div class="lab mono">${esc(r.name)}</div><div class="t" data-tip="${esc(r.name)}: generated ${fmt(r.gen,2)}%, target ${fmt(r.target,2)}%, observed ${fmt(r.obs,2)}%"><i style="width:${100*r.gen/max}%;--c:${R_.cfg.color}"></i><i style="width:${100*r.target/max}%;--c:var(--fit);top:5px;height:3px;opacity:.9"></i><em style="left:${100*r.obs/max}%"></em></div><div class="n">${signed(r.d,2)}</div>`).join('')}</div><p class="chart-note">Bar: generated share. Thin line: fitted target. Tick: observed. Number: generated minus target, percentage points.</p></details>`;
 $('nodeResults').innerHTML=html;attachTips($('nodeResults'));
 $('consFold').addEventListener('toggle',e=>{state.consOpen=e.target.open;});
}

// ---------------------------------------------------------------- page
// the pager and page line live in the deck, whose size does not depend on the page, so the buttons stay where they are;
// a page request superseded by a later one (quick clicks, scrubbing) is dropped when it arrives
let pageSeq=0;
async function showPage(k,keepNode=true){
 stop();const R_=R();k=Math.max(0,Math.min(R_.text.pages-1,k));state.page=k;state.sel=null;state.cursor=null;const seq=++pageSeq;
 $('pageSel').value=k;$('prevPage').disabled=k===0;$('nextPage').disabled=k>=R_.text.pages-1;
 renderHandle();
 const text=$('text'),anchor=text.getBoundingClientRect().top,anchored=window.scrollY>0&&anchor<window.innerHeight*0.6;
 text.classList.add('busy');
 let pg;try{pg=await pageData(k);}finally{if(seq===pageSeq)text.classList.remove('busy');}
 if(seq!==pageSeq)return;
 state.pg=pg;
 // steps of the replay
 const steps=[];for(const L of pg.lines)for(let j=0;j<L.t.length;j++){const pos=L.p0+j,ev=pg.events[pos];if(ev&&ev.length)ev.forEach((e,i)=>steps.push([pos,i]));else steps.push([pos,-1]);}
 state.steps=steps;$('rpSlider').max=steps.length;$('rpSlider').value=steps.length;$('rpPos').textContent='whole page';
 const [a,b]=pageRange(k),nodesHere=nodesOfPage(k),folio=R_.text.page_ids&&R_.text.page_ids[k];
 $('pageTitle').innerHTML=`page <b>${k+1}</b> of ${R_.text.pages}${nodesHere.length>1?` · spans ${nodesHere.map(x=>esc(x<D.model.nodes.length?D.model.nodes[x].id:'beyond')).join(' and ')}`:''} <span class="muted">· lines ${R_.text.page_starts[k]+1}–${R_.text.page_starts[k]+pg.lines.length} · tokens ${int(a+1)}–${int(b)}</span>`;
 $('pageTitle').title=$('pageTitle').textContent;
 if(!keepNode||state.node==null||!pagesOfNode(state.node).includes(k))state.node=nodesHere[0];
 $('nodeSel').value=state.node;
 renderTimeline();renderNodeResults();renderText();renderSide();save();
 if(anchored){const d=text.getBoundingClientRect().top-anchor;if(Math.abs(d)>1)window.scrollBy(0,d);}
}
function tokenClasses(t,pos,L){
 const o=state.overlays,c=['tok','written'];
 if(o.new&&t.new)c.push('o-new');if(o.inn&&t.inn)c.push('o-inn');if(o.hx&&t.hx)c.push('o-hx');if(o.ab&&t.ab)c.push('o-ab');if(o.dg&&t.dg)c.push('o-dg');
 if(o.type&&t.ty)c.push('o-ty-'+t.ty);
 if(o.copy){const p=proposalOf(pos);if(p&&p.src===t.w&&!t.inn)c.push('o-copy');}
 if(o.far){const sd=sourceDraw(pos);if(sd&&sd.far)c.push('o-far');}
 if(state.sel===pos)c.push('sel');
 return c;
}
function proposalOf(pos){const ev=state.pg.events[pos];if(!ev)return null;const a=ev.find(e=>e.t==='A');if(!a||a.id<0)return null;for(const e of ev)if(e.t==='P'&&e.id===Math.floor(a.id/100))return e;return null;}
function snapFor(ln){const d=state.pg._snaps,s=d||state.pg.snaps;for(let l=ln;l>=state.pg.lines[0].ln;l--)if(s[l])return {ln:l,p:d?s[l]:snapshot(s[l])};return null;}
function presStyle(t,ln){const sn=snapFor(ln);if(!sn)return '';const v=valueAt(D.M.X(t.w),sn.p),a=Math.min(1,Math.abs(v)/6);return `--pbg:color-mix(in srgb,${v>=0?'var(--want)':'var(--surplus)'} ${Math.round(100*a)}%,transparent)`;}
function renderText(){
 const pg=state.pg;if(!pg)return;const cur=state.cursor;const hl=highlights();state.hl=hl;
 let html='';
 for(const L of pg.lines){
  let words='';
  for(let j=0;j<L.t.length;j++){
   const pos=L.p0+j,t=L.t[j];
   const future=!!(cur&&pos>cur.pos);           // not written yet: kept in the layout, invisible
   if(future){words+=`<span class="tok future" aria-hidden="true">${esc(t.w)}</span>`;continue;}
   const pending=cur&&pos===cur.pos&&!cur.written;
   const cls=pending?['tok','pending']:tokenClasses(t,pos,L);
   if(hl.pick===pos)cls.push('pick');if(hl.partner===pos)cls.push('partner');if(cur&&pos===cur.pos&&cur.written)cls.push('cur');
   if(!pending&&state.overlays.pres)cls.push('o-pres');
   const wgt=hl.weights&&hl.weights.get(pos);
   const style=(!pending&&state.overlays.pres?presStyle(t,L.ln):'')+(wgt!=null?`;--o:${(0.15+0.85*wgt).toFixed(2)}`:'');
   const label=pending?(hl.pendingText||'…'):t.w;
   words+=`<span class="${cls.join(' ')}" data-pos="${pos}" style="${style}">${esc(label)}${state.overlays.type&&t.ty&&!pending?`<sup class="muted" style="font-size:9px">${TYPE[t.ty]||''}</sup>`:''}${wgt!=null?'<i class="wgt"></i>':''}</span>`;
  }
  const dg=state.overlays.dg&&L.t.some(t=>t.dg);
  html+=`<div class="line ${L.par?'par':''} ${L.pf?'pf':''} ${hl.pool.has(L.ln)?'pool':''} ${dg?'deg':''} ${cur&&L.p0>cur.pos?'future':''}" data-ln="${L.ln}"><span class="ln" title="text line ${L.ln+1}${L.par?', paragraph start':''}${L.pf?', page start':''}${dg?', degenerate stretch: the last 50 words hold fewer than 25 distinct forms':''}">${L.ln+1}${L.par?'<span class="pm">¶</span>':''}</span><span class="words">${words}</span></div>`;
 }
 $('text').innerHTML=html;
 $('text').querySelectorAll('.tok:not(.future)').forEach(el=>{el.addEventListener('click',()=>select(+el.dataset.pos));el.addEventListener('mousemove',e=>tokTip(el,e));el.addEventListener('mouseleave',hideTip);});
}
function tokTip(el,e){
 const pos=+el.dataset.pos,{ln,idx}=posLabel(pos),t=state.pg.lines.find(L=>L.ln===ln)?.t[idx];if(!t)return;
 const p=proposalOf(pos);const parts=[`<b>${esc(t.w)}</b> · token ${int(pos+1)} · line ${ln+1} · ${esc(t.sl||'')}`];
 if(t.new)parts.push('first appearance in this text');if(t.inn)parts.push('made by the innovator');if(t.hx)parts.push('manuscript hapax');if(t.ab)parts.push('spelling absent from the manuscript');
 const tr=trimmedFrom(pos,t);
 if(p)parts.push(`source ${esc(p.src)} (${esc(MODE[p.mode]||p.mode)}) · ${esc(t.ty||'')}${tr?` · trimmed from ${esc(tr)}`:''}`);
 const sd=sourceDraw(pos);if(sd&&sd.far){const pk=Array.isArray(sd.pick)?sd.pick[0]:sd.pick;let where='';try{const L=posLabel(pk);where=L.page===state.page?` (${esc(L.word)}, last used on this page, line ${L.ln+1})`:` (${esc(L.word)}, last used on page ${L.page+1})`;}catch(e){}parts.push('source drawn from the running memory of recent words by the governor\'s far rule'+where);}
 const w=state.hl&&state.hl.weights,pr=w&&w.probs.get(pos);if(pr!=null)parts.push(`in the source window: ${fp(100*pr)}% chance to be drawn`);
 const sn=snapFor(ln);if(sn)parts.push(`pressure value ${signed(valueAt(D.M.X(t.w),sn.p),2)} (line ${sn.ln+1} start)`);
 showTip(parts.join('<br>'),e.clientX,e.clientY);
}

// ---------------------------------------------------------------- highlights from the current step or selection
function currentRecord(){
 if(state.cursor){const ev=state.pg.events[state.cursor.pos];return ev&&state.cursor.k>=0?ev[state.cursor.k]:null;}
 if(state.sel!=null){const ev=state.pg.events[state.sel];if(!ev)return null;const a=ev.find(e=>e.t==='A');return a||ev[ev.length-1];}
 return null;
}
function recordsOf(pos){return state.pg.events[pos]||[];}
// the word Timm's trim fitted to the line, if the written word differs from it (a second part's proposal sits at an earlier position)
function trimmedFrom(pos,t){const ev=recordsOf(pos),a=ev.find(e=>e.t==='A');if(!a||a.id<0)return t&&t.trim||null;const p=pForA(pos,a);if(!p)return t&&t.trim||null;const w=SL.intended(p,a.id%100);return w!==a.word?w:null;}
// the source draw (S record) behind the written word: the last draw before its accepted proposal, if that proposal came from the page window
function sourceDraw(pos){const ev=state.pg.events[pos];if(!ev)return null;const a=ev.find(e=>e.t==='A');if(!a||a.id<0)return null;const id=Math.floor(a.id/100);let s=null;
 for(const e of ev){if(e.t==='S')s=e;else if(e.t==='P'&&e.id===id)return e.mode==='LOCALY'?s:null;}return null;}
function pForA(pos,a){const ev=recordsOf(pos);return ev.find(e=>e.t==='P'&&e.id===Math.floor(a.id/100))||null;}
function sForP(pos,p){const ev=recordsOf(pos),i=ev.indexOf(p);for(let j=i-1;j>=0;j--){if(ev[j].t==='S')return ev[j];if(ev[j].t==='P')break;}return null;}
function highlights(){
 const h={pool:new Set(),pick:null,partner:null,weights:null,pendingText:null};
 const pos=state.cursor?state.cursor.pos:state.sel;if(pos==null)return h;
 let rec=currentRecord();if(!rec)return h;
 let S=null,P=null;
 if(rec.t==='S')S=rec;
 else if(rec.t==='P'){P=rec;S=sForP(pos,rec);}
 else if(rec.t==='A'){P=pForA(pos,rec);S=P?sForP(pos,P):null;}
 if(S){
  if(!S.far){for(const [ln] of S.lines)h.pool.add(ln);h.weights=poolWeights(S,pos);if(Array.isArray(S.pick)){const [ln,i]=S.pick;const p0=R().text.first_pos[ln];if(p0!=null)h.pick=p0+i;}}
  else{const p=SL.farPos(S);if(finite(p))h.pick=p;}
 }
 if(P){
  if(P.srcpos>=0)h.pick=P.srcpos;
  const pr=P.props[0]&&P.props[0][0];
  if(P.props.some(x=>x[1]==='COMBINE')&&P.srcpos>=0){const nxt=P.srcpos+1;const {word}=posLabel(nxt);if(pr&&word&&pr.endsWith(word)&&pr!==word)h.partner=nxt;}
  if(P.dec==='N'&&(P.inn.branch==='concat'||P.inn.branch==='prefixword')){const w=P.inn.word,base=pr;let part=w.startsWith(base)?w.slice(base.length):w.endsWith(base)?w.slice(0,w.length-base.length):null;
   if(part)for(let q=pos-1;q>=Math.max(0,pos-6);q--){if(posLabel(q).word===part){h.partner=q;break;}}}
  if(state.cursor&&rec.t==='P')h.pendingText=P.dec==='N'?P.inn.word:P.props.map(x=>x[0]).join(' ');
 }
 if(state.cursor&&rec.t==='S')h.pendingText='?';
 return h;
}
function poolWeights(S,pos){
 const R_=R(),beta=R_.args.beta_c||0,li=S.li,ps=li?0.15:0.29,draws=S.lines.reduce((a,l)=>a+l[1],0);
 const sn=beta?snapFor(lineOfPos(pos)):null;const out=new Map();let total=0;const vals=[];
 for(const [ln,mult,same] of S.lines){const words=R_.text.lines[ln];if(!words)continue;const p0=R_.text.first_pos[ln];
  words.forEach((w,i)=>{let b=mult/draws*((i===same?ps:0)+(1-ps)/words.length);if(sn)b*=Math.exp(beta*valueAt(D.M.X(w),sn.p));vals.push([p0+i,b]);total+=b;});}
 const max=Math.max(...vals.map(v=>v[1]))||1;for(const [p,b] of vals)out.set(p,b/max);out.total=total;out.probs=new Map(vals.map(([p,b])=>[p,b/total]));return out;
}

// ---------------------------------------------------------------- side panels
function select(pos){stop();state.cursor=null;state.sel=pos;renderText();renderSide();save();}
function renderSide(){
 const pos=state.cursor?state.cursor.pos:state.sel;
 if(pos==null){$('stepBody').innerHTML='<span class="muted">Click a word, or play the page.</span>';renderAux(null);return;}
 const ev=recordsOf(pos),{ln,idx,word}=posLabel(pos),t=state.pg.lines.find(L=>L.ln===ln)?.t[idx];
 const curK=state.cursor?state.cursor.k:-2;   // -2: a clicked word; its written record is the current one
 const later=k=>curK>=0&&k>curK;               // replay: records the cursor has not reached
 const att=SL.attempts(ev),cur=att.findIndex(a=>a.ks.includes(curK)),slot=t&&t.sl,open=state.openLog===pos;
 const foldable=att.length>8||att.some(a=>SL.rows(ev,a.ks,null,false,FP()).some(r=>r.skip));
 let html=`<div class="loghead"><span>Token ${int(pos+1)} · line ${ln+1}, word ${idx+1}</span>${slot?`<span${tipAttr(SLOT_DEF[slot])}>${esc(slot)} slot</span>`:''}${foldable&&open?'<button type="button" class="linkbtn" data-unfold>fold repeats</button>':''}</div>`;
 if(att.length>1)html+=strip(att,ev,cur);
 html+='<div class="log">';
 if(!ev.length)html+=`<div class="att">${recWrap(-1,true,false,row('given',wordCode(word||t?.w||'','Timm\'s seed line: the generator starts from it.'),'',''))}</div>`;
 for(const seg of SL.layout(att.length,cur,open)){
  if(seg.fold){html+=foldRow(seg.fold,att,ev,later(att[seg.fold[0]].ks[0]));continue;}
  const a=att[seg.i];
  html+=`<div class="att"${att.length>1?` data-n="${seg.i+1}"`:''}>${SL.rows(ev,a.ks,curK,open,FP()).map(r=>r.skip?skipRow(r.skip,ev,later(r.skip[0])):recWrap(r.k,r.k===curK,later(r.k),ev[r.k].t==='S'?drawRec(ev[r.k],ev,r.k):proposalRec(ev[r.k],ev))).join('')}</div>`;
 }
 ev.forEach((e,k)=>{if(e.t==='A')html+=`<div class="att fin">${recWrap(k,k===curK||curK===-2,later(k),writtenRec(e,pos,ev))}</div>`;});
 $('stepBody').innerHTML=html+'</div>';attachTips($('stepBody'));
 $('stepBody').querySelectorAll('[data-k]').forEach(el=>el.addEventListener('click',()=>jump(pos,+el.dataset.k)));
 $('stepBody').querySelectorAll('[data-unfold],.fold,.fold-s').forEach(el=>el.addEventListener('click',()=>{state.openLog=el.matches('[data-unfold]')?null:pos;renderSide();}));
 const now=$('stepBody').querySelector('.rec.now');if(now&&state.cursor)keepVisible(now);
 renderAux(pos);
}
// replay from one record of the word shown
function jump(pos,k){const i=state.steps.findIndex(([p,kk])=>p===pos&&kk===k);if(i>=0){stop();setStep(i);}}
function keepVisible(el){const side=el.closest('.tabbody');if(!side||side.scrollHeight<=side.clientHeight)return;const a=el.getBoundingClientRect(),b=side.getBoundingClientRect();if(a.top<b.top+24||a.bottom>b.bottom-8)side.scrollTop+=a.top-b.top-80;}

// ---------------------------------------------------------------- side panel tabs: Step, Source, Pressures, Bifolium in one box of fixed size
function bindTabs(){
 const stored=k=>{try{return localStorage.getItem(k);}catch(e){return null;}};
 state.presOpen=stored('sg-pres-column')==='1';state.wide=stored('sg-wide')==='1';
 $('wideBtn').addEventListener('click',()=>setWide(!state.wide));setWide(state.wide,false);
 $('presToggle').addEventListener('click',()=>setPres(!state.presOpen));$('presClose').addEventListener('click',()=>setPres(false));
 setPres(state.presOpen,false);
 $('detailTabs').querySelectorAll('[data-tab]').forEach(b=>b.addEventListener('click',()=>{state.tab=b.dataset.tab;showTab();}));
 showTab();
}
// the pressures live in their tab, or pushed out into a column to the right of the side panel (the same element moves)
function setPres(on,remember=true){
 state.presOpen=on;$('presCol').hidden=!on;$('pagegrid').classList.toggle('with-pres',on);
 (on?$('presColBody'):document.querySelector('[data-body="pressures"]')).appendChild($('pressureBody'));
 const tab=$('detailTabs').querySelector('[data-tab="pressures"]');tab.hidden=on;if(on&&state.tab==='pressures')state.tab='step';
 const b=$('presToggle');b.setAttribute('aria-pressed',on);b.textContent=on?'⇤':'⇥';
 {const t=on?'Put the pressures back in the tabs':'Open the pressures in a column to the right';b.title=t;b.setAttribute('aria-label',t);}
 if(remember)try{localStorage.setItem('sg-pres-column',on?'1':'0');}catch(e){}
 showTab();
}
// the page browser keeps the site's margins unless they are unlocked; the site menu never moves
function setWide(on,remember=true){
 state.wide=on;document.body.classList.toggle('wide',on);
 const b=$('wideBtn');b.setAttribute('aria-pressed',on);{const t=on?'Back to the standard width':'Use the full window width';b.title=t;b.setAttribute('aria-label',t);}
 if(remember)try{localStorage.setItem('sg-wide',on?'1':'0');}catch(e){}
}
function showTab(){
 $('detailTabs').querySelectorAll('[data-tab]').forEach(b=>{const on=b.dataset.tab===state.tab;b.classList.toggle('on',on);b.setAttribute('aria-selected',on);});
 document.querySelectorAll('.detail .tabbody').forEach(el=>{el.hidden=el.dataset.body!==state.tab;});
 renderAux(state.cursor?state.cursor.pos:state.sel);
}
// the source needs its own view only when the page cannot show it: a far draw, a source from Timm's archive or a
// suggestion, or a window on lines of the previous page
function sourceOffPage(pos){
 const rec=pos==null?null:currentRecord();if(!rec)return false;let S=null,P=null;
 if(rec.t==='S')S=rec;else if(rec.t==='P'){P=rec;S=sForP(pos,rec);}else if(rec.t==='A'){P=pForA(pos,rec);S=P?sForP(pos,P):null;}
 if(S)return !!S.far||S.lines.some(([ln])=>R().text.page_of[ln]!==state.page);
 return !!(P&&P.mode&&P.mode!=='LOCALY');
}
function renderAux(pos){
 const off=sourceOffPage(pos),tab=$('detailTabs').querySelector('[data-tab="source"]');
 tab.classList.toggle('flag',off);tab.title=off?'The source is not on this page: see it here':'The source window and the chosen source are marked on the page';
 if(state.tab==='source'){if(pos==null)$('poolBody').innerHTML='<span class="muted">Click a word, or play the page.</span>';else{renderPool(pos);if(!off&&$('poolBody').firstElementChild)$('poolBody').insertAdjacentHTML('afterbegin','<p class="small muted onpage">Also marked on the page: shaded lines, outlined word.</p>');}}
 if(state.presOpen||state.tab==='pressures')renderPressures(pos);
}

// ---------------------------------------------------------------- the Step log: one row per record, details in tooltips
const fp=x=>x>=1?fmt(x,1):x>=0.1?fmt(x,2):fmt(x,3);   // a percentage with enough digits for small probabilities
const tipAttr=t=>t?` data-tip="${esc(t)}"`:'';
const badge=(cls,label,tip)=>`<span class="dec ${cls}"${tipAttr(tip)}>${esc(label)}</span>`;
const flag=(label,tip)=>`<span class="flag"${tipAttr(tip)}>${esc(label)}</span>`;
const srcChip=(cls,label,tip)=>`<span class="src ${cls}"${tipAttr(tip)}>${esc(label)}</span>`;
const wordCode=(w,tip)=>`<code class="w"${tipAttr(tip)}>${esc(w)}</code>`;
const numCell=(text,tip)=>`<span${tipAttr(tip)}>${text}</span>`;
const row=(stage,main,num,bd,cls='')=>`<div class="lr ${cls}"><span class="st">${stage}</span><span class="mn">${main}</span><span class="nm">${num}</span><span class="bd">${bd}</span></div>`;
const recWrap=(k,now,later,inner)=>`<div class="rec${now?' now':''}${later?' later':''}"${k>=0?` data-k="${k}"`:''}>${inner}</div>`;
const plural=(n,w)=>`${int(n)} ${w}${n===1?'':'s'}`;
function attemptSummary(a,ev){
 const d=a.ks.filter(k=>ev[k].t==='S').length,draws=d?plural(d,'draw')+' · ':'';
 if(a.p==null)return draws+'no proposal';
 const p=ev[a.p];
 return `${draws}<code>${esc(p.src)}</code> → <code>${esc(p.props.map(x=>x[0]).join(' + '))}</code>${p.dec==='N'?` → <code>${esc(p.inn.word)}</code>`:''} · ${OUTCOME[SL.outcome(ev,p)][1]}`;
}
// one square per attempt, coloured by its outcome; past 40 attempts, runs of one outcome merge into a segment
function strip(att,ev,cur){
 const key=a=>a.p!=null?SL.outcome(ev,ev[a.p]):'X',sq=(a,i)=>`<i class="${OUTCOME[key(a)][0]}${i===cur?' now':''}" data-k="${a.p??a.ks[0]}"${tipAttr(`Attempt ${i+1}: ${attemptSummary(a,ev)}`)}></i>`;
 let cells;
 if(att.length<=40)cells=att.map(sq).join('');
 else{
  const runs=[];att.forEach((a,i)=>{const o=key(a),r=runs[runs.length-1];if(r&&r.o===o&&i!==cur&&r.b!==cur)r.b=i;else runs.push({o,a:i,b:i});});
  cells=`<span class="segs">${runs.map(r=>r.a===r.b?sq(att[r.a],r.a):`<i class="seg ${OUTCOME[r.o][0]}" style="flex-grow:${r.b-r.a+1}" data-k="${att[r.a].p??att[r.a].ks[0]}"${tipAttr(`Attempts ${r.a+1}–${r.b+1}: ${OUTCOME[r.o][1]}`)}></i>`).join('')}</span>`;
 }
 return `<div class="strip"><span class="muted">${int(att.length)} attempts</span>${cells}</div>`;
}
function foldRow([a,b],att,ev,later){
 const c=new Map();
 for(let i=a;i<=b;i++){const p=att[i].p,o=p!=null?OUTCOME[SL.outcome(ev,ev[p])][1]:'no proposal';c.set(o,(c.get(o)||0)+1);}
 return `<button type="button" class="fold${later?' later':''}" title="Show every attempt">${a===b?`Attempt ${a+1}`:`Attempts ${a+1}–${b+1}`}: ${[...c].sort((x,y)=>y[1]-x[1]).map(([o,n])=>`${int(n)} ${esc(o)}`).join(' · ')} <span class="muted">· show</span></button>`;
}
// a run of draws Timm discarded, folded into one row: how many, and the words drawn most often
function skipRow(ks,ev,later){
 const R_=R(),c=new Map();let far=0;
 for(const k of ks){const e=ev[k],w=e.far?posLabel(SL.farPos(e)).word:e.mode==='empty'?'—':(R_.text.lines[e.pick[0]]||[])[e.pick[1]]||'';c.set(w,(c.get(w)||0)+1);if(e.far)far++;}
 const top=[...c].sort((a,b)=>b[1]-a[1]),words=top.slice(0,3).map(([w,n])=>`<code class="w">${esc(w)}</code>${n>1?`<span class="op">×${int(n)}</span>`:''}`).join(' ');
 const main=`${int(ks.length)} draws: ${words}${top.length>3?`<span class="op">+${int(top.length-3)} more</span>`:''}`;
 return `<div class="rec fold-s${later?' later':''}" title="Show each draw">${row('draw',main,'',badge('X','skipped',`${int(far)} from the far supply, ${int(ks.length-far)} from Timm's window. Timm's own rule discards each (a long word, the same source twice, or a combined word) and draws again.`),'dim')}</div>`;
}
function drawRec(e,ev,k){
 const R_=R(),A=R_.args,at=(ln,i)=>(R_.text.lines[ln]||[])[i]||'',sk=SL.skipped(ev,k,FP());
 const n=e.lines.length,nw=e.lines.reduce((a,[ln])=>a+(R_.text.lines[ln]||[]).length,0);
 const win=`Timm's page window: the last ${plural(n,'line')} on the page, ${plural(nw,'word')}.`;
 const timm=e.def?`Timm's own draw: line ${e.def[0]+1}, word ${e.def[1]+1}`:'';
 let main,num='';
 if(e.mode==='empty')main=srcChip('','window','No lines on the page yet.')+wordCode('—',timm&&timm+'.');
 else if(e.far){
  const p=SL.farPos(e),L=posLabel(p),pool=e.buf?`the ${int(e.pool[1])} most recently used distinct word forms`:`the last ${int(e.pool[1])} written words`;
  main=srcChip('far','far',`The governor's far rule (probability ${fmt(A.far||0,2)}): the source comes from ${pool}, not from Timm's window.`)+wordCode(L.word,`Last used at token ${int(p+1)}: page ${L.page+1}, line ${L.ln+1}.`);
  num=numCell(`${fp(100*e.prob)}%`,`Selection probability ${fp(100*e.prob)}% (uniform ${fp(100/e.pool[1])}%)<br>Pressure score ${signed(e.score,2)}`);
 }else{
  const [pl,pi]=e.pick,pw=at(pl,pi),where=`Line ${pl+1}, word ${pi+1}`;
  if(e.mode==='timm')main=srcChip('','window',win)+wordCode(pw,`${where}: Timm's own draw.`);
  else{
   const same=e.def&&e.def[0]===pl&&e.def[1]===pi;
   main=srcChip('','window',win)+`<span class="grp">${same?'':`<s class="timm"${tipAttr(`${timm} (<code>${esc(at(e.def[0],e.def[1]))}</code>); the governor picked another word.`)}>${esc(at(e.def[0],e.def[1]))}</s> → `}${wordCode(pw,`${where}${same?': Timm\'s own draw, kept by the governor':''}.`)}</span>`;
   num=numCell(`${fp(100*e.prob)}%`,`Selection probability ${fp(100*e.prob)}% (Timm's ${fp(100*e.base)}%)<br>Pressure score ${signed(e.score,2)}`);
  }
 }
 if(e.rep)main+=flag('no repeat','The word just written is left out of this draw: Timm refused its repeat once at this position.');
 if(e.cap)main+=flag('cap',`No word may take more than ${pct(A.source_cap||0,0)} of this draw; the excess went to the other words.`);
 const next=ev[k+1],bd=!sk?'':next.t==='P'&&next.mode==='LOCALY'?badge('X','unused',LOOP_GUARD):badge('X','skipped',`Timm's own rule discards the draw (a long word, the same source twice, or a combined word) and draws again${next.t==='P'?`; the next source came from his ${esc(MODE[next.mode]||next.mode)}`:''}.`);
 return row('draw',main,num,bd,sk?'dim':'');
}
function proposalRec(e,ev){
 const A=R().args,o=SL.outcome(ev,e),src=e.srcpos>=0?posLabel(e.srcpos):null,srcw=src&&src.word,where=src?`page ${src.page+1}, line ${src.ln+1}`:'';
 let main=SL.forced(ev,ev.indexOf(e),FP())?srcChip('mode','forced',LOOP_GUARD):e.mode&&e.mode!=='LOCALY'?srcChip('mode',SRC_CHIP[e.mode]||e.mode.toLowerCase(),`Source from Timm's ${esc(MODE[e.mode]||e.mode)}${where?`: ${where}`:''}.`):'';
 // the source as the morph received it: Timm's chooser may have removed an initial gallows from the picked word
 const vt=finite(e.es)?`<br>Value ${signed(e.es,2)}`:'',gallows=srcw&&srcw!==e.src&&srcw.replace(/^(ckh|cth|cph|cfh|k|t|p|f)/,'')===e.src;
 main+='<span class="grp">';
 if(gallows)main+=`<code class="w"${tipAttr(`Picked <code>${esc(srcw)}</code> (${where}); Timm's chooser removed its initial gallows before the morph.${vt}`)}><s>${esc(srcw.slice(0,srcw.length-e.src.length))}</s>${esc(e.src)}</code>`;
 else main+=wordCode(e.src,`Source${where?` (${where})`:''}${srcw&&srcw!==e.src?`: Timm's chooser changed the picked <code>${esc(srcw)}</code> before the morph`:''}.${vt}`);
 main+=' → '+e.props.map(([w,ty],k)=>`<span${tipAttr(`${esc(ty.toLowerCase())}${e.vals?`<br>Value ${signed(e.vals[k],2)}`:''}`)}>${diffWord(e.src,w)}</span>`).join(' + ')+'</span>';
 main+=`<span class="op">${esc([...new Set(e.props.map(p=>p[1].toLowerCase()))].join(' · '))}</span>`;
 if(e.inn_failed)main+=flag('no candidate','The innovator fired but found no legal candidate.');
 if(e.props.length>1&&(o==='A'||o==='T'||o==='C'))main+=flag('+1 token','The second part is written at the next position.');
 if(e.dec==='N'){
  const I=e.inn,why=I.short_new?'New but short for the slot':'Already in the text';
  return row('proposal',main,'',badge('N','replaced',`${why}: the innovator replaces it.`))+innovatorRows(e,o);
 }
 const pa=finite(e.delta)?Math.min(1,Math.exp((A.beta_m??1)*e.delta)):null;
 const num=e.dec!=='T'&&e.changed&&finite(e.delta)?numCell(`Δ ${signed(e.delta,2)}`,`Value: source ${signed(e.es,2)} → proposal ${(e.vals||[]).map(v=>signed(v,2)).join(', ')}<br>Δ ${signed(e.delta,2)} · acceptance probability ${fp(100*pa)}%`):'';
 const tips={A:`Accepted${e.delta<0?` with probability ${fp(100*pa)}%`:': Δ ≥ 0'}.`,C:'Unchanged copy: passes without a draw.',T:'Timm\'s run has no governor: every proposal goes to his checks.',
  R:`Rejected (acceptance probability ${fp(100*pa)}%): another source is drawn for this position.`,K:`Rejected after the last of ${int(A.retry||0)} ${A.retry===1?'retry':'retries'}: the unchanged copy <code>${esc(e.src)}</code> is kept.`,
  X:`Refused by Timm's checks (admissible start, repeat caps, fit in the line): he draws again.${e.dec==='A'?' The governor had accepted it.':e.dec==='K'?' The governor had kept the copy.':''}`,
  G:'Equals the word just written, which Timm\'s coin already refused once at this position: another source is drawn.'};
 return row('proposal',main,num,badge(OUTCOME[o][0],OUTCOME[o][1],tips[o]));
}
function innovatorRows(e,o){
 const I=e.inn,prop=e.props[0][0],gal=I.gallows?` · gallows-initial${I.starts==='pf'?' (p or f)':''}`:'';
 const main=`${diffWord(prop,I.word)}<span class="op"${tipAttr(`The <b>${esc(e.slot)}</b> slot runs short of first appearances: target ${pct(I.target,0)}, realised ${pct(I.realised,0)}.<br>Branch: ${esc(BRANCH[I.branch]||I.branch)} (join share ${fmt(I.pc,2)})${gal} · ${plural(I.n,'legal candidate')}.`)}>${esc(BRANCH[I.branch]||I.branch)} · ${plural(I.n,'candidate')}</span>`;
 const num=numCell(`${fp(100*I.prob)}%`,`Selection probability ${fp(100*I.prob)}%<br>Pressure gain ${signed(I.gain,2)}`);
 const bd=o==='X'?badge('X','refused','Refused by Timm\'s checks (admissible start, repeat caps, fit in the line): he draws again.'):badge('N','innovated','Written in place of the proposal.');
 return row('innovator',main,num,bd,'inn')+`<div class="cands">${I.top.map(([w,g,p])=>`<span class="${w===I.word?'sel':''}"${tipAttr(`Pressure gain ${signed(g,2)} · probability ${fp(100*p)}%`)}>${esc(w)} <small>${signed(g,1)}</small></span>`).join('')}</div>`;
}
function writtenRec(e,pos,ev){
 const {ln,idx}=posLabel(pos),t=state.pg.lines.find(L=>L.ln===ln)?.t[idx];
 let main=wordCode(e.word,'')+`<span class="op">${esc(e.type.toLowerCase())}</span>`;
 if(!ev.some(x=>x.t==='P'&&x.id===Math.floor(e.id/100)))main+=flag('part 2','Second part of a split or joined proposal; its first part is the previous token.');
 const tr=trimmedFrom(pos,t);if(tr)main+=flag('trimmed',`Fitted to the line from <code>${esc(tr)}</code> by Timm's trim: a line-final glyph change such as ol → om, shorter glyphs, dropped leading glyphs.`);
 if(t&&t.hx)main+=flag('hapax','The manuscript has this spelling once.');
 if(t&&t.ab)main+=flag('absent','The manuscript does not contain this spelling.');
 return row('written',main,'',e.new?badge('A','new','First appearance in this text.'):badge('X','seen','Already in the text.'));
}
function renderPool(pos){
 const rec=currentRecord();let S=null;
 if(rec){if(rec.t==='S')S=rec;else if(rec.t==='P')S=sForP(pos,rec);else if(rec.t==='A'){const P=pForA(pos,rec);S=P?sForP(pos,P):null;}}
 if(!S){const P=rec&&rec.t==='A'?pForA(pos,rec):rec&&rec.t==='P'?rec:null;$('poolBody').innerHTML=P?`<div class="muted">No window draw for this word: the source came from the ${esc(MODE[P.mode]||P.mode)}.</div>${P.srcpos>=0?srcLine(P.srcpos):''}`:'<span class="muted">—</span>';return;}
 const R_=R();
 if(S.far){
  let html=`<div class="small">${S.buf?`Far supply: the ${int(S.pool[1])} most recently used distinct word forms`:`Recent pool: tokens ${int(S.pool[0]+1)}–${int(S.pool[0]+S.pool[1])} (the last ${int(S.pool[1])} words)`}, uniform base weight × e<sup>pressure</sup>.</div>${srcLine(SL.farPos(S),'chosen')}<div class="small" style="margin-top:6px">Most likely picks:</div><div class="cands">${S.top.map(([p,,pr])=>`<span class="${p===SL.farPos(S)?'sel':''}" data-tip="token ${int(p+1)} · page ${posLabel(p).page+1}, line ${posLabel(p).ln+1} · ${fmt(100*pr,2)}%">${esc(posLabel(p).word)} <small>${fmt(100*pr,1)}%</small></span>`).join('')}</div>`;
  $('poolBody').innerHTML=html;attachTips($('poolBody'));return;
 }
 const W=poolWeights(S,pos);const pick=Array.isArray(S.pick)?R_.text.first_pos[S.pick[0]]+S.pick[1]:null;
 const exact=new Map((S.top||[]).map(([ln,i,p])=>[R_.text.first_pos[ln]+i,p]));
 let html=`<div class="small">${S.lines.length} line${S.lines.length>1?'s':''} in the window${S.mode==='timm'?'; Timm’s base probabilities':`; probability = Timm's base × e<sup>${fmt(R_.args.beta_c,0)} × value</sup>`}. Shade: selection probability.</div>`;
 for(const [ln,mult,same] of S.lines){
  const words=R_.text.lines[ln]||[],p0=R_.text.first_pos[ln],onPage=R_.text.page_of[ln]===state.page;
  html+=`<div class="srcline"><span class="meta">line ${ln+1}${onPage?'':` · page ${R_.text.page_of[ln]+1}`}${mult>1?` · drawn ${mult}×`:''} · same-position word ${same+1}</span>${words.map((w,i)=>{const p=p0+i,pr=exact.get(p)??W.probs.get(p),o=(0.1+0.9*(W.get(p)||0)).toFixed(2);return `<span class="tok" style="background:color-mix(in srgb,var(--pool) ${Math.round(45*o)}%,transparent);${p===pick?'outline:2px solid var(--pick)':''}" data-tip="${esc(w)}: ${fmt(100*(pr||0),2)}%${exact.has(p)?' (exact)':''}">${esc(w)}</span>`;}).join(' ')}</div>`;
 }
 $('poolBody').innerHTML=html;attachTips($('poolBody'));
}
function srcLine(pos,label='source'){const {ln,idx,page}=posLabel(pos),words=R().text.lines[ln]||[];return `<div class="srcline"><span class="meta">${label}: token ${int(pos+1)} · page ${page+1}, line ${ln+1}</span>${words.map((w,i)=>i===idx?`<mark>${esc(w)}</mark>`:esc(w)).join(' ')}</div>`;}
// the pressure vector at the start of the current line (with no word chosen, the page's last line). The rows are the
// constructions most wanted and most in surplus at the page start, kept for the whole page so each bar can be followed;
// the hollow box is the value at the page start, so the gap shows how much the page has resolved
function renderPressures(pos){
 const F=D.model.features,pg=state.pg;if(!pg)return;
 const first=pg.lines[0].ln,ln=pos==null?pg.lines[pg.lines.length-1].ln:lineOfPos(pos),sn=snapFor(ln),s0=snapFor(first);
 if(!sn){$('pressureBody').innerHTML='<span class="muted small">No pressure snapshot on this page yet.</span>';return;}
 const key=`${state.run}:${state.page}`,base=s0||sn;
 if(!state.presRows||state.presRows.key!==key){const idx=[...base.p.keys()].sort((a,b)=>base.p[b]-base.p[a]);state.presRows={key,want:idx.slice(0,7),surplus:idx.slice(-7).reverse()};}
 const w=v=>Math.min(50,Math.abs(v)/3*50),at=v=>`left:${v>=0?50:50-w(v)}%;width:${w(v)}%`;
 const bar=j=>{const v=sn.p[j],v0=s0?s0.p[j]:null,name=esc(F[j].name);
  return `<div class="lab" data-tip="${name}">${name}</div><div class="track" data-tip="${name}<br>line ${sn.ln+1} start ${signed(v,2)}${v0!=null?` · page start ${signed(v0,2)}`:''}"><i class="${v>=0?'pos':'neg'}" style="${at(v)}"></i>${v0!=null?`<b class="start" style="${at(v0)}"></b>`:''}</div><div class="val">${signed(v,2)}</div>`;};
 let html=state.run==='timm'?'<div class="small muted pnote">Timm’s run ignores pressures; shown is what the governor would apply to his text.</div>':'';
 html+=`<div class="small pnote">${pos==null?'End of page: ':''}line ${sn.ln+1} start · <span class="key want"></span>wanted <span class="key surplus"></span>surplus${s0?' <span class="key start"></span>page start':''}</div>`;
 html+=`<div class="bars">${state.presRows.want.map(bar).join('')}</div><div class="bars sep">${state.presRows.surplus.map(bar).join('')}</div>`;
 // the word at this position, or the current proposal: its total, with its constructions folded
 if(pos!=null){
  const rec=currentRecord(),words=[],{word}=posLabel(pos);
  if(rec&&rec.t==='P'){words.push(['source',rec.src]);for(const [x] of rec.props)words.push(['proposal',x]);if(rec.dec==='N')words.push(['innovated',rec.inn.word]);}
  else if(word)words.push(['word',word]);
  for(const [lab,x] of words.slice(0,3)){
   const X=D.M.X(x),v=valueAt(X,sn.p),xs=X.slice().sort((a,b)=>Math.abs(sn.p[b])-Math.abs(sn.p[a]));
   html+=`<details class="wordp" data-lab="${esc(lab)}"${state.wordOpen.has(lab)?' open':''}><summary>${esc(lab)} <code>${esc(x)}</code> · ${X.length} constructions · value <b>${signed(v,2)}</b></summary><div class="bars">${xs.map(bar).join('')}</div></details>`;
  }
 }
 const body=$('pressureBody');body.innerHTML=html;attachTips(body);
 body.querySelectorAll('details.wordp').forEach(d=>d.addEventListener('toggle',()=>{d.open?state.wordOpen.add(d.dataset.lab):state.wordOpen.delete(d.dataset.lab);}));
}

// ---------------------------------------------------------------- replay
function setStep(i){
 const n=state.steps.length;i=Math.max(0,Math.min(n,i));
 if(i>=n){state.cursor=null;$('rpSlider').value=n;$('rpPos').textContent='whole page';renderText();renderSide();return;}
 const [pos,k]=state.steps[i];const ev=recordsOf(pos);const rec=k>=0?ev[k]:null;
 state.cursor={pos,k,written:!rec||rec.t==='A',i};state.sel=null;
 $('rpSlider').value=i;$('rpPos').textContent=`step ${int(i+1)} of ${int(n)} · token ${int(pos-pageRange(state.page)[0]+1)} of ${int(pageRange(state.page)[1]-pageRange(state.page)[0])}`;
 renderText();renderSide();
 const el=$('text').querySelector('.tok.pending,.tok.cur');if(el&&state.playing)el.scrollIntoView({block:'nearest'});
}
function play(){if(state.playing)return;state.playing=true;$('rpPlay').textContent='❚❚ Pause';
 if(!state.cursor)setStep(0);
 const tick=()=>{if(!state.playing)return;const i=(state.cursor?state.cursor.i:-1)+1;
  if(i>=state.steps.length){const k=state.page+1;setStep(state.steps.length);if(k>=R().text.pages){stop();return;}
   state.timer=setTimeout(async()=>{if(!state.playing)return;await showPage(k);if(state.page===k&&state.pg)play();},Math.max(500,2*+$('rpSpeed').value));return;}
  setStep(i);const rec=currentRecord();const base=+$('rpSpeed').value;state.timer=setTimeout(tick,rec&&rec.t==='A'?base*0.6:base);};
 state.timer=setTimeout(tick,+$('rpSpeed').value);}
function stop(){state.playing=false;clearTimeout(state.timer);state.timer=null;if($('rpPlay'))$('rpPlay').textContent='▶ Play';}

// ---------------------------------------------------------------- controls
function bind(){
 $('prevPage').addEventListener('click',()=>showPage(Math.max(0,state.page-1)));
 $('nextPage').addEventListener('click',()=>showPage(Math.min(R().text.pages-1,state.page+1)));
 $('pageSel').addEventListener('change',()=>showPage(+$('pageSel').value));
 $('nodeSel').addEventListener('change',()=>{const s=+$('nodeSel').value,pages=pagesOfNode(s);state.node=s;if(pages.length)showPage(pages.includes(state.page)?state.page:pages[0],true);else{renderTimeline();renderNodeResults();}});
 $('rpPlay').addEventListener('click',()=>state.playing?stop():play());
 $('rpStart').addEventListener('click',()=>{stop();setStep(0);});
 $('rpEnd').addEventListener('click',()=>{stop();setStep(state.steps.length);});
 $('rpBack').addEventListener('click',()=>{stop();setStep((state.cursor?state.cursor.i:state.steps.length)-1);});
 $('rpFwd').addEventListener('click',()=>{stop();setStep((state.cursor?state.cursor.i:-1)+1);});
 $('rpSlider').addEventListener('input',()=>{stop();setStep(+$('rpSlider').value);});
 bindScrub();
 document.addEventListener('keydown',e=>{if(e.target.matches('input,select,textarea'))return;if(e.key==='['||e.key===']'){e.preventDefault();showPage(state.page+(e.key===']'?1:-1));return;}if(e.key==='ArrowRight'){e.preventDefault();stop();setStep((state.cursor?state.cursor.i:-1)+1);}else if(e.key==='ArrowLeft'){e.preventDefault();stop();setStep((state.cursor?state.cursor.i:state.steps.length)-1);}else if(e.key===' '){e.preventDefault();state.playing?stop():play();}});
 document.addEventListener('themechange',()=>{renderTimeline();renderText();});
}
function save(){setHash({run:state.run,page:state.page,node:state.node,pos:state.sel});}
try{await init();}catch(e){error($('text'),e);}
})();
