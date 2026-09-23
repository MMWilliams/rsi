"""Confirmatory run: EXPERIMENT-mechanism-coach-confirmation.md.

Everything that decides the outcome is fixed in the protocol and in the
constants below, which the protocol quotes. Two replications on seeds drawn
after the protocol was written. Each trains a coach from the champion by the
frozen procedure, validates it against the champion on fresh lifetimes built
from training material only, deploys it at each budget where validation shows
a high-confidence gain in every kind of lifetime and runs the champion
elsewhere, scores the deployed policy and the champion on held-out worlds at
six budgets, and journals every decision with the example strings it was made
on, so `audit_mechanism_coach_confirmation.py` can rebuild every task from its
strings and re-derive every total, deployment, gate and sampled decision
without this file's random streams or its simulator.
"""
from __future__ import annotations

import hashlib
import json
import random
import sys
import time
from pathlib import Path

import numpy as np
import psutil

from rsi.common import ROOT, write_json
from rsi.growth_coach import (CHAMPION, Pool, Prior, Simulator, Trainer, draw_worlds,
                              triples)
from rsi.mechanism_worlds import Harness

SCRIPT = Path(__file__)
OUT = ROOT / 'analysis/mechanism-coach-confirmation-20260923.json'
DEST = ROOT / 'runs/mechanism-coach-confirmation-20260923'
REPLICATIONS = (('A', 951101), ('B', 952101))

# The frozen procedure: identical to mechanism_coach_fixed_hedge_dev.py.
TRAINING_WORLDS = 400
PRIOR_SOLVED = 64
STREAM = 100
KEYS_PER_WORLD = 14
MINIMUM_MEMBERS = 130
HELD_OUT_FAMILIES = ('popcount', 'xormod')
NEW_TRIPLE_SHARE = .2
BUDGETS = (128, 256, 512, 1024, 2048, 4096)
SEARCHED = ('unknown', 'pair', 'count', 'depth1', 'affinity', 'soft', 'pick', 'tilt')
SIGMA = {'unknown': .2, 'pair': .2, 'count': .25, 'depth1': 1., 'affinity': .25,
         'soft': .2, 'pick': .25, 'tilt': .2}
PAIRS = 8
SUPPORTED_PER_GENERATION = 6
PRACTICE_PER_GENERATION = 2
GENERATIONS = 40

# High-confidence deployment: validation lifetimes of each kind, never from
# evaluation worlds; deploy at a budget iff every kind's interval is above zero.
VALIDATION_WORLDS = 32
KINDS = ('supported', 'family', 'combination')

# Evaluation and the gate.
EVAL_WORLDS = 128
SPLITS = ('seen_triple', 'new_triple', 'new_family')
IMPROVE_BUDGETS = (1024, 2048, 4096)
SAFE_BUDGETS = (128, 256, 512)
BOOT = 20000
WORKERS = 12


def paired(coach, champion, seed):
    """Coach minus champion over worlds: sum and 95% bootstrap interval, per
    budget. Worlds are the resampled unit because a life is one sample."""
    difference = np.asarray(coach) - np.asarray(champion)
    draws = np.random.default_rng(seed).integers(0, len(difference),
                                                 (BOOT, len(difference)))
    sums = difference[draws].sum(axis=1)
    return {'sum': difference.sum(axis=0).tolist(),
            'low': np.percentile(sums, 2.5, axis=0).tolist(),
            'high': np.percentile(sums, 97.5, axis=0).tolist()}


def deployment(validation, seed):
    """Per budget, whether every kind of validation lifetime shows the coach
    above the champion with its interval entirely above zero."""
    lows = {kind: paired(validation[kind]['coach'], validation[kind]['champion'],
                         seed + i)['low'] for i, kind in enumerate(KINDS)}
    return [all(lows[kind][b] > 0 for kind in KINDS) for b in range(len(BUDGETS))]


def gates(contrasts):
    """Improvement at every budget where the loop receives evidence, and no
    significant loss anywhere else, on every split."""
    improve = {split: {str(b): contrasts[split]['low'][BUDGETS.index(b)] > 0
                       for b in IMPROVE_BUDGETS} for split in SPLITS}
    safe = {split: {str(b): contrasts[split]['high'][BUDGETS.index(b)] >= 0
                    for b in SAFE_BUDGETS} for split in SPLITS}
    passed = all(all(v.values()) for v in improve.values()) and \
        all(all(v.values()) for v in safe.values())
    return {'improve': improve, 'safe': safe, 'passed': passed}


