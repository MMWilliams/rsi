"""C-growth with level 2 charged: groups learned from atom sets the agent earned.

C-growth (`EXPERIMENT-mechanism-learned-confirmation.md`) learned its grouping
from each training world's true atom set, handed over. Here each training world
is instead *lived* by the blind earned loop (no cross-world knowledge, keeps the
atoms of whatever it submitted) for a stream of tasks at a scan budget, and the
grouping is learned from the atoms it submitted, right or wrong. Nothing about
a training world reaches the representation learner except through the agent's
own picks.

Arms, each living the same held-out worlds at six budgets with C-family's
configuration: the champion; groups from 1,600 handed worlds (the C-growth arm,
an upper reference); groups from 400 and 1,600 worlds earned at the deployment
budget; groups from 1,600 worlds earned at 4096 and applied at every budget;
and the earned-1,600 grouping with labels permuted across atoms. The pair prior
is the champion's, fitted on 400 handed worlds, in every arm, so the grouping is
the only difference. Earning cost is reported in scans. Development evidence,
fresh seed.
"""
from __future__ import annotations

import json
import multiprocessing
import random
import sys
import time
import warnings

import numpy as np
import psutil
from sklearn.metrics import adjusted_rand_score

from rsi.common import ROOT, write_json
from rsi.growth_coach import (BLIND, CHAMPION, UNHEDGED, Prior, Simulator, draw_worlds,
                              triples, world_seed)
from rsi.learned_groups import LearnedFamilySimulator, learn_groups
from rsi.mechanism_worlds import Harness

OUT = ROOT / 'analysis/mechanism-earned-groups-probe-20261004.json'
CACHE = ROOT / 'analysis/mechanism-earned-groups-earned-20261004.json'
SEED = 641101
EVAL_WORLDS = 32
TRAINING_WORLDS = 1600
EARLY_WORLDS = 400
PRIOR_WORLDS = 400
PRIOR_SOLVED = 64
EARN_STREAM = 100
STREAM = 100
KEYS_PER_WORLD = 14
MINIMUM_MEMBERS = 130
HELD_OUT_FAMILIES = ('popcount', 'xormod')
BUDGETS = (128, 256, 512, 1024, 2048, 4096)
GROUP_CHOICES = range(3, 13)
WEIGHT, SLIP = 2., .2
SPLITS = ('seen_triple', 'new_triple', 'new_family')
WORKERS = 6
BOOT = 20000
_STATE = {}


def coach_for(budget):
    return UNHEDGED if budget <= 256 else CHAMPION


def _init_earn(seed):
    harness = Harness()
    harness.set_tiebreak(seed + 77)
    _STATE.update(simulator=Simulator(harness), seed=seed)


def _earn(job):
    """Atom keys the blind loop submitted while living one training world, per
    budget, with how many of its picks were correct."""
    index, stream = job
    simulator = _STATE['simulator']
    views = simulator.views(stream, random.Random(world_seed(_STATE['seed'] + 5, index)))
    out = []
    for budget in BUDGETS:
        trace = []
        simulator.lifetime(BLIND, views, None, budget, trace=trace)
        keys = sorted({int(k) for d in trace if d['pick'] >= 0
                       for k in simulator.row_keys[d['pick']]})
        out.append((keys, int(sum(d['hit'] for d in trace))))
    return out


def _init_live(seed, prior, views, labels):
    harness = Harness()
    harness.set_tiebreak(seed + 77)
    agents = {'champion': Simulator(harness)}
    for name, by_budget in labels.items():
        agents[name] = {b: (LearnedFamilySimulator(harness, lab, WEIGHT, SLIP)
                            if lab is not None else None) for b, lab in by_budget.items()}
    _STATE.update(prior=prior, views=views, agents=agents)


def _live(key):
    s = _STATE
    out = {}
    for arm, agent in s['agents'].items():
        row = []
        for budget in BUDGETS:
            if arm == 'champion':
                hits = agent.lifetime(CHAMPION, s['views'][key], s['prior'], budget)
            else:
                chosen = agent[budget] or s['agents']['champion']
                coach = coach_for(budget) if agent[budget] else CHAMPION
                hits = chosen.lifetime(coach, s['views'][key], s['prior'], budget)
            row.append(int(hits.sum()))
        out[arm] = row
    return out


def paired(agent, base, seed):
    difference = np.asarray(agent) - np.asarray(base)
    draws = np.random.default_rng(seed).integers(0, len(difference), (BOOT, len(difference)))
    sums = difference[draws].sum(axis=1)
    return {'sum': difference.sum(axis=0).tolist(),
            'low': np.percentile(sums, 2.5, axis=0).tolist(),
            'high': np.percentile(sums, 97.5, axis=0).tolist()}


