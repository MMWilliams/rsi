"""Incremental feedback learning with separate evaluator and improver endpoints."""
from __future__ import annotations
import argparse, json, random, shutil, time
from pathlib import Path
import numpy as np
from rsi.common import ROOT, Journal, digest, write_json, verify_journal
from rsi.retention_run import file_hash, seal_artifacts
from rsi.semantic_invention import evaluate_program
from rsi.evolving_domain import make_task
from run_policy_transfer import FROZEN, select
from stitch_ten import mixed_banks, source_candidates

SOURCE = 'runs/policy-transfer-20260917b'
ARMS = ('v67', 'v73')
SEEDS = (203301, 203302)
STEPS = 240

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def unique(rows):
    result={}
    for row in rows: result.setdefault(row['program'],row)
    return list(result.values())

def menu():
    result = []
    for name, index, value in [('prefer_v67',7,500),('prefer_v73',10,500),
        ('shorter',6,-5),('longer',6,1),('more_div',0,200),('less_div',0,-100),
        ('more_mul',1,150),('more_xor',2,150),('more_not',5,150),('no_length_penalty',6,0)]:
        weights = list(FROZEN); weights[index] = value
        result.append({'name':name,'weights':weights})
    return result

def x(row):
    p = row['program']
    return [p.count(op)/4 for op in ('div','mul','xor','mask','shr','not')] + [len(p)/1000,
        float(row['source']=='v67'),float(row['source']=='v73'),1.0]

def probability(rows, weights):
    if not rows: return []
    z = np.clip(np.array([x(r) for r in rows]) @ np.array(weights), -30, 30)
    return (1/(1+np.exp(-z))).tolist()

def fit(tasks, pools):
    records=[]; labels=[]; mass=[]
    for task in tasks:
        rows=pools[task['id']]
        for row in rows:
            records.append(x(row)); labels.append(float(row['oracle_correct'])); mass.append(1/max(1,len(rows)))
    a=np.array(records); y=np.array(labels); m=np.array(mass); m/=m.sum()
    w=np.zeros(10)
    for _ in range(STEPS):
        pred=1/(1+np.exp(-np.clip(a@w,-30,30)))
        penalty=w.copy(); penalty[-1]=0
        w-=0.4*(a.T@((pred-y)*m)+0.02*penalty)
    return w.tolist()

def policy_programs(tasks,pools,weights):
    return [(select(pools[t['id']],ARMS,weights) or {}).get('program','') for t in tasks]

def learn_edits(tasks,pools):
    base=policy_programs(tasks,pools,FROZEN)
    labels={t['id']:{r['program']:r['oracle_correct'] for r in pools[t['id']]} for t in tasks}
    records=[]
    for edit in menu():
        programs=policy_programs(tasks,pools,edit['weights'])
        gains=[int(labels[t['id']].get(p,False))-int(labels[t['id']].get(b,False))
               for t,p,b in zip(tasks,programs,base)]
        records.append({'name':edit['name'],'gain':sum(gains),'support':len(tasks),
                        'harmful':sum(g<0 for g in gains)})
    order=sorted(range(len(records)),key=lambda i:(-records[i]['gain'],records[i]['harmful'],i))
    return order,records

