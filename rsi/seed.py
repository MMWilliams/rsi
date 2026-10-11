"""The seed: one agent, one carried state, four operations on itself.

State: its language (the atoms its catalog is built from, shared across
areas), its experience (the atom sets it earned in every world it has lived,
by atom name and area, so that the language may grow under it), per area a
world and self model and a pair prior fitted from that area's experience, the
atoms it invented and when, a ledger of every change it tried with its proof,
and the resource it has spent.

Operations: `live` earns experience in an area under a scan budget; `reflect`
refits an area's model and prior from everything earned there, choosing the
group count and the groups per world by held-out likelihood; `extend` invents
atoms from the grammar for the worlds it could not solve; `prune` proposes
dropping invented atoms that never earned their keep. Every change is a
candidate until `prove` shows it solves more of a held-out set, drawn fresh
for each life, than the carried state does. A change to shared state (the
language) must also leave every other area the seed has lived in no worse.
Only proven changes are kept, nothing kept is reset, and every proof lifetime
is charged to the seed's resource. Nothing here reads a family label or a
true world; an area's pools name where a world came from, for the ledger only.
"""
from __future__ import annotations

import copy
import json
import multiprocessing
import os
import random
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from .environments import draw as draw_env, make_environment
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
THETAS = {7: {'groups': 9, 'per_world': 3, 'slip': .15, 'skew': 0.},
          11: {'groups': 12, 'per_world': 4, 'slip': 0., 'skew': 0.},
          13: {'groups': 6, 'per_world': 2, 'slip': .15, 'skew': 0.}}
_STATE = {}


# -- areas ------------------------------------------------------------------

class Area:
    """Worlds from a generator the seed never sees."""
    name = 'area'
    pools = ('all',)
    spec = {}

    def __init__(self, seed):
        self.full = Harness()
        self.seed = seed

    def _worlds(self, pool, count, rng):
        raise NotImplementedError

    def draw(self, pool, count, rng):
        return [{'pool': pool, 'masks': [self.full.catalog.masks[m] for m in w['stream']]}
                for w in self._worlds(pool, count, rng)]

    def held_out(self, per_pool, salt=0):
        """A fresh held-out set per salt: proofs never reuse one set."""
        rng = random.Random(world_seed(self.seed + 4242, salt))
        out = []
        for pool in self.pools:
            out += self.draw(pool, per_pool, rng)
        for i, w in enumerate(out):
            w['rng'] = world_seed(self.seed + 8 + salt, i)
        return out

    def life_worlds(self, life, count):
        rng = random.Random(world_seed(self.seed + 10, life))
        out = self.life_draw(count, rng)
        rng.shuffle(out)
        for i, w in enumerate(out):
            w['rng'] = world_seed(self.seed + 100 + life, i)
        return out


class MechanismArea(Area):
    """Family-structured worlds. The seed's starting language lacks the
    unfamiliar families, so their worlds hold mechanisms it cannot reach by
    scanning; a fifth of the viable known triples stay out of its lives."""
    name = 'mech'
    pools = ('trained', 'untrained', 'unfamiliar')
    spec = {'kind': 'mech'}

    def __init__(self, seed, unfamiliar=('popcount', 'xormod'), untrained_share=.2,
                 unfamiliar_share=.25):
        super().__init__(seed)
        rng = random.Random(seed)
        families = sorted(self.full.by_family)
        known = [f for f in families if f not in unfamiliar]
        pool = triples(self.full, known, rng, KEYS_PER_WORLD, MINIMUM_MEMBERS)
        rng.shuffle(pool)
        cut = max(1, round(untrained_share * len(pool)))
        everything = triples(self.full, families, rng, KEYS_PER_WORLD, MINIMUM_MEMBERS)
        self.triples = {'untrained': pool[:cut], 'trained': pool[cut:],
                        'unfamiliar': [t for t in everything if set(t) & set(unfamiliar)]}
        self.unfamiliar_share = unfamiliar_share
        self.seed_language = [a for a in atom_expressions() if a[1] not in unfamiliar]

    def _worlds(self, pool, count, rng):
        return draw_worlds(self.full, self.triples[pool], count, rng, KEYS_PER_WORLD,
                           MINIMUM_MEMBERS, STREAM)

    def life_draw(self, count, rng):
        unfamiliar = round(count * self.unfamiliar_share)
        return self.draw('trained', count - unfamiliar, rng) + self.draw('unfamiliar', unfamiliar, rng)


