"""Bounded local copying/editing experiments; no production code changes.

Peak disk plan: isolated compiler and two full runs in temporary storage, <60 MB.
Retain compact JSON, source, and short examples only; delete texts/logs/classes
with TemporaryDirectory after verification. No new model or prediction arrays.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import gzip
import hashlib
import importlib.util
import inspect
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time

import numpy as np

HERE=Path(__file__).resolve().parent
GOV=HERE.parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(GOV))
sys.path.insert(0,str(ROOT/'apps/selfcitation_governor'))
import governor
import build_data
from evaluate import Scorer,read_words
from voynich_gradients.glyph_units import units

CONDITIONS={
    'native_noinnov':dict(policy='native',repair=False,edit=0),
    'native_repair':dict(policy='native',repair=True,edit=0),
    'page_native':dict(policy='page',repair=True,edit=0),
    'page_edit':dict(policy='page',repair=True,edit=.35),
    'spread_native':dict(policy='spread',repair=True,edit=0),
    'spread_edit':dict(policy='spread',repair=True,edit=.35),
    'page_edit_coarse':dict(policy='page',repair=True,edit=.35,coarse=True),
    'spread_edit_coarse':dict(policy='spread',repair=True,edit=.35,coarse=True),
    'page_edit_high':dict(policy='page',repair=True,edit=.75),
    'spread_edit_low':dict(policy='spread',repair=True,edit=.15),
    'spread_edit_tokens':dict(policy='spread',repair=True,edit=.35,token_sample=True),
    'page_stems':dict(policy='page',repair=True,edit=0,long_source=.8),
    'page_stems_edit':dict(policy='page',repair=True,edit=.35,long_source=.8),
    'spread_stems_edit':dict(policy='spread',repair=True,edit=.15,long_source=.8),
}
COARSE=['prefix:qo','prefix:qok','eo','suffix:dy','suffix:edy','suffix:eedy',
        'ch','suffix:ol','suffix:aiin','interior:e','prefix:ch','suffix:y']


def strip(word):
    return word[1:] if len(word)>1 and word[0] in 'ktpf' else word


def build_runtime(folder):
    """Compile an isolated snapshot of current hooks, then add experimental hooks."""
    folder=Path(folder)
    for name in ['Bridge.java','GovernedChooser.java']:
        shutil.copyfile(GOV/name,folder/name)
    spec=importlib.util.spec_from_file_location('isolated_build',GOV/'build.py')
    builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
    builder.HERE=folder
    builder.main()
    pkg=folder/'build/source/de/voynich/text'
    shutil.copyfile(HERE/'HumanSupply.java',pkg/'sourcechooser/HumanSupply.java')
    path=pkg/'sourcechooser/PageSourceGroupChooser.java';source=path.read_text()
    old='        ChooseMode mode = ChooseMode.LOCALY;'
    assert source.count(old)==1
    source=source.replace(old,'        if(HumanSupply.enabled() && !generatedLinesList.isEmpty()) return HumanSupply.choose(generatedLinesList, actualLineList, isLineInitial);\n'+old)
    path.write_text(source,encoding='utf-8')
    path=pkg/'SelfCitationTextGenerator.java';source=path.read_text()
    old='sourceGroups = config.statistics.suggestGroupsForce(count-100);'
    assert source.count(old)==1
    source=source.replace(old,'if(!de.voynich.text.sourcechooser.HumanSupply.enabled()) '+old)
    path.write_text(source,encoding='utf-8')
    path=pkg/'Bridge.java';source=path.read_text()
    old='while(reply!=null&&reply.startsWith("?F\\t")){System.out.println("!F\\t"+freedom(reply.substring(3)));System.out.flush();reply=input.readLine();}'
    assert source.count(old)==1
    new='''while(reply!=null&&(reply.startsWith("?F\\t")||reply.startsWith("?V\\t"))){
                if(reply.startsWith("?F\\t"))System.out.println("!F\\t"+freedom(reply.substring(3)));
                else {StringBuilder valid=new StringBuilder("!V");for(String w:reply.substring(3).split("\\t")){GlyphGroup g=new GlyphGroup(w,GlyphGroup.GENERATE_TYPE.REPLACE);valid.append("\\t").append(canFollow.isValid(g)&&canFollow.hasValidStartGlyph(g)?"1":"0");}System.out.println(valid);}
                System.out.flush();reply=input.readLine();}'''
    path.write_text(source.replace(old,new),encoding='utf-8')
    classes=folder/'build/classes'
    proc=subprocess.run(['java','-jar',str(builder.UP/'ecj.jar'),'-1.8','-encoding','UTF-8','-nowarn','-d',str(classes)]+[str(p) for p in (folder/'build/source').rglob('*.java')],capture_output=True,text=True)
    assert proc.returncode==0,proc.stdout+proc.stderr
    return str(classes)


def install_variant(spec):
    cfg=spec['variant'];original=governor.Governor
    class ExperimentalGovernor(original):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs)
            self.visible=[];self.allowed_positions=set();self.last_recent_pos=-1
            self.recent=Counter();self.birth_examples=[];self.edit_pending={};self.prefix_stats=None
            self.coarse={i for i,f in enumerate(self.m.features) if f['name'] in COARSE}
            assert len(self.coarse)==12
        def refresh_recent(self):
            if self.last_recent_pos!=len(self.emitted):
                self.last_recent_pos=len(self.emitted);self.recent=Counter(self.emitted[-20:])
        def preference(self,word,s,pi):
            ix=self.m.X(word)
            if cfg.get('coarse'):ix=np.array([i for i in ix if i in self.coarse],int)
            return float(pi[ix].sum())
        def value(self,word,s,pi):
            if cfg.get('coarse'):return self.preference(word,s,pi)
            return super().value(word,s,pi)
        def source(self,fields):
            if not cfg['repair']:return super().source(fields)
            self.refresh_recent();pos=int(fields[1]);s=self.m.node(pos);pi=self.pressure(s)
            occurrences={};allowed=set()
            for entry in fields[5:]:
                idx,mult,same,words=entry.split('|',3);idx=int(idx);ws=words.split()
                for j,w in enumerate(ws):
                    k=strip(w)
                    occurrences.setdefault(k,[]).append((idx,j,w,ws[min(j+1,len(ws)-1)]))
                    if cfg['policy']!='native':
                        assert self.emitted[idx+j]==w,(idx+j,w,self.emitted[idx+j])
                        allowed.add(idx+j)
            self.visible=list(occurrences);self.allowed_positions=allowed
            # Four distinct visible forms at most, rather than an exhaustive search.
            pool=self.visible
            if cfg.get('long_source') and self.rng.random()<cfg['long_source']:
                longer=[w for w in pool if len(units(w,'zattera'))>=3]
                if longer:pool=longer
            if cfg.get('token_sample'):
                weights=np.array([len(occurrences[w]) for w in pool],float);weights/=weights.sum()
                chosen=list(dict.fromkeys(self.rng.choice(len(pool),4,p=weights).tolist()))
            else:chosen=self.rng.choice(len(pool),min(4,len(pool)),replace=False)
            candidates=[pool[int(i)] for i in chosen]
            scores=np.array([.5*self.preference(w,s,pi)-math.log1p(2*self.recent[w]) for w in candidates])
            scores-=scores.max();prob=np.exp(scores);prob/=prob.sum()
            k=int(self.rng.choice(len(candidates),p=prob));key=candidates[k]
            copies=occurrences[key];idx,j,w,partner=copies[int(self.rng.integers(len(copies)))]
            self.stats['source_calls']+=1;self.stats['source_forms_considered']+=len(candidates)
            self.stats['source_visible_type_sum']+=len(pool)
            if cfg['policy']=='native':return 'I\t%d\t%d'%(idx,j)
            self.stats['visible_source_draws']+=1
            self.stats['previous_page_picks']+=int(idx+j<int(fields[3]))
            self.stats['source_age_sum']+=pos-(idx+j)
            self.stats['source_age_over200']+=int(pos-(idx+j)>200)
            assert idx+j in allowed
            return 'W\t%s\t%s\t%d'%(w,partner,idx+j)
        def propose(self,fields):
            pos=int(fields[2]);src=fields[6]
            if cfg['policy']!='native' and ':VISIBLE_' in fields[7]:
                self.stats['visible_proposals']+=1
                assert int(fields[3]) in self.allowed_positions,(fields[3],sorted(self.allowed_positions)[:3])
            if cfg['edit'] and len(fields)==9 and self.visible and self.rng.random()<cfg['edit']:
                name=fields[7].split(':');avail=int(name[4]);s=self.m.node(pos);pi=self.pressure(s)
                raw=fields[8].rsplit(':',1)[0];seq=[u.text for u in units(raw,'zattera')]
                if seq:
                    candidates=[];operations=[]
                    for _ in range(3):
                        donor=self.visible[int(self.rng.integers(len(self.visible)))];ds=[u.text for u in units(donor,'zattera')]
                        if not ds:continue
                        op=int(self.rng.integers(5));p=int(self.rng.integers(len(seq)));q=int(self.rng.integers(len(ds)))
                        if op==0:
                            n=int(self.rng.integers(1,min(3,len(seq))+1));m=int(self.rng.integers(1,min(3,len(ds))+1));new=seq[:-n]+ds[-m:]
                        elif op==1:
                            n=int(self.rng.integers(1,min(3,len(seq))+1));m=int(self.rng.integers(1,min(3,len(ds))+1));new=ds[:m]+seq[n:]
                        elif op==2:new=seq[:p]+[ds[q]]+seq[p:]
                        elif op==3:new=seq[:p]+[ds[q]]+seq[p+1:]
                        else:new=seq[:p]+seq[p+1:]
                        w=''.join(new)
                        if w and w!=raw and len(w)<=avail and len(new)<=10 and w not in candidates:
                            candidates.append(w);operations.append(op)
                    self.stats['edit_events']+=1;self.stats['edit_candidates_drawn']+=3
                    if candidates:
                        self.proc.stdin.write('?V\t'+'\t'.join(candidates)+'\n');self.proc.stdin.flush()
                        reply=self.proc.stdout.readline().strip().split('\t');assert reply[0]=='!V',reply
                        candidates=[w for w,v in zip(candidates,reply[1:]) if v=='1']
                    if candidates:
                        self.refresh_recent();options=[raw]+candidates
                        scores=np.array([.5*self.preference(w,s,pi)-math.log1p(2*self.recent[w]) for w in options])
                        scores-=scores.max();prob=np.exp(scores);prob/=prob.sum();k=int(self.rng.choice(len(options),p=prob))
                        if k:
                            self.stats['edit_proposals']+=1;fields=fields.copy();fields[8]=options[k]+':REPLACE'
                            self.edit_pending[int(fields[1])]=dict(pos=pos,source=src,native=raw,word=options[k])
            return super().propose(fields)
        def accept(self,fields):
            pos=int(fields[1]);word=fields[3];event=self.edit_pending.pop(int(fields[2])//100,None)
            if event and word==event['word']:
                self.stats['edited_tokens']+=1
                if word not in self.seen:
                    self.stats['edited_births']+=1
                    if len(self.birth_examples)<20:self.birth_examples.append(event)
            # These records are scoring only, never used to propose a word.
            if len(self.edit_pending)>500:self.edit_pending.clear()
            result=super().accept(fields)
            if pos==34976:self.prefix_stats=dict(self.stats)
            return result
    governor.Governor=ExperimentalGovernor
    # Override the compiled runtime path and expose explicit source restriction.
    popen=governor.subprocess.Popen
    def launch(command,*args,**kwargs):
        command=list(command);i=command.index('-cp');command[i+1]=spec['classes']
        command.insert(1,'-Dbridge.visible='+cfg['policy'])
        return popen(command,*args,**kwargs)
    governor.subprocess.Popen=launch
    fixed=spec['args']['seed']*7919+1014
    default_rng=np.random.default_rng
    governor.np.random.default_rng=lambda seed=None:default_rng(fixed)
    # Snapshot small audit records before the stock main releases the governor.
    accept=ExperimentalGovernor.accept
    def audited_accept(self,fields):
        accept(self,fields)
        install_variant.last=self
    ExperimentalGovernor.accept=audited_accept


def child(path):
    spec=json.loads(Path(path).read_text());install_variant(spec)
    argv=['governor.py']
    for key,value in spec['args'].items():
        if key=='floors' or value is None:continue
        flag='--'+key.replace('_','-')
        if isinstance(value,bool):
            if value:argv.append(flag)
        else:argv.extend([flag,str(value)])
    sys.argv=argv;governor.main()
    g=install_variant.last
    Path(spec['args']['out'],'experiment_audit.json').write_text(json.dumps(dict(examples=g.birth_examples,prefix_stats=g.prefix_stats)))


def score(words,scorer):
    ends=scorer.ends;count=min(len(words),scorer.total)
    eligible=np.flatnonzero(ends<=count);limit=int(ends[eligible[-1]])
    words=words[:limit];shares,bags=scorer.shares(words)
    mattr=np.array([build_data.mattr(words[int(scorer.starts[i]):int(ends[i])],100) for i in eligible])
    fiterr=np.abs(shares-scorer.m.target)[:,scorer.common].mean(1)*100
    obserr=np.abs(shares-scorer.obs_share)[:,scorer.common].mean(1)*100
    seen=set();birth=[]
    for w in words:birth.append(w not in seen);seen.add(w)
    lengths=Counter({w:len(units(w,'zattera')) for w in seen})
    def section(sel):
        idx=[i for i in eligible if sel(i)];weights=scorer.N[idx]
        return dict(mattr100=float(np.average(mattr[[list(eligible).index(i) for i in idx]],weights=weights)),
                    component_fit_pp=float(np.average(fiterr[idx],weights=weights)),
                    component_observed_pp=float(np.average(obserr[idx],weights=weights)))
    r=dict(tokens=limit,types=len(seen),whole=section(lambda i:True),section1a=section(lambda i:scorer.groups[i]=='1a'),
           by_group={g:section(lambda i:scorer.groups[i]==g) for g in dict.fromkeys(scorer.groups[i] for i in eligible)},
           by_node=[dict(id=scorer.nodes[i]['id'],mattr100=float(mattr[j]),component_fit_pp=float(fiterr[i])) for j,i in enumerate(eligible)],
           births_per1000_early=sum(birth[:min(10000,limit)])/min(10000,limit)*1000,
           births_per1000_late=sum(birth[max(0,limit-10000):])/min(10000,limit)*1000,
           birth_counts_1000=[sum(birth[i:i+1000]) for i in range(0,limit,1000)],
           absent_token_share=sum(w not in scorer.vocab for w in words)/limit,
           mean_units=float(np.mean([lengths[w] for w in words])),
           mean_units_new=float(np.mean(list(lengths.values()))),
           family_share=sum(w in {'o','y','qo'} for w in words)/limit,
           adjacent_repeat_share=sum(a==b for a,b in zip(words,words[1:]))/(limit-1))
    return r


def run(condition,seed,lines,classes,scorer):
    args=json.loads((GOV/'runs/n_noinnov_far0/run.json').read_text())['args']
    args.update(seed=seed,lines=lines,trace=False)
    with tempfile.TemporaryDirectory(prefix='voynich_human_run_') as td:
        path=Path(td);args['out']=str(path/'run')
        spec=dict(condition=condition,variant=CONDITIONS[condition],args=args,classes=classes)
        (path/'spec.json').write_text(json.dumps(spec))
        with (path/'log.txt').open('w',encoding='utf-8') as log:
            result=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--child',str(path/'spec.json')],stdout=log,stderr=subprocess.STDOUT)
        if result.returncode:raise RuntimeError((path/'log.txt').read_text()[-6000:])
        out=path/'run';words=read_words(out/'generated_text.txt');meta=json.loads((out/'run.json').read_text())
        metrics=score(words,scorer);audit=json.loads((out/'experiment_audit.json').read_text())
        if condition=='native_noinnov' and seed==1:
            old=read_words(GOV/'runs/n_noinnov_far0/generated_text.txt');assert words[:3514]==old[:3514]
        args['out']='<temporary>'
        return dict(condition=condition,seed=seed,lines=lines,variant=CONDITIONS[condition],args=args,
                    seconds=meta['seconds'],text_sha256=meta['text_sha256'],generated_tokens=meta['tokens'],metrics=metrics,stats=meta['stats'],audit=audit)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--child');parser.add_argument('--only',nargs='+',default=list(CONDITIONS));parser.add_argument('--seeds',type=int,default=2);parser.add_argument('--lines',type=int,default=600);parser.add_argument('--output',default='screen.json');parser.add_argument('--merge',action='store_true')
    args=parser.parse_args()
    if args.child:return child(args.child)
    scorer=Scorer();output=json.loads((HERE/args.output).read_text()) if args.merge else []
    start=time.time()
    with tempfile.TemporaryDirectory(prefix='voynich_human_build_') as tmp:
        classes=build_runtime(tmp)
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(run,c,s,args.lines,classes,scorer) for c in args.only for s in range(1,args.seeds+1)]
            for future in as_completed(futures):
                item=future.result();output=[r for r in output if (r['condition'],r['seed'])!=(item['condition'],item['seed'])];output.append(item)
                print(item['condition'],item['seed'],json.dumps(item['metrics']['section1a']), 'types',item['metrics']['types'],'seconds',round(time.time()-start),flush=True)
                (HERE/args.output).write_text(json.dumps(sorted(output,key=lambda r:(r['condition'],r['seed'])),indent=2)+'\n')
    paths=[Path(__file__),HERE/'HumanSupply.java',GOV/'governor.py',GOV/'build.py',GOV/'Bridge.java',GOV/'GovernedChooser.java']
    (HERE/(Path(args.output).stem+'_source_hashes.json')).write_text(json.dumps({str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},indent=2)+'\n')


if __name__=='__main__':main()
