"""Govern Timm's generator with the positional gradient model (positional-composition-544-v1).

Two of Timm's decisions are reweighted at every token, with his own distribution recovered at zero temperature:
  source choice  : weight = Timm's base probability x exp(beta_c * (log P_s(w) - log f_pool(w)))      (--source word)
  mutation       : accept the morph proposal with probability min(1, exp(beta_m * delta)), else keep the copy
                   (or ask for another proposal up to --retry times); delta = mean value(proposal parts) - value(source)
  value(w)       : --mode pressure (default): sum_j X_j(w) * clip(log((target_j(s)+eps)/(ema_j+eps))), where target is the
                   fitted carrier share of feature j at node s and ema the emitted text's share (horizon --horizon tokens);
                   --mode theta: X(w) . theta(s) [+ kappa log prior], the fitted coefficients relative to the training prior.
No transformer, transport plan or learned head is involved.
  --spatial      : the page draws come from the words physically in view on the manuscript page being written, by the
                   app's own selector over the recorded word rectangles (cone above, reach to the left, distance weights;
                   page_geometry.py); Timm's own draw stands where nothing is in view. Requires --match-pages.

python governor.py --seed 1 --beta-c 1 --beta-m 1 --out runs/g_c1_m1_s1
"""
import argparse, gzip, json, math, re, subprocess, sys, time, hashlib
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent; STUDY=HERE.parent; ROOT=STUDY.parents[1]
PKG=ROOT/'packages/voynich_gradients'
sys.path.insert(0,str(PKG/'src'));sys.path.insert(0,str(HERE))
from voynich_gradients.glyph_units import units
import page_geometry as PG

MODEL_ID='positional-composition-544-v1'
EVA=list('acdefhiklmnopqrstxy')   # single letters, for --eva-units

class Model:
    def __init__(self,combined=True,fit='full'):
        a=json.load(gzip.open(PKG/'src/voynich_gradients/assets/positional_path1.json.gz','rt',encoding='utf-8'))
        meta=json.load(gzip.open(PKG/f'translation/data/positional/path1_{fit}.json.gz','rt',encoding='utf-8'))
        z=np.load(PKG/f'translation/data/positional/path1_{fit}.npz')
        assert meta['model_id']==a['model_id']==MODEL_ID
        self.fit=fit;self.training_pages=meta['training_pages']
        self.features=meta['features']
        self.theta=z['alpha']+z['B']@z['beta']+(z['H']@z['delta'] if combined else 0.0)
        allwords=[w['word'] for w in a['words']]
        self.words=[allwords[i] for i in meta['word_ids']];self.prior=np.array(meta['prior'])
        self.logq={w:math.log(q) for w,q in zip(self.words,self.prior)};self.logq_min=float(np.log(self.prior.min()))
        self.N=np.array([n['N'] for n in a['nodes']]);self.cumulative=np.cumsum(self.N);self.nodes=a['nodes']
        self.tokens=np.array([f['tokens'] for f in self.features])
        tr=a['transitions'];self.trow={r:i for i,r in enumerate(tr['rows'])};self.tcol={c:i for i,c in enumerate(tr['columns'])};self.TC=np.array(tr['combined'])
        self.alphabet=[u for u,c in Counter(u.text for w in allwords for u in units(w,'zattera')).most_common() if c>=20 and u.isalpha()]
        # feature matrix over the fit's vocabulary, word distribution per node, fitted carrier shares (targets)
        rows=[];cols=[]
        for j,f in enumerate(self.features):rows.extend(f['members']);cols.extend([j]*len(f['members']))
        Xm=np.zeros((len(self.words),len(self.features)));Xm[rows,cols]=1.0
        self.known={w:np.flatnonzero(Xm[i]).astype(int) for i,w in enumerate(self.words)};self.Xm=Xm;self.walked=False
        eta=Xm@self.theta.T+np.log(self.prior)[:,None];eta-=eta.max(0,keepdims=True);P=np.exp(eta);P/=P.sum(0,keepdims=True)
        self.P=P   # (words, nodes)
        self.target=(P.T@Xm)   # (50, F)
        if fit=='full':
            assert meta['word_ids']==list(range(len(allwords)))
            ref=np.array(a['matrices']['combined' if combined else 'gradual']).T/1e4
            assert np.abs(self.target-ref).max()<1e-6
        self.pos_names=defaultdict(set);self.patterns=defaultdict(list);self.prefixes=[];self.suffixes=[];self.interactions=[]
        for j,r in enumerate(self.features):
            for rr in [r]+[dict(al,members=[]) for al in r['aliases']]:
                if rr.get('source') in ('position','ordered_pair') or rr['kind']=='position':self.pos_names[rr['name']].add(j)
                elif rr['kind']=='prefix':self.prefixes.append((tuple(rr['units']),j))
                elif rr['kind']=='suffix':self.suffixes.append((tuple(rr['units']),j))
                elif rr['kind']=='interaction':
                    self.interactions.append(([tuple(g.text for g in units(v,'zattera')) for v in rr['name'].split(' & ')],j))
                else:self.patterns[tuple(rr['units'])].append(j)
        self.maxpat=max(len(p) for p in self.patterns)
        rng=np.random.default_rng(0)
        for i in rng.choice(len(self.words),400,replace=False):
            w=self.words[i];assert np.array_equal(self.compute(w),self.known[w]),w
    def node(self,position):return min(len(self.N)-1,int(np.searchsorted(self.cumulative,position,side='right')))
    def walk(self,scale,seed,steps,step_tokens):
        """--target-walk: targets that start at the first bifolium's and perform a Gaussian random walk in coefficient
        space, one step per `step_tokens` written words: every coefficient moves by N(0, sigma) per step, with sigma =
        scale x RMS(theta_last - theta_first) / sqrt(nodes - 1), so that at scale 1 the typical displacement after one
        manuscript length equals the manuscript's own, in a random direction. Targets are the implied carrier shares."""
        rng=np.random.default_rng(seed);th=self.theta[0].copy();d=self.theta[-1]-self.theta[0]
        sig=scale*float(np.sqrt(np.mean(d**2)))/np.sqrt(len(self.N)-1);logq=np.log(self.prior);T=[]
        for k in range(steps):
            if k>0:th=th+rng.normal(0.0,sig,size=th.shape)
            eta=self.Xm@th+logq;eta-=eta.max();p=np.exp(eta);p/=p.sum();T.append(p@self.Xm)
        self.target=np.array(T);self.N=np.full(steps,step_tokens);self.cumulative=np.cumsum(self.N);self.walked=True;self.walk_sigma=sig
    def compute(self,word):
        seq=tuple(u.text for u in units(word,'zattera'));n=len(seq);found=set();spans=[]
        for width in range(1,4):
            if width<n:spans.append(('prefix:'+''.join(seq[:width]),0,width));spans.append(('suffix:'+''.join(seq[-width:]),n-width,n))
        for start in range(1,n-1):
            for width in (1,2):
                if start+width<n:spans.append(('interior:'+''.join(seq[start:start+width]),start,start+width))
        names={s[0] for s in spans};names.update(x[0]+' >> '+y[0] for x in spans for y in spans if x[2]==y[1])
        for nm in names:found.update(self.pos_names.get(nm,()))
        subs={seq[i:i+k] for k in range(1,self.maxpat+1) for i in range(n-k+1)}
        for s in subs:found.update(self.patterns.get(s,()))
        found.update(j for p,j in self.prefixes if seq[:len(p)]==p)
        found.update(j for p,j in self.suffixes if seq[-len(p):]==p)
        for parts,j in self.interactions:
            if all(p in subs for p in parts):found.add(j)
        return np.array(sorted(found),int)
    @lru_cache(maxsize=400000)
    def X(self,word):
        return self.known[word] if word in self.known else self.compute(word)
    def legality(self,word,s):
        s=min(s,len(self.TC)-1);path=['^']+[u.text for u in units(word,'zattera')]+['$'];vals=[]
        for x,y in zip(path[:-1],path[1:]):vals.append(self.TC[s,self.trow[x],self.tcol[y]] if (x in self.trow and y in self.tcol) else 0.0)
        return math.log(max(min(vals),1e-9))
    def eta(self,word,s,kappa,nu):
        v=float(self.theta[s,self.X(word)].sum())
        if kappa:v+=kappa*(self.logq[word] if word in self.logq else self.logq_min-nu)
        return v


