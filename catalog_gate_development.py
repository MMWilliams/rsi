"""Development-only admission gate over frozen evaluator edit catalog."""
import json

from rsi.common import ROOT,write_json


C=ROOT/'runs/evaluator-router-transfer-20260917/results.json'
C_EXPERT=ROOT/'analysis/context-expert-replay-development.json'
D=ROOT/'runs/context-expert-transfer-20260917/results.json'
OUT=ROOT/'analysis/catalog-gate-development.json'
A='E192_classification'
CATALOG=(A,'expert','blend','pairwise_random','combined_pairwise_random','learned_router')


def rows():
    c=json.loads(C.read_text(encoding='utf-8'))['tasks']
    expert={row['id']:row['correct'] for row in
            json.loads(C_EXPERT.read_text(encoding='utf-8'))['tasks']}
    for row in c:
        addon=expert[row['id']]
        row['correct']['expert']=addon['expert']
        row['correct']['blend']=addon['blend']
    d=json.loads(D.read_text(encoding='utf-8'))['tasks']
    return c+d


def choose(admission,margin):
    counts={name:sum(row['correct'][name] for row in admission) for name in CATALOG}
    best=max(CATALOG,key=lambda name:(counts[name],-CATALOG.index(name)))
    if best!=A and counts[best]>=counts[A]+margin:return best,counts
    return A,counts


def main():
    allrows=rows()
    seeds=sorted({r['seed'] for r in allrows})
    episodes=[]
    for seed in seeds:
        tasks=[r for r in allrows if r['seed']==seed]
        assert len(tasks)==32
        admission=tasks[:16];final=tasks[16:]
        methods={}
        for margin in (1,2,3):
            selected,counts=choose(admission,margin)
            methods[str(margin)]={'selected':selected,
                                  'admission_counts':counts,
                                  'final_correct':sum(r['correct'][selected] for r in final)}
        episodes.append({'seed':seed,'admission_tasks':16,'final_tasks':16,
                         'fixed_final':{name:sum(r['correct'][name] for r in final)
                                        for name in CATALOG},
                         'oracle_best_final':max(sum(r['correct'][name] for r in final)
                                                 for name in CATALOG),
                         'gates':methods})
    summary={'scope':'development only; C and D labels previously inspected',
             'episodes':len(episodes),'final_tasks':sum(e['final_tasks'] for e in episodes),
             'fixed':{name:sum(e['fixed_final'][name] for e in episodes)
                      for name in CATALOG},
             'oracle_best_per_episode':sum(e['oracle_best_final'] for e in episodes),
             'gates':{str(margin):{
                 'correct':sum(e['gates'][str(margin)]['final_correct'] for e in episodes),
                 'selection_counts':{name:sum(e['gates'][str(margin)]['selected']==name
                                              for e in episodes) for name in CATALOG}}
                      for margin in (1,2,3)}}
    write_json(OUT,{'summary':summary,'episodes':episodes})
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
