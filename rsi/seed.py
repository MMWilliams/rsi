"""The seed: one agent, one carried state, three operations on itself.

State: its language (the atoms its catalog is built from), its experience
(the atom sets it earned in every world it has lived, by atom name so that the
language may grow under it), its world and self model fitted from that
experience, the pair prior it starts a world from, and a ledger of every
change it tried and whether it was kept.

Operations: `live` earns experience in an area under a scan budget; `reflect`
refits the model and the prior from everything it has earned; `extend` invents
atoms from the grammar for the worlds it could not solve. Every change is a
candidate until `prove` shows it solves more of a fixed held-out set than the
carried state does. Only proven changes are kept, and nothing kept is reset.
Nothing here reads a family label or a true world; the area's pools are named
for the ledger only.
"""
from __future__ import annotations

import json
import multiprocessing
import os
import random
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from .growth_coach import BLIND, CHAMPION, UNHEDGED, Prior, Simulator, draw_worlds, triples, world_seed
from .invention import invent
from .learned_groups import LearnedFamilySimulator
from .mechanism_space import FULL, atom_expressions, make_task, mask_of, vector_test
from .mechanism_worlds import Harness
from .self_world_model import _matrix, fit_restarts

WEIGHT, SLIP = 2., .2
UNHEDGED_UP_TO = 128
KEYS_PER_WORLD, MINIMUM_MEMBERS, STREAM = 14, 130, 100
WORKERS = int(os.environ.get('RSI_WORKERS', 8))
_STATE = {}


class MechanismArea:
    """Worlds from the true generator. The seed's language starts without the
    unfamiliar families, so their worlds hold mechanisms it cannot reach by
    scanning; a fifth of the viable known triples are kept out of its lives."""

    def __init__(self, seed, unfamiliar=('popcount', 'xormod'), untrained_share=.2):
        self.full = Harness()
        self.seed = seed
        rng = random.Random(seed)
        families = sorted(self.full.by_family)
        known = [f for f in families if f not in unfamiliar]
        pool = triples(self.full, known, rng, KEYS_PER_WORLD, MINIMUM_MEMBERS)
        rng.shuffle(pool)
        cut = max(1, round(untrained_share * len(pool)))
        everything = triples(self.full, families, rng, KEYS_PER_WORLD, MINIMUM_MEMBERS)
        self.pools = {'untrained': pool[:cut], 'trained': pool[cut:],
                      'unfamiliar': [t for t in everything if set(t) & set(unfamiliar)]}
        self.seed_language = [a for a in atom_expressions() if a[1] not in unfamiliar]

    def draw(self, pool, count, rng):
        worlds = draw_worlds(self.full, self.pools[pool], count, rng, KEYS_PER_WORLD,
                             MINIMUM_MEMBERS, STREAM)
        return [{'pool': pool, 'triple': list(w['triple']),
                 'masks': [self.full.catalog.masks[m] for m in w['stream']]} for w in worlds]

    def held_out(self, per_pool=24):
        rng = random.Random(self.seed + 4242)
        out = []
        for pool in ('trained', 'untrained', 'unfamiliar'):
            out += self.draw(pool, per_pool, rng)
        for i, w in enumerate(out):
            w['rng'] = world_seed(self.seed + 8, i)
        return out

    def life_worlds(self, life, count, unfamiliar_share=.25):
        rng = random.Random(world_seed(self.seed + 10, life))
        unfamiliar = round(count * unfamiliar_share)
        out = self.draw('trained', count - unfamiliar, rng) + self.draw('unfamiliar', unfamiliar, rng)
        rng.shuffle(out)
        for i, w in enumerate(out):
            w['rng'] = world_seed(self.seed + 100 + life, i)
        return out


# -- the agent inside a worker: the state's language, model and prior --------

