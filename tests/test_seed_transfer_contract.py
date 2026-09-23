"""Exercise the complete transfer interface on an already inspected development bank."""
from seed_improver_transfer import ARMS, inherited_states, loops
from seed_source_search import read, build_records
from rsi.common import ROOT, digest
from rsi.semantic_invention import evaluate_program


def test_frozen_controller_state_and_common_start():
    states = inherited_states()
    assert len(states['I0']) == 60
    assert len(states['I2']) == 66
    assert len(states['I4']) == len(states['I4_scrambled']) == 72
    assert digest(states['I0']) == digest(states['I4'][:60])
    assert digest(states['I2'][:60]) == digest(states['I0'])
    assert [r['utility'] for r in states['I4'][60:]] != [r['utility'] for r in states['I4_scrambled'][60:]]

    root = ROOT/'runs/seed-integration-v2-20260917'
    banks = read(root/'protected_banks.json')
    pools = read(root/'candidate_pools.json')
    tasks = {t['id']:t for group in banks.values() for t in group}
    final_ids = {t['id'] for split,group in banks.items() if split.startswith('final_') for t in group}
    def oracle(key, indices):
        assert key not in final_ids
        if indices is None: indices = range(len(pools[key]))
        return [int(evaluate_program(pools[key][i]['program'],tasks[key]['visible']+tasks[key]['hidden']))
                for i in indices]
    result = loops(build_records(banks,pools),oracle,states)
    assert len(result['arms']) == len(ARMS)
    assert len({a['checkpoints'][0]['model_sha256'] for a in result['arms'].values()}) == 1
    assert all([c['improvement_labels'] for c in a['checkpoints']] == [0,48,96,144,192]
               for a in result['arms'].values())
