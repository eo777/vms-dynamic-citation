// Replay only permutation identities, without the measurement or outcome kernels.
'use strict';
const fs=require('fs');
const [input,output,kind,barg]=process.argv.slice(2),d=JSON.parse(fs.readFileSync(input,'utf8')),B=Number(barg);
const groups=kind==='line'?d.lineGroups:d.groups,original=d.wordIds,ids=Int32Array.from(original),saved=[];
let state=(kind==='line'?742028:642028)>>>0;
function random(){state=(state+0x6D2B79F5)>>>0;let t=state;t=Math.imul(t^(t>>>15),t|1);t^=t+Math.imul(t^(t>>>7),t|61);return ((t^(t>>>14))>>>0)/4294967296;}
for(let b=1;b<=B;b++){
 ids.set(original);
 for(const g of groups)for(let j=g.length-1;j>0;j--){const k=Math.floor(random()*(j+1)),a=g[j],c=g[k],tmp=ids[a];ids[a]=ids[c];ids[c]=tmp;}
 if(b===1||b===B)saved.push({draw:b,ids:Array.from(ids)});
}
fs.writeFileSync(output,JSON.stringify(saved));
