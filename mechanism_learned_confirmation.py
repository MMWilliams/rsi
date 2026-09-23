"""Confirmatory run: EXPERIMENT-mechanism-learned-confirmation.md.

Every constant below is quoted by the protocol. Two replications on seeds drawn
after it was written. Each draws 1,600 training worlds, fits the champion's
pair prior on the first 400, learns atom groups from co-occurrence across the
first 400 and across all 1,600 (`rsi.learned_groups.learn_groups`, count by
held-out world likelihood), then lets the champion and the family agent on
each learned grouping live the same held-out worlds at six budgets. Every
decision is journaled with the example strings it was made on, and the solved
mechanisms of all 1,600 training worlds are recorded, so
`audit_mechanism_learned_confirmation.py` can relearn the groups and replay
decisions without this file's random streams or its simulator.

Nothing here is trained by gradient or search; the only thing learned is the
grouping, from which atoms appear together in training worlds. No family label
is read anywhere in the agent.
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
from rsi.growth_coach import CHAMPION, UNHEDGED, Prior, Simulator, draw_worlds, triples
from rsi.learned_groups import LearnedFamilySimulator, learn_groups
from rsi.mechanism_worlds import Harness

SCRIPT = Path(__file__)
OUT = ROOT / 'analysis/mechanism-learned-confirmation-20260923.json'
DEST = ROOT / 'runs/mechanism-learned-confirmation-20260923'
REPLICATIONS = (('A', 981101), ('B', 982101))

TRAINING_WORLDS = 1600
PRIOR_WORLDS = 400
EARLY_WORLDS = 400
PRIOR_SOLVED = 64
STREAM = 100
KEYS_PER_WORLD = 14
MINIMUM_MEMBERS = 130
HELD_OUT_FAMILIES = ('popcount', 'xormod')
NEW_TRIPLE_SHARE = .2
BUDGETS = (128, 256, 512, 1024, 2048, 4096)
GROUP_CHOICES = range(3, 13)
WEIGHT, SLIP = 2., .2
UNHEDGED_UP_TO = 256

EVAL_WORLDS = 128
SPLITS = ('seen_triple', 'new_triple', 'new_family')
IMPROVE_SPLITS = ('seen_triple', 'new_triple')
SAFE_SPLITS = ('new_family',)
ARMS = ('champion', 'learned', 'early')
BOOT = 20000
WORKERS = 12
_STATE = {}


def agent_coach(budget):
    return UNHEDGED if budget <= UNHEDGED_UP_TO else CHAMPION


def paired(agent, champion, seed):
    difference = np.asarray(agent) - np.asarray(champion)
    draws = np.random.default_rng(seed).integers(0, len(difference), (BOOT, len(difference)))
    sums = difference[draws].sum(axis=1)
    return {'sum': difference.sum(axis=0).tolist(),
            'low': np.percentile(sums, 2.5, axis=0).tolist(),
            'high': np.percentile(sums, 97.5, axis=0).tolist()}


def growth(totals, seed):
    """Learned minus early, summed over every split and budget; worlds are
    resampled within each split and the splits' sums added."""
    rng = np.random.default_rng(seed)
    sums = np.zeros(BOOT)
    total = 0.
    for split in SPLITS:
        per_world = (np.asarray(totals[split]['learned'])
                     - np.asarray(totals[split]['early'])).sum(axis=1)
        total += per_world.sum()
        draws = rng.integers(0, len(per_world), (BOOT, len(per_world)))
        sums += per_world[draws].sum(axis=1)
    return {'sum': float(total), 'low': float(np.percentile(sums, 2.5)),
            'high': float(np.percentile(sums, 97.5))}


def gates(contrasts, grown):
    """C-learned as C-family was gated; C-growth on the pooled difference."""
    improve = {split: {str(b): contrasts[split]['low'][i] > 0 for i, b in enumerate(BUDGETS)}
               for split in IMPROVE_SPLITS}
    safe = {split: {str(b): contrasts[split]['high'][i] >= 0 for i, b in enumerate(BUDGETS)}
            for split in SAFE_SPLITS}
    learned = all(all(v.values()) for v in improve.values()) and \
        all(all(v.values()) for v in safe.values())
    return {'improve': improve, 'safe': safe, 'learned_passed': learned,
            'growth_passed': grown['low'] > 0}


def _init(seed, prior, views, labels):
    harness = Harness()
    harness.set_tiebreak(seed + 77)
    _STATE.update(prior=prior, views=views,
                  agents={'champion': Simulator(harness),
                          'learned': LearnedFamilySimulator(harness, labels['learned'],
                                                            WEIGHT, SLIP),
                          'early': LearnedFamilySimulator(harness, labels['early'],
                                                          WEIGHT, SLIP)})


