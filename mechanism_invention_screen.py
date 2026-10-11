"""Screen I1 for the hypothesis-space axis, one development seed.

The agent's language is a seed subset of the catalog: the seven families its
training worlds use. The two held-out families (popcount, xormod) are not in
it, so worlds that use one of them hold mechanisms it cannot reach by scanning.
Three questions, each a number the programme asks for before machinery is
built:

1. Headroom: what the seed language costs on worlds that need a missing family
   (full language minus seed language, tasks of 100 per world).
2. Direction: can the agent tell, without labels, which worlds need invention?
   Two signals from its own first life: the share of tasks with no consistent
   candidate in the window, and the fit of its earned set under the L1 world
   model. Scored by AUC against the truth.
3. Default: what breadth-first invention from the grammar recovers at its
   cost. The agent lives a world once in the seed language, invents from the
   tasks it could not solve, then lives a second stream of the same world in
   the extended language, against the same second life in the seed language
   (control) and in the full language (oracle extension).

Nothing the agent does reads a label; labels score the result.
"""
from __future__ import annotations

import json
import multiprocessing
import os
import random
import sys
import warnings
from types import SimpleNamespace

import numpy as np
from sklearn.metrics import roc_auc_score

from rsi.common import ROOT, write_json
from rsi.growth_coach import BLIND, Simulator, world_seed
from rsi.invention import candidates, invent
from rsi.mechanism_space import FULL, atom_expressions, make_task, vector_test
from rsi.mechanism_worlds import Harness
from rsi.self_world_model import _matrix, fit_restarts
import mechanism_earned_confirmation as conf
from mechanism_earn_traced import load

SEED = int(os.environ.get('RSI_SEED', 644101))
BUDGET = int(os.environ.get('RSI_BUDGET', 4096))
WORLDS = int(os.environ.get('RSI_WORLDS', 128))
WORKERS = int(os.environ.get('RSI_WORKERS', 8))
STREAM = conf.STREAM
OUT = ROOT / f'analysis/mechanism-invention-screen-{SEED}{os.environ.get("RSI_TAG", "")}.json'
_STATE = {}


def seed_atoms():
    return [a for a in atom_expressions() if a[1] not in conf.HELD_OUT_FAMILIES]


def views_from_masks(harness, masks, rng):
    """Task views against `harness`'s catalog for tasks whose mechanisms are
    given by their masks (the true catalog's), plus each task's constraints."""
    out, tasks = [], []
    for mask in masks:
        task = make_task(SimpleNamespace(masks=[mask]), 0, rng)
        consistent = np.flatnonzero(vector_test(harness.packed, task['visible_pos'],
                                                task['visible_neg']))
        good = vector_test(harness.packed, task['hidden_pos'], task['hidden_neg'])[consistent]
        select = np.lexsort((harness.complexity[consistent], harness.sizes[consistent]))
        out.append({'mechanism': 0, 'rows': consistent[select], 'good': good[select]})
        tasks.append((task['visible_pos'], task['visible_neg']))
    return out, tasks


def _init(tiebreak):
    _STATE.update(tiebreak=tiebreak, harness={})


def _harness(name, extra):
    key = (name, tuple(a[0] for a in extra))
    cache = _STATE['harness']
    if key not in cache:
        if name == 'full':
            atoms = None
        else:
            atoms = seed_atoms() + list(extra)
        h = Harness(atoms)
        h.set_tiebreak(_STATE['tiebreak'])
        if name == 'ext':
            cache = {k: v for k, v in cache.items() if k[0] != 'ext'}   # one extended harness at a time
            _STATE['harness'] = cache
        cache[key] = (h, Simulator(h))
    return cache[key]


