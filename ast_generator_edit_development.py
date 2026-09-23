"""Development-only AST reachability and ranking under source/cap edits."""
from __future__ import annotations

import json
import time
from concurrent.futures import ProcessPoolExecutor

from rsi.common import ROOT,write_json
from rsi.semantic_invention import evaluate_program
from stitch_ten import source_candidates
from mixed_probe_diagnostic import bool_safe_structure
import seed_growth


RUN=ROOT/'runs/temperature-withheld-families-20260917'
OUT=ROOT/'analysis/ast-generator-edit-development.json'
CAP=512
ARMS=('v67','v73','v69')
VARIANTS=('old_128','wide_67_73','wide_plus_69','v69_only')


def generate(task):
    public={'id':task['id'],'visible':task['visible']}
    rows={};elapsed={}
    for arm in ARMS:
        start=time.perf_counter()
        rows[arm]=source_candidates(public,arm,{},CAP)
        elapsed[arm]=time.perf_counter()-start
    return task['id'],rows,elapsed


def merge(*groups):
    unique={}
    for group in groups:
        for row in group:unique.setdefault(row['program'],row)
    return list(unique.values())


def main():
    if OUT.exists():raise RuntimeError('development output already exists')
    tasks=[task for task in json.loads((RUN/'sealed_bank.json').read_text(encoding='utf-8'))
           if task['family']=='ast_transition']
    old=json.loads((RUN/'candidate_pools.json').read_text(encoding='utf-8'))
    start=time.perf_counter()
    with ProcessPoolExecutor(max_workers=8) as executor:
        generated=list(executor.map(generate,tasks))
    by_id={key:(rows,elapsed) for key,rows,elapsed in generated}
    from temperature_withheld_families import inputs,decision
    seed_growth.structure=bool_safe_structure
    model=inputs()
    records=[]
    for task in tasks:
        sources,elapsed=by_id[task['id']]
        pools={
            'old_128':old[task['id']],
            'wide_67_73':merge(sources['v67'],sources['v73']),
            'wide_plus_69':merge(sources['v67'],sources['v73'],sources['v69']),
            'v69_only':sources['v69'],
        }
        truth={}
        def correct(row):
            program=row['program']
            if program not in truth:
                truth[program]=bool(evaluate_program(program,task['hidden'][8:]))
            return truth[program]
        variants={}
        for name,rows in pools.items():
            if rows:
                selected=decision(task,rows,model)['selected']
                scored={key:correct(rows[index]) for key,index in selected.items()}
            else:
                selected={};scored={}
            variants[name]={'candidates':len(rows),'reachable':any(correct(row) for row in rows),
                            'correct':scored,'selected':selected}
        records.append({'id':task['id'],'seed':task['seed'],'family':task['family'],
                        'reference':task.get('reference'),
                        'source_candidates':{arm:len(rows) for arm,rows in sources.items()},
                        'source_seconds':elapsed,'variants':variants})
    names=list(records[0]['variants']['old_128']['correct'])
    def aggregate(name):
        rows=[record['variants'][name] for record in records]
        return {'tasks':len(rows),'total_candidates':sum(row['candidates'] for row in rows),
                'mean_candidates':sum(row['candidates'] for row in rows)/len(rows),
                'reachable':sum(row['reachable'] for row in rows),
                'correct':{key:sum(row['correct'].get(key,False) for row in rows)
                           for key in names}}
    summary={'scope':'development only; AST labels previously inspected',
             'tasks':len(tasks),'cap_per_source':CAP,
             'variants':{name:aggregate(name) for name in VARIANTS},
             'source_candidate_totals':{arm:sum(record['source_candidates'][arm]
                                                for record in records) for arm in ARMS},
             'wall_seconds':time.perf_counter()-start}
    write_json(OUT,{'summary':summary,'tasks':records})
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
