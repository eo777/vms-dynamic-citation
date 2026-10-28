"""Same-token nonlinear and page-relative associations; no future-block outcome.

All candidate predictors precede N in lexical content. Source geometry remains
the app's retrospective geometry. Vocabulary controls are a sensitivity tier.
"""
from pathlib import Path
import gzip,json,warnings
import numpy as np
import pandas as pd
from sklearn.preprocessing import OneHotEncoder,SplineTransformer,StandardScaler
from sklearn.linear_model import Ridge
from sklearn.model_selection import GroupKFold,LeaveOneGroupOut

HERE=Path(__file__).resolve().parent
OUTCOMES=['app_impact','additive_burden','arrival_burden']
METRICS=['components','h1','h2','relative_components','relative_h1','relative_h2']
TIERS={'section':[],
       'position':['log_page_tokens','log_line_position','line_initial','paragraph_initial'],
       'pool':['log_page_tokens','log_line_position','line_initial','paragraph_initial','log_n','log_ess'],
       'vocabulary':['log_page_tokens','log_line_position','line_initial','paragraph_initial','log_n','log_ess','prior_ttr','prior_red','worddiv','log_prior_components']}
CANDIDATES={'baseline':([],False),
    'components_linear':(['components'],False),'components_curve':(['components'],True),
    'relative_components_linear':(['relative_components'],False),'relative_components_curve':(['relative_components'],True),
    'h1_linear':(['h1'],False),'h1_curve':(['h1'],True),'relative_h1_curve':(['relative_h1'],True),
    'h2_linear':(['h2'],False),'h2_curve':(['h2'],True),'relative_h2_curve':(['relative_h2'],True),
    'all_metrics_curve':(['components','h1','h2'],True)}
RNG=np.random.default_rng(2026102702)

def clean(x):
    if isinstance(x,dict):return {str(k):clean(v) for k,v in x.items()}
    if isinstance(x,(list,tuple,np.ndarray)):return [clean(v) for v in x]
    if isinstance(x,(np.integer,)):return int(x)
    if isinstance(x,(np.bool_,)):return bool(x)
    if isinstance(x,(float,np.floating)):return float(x) if np.isfinite(x) else None
    return x

def prepare():
    raw=json.load(gzip.open(HERE/'derived.json.gz','rt',encoding='utf8'));a=pd.DataFrame(raw['rows'])
    for new,old in [('log_page_tokens','prior_page_tokens'),('log_line_position','word_in_line'),('log_n','n'),('log_ess','pair_ess')]:a[new]=np.log1p(a[old])
    a['log_prior_components']=np.log2(a.prior_components)
    a['eligible']=a.full_impact_support&a[METRICS+TIERS['vocabulary']].notna().all(axis=1)
    return raw,a,a[a.eligible].copy().reset_index(drop=True)

def features(train,test,columns,curve):
    if not columns:return np.empty((len(train),0)),np.empty((len(test),0))
    if curve:
        transform=SplineTransformer(n_knots=5,degree=3,knots='quantile',include_bias=False,extrapolation='linear')
        return transform.fit_transform(train[columns]),transform.transform(test[columns])
    return train[columns].to_numpy(float),test[columns].to_numpy(float)

def interval_difference(g,metric,outcome):
    lo,hi=g[metric].quantile([.2,.8]);low=g[g[metric]<=lo];high=g[g[metric]>=hi]
    ids=sorted(g.bifolium.unique());v=[]
    for group in ids:
        l=low[low.bifolium==group][outcome];h=high[high.bifolium==group][outcome]
        v.append([l.sum(),len(l),h.sum(),len(h)])
    v=np.array(v);draw=RNG.integers(0,len(ids),(2000,len(ids)));t=v[draw].sum(1)
    valid=(t[:,1]>0)&(t[:,3]>0);diff=t[valid,0]/t[valid,1]-t[valid,2]/t[valid,3]
    return {'low_mean':low[outcome].mean(),'high_mean':high[outcome].mean(),'difference':low[outcome].mean()-high[outcome].mean(),
            'ci95':np.quantile(diff,[.025,.975]) if len(ids)>=3 else None,'groups':len(ids)}

def descriptive(d):
    result={}
    for region,g in [('all',d)]+list(d.groupby('section',sort=False)):
        r={'n':len(g),'bifolia':g.bifolium.nunique(),'pages':g.page.nunique(),'means':g[OUTCOMES].mean().to_dict(),'metrics':{}}
        for metric in METRICS:
            cuts=np.unique(g[metric].quantile(np.linspace(0,1,11)));q=np.searchsorted(cuts[1:-1],g[metric],side='right')
            curve=[]
            for k in np.unique(q):
                z=g[q==k];curve.append({'x':z[metric].mean(),'n':len(z),**z[OUTCOMES].mean().to_dict()})
            r['metrics'][metric]={'quantiles':g[metric].quantile([.05,.2,.5,.8,.95]).to_list(),'curve':curve,
                'contrasts':{y:interval_difference(g,metric,y) for y in OUTCOMES}}
        result[region]=r
    return result