def replication(harness, simulator, number, seed, journal):
    harness.set_tiebreak(seed + 77)
    rng = random.Random(seed)
    seen = [family for family in harness.by_family if family not in HELD_OUT_FAMILIES]
    seen_pool = triples(harness, seen, rng, KEYS_PER_WORLD, MINIMUM_MEMBERS)
    rng.shuffle(seen_pool)
    cut = max(1, round(NEW_TRIPLE_SHARE * len(seen_pool)))
    new_triples, train_triples = seen_pool[:cut], seen_pool[cut:]
    held_pool = [triple for triple in triples(harness, harness.by_family, rng, KEYS_PER_WORLD,
                                              MINIMUM_MEMBERS)
                 if set(triple) & set(HELD_OUT_FAMILIES)]
    groups = {name: draw_worlds(harness, pool_, EVAL_WORLDS, rng, KEYS_PER_WORLD,
                                MINIMUM_MEMBERS, STREAM)
              for name, pool_ in (('seen_triple', train_triples), ('new_triple', new_triples),
                                  ('new_family', held_pool))}
    reserved = {index for worlds in groups.values() for world in worlds
                for index in world['stream']}
    training = draw_worlds(harness, train_triples, TRAINING_WORLDS, rng, KEYS_PER_WORLD,
                           MINIMUM_MEMBERS, 0)
    solved = []
    for world in training:
        allowed = [index for index in world['members'] if index not in reserved]
        solved.append(sorted(rng.sample(allowed, min(PRIOR_SOLVED, len(allowed)))))
    observed = [sorted({harness.key_index[key] for key in harness.observed_keys(chosen)})
                for chosen in solved]
    priors = {'main': Prior(harness, observed)}
    practice_families = sorted({family for triple in train_triples for family in triple})
    for family in practice_families:
        kept = [sets for world, sets in zip(training, observed) if family not in world['triple']]
        priors[f'without:{family}'] = Prior(harness, kept)
    for triple in train_triples:
        kept = [sets for world, sets in zip(training, observed)
                if world['triple'] != tuple(sorted(triple))]
        priors[f'without:{"+".join(sorted(triple))}'] = Prior(harness, kept)
    views = {f'{split}:{n:02d}': simulator.views(world['stream'], rng, examples=True)
             for split, worlds in groups.items() for n, world in enumerate(worlds)}
    names = {split: [key for key in views if key.startswith(split + ':')] for split in groups}

    def fresh_views(triple_pool, count, stream_rng):
        out = []
        for world in draw_worlds(harness, triple_pool, count, stream_rng, KEYS_PER_WORLD,
                                 MINIMUM_MEMBERS, STREAM + 40):
            stream = [index for index in world['stream'] if index not in reserved][:STREAM]
            out.append(simulator.views(stream, stream_rng))
        return out

    def lifetimes(stream_rng):
        out = [(v, 'main', 'supported')
               for v in fresh_views(train_triples, SUPPORTED_PER_GENERATION, stream_rng)]
        for _ in range(PRACTICE_PER_GENERATION):
            family = practice_families[stream_rng.randrange(len(practice_families))]
            with_family = [t for t in train_triples if family in t]
            out.append((fresh_views(with_family, 1, stream_rng)[0], f'without:{family}',
                        'practice'))
        return out

    pool = Pool(WORKERS, seed + 77, priors, views, BUDGETS)
    trainer = Trainer([BUDGETS], SEARCHED, SIGMA, seed + 21, pairs=PAIRS)
    stream_rng = random.Random(seed + 31)
    history = []
    for generation in range(1, GENERATIONS + 1):
        trainer.generation(pool, lifetimes(stream_rng))
        history.append(trainer.coach(0).as_dict())
        print('replication {} generation {:2d}: {}'.format(
            number, generation, {k: round(v, 2) for k, v in history[-1].items()}), flush=True)
    coach = trainer.coach(0)

    # Validation: fresh lifetimes of each kind, from training material only.
    validation_rng = random.Random(seed + 51)
    lives = {kind: [] for kind in KINDS}
    for _ in range(VALIDATION_WORLDS):
        lives['supported'].append((fresh_views(train_triples, 1, validation_rng)[0], 'main'))
        family = practice_families[validation_rng.randrange(len(practice_families))]
        lives['family'].append((fresh_views([t for t in train_triples if family in t], 1,
                                            validation_rng)[0], f'without:{family}'))
        triple = train_triples[validation_rng.randrange(len(train_triples))]
        lives['combination'].append((fresh_views([triple], 1, validation_rng)[0],
                                     f'without:{"+".join(sorted(triple))}'))
    validation = {}
    for kind in KINDS:
        results = pool.map([(arm, life, 'earned', prior) for arm in (coach, CHAMPION)
                            for life, prior in lives[kind]])
        totals_ = [[int(hits.sum()) for hits in r] for r in results]
        validation[kind] = {'coach': totals_[:VALIDATION_WORLDS],
                            'champion': totals_[VALIDATION_WORLDS:]}
    deploy = deployment(validation, seed + 53)
    print('replication {} deploys the coach at {}'.format(
        number, [b for b, on in zip(BUDGETS, deploy) if on]), flush=True)

    # Evaluation: the champion, the trained coach, and the deployed policy,
    # which is the coach at deployed budgets and the champion elsewhere.
    for split in groups:
        for key in names[split]:
            for step, view in enumerate(views[key]):
                journal.write(json.dumps({'kind': 'task', 'replication': number, 'world': key,
                                          'step': step, 'mechanism': view['mechanism'],
                                          'visible': view['visible'],
                                          'hidden': view['hidden']}) + '\n')
    traces = {arm: {split: pool.map([(chosen, world, 'earned', 'main')
                                     for world in names[split]], traced=True)
                    for split in groups}
              for arm, chosen in (('champion', CHAMPION), ('trained', coach))}
    pool.close()
    traces['coach'] = {split: [[traces['trained' if on else 'champion'][split][w][b]
                                for b, on in enumerate(deploy)]
                               for w in range(len(names[split]))] for split in groups}
    totals = {split: {} for split in groups}
    for arm in ('champion', 'coach', 'trained'):
        for split in groups:
            per_world = []
            for key, per_budget in zip(names[split], traces[arm][split]):
                if arm != 'trained':
                    for budget, trace in zip(BUDGETS, per_budget):
                        for decision in trace:
                            journal.write(json.dumps({
                                'kind': 'decision', 'replication': number, 'world': key,
                                'arm': arm, 'budget': budget, 'step': decision['step'],
                                'pick': decision['pick'], 'hit': decision['hit']}) + '\n')
                per_world.append([sum(d['hit'] for d in trace) for trace in per_budget])
            totals[split][arm] = np.array(per_world)

    contrasts = {split: paired(totals[split]['coach'], totals[split]['champion'], seed + 3)
                 for split in groups}
    trained = {split: paired(totals[split]['trained'], totals[split]['champion'], seed + 3)
               for split in groups}
    return {'seed': seed, 'coach': coach.as_dict(), 'history': history,
            'validation': validation, 'deploy': deploy, 'trained_contrasts': trained,
            'new_triples': [list(t) for t in new_triples],
            'worlds': {split: [{'key': key, 'keys': list(world['keys']),
                                'triple': list(world['triple']), 'stream': world['stream']}
                               for key, world in zip(names[split], worlds)]
                       for split, worlds in groups.items()},
            'prior_solved': solved,
            'totals': {split: {arm: v.tolist() for arm, v in arms_.items()}
                       for split, arms_ in totals.items()},
            'mean_by_budget': {split: {arm: v.mean(axis=0).tolist() for arm, v in arms_.items()}
                               for split, arms_ in totals.items()},
            'contrasts': contrasts, 'gates': gates(contrasts)}


