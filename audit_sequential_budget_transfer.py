"""Reconstruct first-feedback features, second-query allocation and scoring."""
import hashlib
import json

import numpy as np

from rsi.common import ROOT,digest,write_json
from rsi.semantic_invention import evaluate_program
from seed_casebanks import random_bank
from seed_source_search import read
from active_probe_diagnostic import initial_model,choose_probe
from active_evaluator_transfer import unlabeled
from sequential_budget_development import fit,signals,rank
from sequential_budget_transfer import SOURCE,DEST,SEEDS,PER_BANK,EXTRA,METHODS


def main():
    manifest=read(DEST/'manifest.json')
    assert manifest['source_sha256']==hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    assert manifest['runner_sha256']==hashlib.sha256(
        (ROOT/'sequential_budget_transfer.py').read_bytes()).hexdigest()
    source=read(SOURCE)['tasks']
    model=fit(source)
    assert np.array_equal(model[0],np.asarray(manifest['model']['scale']))
    assert np.allclose(model[1],manifest['model']['weights'],atol=0,rtol=0)
    prior=ROOT/'runs/seed-low-9000'
    ranker=initial_model(prior,read(prior/'protected_banks.json'),
                         read(prior/'candidate_pools.json'))
    tasks=read(DEST/'sealed_bank.json');pools=read(DEST/'candidate_pools.json')
    records=read(DEST/'frozen_records.json')
    features=read(DEST/'first_feedback_features.json')
    allocations=read(DEST/'frozen_allocations.json')
    outcomes=read(DEST/'results.json')['tasks']
    assert len(tasks)==len(records)==len(features)==len(outcomes)==PER_BANK*len(SEEDS)
    for seed in SEEDS:
        source_bank=random_bank(seed,PER_BANK,('ast_transition',),visible=2,hidden=22)
        positions=[i for i,t in enumerate(tasks) if t['seed']==seed]
        assert len(positions)==PER_BANK
        for local,i in enumerate(positions):
            task=tasks[i];original=source_bank[local];record=records[i];f=features[i]
            assert task['id']==original['id']==record['id']==f['id']==outcomes[i]['id']
            assert task['visible']==original['visible']
            assert task['probe_inputs']==[z[0] for z in original['hidden'][:8]]
            assert task['probe_outputs']==[z[1] for z in original['hidden'][:8]]
            assert task['final']==original['hidden'][8:]
            rows=pools[task['id']]
            assert digest(rows)==record['candidate_digest']
            assert all(evaluate_program(row['program'],task['visible']) for row in rows)
            candidate=unlabeled(task,rows,ranker)
            first=choose_probe(task['id'],candidate['predicted_probe_outputs'],
                               list(range(candidate['n'])),[],candidate['scores'],
                               'weighted_entropy')
            minimax=max(range(8),key=lambda j:(candidate['features'][j][2],-j))
            candidate['choices']={'weighted_first':first,'minimax':minimax}
            del candidate['features']
            assert candidate==record
            rebuilt=signals({'id':task['id'],'seed':seed,
                             'first_output':task['probe_outputs'][first]},record)
            assert rebuilt==f
            correct=[evaluate_program(row['program'],task['final']) for row in rows]
            order=record['ranking'];pred=record['predicted_probe_outputs']
            remaining=[v for v in order if pred[v][first]==task['probe_outputs'][first]]
            if not remaining:remaining=order
            selected=remaining[0]
            k=f['second_probe']
            second=[v for v in remaining if pred[v][k]==task['probe_outputs'][k]]
            selected2=second[0] if second else selected
            expected={'baseline':bool(correct[order[0]]),
                      'one_query':bool(correct[selected]),
                      'all_two_query':bool(correct[selected2])}
            for method in METHODS:
                chosen=task['id'] in allocations[f'{seed}:{method}']
                expected[method]=bool(correct[selected2 if chosen else selected])
            assert expected==outcomes[i]['correct']
            assert bool(any(correct))==outcomes[i]['reachable']
        group=[features[i] for i in positions]
        for method in METHODS:
            chosen=sorted(group,key=lambda r:(-rank(r,method,model),r['id']))[:EXTRA]
            assert [r['id'] for r in chosen]==allocations[f'{seed}:{method}']
    result={'status':'passed','tasks':len(tasks),'bank_regeneration':True,
            'candidate_visible_fit':True,'first_feedback_features':True,
            'allocation_reconstruction':True,'outcome_reconstruction':True}
    write_json(DEST/'audit.json',result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
