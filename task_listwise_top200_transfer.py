"""Fresh frozen transfer of top-200 task-listwise candidate evaluation."""
from __future__ import annotations

import hashlib
import json
import sys
import time

import joblib
import numpy as np

from rsi.common import ROOT, digest, write_json
from rsi.semantic_invention import evaluate_program
from seed_casebanks import random_bank, shifted_ast_bank
from wide_candidate_reranker_development import features
from dual_specialist_seed_evaluator import load_models, FAMILIAR, SHIFTED
from cross_family_meta_improver_transfer import interval
import post_query_feedback_transfer as previous


DEST = ROOT / 'runs/task-listwise-top200-transfer-20260918'
PROTOCOL = ROOT / 'EXPERIMENT-task-listwise-top200-transfer.md'
SCRIPT = ROOT / 'task_listwise_top200_transfer.py'
DEVELOPMENT = ROOT / 'analysis/task-listwise-top200-development-20260918.json'
TRAINED = ROOT / 'analysis/task-listwise-top200-models-20260918'
PRIOR = ROOT / 'analysis/candidate-stacking-models-20260918/later_stacked.joblib'
SEEDS = tuple(range(905300, 905324))
LEARNED = ('early_listwise', 'later_listwise', 'scrambled_listwise',
           'duplicate_listwise', 'early_bce', 'later_bce')
NAMES = ('dual100', 'dual200', 'mean200', 'familiar200', 'shifted200',
         'early_listwise', 'later_listwise', 'scrambled_listwise',
         'duplicate_listwise', 'early_bce', 'later_bce', 'prior_stack')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize(value):
    return json.loads(json.dumps(value, ensure_ascii=False))


def tasks_for():
    tasks = []
    for seed in SEEDS:
        familiar = random_bank(seed, 4, ('ast_transition',), visible=1, hidden=23)
        shifted = shifted_ast_bank(seed + 100000, 4, visible=1, hidden=23)
        for a, b in zip(familiar, shifted):
            tasks.extend(({**a, 'seed': seed}, {**b, 'seed': seed}))
    return tasks


def public_run(tasks):
    old = previous.SEEDS
    previous.SEEDS = SEEDS
    try:
        return previous.public_run(tasks)
    finally:
        previous.SEEDS = old


def models_for():
    return {**{name: joblib.load(TRAINED/f'{name}.joblib') for name in LEARNED},
            'prior_stack': joblib.load(PRIOR)}


