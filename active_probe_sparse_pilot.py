"""Development-only check that sparse public examples create evaluator headroom."""
import json
import time
from concurrent.futures import ProcessPoolExecutor

from rsi.common import ROOT,write_json
from seed_casebanks import random_bank
from seed_source_search import read
from active_probe_diagnostic import initial_model,task_study,MODES
from stitch_ten import source_candidates


def larger_pool(task):
    public={'id':task['id'],'visible':task['visible']}
    rows={}; elapsed={}
    for arm in ('v67','v73'):
        start=time.perf_counter()
        for row in source_candidates(public,arm,{},128): rows.setdefault(row['program'],row)
        elapsed[arm]=time.perf_counter()-start
    return task['id'],list(rows.values()),elapsed


def main():
    prior=ROOT/'runs/seed-low-9000'
    model=initial_model(prior,read(prior/'protected_banks.json'),read(prior/'candidate_pools.json'))
    tasks=random_bank(207005+9000,12,('ast_transition',),visible=2,hidden=22)
    start=time.perf_counter()
    with ProcessPoolExecutor(max_workers=4) as executor:
        generated=list(executor.map(larger_pool,tasks))
    pools={key:rows for key,rows,_ in generated}
    timing={'parallel_wall_seconds':time.perf_counter()-start,'workers':4,
            'summed_worker_wall_seconds_by_source':{arm:sum(t[arm] for _,_,t in generated)
                                                    for arm in ('v67','v73')}}
    rows=[task_study(task,pools[task['id']],model) for task in tasks]
    summary={'scope':'development, previous task seed with a 2/22 example split and cap 128/source; never use as fresh confirmation',
             'tasks':len(rows),'reachable':sum(row['reachable'] for row in rows),
             'baseline':sum(row['baseline'] for row in rows),
             'discriminating_probe_tasks':sum(max(row['probe_classes'],default=0)>1 for row in rows),
             'best_one_probe':sum(row['best_one_probe'] for row in rows),
             'modes':{mode:{'one':sum(row['modes'][mode][0] for row in rows),
                            'two':sum(row['modes'][mode][1] for row in rows)} for mode in MODES},
             'generation':timing}
    write_json(ROOT/'analysis/active-probe-sparse-pilot-v2-cap128.json',{'summary':summary,'tasks':rows})
    print(json.dumps(summary,indent=2))


if __name__=='__main__': main()
