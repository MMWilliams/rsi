"""Visible-only evaluator representations and feedback-conditioned integration.

No task references, hidden examples, or oracle labels are accepted by feature builders.
"""
from __future__ import annotations

import hashlib
import json
from functools import lru_cache
import numpy as np

from rsi.common import canonical
from rsi.invented_space import _split_atoms
from rsi.semantic_invention import parse_span, _char_predicate
from run_policy_transfer import FROZEN, select

ARMS = ('v67', 'v73')
METHODS = ('lexical', 'structural', 'behavior', 'ensemble', 'guarded')


def base_index(rows):
    chosen = select(rows, ARMS, FROZEN)
    return rows.index(chosen) if chosen is not None else None


@lru_cache(maxsize=30000)
def structure(program):
    """Preserve opcode paths and numeric values, rather than operation counts alone."""
    parsed=[]
    if program.startswith('Concat('):
        for atom in _split_atoms(program[7:-1]):
            span=parse_span(atom)
            if span is not None: parsed.extend(span)
    features=np.zeros(128,dtype=float)
    def add(token,value=1.):
        h=hashlib.sha256(token.encode()).digest()
        features[int.from_bytes(h[:4],'little')%len(features)]+=value*(1 if h[4]%2 else -1)
    def visit(node,path):
        if isinstance(node,dict):
            add(path+':keys:'+','.join(sorted(k for k in node if k not in ('complexity','macro_id'))))
            for key,value in sorted(node.items()):
                if key not in ('complexity','macro_id'): visit(value,path+'/'+key)
        elif isinstance(node,list):
            for i,item in enumerate(node): visit(item,path+'/'+str(i))
        else:
            add(path+'='+str(node))
            if isinstance(node,(int,float)): add(path+':numeric',float(np.sign(node)*np.log1p(abs(node))/5))
    visit(parsed,'root')
    return tuple(np.clip(features/4,-3,3))


@lru_cache(maxsize=30000)
def semantics(program,block):
    """Character-predicate behavior on 256 unlabelled probes and boundary structure."""
    signatures=[]; boundary=[]
    for atom in _split_atoms(program[7:-1]):
        span=parse_span(atom)
        if span is None: continue
        for end in span:
            boundary.append({k:v for k,v in end.items() if k!='predicate'})
            if end.get('kind')=='run':
                bits=tuple(int(_char_predicate(chr(block+i),end['predicate'])) for i in range(256))
                signatures.append(min(bits,tuple(1-b for b in bits)))
    sig=signatures[0] if signatures else (0,)*256
    # Structure of the output boundaries separates behaviorally distinct slices.
    code=int.from_bytes(hashlib.sha256(canonical(boundary).encode()).digest()[:4],'little')
    return sig,code


