"""Development-only active evaluation on already inspected task banks.

The first eight old hidden examples become an unlabeled probe-input pool. Their
outputs are disclosed only after a strategy chooses a probe. The final eight
old hidden examples score the selected program. These banks cannot confirm a
new policy because their outcomes were already inspected in prior studies.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections import Counter,defaultdict
from pathlib import Path

import numpy as np

from rsi.common import ROOT,write_json
from rsi.semantic_invention import semantic_value,evaluate_program
from rsi.invented_space import _split_atoms
from seed_growth import train,predict,pick,representation
from seed_source_search import read,export_model


OFFSETS=(9000,10000,11000,12000,13000,14000)
MODES=('random','entropy','weighted_entropy','minimax')


def program_output(program,text):
    try:
        return ''.join(semantic_value(atom,text) for atom in _split_atoms(program[7:-1]))
    except (ValueError,TypeError,RecursionError,IndexError):
        return None
    except Exception as exc:
        # The task DSL also raises PosError/ParseError; neither is a target string.
        if type(exc).__name__ in ('PosError','ParseError'): return None
        raise


def initial_model(root,banks,pools):
    opened=read(root/'opened_feedback_labels.json')
    feedback=[]
    for task in banks['bootstrap']:
        key=task['id']; rows=pools[key]
        record={'id':key,'public':{'id':key,'visible':task['visible']},'rows':rows,
                'features':representation({'id':key,'visible':task['visible']},rows),
                'labels':np.asarray([opened[key][str(i)] for i in range(len(rows))],dtype=float)}
        feedback.append(record)
    model=train(feedback)
    frozen=read(root/'frozen_loops.json')
    from rsi.common import digest
    assert digest(export_model(model))==frozen['arms']['I0']['checkpoints'][0]['model_sha256']
    return model


def choose_probe(taskid,outputs,remaining,used,scores,mode):
    options=[j for j in range(len(outputs[0])) if j not in used]
    if mode=='random':
        return min(options,key=lambda j:hashlib.sha256((taskid+':random:'+str(j)).encode()).digest())
    weights=np.ones(len(remaining),dtype=float)
    if mode=='weighted_entropy':
        raw=np.asarray([scores[i] for i in remaining],dtype=float)
        weights=np.exp((raw-raw.max())/.1)
    weights/=weights.sum()
    values=[]
    for j in options:
        groups=defaultdict(float)
        for k,i in enumerate(remaining): groups[outputs[i][j]]+=weights[k]
        if mode=='minimax': utility=-max(groups.values())
        else: utility=-sum(p*math.log(p) for p in groups.values() if p>0)
        values.append((utility,-j,j))
    return max(values)[2]


def choose_program(record,scores,remaining):
    if not remaining: return pick(record,scores)
    return max(remaining,key=lambda i:(float(scores[i]),-len(record['rows'][i]['program']),record['rows'][i]['program']))


def task_study(task,rows,model):
    public={'id':task['id'],'visible':task['visible']}
    record={'id':task['id'],'public':public,'rows':rows,'features':representation(public,rows)}
    if not rows: return {'id':task['id'],'family':task['family'],'candidates':0,'reachable':False,
                         'baseline':False,'probe_classes':[],'modes':{mode:[False,False] for mode in MODES},
                         'best_one_probe':False}
    scores=predict(model,record)['ensemble']
    probes=task['hidden'][:8]
    final=task['hidden'][8:]
    outputs=[[program_output(row['program'],pair[0]) for pair in probes] for row in rows]
    correct=[evaluate_program(row['program'],final) for row in rows]
    baseline=choose_program(record,scores,list(range(len(rows))))
    classes=[len(set(row[j] for row in outputs)) for j in range(len(probes))]
    decisions={}
    for mode in MODES:
        remaining=list(range(len(rows))); used=[]; curve=[]
        for _ in range(2):
            j=choose_probe(task['id'],outputs,remaining,used,scores,mode)
            used.append(j)
            matched=[i for i in remaining if outputs[i][j]==probes[j][1]]
            if matched: remaining=matched
            choice=choose_program(record,scores,remaining)
            curve.append(bool(correct[choice]))
        decisions[mode]=curve
    best=False
    for j in range(len(probes)):
        matched=[i for i in range(len(rows)) if outputs[i][j]==probes[j][1]]
        choice=choose_program(record,scores,matched)
        best|=bool(correct[choice])
    return {'id':task['id'],'family':task['family'],'candidates':len(rows),
            'reachable':any(correct),'baseline':bool(correct[baseline]),
            'probe_classes':classes,'modes':decisions,'best_one_probe':best}


def main():
    episodes=[]
    for offset in OFFSETS:
        root=ROOT/'runs'/f'seed-low-{offset}'
        assert read(root/'audit.json')['status']=='passed'
        banks=read(root/'protected_banks.json'); pools=read(root/'candidate_pools.json')
        model=initial_model(root,banks,pools)
        rows=[task_study(task,pools[task['id']],model)
              for split,tasks in banks.items() if split.startswith('final_') for task in tasks]
        episodes.append({'offset':offset,'tasks':rows})
        print('development probe episode '+str(offset)+' closed',flush=True)
    allrows=[row for ep in episodes for row in ep['tasks']]
    summary={'scope':'development only; old hidden examples re-split 8 probe/8 final; no new sealed bank',
             'tasks':len(allrows),'reachable':sum(r['reachable'] for r in allrows),
             'baseline':sum(r['baseline'] for r in allrows),
             'some_candidate_disagreement':sum(max(r['probe_classes'],default=0)>1 for r in allrows),
             'best_one_probe':sum(r['best_one_probe'] for r in allrows),
             'methods':{mode:{'one':sum(r['modes'][mode][0] for r in allrows),
                              'two':sum(r['modes'][mode][1] for r in allrows)} for mode in MODES},
             'by_family':{family:{'n':sum(r['family']==family for r in allrows),
                                  'reachable':sum(r['reachable'] for r in allrows if r['family']==family),
                                  'baseline':sum(r['baseline'] for r in allrows if r['family']==family),
                                  **{mode:[sum(r['modes'][mode][k] for r in allrows if r['family']==family)
                                           for k in (0,1)] for mode in MODES}}
                          for family in sorted({r['family'] for r in allrows})}}
    write_json(ROOT/'analysis/active-probe-development.json',{'summary':summary,'episodes':episodes})
    print(json.dumps(summary,indent=2))


if __name__=='__main__': main()
