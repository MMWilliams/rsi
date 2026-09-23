"""Reconstruct frozen active-evaluator choices and final labels from saved bank."""
import hashlib
import json

import numpy as np

from rsi.common import ROOT,digest,write_json
from rsi.semantic_invention import evaluate_program
from seed_casebanks import random_bank
from seed_source_search import read
from active_probe_diagnostic import initial_model,choose_probe
from active_evaluator_transfer import DEST,SOURCE,SEEDS,PER_BANK,unlabeled,freeze_choices


def main():
    manifest=read(DEST/'manifest.json')
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==manifest['source_sha256']
    assert hashlib.sha256((ROOT/'active_evaluator_transfer.py').read_bytes()).hexdigest()==manifest['runner_sha256']
    banks=read(DEST/'sealed_bank.json')
    pools=read(DEST/'candidate_pools.json')
    frozen=read(DEST/'frozen_decisions.json')
    observed=read(DEST/'results.json')['tasks']
    assert len(banks)==len(frozen)==len(observed)==PER_BANK*len(SEEDS)
    models={name:(np.asarray(m['scale']),np.asarray(m['weights']))
            for name,m in manifest['models'].items()}
    prior=ROOT/'runs/seed-low-9000'
    initial=initial_model(prior,read(prior/'protected_banks.json'),
                          read(prior/'candidate_pools.json'))
    checked=0
    for seed in SEEDS:
        recreated=random_bank(seed,PER_BANK,('ast_transition',),visible=2,hidden=22)
        for task in recreated:
            saved=banks[checked]; record=frozen[checked]; outcome=observed[checked]
            assert saved['id']==record['id']==outcome['id']==task['id']
            assert saved['visible']==task['visible']
            assert saved['probe_inputs']==[p[0] for p in task['hidden'][:8]]
            assert saved['probe_outputs']==[p[1] for p in task['hidden'][:8]]
            assert saved['final']==task['hidden'][8:]
            rows=pools[task['id']]
            assert digest(rows)==record['candidate_digest']
            for row in rows:
                assert evaluate_program(row['program'],task['visible'])
            public={'id':task['id'],'visible':task['visible'],
                    'probe_inputs':saved['probe_inputs']}
            rebuilt=freeze_choices(unlabeled(public,rows,initial),models)
            assert rebuilt==record
            correct=[evaluate_program(row['program'],saved['final']) for row in rows]
            order=record['ranking']; outputs=record['predicted_probe_outputs']
            truth=saved['probe_outputs']
            expected={'baseline':bool(correct[order[0]])}
            for name in ('pairwise','ridge','minimax','entropy','random'):
                j=record['choices'][name]
                matched=set(i for i in range(len(rows)) if outputs[i][j]==truth[j])
                selected=next((i for i in order if i in matched),order[0])
                expected[name]=bool(correct[selected])
            j=record['choices']['weighted_first']
            k=outcome['query_choices']['weighted_second']
            assert 0<=k<8 and k!=j
            remain=[i for i in range(len(rows)) if outputs[i][j]==truth[j]]
            if not remain: remain=list(range(len(rows)))
            assert k==choose_probe(task['id'],outputs,remain,[j],record['scores'],
                                   'weighted_entropy')
            second=[i for i in remain if outputs[i][k]==truth[k]]
            if second: remain=second
            selected=next((i for i in order if i in set(remain)),order[0])
            expected['weighted_two']=bool(correct[selected])
            assert expected==outcome['correct']
            assert bool(any(correct))==outcome['reachable']
            checked+=1
    report={'status':'passed','tasks':checked,'frozen_source_and_runner_hashes':True,
            'bank_regeneration':True,'candidate_visible_fit':True,
            'unlabeled_decision_reconstruction':True,'final_outcome_reconstruction':True}
    write_json(DEST/'audit.json',report)
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