def cv(d,bio_only=False):
    y=d[OUTCOMES].to_numpy();groups=d.bifolium.to_numpy()
    names=[f'{tier}/{c}' for tier in TIERS for c in CANDIDATES]
    preds={name:np.full_like(y,np.nan) for name in names};folds=[];all_warnings=[]
    splitter=LeaveOneGroupOut() if bio_only else GroupKFold(n_splits=5)
    for fold,(tr,te) in enumerate(splitter.split(d,groups=groups)):
        train,test=d.iloc[tr],d.iloc[te]
        assert not set(train.bifolium)&set(test.bifolium)
        enc=OneHotEncoder(handle_unknown='ignore',sparse_output=False)
        section_a=enc.fit_transform(train[['section']]);section_b=enc.transform(test[['section']])
        candidates={c:features(train,test,*setting) for c,setting in CANDIDATES.items()}
        for tier,columns in TIERS.items():
            binary=[c for c in columns if c in ['line_initial','paragraph_initial']];continuous=[c for c in columns if c not in binary]
            u,v=features(train,test,continuous,True);ba,bb=features(train,test,binary,False)
            sa=section_a if tier!='global' else np.empty((len(train),0))
            sb=section_b if tier!='global' else np.empty((len(test),0))
            a=np.column_stack([sa,u,ba]);b=np.column_stack([sb,v,bb])
            for candidate,(ca,cb) in candidates.items():
                # Constant feature permits a global-intercept-only baseline.
                scale=StandardScaler();x=scale.fit_transform(np.column_stack([np.ones(len(train)),a,ca]));z=scale.transform(np.column_stack([np.ones(len(test)),b,cb]))
                with warnings.catch_warnings(record=True) as ws:
                    model=Ridge(alpha=10).fit(x,y[tr]);p=model.predict(z)
                all_warnings.extend(str(w.message) for w in ws)
                preds[f'{tier}/{candidate}'][te]=np.clip(p,0,1)
        folds.append({'fold':fold,'held_out_bifolia':sorted(test.bifolium.unique()),'n_test':len(te)})
        print('CV','Bio' if bio_only else 'all',fold+1,flush=True)
    scores={}
    for region,mask in [('all',np.ones(len(d),bool))]+[(s,d.section.to_numpy()==s) for s in d.section.unique()]:
        code,unique=pd.factorize(groups[mask]);counts=np.bincount(code)
        draws=RNG.integers(0,len(unique),(2000,len(unique)))
        scores[region]={'n':int(mask.sum()),'bifolia':len(unique),'outcomes':{}}
        for j,outcome in enumerate(OUTCOMES):
            errors={name:(y[mask,j]-p[mask,j])**2 for name,p in preds.items()};stats={}
            for name,error in errors.items():
                tier,candidate=name.split('/');base=errors[tier+'/baseline'];improvement=base-error
                sums=np.bincount(code,weights=improvement);bs=np.bincount(code,weights=base)
                bootstrap=100*sums[draws].sum(1)/bs[draws].sum(1)
                entry={'rmse':float(np.sqrt(error.mean())),'mse':float(error.mean()),
                    'improvement_percent':100*improvement.mean()/base.mean(),
                    'improvement_ci95':np.quantile(bootstrap,[.025,.975]) if len(unique)>=3 else None}
                if candidate.endswith('_curve') and candidate[:-6]+'_linear' in CANDIDATES:
                    linear=errors[tier+'/'+candidate[:-6]+'_linear'];delta=linear-error
                    ds=np.bincount(code,weights=delta);ls=np.bincount(code,weights=linear)
                    nonlinear=100*ds[draws].sum(1)/ls[draws].sum(1)
                    entry['versus_linear_percent']=100*delta.mean()/linear.mean()
                    entry['versus_linear_ci95']=np.quantile(nonlinear,[.025,.975]) if len(unique)>=3 else None
                stats[name]=entry
            scores[region]['outcomes'][outcome]=stats
    # Retain only per-bifolium averages, never the full predictions.
    summaries=[]
    for bif,g in d.groupby('bifolium',sort=False):
        idx=g.index.to_numpy();entry={'bifolium':bif,'section':g.section.iloc[0],'n':len(g),'observed':g[OUTCOMES].mean().to_dict(),'predictions':{}}
        for name,p in preds.items():entry['predictions'][name]=dict(zip(OUTCOMES,p[idx].mean(axis=0)))
        summaries.append(entry)
    return {'folds':folds,'scores':scores,'bifolium_means':summaries,'warnings':sorted(set(all_warnings))}

def main():
    raw,a,d=prepare();print('Cohort',len(d),'bifolia',d.bifolium.nunique(),'sections',d.section.value_counts().to_dict(),flush=True)
    results={'settings':raw['settings'],'cohort':{'n':len(d),'bifolia':d.bifolium.nunique(),'pages':d.page.nunique(),
       'rule':'All three source metrics valid, 20 earlier valid page scores, complete 100 containing windows within same bifolium, history controls available.'},
       'tiers':TIERS,'candidates':CANDIDATES,'outcomes':OUTCOMES,'descriptive':descriptive(d),
       'metric_correlation':d[METRICS].corr().to_dict()}
    (HERE/'metrics.json').write_text(json.dumps(clean(results),indent=2)+'\n',encoding='utf8')
    results['cv']=cv(d)
    results['bio_cv']=cv(d[d.section=='4a'].copy().reset_index(drop=True),bio_only=True)
    (HERE/'metrics.json').write_text(json.dumps(clean(results),indent=2)+'\n',encoding='utf8')
    for region in ['all','3c','4a']:
        z=results['cv']['scores'][region]['outcomes']['app_impact']
        print(region,json.dumps(clean({name:stats for name,stats in z.items() if name.startswith('section/') or name in ['pool/components_curve','vocabulary/components_curve']})),flush=True)

if __name__=='__main__':main()
