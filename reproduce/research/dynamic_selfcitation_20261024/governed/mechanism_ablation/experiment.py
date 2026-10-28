"""Controlled reserve / proposal / constraint / feedback experiments.

Peak disk: four temporary Java/Python runs and one compiler, <250 MB outside
the workspace. Retain compact metrics and gzip scored text (<100 KB/stream)
so future scalar statistics do not require generation. No decision/page logs,
model arrays, or complete bigram dictionaries. See RESULTS.md for the design.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor,as_completed
from functools import lru_cache
import gzip
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import time

HERE=Path(__file__).resolve().parent;GOV=HERE.parent;ROOT=GOV.parents[2]
sys.path.insert(0,str(ROOT/'apps/selfcitation_governor'))
import comparison_metrics as cm
import comparison_runs as cr
import numpy as np
e=cm.entropy.exp.e
carry=cm.entropy.exp.carry

@lru_cache(maxsize=100000)
def parts(word):return tuple(u.text for u in e.units(word,'zattera'))

@lru_cache(maxsize=100000)
def edges(word):
    u=('^',)+parts(word)+('$',)
    return tuple(zip(u,u[1:]))


def config(**kw):
    return dict(dict(policy='spread',repair=True,token_sample=True,edit=0,
        kernel='wide',alphabet='stable',legality='learned',firing='fixed',rate=.35,
        unseen=False,repel=True,native=True,rarity=True),**kw)


CONDITIONS={
 'editor_visible':config(kernel='editor',alphabet='visible',legality='native'),
 'editor_visible_uniform':config(kernel='editor',alphabet='visible_uniform',legality='native'),
 'editor_stable':config(kernel='editor',legality='native'),
 'editor_visible_filter':config(kernel='editor',alphabet='visible'),
 'editor_stable_filter':config(kernel='editor'),
 'editor_local_pages':config(kernel='editor',alphabet='visible_uniform',legality='page',repel=False,rarity=False),
 'editor_local_sheet':config(policy='sheet',kernel='editor',alphabet='visible_uniform',legality='page',repel=False,rarity=False),
 'wide_native':config(legality='native'),
 'wide_fixed':config(),
 'wide_visible':config(alphabet='visible'),
 'wide_unseen':config(unseen=True),
 'wide_feedback':config(unseen=True,firing='deficit'),
 'wide_slow':config(rate=.10),
 'wide_fast':config(rate=.70),
 'wide_no_repel':config(repel=False),
 'wide_no_timm':config(native=False),
 'wide_no_rarity':config(rarity=False),
 'wide_local':config(rarity=False,legality='local'),
 'wide_local_no_repel':config(rarity=False,legality='local',repel=False),
 'wide_local_copy':config(rarity=False,legality='local',native=False),
 'wide_page_grammar':config(rarity=False,legality='page'),
 'wide_page_no_repel':config(rarity=False,legality='page',repel=False),
 'wide_page_copy':config(rarity=False,legality='page',native=False),
 'wide_pattern_memory':config(rarity=False,legality='memory',repel=False),
 'sheet_fixed':config(policy='sheet'),
 'sheet_feedback':config(policy='sheet',unseen=True,firing='deficit'),
 'sheet_editor':config(policy='sheet',kernel='editor'),
 'sheet_local':config(policy='sheet',rarity=False,legality='local'),
 'sheet_local_no_repel':config(policy='sheet',rarity=False,legality='local',repel=False),
 'sheet_local_copy':config(policy='sheet',rarity=False,legality='local',native=False),
 'sheet_page_grammar':config(policy='sheet',rarity=False,legality='page'),
 'sheet_page_no_repel':config(policy='sheet',rarity=False,legality='page',repel=False),
 'sheet_pattern_memory':config(policy='sheet',rarity=False,legality='memory',repel=False),
 'page_fixed':config(policy='page'),
}


def build(folder):
    classes,mapping=carry.build(folder)
    path=Path(folder)/'build/source/de/voynich/text/SelfCitationTextGenerator.java';s=path.read_text()
    old='List<GlyphGroup> morphedGroups = Bridge.operations ? Bridge.morphAll(config.groupMorpher, sourceGroups, lastGeneratedGroup, isParagraphInitial, isLineInitial) : config.groupMorpher.morphGroup(sourceGroups, lastGeneratedGroup, isParagraphInitial, isLineInitial);'
    assert s.count(old)==1
    s=s.replace(old,old+'\n                if(Boolean.getBoolean("bridge.copyOnly")){morphedGroups=new java.util.ArrayList<GlyphGroup>();morphedGroups.add(new GlyphGroup(sourceGroups.get(0).glyphGroup,GlyphGroup.GENERATE_TYPE.REPLACE));}')
    path.write_text(s)
    ecj=ROOT/'solve/botanical_enrichment/echo7/copying_trace_20261014/generator/ecj.jar'
    p=subprocess.run(['java','-jar',str(ecj),'-1.8','-encoding','UTF-8','-nowarn','-d',classes]+[str(p) for p in (Path(folder)/'build/source').rglob('*.java')],capture_output=True,text=True)
    assert p.returncode==0,p.stdout+p.stderr
    return classes,mapping


def install(spec):
    e.install_variant(spec);base=e.governor.Governor;cfg=spec['variant']
    class AblationGovernor(base):
        def __init__(self,*a,**kw):
            super().__init__(*a,**kw);self.custom_audit=Counter();self.snapshots=[];self.learned_edges=set()
        def refresh_recent(self):
            if cfg['repel']:return super().refresh_recent()
            self.recent=Counter()
        def native_valid(self,words):
            if not words:return []
            self.proc.stdin.write('?V\t'+'\t'.join(words)+'\n');self.proc.stdin.flush()
            reply=self.proc.stdout.readline().strip().split('\t');assert reply[0]=='!V'
            return [w for w,v in zip(words,reply[1:]) if v=='1']
        def candidates(self,raw,name,avail,s):
            seq=list(parts(raw))
            if not 2<=len(seq)<=9:return []
            alpha=self.m.alphabet if cfg['alphabet']=='stable' else sorted({u for w in self.visible for u in parts(w)})
            if not alpha:return []
            if cfg['kernel']=='editor':
                cand=[]
                for _ in range(3):
                    donor=self.visible[int(self.rng.integers(len(self.visible)))];ds=list(parts(donor))
                    if not ds:continue
                    op=int(self.rng.integers(5));p=int(self.rng.integers(len(seq)));q=int(self.rng.integers(len(ds)))
                    x=ds[q] if cfg['alphabet']=='visible' else alpha[int(self.rng.integers(len(alpha)))]
                    if op==0:
                        n=int(self.rng.integers(1,min(3,len(seq))+1));m=int(self.rng.integers(1,min(3,len(ds))+1));new=seq[:-n]+ds[-m:]
                    elif op==1:
                        n=int(self.rng.integers(1,min(3,len(seq))+1));m=int(self.rng.integers(1,min(3,len(ds))+1));new=ds[:m]+seq[n:]
                    elif op==2:new=seq[:p]+[x]+seq[p:]
                    elif op==3:new=seq[:p]+[x]+seq[p+1:]
                    else:new=seq[:p]+seq[p+1:]
                    if len(new)<=10:cand.append(''.join(new))
            else:
                draw=self.rng.random();pc=self.slot_join[name]*.8
                if draw<pc:
                    recent=list(dict.fromkeys(w for w in self.emitted[-3:] if e.strip(w) in self.visible))
                    if self.rng.random()<.35:
                        # Only visible one-unit words: no full-stream seen-list
                        # consultation in a blind fixed-rate condition.
                        ones=[w for w in self.visible if len(parts(w))==1]+['qo']
                        cand=[x+raw for x in ones]+[raw+x for x in ones if x!='qo']
                    else:cand=[raw+w for w in recent]+[w+raw for w in recent]
                    cand=[w for w in cand if len(parts(w))<=10]
                elif draw<pc+.15:cand=[raw+x+y for x in alpha for y in alpha]+[x+y+raw for x in alpha for y in alpha]
                else:
                    cand=[''.join(seq[:i]+[x]+seq[i:]) for i in range(len(seq)+1) for x in alpha]
                    cand+=[''.join(seq[:i]+seq[i+1:]) for i in range(len(seq))]
                    cand+=[''.join(seq[:i]+[x]+seq[i+1:]) for i in range(len(seq)) for x in alpha if x!=seq[i]]
            cand=sorted(set(w for w in cand if w and w!=raw and len(w)<=avail))
            self.custom_audit['candidates']+=len(cand)
            if cfg['unseen']:cand=[w for w in cand if w not in self.seen]
            # Only the wide kernel uses the innovator's register/rarity rules;
            # these stay fixed in its native-vs-learned transition comparison.
            if cfg['kernel']=='wide':
                gallows=name in ('page-first','paragraph-first') and self.rng.random()<.84
                starts='pf' if gallows and self.rng.random()<.59 else 'ktpf'
                cand=[w for w in cand if (not gallows or w[0] in starts) and
                    (gallows or name in ('page-first','paragraph-first','paragraph-line') or w[0] not in 'pf') and
                    (not cfg.get('rarity',True) or w not in self.m.logq or self.m.logq[w]<=self.a.prior_max)]
            if cfg['legality']=='learned':cand=[w for w in cand if self.m.legality(w,s)>=self.a.legality_min]
            if cfg['legality'] in ('local','page','memory'):
                allowed=set()
                # The original local pilot learned from stripped donor forms.
                # Full-page grammar sees actual written forms, including
                # paragraph-initial gallows, using only permitted positions.
                donors=self.visible if cfg['legality']=='local' else {self.emitted[i] for i in self.allowed_positions}
                for donor in donors:allowed.update(edges(donor))
                if cfg['legality']=='memory':
                    self.learned_edges.update(allowed);allowed=self.learned_edges
                    self.custom_audit['remembered_transitions']=len(allowed)
                cand=[w for w in cand if all(edge in allowed for edge in edges(w))]
            self.custom_audit['after_constraints']+=len(cand)
            cand=self.native_valid(cand)
            self.custom_audit['after_native_grammar']+=len(cand)
            return cand
        def propose(self,fields):
            pos=int(fields[2]);name,rest=self.slot(fields,pos)
            if len(rest)!=1 or not self.visible:return super().propose(fields)
            raw=rest[0].rsplit(':',1)[0]
            if not 2<=len(parts(raw))<=9:return super().propose(fields)
            s=self.m.node(pos);self.custom_audit['eligible']+=1
            if cfg['firing']=='deficit':
                target=self.target(name,s);realised=self.slot_ema.get(name,target)
                p=min(1.,max(0.,4*(target-realised)))
            else:p=cfg['rate']
            if self.rng.random()>=p:return super().propose(fields)
            self.custom_audit['attempts']+=1
            cand=self.candidates(raw,name,self.avail_of.get(pos,99),s)
            if cand:
                self.refresh_recent();pi=self.pressure(s)
                options=([raw]+cand) if cfg['kernel']=='editor' else cand
                scores=np.array([.5*self.preference(w,s,pi)-math.log1p(2*self.recent[w]) for w in options]);scores-=scores.max()
                prob=np.exp(scores);prob/=prob.sum();word=options[int(self.rng.choice(len(options),p=prob))]
                fields=fields.copy();fields[8]=word+':REPLACE'
                self.custom_audit['selected_changes']+=int(word!=raw)
            return super().propose(fields)
        def accept(self,fields):
            super().accept(fields);install.last=self
            if len(self.emitted) in self.m.cumulative:
                self.snapshots.append(dict(tokens=len(self.emitted),audit=dict(self.custom_audit)))
    e.governor.Governor=AblationGovernor
    popen=e.governor.subprocess.Popen
    def launch(command,*args,**kw):
        command=list(command);command.insert(1,'-Dbridge.sheetmap='+spec['sheetmap'])
        if not cfg['native']:command.insert(1,'-Dbridge.copyOnly=true')
        return popen(command,*args,**kw)
    e.governor.subprocess.Popen=launch


def child(path):
    original=e.install_variant
    # e.child delegates to its installer; avoid recursive reassignment.
    def dispatch(spec):
        e.install_variant=original
        install(spec)
    e.install_variant=dispatch
    e.child(path)
    spec=cr.read(Path(path));g=install.last
    (Path(spec['args']['out'])/'mechanism_audit.json').write_text(json.dumps(dict(totals=g.custom_audit,intervals=g.snapshots)))


def run(name,seed,classes,mapping,sc):
    cfg=CONDITIONS[name];args=cr.read(GOV/'runs/n_noinnov_far0/run.json')['args']
    args.update(seed=seed,lines=5000,trace=False,innovate=False,novelty_curve=cfg['firing']=='deficit')
    key='ab_'+name+'_s'+str(seed);dest=HERE/'streams';dest.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='voynich_ablation_run_') as td:
        p=Path(td);out=p/'run';args['out']=str(out)
        spec=dict(condition=name,variant=cfg,args=args,classes=classes,sheetmap=mapping)
        (p/'spec.json').write_text(json.dumps(spec))
        with (p/'log.txt').open('w',encoding='utf-8') as log:
            proc=subprocess.run([sys.executable,'-B',str(Path(__file__)),'--child',str(p/'spec.json')],stdout=log,stderr=subprocess.STDOUT,timeout=1800)
        if proc.returncode:
            return dict(condition=name,seed=seed,variant=cfg,status='failed',error=(p/'log.txt').read_text()[-1200:])
        meta=cr.read(out/'run.json');st=cm.generated_stream(out,meta)
        pack=sc.score(st,key,excerpts=False,details=False)
        pack.update(seed=seed,text_sha256=meta['text_sha256'],runtime_stats=meta['stats'],source='mechanism_ablation/streams/'+key+'.json.gz')
        cm.b.dump(pack,cm.APP/'data/comparison_runs'/f'{key}.json.gz')
        lines=cm.joined_lines(st)
        cache=dict(lines=[ws for _,ws in lines],page_first=st.page_first[:len(lines)],par_first=st.par_first[:len(lines)],tokens=cm.b.T,
            complete_text_sha256=meta['text_sha256'],seed=seed)
        cm.b.dump(cache,dest/f'{key}.json.gz')
        args['out']='<temporary>'
        return dict(condition=name,seed=seed,key=key,variant=cfg,args=args,status='complete',seconds=meta['seconds'],
            text_sha256=meta['text_sha256'],tokens=cm.b.T,whole=pack['whole'],audit=cr.read(out/'mechanism_audit.json'))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--child');ap.add_argument('--only',nargs='+',default=list(CONDITIONS));ap.add_argument('--seeds',nargs='+',type=int,default=[1]);ap.add_argument('--workers',type=int,default=4);ap.add_argument('--output',default='results.json.gz');a=ap.parse_args()
    if a.child:return child(a.child)
    output=HERE/a.output;rows=cr.read(output) if output.exists() else []
    initial=HERE/'initial_results.json.gz'
    if a.output=='results.json.gz' and initial.exists():rows=list({(r['condition'],r['seed']):r for r in cr.read(initial)+rows}.values())
    done={(r['condition'],r['seed']) for r in rows if r['status']=='complete'}
    sc=cm.Scorer();print('Scorer ready',flush=True)
    with tempfile.TemporaryDirectory(prefix='voynich_ablation_build_') as td:
        classes,mapping=build(td);print('Runtime ready',flush=True)
        with ThreadPoolExecutor(max_workers=a.workers) as pool:
            jobs=[pool.submit(run,n,s,classes,mapping,sc) for n in a.only for s in a.seeds if (n,s) not in done]
            for f in as_completed(jobs):
                r=f.result();rows=[x for x in rows if (x['condition'],x['seed'])!=(r['condition'],r['seed'])]+[r]
                cm.b.dump(rows,output)
                print(r['condition'],r['seed'],r['status'],'seconds',round(r.get('seconds',0)),flush=True)
    sources=[Path(__file__),Path(cm.__file__),cm.APP/'word_entropy.py',GOV/'governor.py',GOV/'human_design/experiments.py',GOV/'human_design/HumanSupply.java',GOV/'sheet_morph/SheetSupply.java',GOV/'sheet_morph/carry.py']
    cm.b.dump({str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},HERE/'source_hashes.json')


if __name__=='__main__':main()
