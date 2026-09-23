"""Freeze structural evaluator checkpoints and a within-task scrambled control."""
import hashlib
import json

import numpy as np

from rsi.common import ROOT,write_json
from mixed_evaluator_source import train


SOURCE=ROOT/'analysis/mixed-evaluator-source.json'
OUT=ROOT/'analysis/mixed-evaluator-checkpoints.json'


def main():
    raw=SOURCE.read_bytes()
    source=json.loads(raw)
    rows=source['tasks']
    assert len(rows)==192
    weights={'E0':source['initial_weights']}
    for count in (48,96,192):
        weights[f'E{count}']=train(rows[:count]).tolist()
    assert np.allclose(weights['E192'],source['full_weights'],atol=0,rtol=0)
    scrambled=[]
    for row in rows:
        copy=dict(row)
        y=np.asarray(row['labels'],dtype=int).copy()
        seed=int.from_bytes(hashlib.sha256(('scramble:'+row['id']).encode()).digest()[:8],
                            'little')
        np.random.default_rng(seed).shuffle(y)
        copy['labels']=y.tolist()
        scrambled.append(copy)
    weights['scrambled192']=train(scrambled).tolist()
    report={'scope':'frozen prior to fresh evaluator checkpoint transfer',
            'source_sha256':hashlib.sha256(raw).hexdigest(),
            'training_tasks':{'E0':0,'E48':48,'E96':96,'E192':192,
                              'scrambled192':192},
            'training_candidate_labels':{name:sum(r['n'] for r in rows[:count])
                for name,count in [('E48',48),('E96',96),('E192',192),
                                   ('scrambled192',192)]},
            'weights':weights}
    write_json(OUT,report)
    print(json.dumps({k:v for k,v in report.items() if k!='weights'},indent=2))


if __name__=='__main__':main()
