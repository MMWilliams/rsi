"""Confirmatory run: EXPERIMENT-mechanism-family-confirmation.md.

Every constant below is quoted by the protocol. Two replications on seeds drawn
after it was written. Each builds the champion's cross-world prior from 400
training worlds, then lets the champion and the family-inference agent live
the same held-out worlds at six budgets, and journals every decision with the
example strings it was made on, so `audit_mechanism_family_confirmation.py` can
rebuild every task from its strings and re-derive every total, gate and
sampled decision without this file's random streams or its simulator.

Nothing here is trained. The agent under test is fixed: a posterior over which
three families the world is drawn from, uniform prior over every triple, slip
0.2, weight 2, on top of the champion's orderings; no hedge at budgets 128 and
256, half the budget hedged from 512 up.
"""
from __future__ import annotations

import hashlib
import json
import multiprocessing
import random
import sys
import time
from pathlib import Path

import numpy as np
import psutil

from rsi.common import ROOT, write_json
from rsi.family_inference import FamilySimulator
from rsi.growth_coach import CHAMPION, UNHEDGED, Prior, Simulator, draw_worlds, triples
from rsi.mechanism_worlds import Harness

SCRIPT = Path(__file__)
OUT = ROOT / 'analysis/mechanism-family-confirmation-20260923.json'
DEST = ROOT / 'runs/mechanism-family-confirmation-20260923'
REPLICATIONS = (('A', 971101), ('B', 972101))

TRAINING_WORLDS = 400
PRIOR_SOLVED = 64
STREAM = 100
KEYS_PER_WORLD = 14
MINIMUM_MEMBERS = 130
HELD_OUT_FAMILIES = ('popcount', 'xormod')
NEW_TRIPLE_SHARE = .2
BUDGETS = (128, 256, 512, 1024, 2048, 4096)
WEIGHT, SLIP = 2., .2
UNHEDGED_UP_TO = 256

EVAL_WORLDS = 128
SPLITS = ('seen_triple', 'new_triple', 'new_family')
IMPROVE_SPLITS = ('seen_triple', 'new_triple')
SAFE_SPLITS = ('new_family',)
BOOT = 20000
WORKERS = 12
_STATE = {}


def family_coach(budget):
    return UNHEDGED if budget <= UNHEDGED_UP_TO else CHAMPION


def paired(agent, champion, seed):
    difference = np.asarray(agent) - np.asarray(champion)
    draws = np.random.default_rng(seed).integers(0, len(difference), (BOOT, len(difference)))
    sums = difference[draws].sum(axis=1)
    return {'sum': difference.sum(axis=0).tolist(),
            'low': np.percentile(sums, 2.5, axis=0).tolist(),
            'high': np.percentile(sums, 97.5, axis=0).tolist()}


def gates(contrasts):
    """Gains at every budget on trained and untrained combinations; no
    significant loss at any budget on worlds of an untrained family."""
    improve = {split: {str(b): contrasts[split]['low'][i] > 0 for i, b in enumerate(BUDGETS)}
               for split in IMPROVE_SPLITS}
    safe = {split: {str(b): contrasts[split]['high'][i] >= 0 for i, b in enumerate(BUDGETS)}
            for split in SAFE_SPLITS}
    passed = all(all(v.values()) for v in improve.values()) and \
        all(all(v.values()) for v in safe.values())
    return {'improve': improve, 'safe': safe, 'passed': passed}


def _init(seed, prior, views):
    harness = Harness()
    harness.set_tiebreak(seed + 77)
    _STATE.update(plain=Simulator(harness), family=FamilySimulator(harness, [], WEIGHT, SLIP),
                  prior=prior, views=views)


