"use strict";
// One menu for every page: fills <nav class="site-nav"></nav>, marks the current page, adds the theme toggle.
(function(){
 const pages=[['./','Overview'],['pages.html','Pages'],['mattr.html','MATTR replay'],['heatmap.html','MATTR heatmap'],['reconstruction.html','Reconstruction'],['comparison.html','Comparison'],['innovation.html','Innovation'],['charts.html','Charts'],['validation.html','Validation'],['modifications.html','Modifications']];
 let nav=document.querySelector('nav.site-nav');
 if(!nav){nav=document.createElement('nav');nav.className='site-nav';document.body.prepend(nav);}
 nav.setAttribute('aria-label','Governed self-citation');
 const here=decodeURIComponent(location.pathname.split('/').pop()||'index.html');
 const brand=document.createElement('a');brand.className='brand';brand.href='./';brand.textContent='Governed self-citation';
 const links=pages.map(([href,label])=>{const a=document.createElement('a');a.href=href;a.textContent=label;if((href==='./'?'index.html':href)===here)a.setAttribute('aria-current','page');return a;});
 const spacer=document.createElement('span');spacer.className='spacer';
 const tag=document.createElement('span');tag.className='tag';tag.id='releaseTag';
 const theme=document.createElement('button');theme.type='button';theme.className='theme';
 const stored=(()=>{try{return localStorage.getItem('sg-theme');}catch(e){return null;}})();
 if(stored)document.documentElement.dataset.theme=stored;
 const label=()=>{const t=document.documentElement.dataset.theme;theme.textContent=t==='dark'?'Light':t==='light'?'Dark':(matchMedia('(prefers-color-scheme: dark)').matches?'Light':'Dark');};
 theme.addEventListener('click',()=>{const dark=document.documentElement.dataset.theme==='dark'||(!document.documentElement.dataset.theme&&matchMedia('(prefers-color-scheme: dark)').matches);const next=dark?'light':'dark';document.documentElement.dataset.theme=next;try{localStorage.setItem('sg-theme',next);}catch(e){}label();document.dispatchEvent(new CustomEvent('themechange'));});
 label();
 const opts=document.createElement('span');opts.className='runopts';
 nav.replaceChildren(brand,...links,spacer,opts,tag,theme);
 // the Runs dropdown: a checkbox per run, kept per browser; a run marked hidden in featured.json starts off. Pages read the
 // choice when they load (SG.visibleRuns), so a change reloads the page.
 const key='sg-run-visibility',vis=()=>{try{return JSON.parse(localStorage.getItem(key)||'{}')||{};}catch(e){return {};}};
 Promise.all([SG.load('data/manifest.json?v=614812a7ea'),SG.load('data/comparison_index.json.gz?v=7cd4eabfeb')]).then(([m,comparison])=>{
  if(!m||!m.runs)return;
  const all=new Map(m.runs.map(r=>[r.id,r]));for(const r of comparison.runs)all.set(r.id,{...all.get(r.id),...r});
  const runs=[...all.values()],selected=new Set(SG.visibleRuns(runs).map(r=>r.id));
  if(SG.hash().runs!=null)for(const a of links)a.href+='#runs='+encodeURIComponent(SG.hash().runs);
  const d=document.createElement('details');d.className='runs';const s=document.createElement('summary');s.textContent='Runs';s.title='Choose the runs shown on every page';d.appendChild(s);
  const box=document.createElement('div');box.className='runs-menu';
  const search=document.createElement('input');search.type='search';search.placeholder='Find a method';search.setAttribute('aria-label','Find a run');box.appendChild(search);
  const list=document.createElement('div');list.className='run-options';box.appendChild(list);const inputs=[];
  for(const run of runs){
   const on=selected.has(run.id);
   const l=document.createElement('label');l.style.setProperty('--c',`var(--run-${run.id}, ${run.color})`);
   const c=document.createElement('input');c.type='checkbox';c.checked=on;
   const t=document.createElement('span');t.textContent=run.label+(run.detail_available===false?' (summary only)':run.stats_only?' (statistics only)':'');
   l.append(c,t);list.appendChild(l);inputs.push({run,c,l});
  }
  search.addEventListener('input',()=>inputs.forEach(x=>{x.l.hidden=!x.run.label.toLowerCase().includes(search.value.toLowerCase());}));
  const actions=document.createElement('div');actions.className='row';
  const reset=document.createElement('button');reset.type='button';reset.textContent='Defaults';reset.onclick=()=>inputs.forEach(x=>{x.c.checked=!x.run.hidden;});
  const none=document.createElement('button');none.type='button';none.textContent='Clear';none.onclick=()=>inputs.forEach(x=>{x.c.checked=false;});
  const apply=document.createElement('button');apply.type='button';apply.textContent='Apply selection';apply.onclick=()=>{
   const chosen=inputs.filter(x=>x.c.checked);if(!chosen.length){apply.textContent='Choose at least one';return;}
   const w=vis();for(const x of inputs)w[x.run.id]=x.c.checked;try{localStorage.setItem(key,JSON.stringify(w));}catch(e){}
   SG.setHash({...SG.hash(),runs:chosen.map(x=>x.run.id).join(',')});location.reload();
  };
  actions.append(reset,none,apply);box.appendChild(actions);
  d.appendChild(box);opts.appendChild(d);
  document.addEventListener('click',e=>{if(!d.contains(e.target))d.removeAttribute('open');});
 }).catch(()=>{});
})();