def _live(key):
    s = _STATE
    out = {}
    for arm, agent in s['agents'].items():
        per_budget = []
        for budget in BUDGETS:
            trace = []
            agent.lifetime(CHAMPION if arm == 'champion' else agent_coach(budget),
                           s['views'][key], s['prior'], budget, trace=trace)
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
    prior = Prior(harness, observed[:PRIOR_WORLDS])
    keys = len(harness.key_names)
    labels, counts = {}, {}
    for name, size in (('learned', TRAINING_WORLDS), ('early', EARLY_WORLDS)):
        labels[name], counts[name] = learn_groups(observed[:size], keys,
                                                  choices=GROUP_CHOICES, select='likelihood')
    views = {f'{split}:{n:03d}': simulator.views(world['stream'], rng, examples=True)
             for split, worlds in groups.items() for n, world in enumerate(worlds)}
    names = {split: [key for key in views if key.startswith(split + ':')] for split in groups}
    print('replication {} setup done, groups {}'.format(number, counts), flush=True)

    order = [key for split in SPLITS for key in names[split]]
    with multiprocessing.get_context('spawn').Pool(
            WORKERS, initializer=_init, initargs=(seed, prior, views, labels)) as pool:
        lives = dict(zip(order, pool.map(_live, order, chunksize=1)))

    totals = {split: {} for split in SPLITS}
    for split in SPLITS:
        for key in names[split]:
            for step, view in enumerate(views[key]):
                journal.write(json.dumps({'kind': 'task', 'replication': number, 'world': key,
                                          'step': step, 'mechanism': view['mechanism'],
                                          'visible': view['visible'],
                                          'hidden': view['hidden']}) + '\n')
        for arm in ARMS:
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
    contrasts = {split: paired(totals[split]['learned'], totals[split]['champion'], seed + 3)
                 for split in SPLITS}
    early = {split: paired(totals[split]['early'], totals[split]['champion'], seed + 3)
             for split in SPLITS}
    grown = growth(totals, seed + 4)
    return {'seed': seed, 'new_triples': [list(t) for t in new_triples],
            'group_counts': counts, 'labels': {k: v.tolist() for k, v in labels.items()},
            'worlds': {split: [{'key': key, 'keys': list(world['keys']),
                                'triple': list(world['triple']), 'stream': world['stream']}
                               for key, world in zip(names[split], worlds)]
                       for split, worlds in groups.items()},
            'training_solved': solved,
            'totals': {s: {a: v.tolist() for a, v in arms.items()} for s, arms in totals.items()},
            'mean_by_budget': {s: {a: v.mean(axis=0).tolist() for a, v in arms.items()}
                               for s, arms in totals.items()},
            'contrasts': contrasts, 'early_contrasts': early, 'growth': grown,
            'gates': gates(contrasts, grown)}


def main():
    if OUT.exists():
        raise RuntimeError('analysis exists')
    DEST.mkdir(parents=True, exist_ok=True)
    process = psutil.Process()
    wall, cpu = time.perf_counter(), time.process_time()
    harness = Harness()
    simulator = Simulator(harness)
    result = {'scope': 'confirmatory run, EXPERIMENT-mechanism-learned-confirmation.md',
              'runner_sha256': hashlib.sha256(SCRIPT.read_bytes()).hexdigest(),
              'catalog': {'rows': harness.catalog.size, 'digest': harness.catalog.digest()},
              'budgets': list(BUDGETS), 'splits': list(SPLITS), 'eval_worlds': EVAL_WORLDS,
              'training_worlds': TRAINING_WORLDS, 'prior_worlds': PRIOR_WORLDS,
              'early_worlds': EARLY_WORLDS, 'weight': WEIGHT, 'slip': SLIP,
              'unhedged_up_to': UNHEDGED_UP_TO, 'replications': {}}
    for number, seed in REPLICATIONS:
        path = DEST / f'decisions-{number}.jsonl'
        if path.exists():
            raise RuntimeError(f'{path} exists')
        with path.open('w', encoding='utf-8') as journal:
            block = replication(harness, simulator, number, seed, journal)
        block['decisions_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        result['replications'][number] = block
        g = block['gates']
        print('replication {}: C-learned {} C-growth {}'.format(
            number, g['learned_passed'], g['growth_passed']), flush=True)
    blocks = result['replications'].values()
    result['learned_passed'] = all(b['gates']['learned_passed'] for b in blocks)
    result['growth_passed'] = all(b['gates']['growth_passed'] for b in blocks)
    result['cost'] = {'wall_seconds': time.perf_counter() - wall,
                      'cpu_seconds_parent': time.process_time() - cpu,
                      'peak_rss_mb_parent': process.memory_info().rss / 1e6}
    write_json(OUT, result)
    for number, block in result['replications'].items():
        print(f'\n== replication {number} (seed {block["seed"]}), groups {block["group_counts"]}:'
              ' learned agent minus champion')
        for split in SPLITS:
            e = block['contrasts'][split]
            print('  {:12s}'.format(split) + ''.join(
                '{:+5.0f} [{:.0f},{:.0f}]'.format(s, lo, hi).rjust(17)
                for s, lo, hi in zip(e['sum'], e['low'], e['high'])))
        g = block['growth']
        print('  growth, 1600 minus 400 worlds, pooled: {:+.0f} [{:.0f}, {:.0f}]'.format(
            g['sum'], g['low'], g['high']))
    print('\nC-learned:', 'passed' if result['learned_passed'] else 'failed',
          '| C-growth:', 'passed' if result['growth_passed'] else 'failed')
    print('cost: {:.0f}s wall'.format(result['cost']['wall_seconds']))


if __name__ == '__main__':
    sys.exit(main())