def task_context(visible):
    chars=sorted({ord(c) for text,_ in visible for c in text})
    block=(min(chars)//256)*256 if chars else 0
    target={ord(c)-block for _,out in visible for c in out}
    other={c-block for c in chars}-target
    # All values derive from public examples. Family labels are deliberately absent.
    bins=np.zeros(32)
    for index in target:
        if 0<=index<256: bins[index//16]+=1
    for index in other:
        if 0<=index<256: bins[16+index//16]+=1
    bins/=max(1,len(chars))
    lengths=[len(out)/max(1,len(text)) for text,out in visible]
    scalars=[block/4096,len(chars)/256,(max(chars)-min(chars))/256 if chars else 0,
             float(np.mean(lengths)) if lengths else 0,
             float(np.mean([text.startswith(out) for text,out in visible])) if visible else 0]
    return block, np.r_[scalars,bins]


def representation(public,rows):
    block,ctx=task_context(public['visible'])
    lex=[]; structural=[]; behavior=[]; boundary=[]
    for row in rows:
        p=row['program']
        raw=[p.count(op)/4 for op in ('div','mul','xor','mask','shr','not')]
        raw += [len(p)/1000,float(row['source']=='v67'),float(row['source']=='v73'),1.]
        lex.append(raw)
        structural.append([*raw[:-1],*structure(p),*ctx,1.])
        sig,code=semantics(p,block)
        behavior.append(sig); boundary.append(code)
    return {'lexical':np.asarray(lex,dtype=float).reshape(len(rows),10),
            'structural':np.asarray(structural,dtype=float).reshape(len(rows),175),
            'behavior':np.asarray(behavior,dtype=float).reshape(len(rows),256),
            'boundary':np.asarray(boundary,dtype=np.uint64),'context':ctx,'block':block}


def logistic(x,y,mass):
    if not len(y): return np.zeros(x.shape[1])
    mass=np.asarray(mass); mass=mass/mass.sum()
    w=np.zeros(x.shape[1])
    for _ in range(240):
        pred=1/(1+np.exp(-np.clip(x@w,-30,30)))
        penalty=w.copy(); penalty[-1]=0
        w-=.35*(x.T@((pred-y)*mass)+.015*penalty)
    return w


def train(records):
    """Records contain public features plus feedback labels explicitly opened by host."""
    available=[r for r in records if len(r['labels'])]
    if not available: raise ValueError('feedback contains no candidates')
    labels=np.concatenate([r['labels'] for r in available])
    mass=np.concatenate([np.full(len(r['labels']),1/len(r['labels'])) for r in available])
    fitted={key:logistic(np.concatenate([r['features'][key] for r in available]),labels,mass)
            for key in ('lexical','structural')}
    fitted.update({'memory':np.concatenate([r['features']['behavior'] for r in available]),
        'boundary':np.concatenate([r['features']['boundary'] for r in available]),
        'block':np.concatenate([np.full(len(r['labels']),r['features']['block']) for r in available]),
        'labels':labels,'mass':mass})
    return fitted


def predict(model,record):
    cache=model.setdefault('_predictions',{})
    if record['id'] in cache: return cache[record['id']]
    f=record['features']; n=len(record['rows'])
    scores={key:1/(1+np.exp(-np.clip(f[key]@model[key],-30,30))) for key in ('lexical','structural')}
    behavior=[]
    for vector,boundary in zip(f['behavior'],f['boundary']):
        distance=np.mean(np.abs(model['memory']-vector),axis=1)
        distance+=.1*(model['boundary']!=boundary)
        distance+=.2*(model['block']!=f['block'])
        nearest=np.argsort(distance,kind='stable')[:16]
        weight=np.exp(-distance[nearest]/.035)*model['mass'][nearest]
        behavior.append(float((weight@model['labels'][nearest]+.01*.5)/(weight.sum()+.01)))
    scores['behavior']=np.asarray(behavior)
    scores['ensemble']=(scores['structural']+scores['behavior'])/2
    scores['guarded']=scores['ensemble'].copy()
    if n:
        base=base_index(record['rows'])
        scores['guarded'][base]+=.12
    cache[record['id']]=scores
    return scores


def pick(record,scores):
    if not len(record['rows']): return None
    return max(range(len(record['rows'])),key=lambda i:(float(scores[i]),-len(record['rows'][i]['program']),record['rows'][i]['program']))


def action_indices(model,record):
    predictions=predict(model,record)
    return {'base':base_index(record['rows']),**{name:pick(record,values) for name,values in predictions.items()}}


def contextual_proposals(training,model,record,contextual=True):
    """Predict gains of evaluator-installation edits from feedback task context."""
    context=record['features']['context']; effects=[]
    for prior in training:
        indices=action_indices(model,prior)
        base=prior['labels'][indices['base']] if indices['base'] is not None else 0
        gains=[(prior['labels'][indices[name]] if indices[name] is not None else 0)-base for name in METHODS]
        dist=float(np.mean((context-prior['features']['context'])**2))
        effects.append((dist,np.asarray(gains,dtype=float)))
    effects.sort(key=lambda item:item[0])
    chosen=effects[:12] if contextual else effects
    weights=np.exp(-np.array([item[0] for item in chosen])/.02) if contextual else np.ones(len(chosen))
    values=np.array([item[1] for item in chosen])
    mean=weights@values/max(weights.sum(),1e-12)
    # Penalty for local harmful outcomes. Ties preserve the declared method ordering.
    mean-=.25*(weights@(values<0))/max(weights.sum(),1e-12)
    order=sorted(range(len(METHODS)),key=lambda i:(-mean[i],i))
    return [METHODS[i] for i in order[:2]],mean.tolist()


def integrate(model,record,proposals,margin=.05):
    """Use learned joint evaluator to admit a candidate against the frozen base."""
    predictions=predict(model,record); indices=action_indices(model,record)
    base=indices['base']
    if base is None: return None,'base'
    best=base; origin='base'; utility=float(predictions['ensemble'][base])+margin
    for name in proposals:
        ix=indices[name]
        if ix is not None and float(predictions['ensemble'][ix])>utility:
            utility=float(predictions['ensemble'][ix]); best=ix; origin=name
    return best,origin
