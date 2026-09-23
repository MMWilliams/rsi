"""Confirmatory run for G4 of `EXPERIMENT-metric-world-transfer-confirmation.md`.

Two replications on independent seeds, with the hidden weight vector redrawn
for each. Writes a decision journal so the audit can recompute every number
without re-running anything.
"""
from __future__ import annotations

import hashlib
import json
import random
import time

import numpy as np
import psutil

from rsi.common import ROOT, write_json
from rsi.mechanism_space import DENSITY, make_task, vector_test, world_members
from rsi.mechanism_worlds import Harness, ranks_of
from mechanism_atom_clustering import descriptors
from mechanism_metric_transfer import fit_metric
from mechanism_metric_worlds import proximity, weighted_distance

DEST = ROOT / 'runs/metric-world-confirmation-20260921'
OUT = ROOT / 'analysis/metric-world-confirmation-20260921.json'
SCRIPT = ROOT / 'metric_world_confirmation.py'
REPLICATIONS = ((1, 922001, 778001), (2, 922002, 778002))
ACTIVE_DIMENSIONS = 40
TRAINING_WORLDS = 400
PRIOR_SOLVED = 64
EVAL_WORLDS = 16
TEST_MECHANISMS = 40
KEYS_PER_WORLD = 14
MINIMUM_MEMBERS = 110
HELD_OUT_FAMILIES = ('popcount', 'xormod')
ADAPT = (1, 2, 4, 8)
BUDGETS = (256, 1024, 4096, 16384)
GATE_ADAPT = (1, 2)
GATE_FLOOR = 15
FLOOR = 1e-4
BOOT = 20000
ARMS = ('free_set', 'free_cosine', 'meta_metric', 'meta_scrambled', 'oracle_metric')