class DrawnArea(Area):
    """An environment drawn from the Phase 2 meta-distribution: every atom
    partitioned at random into groups, a world drawing from a few of them, with
    slips. The partition cuts across families, so nothing the seed learned in
    the mechanism area applies except its language."""
    pools = ('env',)

    def __init__(self, seed, env_seed, theta=None):
        super().__init__(seed)
        self.name = f'drawn{env_seed}'
        self.environment = make_environment(self.full, env_seed, theta)
        self.spec = {'kind': 'drawn', 'env_seed': env_seed, 'theta': self.environment['theta']}

    def _worlds(self, pool, count, rng):
        return draw_env(self.full, self.environment, count, rng, KEYS_PER_WORLD,
                        MINIMUM_MEMBERS, STREAM)

    def life_draw(self, count, rng):
        return self.draw('env', count, rng)


def make_area(spec, seed):
    """An area from its spec, or from a name: mech, drawnN, metricN."""
    if isinstance(spec, str):
        name = spec
        if name == 'mech':
            spec = {'kind': 'mech'}
        elif name.startswith('drawn'):
            env_seed = int(name[5:] or 7)
            spec = {'kind': 'drawn', 'env_seed': env_seed, 'theta': THETAS.get(env_seed)}
        elif name.startswith('metric'):
            spec = {'kind': 'metric', 'weight_seed': int(name[6:] or 777001)}
        else:
            raise ValueError(name)
    if spec['kind'] == 'mech':
        return MechanismArea(seed)
    if spec['kind'] == 'drawn':
        return DrawnArea(seed, spec['env_seed'], spec.get('theta'))
    if spec['kind'] == 'metric':
        from .seed_areas import MetricArea
        return MetricArea(seed, spec['weight_seed'])
    raise ValueError(spec)


# -- the agent inside a worker ------------------------------------------------

def _init(language, labels, per_world, prior_sets, tiebreak, budget):
    h = Harness([tuple(a) for a in language])
    h.set_tiebreak(tiebreak)
    sim = Simulator(h)
    if labels:
        arr = np.array([labels.get(k, -1) for k in h.key_names])
        if (arr >= 0).sum() >= 3:
            sim = LearnedFamilySimulator(h, arr, WEIGHT, SLIP, per_world=per_world)
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


# -- the seed ----------------------------------------------------------------

