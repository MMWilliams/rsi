"""Check controller-state isolation and exact low-label purchasing on an old bank."""
from collections import Counter

from seed_low_budget import ARMS, inherited_states, loops
from seed_source_search import read, build_records
from rsi.common import ROOT, digest
from rsi.semantic_invention import evaluate_program


def test_balanced_effects_and_matched_budget():
    states = inherited_states()
    assert len(states['I0']) == 60
    assert len(states['B0']) == 75
    assert Counter(row['tactic'] for row in states['B0'][60:]) == {
        'uniform':3,'uncertainty':3,'disagreement':3,'novelty':3,'combined':3}
    assert digest(states['B0'][:60]) == digest(states['I0'])
    for old,new in zip(states['I0'],states['I0_full_scrambled']):
        assert {k:v for k,v in old.items() if k!='utility'} == {k:v for k,v in new.items() if k!='utility'}
    assert [row['utility'] for row in states['I0']] != [row['utility'] for row in states['I0_full_scrambled']]

    root = ROOT/'runs/seed-integration-v2-20260917'
    banks = read(root/'protected_banks.json')
    pools = read(root/'candidate_pools.json')
    tasks = {t['id']:t for group in banks.values() for t in group}
    final_ids = {t['id'] for split,group in banks.items() if split.startswith('final_') for t in group}
    def oracle(key,indices):
        assert key not in final_ids
        if indices is None: indices = range(len(pools[key]))
        return [int(evaluate_program(pools[key][i]['program'],tasks[key]['visible']+tasks[key]['hidden']))
                for i in indices]
    result = loops(build_records(banks,pools),oracle,states)
    assert len(result['arms']) == len(ARMS)
    assert len({arm['checkpoints'][0]['model_sha256'] for arm in result['arms'].values()}) == 1
    assert all([c['improvement_labels'] for c in arm['checkpoints']] == [0,16,32,48,64]
               for arm in result['arms'].values())
    assert [c['tactic'] for c in result['arms']['static_sequence']['checkpoints'][1:]] == [
        'disagreement','disagreement','uncertainty','combined']