def _init(language, labels, prior_sets, tiebreak, budget):
    h = Harness([tuple(a) for a in language])
    h.set_tiebreak(tiebreak)
    sim = Simulator(h)
    if labels:
        arr = np.array([labels.get(k, -1) for k in h.key_names])
        if (arr >= 0).sum() >= 3:
            sim = LearnedFamilySimulator(h, arr, WEIGHT, SLIP)
    prior = None
    if prior_sets:
        sets = [[h.key_index[k] for k in s if k in h.key_index] for s in prior_sets]
        sets = [s for s in sets if s]
        if sets:
            prior = Prior(h, sets)
    coach = BLIND if prior is None else (UNHEDGED if budget <= UNHEDGED_UP_TO else CHAMPION)
    _STATE.update(h=h, sim=sim, prior=prior, coach=coach, budget=budget)


def _views(h, masks, rng):
    views, tasks = [], []
    for mask in masks:
        task = make_task(SimpleNamespace(masks=[mask]), 0, rng)
        consistent = np.flatnonzero(vector_test(h.packed, task['visible_pos'], task['visible_neg']))
        good = vector_test(h.packed, task['hidden_pos'], task['hidden_neg'])[consistent]
        select = np.lexsort((h.complexity[consistent], h.sizes[consistent]))
        views.append({'mechanism': 0, 'rows': consistent[select], 'good': good[select]})
        tasks.append((task['visible_pos'], task['visible_neg']))
    return views, tasks


def _life(job):
    index, masks, rng_seed = job
    s = _STATE
    h, sim = s['h'], s['sim']
    views, tasks = _views(h, masks, random.Random(rng_seed))
    trace = []
    hits = sim.lifetime(s['coach'], views, s['prior'], s['budget'], trace=trace)
    picks, confident, unsolved = {}, set(), []
    for d in trace:
        if d['pick'] >= 0:
            for k in sim.row_keys[d['pick']]:
                name = h.key_names[k]
                picks[name] = picks.get(name, 0) + 1
                if d['window_consistent'] <= 1:
                    confident.add(name)
        else:
            unsolved.append(tasks[d['step']])
    return {'index': index, 'hits': int(hits.sum()), 'picks': picks,
            'confident': sorted(confident), 'unsolved': unsolved, 'stuck': len(unsolved)}


