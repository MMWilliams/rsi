"""Rebuild source acquisition, child weights and target decisions."""
import hashlib
import json

import numpy as np

from rsi.common import ROOT,digest,write_json
from rsi.semantic_invention import evaluate_program
from seed_casebanks import random_bank
from improver_acquisition_transfer import (
    SOURCE,DEST,FAMILIES,SOURCE_SEED,SOURCE_COUNT,TARGET_SEEDS,PER_BANK,
    BUDGET,METHODS,public_record,acquire,choose)
from improver_acquisition_development import probabilities
from mixed_probe_diagnostic import bool_safe_structure
import seed_growth


def main():
    manifest=json.loads((DEST/'manifest.json').read_text(encoding='utf-8'))
    assert manifest['runner_sha256']==hashlib.sha256(
        (ROOT/'improver_acquisition_transfer.py').read_bytes()).hexdigest()
    assert manifest['source_sha256']==hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    seed_growth.structure=bool_safe_structure
    checkpoint=json.loads(SOURCE.read_text(encoding='utf-8'))
    initial=np.asarray(checkpoint['weights']['E0'])
    source=json.loads((DEST/'source_bank.json').read_text(encoding='utf-8'))
    target=json.loads((DEST/'target_bank.json').read_text(encoding='utf-8'))
    pools=json.loads((DEST/'candidate_pools.json').read_text(encoding='utf-8'))
    saved_public=json.loads((DEST/'source_public_records.json').read_text(encoding='utf-8'))
    saved_logs=json.loads((DEST/'acquisition_logs.json').read_text(encoding='utf-8'))
    child=json.loads((DEST/'child_weights.json').read_text(encoding='utf-8'))
    decisions=json.loads((DEST/'frozen_target_decisions.json').read_text(encoding='utf-8'))
    outcomes=json.loads((DEST/'results.json').read_text(encoding='utf-8'))['tasks']
    assert source==random_bank(SOURCE_SEED,SOURCE_COUNT,FAMILIES,visible=1,hidden=23)
    regenerated=[]
    for seed in TARGET_SEEDS:
        regenerated += [{**task,'seed':seed,'family':FAMILIES[i%len(FAMILIES)]}
            for i,task in enumerate(random_bank(seed,PER_BANK,FAMILIES,visible=1,hidden=23))]
    assert target==regenerated
    assert len(target)==len(decisions)==len(outcomes)
    public=[]
    for task,saved in zip(source,saved_public):
        rows=pools[task['id']]
        assert all(evaluate_program(r['program'],task['visible']) for r in rows)
        built=public_record(task,rows)
        assert built==saved
        public.append(built)
    cache={}
    for method in METHODS:
        weights,log=acquire(method,[r for r in public if r['n']>0],
                            initial,source,pools,cache)
        assert np.allclose(weights,child[method],atol=0,rtol=0)
        assert log==saved_logs[method]
        assert sum(r['candidate_labels'] for r in log)==BUDGET
    opened=[{'id':key[0],'index':key[1],'correct':value}
            for key,value in sorted(cache.items())]
    assert opened==json.loads((DEST/'opened_source_labels.json').read_text(encoding='utf-8'))
    for task,decision,out in zip(target,decisions,outcomes):
        rows=pools[task['id']]
        assert all(evaluate_program(r['program'],task['visible']) for r in rows)
        assert decision['pool_sha256']==digest(rows)
        public_task=public_record(task,rows)
        if rows:
            pred={'E0':probabilities(public_task,initial).tolist(),
                  'E192':probabilities(public_task,
                         np.asarray(checkpoint['weights']['E192'])).tolist()}
            for method in METHODS:
                pred[method]=probabilities(public_task,np.asarray(child[method])).tolist()
        else:pred={name:[] for name in ('E0','E192',*METHODS)}
        assert pred==decision['predicted']
        assert {name:choose(scores,rows) if rows else None
                for name,scores in pred.items()}==decision['selected']
        labels=[bool(evaluate_program(row['program'],task['hidden'][8:])) for row in rows]
        assert bool(any(labels))==out['reachable']
        expected={name:bool(labels[index]) if index is not None else False
                  for name,index in decision['selected'].items()}
        assert expected==out['correct']
    report={'status':'passed','source_tasks':len(source),'target_tasks':len(target),
            'source_bank_rebuilt':True,'target_banks_rebuilt':True,
            'source_labels_and_child_weights_rebuilt':True,
            'target_decisions_and_outcomes_rebuilt':True}
    write_json(DEST/'audit.json',report)
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
