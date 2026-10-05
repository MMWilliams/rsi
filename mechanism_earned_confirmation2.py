"""Confirmatory run: EXPERIMENT-mechanism-earned-confirmation-2.md.

C-growth with level 2 charged. Each replication draws 1,600 training worlds and
lets the blind earned loop (no cross-world knowledge, keeps the atoms of
whatever it submitted) live each for a stream of 100 tasks at budget 4096. Atom
groups are learned from the atoms it submitted, right or wrong, across the first
400 (`early`) and all 1,600 (`earned`) training worlds; nothing about a training
world reaches the representation learner except through the agent's own picks.
The family agent on each grouping then lives the held-out worlds at every budget
next to the champion, a permuted copy of the earned grouping, and the C-growth
grouping learned from handed true sets (an upper reference). Earning scans are
charged and reported.

`--dev SEED` runs one development replication to a separate file; it is how the
runner was rehearsed and is never a confirmation.
"""
from __future__ import annotations

import hashlib
import json
import multiprocessing
import random
import sys
import time
import warnings
from collections import Counter
from pathlib import Path

import numpy as np
import psutil

from rsi.common import ROOT, write_json
from rsi.growth_coach import (BLIND, CHAMPION, UNHEDGED, Prior, Simulator, draw_worlds,
                              triples, world_seed)
from rsi.learned_groups import LearnedFamilySimulator, learn_groups
from rsi.mechanism_worlds import Harness

SCRIPT = Path(__file__)
OUT = ROOT / 'analysis/mechanism-earned-confirmation2-20261005.json'
DEST = ROOT / 'runs/mechanism-earned-confirmation2-20261005'
REPLICATIONS = (('A', 1001101), ('B', 1002101))

TRAINING_WORLDS = 1600
PRIOR_WORLDS = 400
EARLY_WORLDS = 400
MID_WORLDS = 800
PRIOR_SOLVED = 64
EARN_STREAM = 100
EARN_BUDGET = 4096
MINIMUM_PICKS = 3
MINIMUM_WORLDS = 50
STREAM = 100
KEYS_PER_WORLD = 14
MINIMUM_MEMBERS = 130
HELD_OUT_FAMILIES = ('popcount', 'xormod')
NEW_TRIPLE_SHARE = .2
BUDGETS = (128, 256, 512, 1024, 2048, 4096)
GROUP_CHOICES = range(3, 13)
WEIGHT, SLIP = .5, .2
UNHEDGED_UP_TO = 128

EVAL_WORLDS = 128
SPLITS = ('seen_triple', 'new_triple', 'new_family')
IMPROVE_SPLITS = ('seen_triple', 'new_triple')
SAFE_SPLITS = ('new_family',)
GROUPED = ('earned', 'mid', 'early', 'permuted', 'handed')
ARMS = ('champion',) + GROUPED
BOOT = 20000
WORKERS = 12
_STATE = {}


def agent_coach(budget):
    return UNHEDGED if budget <= UNHEDGED_UP_TO else CHAMPION


def paired(agent, base, seed):
    difference = np.asarray(agent) - np.asarray(base)
    draws = np.random.default_rng(seed).integers(0, len(difference), (BOOT, len(difference)))
    sums = difference[draws].sum(axis=1)
    return {'sum': difference.sum(axis=0).tolist(),
            'low': np.percentile(sums, 2.5, axis=0).tolist(),
            'high': np.percentile(sums, 97.5, axis=0).tolist()}


def pooled(totals, a, b, seed):
    """a minus b summed over every split and budget; worlds are resampled within
    each split and the splits' sums added."""
    rng = np.random.default_rng(seed)
    sums, total = np.zeros(BOOT), 0.
    for split in SPLITS:
        per_world = (np.asarray(totals[split][a]) - np.asarray(totals[split][b])).sum(axis=1)
        total += per_world.sum()
        sums += per_world[rng.integers(0, len(per_world), (BOOT, len(per_world)))].sum(axis=1)
    return {'sum': float(total), 'low': float(np.percentile(sums, 2.5)),
            'high': float(np.percentile(sums, 97.5))}


