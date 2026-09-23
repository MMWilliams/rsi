"""Parent/child test of family-conditioned evaluator edit-effect inheritance."""
from __future__ import annotations

import hashlib
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor

from rsi.common import ROOT,digest,write_json
from rsi.semantic_invention import evaluate_program
from seed_casebanks import FAMILIES,random_bank
from mixed_probe_diagnostic import pool,bool_safe_structure
import seed_growth


PRIOR=ROOT/'runs/temperature-withheld-families-20260917/results.json'
DEST=ROOT/'runs/contextual-loss-inheritance-20260917'
SEEDS=tuple(range(902276,902288))
PER_BANK=48
CATALOG=('temp_0.25','temp_0.5','temp_1.0')
POLICIES=('empty','inherited','scrambled')
PRIOR_EFFECTIVE_PER_FAMILY=8


def inputs():
    from temperature_withheld_families import inputs as load
    return load()


def decision(task,rows,data):
    from temperature_withheld_families import decision as choose_model
    return choose_model(task,rows,data)


def prior_tables():
    raw=PRIOR.read_bytes()
    result=json.loads(raw)['summary']['by_family']
    inherited={family:{name:PRIOR_EFFECTIVE_PER_FAMILY*
                       (result[family]['correct'][name]/result[family]['tasks'])
                       for name in CATALOG} for family in FAMILIES}
    scrambled={family:inherited[FAMILIES[(i+1)%len(FAMILIES)]].copy()
               for i,family in enumerate(FAMILIES)}
    empty={family:dict.fromkeys(CATALOG,0.) for family in FAMILIES}
    fixed_context={family:max(CATALOG,key=lambda name:(
        result[family]['correct'][name],-CATALOG.index(name))) for family in FAMILIES}
    return raw,{'empty':empty,'inherited':inherited,'scrambled':scrambled},fixed_context


def verify_prepared():
    manifest=json.loads((DEST/'manifest.json').read_text(encoding='utf-8'))
    assert manifest['prior_sha256']==hashlib.sha256(PRIOR.read_bytes()).hexdigest()
    assert manifest['input_sha256']=={name:hashlib.sha256(value).hexdigest()
                                      for name,value in inputs()[0].items()}
    assert manifest['runner_sha256']==hashlib.sha256(
        (ROOT/'contextual_loss_inheritance.py').read_bytes()).hexdigest()
    return manifest


def prepare():
    if DEST.exists():raise RuntimeError('transfer directory already exists')
    seed_growth.structure=bool_safe_structure
    prior_raw,tables,fixed_context=prior_tables()
    tasks=[{**task,'seed':seed} for seed in SEEDS for task in
           random_bank(seed,PER_BANK,FAMILIES,visible=1,hidden=23)]
    start=time.perf_counter()
    with ProcessPoolExecutor(max_workers=8) as executor:
        generated=list(executor.map(pool,tasks))
    pools={key:rows for key,rows,_ in generated}
    data=inputs()
    records=[decision(task,pools[task['id']],data) for task in tasks]
    manifest={'protocol':'EXPERIMENT-contextual-loss-inheritance.md',
              'prior_sha256':hashlib.sha256(prior_raw).hexdigest(),
              'input_sha256':{name:hashlib.sha256(value).hexdigest()
                              for name,value in data[0].items()},
              'runner_sha256':hashlib.sha256(
                  (ROOT/'contextual_loss_inheritance.py').read_bytes()).hexdigest(),
              'seeds':SEEDS,'per_bank':PER_BANK,'prior_effective_per_family':
              PRIOR_EFFECTIVE_PER_FAMILY,'prior_tables':tables,
              'fixed_context':fixed_context,
              'preparation_wall_seconds':time.perf_counter()-start}
    write_json(DEST/'sealed_bank.json',tasks)
    write_json(DEST/'candidate_pools.json',pools)
    write_json(DEST/'frozen_model_decisions.json',records)
    write_json(DEST/'manifest.json',manifest)
    print(json.dumps({'status':'prepared','tasks':len(tasks),
                      'candidates':sum(map(len,pools.values())),
                      'preparation_wall_seconds':manifest['preparation_wall_seconds']},indent=2))


def verified(task,record,rows):
    assert task['id']==record['id'] and digest(rows)==record['pool_sha256']
    unique={record['selected'][name] for name in CATALOG}
    labels={i:bool(evaluate_program(rows[i]['program'],task['hidden'][8:])) for i in unique}
    return {'id':task['id'],'family':task['family'],
            'correct':{name:labels[record['selected'][name]] for name in CATALOG}},len(unique)


def add(table,feedback):
    for row in feedback:
        family=row['family']
        for name in CATALOG:table[family][name]+=row['correct'][name]


def selected(table):
    return {family:max(CATALOG,key=lambda name:(table[family][name],-CATALOG.index(name)))
            for family in FAMILIES}


