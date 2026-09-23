"""Prove the trained family feature is redundant with visible Unicode block."""
from __future__ import annotations

import json

import numpy as np

from rsi.common import ROOT,write_json
from gated_ast_feedback import public_block
from ast_query_allocation_development import fit,predict
from cross_family_query_value_development import rows_for,choose
from cross_family_query_transfer import DEST,PANELS,LEARNED


BLOCKS=(0x700,0x800,0x900,0xA00,0xC00,0xD00)
SOURCE_TASKS=(ROOT/'runs/full-mixed-ast-sensor-20260918/sealed_bank.json',
              ROOT/'runs/cross-component-mixed-transfer-20260918/sealed_bank.json')


def matrix(rows,kind):
    base=np.asarray([r['features'] for r in rows],float)
    onehot=np.asarray([[float(r['public_block']==b) for b in BLOCKS] for r in rows])
    if kind=='basic':return base
    if kind=='family':return np.c_[base,onehot]
    if kind=='interaction':
        cross=np.einsum('ni,nj->nij',onehot,base[:,2:10]).reshape(len(rows),-1)
        return np.c_[base,onehot,cross]
    raise ValueError(kind)


def main():
    if (DEST/'audit_public_features.json').exists():
        raise RuntimeError('public feature audit already exists')
    source=rows_for();task_lookup={}
    for path in SOURCE_TASKS:
        for task in json.loads(path.read_text()):
            assert task['id'] not in task_lookup
            task_lookup[task['id']]=task
    assert len(task_lookup)==576
    family_to_block={};block_to_family={}
    for row in source:
        block=public_block(task_lookup[row['id']]);row['public_block']=block
        family=row['family']
        family_to_block.setdefault(family,set()).add(block)
        block_to_family.setdefault(block,set()).add(family)
    frozen=json.loads((DEST/'frozen_models.json').read_text())
    y=np.asarray([r['gain'] for r in source],float)
    for name in LEARNED:
        if name=='family_mean':
            rates={str(b):(sum(r['gain'] for r in source if r['public_block']==b)+1)/
                           (sum(r['public_block']==b for r in source)+2)
                   for b in BLOCKS}
            for family,block_set in family_to_block.items():
                block=next(iter(block_set))
                assert rates[str(block)]==frozen[name]['rates'][family]
        else:
            kind,penalty=name.rsplit('_',1)
            model=fit(matrix(source,kind),y,np.zeros(len(y)),float(penalty))
            original=tuple(np.asarray(v,float) for v in frozen[name]['params'])
            assert all(np.allclose(a,b,atol=1e-10) for a,b in zip(model,original))
    allocations=0;tasks=0
    for panel in PANELS:
        directory=DEST/panel
        panel_tasks=json.loads((directory/'sealed_bank.json').read_text())
        records=json.loads((directory/'frozen_records.json').read_text())
        frozen_alloc=json.loads((directory/'frozen_allocations.json').read_text())
        assert all(t['id']==r['id'] for t,r in zip(panel_tasks,records))
        for task,record in zip(panel_tasks,records):
            assert record['public_block']==public_block(task)
            assert family_to_block[record['family']]=={record['public_block']}
        tasks+=len(records)
        for seed,mappings in frozen_alloc.items():
            group=[r for r in records if str(r['seed'])==seed]
            assert len(group)==48
            for name in LEARNED:
                model=frozen[name]
                if name=='family_mean':
                    values=np.asarray([model['rates'][next(iter(block_to_family[r['public_block']]))]
                                       for r in group])
                else:
                    params=tuple(np.asarray(v,float) for v in model['params'])
                    values=predict(params,matrix(group,model['kind']))[0]
                selected=choose(group,name,values)
                assert selected==set(mappings[name])
                allocations+=1
    result={'passed':True,'source_tasks':len(source),'target_tasks':tasks,
            'learned_allocations_reconstructed_from_public_block':allocations,
            'family_to_visible_block':{family:hex(next(iter(blocks)))
                                       for family,blocks in family_to_block.items()}}
    write_json(DEST/'audit_public_features.json',result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
