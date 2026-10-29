'use strict';
const fs=require('fs'),path=require('path'),S=require(path.join(__dirname,'source_snapshot','component_source_math.js'));
const d=JSON.parse(fs.readFileSync(process.argv[2],'utf8')),c=S.prepare(d),N=d.words.length;
function pool(pos,name){
 const original=c.centers[pos];if(!original)return {indices:[],weights:[],available:0};
 const t=name==='cursor'?{...original,x:d.geometry[pos][0]}:original;
 const up=name!=='below',left=name==='full'||name==='cursor'?3:0;
 const line=c.lineOf[pos],page=c.pages.get(d.lines[line].page),cand=[];
 for(const i of page.indices){
  if(up){if(i>=pos)break;}else if(i<=pos)continue;
  const b=c.centers[i];if(!b)continue;let distance,alignment=1;
  if(c.lineOf[i]===line){const dx=b.x-t.x;if(!left||dx>=0||-dx>left*page.wordWidth)continue;distance=-dx/page.wordWidth;}
  else{
   const box=d.geometry[i],dy=up?t.y-b.y:b.y-t.y;
   const near=up?Math.max(0,t.y-box[3]):Math.max(0,box[1]-t.y);
   const far=up?Math.min(8*page.pitch,t.y-box[1]):Math.min(8*page.pitch,box[3]-t.y);
   const horizontal=Math.max(box[0]-t.x,t.x-box[2],0);
   if(dy<=0||far<=0||near>far||horizontal>far*Math.tan(Math.PI/4)+1e-8)continue;
   const dx=b.x-t.x;distance=Math.hypot(dx,dy)/page.pitch;alignment=dy*dy/(dx*dx+dy*dy);
  }
  cand.push({i,distance,w:alignment/(1+distance)**2});
 }
 cand.sort((a,b)=>b.w-a.w||a.distance-b.distance||(up?b.i-a.i:a.i-b.i));
 const chosen=cand.slice(0,100).sort((a,b)=>a.i-b.i);
 return {indices:chosen.map(x=>x.i),weights:chosen.map(x=>x.w),available:cand.length};
}
const names=['full','above','below',...(d.cursor?['cursor']:[])],pools={},references={};
let maxFullWeightError=0;
for(const name of names){
 pools[name]=[];references[name]={components:[],h2:[],worddiv:[]};
 for(let i=0;i<N;i++){
  const p=pool(i,name);pools[name].push([p.indices,p.weights]);
  const m=S.measure(c,p);for(const metric of Object.keys(references[name]))references[name][metric].push(Number.isFinite(m[metric])?m[metric]:null);
  if(name==='full'){
   const q=S.sourcePool(c,i,100,{left:3,depth:8,angle:45,weight:'distance'});
   if(JSON.stringify(q.indices)!==JSON.stringify(p.indices))throw Error('Full pool membership mismatch '+i);
   for(let j=0;j<p.weights.length;j++)maxFullWeightError=Math.max(maxFullWeightError,Math.abs(q.weights[j]-p.weights[j]));
  }
 }
}
if(maxFullWeightError>1e-12)throw Error('Pool weights mismatch');
const words=[...new Set(d.words)],ids=new Map(words.map((w,i)=>[w,i])),feats=new Map(d.words.map((w,i)=>[w,c.tokenFeatures[i].pairs]));
const result={words,wordIds:d.words.map(w=>ids.get(w)),features:words.map(w=>feats.get(w)),pairLeft:c.pairLeft,unitCount:c.unitNames.length,pools,references,pool_validation:{full_memberships_checked:N,max_weight_error:maxFullWeightError}};
fs.writeFileSync(process.argv[3],JSON.stringify(result));