class Seed:
    def __init__(self, path, language=None, name=None, seed=None):
        self.path = Path(path)
        file = self.path / 'state.json'
        if file.exists():
            self.state = json.loads(file.read_text())
            self._migrate(seed)
        else:
            if language is None:
                raise ValueError('a new seed needs a language')
            self.path.mkdir(parents=True, exist_ok=True)
            self.state = {'name': name or self.path.name, 'created': time.strftime('%Y-%m-%d %H:%M'),
                          'version': 0, 'tiebreak': 77, 'seed': seed,
                          'language': [list(a) for a in language],
                          'initial_language': [list(a) for a in language],
                          'experience': [], 'areas': {}, 'inventions': {},
                          'kept': [], 'ledger': [],
                          'resource': {'live_scans': 0, 'proof_scans': 0, 'invention_tests': 0}}
            self.save()

    def _migrate(self, seed):
        s = self.state
        changed = False
        if 'areas' not in s:   # the first seed kept one area's model at the top level
            s['areas'] = {'mech': {'model': s.pop('model', None), 'prior': s.pop('prior', False),
                                   'held_out_score': None}}
            s.pop('held_out_score', None)
            picks = s.pop('experience_all', [])
            s['experience'] = [{'area': 'mech', 'confident': c, 'picks': p}
                               for c, p in zip(s['experience'], picks)]
            s['initial_language'] = [a for a in s['language'] if not a[0].startswith('inv:')]
            s['inventions'] = {a[0]: {'life': None, 'area': 'mech'} for a in s['language']
                               if a[0].startswith('inv:')}
            s['resource'] = {'live_scans': sum(e.get('scans', 0) for e in s['ledger'] if e['op'] == 'live'),
                             'proof_scans': 0, 'invention_tests': 0}
            for e in s['ledger']:
                e.setdefault('area', 'mech')
            changed = True
        if s.get('seed') is None and seed is not None:
            s['seed'] = seed
            changed = True
        for name, a in s['areas'].items():
            if 'spec' not in a:
                a['spec'] = make_area(name, 0).spec if name != 'mech' else {'kind': 'mech'}
                changed = True
        if changed:
            self.save()

    def save(self):
        (self.path / 'state.json').write_text(json.dumps(self.state))

    def lives(self, area=None):
        return sum(1 for e in self.state['ledger']
                   if e['op'] == 'live' and (area is None or e['area'] == area))

    def area_state(self, area, state=None):
        st = self.state if state is None else state
        return st['areas'].setdefault(area, {'model': None, 'prior': False, 'held_out_score': None})

    def candidate(self):
        return copy.deepcopy(self.state)

    def run(self, worlds, budget, area, state=None, workers=WORKERS):
        st = self.state if state is None else state
        a = self.area_state(area, st)
        model = a['model']
        labels = model['labels'] if model else None
        per_world = model.get('per_world', 3) if model else 3
        prior_sets = [e['picks'] for e in st['experience'] if e['area'] == area] if a['prior'] else None
        ctx = multiprocessing.get_context('spawn')
        jobs = [(i, w['masks'], w['rng']) for i, w in enumerate(worlds)]
        for attempt in range(4):
            try:
                with ctx.Pool(max(1, workers >> attempt), initializer=_init,
                              initargs=(st['language'], labels, per_world, prior_sets,
                                        st['tiebreak'], budget)) as pool:
                    out = pool.map(_life, jobs, chunksize=2)
                break
            except MemoryError:
                # the machine's commit is shared with other jobs; wait, then fewer workers
                if attempt == 3:
                    raise
                time.sleep(90)
        return sorted(out, key=lambda r: r['index'])

    @staticmethod
    def score(records, worlds, budget):
        pools = sorted({w['pool'] for w in worlds})
        return {'budget': budget, 'total': int(sum(r['hits'] for r in records)),
                'by_pool': {p: float(np.mean([r['hits'] for r, w in zip(records, worlds) if w['pool'] == p]))
                            for p in pools}}

    # -- live ---------------------------------------------------------------

    def live(self, area, count, budget):
        life = self.lives(area.name)
        worlds = area.life_worlds(life, count)
        records = self.run(worlds, budget, area.name)
        self.area_state(area.name)['spec'] = area.spec
        for r in records:
            self.state['experience'].append({'area': area.name, 'confident': r['confident'],
                                             'picks': sorted(r['picks'])})
        self.state['resource']['live_scans'] += count * STREAM * budget
        entry = {'life': life, 'area': area.name, 'op': 'live', 'worlds': count, 'budget': budget,
                 'scans': count * STREAM * budget, 'version': self.state['version']}
        entry.update(self.score(records, worlds, budget))
        self.state['ledger'].append(entry)
        self.save()
        return life, worlds, records

    # -- reflect ------------------------------------------------------------

    def reflect(self, area, minimum=48, counts=(6, 7, 8), per_worlds=(2, 3, 4)):
        """A candidate model for an area from everything earned there: group
        count and groups per world by held-out likelihood."""
        sets = [e['confident'] for e in self.state['experience'] if e['area'] == area]
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
                for pw in per_worlds:
                    if pw >= g:
                        continue
                    m, _ = fit_restarts(idx[:cut], len(keys), g, restarts=3, per_world=pw)
                    scores[(g, pw)] = float(m.log_likelihood(held))
            best_g, best_pw = max(scores, key=scores.get)
            m, _ = fit_restarts(idx, len(keys), best_g, restarts=3, per_world=best_pw)
        except (ValueError, IndexError) as error:
            return {'error': repr(error)}
        return {'labels': {keys[i]: int(l) for i, l in enumerate(m.labels) if l >= 0},
                'groups': best_g, 'per_world': best_pw, 'worlds': len(sets),
                'held_out_ll': {f'{g},{pw}': v for (g, pw), v in scores.items()},
                'r': {keys[i]: round(float(m.r[i]), 3) for i in np.flatnonzero(m.seen)}}

    # -- extend and prune ---------------------------------------------------

    def extend(self, worlds, records, cands, share=.3, cap=40):
        """Candidate atoms for the worlds with the most unsolved tasks: the
        top `share` of this life's worlds by stuck count, never the easy ones."""
        stuck = np.array([r['stuck'] for r in records])
        cut = max(.15 * STREAM, float(np.quantile(stuck, 1 - share)))
        masks = {a[0]: mask_of(a[2]) for a in self.state['language']}
        known = set(masks.values()) | {FULL & ~m for m in masks.values()}
        new, tests, provenance = {}, 0, []
        for w, r in zip(worlds, records):
            if r['stuck'] < cut:
                continue
            earned = [masks[k] for k in r['picks'] if k in masks]
            kept, n = invent(cands, r['unsolved'], earned,
                             known | set(new) | {FULL & ~m for m in new})
            tests += n
            for j in kept:
                name, _tags, expr, mask = cands[j]
                if len(new) < cap and mask not in new and (FULL & ~mask) not in new:
                    new[mask] = (f'inv:{name}', 'inv', expr)
                    provenance.append({'atom': f'inv:{name}', 'pool': w['pool'], 'stuck': int(r['stuck'])})
        self.state['resource']['invention_tests'] += tests
        return list(new.values()), tests, provenance

    def prune(self, min_lives=2, r_min=.10):
        """Invented atoms that have not earned their keep, two or more lives
        after they entered: never earned with confidence anywhere, or rated by
        every area model that has seen them as found only through the seed's
        own wrong picks (discovery rate below `r_min`, the self model's
        import-only verdict). Candidates for removal; the proof decides."""
        life = self.lives()
        earned = {k for e in self.state['experience'] for k in e['confident']}
        models = [a['model'] for a in self.state['areas'].values() if a.get('model')]
        out = []
        for k, meta in self.state['inventions'].items():
            if life - (meta.get('life') or 0) < min_lives:   # atoms of unknown entry are old
                continue
            ratings = [m['r'][k] for m in models if k in m['r']]
            if k not in earned or (ratings and max(ratings) < r_min):
                out.append(k)
        return out

    # -- prove --------------------------------------------------------------

    def _carried(self, area, held_out, salt, budget):
        a = self.area_state(area.name)
        carried = a['held_out_score']
        if (carried is None or carried.get('version') != self.state['version']
                or carried.get('salt') != salt or carried['budget'] != budget
                or carried.get('size') != len(held_out)):
            carried = self.score(self.run(held_out, budget, area.name), held_out, budget)
            carried.update(version=self.state['version'], salt=salt, size=len(held_out))
            a['held_out_score'] = carried
            self.state['resource']['proof_scans'] += len(held_out) * STREAM * budget
            self.save()
        return carried

    def prove(self, area, held_out, salt, candidate, budget, change, note=None,
              shared=False, per_pool_other=12, tolerance=.02):
        """Keep the candidate only if it solves more of this life's held-out
        set than the carried state and, for a change to shared state, leaves
        every other area the seed has lived in within `tolerance` of its
        carried score. The carried score is cached per state version and
        held-out draw; every proof lifetime is charged."""
        carried = self._carried(area, held_out, salt, budget)
        new = self.score(self.run(held_out, budget, area.name, state=candidate), held_out, budget)
        self.state['resource']['proof_scans'] += len(held_out) * STREAM * budget
        kept = new['total'] > carried['total']
        elsewhere = {}
        if kept and shared:
            for name, a in self.state['areas'].items():
                if name == area.name or not self.lives(name) or not a.get('spec'):
                    continue
                other = make_area(a['spec'], self.state['seed'])
                held = other.held_out(per_pool_other, salt=salt)
                base = self._carried(other, held, salt, budget)
                there = self.score(self.run(held, budget, name, state=candidate), held, budget)
                self.state['resource']['proof_scans'] += len(held) * STREAM * budget
                elsewhere[name] = {'carried': base['total'], 'candidate': there['total']}
                if there['total'] < base['total'] * (1 - tolerance):
                    kept = False
        entry = {'life': self.lives(area.name) - 1, 'area': area.name, 'op': 'prove', 'change': change,
                 'salt': salt, 'carried': carried, 'candidate': new, 'kept': kept}
        if elsewhere:
            entry['elsewhere'] = elsewhere
        if note:
            entry['note'] = note
        self.state['ledger'].append(entry)
        if kept:
            for key in ('language', 'areas', 'inventions'):
                self.state[key] = candidate[key]
            self.state['version'] += 1
            new.update(version=self.state['version'], salt=salt, size=len(held_out))
            self.area_state(area.name)['held_out_score'] = new
            for name in elsewhere:   # their carried scores are now stale
                self.area_state(name)['held_out_score'] = None
            self.state['kept'].append({'life': entry['life'], 'area': area.name, 'change': change,
                                       'gain': new['total'] - carried['total'],
                                       'version': self.state['version']})
        self.save()
        return kept, carried, new, elsewhere
