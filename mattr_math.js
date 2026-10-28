/* Pure replay arithmetic. The scoring window never changes the generator. */
"use strict";
const SG_MATTR=(()=>{
 function normalize(w){return w.length>1&&'ktpf'.includes(w[0])?w.slice(1):w;}
 function upperBound(a,x){let lo=0,hi=a.length;while(lo<hi){let m=(lo+hi)>>1;if(a[m]<=x)lo=m+1;else hi=m;}return lo;}
 function flatten(text){const lines=text.lines,words=lines.flat(),first=[],lineOf=new Uint32Array(words.length);let at=0;lines.forEach((l,i)=>{first.push(at);lineOf.fill(i,at,at+l.length);at+=l.length;});return {words,first,lineOf};}
 function rolling(words,width){
  const counts=new Map(),distinct=new Uint16Array(words.length),score=new Float64Array(words.length),smooth=new Float64Array(words.length),prefix=new Float64Array(words.length+1),redShare=new Float64Array(words.length);
  let sum=0,n=0,singletons=0;
  for(let i=0;i<words.length;i++){
   if(i>=width){const w=words[i-width],old=counts.get(w),c=old-1;if(old===1)singletons--;else if(old===2)singletons++;if(c)counts.set(w,c);else counts.delete(w);}
   const old=counts.get(words[i])||0;if(old===0)singletons++;else if(old===1)singletons--;
   counts.set(words[i],old+1);distinct[i]=counts.size;
   // Every occurrence of a repeated spelling is red, including its first occurrence.
   redShare[i]=i+1<width?NaN:(width-singletons)/width;
   score[i]=i+1<width?NaN:counts.size/width;
   prefix[i+1]=prefix[i]+(Number.isFinite(score[i])?score[i]:0);
   if(Number.isFinite(score[i])){sum+=score[i];n++;}
   if(i-200>=width-1){sum-=score[i-200];n--;}
   smooth[i]=n?sum/n:NaN;
  }
  return {distinct,score,smooth,prefix,redShare,width};
 }
 function step(words,pos,width){
  const start=Math.max(0,pos-width+1),before=words.slice(Math.max(0,pos-width),pos),remaining=words.slice(start,pos),after=[...remaining,words[pos]],counts=new Map();
  for(const w of after)counts.set(w,(counts.get(w)||0)+1);
  const oldUnique=new Set(before).size,unique=counts.size,leaving=pos>=width?words[pos-width]:null;
  return {start,end:pos+1,words:after,counts,unique,size:after.length,repeated:after.length-unique,
   entering:words[pos],enteringRepeat:remaining.includes(words[pos]),leaving,
   leavingLast:leaving!==null&&!remaining.includes(leaving),delta:unique-oldUnique,
   score:after.length===width?unique/width:null};
 }
 function meanInScope(series,pos,start){const first=start+series.width-1;return pos<first?null:(series.prefix[pos+1]-series.prefix[first])/(pos-first+1);}
 function pool(text,line,count,archiveCount){
  const local=[];for(let i=line-count;i<line;i++)if(i>0)local.push(i);
  const archive=[];for(let i=1;i<line&&archive.length<archiveCount;i++)if(text.par[i])archive.push(i);
  return {local,archive};
 }
 function poolStats(text,indices){const counts=new Map();let tokens=0;for(const i of indices)for(const raw of text.lines[i]){const w=normalize(raw);counts.set(w,(counts.get(w)||0)+1);tokens++;}return {tokens,forms:counts.size,counts};}
 // Align token centers within the same physical line, without pretending words correspond.
 function alignedPosition(from,to,pos){const l=from.lineOf[pos],a=from.first[l],b=from.first[l+1]??from.words.length,
  c=to.first[l],d=to.first[l+1]??to.words.length;return c+(pos-a+.5)/(b-a)*(d-c)-.5;}
 function alignToken(from,to,pos){const l=from.lineOf[pos];return Math.max(to.first[l],Math.min((to.first[l+1]??to.words.length)-1,Math.round(alignedPosition(from,to,pos))));}
 // Merge overlapping lookback intervals where the smoothed series loses at least threshold.
 function declines(values,start,end,lag=100,threshold=.05){
  const spans=[];for(let i=start+lag;i<end;i++)if(Number.isFinite(values[i-lag])&&Number.isFinite(values[i])&&values[i-lag]-values[i]>=threshold-1e-12){
   const loss=values[i-lag]-values[i],last=spans.at(-1);
   if(last&&i-lag<=last.end){last.end=i;if(loss>last.loss){last.loss=loss;last.trough=i;}}
   else spans.push({start:i-lag,end:i,loss,trough:i});
  }return spans;
 }
 return {normalize,upperBound,flatten,rolling,step,meanInScope,pool,poolStats,alignedPosition,alignToken,declines};
})();
if(typeof module!=='undefined')module.exports=SG_MATTR;