class Seed:
    def __init__(self, path, language=None, name=None):
        self.path = Path(path)
        file = self.path / 'state.json'
        if file.exists():
            self.state = json.loads(file.read_text())
        else:
            if language is None:
                raise ValueError('a new seed needs a language')
            self.path.mkdir(parents=True, exist_ok=True)
            self.state = {'name': name or self.path.name, 'created': time.strftime('%Y-%m-%d %H:%M'),
                          'version': 0, 'tiebreak': 77,
                          'language': [list(a) for a in language],
                          'experience': [], 'experience_all': [],
                          'model': None, 'prior': False, 'kept': [], 'ledger': [],
                          'held_out_score': None}
            self.save()

    def save(self):
        (self.path / 'state.json').write_text(json.dumps(self.state))

    @property
    def lives(self):
        return sum(1 for e in self.state['ledger'] if e['op'] == 'live')

    def run(self, worlds, budget, state=None, workers=WORKERS):
        st = self.state if state is None else state
        labels = st['model']['labels'] if st['model'] else None
        prior_sets = st['experience_all'] if st['prior'] else None
        ctx = multiprocessing.get_context('spawn')
        with ctx.Pool(workers, initializer=_init,
                      initargs=(st['language'], labels, prior_sets, st['tiebreak'], budget)) as pool:
            out = pool.map(_life, [(i, w['masks'], w['rng']) for i, w in enumerate(worlds)], chunksize=2)
        return sorted(out, key=lambda r: r['index'])

    @staticmethod
    def score(records, worlds, budget):
        pools = sorted({w['pool'] for w in worlds})
        return {'budget': budget, 'total': int(sum(r['hits'] for r in records)),
                'by_pool': {p: float(np.mean([r['hits'] for r, w in zip(records, worlds) if w['pool'] == p]))
                            for p in pools}}

    # -- live ---------------------------------------------------------------

    def live(self, area, count, budget):
        life = self.lives
        worlds = area.life_worlds(life, count)
        records = self.run(worlds, budget)
        for r in records:
            self.state['experience'].append(r['confident'])
            self.state['experience_all'].append(sorted(r['picks']))
        entry = {'life': life, 'op': 'live', 'worlds': count, 'budget': budget,
                 'scans': count * STREAM * budget, 'version': self.state['version']}
        entry.update(self.score(records, worlds, budget))
        self.state['ledger'].append(entry)
        self.save()
        return life, worlds, records

    # -- reflect ------------------------------------------------------------

    def reflect(self, minimum=48, counts=(6, 7, 8)):
        """A candidate model and prior from everything earned so far."""
        sets = self.state['experience']
        if len(sets) < minimum:
            return None
        keys = sorted(a[0] for a in self.state['language'])
        index = {k: i for i, k in enumerate(keys)}
        idx = [[index[k] for k in s if k in index] for s in sets]
        cut = len(idx) * 4 // 5
        held = _matrix(idx[cut:], len(keys))
        scores = {}
        try:
            for g in counts:
                m, _ = fit_restarts(idx[:cut], len(keys), g, restarts=3)
                scores[g] = float(m.log_likelihood(held))
            best = max(scores, key=scores.get)
            m, _ = fit_restarts(idx, len(keys), best, restarts=3)
        except (ValueError, IndexError) as error:
            return {'error': repr(error)}
        return {'labels': {keys[i]: int(l) for i, l in enumerate(m.labels) if l >= 0},
                'groups': best, 'worlds': len(sets), 'held_out_ll': {str(g): v for g, v in scores.items()},
                'r': {keys[i]: round(float(m.r[i]), 3) for i in np.flatnonzero(m.seen)}}

    # -- extend -------------------------------------------------------------

    def extend(self, worlds, records, cands, share=.3, cap=40):
        """Candidate atoms for the worlds with the most unsolved tasks: the
        top `share` of this life's worlds by stuck count."""
        stuck = np.array([r['stuck'] for r in records])
        # the worlds this life could not solve much of, and never the easy ones
        cut = max(.15 * STREAM, float(np.quantile(stuck, 1 - share)))
        masks = {a[0]: mask_of(a[2]) for a in self.state['language']}
        known = set(masks.values()) | {FULL & ~m for m in masks.values()}
        new, tests, provenance = {}, 0, []
        for w, r in zip(worlds, records):
            if r['stuck'] < cut:
                continue
            earned = [masks[k] for k in r['picks'] if k in masks]
            kept, n = invent(cands, r['unsolved'], earned, known | set(new) | {FULL & ~m for m in new})
            tests += n
            for j in kept:
                name, _tags, expr, mask = cands[j]
                if len(new) < cap and mask not in new and (FULL & ~mask) not in new:
                    new[mask] = (f'inv:{name}', 'inv', expr)
                    provenance.append({'atom': f'inv:{name}', 'pool': w['pool'], 'stuck': int(r['stuck'])})
        return list(new.values()), tests, provenance

    # -- prove --------------------------------------------------------------

    def prove(self, held_out, candidate, budget, change, note=None):
        """Keep the candidate only if it solves more held-out tasks than the
        carried state. The held-out set is fixed, so the carried score is
        cached per state version."""
        carried = self.state['held_out_score']
        if carried is None or carried['version'] != self.state['version'] or carried['budget'] != budget:
            carried = self.score(self.run(held_out, budget), held_out, budget)
            carried['version'] = self.state['version']
            self.state['held_out_score'] = carried
            self.save()
        new = self.score(self.run(held_out, budget, state=candidate), held_out, budget)
        kept = new['total'] > carried['total']
        entry = {'life': self.lives - 1, 'op': 'prove', 'change': change, 'carried': carried,
                 'candidate': new, 'kept': kept}
        if note:
            entry['note'] = note
        self.state['ledger'].append(entry)
        if kept:
            for key in ('language', 'model', 'prior'):
                self.state[key] = candidate[key]
            self.state['version'] += 1
            new['version'] = self.state['version']
            self.state['held_out_score'] = new
            self.state['kept'].append({'life': self.lives - 1, 'change': change,
                                       'gain': new['total'] - carried['total'],
                                       'version': self.state['version']})
        self.save()
        return kept, carried, new
