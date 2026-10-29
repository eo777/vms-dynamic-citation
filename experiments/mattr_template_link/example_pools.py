"""The two qokeedy examples of the summary page (f75r, A and B), with their source pools taken apart (28 October, user's
observation that the low diversity of B comes from the words above, not from the words to its left).

For each example target the study selector's pool is listed word by word with its weight and its line offset, and component
diversity, H2 and word diversity are recomputed for the full pool, for the same-line words alone and for the words of the
lines above alone (the study's own measure on each sub-pool). Run from anywhere: python example_pools.py > example_pools.log
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import data as D  # noqa: E402
import component_check as CC  # noqa: E402

JS = r"""
'use strict';
const fs=require('fs'), path=require('path');
const S=require(process.argv[4]);
const d=JSON.parse(fs.readFileSync(process.argv[2],'utf8')); const c=S.prepare(d);
const opt={left:3,depth:8,angle:45,weight:'distance'};
const out={};
for(const pos of d.targets){
  const p=S.sourcePool(c,pos,100,opt); const line=c.lineOf[pos];
  const rows=p.indices.map((i,k)=>({i,word:d.words[i],w:p.weights[k],dline:line-c.lineOf[i],same:c.lineOf[i]===line}));
  const sub=(keep)=>{const idx=[],wt=[];rows.forEach(r=>{if(keep(r)){idx.push(r.i);wt.push(r.w);}});
    const m=S.measure(c,{indices:idx,weights:wt,available:idx.length,full:true}); return {n:idx.length,components:m.components,h2:m.h2,worddiv:m.worddiv,weight:wt.reduce((a,b)=>a+b,0)};};
  out[pos]={word:d.words[pos],line:line,rows,full:sub(()=>true),same:sub(r=>r.same),above:sub(r=>!r.same)};
}
fs.writeFileSync(process.argv[3],JSON.stringify(out));
"""


def main():
    ms = D.manuscript()
    app = CC.load_study_app('legacy')
    ex = json.load(open(HERE / 'summary_figures' / 'component_examples.json', encoding='utf-8'))
    targets = [e['target'] for e in ex['examples']]
    inp = CC.make_input(ms, [L['words'] for L in ms['lines']], app['geometry'], CC.zattera)
    inp['targets'] = targets
    with tempfile.TemporaryDirectory() as td:
        js = Path(td) / 'ex.js'
        js.write_text(JS, encoding='utf-8')
        a, b = Path(td) / 'in.json', Path(td) / 'out.json'
        a.write_text(json.dumps(inp), encoding='utf-8')
        r = subprocess.run(['node', str(js), str(a), str(b), str(HERE / 'component_source_math.js')], capture_output=True, text=True)
        if r.returncode:
            raise SystemExit(r.stderr)
        out = json.loads(b.read_text(encoding='utf-8'))
    labels = ['A', 'B']
    for lab, e in zip(labels, ex['examples']):
        o = out[str(e['target'])]
        tot = o['full']['weight']
        print(f"\n== example {lab}: token {e['target']} '{o['word']}', f75r line {e['locus']}; page figure gives components {e['score']['components']:.1f}")
        for part, name in (('full', 'full pool'), ('same', 'same-line words only'), ('above', 'lines above only')):
            s = o[part]
            comp = 'n/a' if s['components'] is None else f"{s['components']:.1f}"
            h2 = 'n/a' if s['h2'] is None else f"{s['h2']:.2f}"
            print(f"   {name:22s} n={s['n']:2d}  weight share {s['weight'] / tot:5.1%}  components {comp:>5s}  H2 {h2:>5s}  word diversity {s['worddiv']:.2f}")
        print(f"   {'pool words (weight, line offset)':s}:")
        rows = sorted(o['rows'], key=lambda r: -r['w'])
        print('   ' + ', '.join(f"{r['word']} ({r['w'] / tot:.0%}, {'same line' if r['same'] else str(r['dline']) + ' up'})" for r in rows))


if __name__ == '__main__':
    main()
