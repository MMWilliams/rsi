"""The ten v11.1 seeds (review 002, required experiment 2): gates 1 to 5 per
seed and, per area and pool, the carried/start ratio on the fresh set with its
median, minimum, 95% bootstrap interval over seeds and the count below 100%,
as preregistered in EXPERIMENT-seed-confirmation.md."""
import json

import numpy as np

from rsi.common import ROOT, write_json

SEEDS = ['c22', 'c23'] + [f'c{i}' for i in range(24, 32)]
GROWTH, SAFETY, LEVEL0, ALL_PROOFS, DRAWS = 1.15, .9, 3.5, 5., 1_000_000   # 10,000 draws left the discrete median's upper quantile a support point low


def load(path):
    return json.loads((ROOT / path).read_text())


def seed_row(name, ratios):
    state, check, audit = load(f'seeds/{name}/state.json'), load(f'analysis/seed-check-{name}.json'), load(f'analysis/audit-seed-{name}.json')
    live, proof = state['resource']['live_scans'], state['resource']['proof_scans']
    meta = [e for e in state['ledger'] if e['op'] == 'meta']
    charged = sum(e.get('charged', 0) for e in meta)
    below, unsafe = [], []
    for area, v in check['areas'].items():
        ratio = v['carried']['total'] / v['start']['total']
        ratios.setdefault(area, []).append(ratio)
        if ratio < GROWTH:
            below.append({'area': area, 'start': v['start']['total'], 'carried': v['carried']['total']})
        for pool, start in v['start']['by_pool'].items():
            r = v['carried']['by_pool'][pool] / start
            ratios.setdefault(f'{area}/{pool}', []).append(r)
            if r < SAFETY:
                unsafe.append({'pool': f'{area}/{pool}', 'ratio': r})
    level0, every = (proof - charged) / live, proof / live
    gates = {'1_growth': not below, '2_safety': not unsafe, '3_cost': level0 <= LEVEL0 and every <= ALL_PROOFS,
             '4_replay': bool(audit['passed'] and audit['policy_ok'] and audit['meta_ok']),
             '5_adopted': any(e.get('adopted') for e in meta)}
    adopted = [e for e in meta if e.get('adopted')]
    return {'name': name, 'seed': state['seed'], 'gates': gates, 'passes_1_to_4': all(gates[k] for k in list(gates)[:4]),
            'below_growth': below, 'level0_cost': level0, 'all_proof_cost': every,
            'kept_proofs': sum(1 for e in state['ledger'] if e['op'] == 'prove' and e.get('kept')),
            'adopted': [{'knob': e['mutation']['knob'], 'after': e['mutation']['after'], 'rule': e['rule']} for e in adopted]}


def main():
    ratios = {}
    rows = [seed_row(n, ratios) for n in SEEDS]
    rng = np.random.default_rng(919127)
    pools = {}
    for key, values in ratios.items():
        v = np.array(values)
        medians = np.median(v[rng.integers(len(v), size=(DRAWS, len(v)))], axis=1)
        pools[key] = {'median': float(np.median(v)), 'minimum': float(v.min()), 'below_100': int((v < 1).sum()),
                      'interval': [float(np.percentile(medians, 2.5)), float(np.percentile(medians, 97.5))]}
    adopted = [a for r in rows for a in r['adopted']]
    out = {'seeds': rows, 'pools': pools,
           'summary': {'passes_1_to_4': sum(r['passes_1_to_4'] for r in rows), 'seeds': len(rows),
                       'adopting_seeds': sum(bool(r['adopted']) for r in rows), 'adoptions': len(adopted),
                       'adopted_better': sum(a['rule'] == 'better' for a in adopted),
                       'adopted_cheaper': sum(a['rule'] == 'cheaper' for a in adopted),
                       'kept_proofs': sum(r['kept_proofs'] for r in rows),
                       'level0_cost_range': [min(r['level0_cost'] for r in rows), max(r['level0_cost'] for r in rows)],
                       'all_proof_cost_range': [min(r['all_proof_cost'] for r in rows), max(r['all_proof_cost'] for r in rows)]}}
    write_json(ROOT / 'analysis/review002-replication.json', out)
    print(json.dumps(out['summary'], indent=1))
    for r in rows:
        print(r['name'], 'pass' if r['passes_1_to_4'] else 'FAIL', f"{r['level0_cost']:.2f}x {r['all_proof_cost']:.2f}x", r['below_growth'], len(r['adopted']))


if __name__ == '__main__':
    main()
