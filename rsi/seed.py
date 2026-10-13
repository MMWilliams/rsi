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
import shutil
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
        elif name.startswith('str'):
            spec = {'kind': 'string', 'env_seed': int(name[3:] or 7)}
        else:
            raise ValueError(name)
    if spec['kind'] == 'mech':
        return MechanismArea(seed)
    if spec['kind'] == 'drawn':
        return DrawnArea(seed, spec['env_seed'], spec.get('theta'))
    if spec['kind'] == 'metric':
        from .seed_areas import MetricArea
        return MetricArea(seed, spec['weight_seed'])
    if spec['kind'] == 'string':
        from .seed_string import StringArea
        return StringArea(seed, spec['env_seed'])
    raise ValueError(spec)


# -- the agent inside a worker ------------------------------------------------

def _init(language, labels, per_world, prior_sets, tiebreak, budget):
    h = Harness([tuple(a) for a in language if a[1] != 'str'])   # the string form's keys live elsewhere
    h.set_tiebreak(tiebreak, stable=True)   # a row keeps its tie-break when the language changes
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

EXTENSION_SALT = 500     # an extension set's salt is its proof's salt plus this
META_SALT = 5000         # meta sets, on which two branches of the seed are compared
FALLBACK_MENU = ('model', 'prune', 'extend', 'extend+model')   # tested alone after the combination fails
REPLACES = {'extend': 'extend+model'}                           # what a retired fallback gives way to
KNOB_DEFAULTS = {'patience': 4, 'probation': 4, 'extend_cap': 40, 'recurrence': 2}   # the improver's knobs
FORMS = ('character', 'string')
PROCEDURE = {form: dict(KNOB_DEFAULTS) for form in FORMS}                         # one procedure per form
KNOBS = {'patience': (2, 4, 8), 'probation': (2, 4, 8), 'extend_cap': (20, 40, 80), 'recurrence': (2, 3)}


