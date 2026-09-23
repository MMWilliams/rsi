"""Descriptive v2 comparison; the primary arm remains predeclared."""
import json
from rsi.common import ROOT,write_json
from seed_source_search import read


def summarize():
    root=ROOT/'runs/seed-integration-v2-20260917'
    results=read(root/'results.json'); frozen=read(root/'frozen_loops.json'); summaries={}
    for name,arm in results.items():
        curve=[]
        for checkpoint in arm['rounds']:
            curve.append({'round':checkpoint['round'],'correct':sum(p['counts']['deployed'] for p in checkpoint['panels'].values()),
                'panels':{panel:{'n':p['n'],'correct':p['counts']['deployed'],'base':p['counts']['base'],
                    'behavior':p['counts']['behavior'],'reachable':p['reachable']} for panel,p in checkpoint['panels'].items()}})
        initial={row['id']:row for panel in arm['rounds'][0]['panels'].values() for row in panel['tasks']}
        last=[row for panel in arm['rounds'][-1]['panels'].values() for row in panel['tasks']]
        summaries[name]={'curve':curve,'net_gain':curve[-1]['correct']-curve[0]['correct'],
            'gained_tasks':[row['id'] for row in last if row['deployed'] and not initial[row['id']]['deployed']],
            'lost_tasks':[row['id'] for row in last if not row['deployed'] and initial[row['id']]['deployed']],
            'accepted_rounds':[r['round'] for r in frozen['arms'][name]['checkpoints'] if r['accepted']],
            'candidate_queries':arm['candidate_queries'],'improvement_queries':frozen['arms'][name]['improvement_queries'],
            'mean_checkpoint_correct':sum(r['correct'] for r in curve)/5}
    report={'primary':frozen['primary'],'audit':read(root/'audit.json') if (root/'audit.json').exists() else {'status':'pending'},
        'scope':'one episode, 32 prespecified arms; unexpected winners are exploratory','arms':summaries}
    write_json(ROOT/'analysis/seed-integration-v2-summary.json',report)
    print(json.dumps({'primary':report['primary'],'primary_result':summaries[report['primary']],
        'audit':report['audit']},indent=2))


if __name__=='__main__': summarize()
