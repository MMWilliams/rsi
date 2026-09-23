"""Compact descriptive results; no checkpoint selection from confirmation labels."""
import json
from rsi.common import ROOT,write_json
from seed_source_search import read


def summarize():
    root=ROOT/'runs/seed-confirmation-20260917'
    results=read(root/'results.json'); frozen=read(root/'frozen_loops.json')
    summary={}
    for name,arm in results.items():
        curves=[]
        for checkpoint in arm['rounds']:
            panels=checkpoint['panels']
            curves.append({'round':checkpoint['round'],
                'evaluator':sum(p['counts']['ensemble'] for p in panels.values()),
                'deployed':sum(p['counts']['deployed'] for p in panels.values()),
                'panels':{panel:{'n':row['n'],'evaluator':row['counts']['ensemble'],'deployed':row['counts']['deployed'],
                    'base':row['counts']['base'],'reachable':row['reachable']} for panel,row in panels.items()}})
        last=arm['rounds'][-1]
        blocked=[]; rescued=[]
        final_prediction=frozen['arms'][name]['checkpoints'][-1]['final_predictions']
        for panel,row in last['panels'].items():
            for task in row['tasks']:
                if task['ensemble'] and not task['deployed']:
                    pred=final_prediction[panel][task['id']]; scores=pred['probabilities']['ensemble']
                    blocked.append({'id':task['id'],'panel':panel,'score_gap':scores[pred['indices']['ensemble']]-scores[pred['base']]})
                if task['deployed'] and not task['ensemble']: rescued.append(task['id'])
        summary[name]={'curve':curves,'mean_evaluator_correct_across_rounds':sum(r['evaluator'] for r in curves)/5,
            'candidate_queries':arm['candidate_queries'],
            'actions':[c['action'] for c in frozen['arms'][name]['checkpoints']],
            'accepted_rounds':[c['round'] for c in frozen['arms'][name]['checkpoints'] if c['accepted']],
            'deployment_blocked_correct':blocked,'deployment_rescued':rescued}
    artifact={'scope':'one confirmation episode; pooled counts descriptive; panels separately recorded',
        'driver':frozen['driver'],'gate':frozen['gate'],'arms':summary}
    write_json(ROOT/'analysis/seed-confirmation-summary.json',artifact)
    print(json.dumps({name:{'evaluator_curve':[r['evaluator'] for r in row['curve']],
          'deployed_curve':[r['deployed'] for r in row['curve']], 'candidate_queries':row['candidate_queries'],
          'blocked_correct':len(row['deployment_blocked_correct']), 'rescued':len(row['deployment_rescued'])}
          for name,row in summary.items()},indent=2))


if __name__=='__main__': summarize()
