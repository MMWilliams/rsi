"""Development-only verified effect ledger for mixed evaluator edit packages."""
from __future__ import annotations

import json
from collections import defaultdict

from rsi.common import ROOT,write_json
from gated_ast_feedback import public_block,BLOCK_AST
from seed_casebanks import FAMILIES
from cross_family_meta_improver_transfer import sha

SOURCE=ROOT/'runs/cross-component-mixed-transfer-20260918'
PROBES=ROOT/'analysis/cross-family-probe-development.json'
OUT=ROOT/'analysis/typed-edit-effect-development-20260918.json'


def main():
    tasks=json.loads((SOURCE/'sealed_bank.json').read_text())
    results=json.loads((SOURCE/'results.json').read_text())['tasks']
    base=json.loads((SOURCE/'base_pools.json').read_text())
    wide=json.loads((SOURCE/'ast_wide_pools.json').read_text())
    probe=json.loads(PROBES.read_text())['tasks_detail']
    by_probe={r['id']:r for r in probe}
    assert len(tasks)==len(results)==len(probe)==288
    ledger=[]
    for task,out in zip(tasks,results):
        key=task['id'];pr=by_probe[key]
        assert key==out['id']==pr['id']
        ast=public_block(task)==BLOCK_AST
        assert int(out['correct']['ast_ranker'])==pr['zero']
        if ast:assert int(out['correct']['top20_one'])==pr['one']
        outcomes={name:int(value) for name,value in out['correct'].items()}
        outcomes['one_any']=int(pr['one'])
        costs={'base_candidates':len(base[key]),
               'extra_wide_candidates':len(wide[key])-len(base[key]) if ast else 0,
               'one_query_calls':1,
               'predicted_output_cells':pr['candidates']*8}
        row={'id':key,'seed':task['seed'],'family':task['family'],
             'public_block':public_block(task),
             'visible_examples':task['visible'],
             'features':pr['features'],
             'base_reachable':int(out['base_reachable']),
             'wide_reachable':int(out['wide_reachable']),
             'newly_reachable':int(out['wide_reachable'] and not out['base_reachable']),
             'outcomes':outcomes,
             'effects':{'global_sharp':outcomes['sharp_global']-outcomes['fixed_map'],
                        'ast_replay_ranker':outcomes['ast_ranker']-outcomes['fixed_map'],
                        'ast_top20_sensor':outcomes['top20_one']-outcomes['ast_ranker'],
                        'ast_minimax_sensor':outcomes['minimax_one']-outcomes['ast_ranker'],
                        'ast_adaptive_vs_top20':outcomes['adaptive']-outcomes['top20_one'],
                        'all_family_top20_sensor':outcomes['one_any']-outcomes['ast_ranker']},
             'costs':costs}
        ledger.append(row)
    by_seed=defaultdict(list)
    for row in ledger:by_seed[row['seed']].append(row)
    assert len(by_seed)==6 and all(len(v)==48 for v in by_seed.values())
    baseline=sum(r['outcomes']['ast_ranker'] for r in ledger)
    hindsight=0
    for rows in by_seed.values():
        gains=sorted((r['effects']['all_family_top20_sensor'] for r in rows),reverse=True)
        hindsight+=sum(r['outcomes']['ast_ranker'] for r in rows)+sum(gains[:8])
    def aggregate(rows):
        return {'tasks':len(rows),
                'base_reachable':sum(r['base_reachable'] for r in rows),
                'wide_reachable':sum(r['wide_reachable'] for r in rows),
                'newly_reachable':sum(r['newly_reachable'] for r in rows),
                'correct':{name:sum(r['outcomes'][name] for r in rows)
                           for name in ledger[0]['outcomes']},
                'edit_effects':{name:{'gain':sum(r['effects'][name]>0 for r in rows),
                                      'harm':sum(r['effects'][name]<0 for r in rows),
                                      'net':sum(r['effects'][name] for r in rows)}
                                for name in ledger[0]['effects']},
                'extra_wide_candidates':sum(r['costs']['extra_wide_candidates'] for r in rows),
                'predicted_output_cells':sum(r['costs']['predicted_output_cells'] for r in rows)}
    result={'scope':'opened development bank; external final labels, public features and typed edit costs',
            'sources_sha256':{'tasks':sha(SOURCE/'sealed_bank.json'),
                              'results':sha(SOURCE/'results.json'),
                              'base':sha(SOURCE/'base_pools.json'),
                              'wide':sha(SOURCE/'ast_wide_pools.json'),
                              'all_family_probes':sha(PROBES)},
            'overall':aggregate(ledger),
            'by_family':{family:aggregate([r for r in ledger if r['family']==family])
                         for family in FAMILIES},
            'by_bank':{str(seed):aggregate(rows) for seed,rows in by_seed.items()},
            'oracle_hindsight_eight_per_bank':hindsight,
            'baseline_for_hindsight':baseline,
            'rows':ledger,
            'limits':['Opened development labels cannot be used as a final holdout.',
                      'Hindsight package selection requires unavailable final labels.',
                      'Candidate-generation, prediction and query costs are distinct.']}
    write_json(OUT,result)
    print(json.dumps({'overall':result['overall'],
                      'baseline_for_hindsight':baseline,
                      'oracle_hindsight_eight_per_bank':hindsight},indent=2))


if __name__=='__main__':main()