def form_of(spec):
    return 'string' if spec['kind'] == 'string' else 'character'


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
                          'kept': [], 'ledger': [], 'procedure': {f: dict(KNOB_DEFAULTS) for f in FORMS},
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
        s.setdefault('procedure', {f: dict(KNOB_DEFAULTS) for f in FORMS})   # in memory; written with the next real change
        if 'patience' in s['procedure']:              # one procedure for both forms, before 2026-10-12
            s['procedure'] = {f: dict(s['procedure']) for f in FORMS}
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

    def _snapshot(self, file=None):
        """What a replay of a proof needs about this version: the language,
        the areas' models and prior flags, the inventions, and how much
        experience the seed had. Rewritten whenever a proof is kept, so the
        file always holds the state as it was just before or just after."""
        folder = self.path / 'versions'
        folder.mkdir(exist_ok=True)
        file = file or folder / f'{self.state["version"]}.json'
        areas = {name: {k: v for k, v in a.items() if k not in ('held_out_score', 'extension_score')}
                 for name, a in self.state['areas'].items()}
        file.write_text(json.dumps({'version': self.state['version'], 'language': self.state['language'],
                                    'areas': areas, 'inventions': self.state['inventions'],
                                    'experience_len': len(self.state['experience'])}))

    def experience_count(self, area):
        return sum(1 for e in self.state['experience'] if e['area'] == area)

    def lives(self, area=None):
        return sum(1 for e in self.state['ledger']
                   if e['op'] == 'live' and (area is None or e['area'] == area))

    # -- the improver as state ------------------------------------------------

    def procedure(self, form):
        return self.state['procedure'][form]

    def meta_spent(self):
        """Scans charged so far to testing the procedure itself."""
        return sum(e.get('charged', 0) for e in self.state['ledger'] if e['op'] == 'meta')

    def forms(self):
        return {name: form_of(a['spec']) for name, a in self.state['areas'].items() if a.get('spec')}

    def fallback_policy(self, form, upto=None, patience=None, probation=None):
        """What the producer tests on its own after the combination fails, in
        areas of this form, learned from its own ledger: a fallback with
        `patience` rejections and no acceptance since is retired and tried
        again once every `probation` lives of the form; an extension retired
        on its own gives way to the extension with the model. A pure function
        of the ledger up to `upto`, so an auditor can recompute it."""
        patience = self.procedure(form)['patience'] if patience is None else patience
        probation = self.procedure(form)['probation'] if probation is None else probation
        forms = self.forms()
        lives, rejections, retired = 0, {}, {}
        for e in self.state['ledger'][:upto]:
            if forms.get(e.get('area')) != form:
                continue
            if e['op'] == 'live':
                lives += 1
            elif e['op'] == 'prove' and (e.get('note') or {}).get('fallback'):
                key = '+'.join(sorted(e['note']['parts']))
                if e['kept']:
                    rejections[key] = 0
                    retired.pop(key, None)
                else:
                    rejections[key] = rejections.get(key, 0) + 1
                    if rejections[key] >= patience and key not in retired:
                        retired[key] = lives
        idle = {k for k, v in retired.items() if lives == v or (lives - v) % probation}
        active = [k for k in FALLBACK_MENU if k not in idle
                  and (k not in REPLACES.values() or any(REPLACES.get(r) == k for r in idle))]
        return {'lives': lives, 'patience': patience, 'probation': probation, 'active': active,
                'retired': {k: {'rejections': rejections[k], 'since': v} for k, v in retired.items()}}

    def revise(self, area):
        """Record in the ledger the fallback policy this life runs under."""
        form = form_of(area.spec)
        policy = self.fallback_policy(form)
        self.state['ledger'].append({'op': 'revise', 'area': area.name, 'form': form, **policy})
        self.save()
        return policy

    def mutation(self, form):
        """The meta-producer: one change to the procedure to test this life,
        round-robin over its knobs by the lives in this form, each to the
        next value of its cycle."""
        forms = self.forms()
        lives = sum(1 for e in self.state['ledger'] if e['op'] == 'live' and forms.get(e['area']) == form)
        knob = list(KNOBS)[(lives - 1) % len(KNOBS)]
        current = self.procedure(form)[knob]
        others = [v for v in KNOBS[knob] if v != current]
        tried = sum(1 for e in self.state['ledger'] if e['op'] == 'meta' and e['mutation']['knob'] == knob
                    and forms.get(e['area']) == form)
        return knob, others[tried % len(others)]     # each attempt on a knob tries another of its values

    def branch(self, label):
        """A copy of this seed in its own folder, to run one phase under a procedure."""
        path = self.path / 'branches' / label
        path.mkdir(parents=True, exist_ok=True)
        (path / 'state.json').write_text(json.dumps(self.state))
        return Seed(path)

    def meta_proof(self, area, state_a, state_b, budget, life, held_out, boot=4000):
        """Two branch states on a meta set no proof used, paired over worlds:
        b's gain over a, with its bootstrap interval."""
        salt = META_SALT + 100 * sorted(self.state['areas']).index(area.name) + life
        held = area.held_out(-(-held_out // len(area.pools)), salt=salt)
        ha = [r['hits'] for r in self.run(held, budget, area.name, state=state_a)]
        hb = [r['hits'] for r in self.run(held, budget, area.name, state=state_b)]
        diff = np.array(hb, dtype=float) - np.array(ha, dtype=float)
        draws = np.random.default_rng(salt).integers(len(diff), size=(boot, len(diff)))
        means = diff[draws].mean(axis=1)
        return {'salt': salt, 'worlds': len(held), 'a': int(sum(ha)), 'b': int(sum(hb)),
                'mean': float(diff.mean()), 'scans': 2 * len(held) * STREAM * budget,
                'interval': [float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))]}

    def adopt(self, winner, loser, entry):
        """Take the winning branch's state, ledger and snapshots; charge what the
        other branch and the meta set cost; file the loser's final state for
        the auditor."""
        base = dict(self.state['resource'])
        k = sum(1 for e in self.state['ledger'] if e['op'] == 'meta')
        (self.path / 'versions').mkdir(exist_ok=True)
        loser._snapshot(self.path / 'versions' / f'meta{k}_loser.json')
        winner._snapshot()
        for f in (winner.path / 'versions').glob('*.json'):
            shutil.copyfile(f, self.path / 'versions' / f.name)
        self.state = winner.state
        r = self.state['resource']
        charged = (loser.state['resource']['live_scans'] - base['live_scans']
                   + loser.state['resource']['proof_scans'] - base['proof_scans'] + entry['meta']['scans'])
        r['proof_scans'] += charged
        entry['charged'] = charged
        r['invention_tests'] += loser.state['resource']['invention_tests'] - base['invention_tests']
        entry.update(winner_version=self.state['version'], loser_snapshot=f'meta{k}_loser.json',
                     experience_len=len(winner.state['experience']))   # both branches had this much
        self.state['ledger'].append(entry)
        self.save()
        shutil.rmtree(self.path / 'branches', ignore_errors=True)

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
        if worlds and 'tasks' in worlds[0]:       # the string form: its own worker over the same state
            from .seed_string import init_string, life_string
            init, work = init_string, life_string
            jobs = [(i, w['tasks'], w['rng']) for i, w in enumerate(worlds)]
            initargs = (st['language'], labels, prior_sets, st['tiebreak'], budget)
        else:
            init, work = _init, _life
            jobs = [(i, w['masks'], w['rng']) for i, w in enumerate(worlds)]
            initargs = (st['language'], labels, per_world, prior_sets, st['tiebreak'], budget)
        for attempt in range(4):
            try:
                with ctx.Pool(max(1, workers >> attempt), initializer=init, initargs=initargs) as pool:
                    out = pool.map(work, jobs, chunksize=2)
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

    def extend(self, worlds, records, cands, share=.3):
        """Candidate atoms for the worlds with the most unsolved tasks: the
        top `share` of this life's worlds by stuck count, never the easy ones.
        The cap on atoms per life and the recurrence an atom needs are the
        procedure's."""
        form = 'string' if worlds and 'tasks' in worlds[0] else 'character'
        cap, recurrence = self.procedure(form)['extend_cap'], self.procedure(form)['recurrence']
        if form == 'string':
            from .seed_string import extend_string
            return extend_string(self, worlds, records, cap=cap)
        stuck = np.array([r['stuck'] for r in records])
        cut = max(.15 * STREAM, float(np.quantile(stuck, 1 - share)))
        masks = {a[0]: mask_of(a[2]) for a in self.state['language'] if a[1] != 'str'}
        known = set(masks.values()) | {FULL & ~m for m in masks.values()}
        new, tests, provenance = {}, 0, []
        for w, r in zip(worlds, records):
            if r['stuck'] < cut:
                continue
            earned = [masks[k] for k in r['picks'] if k in masks]
            kept, n = invent(cands, r['unsolved'], earned,
                             known | set(new) | {FULL & ~m for m in new}, min_tasks=recurrence)
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

    def _carried(self, area, held_out, salt, budget, key='held_out_score'):
        a = self.area_state(area.name)
        carried = a[key] if key in a else None
        # the carried state's prior is built from the area's experience, which grows every
        # life whether or not a change is kept: a cached score is stale once it has grown
        lived = self.experience_count(area.name)
        if (carried is None or carried.get('version') != self.state['version']
                or carried.get('salt') != salt or carried['budget'] != budget
                or carried.get('size') != len(held_out) or 'hits' not in carried
                or carried.get('experience') != lived):
            records = self.run(held_out, budget, area.name)
            carried = self.score(records, held_out, budget)
            carried.update(version=self.state['version'], salt=salt, size=len(held_out),
                           experience=lived, hits=[r['hits'] for r in records])
            a[key] = carried
            self.state['resource']['proof_scans'] += len(held_out) * STREAM * budget
            self.save()
        return carried

    def prove(self, area, held_out, salt, candidate, budget, change, note=None,
              shared=False, per_pool_other=12, tolerance=.02, boot=4000, extend=True):
        """Keep the candidate only if its gain over the carried state on this
        life's held-out set, paired over worlds, has a bootstrap interval
        above zero and, for a change to shared state, leaves every other area
        the seed has lived in within `tolerance` of its carried score. A
        candidate whose full-set interval straddles zero, with a mean gain
        large enough that a doubled set would clear zero if the gain held,
        is run once more on an extension set of the same size and judged on
        the union. The carried score is cached per state version and
        held-out draw; every proof lifetime is charged."""
        carried = self._carried(area, held_out, salt, budget)

        def interval(diff):
            draws = np.random.default_rng(salt).integers(len(diff), size=(boot, len(diff)))
            means = diff[draws].mean(axis=1)
            return [float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))]

        # the candidate on half the set first; a clear loss stops there
        first = list(range(0, len(held_out), 2))
        second = list(range(1, len(held_out), 2))
        base = np.array(carried['hits'], dtype=float)
        hits = {}
        for part in (first, second):
            records = self.run([held_out[i] for i in part], budget, area.name, state=candidate)
            self.state['resource']['proof_scans'] += len(part) * STREAM * budget
            hits.update(zip(part, (r['hits'] for r in records)))
            done = sorted(hits)
            diff = np.array([hits[i] for i in done]) - base[done]
            bounds = interval(diff)
            if bounds[1] < 0 or diff.mean() <= 0:   # clearly or probably behind: stop at the half set
                break
        done = sorted(hits)
        new = self.score([{'hits': hits[i]} for i in done], [held_out[i] for i in done], budget)
        new.update(hits=[hits[i] for i in done], worlds=len(done), interval=bounds)
        if len(done) < len(held_out):           # stopped early: scale to the full set for the ledger
            new['total'] = int(round(new['total'] * len(held_out) / len(done)))
        kept = bounds[0] > 0 and len(done) == len(held_out)
        extension = None
        if (extend and not kept and len(done) == len(held_out) and diff.mean() > 0
                and bounds[0] > diff.mean() * (1 - 2 ** .5)):
            # at the threshold: a doubled set halves the interval's variance, so it would
            # clear zero if the mean held; one extension set, same size, its own draw
            ext_salt = salt + EXTENSION_SALT
            ext = area.held_out(len(held_out) // len(area.pools), salt=ext_salt)
            base_ext = self._carried(area, ext, ext_salt, budget, key='extension_score')
            records = self.run(ext, budget, area.name, state=candidate)
            self.state['resource']['proof_scans'] += len(ext) * STREAM * budget
            ext_hits = [r['hits'] for r in records]
            diff_all = np.concatenate([diff, np.array(ext_hits, dtype=float) - np.array(base_ext['hits'], dtype=float)])
            bounds_all = interval(diff_all)
            ext_new = self.score(records, ext, budget)
            ext_new.update(hits=ext_hits, worlds=len(ext), interval=bounds_all)
            extension = {'salt': ext_salt, 'carried': base_ext, 'candidate': ext_new}
            kept = bounds_all[0] > 0
        elsewhere = {}
        if kept and shared:
            for name, a in self.state['areas'].items():
                if name == area.name or not self.lives(name) or not a.get('spec'):
                    continue
                if (a['spec']['kind'] == 'string') != (area.spec['kind'] == 'string'):
                    continue   # each form's catalog is built from its own keys: the other is untouched
                other = make_area(a['spec'], self.state['seed'])
                held = other.held_out(max(per_pool_other, -(-24 // len(other.pools))), salt=salt)   # at least 24 worlds
                base = self._carried(other, held, salt, budget)
                there = self.score(self.run(held, budget, name, state=candidate), held, budget)
                self.state['resource']['proof_scans'] += len(held) * STREAM * budget
                elsewhere[name] = {'carried': base['total'], 'candidate': there['total']}
                if there['total'] < base['total'] * (1 - tolerance):
                    kept = False
        entry = {'life': self.lives(area.name) - 1, 'area': area.name, 'op': 'prove', 'change': change,
                 'salt': salt, 'carried': carried, 'candidate': new, 'kept': kept,
                 'experience_len': len(self.state['experience'])}
        if extension:
            entry['extension'] = extension
        if elsewhere:
            entry['elsewhere'] = elsewhere
        if note:
            entry['note'] = note
        self.state['ledger'].append(entry)
        if kept:
            self._snapshot()                      # the state before, for an auditor's replay
            for key in ('language', 'areas', 'inventions'):
                self.state[key] = candidate[key]
            self.state['version'] += 1
            entry['version_after'] = self.state['version']
            self._snapshot()
            new.update(version=self.state['version'], salt=salt, size=len(held_out),
                       experience=self.experience_count(area.name))
            self.area_state(area.name)['held_out_score'] = new
            for name in elsewhere:   # their carried scores are now stale
                self.area_state(name)['held_out_score'] = None
            self.state['kept'].append({'life': entry['life'], 'area': area.name, 'change': change,
                                       'gain': new['total'] - carried['total'],
                                       'version': self.state['version']})
        self.save()
        return kept, carried, new, elsewhere
