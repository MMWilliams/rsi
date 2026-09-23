"""Development-only comparison on previously inspected archives."""
import json
import time
import numpy as np
from rsi.common import ROOT,write_json
from rsi.semantic_invention import evaluate_program
from seed_growth import METHODS,representation,train,predict,pick,base_index,contextual_proposals,integrate


def read(path): return json.loads(path.read_text(encoding='utf-8'))


def records_from_archive(name):
    root=ROOT/'runs'/name; banks=read(root/'protected_banks.json'); pools=read(root/'candidate_pools.json')
    result={}
    for split,tasks in banks.items():
        records=[]
        for task in tasks:
            unique={}
            for row in pools[task['id']]:
                if row['source'] in ('v67','v73'):
                    unique.setdefault(row['program'],{key:value for key,value in row.items() if key!='oracle_correct'})
            rows=list(unique.values()); public={'id':task['id'],'visible':task['visible']}
            labels=np.array([int(evaluate_program(r['program'],task['visible']+task['hidden'])) for r in rows])
            records.append({'id':task['id'],'public':public,'rows':rows,'features':representation(public,rows),'labels':labels})
        result[split]=records
    return result


def summarize(model,records,feedback,integrations=True):
    result={'n':len(records),'base':0,'reachable':0,**{name:0 for name in METHODS}}
    if integrations: result.update({'fixed_pair':0,'global':0,'contextual':0})
    for record in records:
        labels=record['labels']; b=base_index(record['rows'])
        result['base']+=int(labels[b]) if b is not None else 0
        result['reachable']+=int(any(labels))
        for name,scores in predict(model,record).items():
            ix=pick(record,scores); result[name]+=int(labels[ix]) if ix is not None else 0
        if integrations:
            for name,proposals in [('fixed_pair',['structural','behavior']),
                 ('global',contextual_proposals(feedback,model,record,False)[0]),
                 ('contextual',contextual_proposals(feedback,model,record,True)[0])]:
                ix,_=integrate(model,record,proposals); result[name]+=int(labels[ix]) if ix is not None else 0
    return result


if __name__=='__main__':
    started=time.perf_counter()
    source=records_from_archive('policy-transfer-20260917b')
    panels={**records_from_archive('incremental-feedback-20260917'),**records_from_archive('incremental-feedback-ast-20260917')}
    feedback=[]; output=[]
    for round,split in enumerate(('development','admission','transfer_203212','transfer_203213','transfer_203214')):
        feedback+=source[split]; model=train(feedback)
        scores={name:summarize(model,records,feedback) for name,records in panels.items()}
        output.append({'round':round,'feedback_tasks':len(feedback),'panels':scores})
        print(json.dumps(output[-1]),flush=True)
    report={'status':'development_only','checkpoints':output,'seconds':time.perf_counter()-started,
            'warning':'all panels previously inspected; no confirmation or promotion claim'}
    write_json(ROOT/'analysis/seed-growth-development.json',report)
