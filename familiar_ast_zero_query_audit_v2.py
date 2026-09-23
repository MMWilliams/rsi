"""Functional-equivalence and full-replay audit after model-object hash mismatch."""
from __future__ import annotations

import hashlib
import json

import joblib
import numpy as np

from rsi.common import ROOT, write_json
from wide_candidate_reranker_development import features
from candidate_reranker_transfer import model_for
from familiar_ast_zero_query_development import arrays, FIRST, SECOND, MODELS
from familiar_ast_zero_query_transfer import (DEST, MODEL_NAMES, PROTOCOL,
    SCRIPT, SEEDS, tasks_for, public_run, models_for, freeze_choices,
    outcomes_for, summarize, normalize, verify_manifest)


ADDENDUM=ROOT/'AUDIT-ADDENDUM-familiar-ast-zero-query-2026-09-18.md'
SCRIPT_V2=ROOT/'familiar_ast_zero_query_audit_v2.py'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def retrain():
    a=arrays(FIRST)
    b=arrays((SECOND,))
    x=np.r_[a['x'],b['x']]
    y=np.r_[a['y'],b['y']]
    rng=np.random.default_rng(904220)
    scrambled=b['y'].copy()
    for group in b['groups']:
        scrambled[group]=rng.permutation(scrambled[group])
    models={'early':model_for(15).fit(a['x'],a['y']),
        'later':model_for(15).fit(x,y),
        'scrambled':model_for(15).fit(x,np.r_[a['y'],scrambled]),
        'duplicate':model_for(15).fit(
            np.r_[a['x'],a['x'][:len(b['x'])]],
            np.r_[a['y'],a['y'][:len(b['y'])]])}
    return models,x,len(y)


def target_features(tasks,wide,records):
    parts=[]
    for task,rec in zip(tasks,records):
        pool=wide[task['id']]
        parts.append(features(task,pool,rec,min(100,len(rec['orders']['old']))))
    return np.concatenate(parts)


def main():
    if (DEST/'audit_v2.json').exists() or (DEST/'audit.json').exists():
        raise RuntimeError('audit exists')
    assert ADDENDUM.exists()
    manifest=json.loads((DEST/'manifest.json').read_text())
    verify_manifest(manifest)
    tasks=json.loads((DEST/'sealed_bank.json').read_text())
    assert tasks==normalize(tasks_for())
    retrained,source_x,source_count=retrain()
    frozen={name:joblib.load(MODELS/f'{name}.joblib')
            for name in MODEL_NAMES}
    object_hash_equal={name:joblib.hash(retrained[name])==joblib.hash(frozen[name])
                       for name in MODEL_NAMES}
    prediction_checks={}
    for name in MODEL_NAMES:
        a=retrained[name].predict_proba(source_x)
        b=frozen[name].predict_proba(source_x)
        assert np.array_equal(a,b),f'source probability mismatch: {name}'
        prediction_checks[name]={'source_rows':len(source_x)}
    base,wide,predicted,records,allocations,forecasts,cost=public_run(tasks)
    target_x=target_features(tasks,wide,records)
    for name in MODEL_NAMES:
        a=retrained[name].predict_proba(target_x)
        b=frozen[name].predict_proba(target_x)
        assert np.array_equal(a,b),f'target probability mismatch: {name}'
        prediction_checks[name]['target_rows']=len(target_x)
    records,scores=freeze_choices(tasks,wide,records,models_for())
    for name,value in (('base_pools.json',base),('ast_wide_pools.json',wide),
                       ('predicted_probe_outputs.json',predicted),
                       ('frozen_records.json',records),
                       ('frozen_allocations.json',allocations),
                       ('frozen_forecasts.json',forecasts)):
        assert normalize(value)==json.loads((DEST/name).read_text()),name
    stable=('base_candidates','extra_ast_candidates',
            'predicted_output_cells','e0_candidate_scores',
            'post_query_candidate_scores')
    assert all(cost[k]==manifest['cost'][k] for k in stable)
    assert scores==manifest['candidate_scores']
    outcomes,checked=outcomes_for(tasks,wide,records)
    saved=json.loads((DEST/'results.json').read_text())
    assert saved['manifest_sha256']==sha(DEST/'manifest.json')
    assert saved['tasks']==outcomes
    assert saved['summary']==summarize(outcomes,checked)
    result={'passed':True,
            'qualification':'model object hashes differ; exact probabilities equal on all evaluated source and target rows',
            'object_hash_equal':object_hash_equal,
            'probability_checks':prediction_checks,
            'tasks_rebuilt':len(tasks),
            'source_candidate_labels_rechecked':source_count,
            'predicted_output_cells_rechecked':cost['predicted_output_cells'],
            'target_candidate_labels_rechecked':checked,
            'candidate_scores_rechecked':scores,
            'original_protocol_sha256':sha(PROTOCOL),
            'original_runner_sha256':sha(SCRIPT),
            'addendum_sha256':sha(ADDENDUM),
            'auditor_sha256':sha(SCRIPT_V2)}
    write_json(DEST/'audit_v2.json',result)
    write_json(DEST/'audit.json',result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