def _life(job):
    """One lifetime: returns hits, the earned atom names with counts, the
    confident-pick names, and the constraints of the tasks with no consistent
    candidate in the window."""
    index, name, extra, masks, rng_seed = job
    h, sim = _harness(name, extra)
    views, tasks = views_from_masks(h, masks, random.Random(rng_seed))
    trace = []
    hits = sim.lifetime(BLIND, views, None, BUDGET, trace=trace)
    earned, confident, unsolved = {}, set(), []
    for d in trace:
        if d['pick'] >= 0:
            for k in sim.row_keys[d['pick']]:
                earned[h.key_names[k]] = earned.get(h.key_names[k], 0) + 1
                if d['window_consistent'] <= 1:
                    confident.add(h.key_names[k])
        else:
            unsolved.append(tasks[d['step']])
    return {'index': index, 'hits': int(hits.sum()), 'earned': earned,
            'confident': sorted(confident), 'unsolved': unsolved,
            'stuck': sum(1 for d in trace if d['window_consistent'] == 0)}


def run(pool, jobs):
    out = pool.map(_life, jobs, chunksize=4)
    return {r['index']: r for r in out}


def main():
    if OUT.exists():
        raise RuntimeError('analysis exists')
    warnings.filterwarnings('ignore')
    h = Harness()
    _rng, groups, _tr, _s, _e, _h, _p, _n = conf.setup(h, SEED)
    worlds = groups['seen_triple'][:WORLDS] + groups['new_family'][:WORLDS]
    label = np.array([0] * min(WORLDS, len(groups['seen_triple'])) + [1] * min(WORLDS, len(groups['new_family'])))
    streams1 = [[h.catalog.masks[m] for m in w['stream']] for w in worlds]
    streams2 = []
    for i, w in enumerate(worlds):
        rng = random.Random(world_seed(SEED + 9, i))
        members = list(w['members'])
        rng.shuffle(members)
        streams2.append([h.catalog.masks[m] for m in members[:STREAM]])
    seed_masks = {m for _k, _f, e in seed_atoms() for m in (mask_of_cached(e),)}
    known = set(seed_masks) | {FULL & ~m for m in seed_masks}
    atom_family = {}
    for key, family, expr in atom_expressions():
        m = mask_of_cached(expr)
        atom_family[m] = family
        atom_family[FULL & ~m] = family
    cands = candidates()
    print('candidates', len(cands), flush=True)
    rng1 = [world_seed(SEED + 5, i) for i in range(len(worlds))]
    rng2 = [world_seed(SEED + 6, i) for i in range(len(worlds))]
    ctx = multiprocessing.get_context('spawn')
    with ctx.Pool(WORKERS, initializer=_init, initargs=(SEED + 77,)) as pool:
        life1_seed = run(pool, [(i, 'seed', (), streams1[i], rng1[i]) for i in range(len(worlds))])
        print('life 1 seed done', flush=True)
        life1_full = run(pool, [(i, 'full', (), streams1[i], rng1[i]) for i in range(len(worlds))])
        life2_full = run(pool, [(i, 'full', (), streams2[i], rng2[i]) for i in range(len(worlds))])
        life2_seed = run(pool, [(i, 'seed', (), streams2[i], rng2[i]) for i in range(len(worlds))])
        print('full and seed lives done', flush=True)
        # invention from the first life, in the main process
        invented, tests, kept_families = {}, {}, {}
        for i in range(len(worlds)):
            r = life1_seed[i]
            earned_masks = [mask_of_cached(e) for k, _f, e in seed_atoms() if k in r['earned']]
            kept, n = invent(cands, r['unsolved'], earned_masks, known)
            invented[i] = kept
            tests[i] = n
            kept_families[i] = [atom_family.get(cands[j][3], 'novel') for j in kept]
        print('invention done; mean kept', np.mean([len(v) for v in invented.values()]).round(2),
              'mean tests', np.mean(list(tests.values())).round(0), flush=True)
        # a world with nothing invented lives its second life in the seed language
        jobs = [(i, 'ext', tuple((f'inv:{cands[j][0]}', 'inv', cands[j][2]) for j in invented[i]),
                 streams2[i], rng2[i]) for i in range(len(worlds)) if invented[i]]
        life2_ext = dict(life2_seed)
        life2_ext.update(run(pool, jobs))
        print('extended lives done', len(jobs), 'worlds', flush=True)
    # direction signals
    stuck = np.array([life1_seed[i]['stuck'] / STREAM for i in range(len(worlds))])
    sets = [sorted({int(k) for p, _h, n, _s in w if p >= 0 and n <= 1 for k in Simulator(h).row_keys[p]})
            for w in load(SEED)]
    model, _ = fit_restarts(sets[:1280], len(h.key_names), 7, restarts=4)
    earned = np.zeros((len(worlds), len(h.key_names)))
    for i in range(len(worlds)):
        for name in life1_seed[i]['confident']:
            earned[i, h.key_index[name]] = 1.
    _post, loglik = model.world_posterior(earned)
    per_atom = loglik / np.maximum(earned.sum(1), 1)
    solved1 = np.array([life1_seed[i]['hits'] for i in range(len(worlds))])
    signals = {'stuck_rate': stuck, 'neg_loglik': -loglik, 'neg_loglik_per_earned': -per_atom,
               'few_solved': -solved1.astype(float)}
    auc = {k: float(roc_auc_score(label, v)) for k, v in signals.items()}
    # flag at the threshold that keeps 10% of seen worlds flagged
    cut = np.quantile(stuck[label == 0], .9)
    flagged = stuck > cut

    def totals(life, sel):
        return int(sum(life[i]['hits'] for i in np.flatnonzero(sel)))

    def per_world(life, sel):
        return float(np.mean([life[i]['hits'] for i in np.flatnonzero(sel)]))

    result = {'seed': SEED, 'budget': BUDGET, 'worlds_per_group': int(WORLDS), 'candidates': len(cands),
              'auc': auc, 'flag_cut_stuck_rate': float(cut),
              'flagged': {'seen': int(flagged[label == 0].sum()), 'new_family': int(flagged[label == 1].sum())}}
    for name, sel in (('seen', label == 0), ('new_family', label == 1)):
        result[name] = {
            'life1_seed': per_world(life1_seed, sel), 'life1_full': per_world(life1_full, sel),
            'life2_seed': per_world(life2_seed, sel), 'life2_full': per_world(life2_full, sel),
            'life2_ext': per_world(life2_ext, sel),
            'life2_directed': float(np.mean([life2_ext[i]['hits'] if flagged[i] else life2_seed[i]['hits']
                                             for i in np.flatnonzero(sel)])),
            'kept_per_world': float(np.mean([len(invented[i]) for i in np.flatnonzero(sel)])),
            'tests_per_world': float(np.mean([tests[i] for i in np.flatnonzero(sel)])),
            'stuck_rate': float(stuck[sel].mean()),
            'kept_families': dict(zip(*np.unique([f for i in np.flatnonzero(sel) for f in kept_families[i]],
                                                 return_counts=True))) if any(kept_families[i] for i in np.flatnonzero(sel)) else {}}
        result[name]['kept_families'] = {k: int(v) for k, v in result[name]['kept_families'].items()}
    result['worlds'] = [{'label': int(label[i]), 'triple': list(worlds[i]['triple']),
                         'life1_seed': life1_seed[i]['hits'], 'life1_full': life1_full[i]['hits'],
                         'life2_seed': life2_seed[i]['hits'], 'life2_full': life2_full[i]['hits'],
                         'life2_ext': life2_ext[i]['hits'], 'stuck': life1_seed[i]['stuck'],
                         'loglik': float(loglik[i]), 'kept': [cands[j][0] for j in invented[i]],
                         'kept_families': kept_families[i], 'tests': tests[i]}
                        for i in range(len(worlds))]
    write_json(OUT, result)
    print(json.dumps({k: v for k, v in result.items() if k != 'worlds'}, indent=1))


_MASKS = {}


def mask_of_cached(expr):
    from rsi.mechanism_space import mask_of
    key = json.dumps(expr, sort_keys=True)
    if key not in _MASKS:
        _MASKS[key] = mask_of(expr)
    return _MASKS[key]


if __name__ == '__main__':
    sys.exit(main())
