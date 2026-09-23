"""Post-outcome diagnostics; never used for checkpoint fitting or admission."""
import json
from rsi.common import ROOT, digest, write_json
from rsi.semantic_invention import evaluate_program
from incremental_feedback import read, menu, policy_programs, FROZEN, x, decisions

def analyze(name):
    root=ROOT/'runs'/name
    banks=read(root/'protected_banks.json'); pools=read(root/'candidate_pools.json'); results=read(root/'results.json')
    rounds=[]
    for checkpoint in map(str,range(5)):
        masses={key:sum(bool(pools[t['id']]) for t in tasks) for key,tasks in banks.items()}
        rounds.append({'round':int(checkpoint),'evaluator_correct':sum(row['rounds'][checkpoint]['evaluator_correct'] for row in results.values()),
            'brier':sum(results[key]['rounds'][checkpoint]['task_balanced_brier']*mass for key,mass in masses.items())/sum(masses.values()),
            'It_E0':sum(row['rounds'][checkpoint]['crosses']['It_E0']['correct'] for row in results.values()),
            'I0_Et':sum(row['rounds'][checkpoint]['crosses']['I0_Et']['correct'] for row in results.values()),
            'It_Et':sum(row['rounds'][checkpoint]['crosses']['It_Et']['correct'] for row in results.values())})
    menu_scores={}
    for edit in [{'name':'base','weights':list(FROZEN)}]+menu():
        menu_scores[edit['name']]={}
        for bank,tasks in banks.items():
            ps=policy_programs(tasks,pools,edit['weights'])
            menu_scores[edit['name']][bank]=sum(bool(evaluate_program(p,t['visible']+t['hidden'])) for t,p in zip(tasks,ps))
    collisions=0
    for tasks in banks.values():
        for t in tasks:
            buckets={}
            for row in pools[t['id']]: buckets.setdefault(tuple(x(row)),set()).add(bool(evaluate_program(row['program'],t['visible']+t['hidden'])))
            collisions+=any(len(labels)>1 for labels in buckets.values())
    public_banks={key:[{'id':t['id'],'visible':t['visible']} for t in tasks] for key,tasks in banks.items()}
    rerun=decisions(read(root/'feedback_banks.json'),read(root/'feedback_pools.json'),public_banks,pools)
    assert digest(rerun)==digest(read(root/'frozen_decisions.json'))
    return {'run':name,'rounds':rounds,'menu_scores_posthoc':menu_scores,'tasks_with_conflicting_feature_labels':collisions,
            'hidden_fields_removed_decision_replay':'passed'}

if __name__=='__main__':
    rows=[analyze(name) for name in ('incremental-feedback-20260917','incremental-feedback-ast-20260917')]
    write_json(ROOT/'analysis/incremental-feedback-diagnostics.json',rows)
    print(json.dumps(rows,indent=2))
