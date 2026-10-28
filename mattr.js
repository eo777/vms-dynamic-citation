"use strict";
(async()=>{
 const {$,esc,load,fmt,int}=SG,M=SG_MATTR,V=window.SG_RELEASE?.build?'?v='+window.SG_RELEASE.build:'';
 const S={run:'timm',scope:'4a',width:100,pos:0,view:'model',follow:true,playing:false,busy:true,loadId:0,detail:true,bands:null,
  streamStart:-1,streamEnd:-1,displayWin:null,displayPos:-1,paintAll:true,line:-1,page:-1,chartBase:null};
 const cache=new Map(),buttons=new Map(),rows=new Map();
 let readerFrame=null;
 const playback=SG_MATTR_RUNTIME.playback({
  step:()=>{if(S.pos>=range()[1]-1)return false;seek(S.pos+1);return true;},interval:()=>Number($('replaySpeed').value),
  onState:playing=>{S.playing=playing;$('wordPlay').textContent=playing?'Ⅱ Pause':'▶ Play';$('wordPlay').setAttribute('aria-label',playing?'Pause replay':'Play replay');},
  onPause:()=>{cancelAnimationFrame(readerFrame);readerFrame=null;const box=$('textViewport');box.scrollTo({top:box.scrollTop,left:box.scrollLeft,behavior:'auto'});},
  save:setHash,onError:fail
 });
 const scope=()=>S.index.scopes.find(s=>s.id===S.scope);
 const endToken=(flat,line)=>flat.first[line]??flat.words.length;
 const range=(flat=S.flat)=>[flat.first[scope().start],endToken(flat,scope().end)];
 const pageIndex=line=>M.upperBound(S.pageStarts,line)-1;
 const event=()=>S.data.events[S.pos-S.data.event_start];
 const info=line=>S.data.pools[line-S.data.start_line];
 const lineLabel=line=>{const p=S.index.pages[pageIndex(line)];return p.id+' · L'+(line-p.start+1);};
 const display=()=>S.view==='observed'?S.observed:{text:S.text,flat:S.flat,series:S.series};
 const observedPos=()=>M.alignToken(S.flat,S.observed.flat,S.pos);
 const band=id=>{const v=S.run==='timm'&&S.bands&&S.bands.nodes[id]&&S.bands.nodes[id][String(S.width)];return v?[Math.min(...v),Math.max(...v)]:null;};
 function busy(on){S.busy=on;$('replayMain').setAttribute('aria-busy',String(on));for(const id of ['replayScope','replayWidth','wordPlay','wordBack','wordNext','wordScrub','folioSelect','textView','jumpPage','jumpLow','jumpModelDrop','jumpObservedDrop'])$(id).disabled=on;}
 function pause(){playback.pause();}
 function play(){if(S.busy)return;if(S.playing){pause();return;}if(S.pos>=range()[1]-1)seek(range()[0]);follow(true);playback.play();}
 function setHash(){if(!S.flat)return;const next='#'+new URLSearchParams({run:S.run,region:S.scope,word:String(S.pos),window:String(S.width),text:S.view});if(location.hash!==next)history.replaceState(null,'',next);}
 function follow(on){S.follow=on;$('followWord').textContent=on?'Following word':'Follow word';$('followWord').setAttribute('aria-pressed',String(on));}
 function fail(e){pause();busy(true);$('replayError').hidden=false;$('replayError').textContent='The saved replay could not be loaded. '+e.message;console.error(e);}
 function resetReader(){S.streamStart=-1;S.streamEnd=-1;S.displayWin=null;S.displayPos=-1;S.line=-1;S.page=-1;S.paintAll=true;}
 function recompute(){
  S.series=M.rolling(S.flat.words,S.width);S.observed.series=M.rolling(S.observed.flat.words,S.width);
  S.means=S.index.nodes.map(n=>({id:n.id,model:M.meanInScope(S.series,endToken(S.flat,n.end)-1,S.flat.first[n.start]),
   observed:M.meanInScope(S.observed.series,endToken(S.observed.flat,n.end)-1,S.observed.flat.first[n.start])}));
 }
 async function chooseRun(id,initialPos=null){
  pause();busy(true);const ticket=++S.loadId,old=S.flat?{line:S.flat.lineOf[S.pos],col:S.pos-S.flat.first[S.flat.lineOf[S.pos]]}:null;
  try{
   if(!cache.has(id))cache.set(id,(async()=>{const cfg=S.index.runs.find(r=>r.id===id),data=await load(cfg.file+V),text=data.text||await load(data.text_url+V);return {data,text,flat:M.flatten(text)};})());
   const r=await cache.get(id);if(ticket!==S.loadId)return;S.run=id;Object.assign(S,r);recompute();
   $('modelLabel').textContent=S.data.label;
   setScope(S.scope,initialPos??(old?S.flat.first[old.line]+Math.min(old.col,S.text.lines[old.line].length-1):range()[0]));
   $('replayError').hidden=true;busy(false);render();
  }catch(e){cache.delete(id);if(ticket===S.loadId)fail(e);}
 }
 function setScope(id,pos=null){
  pause();S.scope=id;resetReader();follow(true);$('replayScope').value=id;const [lo,hi]=range();S.pos=Math.max(lo,Math.min(hi-1,pos??lo));
  $('wordScrub').min=lo;$('wordScrub').max=hi-1;$('regionTitle').textContent=scope().label;
  $('folioSelect').innerHTML=S.index.pages.map((p,i)=>p.start>=scope().start&&p.end<=scope().end?'<option value="'+i+'">'+esc(p.id)+' · '+esc(p.node.split(':')[1])+'</option>':'').join('');
  analyzeDeclines();drawBase();render();
 }
 function analyzeDeclines(){
  S.drops={model:M.declines(S.series.smooth,...range()),observed:M.declines(S.observed.series.smooth,...range(S.observed.flat))};
  $('curveDefinition').textContent='MATTR · '+S.width+'-word windows · mean of the latest 200 windows';
 }
 function seek(pos,manual=false){if(S.busy&&manual)return;if(manual){pause();follow(true);}const [lo,hi]=range();S.pos=Math.round(Math.max(lo,Math.min(hi-1,pos)));render();}
 function jump(kind){
  pause();const line=S.flat.lineOf[S.pos],[lo,hi]=range();let target;
  if(kind==='low'){target=lo;for(let i=lo;i<hi;i++)if(S.series.score[i]<S.series.score[target])target=i;}
  else if(kind==='page'){const p=S.index.pages.find(p=>p.end-1>line&&p.end<=scope().end&&p.start>=scope().start);target=p?S.flat.first[p.end-1]:hi-1;}
  else{const spans=S.drops[kind],current=kind==='observed'?observedPos():S.pos,span=spans.find(d=>d.start>current+1)||spans[0];if(!span)return;target=kind==='observed'?M.alignToken(S.observed.flat,S.flat,span.start):span.start;}
  seek(target,true);
 }
 function streamWindow(start,end){
  const d=display(),box=$('textViewport'),oldRect=box.getBoundingClientRect();
  const anchor=[...rows.entries()].find(([,row])=>row.getBoundingClientRect().bottom>oldRect.top+15);
  const anchorTop=anchor?anchor[1].getBoundingClientRect().top:0;
  S.rebuilding=true;S.streamStart=start;S.streamEnd=end;
  $('pageText').innerHTML=d.text.lines.slice(start,end).map((words,j)=>{
   const line=start+j,p=S.index.pages[pageIndex(line)],first=d.flat.first[line],heading=line===p.start||line===start;
   return '<div class="mr-text-line '+(d.text.par[line]?'opening':'')+'" data-line="'+line+'">'+(heading?'<div class="mr-page-break">'+esc(p.id)+' · '+esc(p.node)+(line!==p.start?' · continued':'')+'</div>':'')+
    '<div class="mr-line-body"><span class="mr-line-label">'+(line-p.start+1)+(d.text.par[line]?'<i>¶</i>':'')+'</span><div class="mr-line-content">'+words.map((w,k)=>'<button class="mr-token" tabindex="-1" data-pos="'+(first+k)+'" title="Word '+int(first+k+1)+' · '+esc(w)+'">'+esc(w)+'</button>').join(' ')+'</div></div></div>';
  }).join('');
  buttons.clear();rows.clear();for(const b of $('pageText').querySelectorAll('[data-pos]'))buttons.set(+b.dataset.pos,b);for(const r of $('pageText').querySelectorAll('[data-line]'))rows.set(+r.dataset.line,r);
  if(anchor&&rows.has(anchor[0]))box.scrollTop+=rows.get(anchor[0]).getBoundingClientRect().top-anchorTop;
  S.paintAll=true;S.rebuilding=false;
 }
 function ensureStream(line){
  if(S.streamStart<0||line<S.streamStart||line>=S.streamEnd){streamWindow(Math.max(scope().start,line-45),Math.min(scope().end,line+75));return;}
  if(S.follow&&(line>S.streamEnd-18||line<S.streamStart+12)&&!(S.streamStart===scope().start&&line<S.streamStart+12)&&!(S.streamEnd===scope().end&&line>S.streamEnd-18))
   streamWindow(Math.max(scope().start,line-45),Math.min(scope().end,line+75));
 }
 function paintReader(win,modelLine,ev){
  const d=display(),pos=S.view==='observed'?observedPos():S.pos,shown=S.view==='observed'?M.step(d.flat.words,pos,S.width):win,line=d.flat.lineOf[pos];
  if(S.follow||S.streamStart<0)ensureStream(line);
  let dirty;if(S.paintAll)dirty=buttons.keys();else{const set=new Set();if(S.displayWin)for(let p=S.displayWin.start;p<S.displayWin.end;p++)set.add(p);for(let p=shown.start;p<shown.end;p++)set.add(p);if(S.displayPos>=0)set.add(S.displayPos);dirty=set;}
  for(const p of dirty){const b=buttons.get(p);if(!b)continue;const cls='mr-token '+(p===pos?'current':p>pos?'future':p<shown.start?'past':shown.counts.get(d.flat.words[p])>1?'repeat':'single');if(b.className!==cls)b.className=cls;if(p===pos)b.setAttribute('aria-current','true');else if(b.hasAttribute('aria-current'))b.removeAttribute('aria-current');}
  const localStart=modelLine-info(modelLine)[0];
  for(const [l,row] of rows){row.classList.toggle('active',l===line);row.classList.toggle('local-source',S.view==='model'&&l>=localStart&&l<modelLine);row.classList.toggle('is-donor',S.view==='model'&&l===ev[1]);}
  if(S.follow&&(pos!==S.displayPos||S.paintAll))scrollCurrent(pos,S.playing&&!S.paintAll);
  S.displayWin=shown;S.displayPos=pos;S.paintAll=false;
 }
 function scrollCurrent(pos,smooth=false){
  const b=buttons.get(pos),box=$('textViewport');if(!b)return;
  const r=b.getBoundingClientRect(),v=box.getBoundingClientRect();
  if(r.top<v.top+box.clientHeight*.28||r.bottom>v.top+box.clientHeight*.65)box.scrollTo({top:box.scrollTop+r.top-v.top-box.clientHeight*.43,behavior:smooth&&!matchMedia('(prefers-reduced-motion: reduce)').matches?'smooth':'auto'});
 }
 function bar(id,forms,tokens){
  const share=tokens?forms/tokens:0;$(id+'Bar').style.setProperty('--share',share*100+'%');
  const label=int(forms)+' forms / '+int(tokens)+' words';$(id+'Count').textContent=label;$(id+'Share').textContent=fmt(share*100,1)+'%';
  $(id+'Bar').setAttribute('aria-label',label+'; '+int(tokens-forms)+' repeated slots');
 }
 function render(){
  if(!S.flat)return;const line=S.flat.lineOf[S.pos],page=pageIndex(line),win=M.step(S.flat.words,S.pos,S.width),ev=event(),pool=info(line),[lo,hi]=range(),op=observedPos();
  $('wordScrub').value=S.pos;$('replayPosition').textContent='Word '+int(S.pos-lo+1)+' / '+int(hi-lo);$('replayExtent').textContent='#'+int(S.pos+1);
  const p=S.index.pages[page];$('folioTitle').textContent=S.view==='model'?'Generated text':'Actual manuscript';$('folioGroup').textContent=(p.group==='4a'?'BIO':p.group)+' · '+p.id+' · '+p.node;
  $('folioSelect').value=page;paintReader(win,line,ev);
  $('windowLabel').textContent='Model · last '+S.width+' words';bar('window',win.unique,win.size);
  if(S.line!==line){bar('local',pool[2],pool[1]);bar('archive',pool[5],pool[4]);$('poolNote').textContent=(line===p.end-1?'Page-final source reset. ':'')+'Pool bars use different word counts; these shares are not MATTR comparisons.';S.line=line;}
  $('localGate').textContent=ev[0]===0?'used':pool[0]+(pool[0]===1?' line':' lines');$('archiveGate').textContent=ev[0]===1?'used':pool[6]?'open':'closed';
  const label={LOCALY:'Local source',PARAGRAPH_INITIAL:'Paragraph archive',SUGGESTION:'Suggestion',FORCE:'Forced suggestion',RANDOM:'Startup'};
  $('wordStep').setAttribute('aria-live',S.playing?'off':'polite');
  $('wordStep').innerHTML='<div class="step-main">'+(S.view==='observed'?'<span>Model step:</span>':'')+'<strong>'+esc(win.entering)+'</strong><span>enters · <strong>'+esc(win.leaving||'—')+'</strong> leaves</span><span class="step-delta '+(win.delta>0?'gain':'')+'">'+(win.delta>0?'+':'')+win.delta+' distinct · '+win.repeated+' repeats / '+win.size+'</span></div><span class="step-source">'+esc(label[S.data.modes[ev[0]]])+(ev[1]>=0?' · '+esc(lineLabel(ev[1])):'')+' · <strong>'+esc(S.data.source_vocab[ev[2]])+'</strong> + <strong>'+esc(S.data.source_vocab[ev[3]])+'</strong> <span class="op">'+esc(S.data.operations[ev[4]].toLowerCase())+'</span></span>';
  const m=S.series.smooth[S.pos],o=S.observed.series.smooth[op];$('modelValue').textContent=fmt(m,3);$('observedValue').textContent=fmt(o,3);$('differenceValue').textContent=(m-o>0?'+':'')+fmt(m-o,3);
  const mean=S.means.find(n=>n.id===p.node);$('bifolioReadout').innerHTML='<strong>'+esc(p.node)+'</strong> · bifolium MATTR: <span class="model">model '+fmt(mean.model,3)+'</span>'+(band(p.node)?' <span class="muted">(seeds 1–'+S.bands.seeds.length+': '+fmt(band(p.node)[0],3)+'–'+fmt(band(p.node)[1],3)+')</span>':'')+' · manuscript '+fmt(mean.observed,3);
  $('chartReadout').textContent=S.drops.model.length+' model / '+S.drops.observed.length+' MS decline spans · fall ≥ 0.05 over 100 tokens';
  drawCursor();S.page=page;playback.saveSoon();
  $('wordBack').disabled=S.busy||S.pos===lo;$('wordNext').disabled=S.busy||S.pos===hi-1;$('jumpModelDrop').disabled=S.busy||!S.drops.model.length;$('jumpObservedDrop').disabled=S.busy||!S.drops.observed.length;
 }
 // the band legend shows only while there is a band to read: Original Timm, means on
 function legendBands(){$('bandLegend').hidden=!(S.means_shown&&S.run==='timm'&&S.bands);}
 function drawBase(){
  legendBands();
  if(!S.series)return;const canvas=$('replayChart'),w=canvas.clientWidth,h=canvas.clientHeight;if(w<20||h<20)return;
  const dpr=devicePixelRatio||1;canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);const base=document.createElement('canvas');base.width=canvas.width;base.height=canvas.height;const c=base.getContext('2d');c.scale(dpr,dpr);
  const style=getComputedStyle(document.documentElement),col=n=>style.getPropertyValue(n).trim(),blue=col('--pool'),ink=col('--ink'),muted=col('--ink2'),gold=col('--hapax'),grid=col('--line');
  const [lo,hi]=range(),[ol,oh]=range(S.observed.flat),left=40,right=w-14,top=38,gap=54,poolTop=h-51,poolBottom=h-19,plotHeight=(h-83-top-gap)/2;
  let min=1,max=0,maxPool=1;for(const [values,a,b] of [[S.detail?S.series.score:S.series.smooth,lo,hi],[S.detail?S.observed.series.score:S.observed.series.smooth,ol,oh]])for(let i=a;i<b;i++)if(Number.isFinite(values[i])){min=Math.min(min,values[i]);max=Math.max(max,values[i]);}
  for(const n of S.index.nodes)if(n.end>scope().start&&n.start<scope().end){const m=S.means.find(m=>m.id===n.id);if(!S.means_on())continue;for(const v of [m.model,m.observed,...(band(n.id)||[])])if(v!==null){min=Math.min(min,v);max=Math.max(max,v);}}
  min=Math.max(0,Math.floor((min-.025)*20)/20);max=Math.min(1,Math.ceil((max+.025)*20)/20);if(max-min<.15){min=Math.max(0,min-.05);max=Math.min(1,max+.05);}
  for(let l=scope().start;l<scope().end;l++)maxPool=Math.max(maxPool,info(l)[1]);
  const x=p=>left+(p-ol)/(oh-ol-1)*(right-left),xm=p=>x(M.alignedPosition(S.flat,S.observed.flat,p)),yp=v=>poolBottom-v/maxPool*(poolBottom-poolTop);
  const panels=[
   {kind:'observed',title:'ACTUAL MANUSCRIPT',series:S.observed.series,start:ol,end:oh,xx:x,color:ink,dash:[],top},
   {kind:'model',title:'ORIGINAL TIMM',series:S.series,start:lo,end:hi,xx:xm,color:blue,dash:[],top:top+plotHeight+gap}
  ];
  for(const p of panels){
   p.bottom=p.top+plotHeight;p.y=v=>p.bottom-(v-min)/(max-min)*plotHeight;
   c.textBaseline='middle';c.textAlign='left';c.font='600 10px system-ui';c.fillStyle=p.color;c.fillText(p.title,left,p.top-28);
   c.font='9px system-ui';c.fillStyle=muted;c.textAlign='right';c.fillText('MATTR',left-7,p.top-11);
   // Both reference means appear in each panel on the same MATTR scale.
   let lastLabel=-Infinity;
   for(const [i,n] of S.index.nodes.entries()){
    if(n.end<=scope().start||n.start>=scope().end)continue;const a=Math.max(left,x(S.observed.flat.first[n.start])),b=Math.min(right,x(endToken(S.observed.flat,n.end))),mid=(a+b)/2;
    c.fillStyle=col(i%2?'--band-b':'--band-a');c.globalAlpha=.28;c.fillRect(a,p.top,b-a,plotHeight);c.globalAlpha=1;
    if(mid-lastLabel>42){c.textAlign='center';c.fillStyle=muted;c.fillText(n.id.split(':')[1],mid,p.top-11);lastLabel=mid;}
    const means=S.means[i],bd=band(n.id);
    if(S.means_on()&&bd){c.save();c.fillStyle=blue;c.globalAlpha=.16;c.fillRect(a+2,p.y(bd[1]),Math.max(0,b-a-4),Math.max(1,p.y(bd[0])-p.y(bd[1])));c.restore();}
    if(S.means_on())for(const [v,color,dash] of [[means.model,blue,[]],[means.observed,ink,[]]])if(v!==null){
     const yy=p.y(v),aa=a+2,bb=Math.max(aa,b-2);c.save();c.fillStyle=color;c.globalAlpha=.23;if(!(bd&&color===blue))c.fillRect(aa,yy-5,bb-aa,10);
     c.strokeStyle=color;c.globalAlpha=.72;c.lineWidth=1.7;c.setLineDash(dash);c.beginPath();c.moveTo(aa,yy);c.lineTo(bb,yy);c.stroke();
     c.setLineDash([]);c.lineWidth=1;c.beginPath();c.moveTo(aa,yy-4);c.lineTo(aa,yy+4);c.moveTo(bb,yy-4);c.lineTo(bb,yy+4);c.stroke();c.restore();
    }
    c.strokeStyle=grid;c.lineWidth=.6;c.beginPath();c.moveTo(a,p.top);c.lineTo(a,p.bottom);c.stroke();
   }
   c.textAlign='right';const stride=(max-min)>.4||plotHeight<150?.1:.05;
   for(let v=Math.ceil(min/stride)*stride;v<=max+.001;v+=stride){c.strokeStyle=grid;c.lineWidth=.6;c.beginPath();c.moveTo(left,p.y(v));c.lineTo(right,p.y(v));c.stroke();c.fillStyle=muted;c.fillText(v.toFixed(2),left-7,p.y(v));}
   function curve(values,yy,color,alpha,width,dash=[]){
    c.save();c.beginPath();c.rect(left,p.top,right-left,plotHeight);c.clip();c.strokeStyle=color;c.globalAlpha=alpha;c.lineWidth=width;c.setLineDash(dash);c.beginPath();let started=false;
    for(let i=p.start;i<p.end;i++){if(!Number.isFinite(values[i])){started=false;continue;}if(!started){c.moveTo(p.xx(i),yy(values[i]));started=true;}else c.lineTo(p.xx(i),yy(values[i]));}c.stroke();c.restore();
   }
   if(S.detail)curve(p.series.score,p.y,p.color,.45,1);
   curve(p.series.smooth,p.y,p.color,1,2,p.dash);
   c.fillStyle=gold;for(const span of S.drops[p.kind])c.fillRect(Math.max(left,p.xx(span.start)),p.bottom+5,Math.max(1,Math.min(right,p.xx(span.end))-Math.max(left,p.xx(span.start))),3);
  }
  c.fillStyle=muted;c.textAlign='left';c.font='9px system-ui';c.fillText('Timm local source words · 0–'+int(maxPool),left,poolTop-10);
  c.strokeStyle=gold;c.lineWidth=1.2;c.beginPath();let prev=null;for(let l=scope().start;l<scope().end;l++){const xx=x(S.observed.flat.first[l]),yy=yp(info(l)[1]);if(prev===null)c.moveTo(xx,yy);else{c.lineTo(xx,prev);c.lineTo(xx,yy);}prev=yy;}c.lineTo(right,prev);c.stroke();
  c.strokeStyle=grid;c.beginPath();c.moveTo(left,poolBottom);c.lineTo(right,poolBottom);c.stroke();
  c.fillStyle=muted;for(let i=0;i<=4;i++){c.textAlign=i===0?'left':i===4?'right':'center';c.fillText(int(Math.round((oh-ol-1)*i/4)+1),left+(right-left)*i/4,h-5);}
  S.chartBase=base;S.chartGeom={w,h,dpr,left,right,top,poolBottom,x,xm,ol,oh,panels};drawCursor();
 }
 function drawCursor(){
  if(!S.chartBase)return;const c=$('replayChart').getContext('2d'),g=S.chartGeom;c.setTransform(1,0,0,1,0,0);c.clearRect(0,0,g.w*g.dpr,g.h*g.dpr);c.drawImage(S.chartBase,0,0);c.scale(g.dpr,g.dpr);
  const css=getComputedStyle(document.documentElement),xx=g.xm(S.pos),op=observedPos();c.strokeStyle=css.getPropertyValue('--muted').trim();c.lineWidth=1;c.setLineDash([2,3]);
  for(const p of g.panels){c.beginPath();c.moveTo(xx,p.top);c.lineTo(xx,p.bottom+8);c.stroke();}
  c.beginPath();c.moveTo(xx,g.poolBottom-32);c.lineTo(xx,g.poolBottom);c.stroke();c.setLineDash([]);
  for(const p of g.panels){
   const pos=p.kind==='model'?S.pos:op;
   const v=p.series.smooth[pos];if(Number.isFinite(v)){c.fillStyle=p.color;c.beginPath();c.arc(xx,p.y(v),3,0,Math.PI*2);c.fill();}
  }
 }
 function bind(){
  $('replayScope').onchange=e=>setScope(e.target.value);
  $('replayWidth').onchange=e=>{pause();S.width=+e.target.value;recompute();analyzeDeclines();S.paintAll=true;drawBase();render();};
  $('wordPlay').onclick=play;$('wordBack').onclick=()=>seek(S.pos-1,true);$('wordNext').onclick=()=>seek(S.pos+1,true);$('wordScrub').oninput=e=>seek(+e.target.value,true);
  $('folioSelect').onchange=e=>seek(S.flat.first[S.index.pages[+e.target.value].start],true);
  $('jumpPage').onclick=()=>jump('page');$('jumpLow').onclick=()=>jump('low');$('jumpModelDrop').onclick=()=>jump('model');$('jumpObservedDrop').onclick=()=>jump('observed');
  $('textView').onchange=e=>{S.view=e.target.value;resetReader();follow(true);render();};$('followWord').onclick=()=>{follow(!S.follow);if(S.follow)render();};
  $('pageText').onclick=e=>{const b=e.target.closest('[data-pos]');if(b)seek(S.view==='observed'?M.alignToken(S.observed.flat,S.flat,+b.dataset.pos):+b.dataset.pos,true);};
  const box=$('textViewport');box.addEventListener('wheel',()=>follow(false),{passive:true});box.addEventListener('touchstart',()=>follow(false),{passive:true});
  box.onscroll=()=>{if(S.rebuilding||S.follow||S.busy)return;let start=S.streamStart;if(box.scrollTop<70&&start>scope().start)start=Math.max(scope().start,start-50);else if(box.scrollTop+box.clientHeight>box.scrollHeight-100&&S.streamEnd<scope().end)start=Math.min(scope().end-120,start+50);else return;if(start===S.streamStart)return;streamWindow(start,Math.min(scope().end,start+120));render();};
  $('detailCurve').onclick=()=>{S.detail=!S.detail;$('detailCurve').setAttribute('aria-pressed',String(S.detail));drawBase();};
  $('meanBars').onclick=()=>{S.means_shown=!S.means_shown;$('meanBars').setAttribute('aria-pressed',String(S.means_shown));legendBands();drawBase();};
  $('readMethod').onclick=()=>{pause();$('methodDialog').showModal();};$('closeMethod').onclick=()=>$('methodDialog').close();
  const canvas=$('replayChart');let dragging=false;const chartSeek=e=>{if(S.busy||!S.chartGeom)return;const g=S.chartGeom,rect=canvas.getBoundingClientRect(),f=Math.max(0,Math.min(1,(e.clientX-rect.left-g.left)/(g.right-g.left))),p=Math.round(g.ol+f*(g.oh-g.ol-1));seek(M.alignToken(S.observed.flat,S.flat,p),true);};
  canvas.onpointerdown=e=>{dragging=true;canvas.setPointerCapture(e.pointerId);chartSeek(e);};canvas.onpointermove=e=>{if(dragging)chartSeek(e);};canvas.onpointerup=()=>dragging=false;canvas.onpointercancel=()=>dragging=false;
  document.addEventListener('keydown',e=>{if(S.busy||$('methodDialog').open||e.ctrlKey||e.altKey||e.metaKey||e.target.matches('input,select,textarea')||e.target.isContentEditable)return;if(e.key==='ArrowLeft'||e.key==='ArrowRight'){e.preventDefault();seek(S.pos+(e.key==='ArrowLeft'?-1:1),true);}else if(e.code==='Space'&&!e.target.closest('button')){e.preventDefault();play();}});
  document.addEventListener('themechange',drawBase);document.addEventListener('visibilitychange',()=>{if(document.hidden)pause();});window.addEventListener('pagehide',pause);
  new ResizeObserver(()=>document.documentElement.style.setProperty('--mr-nav-height',document.querySelector('.site-nav').offsetHeight+'px')).observe(document.querySelector('.site-nav'));
  new ResizeObserver(()=>{cancelAnimationFrame(readerFrame);readerFrame=requestAnimationFrame(()=>{readerFrame=null;if(S.flat&&S.follow&&!S.busy)scrollCurrent(S.displayPos);});}).observe(box);
  let frame;new ResizeObserver(()=>{cancelAnimationFrame(frame);frame=requestAnimationFrame(drawBase);}).observe(canvas);
 }
 try{
  S.index=await load('data/mattr_replay/index.json?v=9742ae923f');S.bands=await load('data/mattr_replay/seed_bands.json?v=50129474ed'+V).catch(()=>null);
  S.means_shown=true;S.means_on=()=>S.means_shown;S.pageStarts=S.index.pages.map(p=>p.start);
  const text=await load(S.index.observed_file+V);S.observed={text,flat:M.flatten(text)};
  const h=new URLSearchParams(location.hash.slice(1));S.run='timm';S.scope=S.index.scopes.some(s=>s.id===h.get('region'))?h.get('region'):'4a';S.width=[50,100,200].includes(+h.get('window'))?+h.get('window'):100;S.view=h.get('text')==='observed'?'observed':'model';
  $('replayScope').innerHTML=S.index.scopes.map(s=>'<option value="'+s.id+'">'+esc(s.label)+'</option>').join('');$('replayWidth').value=S.width;$('textView').value=S.view;bind();
  await chooseRun(S.run,h.has('word')&&Number.isFinite(+h.get('word'))?+h.get('word'):null);
 }catch(e){fail(e);}
})();