def predict_listwise(frozen, x):
    # Import after the Windows generator worker pool exits. Spawned workers
    # otherwise import PyTorch eight times and can exhaust memory.
    import torch
    torch.set_num_threads(1)
    class Ranker(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.layers = torch.nn.Sequential(
                torch.nn.Linear(191,32),torch.nn.ReLU(),torch.nn.Linear(32,1))
        def forward(self, value):
            return self.layers(value).squeeze(-1)
    model=Ranker()
    model.load_state_dict({key:torch.from_numpy(value) for key,value
                           in frozen['weights']['120'].items()})
    model.eval()
    with torch.no_grad():
        normalized=(x-frozen['mean'])/frozen['scale']
        return model(torch.from_numpy(normalized)).numpy()


def choices_for(tasks, wide, records, specialists, models):
    started = time.perf_counter()
    rows = []
    for task, rec in zip(tasks, records):
        pool = wide[task['id']]
        order = rec['orders']['old']
        n = min(200, len(order))
        n100 = min(100, n)
        structural = features(task, pool, rec, n)
        pf = specialists['familiar'].predict_proba(structural)[:,1]
        ps = specialists['shifted'].predict_proba(structural)[:,1]
        score = np.asarray(rec['old_scores'], float)
        std = max(float(score.std()), .05)
        meta = np.stack((pf, ps, np.maximum(pf, ps),
                         np.abs(pf-ps), pf*ps,
                         (score[order[:n]]-score[order[0]])/std,
                         np.arange(n)/100.), axis=1).astype(np.float32)
        x = np.c_[structural, meta].astype(np.float32)
        head = lambda p, limit: max(range(limit),
            key=lambda i: (float(p[i]), -i))
        f100,s100 = head(pf,n100),head(ps,n100)
        f200,s200 = head(pf,n),head(ps,n)
        l = {'dual100': s100 if ps[s100]>pf[f100] else f100,
             'dual200': s200 if ps[s200]>pf[f200] else f200,
             'mean200': head((pf+ps)/2,n),
             'familiar200': f200,'shifted200': s200}
        for name, model in models.items():
            p = (predict_listwise(model,x) if name.endswith('_listwise')
                 else model.predict_proba(x)[:,1])
            l[name] = head(p,n)
        choices = {name:order[i] for name,i in l.items()}
        costs = {name: (2*n100 if name=='dual100' else
                        2*n if name in ('dual200','mean200',
                                        'familiar200','shifted200') else 3*n)
                 for name in choices}
        rows.append({'id':task['id'],'seed':task['seed'],
                     'pool_sha256':digest(pool),'choices':choices,
                     'candidate_scores':costs,
                     'top100_indices':order[:n100],
                     'top200_indices':order[:n]})
    return rows,time.perf_counter()-started


def manifest():
    files = ('sealed_bank.json','base_pools.json','ast_wide_pools.json',
             'frozen_records.json','public_choices.json')
    return {'protocol_sha256':sha(PROTOCOL),'script_sha256':sha(SCRIPT),
            'development_sha256':sha(DEVELOPMENT),
            'specialist_sha256':{'familiar':sha(FAMILIAR),'shifted':sha(SHIFTED)},
            'model_sha256':{name:sha(TRAINED/f'{name}.joblib') for name in LEARNED},
            'prior_model_sha256':sha(PRIOR),'seeds':list(SEEDS),'tasks':192,
            'frozen_sha256':{name:sha(DEST/name) for name in files}}


def verify_manifest():
    saved=json.loads((DEST/'manifest.json').read_text())
    expected=manifest()
    assert all(saved[key]==value for key,value in expected.items())
    return saved


def prepare():
    if DEST.exists():raise RuntimeError('run already exists')
    dev=json.loads(DEVELOPMENT.read_text())
    assert dev['scope']=='opened development only'
    tasks=tasks_for()
    base,wide,_,records,_,_,cost=public_run(tasks)
    rows,decision_seconds=choices_for(tasks,wide,records,
                                      load_models(),models_for())
    DEST.mkdir(parents=True)
    for name,value in (('sealed_bank.json',tasks),('base_pools.json',base),
                       ('ast_wide_pools.json',wide),
                       ('frozen_records.json',records),
                       ('public_choices.json',rows)):
        write_json(DEST/name,value)
    source=dev['source']
    write_json(DEST/'manifest.json',{**manifest(),
        'source_candidate_labels':source,
        'generation_cost':cost,'public_decision_wall_seconds':decision_seconds})
    print(json.dumps({'frozen':True,'tasks':len(tasks),
        'source_candidate_labels':source,'generation_cost':cost,
        'public_decision_wall_seconds':decision_seconds},indent=2))


def outcome_rows(tasks,wide,rows):
    outcome=[];checked=0
    for task,row in zip(tasks,rows):
        pool=wide[task['id']]
        assert task['id']==row['id'] and digest(pool)==row['pool_sha256']
        labels=[int(bool(evaluate_program(item['program'],task['hidden'][8:])))
                for item in pool]
        checked+=len(labels)
        outcome.append({'id':task['id'],'seed':task['seed'],
            'domain':'shifted' if task['family']=='shifted_ast' else 'familiar',
            'labels':{name:labels[index] for name,index in row['choices'].items()},
            'top100_reachable':int(any(labels[i] for i in row['top100_indices'])),
            'top200_reachable':int(any(labels[i] for i in row['top200_indices'])),
            'full_reachable':int(any(labels))})
    return outcome,checked


def contrast(banks,a,b):
    d=[row[a]-row[b] for row in banks]
    return {'gain':sum(d),'positive_banks':sum(v>0 for v in d),
            'negative_banks':sum(v<0 for v in d),'interval':interval(d),
            'bank_differences':d}


def summarize(outcome,rows,checked):
    banks=[]
    for seed in SEEDS:
        ids=[i for i,r in enumerate(outcome) if r['seed']==seed]
        bank={'seed':seed,**{field:sum(outcome[i][field] for i in ids)
            for field in ('top100_reachable','top200_reachable','full_reachable')}}
        for name in NAMES:
            bank[name]=sum(outcome[i]['labels'][name] for i in ids)
            bank[name+'_candidate_scores']=sum(rows[i]['candidate_scores'][name]
                                               for i in ids)
            for domain in ('familiar','shifted'):
                bank[name+'_'+domain]=sum(outcome[i]['labels'][name] for i in ids
                                          if outcome[i]['domain']==domain)
        banks.append(bank)
    totals={key:sum(b[key] for b in banks) for key in banks[0] if key!='seed'}
    names=('early_listwise','scrambled_listwise','duplicate_listwise',
           'later_bce','dual200','prior_stack','mean200')
    comparisons={f'later_listwise_minus_{name}':contrast(banks,'later_listwise',name)
                 for name in names}
    objective=comparisons['later_listwise_minus_later_bce']
    early=comparisons['later_listwise_minus_early_listwise']
    dual=comparisons['later_listwise_minus_dual200']
    prior=comparisons['later_listwise_minus_prior_stack']
    growth=(all(comparisons[f'later_listwise_minus_{name}']['gain']>=5 for name in
                ('early_listwise','scrambled_listwise','duplicate_listwise')) and
            early['interval'][0]>0 and early['positive_banks']>=8)
    objective_gate=(objective['gain']>=6 and objective['interval'][0]>0 and
                    objective['positive_banks']>=10)
    integration=(dual['gain']>=8 and prior['gain']>=8 and
                 dual['interval'][0]>0 and prior['interval'][0]>0 and
                 dual['positive_banks']>=12 and
                 totals['later_listwise_familiar']>=totals['familiar200_familiar']-8 and
                 totals['later_listwise_shifted']>=totals['shifted200_shifted']-8)
    return {'tasks':len(outcome),'candidate_labels_checked':checked,
            'totals':totals,'comparisons':comparisons,
            'gates':{'objective':objective_gate,'incremental_feedback':growth,
                     'integration':integration},'banks':banks}


def score():
    if (DEST/'results.json').exists():raise RuntimeError('already scored')
    verify_manifest()
    tasks=json.loads((DEST/'sealed_bank.json').read_text())
    wide=json.loads((DEST/'ast_wide_pools.json').read_text())
    rows=json.loads((DEST/'public_choices.json').read_text())
    outcome,checked=outcome_rows(tasks,wide,rows)
    summary=summarize(outcome,rows,checked)
    write_json(DEST/'results.json',{'manifest_sha256':sha(DEST/'manifest.json'),
                                   'summary':summary,'tasks':outcome})
    print(json.dumps({k:v for k,v in summary.items() if k!='banks'},indent=2))


def audit():
    if (DEST/'audit.json').exists():raise RuntimeError('already audited')
    m=verify_manifest()
    tasks=tasks_for()
    assert normalize(tasks)==json.loads((DEST/'sealed_bank.json').read_text())
    base,wide,_,records,_,_,cost=public_run(tasks)
    rows,_=choices_for(tasks,wide,records,load_models(),models_for())
    for name,value in (('base_pools.json',base),('ast_wide_pools.json',wide),
                       ('frozen_records.json',records),
                       ('public_choices.json',rows)):
        assert normalize(value)==json.loads((DEST/name).read_text()),name
    stable=('base_candidates','extra_ast_candidates',
            'predicted_output_cells','e0_candidate_scores',
            'post_query_candidate_scores')
    assert all(cost[key]==m['generation_cost'][key] for key in stable)
    outcome,checked=outcome_rows(tasks,wide,rows)
    summary=summarize(outcome,rows,checked)
    saved=json.loads((DEST/'results.json').read_text())
    assert saved=={'manifest_sha256':sha(DEST/'manifest.json'),
                   'summary':summary,'tasks':outcome}
    result={'passed':True,'tasks_rebuilt':len(tasks),
            'candidate_output_cells_rebuilt':cost['predicted_output_cells'],
            'candidate_model_predictions_rebuilt':sum(
                len(r['top200_indices'])*9 for r in rows),
            'candidate_labels_rebuilt':checked,
            'source_model_files_verified':len(LEARNED)+1}
    write_json(DEST/'audit.json',result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    {'prepare':prepare,'score':score,'audit':audit}[sys.argv[1]]()