def decisions(training,training_pools,banks,pools):
    seen=list(training['development'])
    states=[{'round':0,'evaluator':fit(seen,training_pools),'edit_order':list(range(len(menu()))),'edit_effects':[]}]
    for index,split in enumerate(('admission','transfer_203212','transfer_203213','transfer_203214'),1):
        seen+=training[split]
        order,effects=learn_edits(seen,training_pools)
        states.append({'round':index,'evaluator':fit(seen,training_pools),'edit_order':order,'edit_effects':effects})
    output={}
    for bank,tasks in banks.items():
        output[bank]={}
        for state in states:
            probs={t['id']:dict(zip([r['program'] for r in pools[t['id']]],probability(pools[t['id']],state['evaluator']))) for t in tasks}
            evaluator_choices=[]
            for t in tasks:
                rows=pools[t['id']]; ps=probability(rows,state['evaluator'])
                ix=max(range(len(rows)),key=lambda i:(ps[i],-len(rows[i]['program']),rows[i]['program'])) if rows else None
                evaluator_choices.append(rows[ix]['program'] if ix is not None else '')
            crosses={}
            scrambled=list(state['edit_order']); random.Random(918+state['round']).shuffle(scrambled)
            for label,order,ev in [('I0_E0',states[0]['edit_order'],states[0]['evaluator']),
                ('It_E0',state['edit_order'],states[0]['evaluator']),('I0_Et',states[0]['edit_order'],state['evaluator']),
                ('It_Et',state['edit_order'],state['evaluator']),('scrambled_Et',scrambled,state['evaluator'])]:
                values={t['id']:dict(zip([r['program'] for r in pools[t['id']]],probability(pools[t['id']],ev))) for t in tasks}
                alternatives=[{'name':'base','weights':list(FROZEN)}]+[menu()[i] for i in order[:2]]
                evaluated=[]
                for edit in alternatives:
                    programs=policy_programs(tasks,pools,edit['weights'])
                    utility=sum(values[t['id']].get(p,0.0) for t,p in zip(tasks,programs))
                    evaluated.append({'edit':edit['name'],'predicted_utility':utility,'programs':programs})
                picked=max(range(len(evaluated)),key=lambda i:(evaluated[i]['predicted_utility'],-i))
                crosses[label]={'proposals':[e['name'] for e in alternatives[1:]],'alternatives':evaluated,
                                'selected':evaluated[picked]}
            output[bank][str(state['round'])]={'probabilities':probs,'evaluator_programs':evaluator_choices,'crosses':crosses}
    return {'checkpoints':states,'decisions':output}

def grade(banks,pools,chosen):
    result={}
    for bank,tasks in banks.items():
        labels={t['id']:{r['program']:bool(evaluate_program(r['program'],t['visible']+t['hidden'])) for r in pools[t['id']]} for t in tasks}
        def count(programs): return sum(labels[t['id']].get(p,False) for t,p in zip(tasks,programs))
        base=count(policy_programs(tasks,pools,FROZEN))
        rounds={}
        for checkpoint,row in chosen['decisions'][bank].items():
            errors=[]
            for t in tasks:
                rs=pools[t['id']]
                if rs: errors.append(sum((row['probabilities'][t['id']][r['program']]-int(labels[t['id']][r['program']]))**2 for r in rs)/len(rs))
            rounds[checkpoint]={'evaluator_correct':count(row['evaluator_programs']),
                'task_balanced_brier':sum(errors)/len(errors) if errors else None,
                'crosses':{name:{'correct':count(c['selected']['programs']),'gain_over_base':count(c['selected']['programs'])-base,
                                 'edit':c['selected']['edit']} for name,c in row['crosses'].items()}}
        result[bank]={'n':len(tasks),'base_correct':base,'reachable':sum(any(labels[t['id']].values()) for t in tasks),'rounds':rounds}
    return result

def make_banks(panel='mixed'):
    if panel=='ast':
        banks={}
        for seed in (203303,203304):
            rng=random.Random(seed)
            banks[str(seed)]=[dict(make_task(rng,'final',i,'ast_transition',8,13),family='ast_transition') for i in range(12)]
        return banks
    return {str(seed):mixed_banks({'bank_seed':seed,'bank_counts':{'final':12},'visible_examples':8,'hidden_examples':13})['final'] for seed in SEEDS}

