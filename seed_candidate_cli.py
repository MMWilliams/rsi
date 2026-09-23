"""Visible-only inference entry point for an exported seed candidate."""
import argparse,json
from pathlib import Path
from seed_growth import representation,predict,pick,base_index
from seed_meta import restore_model
from seed_source_search import read
from stitch_ten import source_candidates


def solve(public,state):
    if set(public)!={'id','visible'}: raise ValueError('public task must contain only id and visible')
    unique={}
    for arm in ('v67','v73'):
        for row in source_candidates(public,arm,{},state['candidate_cap_per_source']): unique.setdefault(row['program'],row)
    rows=list(unique.values()); record={'id':public['id'],'public':public,'rows':rows,'features':representation(public,rows)}
    model=restore_model(state['model']); scores=predict(model,record)[state['driver']]
    proposed=pick(record,scores); base=base_index(rows)
    deployed=proposed if base is None or (proposed is not None and scores[proposed]>scores[base]+state['deployment_margin']) else base
    return {'program':rows[deployed]['program'] if deployed is not None else '',
        'candidate_count':len(rows),'driver':state['driver'],'status':state['status'],
        'base_index':base,'evaluator_index':proposed,'deployed_index':deployed,
        'note':'prediction only; no oracle correctness is claimed'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('public_task'); parser.add_argument('--state',default='output/seed-improver-candidate/state.json')
    args=parser.parse_args(); print(json.dumps(solve(read(Path(args.public_task)),read(Path(args.state))),indent=2))
