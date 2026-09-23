"""Six-episode transfer screen; no winner is selected here."""
import json
from collections import Counter
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent
OFFSETS = (3000,4000,5000,6000,7000,8000)
ARMS = ('I0','I2','I4','I4_scrambled','empty','I0_online','I4_online',
        'fixed_uniform','fixed_novelty','fixed_disagreement','fixed_combined','fixed_uncertainty_strict')


def read(path): return json.loads(path.read_text(encoding='utf-8'))


def count(checkpoint,key='deployed'):
    return sum(panel['counts'][key] for panel in checkpoint['panels'].values())


def task_map(checkpoint):
    return {row['id']:bool(row['deployed']) for panel in checkpoint['panels'].values() for row in panel['tasks']}


def paired(left,right):
    a,b=task_map(left),task_map(right)
    return {'right_only':[key for key in a if b[key] and not a[key]],
            'left_only':[key for key in a if a[key] and not b[key]]}


def summarize():
    episodes=[]
    for offset in OFFSETS:
        root=ROOT/'runs'/f'seed-transfer-{offset}'
        results=read(root/'results.json'); frozen=read(root/'frozen_loops.json')
        costs=read(root/'loop_costs.json'); generation=read(root/'generation_times.json')
        assert set(results)==set(ARMS)
        controls={key:count(results['I0']['rounds'][0],key)
                  for key in results['I0']['rounds'][0]['panels']['final_mixed']['counts']}
        curves={arm:[count(c) for c in results[arm]['rounds']] for arm in ARMS}
        updates={arm:[{'round':r,'accepted':bool(frozen['arms'][arm]['checkpoints'][r]['accepted']),
                       'tactic':frozen['arms'][arm]['checkpoints'][r]['tactic'],
                       'delta':curves[arm][r]-curves[arm][r-1],
                       'tasks':paired(results[arm]['rounds'][r-1],results[arm]['rounds'][r])}
                      for r in range(1,5)] for arm in ARMS}
        episode={'offset':offset,'audit':read(root/'audit.json') if (root/'audit.json').exists() else {'status':'pending'},
                 'initial_controls':controls,
                 'reachable':sum(p['reachable'] for p in results['I0']['rounds'][0]['panels'].values()),
                 'reachability_by_panel':{p:row['reachable'] for p,row in
                                          results['I0']['rounds'][0]['panels'].items()},
                 'curves':curves,'updates':updates,
                 'panels':{arm:{p:[c['panels'][p]['counts']['deployed'] for c in results[arm]['rounds']]
                                for p in results[arm]['rounds'][0]['panels']} for arm in ARMS},
                 'costs':costs,'candidate_generation':generation,
                 'paired_final':{other:paired(results[other]['rounds'][-1],results['I4']['rounds'][-1])
                                 for other in ARMS if other!='I4'}}
        episodes.append(episode)
    aggregate={arm:{'final':[ep['curves'][arm][-1] for ep in episodes],
                    'initial':[ep['curves'][arm][0] for ep in episodes],
                    'net':[ep['curves'][arm][-1]-ep['curves'][arm][0] for ep in episodes],
                    'useful_updates':sum(step['delta']>0 for ep in episodes for step in ep['updates'][arm]),
                    'net_harmful_updates':sum(step['delta']<0 for ep in episodes for step in ep['updates'][arm]),
                    'updates_with_task_loss':sum(bool(step['tasks']['left_only']) for ep in episodes
                                                 for step in ep['updates'][arm]),
                    'accepted_updates':sum(step['accepted'] for ep in episodes for step in ep['updates'][arm])}
               for arm in ARMS}
    differences=[a-b for a,b in zip(aggregate['I4']['final'],aggregate['I0']['final'])]
    screen={'I4_minus_I0_by_episode':differences,
            'I4_wins':sum(x>0 for x in differences),
            'mean_I4_minus_I0':mean(differences),
            'mean_I4':mean(aggregate['I4']['final']),
            'mean_fixed_uncertainty':mean(aggregate['fixed_uncertainty_strict']['final']),
            'mean_fixed_disagreement':mean(aggregate['fixed_disagreement']['final'])}
    screen['passed']=(screen['I4_wins']>=5 and screen['mean_I4_minus_I0']>=2
                      and screen['mean_I4']>screen['mean_fixed_uncertainty']
                      and screen['mean_I4']>screen['mean_fixed_disagreement'])
    prior_names=('seed-source-search-20260917','seed-integration-v2-20260917',
                 'seed-v2-replica-1','seed-v2-replica-2')
    source_cost={name:sum(map(len,read(ROOT/'runs'/name/(
                  'opened_source_labels.json' if name==prior_names[0]
                  else 'opened_feedback_labels.json')).values())) for name in prior_names}
    signatures=[]
    for name in (*prior_names, *(f'seed-transfer-{offset}' for offset in OFFSETS)):
        banks=read(ROOT/'runs'/name/'protected_banks.json')
        signatures.extend(json.dumps(task['visible'],sort_keys=True) for tasks in banks.values() for task in tasks)
    duplicates=sum(value-1 for value in Counter(signatures).values() if value>1)
    report={'scope':'Six independent whole learning episodes, 12 frozen policy arms',
            'primary':'I4 versus I0 under identical new bases and label allowance',
            'screen':screen,'episodes':episodes,'aggregate':aggregate,
            'source_acquisition_unique_labels_across_all_archived_arms':source_cost,
            'duplicate_public_example_sets_across_source_donor_transfer':duplicates,
            'source_state_lengths':{k:len(v) for k,v in read(ROOT/'analysis/seed-transfer-inherited-states.json').items()}}
    output=ROOT/'analysis/seed-transfer-summary.json'
    output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'audits':[ep['audit']['status'] for ep in episodes],
                      'reachability':[ep['reachable'] for ep in episodes],
                      'initial_controls':{k:[ep['initial_controls'][k] for ep in episodes]
                                          for k in episodes[0]['initial_controls']},
                      'screen':screen,'aggregate':aggregate},indent=2))


if __name__=='__main__': summarize()
