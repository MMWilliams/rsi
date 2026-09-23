"""Functional public-only reconstruction of sensor allocations, audit addendum."""
from __future__ import annotations

import json

import joblib
import numpy as np

from rsi.common import ROOT,write_json
from ast_feedback_replay_update import updated_model
from ast_probe_sensor_transfer import rank
from ast_probe_sensor_development import choose_probe
from dual_specialist_seed_evaluator import load_models
from listwise_budgeted_sensor_transfer import (
    DEST,LISTWISE,LEARNED,public_rows,allocations,normalize)


OUT=DEST/'public_nonleakage_addendum.json'


def main():
    if OUT.exists():raise RuntimeError('addendum already exists')
    assert json.loads((DEST/'audit.json').read_text())['passed']
    tasks=json.loads((DEST/'sealed_bank.json').read_text())
    wide=json.loads((DEST/'ast_wide_pools.json').read_text())
    matrix=json.loads((DEST/'predicted_probe_outputs.json').read_text())
    frozen_records=json.loads((DEST/'frozen_records.json').read_text())
    model=updated_model()
    public_tasks=[];reconstructed=[]
    for task,rec in zip(tasks,frozen_records):
        # No hidden examples, family, reference, or true output is handed to rank.
        public={'id':task['id'],'seed':task['seed'],'visible':task['visible']}
        public_tasks.append(public)
        pool=wide[task['id']]
        scores,order=rank(public,pool,model)
        probe=choose_probe(task['id'],matrix[task['id']],order,scores,
                           set(range(len(pool))),[],'top20_entropy')
        assert np.array_equal(scores,rec['old_scores'])
        assert order==rec['orders']['old'] and probe==rec['probe']
        reconstructed.append({'id':task['id'],'seed':task['seed'],
            'old_scores':scores,'orders':{'old':order},'probe':probe})
    rows,_=public_rows(public_tasks,wide,matrix,reconstructed,
                       load_models(),joblib.load(LISTWISE))
    assert normalize(rows)==json.loads((DEST/'public_rows.json').read_text())
    saved_models={name:joblib.load(DEST/f'{name}.joblib') for name in LEARNED}
    selected=allocations(rows,saved_models)
    assert normalize(selected)==json.loads((DEST/'allocations.json').read_text())
    result={'passed':True,'tasks_publicly_reconstructed':len(tasks),
            'ranker_orders_reconstructed':len(tasks),
            'probe_locations_reconstructed':len(tasks),
            'allocator_feature_vectors_reconstructed':len(tasks),
            'model_forecasts_reconstructed':len(tasks)*len(LEARNED),
            'allocations_reconstructed':{name:len(ids) for name,ids in selected.items()},
            'public_inputs_used':['id','seed','visible','candidate_pools',
                                  'predicted_candidate_probe_outputs'],
            'host_preparation_had_read_true_probe_outputs':True,
            'interpretation':'frozen choices are functionally independent of those true outputs; host preparation timing still violated literal freeze order'}
    write_json(OUT,result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