def replication(harness, latent, number, seed, weight_seed, journal):
    catalog = harness.catalog
    dimensions = latent.shape[1]
    rng = random.Random(seed)
    harness.set_tiebreak(seed + 77)

    weight_rng = np.random.default_rng(weight_seed)
    true_weights = np.zeros(dimensions)
    active = weight_rng.choice(dimensions, ACTIVE_DIMENSIONS, replace=False)
    true_weights[active] = weight_rng.uniform(.5, 4., ACTIVE_DIMENSIONS)

    families = np.array([key.split(':')[0] for key in harness.key_names])
    seen_centres = [index for index in range(len(families))
                    if families[index] not in HELD_OUT_FAMILIES]
    held_centres = [index for index in range(len(families))
                    if families[index] in HELD_OUT_FAMILIES]

    def world_from(centre):
        distance = weighted_distance(latent, true_weights, centre)
        chosen = [harness.key_names[index]
                  for index in np.argsort(distance)[:KEYS_PER_WORLD]]
        members = [index for index in world_members(catalog, harness.by_key, chosen)
                   if DENSITY[0] <= harness.density[index] <= DENSITY[1]]
        if len(members) < MINIMUM_MEMBERS:
            return None
        return {'centre': int(centre), 'keys': chosen, 'members': members}

    def draw(centres, count):
        out, attempts = [], 0
        while len(out) < count and attempts < count * 60:
            attempts += 1
            world = world_from(centres[rng.randrange(len(centres))])
            if world is not None:
                out.append(world)
        if len(out) < count:
            raise RuntimeError(f'only {len(out)} of {count} worlds met the size floor')
        return out

    evaluation = {'seen_centre': draw(seen_centres, EVAL_WORLDS),
                  'new_family_centre': draw(held_centres, EVAL_WORLDS)}
    for worlds in evaluation.values():
        for world in worlds:
            members = list(world['members'])
            rng.shuffle(members)
            world['test'] = members[:TEST_MECHANISMS]
            world['pool'] = members[TEST_MECHANISMS:]
    reserved = {index for worlds in evaluation.values() for world in worlds
                for index in world['test']}

    training = draw(seen_centres, TRAINING_WORLDS)
    observed_sets = []
    for world in training:
        allowed = [index for index in world['members'] if index not in reserved]
        solved = rng.sample(allowed, min(PRIOR_SOLVED, len(allowed)))
        observed_sets.append(sorted({harness.key_index[key]
                                     for key in harness.observed_keys(solved)}))
    model = fit_metric(latent, observed_sets, rng)
    fitted = np.maximum(model.coef_[0], 0.)
    scrambled = fitted[np.random.default_rng(seed + 5).permutation(dimensions)]
    weights = {'free_cosine': np.ones(dimensions), 'meta_metric': fitted,
               'meta_scrambled': scrambled, 'oracle_metric': true_weights}
    correlation = float(np.corrcoef(fitted, true_weights)[0, 1])

    arms = [f'{name}:{k}' for k in ADAPT for name in ARMS]
    outcomes = {split: {arm: {budget: [] for budget in BUDGETS} for arm in arms}
                for split in evaluation}

    for split, worlds in evaluation.items():
        for world_number, world in enumerate(worlds):
            ranks = {}
            for k in ADAPT:
                counts = harness.key_counts(world['pool'][:k])
                present = list(np.flatnonzero(counts))
                direct = (counts > 0).astype(float)
                for name in ARMS:
                    score = direct if name == 'free_set' else np.maximum(
                        direct, proximity(latent, weights[name], present))
                    ranks[f'{name}:{k}'] = ranks_of(
                        harness.order_from_key_scores(np.log(score + FLOOR)))
            for mechanism in world['test']:
                task = make_task(catalog, mechanism, rng)
                consistent = np.flatnonzero(vector_test(harness.packed, task['visible_pos'],
                                                        task['visible_neg']))
                if len(consistent) == 0:
                    continue
                good = vector_test(harness.packed, task['hidden_pos'],
                                   task['hidden_neg'])[consistent]
                select = np.lexsort((harness.complexity[consistent],
                                     harness.sizes[consistent]))
                where = {int(index): position for position, index in enumerate(consistent)}
                picks = {}
                for arm in arms:
                    ranked = ranks[arm][consistent]
                    row = {}
                    for budget in BUDGETS:
                        chosen = -1
                        for candidate in select:
                            if ranked[candidate] < budget:
                                chosen = int(consistent[candidate])
                                break
                        row[str(budget)] = chosen
                        outcomes[split][arm][budget].append(
                            0 if chosen < 0 else int(good[where[chosen]]))
                    picks[arm] = row
                journal.write(json.dumps({
                    'replication': number, 'split': split, 'world': world_number,
                    'mechanism': int(mechanism), 'keys': list(world['keys']),
                    'pool': [int(index) for index in world['pool'][:max(ADAPT)]],
                    'visible': task['visible'], 'hidden': task['hidden'],
                    'picks': picks}) + '\n')
    return evaluation, outcomes, arms, correlation


def summarise(outcomes, arms, seed):
    boot = np.random.default_rng(seed + 31)
    block = {}
    for split in outcomes:
        tasks = len(outcomes[split][arms[0]][BUDGETS[0]])
        draws = boot.integers(0, tasks, (BOOT, tasks))

        def paired(a, b, budget):
            difference = np.asarray(outcomes[split][a][budget], float) - \
                np.asarray(outcomes[split][b][budget], float)
            sums = difference[draws].sum(axis=1)
            return {'sum': float(difference.sum()), 'tasks': tasks,
                    'interval': [float(np.percentile(sums, 2.5)),
                                 float(np.percentile(sums, 97.5))]}

        entry = {'tasks': tasks,
                 'rate': {arm: {str(budget): float(np.mean(outcomes[split][arm][budget]))
                                for budget in BUDGETS} for arm in arms}}
        for left, right in (('meta_metric', 'free_cosine'), ('meta_metric', 'meta_scrambled'),
                            ('meta_metric', 'free_set'), ('oracle_metric', 'free_cosine'),
                            ('free_cosine', 'free_set')):
            entry[f'{left}_minus_{right}'] = {
                str(k): {str(budget): paired(f'{left}:{k}', f'{right}:{k}', budget)
                         for budget in BUDGETS} for k in ADAPT}
        block[split] = entry
    return block