def grouping(observed, keys):
    """Learned labels, or None when the earned sets are too sparse to cluster."""
    seen = len({k for s in observed for k in s})
    choices = [g for g in GROUP_CHOICES if g < seen]
    if len(choices) == 0:
        return None, 0
    try:
        return learn_groups(observed, keys, choices=choices, select='likelihood')
    except ValueError:
        return None, 0


def main():
    if OUT.exists():
        raise RuntimeError('analysis exists')
    warnings.filterwarnings('ignore', message='Graph is not fully connected')
    process = psutil.Process()
    wall, cpu = time.perf_counter(), time.process_time()
    harness = Harness()
    harness.set_tiebreak(SEED + 77)
    simulator = Simulator(harness)
    rng = random.Random(SEED)
    seen = [f for f in harness.by_family if f not in HELD_OUT_FAMILIES]
    seen_pool = triples(harness, seen, rng, KEYS_PER_WORLD, MINIMUM_MEMBERS)
    rng.shuffle(seen_pool)
    cut = max(1, round(.2 * len(seen_pool)))
    new_triples, train_triples = seen_pool[:cut], seen_pool[cut:]
    held_pool = [t for t in triples(harness, harness.by_family, rng, KEYS_PER_WORLD,
                                    MINIMUM_MEMBERS) if set(t) & set(HELD_OUT_FAMILIES)]
    groups = {name: draw_worlds(harness, pool_, EVAL_WORLDS, rng, KEYS_PER_WORLD,
                                MINIMUM_MEMBERS, STREAM)
              for name, pool_ in (('seen_triple', train_triples), ('new_triple', new_triples),
                                  ('new_family', held_pool))}
    reserved = {i for worlds in groups.values() for w in worlds for i in w['stream']}
    training = draw_worlds(harness, train_triples, TRAINING_WORLDS, rng, KEYS_PER_WORLD,
                           MINIMUM_MEMBERS, 0)
    keys = len(harness.key_names)
    handed, earn_streams = [], []
    for world in training:
        allowed = [i for i in world['members'] if i not in reserved]
        rng.shuffle(allowed)
        chosen = sorted(allowed[:PRIOR_SOLVED])
        handed.append(sorted({harness.key_index[k] for k in harness.observed_keys(chosen)}))
        earn_streams.append(allowed[:EARN_STREAM])
    prior = Prior(harness, handed[:PRIOR_WORLDS])

    # Earning is most of the cost and depends only on the seed, so it is cached
    # and a rerun after an interrupted evaluation starts from it.
    if CACHE.exists():
        cached = json.loads(CACHE.read_text())
        assert cached['streams'] == earn_streams
        earned = [[(keys, hits) for keys, hits in world] for world in cached['earned']]
    else:
        with multiprocessing.get_context('spawn').Pool(WORKERS, initializer=_init_earn,
                                                       initargs=(SEED,)) as pool:
            earned = pool.map(_earn, list(enumerate(earn_streams)), chunksize=8)
        write_json(CACHE, {'seed': SEED, 'streams': earn_streams, 'earned': earned})
    print('earning done {:.0f}s'.format(time.perf_counter() - wall), flush=True)

    family_of = np.array([sorted(harness.by_family).index(k.split(':')[0])
                          for k in harness.key_names])
    true_sets = [{harness.key_index[k] for k in w['keys']} for w in training]
    quality = {}
    earned_sets = {}
    for b_index, budget in enumerate(BUDGETS):
        sets = [earned[w][b_index][0] for w in range(TRAINING_WORLDS)]
        earned_sets[budget] = sets
        sizes = [len(s) for s in sets]
        precision = [len(set(s) & true_sets[w]) / len(s) for w, s in enumerate(sets) if s]
        quality[str(budget)] = {
            'mean_atoms': float(np.mean(sizes)), 'empty_share': float(np.mean([z == 0 for z in sizes])),
            'precision': float(np.mean(precision)) if precision else None,
            'solved_per_world': float(np.mean([earned[w][b_index][1] for w in range(TRAINING_WORLDS)])),
            'scans_charged': budget * EARN_STREAM * TRAINING_WORLDS}

    labels = {'handed': {}, 'early': {}, 'earned': {}, 'earned_4096': {}, 'permuted': {}}
    counts = {name: {} for name in labels}
    ari = {name: {} for name in labels}
    handed_labels, handed_count = learn_groups(handed, keys, choices=GROUP_CHOICES,
                                               select='likelihood')
    fixed, fixed_count = grouping(earned_sets[4096], keys)
    perm_rng = np.random.default_rng(SEED + 9)
    for budget in BUDGETS:
        early, early_count = grouping(earned_sets[budget][:EARLY_WORLDS], keys)
        full, full_count = grouping(earned_sets[budget], keys)
        permuted = None if full is None else full[perm_rng.permutation(keys)]
        for name, lab, count in (('handed', handed_labels, handed_count),
                                 ('early', early, early_count), ('earned', full, full_count),
                                 ('earned_4096', fixed, fixed_count),
                                 ('permuted', permuted, full_count)):
            labels[name][budget] = lab
            counts[name][str(budget)] = int(count)
            if lab is not None:
                mask = lab >= 0
                ari[name][str(budget)] = float(adjusted_rand_score(family_of[mask], lab[mask]))
    print('groups learned', counts, flush=True)

    views = {f'{split}:{n:03d}': simulator.views(w['stream'], rng)
             for split, worlds in groups.items() for n, w in enumerate(worlds)}
    order = list(views)
    with multiprocessing.get_context('spawn').Pool(
            WORKERS, initializer=_init_live, initargs=(SEED, prior, views, labels)) as pool:
        lives = dict(zip(order, pool.map(_live, order, chunksize=1)))

    arms = ['champion'] + list(labels)
    totals = {split: {arm: np.array([lives[k][arm] for k in order if k.startswith(split + ':')])
                      for arm in arms} for split in SPLITS}
    contrasts = {split: {arm: paired(totals[split][arm], totals[split]['champion'], SEED + 3)
                         for arm in arms[1:]} for split in SPLITS}
    versus = {split: {pair: paired(totals[split][a], totals[split][b], SEED + 4)
                      for pair, (a, b) in (('earned-early', ('earned', 'early')),
                                           ('earned-permuted', ('earned', 'permuted')),
                                           ('handed-earned', ('handed', 'earned')))}
              for split in SPLITS}
    pooled = {}
    for pair, (a, b) in (('earned-early', ('earned', 'early')),
                         ('earned_4096-early', ('earned_4096', 'early'))):
        boot_rng = np.random.default_rng(SEED + 5)
        sums, total = np.zeros(BOOT), 0.
        for split in SPLITS:
            per_world = (totals[split][a] - totals[split][b]).sum(axis=1)
            total += per_world.sum()
            sums += per_world[boot_rng.integers(0, len(per_world), (BOOT, len(per_world)))].sum(axis=1)
        pooled[pair] = {'sum': float(total), 'low': float(np.percentile(sums, 2.5)),
                        'high': float(np.percentile(sums, 97.5))}

    result = {'scope': 'development, fresh seed', 'seed': SEED, 'budgets': list(BUDGETS),
              'eval_worlds': EVAL_WORLDS, 'training_worlds': TRAINING_WORLDS,
              'earn_stream': EARN_STREAM, 'earning_agent': 'blind earned loop, no prior',
              'earned_quality': quality, 'group_counts': counts, 'ari_vs_families': ari,
              'mean_by_budget': {s: {a: v.mean(axis=0).tolist() for a, v in arms_.items()}
                                 for s, arms_ in totals.items()},
              'contrasts_vs_champion': contrasts, 'contrasts': versus, 'pooled_growth': pooled,
              'cost': {'wall_seconds': time.perf_counter() - wall,
                       'cpu_seconds_parent': time.process_time() - cpu,
                       'peak_rss_mb_parent': process.memory_info().rss / 1e6}}
    write_json(OUT, result)

    print('\nearned sets per budget:')
    for b, q in quality.items():
        print('  {:>5}: {:.1f} atoms, precision {}, empty {:.2f}, solved {:.1f}/{}'.format(
            b, q['mean_atoms'], None if q['precision'] is None else round(q['precision'], 3),
            q['empty_share'], q['solved_per_world'], EARN_STREAM))
    print('ARI', ari)
    for split in SPLITS:
        print(f'\n{split}: minus champion, tasks of {EVAL_WORLDS * STREAM}')
        for arm in arms[1:]:
            e = contrasts[split][arm]
            print('  {:12s}'.format(arm) + ''.join(
                '{:+5.0f} [{:.0f},{:.0f}]'.format(s, lo, hi).rjust(17)
                for s, lo, hi in zip(e['sum'], e['low'], e['high'])))
        for pair, e in versus[split].items():
            print('  {:16s}'.format(pair) + ''.join(
                '{:+5.0f} [{:.0f},{:.0f}]'.format(s, lo, hi).rjust(17)
                for s, lo, hi in zip(e['sum'], e['low'], e['high'])))
    print('\npooled growth:', pooled)
    print('cost {:.0f}s wall'.format(result['cost']['wall_seconds']))


if __name__ == '__main__':
    sys.exit(main())
