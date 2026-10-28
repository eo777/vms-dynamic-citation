/* Display-only page layers. Never alter the geometry used by source-pool scores. */
"use strict";
const SG_HEATMAP_PAGE=(()=>{
 const NS='http://www.w3.org/2000/svg';
 function create({atlas,onChange}){
  const controls=document.getElementById('pageDisplayControls'),imageToggle=document.getElementById('pageImage'),
   labelToggle=document.getElementById('pageWords'),boxStyle=document.getElementById('pageBoxes'),status=document.getElementById('pageImageStatus');
  let data=null,expanded=null,reviewPromise=null,ticket=0;
  const states=new WeakMap();
  function state(figure){
   if(!states.has(figure)){
    const svg=figure.querySelector('svg');
    states.set(figure,{svg,viewBox:svg.getAttribute('viewBox'),native:null,
     boxes:[...svg.querySelectorAll('rect')].map(box=>({box,raw:['x','y','width','height'].map(a=>Number(box.getAttribute(a)))}))});
   }
   return states.get(figure);
  }
  function raw(figure){
   const s=state(figure);s.svg.setAttribute('viewBox',s.viewBox);
   for(const {box,raw} of s.boxes){['x','y','width','height'].forEach((a,k)=>box.setAttribute(a,raw[k]));box.classList.remove('no-native-box');}
   s.svg.querySelector('.manuscript-image')?.remove();s.native=null;
   figure.classList.remove('image-backed');
  }
  function labels(){
   if(!expanded||!data)return;
   const s=state(expanded);s.svg.querySelector('.page-word-labels')?.remove();
   expanded.classList.toggle('words-visible',labelToggle.checked);
   if(!labelToggle.checked)return;
   const layer=document.createElementNS(NS,'g');layer.setAttribute('class','page-word-labels');layer.setAttribute('aria-hidden','true');
   const seen=new Set();
   for(const {box} of s.boxes){
    if(!box.dataset.tokenIndices||box.classList.contains('invalid-geometry')||box.classList.contains('no-native-box'))continue;
    const indices=box.dataset.tokenIndices.split(',').map(Number),key=indices.join(',');
    if(seen.has(key))continue;seen.add(key);
    const related=s.boxes.map(entry=>entry.box).filter(b=>b.dataset.tokenIndices===box.dataset.tokenIndices&&!b.classList.contains('no-native-box'));
    const parts=related.map(b=>['x','y','width','height'].map(a=>Number(b.getAttribute(a))));
    // A multi-piece label spans its whole adjacent group, never just piece one.
    const x=Math.min(...parts.map(b=>b[0])),y=Math.min(...parts.map(b=>b[1])),
     w=Math.max(...parts.map(b=>b[0]+b[2]))-x,h=Math.max(...parts.map(b=>b[1]+b[3]))-y,text=document.createElementNS(NS,'text');
    text.textContent=SG_REVIEW.boxLabel(data,indices);text.setAttribute('x',x+1);text.setAttribute('y',y+h*.72);
    text.setAttribute('font-size',Math.min(s.native?12:18,h*.65));text.setAttribute('textLength',Math.max(2,w-2));text.setAttribute('lengthAdjust','spacingAndGlyphs');
    text.classList.toggle('label-member',box.classList.contains('window-member'));layer.append(text);
   }
   s.svg.append(layer);
  }
  async function apply(){
   const current=++ticket;controls.hidden=!expanded;status.hidden=!expanded;
   if(!expanded)return;
   const figure=expanded,s=state(figure);
   figure.dataset.boxStyle=boxStyle.value;raw(figure);labels();onChange();
   status.textContent='Word labels preserve uncertain spaces (commas). Dashed amber boxes have unresolved word positions.';
   if(!imageToggle.checked)return;
   status.textContent='Loading matching Voynichese image coordinates…';
   try{
    if(!reviewPromise)reviewPromise=SG.load('data/spatial_review.json.gz?v=97acca8478').catch(error=>{reviewPromise=null;throw error;});
    const review=await reviewPromise;if(current!==ticket)return;
    const native=SG_REVIEW.nativePage(review,figure.dataset.page);
    if(!native.image||!native.boxes.size){status.textContent='No registered Voynichese image is available for this page.';return;}
    s.native=native;s.svg.setAttribute('viewBox','0 0 636 900');figure.classList.add('image-backed');
    let missing=0;
    for(const {box} of s.boxes){
     const b=box.dataset.nativeBox?box.dataset.nativeBox.split(',').map(Number):box.hasAttribute('data-xml-index')?native.boxes.get(Number(box.dataset.xmlIndex)):null;
     box.classList.toggle('no-native-box',!b);
     if(b){['x','y','width','height'].forEach((a,k)=>box.setAttribute(a,[b[0],b[1],b[2]-b[0],b[3]-b[1]][k]));}else missing++;
    }
    const image=document.createElementNS(NS,'image');image.setAttribute('class','manuscript-image');image.setAttribute('width','636');image.setAttribute('height','900');
    image.setAttribute('aria-hidden','true');image.setAttribute('preserveAspectRatio','none');
    image.addEventListener('load',()=>{if(current===ticket)status.textContent='Voynichese image · matching native word boxes · commas mark uncertain spaces.'+(missing?' '+missing+' unregistered boxes are hidden.':'');});
    image.addEventListener('error',()=>{if(current===ticket)status.textContent='The external image could not load. Turn off Page image to return to the coordinate view.';});
    s.svg.prepend(image);image.setAttribute('href',native.image);labels();onChange();
   }catch(error){if(current===ticket)status.textContent='Could not load the image registration. Turn Page image off and on to retry.';}
  }
  for(const control of [imageToggle,labelToggle,boxStyle])control.addEventListener('change',()=>{
   if(control===imageToggle)apply();else{if(expanded)expanded.dataset.boxStyle=boxStyle.value;labels();onChange();}
  });
  return {
   expand(figure){if(expanded&&expanded!==figure){raw(expanded);expanded.removeAttribute('data-box-style');expanded.classList.remove('words-visible');state(expanded).svg.querySelector('.page-word-labels')?.remove();}expanded=figure;apply();},
   setData(value){data=value;imageToggle.disabled=!data.spatialReview;if(imageToggle.disabled&&imageToggle.checked){imageToggle.checked=false;apply();}else labels();},labels,
   readHash(h){imageToggle.checked=h.image==='1';labelToggle.checked=h.words==='1';boxStyle.value=['fill','outline','hidden'].includes(h.boxes)?h.boxes:'fill';},
   hash(){return {image:imageToggle.checked?'1':undefined,words:labelToggle.checked?'1':undefined,boxes:boxStyle.value==='fill'?undefined:boxStyle.value};},
   guide(box,point){const s=states.get(box.closest('figure'));if(!s?.native)return {...point,scale:1};
    const r=s.native.registration;if(!r||r.maxCenterError>=2)return null;
    return {x:Number(box.getAttribute('x'))+Number(box.getAttribute('width'))/2,y:Number(box.getAttribute('y'))+Number(box.getAttribute('height'))/2,scale:r.scale};}
  };
 }
 return {create};
})();
