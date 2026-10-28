"""Portable current-model arrays with explicit axes, units and provenance."""
from functools import lru_cache
import gzip,hashlib,json
from pathlib import Path
import numpy as np


class Bundle:
    def __init__(self,directory=None):
        self.directory=Path(directory) if directory else Path(__file__).parent/'assets'

    @lru_cache(maxsize=6)
    def read(self,name):
        manifest=json.loads((self.directory/'manifest.json').read_text(encoding='utf-8'))
        if name=='catalog' and 'raw_catalog' in manifest['assets']:
            raw=self.read('raw_catalog');d=self.current()
            return dict(model_id=d['model_id'],components=d['features'],words=[dict(a,**b) for a,b in zip(raw['words'],d['words'])])
        if name not in manifest['assets']:
            raise KeyError(f'{name!r} is not a current asset; use current(), component_matrix(), transition_matrix() or pair().')
        filename=manifest['assets'][name]['file'];path=self.directory/filename
        if filename.endswith('.gz'):
            with gzip.open(path,'rt',encoding='utf-8') as f:return json.load(f)
        return json.loads(path.read_text(encoding='utf-8'))

    def verify(self):
        m=json.loads((self.directory/'manifest.json').read_text(encoding='utf-8'))
        bad=[k for k,v in m['assets'].items() if hashlib.sha256((self.directory/v['file']).read_bytes()).hexdigest()!=v['sha256']]
        if bad:raise ValueError(f'Asset checksum mismatch: {bad}')
        return dict(verified_assets=len(m['assets']),version=m['version'],model_id=m['model_id'])

    def current(self,path=1):return self.read(f'positional_path{path}')

    def axes(self,path=1):return self.read('axes')['paths'][str(path)]

    def component_index(self,name,path=1):
        hits=[i for i,f in enumerate(self.current(path)['features']) if name in (f['id'],f['name']) or name in [a['name'] for a in f['aliases']]]
        if len(hits)!=1:raise KeyError(f'Expected one component for {name!r}; found {len(hits)}')
        return hits[0]

    def component(self,name,path=1):
        i=self.component_index(name,path);d=self.current(path)
        return dict(model_id=d['model_id'],definition=d['features'][i],trajectory={k:v[i] for k,v in d['matrices'].items()},axes=self.axes(path))

    def component_matrix(self,field='gradual_change',path=1):
        d=self.current(path);aliases={'gradual_level':'gradual','combined_level':'combined','jump_level':'jump','observed_rate':'observed'}
        field=aliases.get(field,field);axis='boundaries' if field.endswith('_change') else 'nodes'
        units='rate per path arc' if field=='slope' else 'log weight per path arc' if field=='coefficient_slope' else 'log weight' if field=='coefficient' else 'tokens' if field=='counts' else 'per 10000 tokens'
        return dict(model_id=d['model_id'],values=np.asarray(d['matrices'][field]),row_ids=[r['id'] for r in d['features']],
                    columns=self.axes(path)[axis],axis=axis,units=units,active=[r['active'] for r in d['features']])

    def transition_matrix(self,field='conditional_delta',path=1):
        d=self.current(path);t=d['transitions'];v=np.asarray(t['gradual' if field=='conditional_delta' else field]);axis=d['nodes']
        if field=='conditional_delta':v=np.diff(v,axis=0);axis=self.axes(path)['boundaries']
        return dict(model_id=d['model_id'],values=v,rows=t['rows'],columns=t['columns'],time=axis,
                    units='conditional probability per path arc' if field=='slope' else 'conditional probability')

    def word(self,spelling,path=1):
        d=self.current(path);i=next((i for i,w in enumerate(d['words']) if w['word']==spelling),None)
        if i is None:raise KeyError(spelling)
        return dict(d['words'][i],model_id=d['model_id'],counts=d['word_counts'][i],gradual=d['word_gradual'][i],
                    combined=d['word_combined'][i],component_ids=[d['features'][j]['id'] for j in d['words'][i]['components']])

    def pair(self,a,b,path=1):
        ia,ib=self.component_index(a,path),self.component_index(b,path);d=self.current(path)
        A=set(d['features'][ia]['members']);B=set(d['features'][ib]['members'])
        labels=np.array([2*(i in A)+(i in B) for i in range(len(d['words']))]);fields={}
        for label,key in [('counts','word_counts'),('gradual','word_gradual'),('combined','word_combined')]:
            v=np.asarray(d[key]);fields[label]=np.array([v[labels==j].sum(0) for j in range(4)]).T.tolist()
        return dict(model_id=d['model_id'],a=d['features'][ia]['name'],b=d['features'][ib]['name'],cohort_order=['neither','b_only','a_only','both'],
                    **fields,joint_word_ids=sorted(A&B),identifiable=bool(A-B and B-A and A&B),tested=False,
                    note='Four-cohort predictions of the joint positional model. Descriptive conditional behavior, not the archived five-model interaction test.')

    def partition(self,parent,child,path=1):
        a,b=self.component_index(parent,path),self.component_index(child,path);d=self.current(path)
        A=set(d['features'][a]['members']);B=set(d['features'][b]['members'])
        if not B<A:raise ValueError('Child must be a proper subset of parent')
        ca=np.asarray(d['matrices']['counts'][a]);cb=np.asarray(d['matrices']['counts'][b]);pa=np.asarray(d['matrices']['gradual'][a]);pb=np.asarray(d['matrices']['gradual'][b])
        return dict(model_id=d['model_id'],observed_share=np.divide(cb,ca,out=np.full_like(cb,np.nan),where=ca>0),
                    gradual_share=pb/pa,remainder=pa-pb,conditional_on='Joint positional model; no separate conditional spline refit')

    def chronology(self,path=1,early_a=False):
        d=self.current(path);idx=[i for i,n in enumerate(d['nodes']) if not early_a or n['group'] in ('1a','1b','1.5a','2a')]
        return dict(d['chronology'],model_id=d['model_id'],nodes=d['nodes'],partitions=d['partitions'],selected_node_indices=idx)

    def gradient_contribution(self,name,path=1):
        i=self.component_index(name,path);d=self.current(path)
        return dict(model_id=d['model_id'],component_id=d['features'][i]['id'],own_log_weight=d['matrices']['coefficient'][i],
                    own_log_slope=d['matrices']['coefficient_slope'][i],carrier_rate_slope=d['matrices']['slope'][i],axis=d['nodes'],
                    interpretation='Own coefficients and total carrier response are separate; total includes all overlapping effects and probability normalization.')
