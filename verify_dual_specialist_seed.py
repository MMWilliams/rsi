"""Reproduce the audited mixed-bank confidence choices from public inputs only."""
from __future__ import annotations

import hashlib
import json

from rsi.common import ROOT,write_json
from dual_specialist_seed_evaluator import FAMILIAR,SHIFTED,load_models,select


RUN=ROOT/'runs/dual-specialist-integration-transfer-20260918'
OUT=ROOT/'analysis/dual-specialist-seed-equivalence-20260918.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUT.exists():raise RuntimeError('verification exists')
    assert json.loads((RUN/'audit.json').read_text())['passed']
    tasks=json.loads((RUN/'sealed_bank.json').read_text())
    wide=json.loads((RUN/'ast_wide_pools.json').read_text())
    records=json.loads((RUN/'frozen_records.json').read_text())
    models=load_models()
    count=0;cost=0;experts={'familiar':0,'shifted':0}
    for task,record in zip(tasks,records):
        public={'id':task['id'],'visible':task['visible']}
        selected=select(public,wide[task['id']],record,models)
        assert selected['index']==record['dual_choices']['confidence']
        assert selected['program']==wide[task['id']][selected['index']]['program']
        count+=1;cost+=selected['candidate_scores']
        experts[selected['expert']]+=1
    result={'passed':True,'choices_reproduced':count,
            'public_task_fields':['id','visible'],
            'candidate_scores':cost,'selected_experts':experts,
            'source_audit_sha256':sha(RUN/'audit.json'),
            'familiar_model_sha256':sha(FAMILIAR),
            'shifted_model_sha256':sha(SHIFTED)}
    write_json(OUT,result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