def gates(contrasts, grown, structure):
    """Growth and structure on pooled differences; safety in every one of the
    18 cells. `improve` (every cell above the champion) is reported, not gated:
    the handed true-set reference fails it at 256-512 in development."""
    improve = {split: {str(b): contrasts[split]['low'][i] > 0 for i, b in enumerate(BUDGETS)}
               for split in SPLITS}
    safe = {split: {str(b): contrasts[split]['high'][i] >= 0 for i, b in enumerate(BUDGETS)}
            for split in SPLITS}
    passed = {'growth_passed': grown['low'] > 0, 'structure_passed': structure['low'] > 0,
              'safe_passed': all(all(v.values()) for v in safe.values())}
    return {'improve': improve, 'safe': safe, **passed,
            'earned_passed': all(passed.values())}


def _init_earn(seed):
    harness = Harness()
    harness.set_tiebreak(seed + 77)
    _STATE.update(simulator=Simulator(harness), seed=seed)


def _earn(job):
    """Decisions of the blind loop living one training world at EARN_BUDGET."""
    index, stream = job
    simulator = _STATE['simulator']
    views = simulator.views(stream, random.Random(world_seed(_STATE['seed'] + 5, index)))
    trace = []
    simulator.lifetime(BLIND, views, None, EARN_BUDGET, trace=trace)
    return [(int(d['pick']), int(d['hit'])) for d in trace]


def _init_live(seed, prior, views, labels):
    harness = Harness()
    harness.set_tiebreak(seed + 77)
    agents = {'champion': Simulator(harness)}
    agents.update({name: (agents['champion'] if labels[name] is None else
                          LearnedFamilySimulator(harness, labels[name], WEIGHT, SLIP))
                   for name in GROUPED})
    _STATE.update(ungrouped={name for name in GROUPED if labels[name] is None})
    _STATE.update(prior=prior, views=views, agents=agents)


def _live(key):
    s = _STATE
    out = {}
    for arm, agent in s['agents'].items():
        per_budget = []
        for budget in BUDGETS:
            trace = []
            plain = arm == 'champion' or arm in s['ungrouped']
            agent.lifetime(CHAMPION if plain else agent_coach(budget),
                           s['views'][key], s['prior'], budget, trace=trace)
            per_budget.append([(int(d['pick']), int(d['hit'])) for d in trace])
        out[arm] = per_budget
    return out


def earned_set(decisions, row_keys, minimum):
    """Atoms that appear in at least `minimum` of the world's submitted picks:
    an atom of the world recurs across its mechanisms, an atom imported by a
    wrong pick rarely does. Uses nothing but the agent's own picks."""
    counts = Counter(int(k) for pick, _hit in decisions if pick >= 0 for k in row_keys[pick])
    return sorted(k for k, n in counts.items() if n >= minimum)


def confident(sets):
    """Sets restricted to atoms earned in at least MINIMUM_WORLDS worlds; the
    rest join the unseen group, which the agent treats neutrally, rather than
    being clustered on too little evidence."""
    worlds_with = Counter(k for s in sets for k in s)
    return [[k for k in s if worlds_with[k] >= MINIMUM_WORLDS] for s in sets]


def journal_cache(journal, number):
    return Path(journal.name).with_name(f'earning-{number}.json')


