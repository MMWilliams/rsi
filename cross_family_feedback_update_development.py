"""Inspected pilot: does new cross-family feedback improve the allocator?"""
from __future__ import annotations

import json

import numpy as np

from rsi.common import ROOT,write_json
from seed_casebanks import FAMILIES
from ast_query_allocation_development import fit,predict
from cross_family_query_value_development import rows_for,matrix,choose
from cross_family_query_transfer import DEST,model_values


OUT=ROOT/'analysis/cross-family-feedback-update-development.json'


def panel_rows(panel):
    directory=DEST/panel
    records=json.loads((directory/'frozen_records.json').read_text())
    results=json.loads((directory/'results.json').read_text())['tasks']
    assert all(a['id']==b['id'] for a,b in zip(records,results))
    return [{'id':r['id'],'seed':r['seed'],'family':r['family'],
             'features':r['features'],'zero':int(o['zero']),'one':int(o['one']),
             'gain':int(o['one'])-int(o['zero'])} for r,o in zip(records,results)]


def model(rows):
    x=matrix(rows,'interaction')
    y=np.asarray([r['gain'] for r in rows],float)
    params=fit(x,y,np.zeros(len(y)),100.)
    return {'kind':'interaction','penalty':100.,
            'params':[v.tolist() for v in params]}


def main():
    if OUT.exists():raise RuntimeError('development output exists')
    source=rows_for();admission=panel_rows('a');target=panel_rows('b')
    assert len(source)==576 and len(admission)==len(target)==288
    old=json.loads((DEST/'frozen_models.json').read_text())['interaction_100']
    assert model(source)==old
    full=source+admission
    scrambled=[dict(r) for r in admission]
    for family in FAMILIES:
        idx=[i for i,r in enumerate(admission) if r['family']==family]
        for target_i,source_i in zip(idx,idx[-1:]+idx[:-1]):
            scrambled[target_i]={**scrambled[target_i],
                                  'gain':admission[source_i]['gain']}
    variants={'old':old,'updated':model(full),
              'scrambled_update':model(source+scrambled),
              'duplicate_source':model(source+source[:288])}
    frozen=json.loads((DEST/'b/frozen_allocations.json').read_text())
    banks=[]
    predictions={name:model_values(v,target) for name,v in variants.items()}
    by_id={r['id']:i for i,r in enumerate(target)}
    for seed in sorted({r['seed'] for r in target}):
        group=[r for r in target if r['seed']==seed]
        idx=[by_id[r['id']] for r in group]
        scores={}
        for name,values in predictions.items():
            picked=choose(group,name,values[idx])
            scores[name]=sum(r['one'] if r['id'] in picked else r['zero'] for r in group)
            if name=='old':assert picked==set(frozen[str(seed)]['interaction_100'])
        selected=set(frozen[str(seed)]['transform_mutation'])
        scores['fixed_transform_mutation']=sum(r['one'] if r['id'] in selected else r['zero']
                                                for r in group)
        banks.append({'seed':seed,'correct':scores})
    y=np.asarray([r['gain'] for r in target],float)
    report={'scope':'inspected update pilot; panel B labels were already open',
            'source_tasks':len(source),'new_admission_tasks':len(admission),
            'target_tasks':len(target),
            'correct':{name:sum(b['correct'][name] for b in banks)
                       for name in (*variants,'fixed_transform_mutation')},
            'gain_brier':{name:float(np.mean((np.clip(v,0,1)-y)**2))
                          for name,v in predictions.items()},
            'by_bank':banks}
    write_json(OUT,report)
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