def _live(key):
    s = _STATE
    out = {}
    for arm in ('champion', 'family'):
        per_budget = []
        for budget in BUDGETS:
            trace = []
            if arm == 'champion':
                s['plain'].lifetime(CHAMPION, s['views'][key], s['prior'], budget, trace=trace)
            else:
                s['family'].lifetime(family_coach(budget), s['views'][key], s['prior'], budget,
                                     trace=trace)
            per_budget.append([(d['pick'], d['hit']) for d in trace])
        out[arm] = per_budget
    return out


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
    prior = Prior(harness, observed)
    views = {f'{split}:{n:03d}': simulator.views(world['stream'], rng, examples=True)
             for split, worlds in groups.items() for n, world in enumerate(worlds)}
    names = {split: [key for key in views if key.startswith(split + ':')] for split in groups}
    print('replication {} setup done'.format(number), flush=True)

    keys = [key for split in SPLITS for key in names[split]]
    with multiprocessing.get_context('spawn').Pool(
            WORKERS, initializer=_init, initargs=(seed, prior, views)) as pool:
        lives = dict(zip(keys, pool.map(_live, keys, chunksize=1)))

    totals = {split: {} for split in SPLITS}
    for split in SPLITS:
        for key in names[split]:
            for step, view in enumerate(views[key]):
                journal.write(json.dumps({'kind': 'task', 'replication': number, 'world': key,
                                          'step': step, 'mechanism': view['mechanism'],
                                          'visible': view['visible'],
                                          'hidden': view['hidden']}) + '\n')
        for arm in ('champion', 'family'):
            per_world = []
            for key in names[split]:
                row = []
                for budget, decisions in zip(BUDGETS, lives[key][arm]):
                    for step, (pick, hit) in enumerate(decisions):
                        journal.write(json.dumps({
                            'kind': 'decision', 'replication': number, 'world': key,
                            'arm': arm, 'budget': budget, 'step': step, 'pick': pick,
                            'hit': hit}) + '\n')
                    row.append(sum(hit for _pick, hit in decisions))
                per_world.append(row)
            totals[split][arm] = np.array(per_world)
    contrasts = {split: paired(totals[split]['family'], totals[split]['champion'], seed + 3)
                 for split in SPLITS}
    return {'seed': seed, 'new_triples': [list(t) for t in new_triples],
            'worlds': {split: [{'key': key, 'keys': list(world['keys']),
                                'triple': list(world['triple']), 'stream': world['stream']}
                               for key, world in zip(names[split], worlds)]
                       for split, worlds in groups.items()},
            'prior_solved': solved,
            'totals': {s: {a: v.tolist() for a, v in arms.items()} for s, arms in totals.items()},
            'mean_by_budget': {s: {a: v.mean(axis=0).tolist() for a, v in arms.items()}
                               for s, arms in totals.items()},
            'contrasts': contrasts, 'gates': gates(contrasts)}


def main():
    if OUT.exists():
        raise RuntimeError('analysis exists')
    DEST.mkdir(parents=True, exist_ok=True)
    process = psutil.Process()
    wall, cpu = time.perf_counter(), time.process_time()
    harness = Harness()
    simulator = Simulator(harness)
    result = {'scope': 'confirmatory run, EXPERIMENT-mechanism-family-confirmation.md',
              'runner_sha256': hashlib.sha256(SCRIPT.read_bytes()).hexdigest(),
              'catalog': {'rows': harness.catalog.size, 'digest': harness.catalog.digest()},
              'budgets': list(BUDGETS), 'splits': list(SPLITS), 'eval_worlds': EVAL_WORLDS,
              'weight': WEIGHT, 'slip': SLIP, 'unhedged_up_to': UNHEDGED_UP_TO,
              'replications': {}}
    for number, seed in REPLICATIONS:
        path = DEST / f'decisions-{number}.jsonl'
        if path.exists():
            raise RuntimeError(f'{path} exists')
        with path.open('w', encoding='utf-8') as journal:
            block = replication(harness, simulator, number, seed, journal)
        block['decisions_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        result['replications'][number] = block
        print('replication {}: gate {}'.format(number, block['gates']['passed']), flush=True)
    result['passed'] = all(b['gates']['passed'] for b in result['replications'].values())
    result['cost'] = {'wall_seconds': time.perf_counter() - wall,
                      'cpu_seconds_parent': time.process_time() - cpu,
                      'peak_rss_mb_parent': process.memory_info().rss / 1e6}
    write_json(OUT, result)
    for number, block in result['replications'].items():
        print(f'\n== replication {number} (seed {block["seed"]}): family agent minus champion')
        for split in SPLITS:
            e = block['contrasts'][split]
            print('  {:12s}'.format(split) + ''.join(
                '{:+5.0f} [{:.0f},{:.0f}]'.format(s, lo, hi).rjust(17)
                for s, lo, hi in zip(e['sum'], e['low'], e['high'])))
    print('\nclaim:', 'passed' if result['passed'] else 'failed')
    print('cost: {:.0f}s wall'.format(result['cost']['wall_seconds']))


if __name__ == '__main__':
    sys.exit(main())
