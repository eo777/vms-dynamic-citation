"use strict";
// The Step log of the page browser: one word's trace records (S source draw, P proposal, A written) grouped into
// attempts. An attempt is the draws that lead to one proposal. Pure functions, no DOM (test/steplog.test.js).
// firstPos: the run's token position of each text line's first word (text.json first_pos).
const SG_STEPLOG=(()=>{
 // [{ks: record indices, p: index of the proposal or null}]; written records (A) stay outside the attempts
 function attempts(ev){
  const out=[];let cur=[];
  ev.forEach((e,k)=>{if(e.t==='A')return;cur.push(k);if(e.t==='P'){out.push({ks:cur,p:k});cur=[];}});
  if(cur.length)out.push({ks:cur,p:null});
  return out;
 }
 // far draws: the token position of the picked word's last use (build_data.py writes the position; data built before
 // its far-pick fix carry [position + 1, buffer index])
 const farPos=S=>Array.isArray(S.pick)?S.pick[0]-1:S.pick;
 // the token position a draw picked: window draws name (line, word); a draw on an empty page has none
 const pickPos=(S,firstPos)=>S.mode==='empty'?null:S.far?farPos(S):firstPos[S.pick[0]]+S.pick[1];
 // a page-window proposal whose source is not its draw's pick: after more than a hundred draws at one position Timm's
 // generator takes a forced suggestion, while the chooser mode still reads page window
 function forced(ev,k,firstPos){
  const p=ev[k],s=ev[k-1];
  return p.mode==='LOCALY'&&!!s&&s.t==='S'&&s.mode!=='empty'&&pickPos(s,firstPos)!==p.srcpos;
 }
 // Timm discards a draw (a long word, the same source twice, a combined word) when another draw follows it, or a
 // proposal whose source came from another chooser mode or was forced: only page-window draws pass the governor
 function skipped(ev,k,firstPos){
  const n=ev[k+1];
  return !!n&&(n.t==='S'||(n.t==='P'&&(n.mode!=='LOCALY'||forced(ev,k+1,firstPos))));
 }
 function written(ev,p){return ev.some(x=>x.t==='A'&&x.id>=0&&Math.floor(x.id/100)===p.id);}
 // outcome of a proposal: A accepted, C unchanged copy, T Timm's run (no governor), R rejected and drawn again,
 // K copy kept after the last retry, N innovated, X refused by Timm's checks, G sent back by the repeat guard
 function outcome(ev,p){
  if(p.rep)return 'G';
  if(p.dec==='R')return 'R';
  if(!written(ev,p))return 'X';
  if(p.dec==='N'||p.dec==='K'||p.dec==='T')return p.dec;
  return p.changed?'A':'C';
 }
 // the word a proposal writes at part k: the kept copy, the innovated word or the proposal itself; a written word that
 // differs from it was fitted to the line by Timm's trim (written as SHORTEN)
 function intended(p,k){return p.dec==='K'?p.src:p.dec==='N'?p.inn.word:(p.props[k]||p.props[0])[0];}
 // which attempts are drawn in full: all of up to eight; beyond that the first, the last three and the one holding the
 // current record, with the rest folded into [first, last] ranges
 function layout(n,cur,open){
  const show=new Set(open||n<=8?[...Array(n).keys()]:[0,n-3,n-2,n-1]);
  if(cur!=null&&cur>=0)show.add(cur);
  const out=[];
  for(let i=0;i<n;i++){
   if(show.has(i)){out.push({i});continue;}
   const last=out[out.length-1];if(last&&last.fold)last.fold[1]=i;else out.push({fold:[i,i]});
  }
  return out;
 }
 // the rows of one attempt: three or more skipped draws in a row fold into one row; a fold holding the current record
 // splits around it
 function rows(ev,ks,curK,open,firstPos){
  const out=[];let run=[];
  const part=r=>{if(r.length>1)out.push({skip:r});else r.forEach(k=>out.push({k}));};
  const flush=()=>{
   const i=run.indexOf(curK);
   if(open||run.length<3)run.forEach(k=>out.push({k}));
   else if(i<0)out.push({skip:run});
   else{part(run.slice(0,i));out.push({k:curK});part(run.slice(i+1));}
   run=[];
  };
  for(const k of ks){if(ev[k].t==='S'&&skipped(ev,k,firstPos))run.push(k);else{flush();out.push({k});}}
  flush();
  return out;
 }
 return {attempts,farPos,pickPos,forced,skipped,written,outcome,intended,layout,rows};
})();
