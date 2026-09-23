"""Confirmatory run for G6 of
`EXPERIMENT-metric-world-transfer-confirmation-3.md`.

Identical to the G5 run except for the number of evaluation worlds, 32 per
split instead of 16, and the floor that follows from it, +30 of 1,280 instead
of +15 of 640, which is the same effect size per task. G5 failed one cell of
sixteen in each replication, k=2 at budget 256, where the true weighting itself
is worth only +19 in one replication and the fitted metric's interval touched
zero in the other. This adds power at a fixed effect size and changes nothing
else. Every constant it overrides is recorded in the output.
"""
from __future__ import annotations

import hashlib
import time

import numpy as np
import psutil

import metric_world_confirmation as base
from rsi.common import ROOT, write_json
from rsi.mechanism_worlds import Harness
from mechanism_atom_clustering import descriptors
from mechanism_metric_identifiability import reduce_to

DEST = ROOT / 'runs/metric-world-confirmation3-20260921'
OUT = ROOT / 'analysis/metric-world-confirmation3-20260921.json'
SCRIPT = ROOT / 'metric_world_confirmation3.py'
REPLICATIONS = ((1, 924001, 780001), (2, 924002, 780002))
WIDTH = 32
ACTIVE_DIMENSIONS = 8
EVAL_WORLDS = 32
GATE_FLOOR = 30


def main():
    if OUT.exists():
        raise RuntimeError('analysis exists')
    DEST.mkdir(parents=True, exist_ok=True)
    process = psutil.Process()
    wall, cpu = time.perf_counter(), time.process_time()

    harness = Harness()
    latent = reduce_to(descriptors(harness), WIDTH)
    overridden = {'ACTIVE_DIMENSIONS': [base.ACTIVE_DIMENSIONS, ACTIVE_DIMENSIONS],
                  'EVAL_WORLDS': [base.EVAL_WORLDS, EVAL_WORLDS],
                  'GATE_FLOOR': [base.GATE_FLOOR, GATE_FLOOR]}
    base.ACTIVE_DIMENSIONS = ACTIVE_DIMENSIONS
    base.EVAL_WORLDS = EVAL_WORLDS
    base.GATE_FLOOR = GATE_FLOOR

    result = {'scope': 'confirmatory run, EXPERIMENT-metric-world-transfer-confirmation-3.md',
              'runner_sha256': hashlib.sha256(SCRIPT.read_bytes()).hexdigest(),
              'base_runner_sha256': hashlib.sha256(base.SCRIPT.read_bytes()).hexdigest(),
              'catalog': {'rows': harness.catalog.size, 'digest': harness.catalog.digest()},
              'descriptor_dimensions': int(latent.shape[1]),
              'active_dimensions': ACTIVE_DIMENSIONS, 'overridden': overridden,
              'gate_floor': base.GATE_FLOOR, 'budgets': list(base.BUDGETS),
              'adapt': list(base.ADAPT),
              'held_out_families': list(base.HELD_OUT_FAMILIES), 'replications': {}}

    for number, seed, weight_seed in REPLICATIONS:
        path = DEST / f'decisions-{number}.jsonl'
        if path.exists():
            raise RuntimeError(f'{path} exists')
        with path.open('w', encoding='utf-8') as journal:
            evaluation, outcomes, arms, correlation = base.replication(
                harness, latent, number, seed, weight_seed, journal)
        block = base.summarise(outcomes, arms, seed)
        verdict = base.gate(block)
        result['replications'][str(number)] = {
            'seed': seed, 'weight_seed': weight_seed,
            'fitted_true_weight_correlation': correlation,
            'splits': block, 'gate': verdict,
            'worlds': {split: [{'centre': world['centre'], 'members': len(world['members'])}
                               for world in worlds]
                       for split, worlds in evaluation.items()},
            'decisions_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        print('replication {}: G6 {} (weight correlation {:.3f}){}'.format(
            number, verdict['passed'], correlation,
            '' if verdict['passed'] else ' failed at ' + ', '.join(verdict['failed_cells'])))

    result['cost'] = {'wall_seconds': time.perf_counter() - wall,
                      'cpu_seconds': time.process_time() - cpu,
                      'peak_rss_mb': process.memory_info().rss / 1e6}
    write_json(OUT, result)

    verdicts = [result['replications'][str(number)]['gate']['passed']
                for number, _, _ in REPLICATIONS]
    print('G6:', 'passed' if all(verdicts) else 'failed', verdicts)
    for number, _, _ in REPLICATIONS:
        entry = result['replications'][str(number)]['splits']['new_family_centre']
        for key in ('meta_metric_minus_free_cosine', 'meta_metric_minus_meta_scrambled'):
            print('replication {} new_family_centre, {}:'.format(number, key))
            for k in base.ADAPT:
                row = entry[key][str(k)]
                print('  k={:<3d}'.format(k) + ''.join(
                    '{:+6.0f}{:<13s}'.format(row[str(b)]['sum'],
                                             str([round(x) for x in row[str(b)]['interval']]))
                    for b in base.BUDGETS))
    print('cost: {wall_seconds:.1f}s wall, {cpu_seconds:.1f}s cpu, {peak_rss_mb:.0f} MB'
          .format(**result['cost']))


if __name__ == '__main__':
    main()