def admit():
    if (DEST/'parent_frozen.json').exists() or (DEST/'child_frozen.json').exists():
        raise RuntimeError('policy choices already frozen')
    manifest=verify_prepared()
    tasks=json.loads((DEST/'sealed_bank.json').read_text(encoding='utf-8'))
    pools=json.loads((DEST/'candidate_pools.json').read_text(encoding='utf-8'))
    records=json.loads((DEST/'frozen_model_decisions.json').read_text(encoding='utf-8'))
    tables=prior_tables()[1]
    start=time.perf_counter();evaluations=0
    parents=[]
    for episode in range(len(SEEDS)//2):
        offset=episode*96
        admission=[]
        for index in range(offset,offset+24):
            row,n=verified(tasks[index],records[index],pools[tasks[index]['id']])
            admission.append(row);evaluations+=n
        states=json.loads(json.dumps(tables))
        for table in states.values():add(table,admission)
        choices={name:selected(table) for name,table in states.items()}
        parents.append({'episode':episode,'parent_seed':SEEDS[2*episode],
                        'child_seed':SEEDS[2*episode+1],
                        'admission':admission,'parent_choice':choices,
                        'parent_tables':states})
    write_json(DEST/'parent_frozen.json',{'episodes':parents})
    parent_sha256=hashlib.sha256((DEST/'parent_frozen.json').read_bytes()).hexdigest()
    children=[]
    for parent in parents:
        episode=parent['episode'];offset=episode*96
        states=parent['parent_tables']
        parent_final=[]
        for index in range(offset+24,offset+48):
            row,n=verified(tasks[index],records[index],pools[tasks[index]['id']])
            parent_final.append(row);evaluations+=n
        for table in states.values():add(table,parent_final)
        child_admission=[]
        for index in range(offset+48,offset+72):
            row,n=verified(tasks[index],records[index],pools[tasks[index]['id']])
            child_admission.append(row);evaluations+=n
        for table in states.values():add(table,child_admission)
        choices={name:selected(table) for name,table in states.items()}
        children.append({'episode':episode,'parent_seed':parent['parent_seed'],
                         'child_seed':parent['child_seed'],
                         'parent_admission':parent['admission'],
                         'parent_final':parent_final,
                         'child_admission':child_admission,
                         'parent_choice':parent['parent_choice'],
                         'child_choice':choices,'child_tables':states})
    journal={'parent_sha256':parent_sha256,'episodes':children,
             'distinct_program_evaluations':evaluations,
             'maximum_example_checks':evaluations*15,
             'admission_wall_seconds':time.perf_counter()-start}
    write_json(DEST/'child_frozen.json',journal)
    print(json.dumps({'status':'admitted','episodes':len(children),
                      'distinct_program_evaluations':evaluations,
                      'maximum_example_checks':evaluations*15},indent=2))


def score():
    if (DEST/'results.json').exists():raise RuntimeError('results already exist')
    manifest=verify_prepared()
    tasks=json.loads((DEST/'sealed_bank.json').read_text(encoding='utf-8'))
    pools=json.loads((DEST/'candidate_pools.json').read_text(encoding='utf-8'))
    records=json.loads((DEST/'frozen_model_decisions.json').read_text(encoding='utf-8'))
    journal=json.loads((DEST/'child_frozen.json').read_text(encoding='utf-8'))
    assert journal['parent_sha256']==hashlib.sha256(
        (DEST/'parent_frozen.json').read_bytes()).hexdigest()
    episodes=[];final_evaluations=0
    for entry in journal['episodes']:
        episode=entry['episode'];offset=episode*96
        child_final=[]
        for index in range(offset+72,offset+96):
            row,n=verified(tasks[index],records[index],pools[tasks[index]['id']])
            task=tasks[index]
            row['reachable']=any(evaluate_program(candidate['program'],task['hidden'][8:])
                                 for candidate in pools[task['id']])
            child_final.append(row);final_evaluations+=n
        def count(rows,name):return sum(row['correct'][name] for row in rows)
        parent_fixed={name:count(entry['parent_final'],name) for name in CATALOG}
        child_fixed={name:count(child_final,name) for name in CATALOG}
        def policy_score(rows,choice):
            return sum(row['correct'][choice[row['family']]] for row in rows)
        parent_policy={name:policy_score(entry['parent_final'],choice)
                       for name,choice in entry['parent_choice'].items()}
        child_policy={name:policy_score(child_final,choice)
                      for name,choice in entry['child_choice'].items()}
        parent_policy['fixed_context']=policy_score(entry['parent_final'],manifest['fixed_context'])
        child_policy['fixed_context']=policy_score(child_final,manifest['fixed_context'])
        episodes.append({'episode':episode,'parent_seed':entry['parent_seed'],
                         'child_seed':entry['child_seed'],
                         'parent_fixed':parent_fixed,'child_fixed':child_fixed,
                         'parent_policy':parent_policy,'child_policy':child_policy,
                         'parent_choice':entry['parent_choice'],
                         'child_choice':entry['child_choice'],
                         'child_final':child_final})
    def aggregate(stage,key):
        names=list(episodes[0][key])
        return {name:sum(row[key][name] for row in episodes) for name in names}
    summary={'scope':'fresh six-family contextual parent-child edit transfer',
             'episodes':len(episodes),'parent_final_tasks':len(episodes)*24,
             'child_final_tasks':len(episodes)*24,
             'child_reachable':sum(row['reachable'] for episode in episodes
                                   for row in episode['child_final']),
             'child_reachable_by_family':{family:sum(row['reachable'] for episode in episodes
                                                    for row in episode['child_final']
                                                    if row['family']==family)
                                          for family in FAMILIES},
             'parent_fixed':aggregate('parent','parent_fixed'),
             'child_fixed':aggregate('child','child_fixed'),
             'parent_policy':aggregate('parent','parent_policy'),
             'child_policy':aggregate('child','child_policy'),
             'child_inherited_minus_empty_by_episode':[
                 row['child_policy']['inherited']-row['child_policy']['empty']
                 for row in episodes],
             'admission_program_evaluations':journal['distinct_program_evaluations'],
             'final_program_evaluations':final_evaluations,
             'child_by_family':{family:{name:sum(
                 row['correct'][episode['child_choice'][name][family]]
                 for episode in episodes for row in episode['child_final']
                 if row['family']==family) for name in POLICIES}
                 for family in FAMILIES}}
    write_json(DEST/'results.json',{'summary':summary,'episodes':episodes})
    print(json.dumps(summary,indent=2))


if __name__=='__main__':{'prepare':prepare,'admit':admit,'score':score}[sys.argv[1]]()
