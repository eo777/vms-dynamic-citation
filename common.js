"use strict";
// Shared by every page: data loading, the unit segmenter and construction matcher (a browser port of the governor's
// Model.compute, verified against it in test/matcher.test.js), chart renderers, tooltips, formatting.
const SG=(()=>{
 const $=id=>document.getElementById(id);
 const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const finite=x=>typeof x==='number'&&Number.isFinite(x);
 const fmt=(x,d=1)=>finite(x)?x.toLocaleString('en-US',{minimumFractionDigits:d,maximumFractionDigits:d}):'—';
 const int=x=>finite(x)?Math.round(x).toLocaleString('en-US'):'—';
 const pct=(x,d=1)=>finite(x)?fmt(100*x,d)+'%':'—';
 const signed=(x,d=2)=>finite(x)?(x>0?'+':x<0?'−':'')+fmt(Math.abs(x),d):'—';
 const sum=a=>a.reduce((s,v)=>s+(finite(v)?v:0),0);
 const mean=a=>{const f=a.filter(finite);return f.length?sum(f)/f.length:NaN;};
 const GROUP_ORDER=['1a','1b','1.5a','2a','5a','6','3b','3a','3c','4c','4a'];
 const groupVar=g=>`var(--g-${String(g).replace('.','_')})`;
 const SERIES={observed:'var(--obs)',fitted:'var(--fit)',timm:'var(--timm)',governed:'var(--gov)',far0:'var(--far0)',iid:'var(--iid)'};
 const cssVar=name=>getComputedStyle(document.documentElement).getPropertyValue(name).trim();

 async function readGz(url){
  const r=await fetch(url);if(!r.ok)throw Error(`${url}: ${r.status}`);
  if(/\.gz(\?|$)/.test(url)){
   if(!('DecompressionStream' in window))throw Error('This browser cannot decompress the data files (no DecompressionStream).');
   return JSON.parse(await new Response(r.body.pipeThrough(new DecompressionStream('gzip'))).text());
  }
  return r.json();
 }
 const cache={};
 const load=url=>cache[url]||(cache[url]=readGz(url).catch(e=>{delete cache[url];throw e;}));

 // ---- units (Zattera slot alphabet), as voynich_gradients.glyph_units.zattera_units
 const COMPOSITES=['cph','cfh','ckh','cth','ch','sh'],SINGLE=new Set('qsdoylrktpfamn');
 function atoms(word){
  const out=[];let i=0;
  while(i<word.length){
   const c=word[i];
   if(c==='{'){const j=word.indexOf('}',i+1);if(j<0){out.push([c,'literal']);i++;continue;}out.push([word.slice(i,j+1),'ligature']);i=j+1;continue;}
   if(c==='@'){const m=/^@\d+;/.exec(word.slice(i));if(m){out.push([m[0],'extended']);i+=m[0].length;continue;}}
   const comp=COMPOSITES.find(k=>word.startsWith(k,i));
   if(comp){out.push([comp,'composite']);i+=comp.length;continue;}
   out.push([c,'glyph']);i++;
  }
  return out;
 }
 function units(word){
  const a=atoms(word),out=[];let i=0;
  while(i<a.length){
   const [raw,kind]=a[i];
   if(kind!=='glyph'&&kind!=='composite'){out.push(raw);i++;continue;}
   if(kind==='composite'){out.push(raw);i++;continue;}
   if(raw==='e'||raw==='i'){let j=i;while(j<a.length&&a[j][1]==='glyph'&&a[j][0]===raw)j++;out.push(raw.repeat(j-i));i=j;continue;}
   out.push(raw);i++;
  }
  return out;
 }
 const rawUnits=word=>atoms(word).flatMap(([s,k])=>k==='glyph'||k==='composite'?[...s]:[s]);

 // ---- construction matcher: Model.compute in governor.py
 function matcher(features){
  const pos=new Map(),patterns=new Map(),prefixes=[],suffixes=[],interactions=[];let maxpat=1;
  const add=(m,k,j)=>{const v=m.get(k);if(v){if(!v.includes(j))v.push(j);}else m.set(k,[j]);};
  features.forEach((f,j)=>{
   for(const r of [f,...(f.aliases||[])]){
    if(r.source==='position'||r.source==='ordered_pair'||r.kind==='position')add(pos,r.name,j);
    else if(r.kind==='prefix')prefixes.push([r.units,j]);
    else if(r.kind==='suffix')suffixes.push([r.units,j]);
    else if(r.kind==='interaction')interactions.push([r.name.split(' & ').map(units),j]);
    else{add(patterns,r.units.join('\u0001'),j);maxpat=Math.max(maxpat,r.units.length);}
   }
  });
  const memo=new Map();
  function X(word){
   if(memo.has(word))return memo.get(word);
   const seq=units(word),n=seq.length,found=new Set(),spans=[];
   for(let w=1;w<=3;w++)if(w<n){spans.push(['prefix:'+seq.slice(0,w).join(''),0,w]);spans.push(['suffix:'+seq.slice(n-w).join(''),n-w,n]);}
   for(let s=1;s<n-1;s++)for(const w of [1,2])if(s+w<n)spans.push(['interior:'+seq.slice(s,s+w).join(''),s,s+w]);
   const names=new Set(spans.map(s=>s[0]));
   for(const x of spans)for(const y of spans)if(x[2]===y[1])names.add(x[0]+' >> '+y[0]);
   for(const nm of names){const v=pos.get(nm);if(v)v.forEach(j=>found.add(j));}
   const subs=new Set();
   for(let k=1;k<=maxpat;k++)for(let i=0;i+k<=n;i++)subs.add(seq.slice(i,i+k).join('\u0001'));
   for(const s of subs){const v=patterns.get(s);if(v)v.forEach(j=>found.add(j));}
   for(const [p,j] of prefixes)if(p.length<=n&&p.every((u,i)=>seq[i]===u))found.add(j);
   for(const [p,j] of suffixes)if(p.length<=n&&p.every((u,i)=>seq[n-p.length+i]===u))found.add(j);
   for(const [parts,j] of interactions)if(parts.every(p=>subs.has(p.join('\u0001'))))found.add(j);
   const out=[...found].sort((a,b)=>a-b);memo.set(word,out);return out;
  }
  return {X};
 }
 // pressure snapshot (base64 of int8, units of 0.025) -> Float32Array
 function snapshot(b64){
  const bin=atob(b64),out=new Float32Array(bin.length);
  for(let i=0;i<bin.length;i++){let v=bin.charCodeAt(i);if(v>127)v-=256;out[i]=v*0.025;}
  return out;
 }
 // the same, as raw int8 steps (for delta-coded snapshots, which the page browser adds up)
 function snapshotInts(b64){
  const bin=atob(b64),out=new Int16Array(bin.length);
  for(let i=0;i<bin.length;i++){let v=bin.charCodeAt(i);if(v>127)v-=256;out[i]=v;}
  return out;
 }
 const valueAt=(X,snap)=>{let s=0;for(const j of X)s+=snap[j];return s;};

 // ---- tooltip
 let tip=null;
 function showTip(html,x,y){
  if(!tip){tip=document.createElement('div');tip.className='tip';document.body.appendChild(tip);}
  tip.innerHTML=html;tip.style.display='block';
  const w=tip.offsetWidth,h=tip.offsetHeight;
  let left=x+14,top=y+14;
  if(left+w>innerWidth-8)left=x-w-10;if(top+h>innerHeight-8)top=y-h-10;
  tip.style.left=left+'px';tip.style.top=top+'px';
 }
 function hideTip(){if(tip)tip.style.display='none';}
 // a tooltip never outlives the pointer. An element redrawn under the pointer (the replay, the step log, the scrubber) or
 // covered by an enlarged chart never sends its mouseleave, so the tooltip also hides whenever the pointer is over nothing
 // that shows one, and on any click, key, wheel or scroll, or when the pointer leaves the window
 const TIPZONE='[data-tip],.tipzone,.tok,.scrub,.chart .hit';
 if(typeof addEventListener==='function'){   // a browser; the tests load this file without one
  addEventListener('mousemove',e=>{if(tip&&tip.style.display!=='none'&&!(e.target.closest&&e.target.closest(TIPZONE)))hideTip();},{capture:true,passive:true});
  for(const ev of ['pointerdown','keydown','wheel','scroll'])addEventListener(ev,hideTip,{capture:true,passive:true});
  document.documentElement.addEventListener('mouseleave',hideTip);
 }
 function attachTips(root){
  root.querySelectorAll('[data-tip]').forEach(el=>{
   el.addEventListener('mousemove',e=>showTip(el.dataset.tip,e.clientX,e.clientY));
   el.addEventListener('mouseleave',hideTip);
  });
 }

 // ---- line chart with Golf group bands, optional seed range bands, hover crosshair
 function golfSpans(groups){const spans=[];groups.forEach((g,i)=>{const last=spans[spans.length-1];if(last&&last.group===g)last.end=i;else spans.push({group:g,start:i,end:i});});return spans;}
 function lineChart(series,labels,opt={}){
  const width=opt.width||900,left=opt.left||54,right=16,top=14,groups=opt.groups||null;
  const spans=groups&&groups.length===labels.length?golfSpans(groups):[];
  const catSpace=spans.length?18:0,bottom=26+catSpace,height=(opt.height||230)+catSpace,pw=width-left-right,ph=height-top-bottom;
  const all=[];for(const s of series){s.values.forEach(v=>finite(v)&&all.push(v));if(s.band)s.band.forEach(b=>b&&b.forEach(v=>finite(v)&&all.push(v)));}
  if(!all.length)return '<p class="empty">No values.</p>';
  let lo=opt.zero===false?Math.min(...all):Math.min(0,...all),hi=Math.max(...all);
  if(opt.max!=null)hi=Math.max(hi,opt.max);if(hi===lo){hi+=Math.abs(hi)*.1||1;}
  const pad=(hi-lo)*.06;hi+=pad;if(lo<0)lo-=pad;
  const X=i=>left+pw*i/Math.max(1,labels.length-1),Y=v=>top+ph*(hi-v)/(hi-lo);
  let svg=`<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${esc(opt.title||'chart')}">`;
  for(const sp of spans){
   const x1=sp.start===0?left:X(sp.start-.5),x2=sp.end===labels.length-1?left+pw:X(sp.end+.5);
   svg+=`<rect class="golf-shade" x="${x1}" y="${top}" width="${x2-x1}" height="${ph}" fill="${groupVar(sp.group)}"/>`;
   if(sp.start>0)svg+=`<line class="golf-boundary" x1="${x1}" x2="${x1}" y1="${top}" y2="${top+ph+10}"/>`;
   svg+=`<rect x="${x1}" y="${top+ph+3}" width="${x2-x1}" height="4" fill="${groupVar(sp.group)}" stroke="var(--line2)" stroke-width=".4"/>`;
   const cx=(x1+x2)/2;if(x2-x1>14)svg+=`<text class="golf-label" text-anchor="middle" x="${cx}" y="${top+ph+19}">${esc(sp.group)}</text>`;
  }
  const digits=opt.digits??(Math.abs(hi)>15?0:Math.abs(hi)<.1?2:1);
  for(let k=0;k<=4;k++){const v=lo+(hi-lo)*k/4,y=Y(v);svg+=`<line class="gridline" x1="${left}" x2="${width-right}" y1="${y}" y2="${y}"/><text class="axis" text-anchor="end" x="${left-7}" y="${y+4}">${esc(fmt(v,digits))}${opt.unit||''}</text>`;}
  if(lo<0&&hi>0)svg+=`<line x1="${left}" x2="${width-right}" y1="${Y(0)}" y2="${Y(0)}" stroke="var(--line2)"/>`;
  for(const i of opt.markers||[])if(i>=0&&i<labels.length)svg+=`<line x1="${X(i)}" x2="${X(i)}" y1="${top}" y2="${top+ph}" stroke="var(--inn)" stroke-width="1.5" stroke-dasharray="4 3"/>`;
  for(const s of series)if(s.band){
   let d='',back='';const [lo_,hi_]=s.band;
   for(let i=0;i<labels.length;i++){if(!finite(lo_[i])||!finite(hi_[i]))continue;d+=`${d?'L':'M'}${X(i).toFixed(1)},${Y(hi_[i]).toFixed(1)} `;back=`L${X(i).toFixed(1)},${Y(lo_[i]).toFixed(1)} `+back;}
   svg+=`<path d="${d}${back}Z" fill="${s.color}" fill-opacity=".18" stroke="none"/>`;
  }
  const ticks=new Set();const count=Math.min(opt.ticks||8,labels.length);for(let i=0;i<count;i++)ticks.add(Math.round(i*(labels.length-1)/Math.max(count-1,1)));
  for(const i of ticks){const anchor=i===0?'start':i===labels.length-1?'end':'middle';svg+=`<text class="axis" text-anchor="${anchor}" x="${X(i)}" y="${height-6}">${esc(labels[i])}</text>`;}
  for(const s of series){
   let path='',started=false;
   for(let i=0;i<s.values.length;i++){const v=s.values[i];if(!finite(v)){started=false;continue;}path+=`${started?'L':'M'}${X(i).toFixed(1)},${Y(v).toFixed(1)} `;started=true;}
   svg+=`<path d="${path}" fill="none" stroke="${s.color}" stroke-width="${s.width||2}" ${s.dash?'stroke-dasharray="5 4"':''} stroke-linejoin="round"/>`;
   if(s.dots)for(let i=0;i<s.values.length;i++){const v=s.values[i];if(finite(v))svg+=`<circle cx="${X(i)}" cy="${Y(v)}" r="2.4" fill="${s.color}"/>`;}
  }
  svg+=`<g class="hover"><line class="xh" x1="0" x2="0" y1="${top}" y2="${top+ph}" stroke="var(--ink2)" stroke-width="1" style="display:none"/><rect class="hit" x="${left}" y="${top}" width="${pw}" height="${ph}" fill="transparent"/></g>`;
  svg+='</svg>';
  const id='c'+Math.random().toString(36).slice(2,8);
  queueMicrotask(()=>{
   const host=document.querySelector(`[data-chart="${id}"]`);if(!host)return;const g=host.querySelector('svg');
   // axis text keeps about 11 px on screen however far the chart is scaled (--k = drawing units per screen pixel)
   const fit=()=>{const w=g.getBoundingClientRect().width;if(w)g.style.setProperty('--k',(width/w).toFixed(3));};fit();if(window.ResizeObserver)new ResizeObserver(fit).observe(g);
   const hit=g.querySelector('.hit'),xh=g.querySelector('.xh');
   hit.addEventListener('mousemove',e=>{
    const r=g.getBoundingClientRect(),sx=(e.clientX-r.left)*width/r.width;
    const i=Math.max(0,Math.min(labels.length-1,Math.round((sx-left)/pw*(labels.length-1))));
    xh.setAttribute('x1',X(i));xh.setAttribute('x2',X(i));xh.style.display='';
    const rows=series.map(s=>`<div><span style="color:${s.color}">■</span> ${esc(s.label)}: <b>${esc(finite(s.values[i])?fmt(s.values[i],opt.tipDigits??2):'—')}${opt.unit||''}</b>${s.band&&finite(s.band[0][i])?` <span style="opacity:.75">±${fmt((s.band[1][i]-s.band[0][i])/2,opt.tipDigits??2)}</span>`:''}</div>`).join('');
    showTip(`<b>${esc(labels[i])}</b>${groups?` · ${esc(groups[i])}`:''}${rows}`,e.clientX,e.clientY);
   });
   hit.addEventListener('mouseleave',()=>{xh.style.display='none';hideTip();});
  });
  return `<div class="chart" data-chart="${id}">${svg}</div>`;
 }
 // a run's name in text ink, with its colour as a dot beside it
 const runName=(r,label=r.label)=>`<span class="rn" style="--c:${r.color}"${label!==r.label?` title="${esc(r.label)}"`:''}>${esc(label)}</span>`;
 const legend=series=>`<div class="legend">${series.map(s=>`<span class="${s.dash?'dash':''}${s.band?' band':''}" style="--c:${s.color}">${esc(s.label)}</span>`).join('')}</div>`;

 // ---- compared bars: observed marker, one bar per run
 function cmpRows(rows,opt={}){
  // rows: [{label, obs, values:[{v,color,label}]}] ; one scale
  const max=Math.max(...rows.flatMap(r=>[r.obs??0,...r.values.map(x=>x.v??0)]))||1;
  return `<div class="cmp">${rows.map(r=>r.values.map((x,k)=>`<div class="lab mono" title="${esc(r.label)}">${k===0?esc(r.label)+(finite(r.obs)?` <small style="font-family:var(--sans);color:var(--muted)">obs ${esc(opt.format?opt.format(r.obs):fmt(r.obs,1))}</small>`:''):''}</div><div class="t" data-tip="${esc(x.label)}: ${esc(opt.format?opt.format(x.v):fmt(x.v,1))}${finite(r.obs)?' · observed '+esc(opt.format?opt.format(r.obs):fmt(r.obs,1)):''}"><i style="width:${100*(x.v||0)/max}%;--c:${x.color}"></i>${finite(r.obs)?`<em style="left:${100*r.obs/max}%"></em>`:''}</div><div class="n">${esc(opt.format?opt.format(x.v):fmt(x.v,1))}</div>`).join('')).join('')}</div>`;
 }

 // ---- diverging heatmap of a square matrix of log ratios (generated / observed)
 function heatmap(matrix,rows,cols,opt={}){
  const cell=opt.cell||18,left=opt.left||34,top=opt.top||30,w=left+cols.length*cell+4,h=top+rows.length*cell+4,lim=opt.limit||2;
  let svg=`<svg viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" role="img" aria-label="${esc(opt.title||'heatmap')}">`;
  cols.forEach((c,j)=>svg+=`<text x="${left+j*cell+cell/2}" y="${top-6}" text-anchor="middle">${esc(c)}</text>`);
  rows.forEach((r,i)=>{
   svg+=`<text x="${left-5}" y="${top+i*cell+cell/2+4}" text-anchor="end">${esc(r)}</text>`;
   cols.forEach((c,j)=>{
    const v=matrix[i][j];let fill='var(--bg)',tipv='no data';
    if(v&&v.n!=null){
     const z=Math.max(-lim,Math.min(lim,v.z)),a=Math.abs(z)/lim;
     fill=z>0?`color-mix(in srgb,var(--dv-red) ${Math.round(100*a)}%,var(--surface))`:z<0?`color-mix(in srgb,var(--dv-blue) ${Math.round(100*a)}%,var(--surface))`:'var(--surface)';
     tipv=v.tip;
    }
    svg+=`<rect x="${left+j*cell}" y="${top+i*cell}" width="${cell-1}" height="${cell-1}" fill="${fill}" data-tip="${esc(`${r} → ${c}: ${tipv}`)}"/>`;
   });
  });
  return svg+'</svg>';
 }

 // ---- small helpers
 const groupsOf=nodes=>nodes.map(n=>n.group);
 function hash(){const o={};for(const [k,v] of new URLSearchParams(location.hash.slice(1)))o[k]=v;return o;}
 function setHash(o){const p=new URLSearchParams();for(const k of Object.keys(o))if(o[k]!=null&&o[k]!=='')p.set(k,o[k]);history.replaceState(null,'',(p.toString()?'#'+p.toString():location.pathname));}
 function runColor(id){return cssVar('--run-'+id)?`var(--run-${id})`:'var(--ink2)';}
 // ---- overlay: a chart opened full width (the enlarge buttons on the small cards)
 function openOverlay(title,html){
  hideTip();
  let ov=document.getElementById('sg-chart-overlay');
  if(!ov){ov=document.createElement('div');ov.id='sg-chart-overlay';ov.className='overlay';ov.innerHTML='<div class="box" role="dialog" aria-modal="true"><header><h3></h3><button type="button" class="close" title="Close (Esc)">\u2715</button></header><div class="body"></div></div>';document.body.appendChild(ov);
   const close=()=>{hideTip();ov.style.display='none';ov.querySelector('.body').innerHTML='';};
   ov.addEventListener('click',e=>{if(e.target===ov||e.target.closest('.close'))close();});
   document.addEventListener('keydown',e=>{if(e.key==='Escape'&&ov.style.display!=='none')close();});}
  ov.querySelector('h3').innerHTML=title;const body=ov.querySelector('.body');body.innerHTML=html;attachTips(body);ov.style.display='flex';
 }
 const enlargeButton=key=>`<button type="button" class="enlarge" data-enlarge="${key}" title="Enlarge this chart">\u2922 enlarge</button>`;
 // every run can be switched on or off in the menu's Runs dropdown (site_nav.js); the choice is kept per browser, and a run
 // marked hidden in featured.json starts off
 function runVisibility(){try{return JSON.parse(localStorage.getItem('sg-run-visibility')||'{}')||{};}catch(e){return {};}}
 function setRunVisible(id,on){const v=runVisibility();v[id]=!!on;try{localStorage.setItem('sg-run-visibility',JSON.stringify(v));}catch(e){}}
 // run colours are theme tokens (--run-<id> in style.css, stepped for light and dark); featured.json's colour is the fallback
 function themeRuns(runs){for(const r of runs){if(r.hex==null)r.hex=r.color;r.color=cssVar('--run-'+r.id)?`var(--run-${r.id})`:r.hex;}return runs;}
 function visibleRuns(runs){const h=hash(),selected=h.runs!=null?new Set(h.runs.split(',')):null,v=runVisibility();return themeRuns(runs).filter(r=>selected?selected.has(r.id):(r.id in v?v[r.id]:!r.hidden));}
 function shareControls(section){return `<span class="share-controls"><a class="direct-link" href="#section=${encodeURIComponent(section)}" data-direct="${esc(section)}" aria-label="Direct link to ${esc(section)}">Link</a><button type="button" data-share="${esc(section)}">Copy link</button></span>`;}
 function bindShares(root,getState){
  const url=section=>{const u=new URL(location.href);u.hash=new URLSearchParams({...getState(),section}).toString();return u.href;};
  const sync=()=>root.querySelectorAll('[data-direct]').forEach(a=>{a.href=url(a.dataset.direct);});
  sync();root.addEventListener('pointerover',sync);root.addEventListener('focusin',sync);
  root.addEventListener('click',async e=>{
   const b=e.target.closest('[data-share]');if(!b)return;const link=url(b.dataset.share);
   try{await navigator.clipboard.writeText(link);b.textContent='Copied';setTimeout(()=>{b.textContent='Copy link';},1800);}
   catch(err){openOverlay('Direct link',`<p>Copy this address to restore the selected runs and controls.</p><input aria-label="Share URL" class="share-url" readonly value="${esc(link)}">`);const input=document.querySelector('.share-url');input.focus();input.select();}
  });
 }
 function restoreSection(){const section=hash().section;if(section)requestAnimationFrame(()=>{const el=document.getElementById(section);if(el)el.scrollIntoView({block:'start'});});}
 function diffWord(a,b){
  // glyph-level diff between a source word and its proposal (LCS over units), as html
  const A=units(a),B=units(b),n=A.length,m=B.length,L=Array.from({length:n+1},()=>new Array(m+1).fill(0));
  for(let i=n-1;i>=0;i--)for(let j=m-1;j>=0;j--)L[i][j]=A[i]===B[j]?L[i+1][j+1]+1:Math.max(L[i+1][j],L[i][j+1]);
  let i=0,j=0,out='';
  while(i<n&&j<m){if(A[i]===B[j]){out+=esc(A[i]);i++;j++;}else if(L[i+1][j]>=L[i][j+1]){out+=`<span class="del">${esc(A[i])}</span>`;i++;}else{out+=`<span class="ins">${esc(B[j])}</span>`;j++;}}
  while(i<n)out+=`<span class="del">${esc(A[i++])}</span>`;while(j<m)out+=`<span class="ins">${esc(B[j++])}</span>`;
  return `<span class="diff mono">${out}</span>`;
 }
 function error(el,e){el.innerHTML=`<div class="error">${esc(e.message||e)}\n\nThe pages read their data with fetch(); open the app through a web server (for example: python -m http.server in the app folder), not from a file:// address.</div>`;console.error(e);}
 return {$,esc,finite,fmt,int,pct,signed,sum,mean,GROUP_ORDER,groupVar,SERIES,cssVar,load,readGz,units,rawUnits,matcher,snapshot,snapshotInts,valueAt,showTip,hideTip,attachTips,lineChart,legend,cmpRows,heatmap,groupsOf,hash,setHash,runColor,runVisibility,setRunVisible,visibleRuns,themeRuns,runName,openOverlay,enlargeButton,diffWord,error,shareControls,bindShares,restoreSection};
})();
