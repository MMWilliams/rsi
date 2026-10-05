"""Self model by self-simulation, inside the agent's own world model.

From earned sets alone the agent cannot tell "I rarely find atom k" from "atom k
is rarely in worlds" (`mechanism-self-world-accuracy-20261005.json`: discovery
rate Pearson 0.54-0.71 raw, 0.08-0.27 on filtered sets). So the agent measures
itself instead: it imagines worlds from its fitted world model, builds their
tasks from the catalog with the task generator, lives them with its own earning
policy (the blind loop at 4096), and counts how often each atom present was
earned. Those rates are fixed into the model, which is refitted with per-atom
prevalence, now identifiable; then the loop repeats. Nothing here reads a true
world, family or label; ground truth is used only to score the result.

Scored on the three opened development seeds against the same truth as the
first pass: discovery rate per atom, groups against families, and P(atom in a
held-out world | earned set).
"""
from __future__ import annotations

import json
import multiprocessing
import random
import sys
import warnings

import numpy as np
from sklearn.metrics import adjusted_rand_score

from rsi.common import ROOT, write_json
from rsi.growth_coach import BLIND, Simulator, world_seed
from rsi.mechanism_space import world_members
from rsi.mechanism_worlds import Harness
from rsi.self_world_model import _matrix, fit, select
import mechanism_earned_confirmation as conf
from mechanism_earned_trust_screen import earning_of
from mechanism_self_world_accuracy import scores

SEEDS = (643101, 644101, 645101)
TRAIN = 1280
IMAGINED = 800
ROUNDS = 2
OUT = ROOT / 'analysis/mechanism-self-simulation-20261005.json'
_STATE = {}


def imagine(harness, model, seed, rng):
    """Imagined worlds' streams, from the world model's own generative story."""
    worlds, streams = [], []
    while len(worlds) < IMAGINED:
        for keys in model.sample_worlds(IMAGINED - len(worlds), rng):
            names = sorted(harness.key_names[k] for k in keys)
            members = world_members(harness.catalog, harness.by_key, names)
            if len(members) < conf.MINIMUM_MEMBERS:
                continue
            members = list(members)
            rng.shuffle(members)
            worlds.append(keys)
            streams.append(members[:conf.EARN_STREAM])
    return worlds, streams


def _init_self(agent_seed, imagination_seed):
    """The agent as it is, tie-break included: its scan order among hypotheses
    it scores equally is part of what it will and will not find."""
    harness = Harness()
    harness.set_tiebreak(agent_seed + 77)
    _STATE.update(simulator=Simulator(harness), seed=imagination_seed)


def _earn_self(job):
    index, stream = job
    simulator = _STATE['simulator']
    views = simulator.views(stream, random.Random(world_seed(_STATE['seed'] + 5, index)))
    trace = []
    simulator.lifetime(BLIND, views, None, conf.EARN_BUDGET, trace=trace)
    return [(int(d['pick']), int(d['hit'])) for d in trace]


def simulate(harness, simulator, model, seed, round_):
    rng = np.random.default_rng(seed * 10 + round_)
    worlds, streams = imagine(harness, model, seed, rng)
    with multiprocessing.get_context('spawn').Pool(conf.WORKERS, initializer=_init_self,
                                                   initargs=(seed, seed * 10 + round_)) as pool:
        earning = pool.map(_earn_self, list(enumerate(streams)), chunksize=8)
    keys = len(harness.key_names)
    present, found = np.zeros(keys), np.zeros(keys)
    for world, decisions in zip(worlds, earning):
        earned = set(conf.earned_set(decisions, simulator.row_keys, 1))
        for k in world:
            present[k] += 1
            found[k] += k in earned
    r = np.where(present >= 3, found / np.maximum(present, 1), model.r)
    return r, present


def evaluate(model, earned, truth, true_r, family_of):
    held_e, held_t = earned[TRAIN:], truth[TRAIN:]
    ok = ~np.isnan(true_r) & model.seen
    grouped = model.labels >= 0
    return {'ari': float(adjusted_rand_score(family_of[grouped], model.labels[grouped])),
            'atoms_grouped': int(grouped.sum()),
            'membership': scores(model.membership(held_e), held_t),
            'r_pearson': float(np.corrcoef(model.r[ok], true_r[ok])[0, 1]),
            'r_mae': float(np.abs(model.r[ok] - true_r[ok]).mean())}


def main():
    if OUT.exists():
        raise RuntimeError('analysis exists')
    warnings.filterwarnings('ignore', message='Graph is not fully connected')
    harness = Harness()
    simulator = Simulator(harness)
    keys = len(harness.key_names)
    families = sorted(harness.by_family)
    family_of = np.array([families.index(k.split(':')[0]) for k in harness.key_names])
    result = {}
    for seed in SEEDS:
        _rng, _g, training, _s, streams, _h, _p, _n = conf.setup(harness, seed)
        if seed == 645101:
            cache = ROOT / 'runs/mechanism-earned-confirmation2-dev-645101/earning-dev.json'
            earning = json.loads(cache.read_text())['earning']
        else:
            earning = earning_of(seed, streams)
        sets = [conf.earned_set(d, simulator.row_keys, 1) for d in earning]
        earned = _matrix(sets, keys)
        truth = _matrix([[harness.key_index[k] for k in w['keys']] for w in training], keys)
        has = truth[:TRAIN].sum(0)
        true_r = np.where(has > 0, (earned[:TRAIN] * truth[:TRAIN]).sum(0) / np.maximum(has, 1),
                          np.nan)
        model, count, _scores, _trace = select(sets[:TRAIN], keys)
        rounds = [{'round': 0, **evaluate(model, earned, truth, true_r, family_of)}]
        print(seed, rounds[-1], flush=True)
        for round_ in range(1, ROUNDS + 1):
            r, present = simulate(harness, simulator, model, seed, round_)
            model, _trace = fit(sets[:TRAIN], keys, model.groups, fixed_r=r, init=model)
            rounds.append({'round': round_, 'atoms_simulated': int((present >= 3).sum()),
                           **evaluate(model, earned, truth, true_r, family_of)})
            print(seed, rounds[-1], flush=True)
        result[str(seed)] = {'groups': int(count), 'rounds': rounds}
    write_json(OUT, result)


if __name__ == '__main__':
    sys.exit(main())
