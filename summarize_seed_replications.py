"""Descriptive whole-episode comparison; never selects a deployment checkpoint."""
import json
from collections import Counter
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent
RUNS = ('seed-integration-v2-20260917', 'seed-v2-replica-1', 'seed-v2-replica-2')
PRIMARY = 'fixed_novelty__argmax__proper_tie'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def count(checkpoint, method='deployed'):
    return sum(panel['counts'][method] for panel in checkpoint['panels'].values())


def task_outcomes(checkpoint):
    return {row['id']: bool(row['deployed'])
            for panel in checkpoint['panels'].values() for row in panel['tasks']}


def paired(before, after):
    return {'gained': [key for key in before if after[key] and not before[key]],
            'lost': [key for key in before if before[key] and not after[key]]}


def summarize_episode(name):
    root = ROOT / 'runs' / name
    results = read(root / 'results.json')
    frozen = read(root / 'frozen_loops.json')
    costs = read(root / 'loop_costs.json')
    initial = results[PRIMARY]['rounds'][0]
    methods = next(iter(initial['panels'].values()))['counts']
    episode = {'run': name, 'audit': read(root / 'audit.json') if (root / 'audit.json').exists() else {'status': 'pending'},
               'initial_controls': {key: count(initial, key) for key in methods},
               'reachable': sum(p['reachable'] for p in initial['panels'].values()),
               'initial_panels': {key: p['counts'] for key, p in initial['panels'].items()}, 'arms': {}}
    for key, arm in results.items():
        checkpoints = frozen['arms'][key]['checkpoints']
        curve = [count(c) for c in arm['rounds']]
        transitions = []
        for before, after, event in zip(arm['rounds'], arm['rounds'][1:], checkpoints[1:]):
            changes = paired(task_outcomes(before), task_outcomes(after))
            transitions.append({'round': event['round'], 'accepted': event['accepted'],
                                'tactic': event['tactic'], 'net': count(after) - count(before), **changes})
        episode['arms'][key] = {'curve': curve, 'net_gain': curve[-1] - curve[0],
                               'paired': paired(task_outcomes(arm['rounds'][0]), task_outcomes(arm['rounds'][-1])),
                               'transitions': transitions,
                               'accepted_updates': sum(bool(c['accepted']) for c in checkpoints),
                               'useful_updates': sum(t['net'] > 0 for t in transitions),
                               'harmful_updates': sum(t['net'] < 0 for t in transitions),
                               'updates_with_any_task_loss': sum(bool(t['lost']) for t in transitions),
                               'initial_brier': mean(p['driver_brier'] for p in arm['rounds'][0]['panels'].values()),
                               'final_brier': mean(p['driver_brier'] for p in arm['rounds'][-1]['panels'].values()),
                               'costs': costs[key],
                               'panel_curves': {panel: [c['panels'][panel]['counts']['deployed'] for c in arm['rounds']]
                                                for panel in initial['panels']}}
    return episode


def main():
    episodes = [summarize_episode(name) for name in RUNS]
    aggregate = {}
    for arm in episodes[0]['arms']:
        rows = [e['arms'][arm] for e in episodes]
        aggregate[arm] = {'episode_curves': [r['curve'] for r in rows],
                          'pooled_initial': sum(r['curve'][0] for r in rows),
                          'pooled_final': sum(r['curve'][-1] for r in rows),
                          'episode_gains': [r['net_gain'] for r in rows],
                          'net_gain': sum(r['net_gain'] for r in rows),
                          'useful_updates': sum(r['useful_updates'] for r in rows),
                          'harmful_updates': sum(r['harmful_updates'] for r in rows),
                          'updates_with_any_task_loss': sum(r['updates_with_any_task_loss'] for r in rows),
                          'accepted_updates': sum(r['accepted_updates'] for r in rows),
                          'pooled_gained': sum(len(r['paired']['gained']) for r in rows),
                          'pooled_lost': sum(len(r['paired']['lost']) for r in rows)}
    ranking = sorted(aggregate, key=lambda key: (-aggregate[key]['pooled_final'],
                     -sum(sum(curve) for curve in aggregate[key]['episode_curves']), key))
    initial_controls = {key: [e['initial_controls'][key] for e in episodes]
                        for key in episodes[0]['initial_controls']}
    comparisons = {}
    for policy in ('argmax', 'margin'):
        for gate in ('strict', 'proper_tie'):
            suffix = '__' + policy + '__' + gate
            comparisons[policy + '__' + gate] = {
                mode: [e['arms'][mode + suffix]['curve'][-1] for e in episodes]
                for mode in ('fixed_uniform', 'fixed_uncertainty', 'fixed_disagreement',
                             'fixed_novelty', 'fixed_combined', 'meta4', 'meta4_scrambled', 'meta4_online')}
    # Public-example overlap is a separate diagnostic, not a label-based filter.
    signatures = []
    for name in RUNS:
        banks = read(ROOT / 'runs' / name / 'protected_banks.json')
        signatures.extend(json.dumps(t['visible'], ensure_ascii=True) for tasks in banks.values() for t in tasks)
    duplicates = sum(value - 1 for value in Counter(signatures).values() if value > 1)
    report = {'scope': 'Three whole learning episodes; descriptive comparison, not 144 independent learning trials.',
              'primary': PRIMARY, 'episodes': episodes, 'initial_controls': initial_controls,
              'aggregate': aggregate, 'exploratory_ranking': ranking, 'controller_comparisons': comparisons,
              'duplicate_public_example_sets_across_episodes': duplicates,
              'ranking_rule': 'final correctness, then sum of all checkpoint correctness, then arm name; descriptive only',
              'oracle_limit': 'Finite task examples and replay using the same host interpreter; no universal correctness or general intelligence claim.'}
    output = ROOT / 'analysis' / 'seed-replication-summary.json'
    output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'audits': [e['audit']['status'] for e in episodes], 'initial_controls': initial_controls,
                      'primary': aggregate[PRIMARY], 'top_10': {key: aggregate[key] for key in ranking[:10]},
                      'controllers': comparisons, 'public_duplicates': duplicates}, indent=2))


if __name__ == '__main__':
    main()