def grouping(sets, keys):
    """Learned labels and count, or (None, 0) when too few atoms clear the
    evidence bar to cluster: that agent has no grouping and plays the champion."""
    fit = len({k for s in sets[:len(sets) * 4 // 5] for k in s})
    choices = [g for g in GROUP_CHOICES if g < fit]
    if not choices:
        return None, 0
    return learn_groups(sets, keys, choices=choices, select='likelihood')


def setup(harness, seed):
    """Everything a replication draws before earning, in its stream order."""
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
    solved, earn_streams = [], []
    for world in training:
        allowed = [index for index in world['members'] if index not in reserved]
        rng.shuffle(allowed)
        solved.append(sorted(allowed[:PRIOR_SOLVED]))
        earn_streams.append(allowed[:EARN_STREAM])
    handed = [sorted({harness.key_index[key] for key in harness.observed_keys(chosen)})
              for chosen in solved]
    prior = Prior(harness, handed[:PRIOR_WORLDS])
    return (rng, groups, training, solved, earn_streams, handed, prior, new_triples)


def replication(harness, simulator, number, seed, journal):
    rng, groups, training, solved, earn_streams, handed, prior, new_triples = \
        setup(harness, seed)
    start = time.perf_counter()
    # Earning is deterministic in the seed and most of the cost, so a rerun after
    # a failure downstream of it starts from the saved decisions.
    cache = journal_cache(journal, number)
    if cache.exists():
        saved = json.loads(cache.read_text())
        assert saved['streams'] == earn_streams
        earning = saved['earning']
    else:
        with multiprocessing.get_context('spawn').Pool(WORKERS, initializer=_init_earn,
                                                       initargs=(seed,)) as pool:
            earning = pool.map(_earn, list(enumerate(earn_streams)), chunksize=8)
        write_json(cache, {'seed': seed, 'streams': earn_streams, 'earning': earning})
    earned = [earned_set(decisions, simulator.row_keys, MINIMUM_PICKS) for decisions in earning]
    true_sets = [{harness.key_index[key] for key in world['keys']} for world in training]
    precision = [len(set(s) & true_sets[w]) / len(s) for w, s in enumerate(earned) if s]
    earn_report = {'seconds': time.perf_counter() - start,
                   'scans_charged': EARN_BUDGET * EARN_STREAM * TRAINING_WORLDS,
                   'mean_atoms': float(np.mean([len(s) for s in earned])),
                   'precision': float(np.mean(precision)),
                   'solved_per_world': float(np.mean([sum(h for _p, h in d) for d in earning]))}

    keys = len(harness.key_names)
    labels, counts = {}, {}
    for name, sets in (('earned', confident(earned)), ('mid', confident(earned[:MID_WORLDS])),
                       ('early', confident(earned[:EARLY_WORLDS])), ('handed', handed)):
        labels[name], counts[name] = grouping(sets, keys)
    labels['permuted'] = None if labels['earned'] is None else \
        labels['earned'][np.random.default_rng(seed + 9).permutation(keys)]
    counts['permuted'] = counts['earned']
    views = {f'{split}:{n:03d}': simulator.views(world['stream'], rng, examples=True)
             for split, worlds in groups.items() for n, world in enumerate(worlds)}
    names = {split: [key for key in views if key.startswith(split + ':')] for split in groups}
    print('replication {} setup done, earning {:.0f}s, groups {}'.format(
        number, earn_report['seconds'], counts), flush=True)

    order = [key for split in SPLITS for key in names[split]]
    with multiprocessing.get_context('spawn').Pool(
            WORKERS, initializer=_init_live, initargs=(seed, prior, views, labels)) as pool:
        lives = dict(zip(order, pool.map(_live, order, chunksize=1)))

    for w, decisions in enumerate(earning):
        journal.write(json.dumps({'kind': 'earn', 'replication': number, 'world': w,
                                  'stream': earn_streams[w], 'decisions': decisions}) + '\n')
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
    contrasts = {arm: {split: paired(totals[split][arm], totals[split]['champion'], seed + 3)
                       for split in SPLITS} for arm in GROUPED}
    grown = pooled(totals, 'earned', 'early', seed + 4)
    structure = pooled(totals, 'earned', 'permuted', seed + 5)
    reference = pooled(totals, 'handed', 'earned', seed + 6)
    steps = {'mid_minus_early': pooled(totals, 'mid', 'early', seed + 7),
             'earned_minus_mid': pooled(totals, 'earned', 'mid', seed + 8)}
    gain = pooled(totals, 'earned', 'champion', seed + 10)['sum']
    ceiling = pooled(totals, 'handed', 'champion', seed + 10)['sum']
    return {'seed': seed, 'new_triples': [list(t) for t in new_triples],
            'earning': earn_report, 'group_counts': counts,
            'labels': {k: None if v is None else v.tolist() for k, v in labels.items()},
            'worlds': {split: [{'key': key, 'keys': list(world['keys']),
                                'triple': list(world['triple']), 'stream': world['stream']}
                               for key, world in zip(names[split], worlds)]
                       for split, worlds in groups.items()},
            'training_solved': solved, 'training_keys': [list(w['keys']) for w in training],
            'earned_sets': earned,
            'totals': {s: {a: v.tolist() for a, v in arms.items()} for s, arms in totals.items()},
            'mean_by_budget': {s: {a: v.mean(axis=0).tolist() for a, v in arms.items()}
                               for s, arms in totals.items()},
            'contrasts': contrasts, 'growth': grown, 'structure': structure,
            'handed_minus_earned': reference, 'growth_steps': steps,
            'share_of_handed_gain': gain / ceiling if ceiling > 0 else None,
            'gates': gates(contrasts['earned'], grown, structure)}


def main():
    warnings.filterwarnings('ignore', message='Graph is not fully connected')
    dev = sys.argv[1:2] == ['--dev']
    out, dest, reps = OUT, DEST, REPLICATIONS
    if dev:
        seed = int(sys.argv[2])
        out = ROOT / f'analysis/mechanism-earned-confirmation2-dev-{seed}.json'
        dest = ROOT / f'runs/mechanism-earned-confirmation2-dev-{seed}'
        reps = (('dev', seed),)
    if out.exists():
        raise RuntimeError('analysis exists')
    dest.mkdir(parents=True, exist_ok=True)
    process = psutil.Process()
    wall, cpu = time.perf_counter(), time.process_time()
    harness = Harness()
    simulator = Simulator(harness)
    result = {'scope': ('development rehearsal' if dev else
                        'confirmatory run, EXPERIMENT-mechanism-earned-confirmation-2.md'),
              'runner_sha256': hashlib.sha256(SCRIPT.read_bytes()).hexdigest(),
              'catalog': {'rows': harness.catalog.size, 'digest': harness.catalog.digest()},
              'budgets': list(BUDGETS), 'splits': list(SPLITS), 'eval_worlds': EVAL_WORLDS,
              'training_worlds': TRAINING_WORLDS, 'prior_worlds': PRIOR_WORLDS,
              'early_worlds': EARLY_WORLDS, 'mid_worlds': MID_WORLDS,
              'minimum_picks': MINIMUM_PICKS, 'minimum_worlds': MINIMUM_WORLDS,
              'earn_budget': EARN_BUDGET,
              'earn_stream': EARN_STREAM, 'weight': WEIGHT, 'slip': SLIP,
              'unhedged_up_to': UNHEDGED_UP_TO, 'replications': {}}
    for number, seed in reps:
        path = dest / f'decisions-{number}.jsonl'
        if path.exists():
            raise RuntimeError(f'{path} exists')
        with path.open('w', encoding='utf-8') as journal:
            block = replication(harness, simulator, number, seed, journal)
        block['decisions_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        result['replications'][number] = block
        g = block['gates']
        print('replication {}: C-earned {} (growth {} structure {} safe {})'.format(
            number, g['earned_passed'], g['growth_passed'], g['structure_passed'],
            g['safe_passed']), flush=True)
    blocks = result['replications'].values()
    for gate in ('earned_passed', 'growth_passed', 'structure_passed', 'safe_passed'):
        result[gate] = all(b['gates'][gate] for b in blocks)
    result['cost'] = {'wall_seconds': time.perf_counter() - wall,
                      'cpu_seconds_parent': time.process_time() - cpu,
                      'peak_rss_mb_parent': process.memory_info().rss / 1e6}
    write_json(out, result)
    for number, block in result['replications'].items():
        print(f'\n== replication {number} (seed {block["seed"]}), groups {block["group_counts"]},'
              f' earning {block["earning"]}')
        for arm in GROUPED:
            print(f'  {arm} minus champion')
            for split in SPLITS:
                e = block['contrasts'][arm][split]
                print('    {:12s}'.format(split) + ''.join(
                    '{:+5.0f} [{:.0f},{:.0f}]'.format(s, lo, hi).rjust(17)
                    for s, lo, hi in zip(e['sum'], e['low'], e['high'])))
        for name, g in (('growth', block['growth']), ('structure', block['structure']),
                        ('handed_minus_earned', block['handed_minus_earned']),
                        *block['growth_steps'].items()):
            print('  {}: {:+.0f} [{:.0f}, {:.0f}]'.format(name, g['sum'], g['low'], g['high']))
        print('  share of handed gain:', block['share_of_handed_gain'])
    print('\nC-earned:', result['earned_passed'], '| growth:', result['growth_passed'],
          '| structure:', result['structure_passed'], '| safe:', result['safe_passed'])
    print('cost: {:.0f}s wall'.format(result['cost']['wall_seconds']))


if __name__ == '__main__':
    sys.exit(main())
