"""Output-blind public AST candidate and probe preparation.

The host may store sealed task oracle examples, but this module reads only the
visible pair and the *input strings* of eight offered output queries. It never
reads their true outputs or the hidden correctness suffix.
"""
from __future__ import annotations

import time
from concurrent.futures import ProcessPoolExecutor

from rsi.common import digest
from gated_ast_feedback import pools_for
from ast_probe_sensor_transfer import predicted_outputs,rank
from ast_probe_sensor_development import choose_probe
from ast_feedback_replay_update import updated_model


def prepare_public(tasks,max_workers=8):
    started=time.perf_counter()
    generator_tasks=[{'id':task['id'],'visible':task['visible'],
                      'family':'ast_transition'} for task in tasks]
    base,wide,generation_times=pools_for(generator_tasks)
    query_offers=[({'id':task['id'],
                    'probe_inputs':[pair[0] for pair in task['hidden'][:8]]},
                   wide[task['id']]) for task in tasks]
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        predicted=dict(executor.map(predicted_outputs,query_offers))
    model=updated_model()
    records=[]
    for task in tasks:
        public={'id':task['id'],'seed':task['seed'],
                'visible':task['visible']}
        pool=wide[task['id']]
        scores,order=rank(public,pool,model)
        probe=choose_probe(task['id'],predicted[task['id']],order,scores,
                           set(range(len(pool))),[],'top20_entropy')
        records.append({'id':task['id'],'seed':task['seed'],
                        'pool_sha256':digest(pool),'old_scores':scores,
                        'orders':{'old':order},'probe':probe})
    cost={'base_candidates':sum(map(len,base.values())),
          'extra_ast_candidates':sum(len(wide[key])-len(base[key])
                                     for key in base),
          'predicted_output_cells':sum(len(wide[task['id']])*8
                                       for task in tasks),
          'old_ranker_candidate_scores':sum(map(len,wide.values())),
          'generation_seconds':sum(generation_times.values()),
          'public_preparation_wall_seconds':time.perf_counter()-started}
    return base,wide,predicted,records,cost
