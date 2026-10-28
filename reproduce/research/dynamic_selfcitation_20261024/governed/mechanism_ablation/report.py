"""Summarize controlled changes without selecting on a single aggregate score."""
from collections import Counter
import gzip
import json
import math
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'apps/selfcitation_governor'))
from comparison_runs import APP,GOV,read,catalog
import comparison_metrics as cm

METRICS=('component','mattr','types','births','cumulative','h1','h2','word_h1','word_h2','word_order_gain','pair_excess','degenerate')
CONTRASTS=[
 ('editor_visible','editor_stable','Stable insertion/substitution repertoire'),
 ('editor_visible','editor_visible_uniform','Uniform visible-unit draw instead of donor-weighted units'),
 ('editor_visible_uniform','editor_stable','Stable repertoire instead of uniform visible repertoire'),
 ('editor_visible_uniform','editor_local_pages','Bounded hybrid: visible page grammar plus removal of recent-use penalty'),
 ('editor_local_pages','editor_local_sheet','Same bounded local editor: same bifolium instead of two pages'),
 ('editor_visible','editor_visible_filter','Add learned transition constraint to visible editor'),
 ('editor_stable','editor_stable_filter','Add learned transition constraint to stable editor'),
 ('wide_native','wide_fixed','Learned transition constraint in wide kernel'),
 ('wide_fixed','wide_visible','Restrict wide alphabet to visible units'),
 ('wide_fixed','wide_unseen','Require globally unseen output'),
 ('wide_unseen','wide_feedback','Deficit feedback instead of fixed attempts; same unseen filter'),
 ('wide_fixed','wide_no_repel','Remove recent-use penalty'),
 ('wide_fixed','wide_no_timm','Replace native morph output by the copied source'),
 ('wide_fixed','wide_no_rarity','Remove manuscript word-rarity filter'),
 ('wide_no_rarity','wide_local','Use visible-word adjacency grammar instead of manuscript transitions'),
 ('wide_local','wide_local_copy','Local grammar: replace native morph output by copy'),
 ('wide_local','wide_local_no_repel','Local grammar: remove recent-use penalty'),
 ('wide_local','wide_page_grammar','Learn grammar from actual written forms instead of stripped donors'),
 ('wide_page_grammar','wide_page_no_repel','Full visible-page grammar: remove recent-use penalty'),
 ('wide_page_grammar','wide_page_copy','Full visible-page grammar: replace native morph output by copy'),
 ('wide_page_grammar','sheet_page_grammar','Full visible-page grammar: same bifolium instead of two pages'),
 ('sheet_page_grammar','sheet_page_no_repel','Same bifolium and full-page grammar: remove recent-use penalty'),
 ('wide_page_no_repel','wide_pattern_memory','Remember encountered glyph joins across page changes'),
 ('sheet_page_no_repel','sheet_pattern_memory','Same bifolium: remember glyph joins, not off-sheet words'),
 ('sheet_local','sheet_local_no_repel','Same bifolium and local grammar: remove recent-use penalty'),
 ('wide_fixed','wide_slow','Reduce fixed attempt probability from .35 to .10'),
 ('wide_fixed','wide_fast','Increase fixed attempt probability from .35 to .70'),
 ('page_fixed','wide_fixed','Permit the preceding page as well as current page'),
 ('wide_fixed','sheet_fixed','Same-bifolium reserve instead of current + preceding page'),
 ('wide_feedback','sheet_feedback','Same-bifolium reserve under feedback'),
 ('editor_stable_filter','sheet_editor','Same-bifolium reserve with bounded editor'),
 ('wide_local','sheet_local','Same-bifolium reserve with local grammar'),
 ('wide_local_copy','sheet_local_copy','Same-bifolium reserve with local grammar and copying')]


