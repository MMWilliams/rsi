"""Transferable effect knowledge for selecting feedback tactics."""
import numpy as np
from seed_source_search import TACTICS,query_values


def restore_model(saved):
    return {key:np.array(value,dtype=np.uint64 if key=='boundary' else float) for key,value in saved.items()}


def state_features(model,remaining,driver,round,admission_correct,admission_count):
    values=[query_values(model,r,driver) for r in remaining]
    columns=np.array([[v['uncertainty'],v['disagreement'],v['novelty']] for v in values])
    if not len(columns): columns=np.zeros((1,3))
    return [*columns.mean(axis=0),*columns.max(axis=0),round/4,
            admission_correct/max(1,admission_count),sum(bool(r['rows']) for r in remaining)/max(1,len(remaining))]


def extract_effects(source_result,records):
    effects=[]
    for name,episode in source_result['episodes'].items():
        driver=episode['driver']; checkpoints=episode['checkpoints']
        for round in range(1,len(checkpoints)):
            parent=checkpoints[round-1]; child=checkpoints[round]
            model=restore_model(parent['model'])
            remaining=[r for r in records['reservoir'] if r['id'] not in set(parent['feedback_ids'])]
            old=parent['admission'][driver]; new=child['admission'][driver]
            n=len(old['rows'])
            harmed=sum(a['correct'] and not b['correct'] for a,b in zip(old['rows'],new['rows']))
            effects.append({'episode':name,'round':round,'driver':driver,'tactic':episode['tactic'],
                'state':state_features(model,remaining,driver,round-1,old['correct'],n),
                'gain':(new['correct']-old['correct'])/n,'harm':harmed/n,
                'utility':(new['correct']-old['correct']-.25*harmed)/n})
    return effects


def choose_tactic(effects,driver,state):
    relevant=[r for r in effects if r['driver']==driver]
    if not relevant: return 'uniform',{'uniform':0.}
    context=np.asarray(state)
    scored={}
    for tactic in TACTICS:
        examples=[r for r in relevant if r['tactic']==tactic]
        if not examples:
            scored[tactic]=0.; continue
        distances=np.array([np.mean((context-np.asarray(r['state']))**2) for r in examples])
        weight=np.exp(-distances/.035)
        utilities=np.array([r['utility'] for r in examples])
        # Shrink sparse evidence toward zero rather than treating one gain as certain.
        scored[tactic]=float((weight@utilities)/(weight.sum()+1.0))
    selected=max(TACTICS,key=lambda tactic:(scored[tactic],-TACTICS.index(tactic)))
    return selected,scored