def run(output,panel='mixed'):
    output.mkdir(parents=True,exist_ok=False); journal=Journal(output/'events.jsonl')
    paths=list((ROOT/'rsi').glob('*.py'))+[ROOT/n for n in ('incremental_feedback.py','run_policy_transfer.py','stitch_ten.py','run_ast_v66.py','EXPERIMENT-incremental-feedback.md','EXPERIMENT-incremental-feedback-ast.md')]
    hashes={p.relative_to(ROOT).as_posix():file_hash(p) for p in paths}
    for p in paths:
        dest=output/'source'/p.relative_to(ROOT); dest.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(p,dest)
    write_json(output/'source_manifest.json',hashes)
    write_json(output/'config.json',{'panel':panel})
    training=read(ROOT/SOURCE/'protected_banks.json'); old=read(ROOT/SOURCE/'candidate_pools.json')
    old={key:unique([r for r in rows if r['source'] in ARMS]) for key,rows in old.items()}
    write_json(output/'feedback_banks.json',training); write_json(output/'feedback_pools.json',old)
    journal.append('protocol_frozen',{'source':SOURCE,'source_hashes':hashes,'seeds':(203303,203304) if panel=='ast' else SEEDS,'panel':panel,'fit_steps':STEPS,'menu':menu(),
        'feedback_sha256':digest([training,old])})
    banks=make_banks(panel); write_json(output/'protected_banks.json',banks)
    old_content={digest([t['visible'],t['hidden']]) for tasks in training.values() for t in tasks}
    assert all(digest([t['visible'],t['hidden']]) not in old_content for tasks in banks.values() for t in tasks)
    pools={}; costs={arm:{'seconds':0.,'calls':0,'candidates':0} for arm in ARMS}
    for bank,tasks in banks.items():
        for t in tasks:
            pools[t['id']]=[]
            for arm in ARMS:
                start=time.perf_counter(); rows=source_candidates({'id':t['id'],'visible':t['visible']},arm,{},8)
                costs[arm]['seconds']+=time.perf_counter()-start; costs[arm]['calls']+=1; costs[arm]['candidates']+=len(rows)
                pools[t['id']]+=rows
            pools[t['id']]=unique(pools[t['id']])
        print('candidate bank closed: '+bank,flush=True)
    write_json(output/'candidate_pools.json',pools)
    chosen=decisions(training,old,banks,pools)
    write_json(output/'frozen_decisions.json',chosen); journal.append('all_decisions_frozen',{'sha256':digest(chosen)})
    result=grade(banks,pools,chosen)
    write_json(output/'results.json',result); write_json(output/'generation_costs.json',costs)
    write_json(output/'learning_costs.json',{'logistic_fit_iterations':STEPS*5,'checkpoint_count':5,
        'edit_feedback_task_evaluations':sum((24+12*i)*len(menu()) for i in range(4)),
        'source_archive_acquisition_excluded_from_incremental_cost':True,
        'proposal_allowance':2,'note':'shared pools; authored fixed edits; source archive acquisition must be charged for end-to-end claims'})
    assert all(file_hash(ROOT/name)==sha for name,sha in hashes.items())
    journal.append('completed',{'sha256':digest(result)}); seal_artifacts(output)
    return result

def audit(output):
    for name,row in read(output/'artifact_manifest.json').items(): assert file_hash(output/name)==row['sha256'],name
    for name,sha in read(output/'source_manifest.json').items():
        assert file_hash(output/'source'/name)==sha and file_hash(ROOT/name)==sha,name
    cfg=read(output/'config.json') if (output/'config.json').exists() else {'panel':'mixed'}
    banks=make_banks(cfg['panel']); assert digest(banks)==digest(read(output/'protected_banks.json'))
    training=read(output/'feedback_banks.json'); old=read(output/'feedback_pools.json'); pools=read(output/'candidate_pools.json')
    labels=0
    for tasks in training.values():
        for t in tasks:
            for row in old[t['id']]:
                assert row['oracle_correct']==bool(evaluate_program(row['program'],t['visible']+t['hidden'])); labels+=1
    for tasks in banks.values():
        for t in tasks:
            expected=unique([r for arm in ARMS for r in source_candidates({'id':t['id'],'visible':t['visible']},arm,{},8)])
            assert digest(expected)==digest(pools[t['id']])
            assert all('oracle_correct' not in r for r in pools[t['id']])
    chosen=decisions(training,old,banks,pools); assert digest(chosen)==digest(read(output/'frozen_decisions.json'))
    result=grade(banks,pools,chosen); assert digest(result)==digest(read(output/'results.json'))
    events=[json.loads(line) for line in (output/'events.jsonl').read_text().splitlines()]
    assert verify_journal(output/'events.jsonl')==len(events)
    assert [e['kind'] for e in events]==['protocol_frozen','all_decisions_frozen','completed']
    assert events[1]['payload']['sha256']==digest(chosen) and events[2]['payload']['sha256']==digest(result)
    report={'status':'passed','candidate_calls_replayed':48,'feedback_labels_rechecked':labels,'checkpoints_replayed':5,
            'scope':'deterministic replay using the same host interpreter; no independent semantic oracle'}
    write_json(output/'audit.json',report); return report

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('output'); parser.add_argument('--audit',action='store_true')
    parser.add_argument('--panel',choices=('mixed','ast'),default='mixed'); args=parser.parse_args()
    print(json.dumps(audit(ROOT/args.output) if args.audit else run(ROOT/args.output,args.panel),indent=2))
