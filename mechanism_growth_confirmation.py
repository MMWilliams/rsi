"""Confirmatory run for G1, G2 and G3 of
`EXPERIMENT-mechanism-growth-confirmation.md`.

Two replications on independent seeds, three splits, sixteen worlds each. The
runner writes a task bank and a decision record so that an independent audit
can recompute every number through the host interpreter instead of the mask
arithmetic used here.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import random
import time

import numpy as np
import psutil
from sklearn.linear_model import LogisticRegression

from rsi.common import ROOT, write_json
from rsi.mechanism_space import make_task, vector_test, world_members
from rsi.mechanism_worlds import Harness, affinity, ranks_of

DEST = ROOT / 'runs/mechanism-growth-confirmation-20260921'
OUT = ROOT / 'analysis/mechanism-growth-confirmation-20260921.json'
SCRIPT = ROOT / 'mechanism_growth_confirmation.py'
REPLICATIONS = ((1, 921001), (2, 921002))
TRAINING_WORLDS = 400
PRIOR_SOLVED = 64
EVAL_WORLDS = 16
TEST_MECHANISMS = 40
KEYS_PER_WORLD = 14
FAMILIES_PER_WORLD = 3
ADAPT = (1, 2, 4, 8, 16, 32)
BUDGETS = (256, 1024, 4096, 16384, None)
HELD_OUT_FAMILIES = ('popcount', 'xormod')
HELD_OUT_TRIPLES = 6
MINIMUM_MEMBERS = 120
FLOOR = 1e-4
BOOT = 20000
POSITIVE_PAIRS = 24
NEGATIVE_PAIRS = 48
STATIC = ('complexity', 'density')
ADAPTIVE = ('free_count', 'free_set', 'wrong_world', 'meta_identity', 'meta_metric',
            'meta_both', 'meta_uniform', 'meta_identity_scrambled',
            'meta_metric_scrambled')
FREE = ('free_count', 'free_set')


def fwht(rows):
    rows = rows.astype(np.float64).copy()
    width = rows.shape[-1]
    step = 1
    while step < width:
        for start in range(0, width, step * 2):
            left = rows[:, start:start + step].copy()
            right = rows[:, start + step:start + 2 * step].copy()
            rows[:, start:start + step] = left + right
            rows[:, start + step:start + 2 * step] = left - right
        step *= 2
    return rows


def descriptors(harness):
    from rsi.mechanism_space import ALPHABET_SIZE, mask_of
    lookup = {atom[0]: atom[2] for atom in harness.catalog.atoms}
    rows = np.zeros((len(harness.key_names), ALPHABET_SIZE))
    for index, key in enumerate(harness.key_names):
        mask = mask_of(lookup[key])
        rows[index] = np.array([(mask >> bit) & 1 for bit in range(ALPHABET_SIZE)],
                               float) * 2 - 1
    fourier = np.abs(np.fft.rfft(rows, axis=1))
    walsh = np.abs(fwht(rows))
    block = np.concatenate([fourier / np.linalg.norm(fourier, axis=1, keepdims=True),
                            walsh / np.linalg.norm(walsh, axis=1, keepdims=True)], axis=1)
    centred = block - block.mean(axis=0, keepdims=True)
    return centred / np.maximum(centred.std(axis=0, keepdims=True), 1e-9)


def fit_metric(latent, observed_sets, rng):
    size = latent.shape[0]
    features, labels = [], []
    for indices in observed_sets:
        indices = list(indices)
        if len(indices) < 2:
            continue
        for _ in range(POSITIVE_PAIRS):
            left, right = rng.sample(indices, 2)
            features.append(latent[left] * latent[right])
            labels.append(1)
        for _ in range(NEGATIVE_PAIRS):
            left = rng.choice(indices)
            right = rng.randrange(size)
            if right in indices:
                continue
            features.append(latent[left] * latent[right])
            labels.append(0)
    model = LogisticRegression(max_iter=3000, C=.25)
    model.fit(np.asarray(features), np.asarray(labels))
    return model


def metric_scores(model, latent, observed):
    if not len(observed):
        return np.zeros(latent.shape[0])
    logits = (latent * model.coef_[0]) @ latent[observed].T + model.intercept_[0]
    return 1. / (1. + np.exp(-logits.max(axis=1)))


def replication(harness, latent, number, seed, journal):
    catalog = harness.catalog
    keys = len(harness.key_names)
    rng = random.Random(seed)
    harness.set_tiebreak(seed + 77)

    seen_families = [family for family in sorted(harness.by_family)
                     if family not in HELD_OUT_FAMILIES]
    viable = [triple for triple in itertools.combinations(seen_families, FAMILIES_PER_WORLD)
              if harness.sample_world(triple, rng, KEYS_PER_WORLD, MINIMUM_MEMBERS)]
    held_triples = sorted(rng.sample(viable, HELD_OUT_TRIPLES))
    training_triples = [triple for triple in viable if triple not in held_triples]
    held_family_triples = [triple for triple in
                           itertools.combinations(sorted(harness.by_family), FAMILIES_PER_WORLD)
                           if set(triple) & set(HELD_OUT_FAMILIES)]

    def draw(triples, count):
        out = []
        while len(out) < count:
            world = harness.sample_world(triples[rng.randrange(len(triples))], rng,
                                         KEYS_PER_WORLD, MINIMUM_MEMBERS)
            if world is not None:
                out.append(world)
        return out

    evaluation = {'seen_triple': draw(training_triples, EVAL_WORLDS),
                  'new_triple': draw(held_triples, EVAL_WORLDS),
                  'new_family': draw(held_family_triples, EVAL_WORLDS)}
    for worlds in evaluation.values():
        for world in worlds:
            members = list(world['members'])
            rng.shuffle(members)
            world['test'] = members[:TEST_MECHANISMS]
            world['pool'] = members[TEST_MECHANISMS:]
    reserved = {mechanism for worlds in evaluation.values() for world in worlds
                for mechanism in world['test']}

    training = draw(training_triples, TRAINING_WORLDS)
    uniform_training = []
    while len(uniform_training) < TRAINING_WORLDS:
        chosen = rng.sample(harness.key_names, KEYS_PER_WORLD)
        members = world_members(catalog, harness.by_key, chosen)
        if len(members) >= MINIMUM_MEMBERS:
            uniform_training.append({'members': members})

    def observe(worlds):
        out = []
        for world in worlds:
            allowed = [index for index in world['members'] if index not in reserved]
            solved = rng.sample(allowed, min(PRIOR_SOLVED, len(allowed)))
            out.append(sorted({harness.key_index[key]
                               for key in harness.observed_keys(solved)}))
        return out

    structured_sets = observe(training)
    identity = affinity(structured_sets, keys)
    uniform = affinity(observe(uniform_training), keys)
    permutation = np.random.default_rng(seed + 5).permutation(keys)
    identity_scrambled = identity[np.ix_(permutation, permutation)]
    metric = fit_metric(latent, structured_sets, rng)
    latent_scrambled = latent[np.random.default_rng(seed + 9).permutation(keys)]
    metric_scrambled = fit_metric(latent_scrambled, structured_sets, rng)

    static_ranks = {
        'complexity': ranks_of(np.lexsort((harness.tiebreak, harness.complexity))),
        'density': ranks_of(np.lexsort((harness.tiebreak, np.abs(harness.density - .5))))}
    arms = list(STATIC) + [f'{name}:{k}' for k in ADAPT for name in ADAPTIVE]
    outcomes = {split: {arm: {budget: [] for budget in BUDGETS} for arm in arms}
                for split in evaluation}
    unsolvable = 0

    for split, worlds in evaluation.items():
        for number_in_split, world in enumerate(worlds):
            other = worlds[(number_in_split + 1) % len(worlds)]['pool']
            ranks = dict(static_ranks)
            for k in ADAPT:
                counts = harness.key_counts(world['pool'][:k])
                present = list(np.flatnonzero(counts))
                direct = (counts > 0).astype(float)
                wrong = (harness.key_counts(other[:k]) > 0).astype(float)
                scores = {
                    'free_count': np.log1p(counts),
                    'free_set': np.log(direct + FLOOR),
                    'wrong_world': np.log(wrong + FLOOR),
                    'meta_identity': np.log(np.maximum(
                        direct, identity[present].max(axis=0) if present else 0.) + FLOOR),
                    'meta_uniform': np.log(np.maximum(
                        direct, uniform[present].max(axis=0) if present else 0.) + FLOOR),
                    'meta_identity_scrambled': np.log(np.maximum(
                        direct,
                        identity_scrambled[present].max(axis=0) if present else 0.) + FLOOR),
                    'meta_metric': np.log(np.maximum(
                        direct, metric_scores(metric, latent, present)) + FLOOR),
                    'meta_metric_scrambled': np.log(np.maximum(
                        direct, metric_scores(metric_scrambled, latent_scrambled,
                                              present)) + FLOOR),
                }
                scores['meta_both'] = np.log(np.maximum(
                    np.exp(scores['meta_identity']),
                    np.exp(scores['meta_metric'])))
                for name, score in scores.items():
                    ranks[f'{name}:{k}'] = ranks_of(harness.order_from_key_scores(score))
            for mechanism in world['test']:
                task = make_task(catalog, mechanism, rng)
                consistent = np.flatnonzero(vector_test(harness.packed, task['visible_pos'],
                                                        task['visible_neg']))
                if len(consistent) == 0:
                    unsolvable += 1
                    continue
                good = vector_test(harness.packed, task['hidden_pos'],
                                   task['hidden_neg'])[consistent]
                view = {'consistent': consistent,
                        'select': np.lexsort((harness.complexity[consistent],
                                              harness.sizes[consistent]))}
                where = {int(index): position for position, index in enumerate(consistent)}
                picks = {arm: dict(_picks(view, ranks[arm], catalog.size)) for arm in arms}
                journal.write(json.dumps({
                    'replication': number, 'split': split, 'world': number_in_split,
                    'mechanism': int(mechanism), 'keys': list(world['keys']),
                    'pool': [int(index) for index in world['pool'][:max(ADAPT)]],
                    'other_pool': [int(index) for index in other[:max(ADAPT)]],
                    'visible': task['visible'], 'hidden': task['hidden'],
                    'picks': {arm: {str(budget): pick for budget, pick in row.items()}
                              for arm, row in picks.items()}}) + '\n')
                for arm in arms:
                    for budget, pick in picks[arm].items():
                        outcomes[split][arm][budget].append(
                            0 if pick < 0 else int(good[where[pick]]))
    return evaluation, outcomes, arms, unsolvable


def _picks(view, position, catalog_size):
    ranked = position[view['consistent']]
    for budget in BUDGETS:
        limit = catalog_size if budget is None else budget
        chosen = -1
        for candidate in view['select']:
            if ranked[candidate] < limit:
                chosen = int(view['consistent'][candidate])
                break
        yield budget, chosen


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

        rate = {arm: {str(budget): float(np.mean(outcomes[split][arm][budget]))
                      for budget in BUDGETS} for arm in arms}
        best_free = {(k, budget): max(FREE, key=lambda name: rate[f'{name}:{k}'][str(budget)])
                     for k in ADAPT for budget in BUDGETS}
        entry = {'tasks': tasks, 'rate': rate,
                 'best_free': {str(k): {str(budget): best_free[(k, budget)]
                                        for budget in BUDGETS} for k in ADAPT}}
        for name in ('meta_identity', 'meta_metric', 'meta_both'):
            entry[f'{name}_minus_best_free'] = {
                str(k): {str(budget): paired(f'{name}:{k}',
                                             f'{best_free[(k, budget)]}:{k}', budget)
                         for budget in BUDGETS} for k in ADAPT}
        entry['meta_identity_minus_uniform'] = {
            str(k): {str(budget): paired(f'meta_identity:{k}', f'meta_uniform:{k}', budget)
                     for budget in BUDGETS} for k in ADAPT}
        entry['meta_identity_minus_scrambled'] = {
            str(k): {str(budget): paired(f'meta_identity:{k}',
                                         f'meta_identity_scrambled:{k}', budget)
                     for budget in BUDGETS} for k in ADAPT}
        entry['meta_metric_minus_scrambled'] = {
            str(k): {str(budget): paired(f'meta_metric:{k}', f'meta_metric_scrambled:{k}',
                                         budget) for budget in BUDGETS} for k in ADAPT}
        entry['free_set_minus_static'] = {
            str(k): {str(budget): paired(f'free_set:{k}',
                                         max(STATIC, key=lambda n: rate[n][str(budget)]),
                                         budget) for budget in BUDGETS} for k in ADAPT}
        entry['free_set_minus_wrong_world'] = {
            str(k): {str(budget): paired(f'free_set:{k}', f'wrong_world:{k}', budget)
                     for budget in BUDGETS} for k in ADAPT}
        block[split] = entry
    return block


def gates(block):
    """The predeclared criteria, read exactly where the protocol says."""
    def positive(entry, floor=0.):
        return entry['sum'] >= floor and entry['interval'][0] > 0

    pooled = {'tasks': sum(block[split]['tasks'] for split in block)}
    g1_free = sum(block[split]['free_set_minus_static']['32']['256']['sum'] for split in block)
    g1_wrong = sum(block[split]['free_set_minus_wrong_world']['32']['256']['sum']
                   for split in block)
    g1_low = min(block[split]['free_set_minus_static']['32']['256']['interval'][0]
                 for split in block)
    g1_wrong_low = min(block[split]['free_set_minus_wrong_world']['32']['256']['interval'][0]
                       for split in block)
    pooled['G1'] = {'free_set_minus_static': g1_free, 'free_set_minus_wrong_world': g1_wrong,
                    'passed': g1_free >= 400 and g1_wrong >= 400 and g1_low > 0
                    and g1_wrong_low > 0}
    new_triple = block['new_triple']
    pooled['G2'] = {'passed': all(
        positive(new_triple['meta_identity_minus_best_free'][str(k)]['1024'], 20)
        and positive(new_triple['meta_identity_minus_uniform'][str(k)]['1024'])
        and positive(new_triple['meta_identity_minus_scrambled'][str(k)]['1024'])
        for k in (1, 2, 4))}
    new_family = block['new_family']
    pooled['G3'] = {'passed': all(
        positive(new_family['meta_metric_minus_best_free'][str(k)]['1024'], 20)
        and positive(new_family['meta_metric_minus_scrambled'][str(k)]['1024'])
        for k in (2, 4))}
    return pooled


def main():
    if OUT.exists():
        raise RuntimeError('analysis exists')
    DEST.mkdir(parents=True, exist_ok=True)
    process = psutil.Process()
    wall, cpu = time.perf_counter(), time.process_time()

    harness = Harness()
    latent = descriptors(harness)
    result = {'scope': 'confirmatory run, EXPERIMENT-mechanism-growth-confirmation.md',
              'runner_sha256': hashlib.sha256(SCRIPT.read_bytes()).hexdigest(),
              'catalog': {'rows': harness.catalog.size, 'digest': harness.catalog.digest()},
              'budgets': [str(budget) for budget in BUDGETS], 'adapt': list(ADAPT),
              'held_out_families': list(HELD_OUT_FAMILIES),
              'training_worlds': TRAINING_WORLDS, 'prior_solved': PRIOR_SOLVED,
              'replications': {}}

    for number, seed in REPLICATIONS:
        path = DEST / f'decisions-{number}.jsonl'
        if path.exists():
            raise RuntimeError(f'{path} exists')
        with path.open('w', encoding='utf-8') as journal:
            evaluation, outcomes, arms, unsolvable = replication(
                harness, latent, number, seed, journal)
        block = summarise(outcomes, arms, seed)
        result['replications'][str(number)] = {
            'seed': seed, 'unsolvable': unsolvable, 'splits': block,
            'gates': gates(block),
            'worlds': {split: [{'keys': list(world['keys']), 'members': len(world['members'])}
                               for world in worlds] for split, worlds in evaluation.items()},
            'decisions_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        gate = result['replications'][str(number)]['gates']
        print('replication {}: G1 {} G2 {} G3 {}'.format(
            number, gate['G1']['passed'], gate['G2']['passed'], gate['G3']['passed']))

    result['cost'] = {'wall_seconds': time.perf_counter() - wall,
                      'cpu_seconds': time.process_time() - cpu,
                      'peak_rss_mb': process.memory_info().rss / 1e6}
    write_json(OUT, result)

    for claim in ('G1', 'G2', 'G3'):
        verdicts = [result['replications'][str(number)]['gates'][claim]['passed']
                    for number, _ in REPLICATIONS]
        print('{}: {}'.format(claim, 'passed' if all(verdicts) else 'failed'), verdicts)
    print('cost: {wall_seconds:.1f}s wall, {cpu_seconds:.1f}s cpu, {peak_rss_mb:.0f} MB'
          .format(**result['cost']))


if __name__ == '__main__':
    main()