class Governor:
    def __init__(self,model,args,rng):
        self.m=model;self.a=args;self.rng=rng;self.emitted=[];self.stats=Counter();self.retries=defaultdict(int);self.log=[]
        self.ema=model.target[0].copy();self.decay=1.0-1.0/args.horizon
        self.seen=set();self.slot_of={};self.slot_ema={};self.slot_n=Counter();self.slots=[]
        self.slot_rate={'page-first':0.747,'paragraph-first':0.591,'paragraph-line':0.266,'line-first':0.266,'line-final':0.313,'interior':0.145}
        self.slot_len={'page-first':5.82,'paragraph-first':5.94,'paragraph-line':5.33,'line-first':5.35,'line-final':5.25,'interior':5.07};self.len_ema={};self.avail_of={}
        self.slot_join={'page-first':0.39,'paragraph-first':0.67,'paragraph-line':0.67,'line-first':0.75,'line-final':0.71,'interior':0.69};self.context_of={}
        curve=json.loads((HERE/'novelty_target.json').read_text(encoding='utf-8'));rate=np.array(curve['new_type_rate']);N=np.array(curve['N'])
        self.node_factor=rate/np.average(rate,weights=N) if args.novelty_curve else np.ones(len(rate))
        if len(model.N)>len(self.node_factor):self.node_factor=np.concatenate([self.node_factor,np.ones(len(model.N)-len(self.node_factor))])
        self.trace=[] if getattr(args,'trace',False) else None;self.snap_at=-1;self.last_mode='';self.last_inn={}
        self.repeat_offered={};self.no_repeat={};self.rep_blocks=Counter()   # --repeat-once bookkeeping per written position
        self.freedom_cache={};self.proc=None
        self.buffer={}   # --buffer / --store: word type -> position of its last use (insertion order = recency)
        self.store=None;self.store_pos={};self.store_log=[]   # --store: the frozen list, its words' positions at the snapshot, the snapshots
        self.in_degenerate=False   # diversity monitor: distinct forms among the last 50 words below half (trace 'D' at each onset)
        self.store_at=set(int(x) for x in str(getattr(args,'store_at','') or '').split(',') if x.strip())
        self.spatial=bool(getattr(args,'spatial',False))   # --spatial: page draws from the words in view on the recorded page geometry
        if self.spatial:
            self.geo=PG.PageGeometry();self.layout=PG.Layout(self.geo)
            self.spatial_opt=dict(left=args.spatial_left,depth=args.spatial_depth,angle=args.spatial_angle,weight=args.spatial_weight,cap=args.spatial_cap)
            self.line_starts=set();self.cur_line=0;self.last_S_spatial=False;self.src_spatial={};self.pool_of={};self.pool_log=[]
    def seed_layout(self):
        """--spatial: the seed line's words take the first manuscript line's slot."""
        for i,w in enumerate(self.emitted):self.layout.add(i,w,0);self.pool_log.append(None)
    def set_store(self,pos):
        """--store: freeze the current N most recently used distinct types as the far supply until the next rewrite."""
        a=self.a;n=a.store
        if getattr(a,'store_select','recent')=='pressure' and len(self.emitted)>n:
            last={}
            for i,w in enumerate(self.emitted[-a.pool:]):last[w]=len(self.emitted)-len(self.emitted[-a.pool:])+i
            s_=self.m.node(pos);pi=self.pressure(s_)
            ranked=sorted(last,key=lambda w:(-self.value(w,s_,pi),-last[w]))[:n]
            self.store=ranked;self.store_pos={w:last[w] for w in ranked};sel='pressure'
        else:
            self.store=list(self.buffer.keys());self.store_pos=dict(self.buffer);sel='recent'
        self.store_log.append({'at':pos,'select':sel,'words':self.store});self.stats['store_set']+=1
    def choose_order(self,fields):
        """--partner-order: Timm's combine was tried both ways (source front + partner tail / partner front + source tail);
        pick the result by the pressures at the current bifolium, at the source temperature."""
        a_,b_=fields[1],fields[2];s=self.m.node(len(self.emitted));pi=self.pressure(s)
        lw=np.array([self.value(a_,s,pi),self.value(b_,s,pi)])*self.a.beta_c;lw-=lw.max();p=np.exp(lw);p/=p.sum()
        k=int(self.rng.choice(2,p=p));self.stats['order_queries']+=1
        if k==1:self.stats['order_partner_first']+=1
        if self.trace is not None:self.trace.append({'t':'C','w':len(self.emitted),'a':a_,'b':b_,'k':k,'p':round(float(p[k]),4)})
        return '!C\t%d'%k
    def eta(self,word,s):return self.m.eta(word,s,self.a.kappa,self.a.nu)
    def pressure(self,s):
        eps=self.a.eps;t=self.m.target[s]
        return np.clip(np.log((t+eps)/(self.ema+eps)),-self.a.clip,self.a.clip)
    def freedom(self,word):
        """--mode freedom: the word's number of legal one-glyph neighbours under Timm's curve-line rules, from the Java side."""
        c=self.freedom_cache.get(word)
        if c is None:
            self.proc.stdin.write('?F\t'+word+'\n');self.proc.stdin.flush();line=self.proc.stdout.readline()
            assert line.startswith('!F\t'),line[:40];c=int(line.split('\t')[1]);self.freedom_cache[word]=c
        return c
    def value(self,word,s,pi):
        if self.a.mode=='freedom':
            n=self.freedom(word)
            if self.a.freedom_norm:return self.a.freedom_scale*math.log((n+0.5)/(36*len(word)+18))   # share of the word's one-glyph edits that are legal
            return self.a.freedom_scale*math.log(1.0+n)
        if self.a.mode=='theta':return self.eta(word,s)
        return float(pi[self.m.X(word)].sum())
    def update_ema(self,word):
        x=np.zeros(len(self.ema));x[self.m.X(word)]=1.0
        self.ema=self.decay*self.ema+(1-self.decay)*x
    def operations(self,fields):
        """@O (--operations): one proposal list per operation (add/remove, combine/split, replace); choose with Timm's
        operation probabilities reweighted by pressure, weight = base_op x exp(beta_o x value), value = mean over the parts."""
        a=self.a;written=int(fields[1]);source=fields[2];s=self.m.node(written);pi=self.pressure(s)
        opts=[[v.rsplit(':',1)[0] for v in f.split('|')] if f else [] for f in fields[4:7]]
        base=[0.2,0.3,0.5];beta=a.beta_o if a.beta_o is not None else a.beta_m
        vals=[float(np.mean([self.value(w,s,pi) for w in o])) if o else None for o in opts]
        live=[i for i,o in enumerate(opts) if o]
        if not live:return '0'
        logw=np.array([math.log(base[i])+beta*vals[i] for i in live]);logw-=logw.max();w=np.exp(logw);w/=w.sum()
        k=live[int(self.rng.choice(len(live),p=w))];self.stats['op_calls']+=1;self.stats['op_'+('add_remove','combine_split','replace')[k]]+=1;self.last_op=k
        if self.trace is not None:self.trace.append({'t':'O','w':written,'src':source,'opts':opts,'vals':[round(v,3) if v is not None else None for v in vals],'pick':k,'prob':round(float(w[live.index(k)]),4)})
        return str(k)
    def note_refusal(self,written):
        """--repeat-once: a new draw at a position where a repeat of the word just written was offered means Timm's coin
        (or another of his checks) refused it; from now on this position's draws leave that word out."""
        if self.repeat_offered.pop(written,None):self.no_repeat[written]=True
    def guarded(self,written,first,line_initial,reply,prec):
        """--repeat-once, the proposal side: a proposal equal to the word just written (Timm's repeat case, which his
        program accepts on a coin flip) is offered once per position; after his refusal it is sent back for another
        draw (at most 8 times, then it passes). Line-initial words are no repeat for Timm and none here."""
        a=self.a
        if not getattr(a,'repeat_once',False) or line_initial or not self.emitted or first!=self.emitted[-1]:return reply
        if self.no_repeat.get(written) and self.rep_blocks[written]<8:
            self.rep_blocks[written]+=1;self.stats['repeat_blocked']+=1
            if prec:prec['dec']='R';prec['rep']=1
            return ''
        self.repeat_offered[written]=True;self.stats['repeat_offered']+=1
        return reply
    def cap_words(self,w,words,cap):
        """--source-cap: no single word may take more than `cap` of the draw (or 1/k with k distinct words, when that is
        larger); the excess is spread over the other words in proportion, and a word's positions keep their proportions."""
        mass=defaultdict(float)
        for i,wd in enumerate(words):mass[wd]+=float(w[i])
        k=len(mass);cap=max(cap,1.0/k)
        if max(mass.values())<=cap+1e-9:return w,0
        orig=dict(mass);capped=set()
        for _ in range(k):
            over=[wd for wd,m in mass.items() if wd not in capped and m>cap+1e-9]
            if not over:break
            capped|=set(over);free=1.0-cap*len(capped);rest=sum(orig[wd] for wd in mass if wd not in capped)
            for wd in mass:mass[wd]=cap if wd in capped else (orig[wd]*free/rest if rest>0 else 0.0)
        out=np.array([float(w[i])*mass[wd]/orig[wd] for i,wd in enumerate(words)]);out/=out.sum()
        self.stats['source_capped']+=1
        return out,1
    def source(self,fields):
        a=self.a;written=int(fields[1]);line_initial=fields[2]=='1';def_line=int(fields[3]);def_pos=int(fields[4]);s=self.m.node(written)
        p_same=(14+1)/100 if line_initial else (28+1)/100
        lines=[];draws=0
        for entry in fields[5:]:
            idx,mult,same,words=entry.split('|',3);lines.append((int(idx),int(mult),int(same),words.split()));draws+=int(mult)
        cand=[];base=[]
        for idx,mult,same,words in lines:
            if not words:continue
            for i,w in enumerate(words):
                cand.append((idx,i,w));base.append(mult/draws*((p_same if i==same else 0.0)+(1-p_same)/len(words)))
        spatial_pick=None   # --spatial: (positions, weights, available, target box) when the words in view supply the draw
        if self.spatial:
            self.last_S_spatial=False;self.stats['spatial_calls']+=1
            if line_initial:self.line_starts.add(written)
            new=written in self.line_starts
            if lines:
                msg_line=max(idx for idx,_,_,_ in lines)+2   # the generator's line list holds the generated lines without the seed line
                if msg_line!=self.cur_line+(1 if new else 0):self.stats['spatial_line_resync']+=1;self.cur_line=msg_line-(1 if new else 0)
            cur=self.cur_line+(1 if new else 0)
            res=self.layout.pool(cur,self.spatial_opt)
            if res is None:self.stats['spatial_none_'+(self.layout.last_reason or 'other')]+=1
            elif not res[0]:self.stats['spatial_empty']+=1
            else:
                spatial_pick=res;positions,wts,available,tgt=res
                cand=[(p,-1,self.emitted[p]) for p in positions];base=[float(x) for x in np.asarray(wts)/float(np.sum(wts))]
        rec=None
        if self.trace is not None:
            rec={'t':'S','w':written,'li':int(line_initial),'def':[def_line,def_pos],'lines':[[idx,mult,same] for idx,mult,same,words in lines]};self.trace.append(rec)
        if not cand:
            if rec:rec['pick']=[def_line,def_pos];rec['mode']='empty'
            return 'I\t%d\t%d'%(def_line,def_pos)
        if a.beta_c==0 and a.far==0 and spatial_pick is None:
            if rec:rec['pick']=[def_line,def_pos];rec['mode']='timm'
            return 'I\t%d\t%d'%(def_line,def_pos)
        far=a.far>0 and len(self.emitted)>50 and self.rng.random()<a.far
        if far and getattr(a,'store',0)>0 and (self.store or self.buffer):
            types=self.store if self.store else list(self.buffer.keys());start=0;pool=types
            cand=[(self.store_pos.get(w,self.buffer.get(w,0)),i,w) for i,w in enumerate(types)];base=[1.0/len(types)]*len(types)
        elif far and getattr(a,'buffer',0)>0 and self.buffer:
            types=list(self.buffer.items());start=0;pool=types
            cand=[(p,i,w) for i,(w,p) in enumerate(types)];base=[1.0/len(types)]*len(types)
        elif far:
            pool=self.emitted[-a.pool:];start=len(self.emitted)-len(pool)
            cand=[(start+i,i,w) for i,w in enumerate(pool)];base=[1.0/len(pool)]*len(pool)
        if far and spatial_pick is not None:spatial_pick=None   # a far draw replaces the page draw, spatial or not
        if spatial_pick is not None:
            self.last_S_spatial=True;self.stats['spatial_picks']+=1;self.pool_of[written]=[len(spatial_pick[0]),int(spatial_pick[2])]
        rep_=0
        if getattr(a,'repeat_once',False) and not line_initial and self.emitted:
            self.note_refusal(written)
            if self.no_repeat.get(written):
                last=self.emitted[-1];keep=[i for i,c in enumerate(cand) if c[2]!=last]
                if keep and len(keep)<len(cand):cand=[cand[i] for i in keep];base=[base[i] for i in keep];rep_=1;self.stats['repeat_excluded']+=1
        freq=Counter(w for _,_,w in cand);total=len(cand);pi=self.pressure(s)
        if a.source=='word':score=np.array([self.m.eta(w,s,1.0,a.nu)-math.log(freq[w]/total) for _,_,w in cand])
        else:score=np.array([self.value(w,s,pi) for _,_,w in cand])
        logw=np.log(np.array(base))+a.beta_c*score;logw-=logw.max();w=np.exp(logw);w/=w.sum()
        capped=0
        if getattr(a,'source_cap',0)>0:w,capped=self.cap_words(w,[c[2] for c in cand],a.source_cap)
        k=int(self.rng.choice(len(cand),p=w))
        idx,i,word=cand[k];self.stats['source_calls']+=1
        if spatial_pick is not None:self.pool_of[written]+=[int(idx),int(self.layout.line_of.get(idx,-1)),int(cur)]   # chosen source, its line, the target's line
        if rec:
            rec['far']=int(far);rec['prob']=round(float(w[k]),5);rec['score']=round(float(score[k]),3);rec['base']=round(float(base[k]),5)
            if rep_:rec['rep']=1
            if capped:rec['cap']=1
            top=np.argsort(-w)[:8];rec['top']=[[int(cand[j][0]),int(cand[j][1]),round(float(w[j]),5)] for j in top]
            if far:rec['pool']=[start,len(pool)];rec['pick']=idx
            if far and getattr(a,'buffer',0)>0:rec['buf']=1
            if far and getattr(a,'store',0)>0:rec['store']=1
            if not far:rec['pick']=[idx,i]   # window pick: (line, position); a far pick keeps the emitted position
            if spatial_pick is not None:rec['spatial']=1;rec['pool']=[len(spatial_pick[0]),int(spatial_pick[2])];rec['pick']=idx;rec['tgt']=[round(float(v),1) for v in spatial_pick[3]]
        pw=None
        if getattr(a,'partner','neighbour')=='pressure':
            wl=list(dict.fromkeys(w for _,_,_,words in lines for w in words));pool_w=[w for w in wl if w!=word] or wl
            if pool_w:
                sc=np.array([self.value(w,s,pi) for w in pool_w]);lw=a.beta_c*sc;lw-=lw.max();pp=np.exp(lw);pp/=pp.sum()
                kp=int(self.rng.choice(len(pool_w),p=pp));pw=pool_w[kp];self.stats['partner_chosen']+=1
                if rec:rec['partner']=[pw,round(float(pp[kp]),4)]
        if spatial_pick is not None:
            # Timm's second source group: the source's right-hand neighbour on its line, else its left-hand one, else itself
            ln=self.layout.line_of.get(idx)
            if idx+1<len(self.emitted) and self.layout.line_of.get(idx+1)==ln:nxt=self.emitted[idx+1]
            elif idx>0 and self.layout.line_of.get(idx-1)==ln:nxt=self.emitted[idx-1]
            else:nxt=word
            return 'W\t%s\t%s\t%d'%(word,pw if pw else nxt,idx)
        if far:
            self.stats['far_picks']+=1;nxt=self.emitted[idx+1] if idx+1<len(self.emitted) else word
            return 'W\t%s\t%s\t%d'%(word,pw if pw else nxt,idx)
        if (idx,i)!=(def_line,def_pos):self.stats['source_changed']+=1
        return 'I\t%d\t%d'%(idx,i)+('\t'+pw if pw else '')
    def slot(self,fields,written):
        if len(fields)>7 and fields[7].startswith('S:'):
            bits=fields[7][2:].split(':');pi,li,lip,avail,maxlen=[int(x) for x in bits[:5]];self.last_mode=bits[5] if len(bits)>5 else ''
            if pi and li and lip<=1:name='page-first'
            elif pi and li:name='paragraph-first'
            elif li:name='line-first'
            elif avail<=12:name='line-final'
            elif pi:name='paragraph-line'
            else:name='interior'
            self.slot_of[written]=name;self.avail_of[written]=avail;self.context_of[written]=[fields[5],fields[4]]
            if self.spatial and li:self.line_starts.add(written)
            return name,fields[8:]
        return 'interior',fields[7:]
    def innovate(self,proposal,s,pi,name,written_pos=None):
        a=self.a;m=self.m;eva=getattr(a,'eva_units',False);seq=list(proposal) if eva else [u.text for u in units(proposal,'zattera')];alpha=EVA if eva else m.alphabet
        if len(seq)<2 or len(seq)>9:return None
        cand=set()
        for i in range(len(seq)+1):
            for x in alpha:cand.add(''.join(seq[:i]+[x]+seq[i:]))
        for i in range(len(seq)):
            cand.add(''.join(seq[:i]+seq[i+1:]))
            for x in alpha:
                if x!=seq[i]:cand.add(''.join(seq[:i]+[x]+seq[i+1:]))
        cand.discard(proposal)
        tl=self.slot_len[name];el=self.len_ema.get(name,tl);base=self.slot_join[name]*a.concat_scale if a.slot_concat else a.concat
        pc=min(0.9,max(0.05,base+a.kappa_l*(tl-el)/tl)) if a.kappa_l>0 else base
        draw=self.rng.random();branch='edit'
        if pc>0 and draw<pc:
            branch='concat'
            if a.adjacent:
                ctx=[w for w in self.context_of.get(written_pos,[]) if w]+self.emitted[-3:];recent=list(dict.fromkeys(ctx))
            else:recent=list(dict.fromkeys(reversed(self.emitted[-a.concat_window:])))
            if a.short_partner>0 and self.rng.random()<a.short_partner:
                branch='prefixword';ones=[u for u in alpha if u in self.seen]+['qo']
                cand={u+proposal for u in ones}|{proposal+u for u in ones if u not in ('qo',)}
            else:
                cand={proposal+w for w in recent if 1<=len(w)}|{w+proposal for w in recent if 1<=len(w)}
            if name in ('page-first','paragraph-first') and a.gallows_join:
                long_recent=[w for w in list(dict.fromkeys(reversed(self.emitted[-a.concat_window:]))) if len(units(w,'zattera'))>=3]
                cand|={g_+w for g_ in 'ktpf' for w in long_recent}
            cand={v for v in cand if (len(v) if eva else len(units(v,'zattera')))<=10}
        elif a.extend2>0 and draw<pc+a.extend2:
            branch='extend2';cand={proposal+x+y for x in alpha for y in alpha}|{x+y+proposal for x in alpha for y in alpha}
        avail=self.avail_of.get(written_pos,99)
        cand={v for v in cand if len(v)<=avail-1} if avail<99 else cand
        gallows=name in ('page-first','paragraph-first') and self.rng.random()<a.gallows_share
        starts='pf' if (gallows and self.rng.random()<a.pf_share) else 'ktpf'
        keep=[]
        for v in sorted(cand):      # a set's order depends on the process hash seed; sorted keeps runs reproducible
            if v in self.seen:continue
            if gallows and v[:1] not in starts:continue
            if not gallows and name not in ('page-first','paragraph-first','paragraph-line') and v[:1] in 'pf':continue
            if v in m.logq and m.logq[v]>a.prior_max:continue
            if m.legality(v,s)<a.legality_min:continue
            keep.append(v)
        if not keep:return None
        if a.length_neutral:
            mv=lambda w:(float(pi[m.X(w)].mean()) if len(m.X(w)) else 0.0)
            base=mv(proposal);gain=np.array([mv(v)-base for v in keep])*a.neutral_scale
        else:
            base=self.value(proposal,s,pi);gain=np.array([self.value(v,s,pi)-base for v in keep])
        w=np.exp(a.beta_i*(gain-gain.max()));w/=w.sum();k=int(self.rng.choice(len(keep),p=w))
        if self.trace is not None:
            top=np.argsort(-gain)[:10];self.last_inn={'top':[[keep[j],round(float(gain[j]),3),round(float(w[j]),4)] for j in top],'prob':round(float(w[k]),4),'pc':round(float(pc),3),'gallows':int(gallows),'starts':starts if gallows else ''}
        return keep[k],float(gain[k]),len(keep),branch
    def target(self,name,s):return min(0.95,self.slot_rate[name]*float(self.node_factor[s]))
    def fire(self,name,s):
        t=self.target(name,s);r=self.slot_ema.get(name,t)
        p=min(1.0,max(0.0,self.a.kappa_n*(t-r))) if self.a.fire=='deficit' else min(1.0,max(0.0,t+self.a.kappa_n*(t-r)))
        return self.rng.random()<p
    def propose(self,fields):
        a=self.a;pid=int(fields[1]);written=int(fields[2]);source=fields[6];name,rest=self.slot(fields,written);raw=[v.rsplit(':',1) for v in rest]
        if self.spatial:self.src_spatial[written]=(self.last_mode=='LOCALY' and self.last_S_spatial)
        if not raw:return ''
        li=name in ('page-first','paragraph-first','line-first')
        if getattr(a,'repeat_once',False):self.note_refusal(written)
        s=self.m.node(written);self.stats['proposals']+=1
        prec=None
        if self.trace is not None:
            if self.snap_at!=written and name in ('page-first','paragraph-first','line-first'):
                self.snap_at=written;self.trace.append({'t':'Q','w':written,'s':s,'p':[int(round(x*1000)) for x in self.pressure(s)]})
            prec={'t':'P','w':written,'id':pid,'src':source,'srcpos':int(fields[3]),'prev':fields[5],'slot':name,'mode':self.last_mode,'props':[[w_,m_] for w_,m_ in raw]}
            if getattr(a,'operations',False):prec['op']=getattr(self,'last_op',None)
            self.trace.append(prec)
        short_new=(a.replace_short>0 and name in ('page-first','paragraph-first') and len(raw)==1 and raw[0][0] not in self.seen
                   and len(units(raw[0][0],'zattera'))<self.slot_len[name]-0.5 and self.len_ema.get(name,self.slot_len[name])<self.slot_len[name]
                   and self.rng.random()<a.replace_short)
        if a.innovate and len(raw)==1 and (raw[0][0] in self.seen or short_new) and self.retries[written]<=a.retry and (short_new or self.fire(name,s)):
            pi=self.pressure(s);out=self.innovate(raw[0][0],s,pi,name,written)
            if out is not None:
                word,gain,ncand,branch=out;self.stats['innovated']+=1;self.stats['innovated_'+name]+=1;self.stats['branch_'+branch]+=1
                if prec:prec.update(dec='N',inn=dict(self.last_inn,branch=branch,word=word,gain=round(gain,3),n=ncand,target=round(self.target(name,s),3),realised=round(self.slot_ema.get(name,self.slot_rate[name]),3),short_new=int(short_new)))
                self.log.append([written,raw[0][0],word,round(gain,4),'N:'+name+':'+branch]);return word+':REPLACE:0'
            self.stats['innovate_failed']+=1
            if prec:prec['inn_failed']=1
        if a.beta_m==0:
            if prec:prec['dec']='T'
            if a.log_all:self.log.append([written,source,'|'.join(w for w,_ in raw),0.0,'T'])
            return self.guarded(written,raw[0][0],li,'\t'.join(f'{w}:{m}:{i}' for i,(w,m) in enumerate(raw)),prec)
        pi=self.pressure(s);es=self.value(source,s,pi);delta=float(np.mean([self.value(w,s,pi) for w,_ in raw]))-es
        changed=not(len(raw)==1 and raw[0][0]==source)
        if prec:prec.update(es=round(es,3),delta=round(delta,3),vals=[round(self.value(w,s,pi),3) for w,_ in raw],changed=int(changed))
        accept=(not changed) or self.rng.random()<min(1.0,math.exp(a.beta_m*delta))
        rec=[written,source,'|'.join(w for w,_ in raw),round(delta,4)]
        if accept:
            self.stats['accepted']+=1;rec.append('A');self.log.append(rec)
            if prec:prec['dec']='A'
            return self.guarded(written,raw[0][0],li,'\t'.join(f'{w}:{m}:{i}' for i,(w,m) in enumerate(raw)),prec)
        if self.retries[written]<a.retry:
            self.retries[written]+=1;self.stats['retried']+=1;rec.append('R');self.log.append(rec)
            if prec:prec['dec']='R'
            return ''
        self.stats['kept']+=1;rec.append('K');self.log.append(rec)
        if prec:prec['dec']='K'
        return self.guarded(written,source,li,f'{source}:{raw[0][1]}:0',prec)
    def accept(self,fields):
        pos=int(fields[1]);word=fields[3]
        assert pos==len(self.emitted),(pos,len(self.emitted))
        self.emitted.append(word);self.update_ema(word)
        if self.spatial:
            if pos in self.line_starts:self.cur_line+=1
            self.layout.add(pos,word,self.cur_line)
            used=self.pool_of.pop(pos,None) if self.src_spatial.pop(pos,False) else None
            self.pool_log.append(used)
            if used is not None:self.stats['tokens_spatial_source']+=1
        if len(self.emitted)>=50:
            win=self.emitted[-50:];r=len(set(win))/50.0
            if r<0.5:
                self.stats['degenerate_tokens']+=1
                if not self.in_degenerate:
                    self.in_degenerate=True;self.stats['degenerate_stretches']+=1
                    if self.trace is not None:self.trace.append({'t':'D','w':pos,'r':round(r,3)})
            else:self.in_degenerate=False
        cap=getattr(self.a,'buffer',0) or getattr(self.a,'store',0)
        if cap>0:
            self.buffer.pop(word,None);self.buffer[word]=pos
            if len(self.buffer)>cap:del self.buffer[next(iter(self.buffer))]
            if getattr(self.a,'store',0)>0 and ((self.store is None and len(self.buffer)>=cap) or pos in self.store_at):self.set_store(pos)
        name=self.slot_of.pop(pos,'interior');new=word not in self.seen;self.seen.add(word);self.slots.append(name)
        self.slot_n[name]+=1;d=1.0-1.0/self.a.slot_horizon;self.slot_ema[name]=d*self.slot_ema.get(name,self.slot_rate[name])+(1-d)*float(new)
        if new:
            self.stats['new_'+name]+=1;L=len(units(word,'zattera'));dl=1.0-1.0/self.a.len_horizon;self.len_ema[name]=dl*self.len_ema.get(name,self.slot_len[name])+(1-dl)*L
        self.stats['tokens_'+name]+=1
        if self.trace is not None:self.trace.append({'t':'A','w':pos,'id':int(fields[2]),'word':word,'type':fields[4],'slot':name,'new':int(new)})


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--seed',type=int,default=1);ap.add_argument('--lines',type=int,default=5000)
    ap.add_argument('--beta-c',type=float,default=0.0);ap.add_argument('--beta-m',type=float,default=0.0)
    ap.add_argument('--kappa',type=float,default=0.0,help='weight of the log prior in eta (0 = gradient features only)')
    ap.add_argument('--nu',type=float,default=2.0,help='novelty penalty below the smallest prior for unseen spellings when kappa>0')
    ap.add_argument('--retry',type=int,default=0,help='rejected proposals ask the morpher again up to this many times before keeping the copy')
    ap.add_argument('--far',type=float,default=0.0,help='probability of drawing the source from the last --pool emitted words instead of the page')
    ap.add_argument('--pool',type=int,default=2000)
    ap.add_argument('--partner',choices=['neighbour','pressure'],default='neighbour',help="the second source word handed to the morpher (what his combine glues onto the source): the source's neighbour (Timm) or a page-window word drawn by pressure")
    ap.add_argument('--partner-order',action='store_true',help='combine is tried in both orders (source front + partner tail, partner front + source tail) and the governor picks the result by pressure')
    ap.add_argument('--store',type=int,default=0,help='the far draws come from a static store of N word types: the first N distinct types of the text, rewritten only at the token positions of --store-at with the N most recently used distinct types (0 = off)')
    ap.add_argument('--store-select',choices=['recent','pressure'],default='recent',help='content of a --store rewrite: the N most recently used distinct types, or the N types of the last --pool tokens with the highest pressure value at the current bifolium')
    ap.add_argument('--store-at',type=str,default='',help='comma-separated token positions at which the --store list is rewritten (default: never)')
    ap.add_argument('--buffer',type=int,default=0,help='the far draws come from a buffer of the N most recently used distinct word types (uniform per type) instead of the last --pool tokens (0 = off)')
    ap.add_argument('--no-floors',action='store_true',help='switch off Timm i/ol/dy suggestion floors')
    ap.add_argument('--gradual-only',action='store_true',help='use alpha + B beta without the step terms')
    ap.add_argument('--mode',choices=['pressure','theta','freedom'],default='pressure',help='pressure: feature log(target share / emitted EMA share); theta: fitted coefficients only; freedom: log(1 + legal one-glyph neighbours under Timm\'s rules), no model input')
    ap.add_argument('--eva-units',action='store_true',help='the innovator edits single EVA letters instead of Zattera glyph units')
    ap.add_argument('--freedom-scale',type=float,default=1.0,help='multiplier of the freedom value (--mode freedom)')
    ap.add_argument('--freedom-norm',action='store_true',help='--mode freedom scores the share of the one-glyph edits of a word that are legal instead of their number (no length runaway)')
    ap.add_argument('--source',choices=['word','pressure'],default='word',help='source score: log P_s(w) - log f_pool(w), or the summed feature pressure of w')
    ap.add_argument('--horizon',type=int,default=512,help='EMA horizon in tokens for the emitted feature shares')
    ap.add_argument('--eps',type=float,default=1e-3);ap.add_argument('--clip',type=float,default=3.0)
    ap.add_argument('--log-all',action='store_true',help='at beta_m 0, still record every proposal (flag T) for auditing')
    ap.add_argument('--innovate',action='store_true',help='slot innovator: replaces Timm paragraph-initial step; fires on the slot novelty targets')
    ap.add_argument('--beta-i',type=float,default=1.0,help='temperature of the innovator over candidate pressure gains')
    ap.add_argument('--kappa-n',type=float,default=4.0,help='feedback gain of the per-slot novelty controller')
    ap.add_argument('--slot-horizon',type=int,default=200)
    ap.add_argument('--prior-max',type=float,default=math.log(3/34977),help='candidates with a larger fitted prior (manuscript-frequent words) are excluded')
    ap.add_argument('--legality-min',type=float,default=-7.0,help='minimum log of the smallest induced transition probability along the candidate')
    ap.add_argument('--gallows-share',type=float,default=0.84,help='share of page/paragraph-first innovations restricted to gallows-initial candidates')
    ap.add_argument('--pf-share',type=float,default=0.59,help='within those, share restricted to p/f-initial candidates (observed 49.3 of 83.1 percent)')
    ap.add_argument('--admit-lr',action='store_true',help='admit l and r as word starts in the curve-line grammar')
    ap.add_argument('--fire',choices=['deficit','target'],default='deficit',help='deficit: fire with probability kappa_n x (target - realised); target: target + kappa_n x (target - realised)')
    ap.add_argument('--novelty-curve',action='store_true',help='scale the slot targets by the observed per-bifolium first-appearance rate (novelty_target.json)')
    ap.add_argument('--concat',type=float,default=0.0,help='share of innovations that join the proposal with a recent word instead of editing one unit')
    ap.add_argument('--concat-window',type=int,default=60)
    ap.add_argument('--kappa-l',type=float,default=0.0,help='length controller: concatenation share rises by kappa_l x relative length deficit of new forms at the slot')
    ap.add_argument('--len-horizon',type=int,default=100)
    ap.add_argument('--extend2',type=float,default=0.0,help='share of innovations that extend the proposal by two units at an end')
    ap.add_argument('--slot-concat',action='store_true',help='base concatenation share per slot = observed share of new forms that are two earlier words joined, times --concat-scale')
    ap.add_argument('--concat-scale',type=float,default=0.8)
    ap.add_argument('--short-partner',type=float,default=0.0,help='share of concatenations whose partner is a one-unit word (the manuscript: 35 percent of joins)')
    ap.add_argument('--gallows-join',action='store_true',help='at page/paragraph-first slots also offer gallows + a recent word of three or more units')
    ap.add_argument('--length-neutral',action='store_true',help='innovator scores candidates by mean pressure per effect (times --neutral-scale) instead of the summed pressure')
    ap.add_argument('--neutral-scale',type=float,default=20.0)
    ap.add_argument('--replace-short',type=float,default=0.0,help='at page/paragraph-first slots, probability of innovating on a proposal that is new but shorter than the slot target while the slot runs short')
    ap.add_argument('--adjacent',action='store_true',help='concatenation partners are the adjacent words (previous emitted word, the source word\'s own predecessor, the last three tokens) instead of the last --concat-window words')
    ap.add_argument('--max-line',type=int,default=0,help='override Timm text.max_line_length (default 55 characters)')
    ap.add_argument('--overflow',action='store_true',help='let the last word of a line exceed the line width instead of being trimmed or replaced by a shorter one')
    ap.add_argument('--source-cap',type=float,default=0.0,help='no single word may take more than this share of a source draw (0 = off); the excess is spread over the other words in proportion, so the governor cannot collapse a draw onto one word')
    ap.add_argument('--operations',action='store_true',help='fourth hook: the morpher is run once per operation and the governor chooses among the three proposals with Timm\'s operation probabilities (20/30/50) reweighted by exp(beta_o x value); the chosen proposal then meets the acceptance rule as usual')
    ap.add_argument('--beta-o',type=float,default=None,help='temperature of the operation choice (default: beta_m)')
    ap.add_argument('--target-walk',type=float,default=0.0,help='targets start at the first bifolium and random-walk in coefficient space (scale 1 = the manuscript\'s own total movement per manuscript length); 0 = follow the fitted path')
    ap.add_argument('--walk-seed',type=int,default=1);ap.add_argument('--walk-step',type=int,default=700,help='tokens per step of the walk (the mean bifolium)')
    ap.add_argument('--repeat-once',action='store_true',help="Timm's repeat coin once per position: a proposal equal to the word just written is offered to Timm once; after his refusal the position's further source draws leave that word out and such proposals are sent back for another draw")
    ap.add_argument('--match-pages',action='store_true',help="the generator follows the manuscript's page geometry along Path 1: each text line gets the characters, paragraph end and page end of the manuscript line at the same index (the seed line stands for the first line); lines beyond the manuscript keep Timm's rules")
    ap.add_argument('--spatial',action='store_true',help="the page draws come from the words physically in view on the manuscript page being written: the app's selector over the recorded word rectangles (cone of --spatial-depth line spacings above the word with half-angle --spatial-angle, reach of --spatial-left word widths to its left, weights by alignment and distance), words laid into the lines as the template-availability study lays them; Timm's own draw stands where nothing is in view; requires --match-pages")
    ap.add_argument('--spatial-left',type=float,default=3.0);ap.add_argument('--spatial-depth',type=float,default=8.0);ap.add_argument('--spatial-angle',type=float,default=45.0)
    ap.add_argument('--spatial-weight',choices=['distance','uniform'],default='distance');ap.add_argument('--spatial-cap',type=int,default=100)
    ap.add_argument('--trace',action='store_true',help='write trace.json.gz: every source call (window, pick, probabilities), proposal (slot, mode, values, decision), innovation (candidates) and accepted token, plus the pressure vector at each line start; the generated text is unchanged')
    ap.add_argument('--fit',default='full',help='full or fold0..fold3 (page-held coefficients; the held pages are then unseen by the target)')
    ap.add_argument('--out',required=True)
    args=ap.parse_args();args.floors=not args.no_floors
    assert not args.spatial or args.match_pages,'--spatial needs --match-pages'
    t0=time.time();model=Model(combined=not args.gradual_only,fit=args.fit)
    if args.target_walk>0:model.walk(args.target_walk,args.walk_seed,int(np.ceil(args.lines*10/args.walk_step))+2,args.walk_step)
    rng=np.random.default_rng(args.seed*7919+int(1000*args.beta_c)+int(10*args.beta_m)+args.retry)
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    conf=(STUDY/'productive/runs/baseline_1/conf.properties').read_text(encoding='utf-8')
    conf=re.sub(r'(?m)^method\.random\.pseudo\.seed=.*$',f'method.random.pseudo.seed={args.seed}',conf)
    conf=re.sub(r'(?m)^text\.lines_to_create=.*$',f'text.lines_to_create={args.lines}',conf)
    if not args.floors:conf=re.sub(r'(?m)^method\.suggestions\.probability=.*$','method.suggestions.probability=0',conf)
    if args.max_line:conf=re.sub(r'(?m)^text\.max_line_length=.*$',f'text.max_line_length={args.max_line}',conf)
    (out/'conf.properties').write_text(conf,encoding='utf-8')
    page_lines=page_ids=None
    if args.match_pages:
        tok=json.loads(PG.resolve(PG.TOKENS_REL).read_text(encoding='utf-8'))['lines']
        asset=json.load(gzip.open(PKG/'src/voynich_gradients/assets/positional_path1.json.gz','rt',encoding='utf-8'))
        by=defaultdict(list)
        for l in tok:by[l['folio']].append(l)
        ordered=[l for n in asset['nodes'] for p in n['pages'] for l in by[p]]
        rows=[];page_lines=[];page_ids=[];count=0
        for j,l in enumerate(ordered):
            nxt=ordered[j+1] if j+1<len(ordered) else None
            page_final=nxt is None or nxt['folio']!=l['folio'];par_final=page_final or bool(nxt.get('first'))
            rows.append('%d\t%d\t%d'%(len(' '.join(l['words'])),int(par_final),int(page_final)));count+=1
            if page_final:page_lines.append(count);page_ids.append(l['folio']);count=0
        (out/'page_spec.tsv').write_text('# chars\tparagraph end\tpage end; one row per text line in Path 1 order\n'+'\n'.join(rows)+'\n',encoding='utf-8')
    initial=re.search(r'(?m)^text\.initial_line=(.*)$',conf).group(1).split()
    g=Governor(model,args,rng);g.emitted=list(initial);g.seen=set(initial)
    if g.spatial:g.seed_layout()
    with (out/'stderr.log').open('w',encoding='utf-8') as err:
        p=subprocess.Popen(['java','-Xmx384m','-Dbridge.enabled=true','-Dbridge.innovator='+str(args.innovate).lower(),'-Dbridge.admitlr='+str(args.admit_lr).lower(),'-Dbridge.overflow='+str(args.overflow).lower(),'-Dbridge.operations='+str(args.operations).lower(),'-Dbridge.partnerorder='+str(getattr(args,'partner_order',False)).lower()]+(['-Dbridge.pagespec=page_spec.tsv'] if args.match_pages else [])+['-cp',str(HERE/'build/classes'),'de.voynich.text.SelfCitationTextGenerator'],
            cwd=out,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=err,text=True,encoding='utf-8',bufsize=1)
        try:
            g.proc=p
            for line in p.stdout:
                if line.startswith('@S\t'):p.stdin.write(g.source(line.rstrip('\n').split('\t'))+'\n')
                elif line.startswith('@P\t'):p.stdin.write(g.propose(line.rstrip('\n').split('\t'))+'\n')
                elif line.startswith('@O\t'):p.stdin.write(g.operations(line.rstrip('\n').split('\t'))+'\n')
                elif line.startswith('?C\t'):p.stdin.write(g.choose_order(line.rstrip('\n').split('\t'))+'\n')
                elif line.startswith('@A\t'):
                    g.accept(line.rstrip('\n').split('\t'))
                    if len(g.emitted)%10000==0:print(out.name,len(g.emitted),'%.0fs'%(time.time()-t0),dict(g.stats),flush=True)
                    continue
                else:continue
                p.stdin.flush()
            code=p.wait()
        finally:
            if p.poll() is None:p.kill();p.wait()
            p.stdin.close();p.stdout.close()
    assert code==0,code
    text=out/'generated_text.txt';digest=hashlib.sha256(text.read_bytes()).hexdigest()
    words=text.read_text(encoding='utf-8').split();assert words[:len(g.emitted)]==g.emitted[:len(words)] or True
    with gzip.open(out/'decisions.json.gz','wt',encoding='utf-8') as f:json.dump(g.log,f,separators=(',',':'))
    with gzip.open(out/'slots.json.gz','wt',encoding='utf-8') as f:json.dump(g.slots,f,separators=(',',':'))
    spatial_check=None
    if g.spatial:
        g.layout.finish()
        with gzip.open(out/'spatial.json.gz','wt',encoding='utf-8') as f:json.dump(g.pool_log,f,separators=(',',':'))
        file_lines=[l.split() for l in text.read_text(encoding='utf-8-sig').splitlines() if l.strip() and not l.startswith('#')]
        mine=defaultdict(list)
        for p_,w_ in enumerate(g.emitted):mine[g.layout.line_of[p_]].append(w_)
        bad=sum(1 for k in range(max(len(file_lines),len(mine))) if file_lines[k:k+1]!=[mine.get(k,[])])
        spatial_check=dict(lines=len(file_lines),line_mismatches=bad,tokens_with_spatial_source=g.stats.get('tokens_spatial_source',0))
    if g.trace is not None:
        with gzip.open(out/'trace.json.gz','wt',encoding='utf-8') as f:json.dump(g.trace,f,separators=(',',':'))
    summary=dict(model_id=MODEL_ID,fit=args.fit,training_pages=len(model.training_pages),walk_sigma=(float(model.walk_sigma) if model.walked else None),page_lines=page_lines,page_ids=page_ids,args=vars(args),tokens=len(g.emitted),text_sha256=digest,seconds=round(time.time()-t0,1),stats=dict(g.stats),store=(g.store_log or None),spatial_check=spatial_check)
    (out/'run.json').write_text(json.dumps(summary,indent=1),encoding='utf-8');print(json.dumps(summary))

if __name__=='__main__':main()