def gate(block):
    """G4, read at every budget and both k, as the protocol requires."""
    split = block['new_family_centre']
    cells = []
    for k in GATE_ADAPT:
        for budget in BUDGETS:
            versus_free = split['meta_metric_minus_free_cosine'][str(k)][str(budget)]
            versus_scrambled = split['meta_metric_minus_meta_scrambled'][str(k)][str(budget)]
            cells.append({
                'k': k, 'budget': budget,
                'minus_free_cosine': versus_free['sum'],
                'minus_scrambled': versus_scrambled['sum'],
                'passed': bool(versus_free['sum'] >= GATE_FLOOR
                               and versus_free['interval'][0] > 0
                               and versus_scrambled['sum'] > 0
                               and versus_scrambled['interval'][0] > 0)})
    return {'cells': cells, 'passed': all(cell['passed'] for cell in cells),
            'failed_cells': [f"k={cell['k']} budget={cell['budget']}"
                             for cell in cells if not cell['passed']]}


def main():
    if OUT.exists():
        raise RuntimeError('analysis exists')
    DEST.mkdir(parents=True, exist_ok=True)
    process = psutil.Process()
    wall, cpu = time.perf_counter(), time.process_time()

    harness = Harness()
    latent = descriptors(harness)
    result = {'scope': 'confirmatory run, EXPERIMENT-metric-world-transfer-confirmation.md',
              'runner_sha256': hashlib.sha256(SCRIPT.read_bytes()).hexdigest(),
              'catalog': {'rows': harness.catalog.size, 'digest': harness.catalog.digest()},
              'descriptor_dimensions': int(latent.shape[1]),
              'active_dimensions': ACTIVE_DIMENSIONS, 'gate_floor': GATE_FLOOR,
              'budgets': list(BUDGETS), 'adapt': list(ADAPT),
              'held_out_families': list(HELD_OUT_FAMILIES), 'replications': {}}

    for number, seed, weight_seed in REPLICATIONS:
        path = DEST / f'decisions-{number}.jsonl'
        if path.exists():
            raise RuntimeError(f'{path} exists')
        with path.open('w', encoding='utf-8') as journal:
            evaluation, outcomes, arms, correlation = replication(
                harness, latent, number, seed, weight_seed, journal)
        block = summarise(outcomes, arms, seed)
        verdict = gate(block)
        result['replications'][str(number)] = {
            'seed': seed, 'weight_seed': weight_seed,
            'fitted_true_weight_correlation': correlation,
            'splits': block, 'gate': verdict,
            'worlds': {split: [{'centre': world['centre'], 'members': len(world['members'])}
                               for world in worlds]
                       for split, worlds in evaluation.items()},
            'decisions_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        print('replication {}: G4 {} (weight correlation {:.3f}){}'.format(
            number, verdict['passed'], correlation,
            '' if verdict['passed'] else ' failed at ' + ', '.join(verdict['failed_cells'])))

    result['cost'] = {'wall_seconds': time.perf_counter() - wall,
                      'cpu_seconds': time.process_time() - cpu,
                      'peak_rss_mb': process.memory_info().rss / 1e6}
    write_json(OUT, result)

    verdicts = [result['replications'][str(number)]['gate']['passed']
                for number, _, _ in REPLICATIONS]
    print('G4:', 'passed' if all(verdicts) else 'failed', verdicts)
    for number, _, _ in REPLICATIONS:
        entry = result['replications'][str(number)]['splits']['new_family_centre']
        print('replication {} new_family_centre, meta_metric minus free_cosine:'.format(number))
        for k in ADAPT:
            row = entry['meta_metric_minus_free_cosine'][str(k)]
            print('  k={:<3d}'.format(k) + ''.join(
                '{:+6.0f}{:<13s}'.format(row[str(b)]['sum'],
                                         str([round(x) for x in row[str(b)]['interval']]))
                for b in BUDGETS))
    print('cost: {wall_seconds:.1f}s wall, {cpu_seconds:.1f}s cpu, {peak_rss_mb:.0f} MB'
          .format(**result['cost']))


if __name__ == '__main__':
    main()