def main():
    if OUT.exists():
        raise RuntimeError('analysis exists')
    DEST.mkdir(parents=True, exist_ok=True)
    process = psutil.Process()
    wall, cpu = time.perf_counter(), time.process_time()
    harness = Harness()
    simulator = Simulator(harness)
    result = {'scope': 'confirmatory run, EXPERIMENT-mechanism-coach-confirmation.md',
              'runner_sha256': hashlib.sha256(SCRIPT.read_bytes()).hexdigest(),
              'catalog': {'rows': harness.catalog.size, 'digest': harness.catalog.digest()},
              'budgets': list(BUDGETS), 'splits': list(SPLITS),
              'improve_budgets': list(IMPROVE_BUDGETS), 'safe_budgets': list(SAFE_BUDGETS),
              'eval_worlds': EVAL_WORLDS, 'generations': GENERATIONS, 'replications': {}}
    for number, seed in REPLICATIONS:
        path = DEST / f'decisions-{number}.jsonl'
        if path.exists():
            raise RuntimeError(f'{path} exists')
        with path.open('w', encoding='utf-8') as journal:
            block = replication(harness, simulator, number, seed, journal)
        block['decisions_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        result['replications'][number] = block
        print('replication {}: gate {}'.format(number, block['gates']['passed']), flush=True)
    result['passed'] = all(block['gates']['passed']
                           for block in result['replications'].values())
    result['cost'] = {'wall_seconds': time.perf_counter() - wall,
                      'cpu_seconds_parent': time.process_time() - cpu,
                      'peak_rss_mb_parent': process.memory_info().rss / 1e6}
    write_json(OUT, result)

    for number, block in result['replications'].items():
        deployed = [b for b, on in zip(BUDGETS, block['deploy']) if on]
        for label, key in (('deployed policy', 'contrasts'), ('trained coach', 'trained_contrasts')):
            print(f'\n== replication {number} (seed {block["seed"]}), deployed at {deployed}: '
                  f'{label} minus champion')
            for split in SPLITS:
                entry = block[key][split]
                print('  {:12s}'.format(split) + ''.join(
                    '{:+5.0f} [{:.0f},{:.0f}]'.format(s, lo, hi).rjust(17)
                    for s, lo, hi in zip(entry['sum'], entry['low'], entry['high'])))
    print('\nclaim:', 'passed' if result['passed'] else 'failed')
    print('cost: {:.0f}s wall'.format(result['cost']['wall_seconds']))


if __name__ == '__main__':
    sys.exit(main())
