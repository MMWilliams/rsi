"""Whole-episode and first-edit comparisons for the low-label study."""
import json
from pathlib import Path
from statistics import mean

ROOT=Path(__file__).resolve().parent
OFFSETS=(9000,10000,11000,12000,13000,14000)
TACTICS=('uniform','uncertainty','disagreement','novelty','combined')
LEARNED=('I0','I0_full_scrambled','B0','I4')
ARMS=LEARNED+('static_sequence',)+tuple('fixed_'+t for t in TACTICS)


def read(path): return json.loads(path.read_text(encoding='utf-8'))


def count(checkpoint,key='deployed'):
    return sum(panel['counts'][key] for panel in checkpoint['panels'].values())


def effects(old,new):
    n=len(old['rows'])
    harmed=sum(a['correct'] and not b['correct'] for a,b in zip(old['rows'],new['rows']))
    return {'gain':(new['correct']-old['correct'])/n,'harm':harmed/n,
            'utility':(new['correct']-old['correct']-.25*harmed)/n,
            'correct_delta':new['correct']-old['correct'],'harmed_tasks':harmed}


def summarize():
    episodes=[]
    for offset in OFFSETS:
        root=ROOT/'runs'/f'seed-low-{offset}'
        results=read(root/'results.json'); frozen=read(root/'frozen_loops.json')
        assert set(results)==set(ARMS)
        costs=read(root/'loop_costs.json')
        initial=results['I0']['rounds'][0]
        old=frozen['arms']['I0']['checkpoints'][0]['admission']
        factual={}
        for tactic in TACTICS:
            cp=frozen['arms']['fixed_'+tactic]['checkpoints'][1]
            assert cp['tactic']==tactic
            assert frozen['arms']['fixed_'+tactic]['checkpoints'][0]['model_sha256']==frozen['arms']['I0']['checkpoints'][0]['model_sha256']
            assert cp['improvement_labels']==16
            factual[tactic]=effects(old,cp['candidate_admission'])
        judgments={}
        for arm in LEARNED:
            cp=frozen['arms'][arm]['checkpoints'][1]
            tactic=cp['tactic']; assert tactic in TACTICS
            fixed=frozen['arms']['fixed_'+tactic]['checkpoints'][1]
            assert cp['query_log']==fixed['query_log']
            assert cp['candidate_admission']==fixed['candidate_admission']
            predicted=cp['effect_scores']
            assert set(predicted)==set(TACTICS)
            true_utility=factual[tactic]['utility']
            best=max(row['utility'] for row in factual.values())
            judgments[arm]={'selected':tactic,'predicted':predicted,
                            'realized_utility':true_utility,'best_tested_utility':best,
                            'regret':best-true_utility,
                            'mae':mean(abs(predicted[t]-factual[t]['utility']) for t in TACTICS),
                            'selected_is_best':abs(best-true_utility)<1e-12}
        curves={arm:[count(cp) for cp in results[arm]['rounds']] for arm in ARMS}
        updates={arm:[{'round':index,'accepted':bool(frozen['arms'][arm]['checkpoints'][index]['accepted']),
                       'tactic':frozen['arms'][arm]['checkpoints'][index]['tactic'],
                       'final_delta':curves[arm][index]-curves[arm][index-1]}
                      for index in range(1,5)] for arm in ARMS}
        episodes.append({'offset':offset,
                         'audit':read(root/'audit.json') if (root/'audit.json').exists() else {'status':'pending'},
                         'initial_controls':{key:count(initial,key) for key in initial['panels']['final_mixed']['counts']},
                         'reachable_by_panel':{panel:row['reachable'] for panel,row in initial['panels'].items()},
                         'curves':curves,'updates':updates,'first_edit_factual':factual,
                         'first_edit_judgments':judgments,'costs':costs,
                         'candidate_generation':read(root/'generation_times.json')})
    summary={arm:{'final':[ep['curves'][arm][-1] for ep in episodes],
                  'initial':[ep['curves'][arm][0] for ep in episodes],
                  'net':[ep['curves'][arm][-1]-ep['curves'][arm][0] for ep in episodes],
                  'useful_updates':sum(x['final_delta']>0 for ep in episodes for x in ep['updates'][arm]),
                  'net_harmful_updates':sum(x['final_delta']<0 for ep in episodes for x in ep['updates'][arm]),
                  'accepted_updates':sum(x['accepted'] for ep in episodes for x in ep['updates'][arm])}
             for arm in ARMS}
    screen={}
    for candidate,control in (('I0','static_sequence'),('I0','I0_full_scrambled'),('B0','I0')):
        differences=[a-b for a,b in zip(summary[candidate]['final'],summary[control]['final'])]
        screen[candidate+'_vs_'+control]={'paired_differences':differences,'wins':sum(x>0 for x in differences),
                                          'mean_gain':mean(differences),
                                          'passed':sum(x>0 for x in differences)>=4 and mean(differences)>=1}
    edit_eval={arm:{'mean_mae':mean(ep['first_edit_judgments'][arm]['mae'] for ep in episodes),
                    'mean_regret':mean(ep['first_edit_judgments'][arm]['regret'] for ep in episodes),
                    'best_edit_selected':sum(ep['first_edit_judgments'][arm]['selected_is_best'] for ep in episodes)}
               for arm in LEARNED}
    report={'scope':'six whole independent episodes; ten policy arms; 16 improvement labels per round',
            'episodes':episodes,'aggregate':summary,'screen':screen,'first_edit_evaluation':edit_eval,
            'frozen_state_lengths':{name:len(rows) for name,rows in read(ROOT/'analysis/seed-low-budget-states.json').items()}}
    output=ROOT/'analysis/seed-low-budget-summary.json'
    output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'audits':[ep['audit']['status'] for ep in episodes],
                      'reachability':[sum(ep['reachable_by_panel'].values()) for ep in episodes],
                      'screen':screen,'edit_eval':edit_eval,
                      'final_totals':{arm:sum(row['final']) for arm,row in summary.items()}},indent=2))


if __name__=='__main__': summarize()
