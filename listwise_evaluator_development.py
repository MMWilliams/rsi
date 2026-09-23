"""Development-only linear and nonlinear listwise evaluator training edits."""
from __future__ import annotations

import json

import numpy as np
import torch

from rsi.common import ROOT,write_json
from mixed_evaluator_transfer import choose
from pairwise_evaluator_development import target_b
from mixed_probe_diagnostic import bool_safe_structure
import seed_growth


SOURCE=ROOT/'analysis/mixed-evaluator-source.json'
TARGET_A=ROOT/'analysis/improver-acquisition-target-development.json'
OUT=ROOT/'analysis/listwise-evaluator-development-v2.json'
EPOCHS=(40,80,120)
SEED=902500


class Ranker(torch.nn.Module):
    def __init__(self,width):
        super().__init__()
        self.layers=(torch.nn.Linear(175,1) if width==0 else
                     torch.nn.Sequential(torch.nn.Linear(175,width),
                                         torch.nn.ReLU(),torch.nn.Linear(width,1)))
    def forward(self,x):return self.layers(x).flatten()


def pack(rows):
    x=np.concatenate([np.asarray(r['structural'],dtype=np.float32) for r in rows])
    y=np.concatenate([np.asarray(r['labels'],dtype=bool) for r in rows])
    sizes=[r['n'] for r in rows]
    return x,y,sizes


def score(model,mean,scale,tasks,device):
    correct=0;reachable=0
    with torch.no_grad():
        for task in tasks:
            if not task['n']:continue
            x=(np.asarray(task['structural'],dtype=np.float32)-mean)/scale
            logits=model(torch.from_numpy(x).to(device)).cpu().numpy()
            index=choose(logits,[{'program':p} for p in task['programs']])
            correct+=bool(task['labels'][index]);reachable+=any(task['labels'])
    return {'correct':correct,'reachable':reachable,'tasks':len(tasks)}


def train_variant(name,width,source,a,b,device):
    torch.manual_seed(SEED+width)
    np.random.seed(SEED+width)
    x,y,sizes=pack(source)
    mean=x.mean(axis=0);scale=np.maximum(x.std(axis=0),.05)
    tx=torch.from_numpy((x-mean)/scale).to(device)
    ty=torch.from_numpy(y).to(device)
    model=Ranker(width).to(device)
    optimizer=torch.optim.AdamW(model.parameters(),lr=.001,weight_decay=.001)
    results={};weights={}
    offsets=np.cumsum([0,*sizes])
    for epoch in range(1,max(EPOCHS)+1):
        model.train();optimizer.zero_grad()
        logits=model(tx)
        losses=[]
        for i in range(len(sizes)):
            left,right=offsets[i],offsets[i+1]
            mask=ty[left:right]
            if not bool(mask.any()) or bool(mask.all()):continue
            values=logits[left:right]
            losses.append(torch.logsumexp(values,0)-torch.logsumexp(values[mask],0))
        loss=torch.stack(losses).mean()
        loss.backward();optimizer.step()
        if epoch in EPOCHS:
            model.eval()
            results[str(epoch)]={'source':score(model,mean,scale,source,device),
                                 'A':score(model,mean,scale,a,device),
                                 'B':score(model,mean,scale,b,device),
                                 'training_loss':float(loss.detach().cpu())}
            weights[str(epoch)]={key:value.detach().cpu().numpy().tolist()
                                  for key,value in model.state_dict().items()}
    return {'width':width,'normalization_mean':mean.tolist(),
            'normalization_scale':scale.tolist(),
            'scores':results,'checkpoint_weights':weights}


def main():
    seed_growth.structure=bool_safe_structure
    source=json.loads(SOURCE.read_text(encoding='utf-8'))['tasks']
    a=json.loads(TARGET_A.read_text(encoding='utf-8'))
    b=target_b()
    device='cuda' if torch.cuda.is_available() else 'cpu'
    variants={name:train_variant(name,width,source,a,b,device)
              for name,width in [('mlp32',32)]}
    summary={'scope':'development only; target labels previously inspected',
             'device':device,'source_tasks':len(source),'source_candidate_labels':
             sum(r['n'] for r in source),'seed':SEED,'epochs':EPOCHS,
             'results':{name:row['scores'] for name,row in variants.items()}}
    write_json(OUT,{'summary':summary,'variants':variants})
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
