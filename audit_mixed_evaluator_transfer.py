"""Rebuild fixed-pool evaluator transfer decisions and final correctness."""
import hashlib
import json

import numpy as np

from rsi.common import ROOT,digest,write_json
from rsi.semantic_invention import evaluate_program
from seed_casebanks import random_bank
from seed_source_search import read
from seed_growth import representation
from active_probe_diagnostic import program_output,choose_probe
from mixed_probe_diagnostic import bool_safe_structure
from mixed_evaluator_transfer import SOURCE,DEST,SEEDS,FAMILIES,PER_BANK,CHECKPOINTS,choose
import seed_growth


def main():
    manifest=read(DEST/'manifest.json')
    assert manifest['runner_sha256']==hashlib.sha256(
        (ROOT/'mixed_evaluator_transfer.py').read_bytes()).hexdigest()
    assert manifest['source_sha256']==hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    checkpoint=read(SOURCE)
    seed_growth.structure=bool_safe_structure
    tasks=read(DEST/'sealed_bank.json');pools=read(DEST/'candidate_pools.json')
    records=read(DEST/'frozen_decisions.json')
    outcomes=read(DEST/'results.json')['tasks']
    assert len(tasks)==len(records)==len(outcomes)==PER_BANK*len(SEEDS)
    checked=0
    for seed in SEEDS:
        original=random_bank(seed,PER_BANK,FAMILIES,visible=1,hidden=23)
        positions=[i for i,t in enumerate(tasks) if t['seed']==seed]
        assert len(positions)==PER_BANK
        for local,i in enumerate(positions):
            task=tasks[i];src=original[local];rec=records[i];out=outcomes[i]
            assert task['id']==src['id']==rec['id']==out['id']
            assert task['visible']==src['visible']
            assert task['probe_inputs']==[p[0] for p in src['hidden'][:8]]
            assert task['probe_outputs']==[p[1] for p in src['hidden'][:8]]
            assert task['final']==src['hidden'][8:]
            rows=pools[task['id']]
            assert rec['pool_sha256']==digest(rows)
            assert all(evaluate_program(r['program'],task['visible']) for r in rows)
            x=representation({'id':task['id'],'visible':task['visible']},rows)['structural']
            for name in CHECKPOINTS:
                w=np.asarray(checkpoint['weights'][name])
                scores=(1/(1+np.exp(-np.clip(x@w,-30,30)))).tolist()
                assert np.allclose(scores,rec['predicted'][name],atol=0,rtol=0)
                assert choose(scores,rows)==rec['selected'][name]
            assert rec['selected']['first_generated']==0
            assert rec['selected']['shortest']==min(range(len(rows)),key=lambda j:(
                len(rows[j]['program']),rows[j]['program']))
            predicted=[[program_output(row['program'],inp) for inp in task['probe_inputs']]
                       for row in rows]
            assert predicted==rec['probe_outputs_predicted']
            probe=choose_probe(task['id'],predicted,list(range(len(rows))),[],
                               rec['predicted']['E0'],'entropy')
            assert probe==rec['entropy_probe']
            labels=[bool(evaluate_program(row['program'],task['final'])) for row in rows]
            assert bool(any(labels))==out['reachable']
            assert {name:bool(labels[j]) for name,j in rec['selected'].items()}==out['no_query']
            matching=[j for j in range(len(rows))
                      if predicted[j][probe]==task['probe_outputs'][probe]]
            for name in CHECKPOINTS:
                scores=rec['predicted'][name]
                index=max(matching,key=lambda j:(float(scores[j]),
                    -len(rows[j]['program']),rows[j]['program'])) if matching else rec['selected'][name]
                assert bool(labels[index])==out['one_query'][name]
                brier=float(np.mean((np.asarray(scores)-np.asarray(labels,dtype=float))**2))
                assert abs(brier-out['brier'][name])<1e-14
            checked+=1
    report={'status':'passed','tasks':checked,'bank_regeneration':True,
            'candidate_visible_fit':True,'checkpoint_selection_reconstruction':True,
            'probe_reconstruction':True,'final_label_reconstruction':True}
    write_json(DEST/'audit.json',report)
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
