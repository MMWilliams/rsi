"""Opened-bank diagnostic of first and second exact-output query value."""
from __future__ import annotations

import json
import sys

import numpy as np

from rsi.common import ROOT,write_json
from rsi.semantic_invention import evaluate_program
from ast_probe_sensor_development import choose_probe
from ast_query_allocation_development import allocate
from cross_family_meta_improver_transfer import sha

RUNS={'meta':ROOT/'runs/cross-family-meta-improver-transfer-20260918',
      'stable':ROOT/'runs/stable-cross-family-improver-transfer-20260918'}


def run(name,stage):
    directory=RUNS[name]/stage
    out=ROOT/f'analysis/two-query-effects-{name}-{stage}-20260918.json'
    if out.exists():raise RuntimeError(f'{out} already exists')
    tasks=json.loads((directory/'sealed_bank.json').read_text())
    base=json.loads((directory/'base_pools.json').read_text())
    wide=json.loads((directory/'ast_wide_pools.json').read_text())
    matrix=json.loads((directory/'predicted_probe_outputs.json').read_text())
    records=json.loads((directory/'frozen_records.json').read_text())
    outcomes=json.loads((directory/'results.json').read_text())['tasks']
    assert len(tasks)==len(records)==len(outcomes)==288
    rows=[]
    for task,record,previous in zip(tasks,records,outcomes):
        key=task['id'];pool=wide.get(key,base[key]);predicted=matrix[key]
        assert key==record['id']==previous['id']
        order=record['order'];first=record['first_probe'];scores=record['scores']
        remaining=set(range(len(pool)))
        matched={i for i in remaining if predicted[i][first]==task['hidden'][first][1]}
        if matched:remaining=matched
        one_index=next(i for i in order if i in remaining)
        assert one_index==previous['selected_after_query']
        second=choose_probe(key,predicted,order,scores,remaining,[first],'top20_entropy')
        matched={i for i in remaining if predicted[i][second]==task['hidden'][second][1]}
        if matched:remaining=matched
        two_index=next(i for i in order if i in remaining)
        two=int(bool(evaluate_program(pool[two_index]['program'],task['hidden'][8:])))
        zero=int(previous['zero']);one=int(previous['one'])
        rows.append({'id':key,'seed':task['seed'],'family':task['family'],
                     'public_block':record['public_block'],'features':record['features'],
                     'zero':zero,'one':one,'two':two,
                     'gain1':one-zero,'gain2':two-one,
                     'first_probe':first,'second_probe':second,
                     'second_selected_index':two_index})
    banks=[]
    for seed in sorted({r['seed'] for r in rows}):
        group=[r for r in rows if r['seed']==seed]
        assert len(group)==48
        y1=np.asarray([r['gain1'] for r in group]);y2=np.asarray([r['gain2'] for r in group])
        oracle_actions=allocate(y1,y2,8)
        best=sum((r['zero'],r['one'],r['two'])[a] for r,a in zip(group,oracle_actions))
        one_only=sum(r['zero'] for r in group)+sum(sorted((r['gain1'] for r in group),reverse=True)[:8])
        banks.append({'seed':seed,'zero':sum(r['zero'] for r in group),
                      'one_each':sum(r['one'] for r in group),
                      'two_each':sum(r['two'] for r in group),
                      'hindsight_eight_0_1':one_only,
                      'hindsight_eight_0_1_2':best,
                      'oracle_actions':oracle_actions})
    result={'scope':'opened development bank; second output acquired offline from sealed interpreter',
            'run':name,'stage':stage,
            'source_sha256':{n:sha(directory/n) for n in
                             ('sealed_bank.json','base_pools.json','ast_wide_pools.json',
                              'predicted_probe_outputs.json','frozen_records.json','results.json')},
            'summary':{'tasks':len(rows),'zero':sum(r['zero'] for r in rows),
                       'one_each':sum(r['one'] for r in rows),
                       'two_each':sum(r['two'] for r in rows),
                       'first_gains':sum(r['gain1']>0 for r in rows),
                       'first_harms':sum(r['gain1']<0 for r in rows),
                       'second_gains':sum(r['gain2']>0 for r in rows),
                       'second_harms':sum(r['gain2']<0 for r in rows),
                       'hindsight_eight_0_1':sum(b['hindsight_eight_0_1'] for b in banks),
                       'hindsight_eight_0_1_2':sum(b['hindsight_eight_0_1_2'] for b in banks)},
            'by_bank':banks,'rows':rows,
            'limits':['Hindsight uses unavailable final correctness labels.',
                      'Training on every second-query effect would require a second true output per task.']}
    write_json(out,result)
    print(json.dumps({'run':name,'stage':stage,'summary':result['summary']},indent=2))


if __name__=='__main__':run(sys.argv[1],sys.argv[2])
