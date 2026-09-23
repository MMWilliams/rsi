"""Freeze two-evaluator router trained on inspected whole-task feedback."""
import hashlib
import json

from rsi.common import ROOT,write_json
from evaluator_router_development import fit,SOURCE


OUT=ROOT/'analysis/evaluator-router-frozen.json'


def main():
    raw=SOURCE.read_bytes()
    episodes=json.loads(raw)['episodes']
    rows=[*episodes[0]['tasks'],*episodes[1]['tasks']]
    scale,w,n=fit(rows)
    report={'scope':'frozen before new evaluator-router transfer',
            'source_sha256':hashlib.sha256(raw).hexdigest(),
            'source_tasks':len(rows),'decisive_feedback_tasks':n,
            'scale':scale.tolist(),'weights':w.tolist(),
            'component_file':'analysis/pairwise-evaluator-development.json'}
    write_json(OUT,report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('scale','weights')},indent=2))


if __name__=='__main__':main()