def main():
    index=read(APP/'data/comparison_index.json.gz');nodes=index['nodes'];obs=read(APP/'data/comparison_runs/observed.json.gz')
    result=dict(definition='Token-weighted mean of matched bifolium estimates. Mean absolute errors are computed before averaging seeds. Seed 1 screens; seeds 2/3 are replication.',scopes={},runs={},references={},contrasts=[],observed_whole=obs['whole'])
    scopes={g:[i for i,n in enumerate(nodes) if g=='all' or (g=='nonbio' and n['group']!='4a') or n['group']==g] for g in ('all','nonbio','1a','4a')}
    def avg(v,ids):return sum(v[i]*nodes[i]['N'] for i in ids)/sum(nodes[i]['N'] for i in ids)
    for scope,ids in scopes.items():result['scopes'][scope]=dict(tokens=sum(nodes[i]['N'] for i in ids),observed={k:avg(obs['series'][k],ids) for k in METRICS},word_pooled=obs['word_entropy_regions'][scope])
    records=[]
    for filename in ('initial_results.json.gz','results.json.gz','local_results.json.gz','combined_results.json.gz','page_grammar_results.json.gz','pattern_results.json.gz','uniform_results.json.gz','bounded_results.json.gz','replication.json.gz','replication_page.json.gz'):
        p=HERE/filename
        if p.exists():records.extend(read(p))
    records=list({(r['condition'],r['seed']):r for r in records}.values())
    retired=read(HERE/'retired_text_audit.json.gz') if (HERE/'retired_text_audit.json.gz').exists() else {}
    for name in dict.fromkeys(r['condition'] for r in records):
        rs=sorted((r for r in records if r['condition']==name and r['status']=='complete'),key=lambda r:r['seed'])
        if not rs:continue
        packs=[read(APP/'data/comparison_runs'/f"{r['key']}.json.gz") for r in rs]
        row=dict(seeds=[r['seed'] for r in rs],settings=rs[0]['variant'],scopes={},word_pooled={},remembered_transitions=[r['audit']['intervals'][-1]['audit'].get('remembered_transitions',0) for r in rs])
        row['whole']={k:[p['whole'][k] for p in packs] for k in ('types','degenerate_share','short_share')}
        row['minimum_d50']=[p['degeneracy']['min'] for p in packs]
        for scope,ids in scopes.items():
            row['scopes'][scope]={}
            for k in METRICS:
                values=[avg(p['series'][k],ids) for p in packs];errors=[avg([abs(a-b) for a,b in zip(p['series'][k],obs['series'][k])],ids) for p in packs]
                row['scopes'][scope][k]=dict(mean=sum(values)/len(values),values=values,min=min(values),max=max(values),mae=sum(errors)/len(errors),errors=errors)
            carriers=[]
            for r in rs:
                if r['key'] in retired:
                    carriers.append(retired[r['key']]['n_words_pct'][scope]);continue
                c=read(HERE/'streams'/f"{r['key']}.json.gz");words=[w for line in c['lines'] for w in line]
                carriers.append(100*sum('n' in w for i in ids for w in words[nodes[i]['start']:nodes[i]['end']])/sum(nodes[i]['N'] for i in ids))
            row['scopes'][scope]['n_words_pct']=dict(mean=sum(carriers)/len(carriers),values=carriers,min=min(carriers),max=max(carriers))
            row['word_pooled'][scope]={k:[p['word_entropy_regions'][scope][k] for p in packs] for k in packs[0]['word_entropy_regions'][scope]}
        result['runs'][name]=row
    for a,b,title in CONTRASTS:
        if a not in result['runs'] or b not in result['runs']:continue
        A=result['runs'][a];B=result['runs'][b];seeds=sorted(set(A['seeds'])&set(B['seeds']))
        deltas={}
        for k in METRICS:
            vs=[B['scopes']['nonbio'][k]['values'][B['seeds'].index(s)]-A['scopes']['nonbio'][k]['values'][A['seeds'].index(s)] for s in seeds]
            es=[B['scopes']['nonbio'][k]['errors'][B['seeds'].index(s)]-A['scopes']['nonbio'][k]['errors'][A['seeds'].index(s)] for s in seeds]
            deltas[k]=dict(values=vs,mean=sum(vs)/len(vs),error_delta=sum(es)/len(es),error_deltas=es)
        result['contrasts'].append(dict(a=a,b=b,title=title,seeds=seeds,deltas=deltas))
    # Attribute the observed H1 change to symbol-frequency contributions,
    # without retaining per-run glyph or bigram distributions.
    contributions={}
    for name in ('editor_visible','editor_visible_uniform','editor_stable'):
        if name not in result['runs']:continue
        for seed in result['runs'][name]['seeds']:
            if f'ab_{name}_s{seed}' in retired:
                contributions[name,seed]=Counter(retired[f'ab_{name}_s{seed}']['h1_contributions']);continue
            c=read(HERE/'streams'/f'ab_{name}_s{seed}.json.gz');words=[w for line in c['lines'] for w in line];values=Counter()
            for i in scopes['nonbio']:
                n=nodes[i];counts=Counter(' '.join(words[n['start']:n['end']]));total=sum(counts.values())
                for symbol,count in counts.items():
                    p=count/total;values[symbol]+=-p*math.log2(p)*n['N']/result['scopes']['nonbio']['tokens']
            contributions[name,seed]=values
    for c in result['contrasts']:
        if (c['a'],c['seeds'][0]) not in contributions or (c['b'],c['seeds'][0]) not in contributions:continue
        symbols=set().union(*(set(contributions[name,seed]) for name in (c['a'],c['b']) for seed in c['seeds']))
        c['h1_symbol_contributions']={symbol:sum(contributions[c['b'],seed][symbol]-contributions[c['a'],seed][symbol] for seed in c['seeds'])/len(c['seeds']) for symbol in sorted(symbols)}
        assert abs(sum(c['h1_symbol_contributions'].values())-c['deltas']['h1']['mean'])<1.1e-6
    reference_ids={'timm','governed','noinnov_memory','exp_spread_native','exp_spread_edit_low','exp_spread_edit_tokens','exp_previous25_edit','exp_sheet_base','exp_current_ops'}
    for run in catalog():
        if run['id'] not in reference_ids:continue
        packs=[read(APP/'data/comparison_runs'/f"{r['key']}.json.gz") for r in run['records']]
        row=dict(label=run['label'],seeds=[r['seed'] for r in run['records']],scopes={},word_pooled={},whole={k:[p['whole'][k] for p in packs] for k in ('types','degenerate_share','short_share')})
        for scope,ids in scopes.items():
            row['scopes'][scope]={}
            for k in METRICS:
                available=[p for p in packs if k in p['series']]
                if not available:continue
                values=[avg(p['series'][k],ids) for p in available];errors=[avg([abs(a-b) for a,b in zip(p['series'][k],obs['series'][k])],ids) for p in available]
                row['scopes'][scope][k]=dict(mean=sum(values)/len(values),values=values,min=min(values),max=max(values),mae=sum(errors)/len(errors),errors=errors,scored_seeds=len(available))
            available=[p for p in packs if 'word_entropy_regions' in p]
            if available:row['word_pooled'][scope]={k:[p['word_entropy_regions'][scope][k] for p in available] for k in available[0]['word_entropy_regions'][scope]}
        result['references'][run['id']]=row
    cm.b.dump(result,APP/'data/mechanism_study.json.gz')
    print('Outside 4a: method, seeds, MATTR, births/1000, H1, H2, n-carriers%, component MAE, word-order gain')
    for name,r in result['runs'].items():
        p=r['scopes']['nonbio'];print(name,r['seeds'],*[round(p[k]['mean'],4) for k in ('mattr','births','h1','h2','n_words_pct','component','word_order_gain')])
    print('MS',*[round(result['scopes']['nonbio']['observed'][k],4) for k in ('mattr','births','h1','h2','component','word_order_gain')])


if __name__=='__main__':main()
