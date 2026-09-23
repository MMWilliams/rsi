"""A trainable coach for the earned loop, and a simulator fast enough to train it.

The earned loop (`mechanism_lifelong.py`, `mechanism_cold_start.py`,
`mechanism_hedged_start.py`) runs one fixed rule for a whole life: order the
catalog by what it has submitted so far plus a cross-world prior, scan `B`
rows, submit by the free rule, keep the atoms of the submission. Nothing about
that rule is learned. The coach is an external component whose parameters set
every free choice in that rule, and which can be trained by policy search on
the return of whole lifetimes in training worlds: the number of tasks solved.

Coach parameters (the champion, cold-start prior with a half hedge, is
`CHAMPION`; every field at its champion value reproduces that arm exactly):

  unknown   weight on log(FLOOR + min(evidence, 1)) per atom: how far a row
            built from atoms the agent has no evidence for is pushed down
  pair      weight on log(FLOOR + pair co-occurrence) from the training worlds
  count     weight on log(1 + evidence) per atom: repeated evidence counts more
  depth1    additive bonus for depth-one rows
  affinity  weight on log(FLOOR + max over known atoms k of P(atom | k)) for
            atoms without evidence: the conditional cross-world prior
  soft      evidence credited to the atoms of every other consistent candidate
            inside the window, divided by how many there were
  pick      preference, among consistent candidates inside the window, for
            those built from atoms the agent already has evidence for
  hedge     share of the scan budget reserved for the order with no prior terms
  hedge_slope  change in that share per doubling of the budget above 1024,
            so the reserve can differ between tight and generous budgets
  tilt      budget allocation over the stream at a fixed total: task t of T
            gets B * (1 + tilt * (1 - 2t / (T - 1))) scans, so a positive tilt
            spends early, while the agent knows nothing, and a negative one late
  rotate    share of each task's scans spent on a slice of the ordering below
            the head, moved one slice further down on every task and wrapping
            after `ROTATION` tasks, so that tasks without new evidence do not
            all rescan the same rows

Evidence is earned only from the agent's own submissions and window, so no arm
here consults anything outside the task. The window computation is exact: it
agrees row for row with a full `np.lexsort` and with `interleave`, which
`tests/test_growth_coach.py` checks against a port of the original loop.
"""
from __future__ import annotations

import itertools
import random
from dataclasses import asdict, dataclass, fields, replace

import numpy as np

from .mechanism_space import make_task, vector_test
from .mechanism_worlds import Harness, affinity

FLOOR = 1e-4
ROTATION = 16


@dataclass(frozen=True)
class Coach:
    unknown: float = 1.
    pair: float = 1.
    count: float = 0.
    depth1: float = 0.
    affinity: float = 0.
    soft: float = 0.
    pick: float = 0.
    hedge: float = .5
    hedge_slope: float = 0.
    tilt: float = 0.
    rotate: float = 0.

    def vector(self):
        return np.array([getattr(self, field.name) for field in fields(self)])

    @classmethod
    def from_vector(cls, values):
        return cls(**{field.name: float(value) for field, value in zip(fields(cls), values)})

    def clipped(self):
        """Parameters restricted to the range where each one means something."""
        return replace(self, unknown=max(self.unknown, 0.), soft=min(max(self.soft, 0.), 1.),
                       pick=max(self.pick, 0.), hedge=min(max(self.hedge, 0.), .95),
                       tilt=min(max(self.tilt, -.95), .95),
                       rotate=min(max(self.rotate, 0.), .95))

    def share(self, budget):
        """The hedge share at a budget level."""
        return min(max(self.hedge + self.hedge_slope * np.log2(budget / 1024), 0.), .95)

    def budgets(self, budget, steps):
        """Scans allotted to each task of a stream; they sum to about
        `budget * steps` whatever the tilt."""
        if not self.tilt or steps < 2:
            return [budget] * steps
        return [max(1, round(budget * (1 + self.tilt * (1 - 2 * t / (steps - 1)))))
                for t in range(steps)]

    def as_dict(self):
        return asdict(self)


CHAMPION = Coach()
UNHEDGED = Coach(hedge=0.)
BLIND = Coach(pair=0., hedge=0.)


class Prior:
    """What the training worlds say, computed once and shared by every arm."""

    def __init__(self, harness, observed_sets):
        keys = len(harness.key_names)
        counts = np.zeros((keys, keys))
        for indices in observed_sets:
            indices = list(indices)
            block = np.zeros(keys)
            block[indices] = 1.
            counts[np.ix_(indices, range(keys))] += block
        self._derive(harness, counts / max(len(observed_sets), 1))
        self.log_conditional = np.log(affinity(observed_sets, keys) + FLOOR)

    def _derive(self, harness, pair):
        self.pair = pair
        self.appearance = np.diag(pair).copy()
        self.pair_rows = np.log(harness.pair_scores(pair) + FLOOR)
        # The same values indexed by (left atom, right atom or `keys` for a
        # depth-one row, which takes its atom's diagonal).
        self.pair_table = np.log(np.hstack([pair, self.appearance[:, None]]) + FLOOR)

    def permuted(self, harness, permutation):
        """The same prior with atom labels permuted: the structure control."""
        clone = object.__new__(Prior)
        clone._derive(harness, self.pair[np.ix_(permutation, permutation)])
        clone.log_conditional = self.log_conditional[np.ix_(permutation, permutation)]
        return clone


class Simulator:
    """Lifetimes of the earned loop under a coach, with an exact window."""

    def __init__(self, harness: Harness):
        self.h = harness
        self.n = harness.catalog.size
        self.keys = len(harness.key_names)
        self.left = harness.left.astype(np.intp)
        self.right = np.where(harness.right >= 0, harness.right, self.keys).astype(np.intp)
        self.pair_index = self.left * (self.keys + 1) + self.right
        self.depth1_table = np.zeros((self.keys, self.keys + 1))
        self.depth1_table[:, self.keys] = 1.
        self.row_keys = [tuple(k for k in (harness.left[i], harness.right[i]) if k >= 0)
                         for i in range(self.n)]
        self.scratch = np.full(self.n, np.inf)
        self.buffer = np.empty(self.n)

    # -- tasks -------------------------------------------------------------

    def views(self, stream, rng, examples=False):
        """Everything about a task stream that does not depend on the arm,
        with the example strings themselves when an audit will need them."""
        out = []
        for mechanism in stream:
            task = make_task(self.h.catalog, mechanism, rng)
            consistent = np.flatnonzero(vector_test(self.h.packed, task['visible_pos'],
                                                    task['visible_neg']))
            good = vector_test(self.h.packed, task['hidden_pos'],
                               task['hidden_neg'])[consistent]
            select = np.lexsort((self.h.complexity[consistent], self.h.sizes[consistent]))
            view = {'mechanism': int(mechanism), 'rows': consistent[select],
                    'good': good[select]}
            if examples:
                view.update(visible=task['visible'], hidden=task['hidden'])
            out.append(view)
        return out

    # -- scores ------------------------------------------------------------

    def atom_terms(self, coach, evidence, prior):
        """Per-atom scores with and without the prior's conditional term.

        Before any evidence the atom terms are zero, as in the original arms:
        the no-evidence order is the prior (or the tie-break) and nothing else.
        """
        if not evidence.any():
            zero = np.zeros(self.keys + 1)
            return zero, zero
        base = coach.unknown * np.log(FLOOR + np.minimum(evidence, 1.))
        if coach.count:
            base = base + coach.count * np.log1p(evidence)
        plain = np.append(base, 0.)
        if not coach.affinity:
            return plain, plain
        known = np.flatnonzero(evidence > 0)
        lifted = base + coach.affinity * np.where(
            evidence > 0, 0., prior.log_conditional[known].max(axis=0))
        return np.append(lifted, 0.), plain

    def constants(self, coach, prior):
        """The parts of the two score tables that do not change within a life.

        Every row score is a function of the row's (left, right) atom pair, so
        scores are built as a table over pairs and gathered once.
        """
        first = second = None
        if coach.pair:
            first = coach.pair * prior.pair_table
        if coach.depth1:
            second = coach.depth1 * self.depth1_table
            first = second if first is None else first + second
        return first, second

    def row_scores(self, terms, constant):
        # terms[keys] is zero, so a depth-one row adds exactly 0. for its
        # missing second atom, as `Harness.row_scores` does, and the sum is
        # formed in the same order as the original arms: atoms, then prior.
        table = terms[:self.keys, None] + terms[None, :]
        if constant is not None:
            table += constant
        return np.take(table.ravel(), self.pair_index)

    def orderings(self, terms, constants, share):
        """Row scores of the coach's ordering and, when hedged, of the
        ordering without prior terms."""
        lifted, plain = terms
        first = self.row_scores(lifted, constants[0])
        return first, (self.row_scores(plain, constants[1]) if share else None)

    def window(self, scores, budget, share):
        """The rows inside the first `budget` of the coach's ordering, as a
        boolean mask over the catalog."""
        first, second = scores
        if second is None:
            return self.top_mask(first, budget)
        return self.hedged_mask(first, second, share, budget)

    # -- windows -----------------------------------------------------------

    def _threshold(self, score, k):
        """The rows above the k-th largest score, and the tied rows at it that
        the tie-break admits."""
        tb = self.h.tiebreak
        np.copyto(self.buffer, score)
        self.buffer.partition(self.n - k)
        kth = self.buffer[self.n - k]
        above = np.flatnonzero(score > kth)
        ties = np.flatnonzero(score == kth)
        need = k - len(above)
        if need < len(ties):
            ties = ties[np.argpartition(tb[ties], need - 1)[:need]]
        return above, ties

    def top(self, score, k):
        """The first `k` rows of `lexsort((tiebreak, -score))`, in order."""
        tb = self.h.tiebreak
        if k >= self.n:
            return np.lexsort((tb, -score))
        chosen = np.concatenate(self._threshold(score, k))
        return chosen[np.lexsort((tb[chosen], -score[chosen]))]

    def top_mask(self, score, budget):
        mask = np.zeros(self.n, dtype=bool)
        if budget >= self.n:
            mask[:] = True
            return mask
        above, ties = self._threshold(score, budget)
        mask[above] = True
        mask[ties] = True
        return mask

    def hedged_top(self, first, second, share, k):
        """The first `k` rows of `interleave(first order, second order)`, in
        order.

        A row among them is among the first `k` of at least one ordering, and
        its merged key is min(rank1 / (1 - share), rank2 / share), so only the
        two top lists are needed.
        """
        top1 = self.top(first, k + 1)
        top2 = self.top(second, k + 1)
        merged = self.scratch
        merged[top1] = np.arange(len(top1)) / (1. - share)
        merged[top2] = np.minimum(merged[top2], np.arange(len(top2)) / share)
        union = np.union1d(top1, top2)
        chosen = union[np.lexsort((union, merged[union]))[:k]]
        merged[union] = np.inf
        return chosen

    def ranked(self, scores, k, share):
        """The first `k` rows of the coach's ordering, in order."""
        first, second = scores
        if second is None:
            return self.top(first, min(k, self.n))
        return self.hedged_top(first, second, share, min(k, self.n - 1))

    def hedged_mask(self, first, second, share, budget):
        """The first `budget` rows of `interleave(first order, second order)`."""
        mask = np.zeros(self.n, dtype=bool)
        if budget >= self.n:
            mask[:] = True
            return mask
        mask[self.hedged_top(first, second, share, budget)] = True
        return mask

    def inside(self, rows, score, budget):
        """Which of `rows` fall in the first `budget` of one ordering."""
        return self.top_mask(score, budget)[rows]

    def inside_hedged(self, rows, first, second, share, budget):
        """Which of `rows` fall in the first `budget` of `interleave`."""
        return self.hedged_mask(first, second, share, budget)[rows]

    # -- a life ------------------------------------------------------------

    def lifetime(self, coach, views, prior, budget, arm='earned', trace=None):
        """Tasks solved over one stream. `arm` is 'earned' (keeps what it
        submitted), 'guarded' (the same, but the hedged share of the scans
        always follows the fixed no-prior rule, whatever the coach says),
        'revealed' (told the true mechanism) or 'static' (never updates)."""
        evidence = np.zeros(self.keys)
        hits = np.zeros(len(views), dtype=np.int8)
        constants = self.constants(coach, prior)
        if arm == 'guarded':
            constants = (constants[0], None)
        share = coach.share(budget)
        allotted = coach.budgets(budget, len(views))
        terms = scores = mask = scans = ranking = None
        for step, view in enumerate(views):
            # The scores are a function of the atom terms alone and the window
            # of the scores and the scans allotted, so each is recomputed only
            # when what it depends on changes.
            fresh = self.atom_terms(coach, evidence, prior)
            if arm == 'guarded':
                fresh = (fresh[0], self.atom_terms(BLIND, evidence, prior)[1])
            if terms is None or not (np.array_equal(fresh[0], terms[0])
                                     and np.array_equal(fresh[1], terms[1])):
                terms = fresh
                scores = self.orderings(terms, constants, share)
                scans = None
                ranking = None
            rows = view['rows']
            if coach.rotate:
                head = round((1 - coach.rotate) * allotted[step])
                width = allotted[step] - head
                need = head + ROTATION * width
                if ranking is None or len(ranking) < need:
                    ranking = self.ranked(scores, need, share)
                start = head + (step % ROTATION) * width
                inside = np.concatenate([ranking[:head], ranking[start:start + width]])
                candidates = np.flatnonzero(np.isin(rows, inside))
            else:
                if scans != allotted[step]:
                    scans = allotted[step]
                    mask = self.window(scores, scans, share)
                candidates = np.flatnonzero(mask[rows])
            pick = -1
            if len(candidates):
                if coach.pick:
                    known = np.array([sum(evidence[k] > 0 for k in self.row_keys[rows[c]])
                                      for c in candidates])
                    pick = int(candidates[np.argmin(np.arange(len(candidates))
                                                    - coach.pick * 10. * known)])
                else:
                    pick = int(candidates[0])
            hit = int(pick >= 0 and view['good'][pick])
            hits[step] = hit
            if trace is not None:
                trace.append({'step': step, 'mechanism': view['mechanism'],
                              'pick': int(rows[pick]) if pick >= 0 else -1, 'hit': hit,
                              'window_consistent': int(len(candidates))})
            if arm == 'static':
                continue
            if arm == 'revealed':
                for key in self.row_keys[view['mechanism']]:
                    evidence[key] += 1.
                continue
            if pick < 0:
                continue
            for key in self.row_keys[rows[pick]]:
                evidence[key] += 1.
            if coach.soft and len(candidates) > 1:
                credit = coach.soft / len(candidates)
                for c in candidates:
                    if c != pick:
                        for key in self.row_keys[rows[c]]:
                            evidence[key] += credit
        return hits


# -- worlds and priors, as the cold-start and hedged-start runs built them --

def triples(harness, families, rng, keys_per_world, minimum):
    return [triple for triple in itertools.combinations(sorted(families), 3)
            if harness.sample_world(triple, rng, keys_per_world, minimum)]


def draw_worlds(harness, triple_pool, count, rng, keys_per_world, minimum, stream):
    out = []
    while len(out) < count:
        world = harness.sample_world(triple_pool[rng.randrange(len(triple_pool))], rng,
                                     keys_per_world, minimum)
        if world is None:
            continue
        members = list(world['members'])
        rng.shuffle(members)
        world['stream'] = members[:stream]
        out.append(world)
    return out


def observed_sets(harness, worlds, reserved, solved_per_world, rng):
    out = []
    for world in worlds:
        allowed = [index for index in world['members'] if index not in reserved]
        solved = rng.sample(allowed, min(solved_per_world, len(allowed)))
        out.append(sorted({harness.key_index[key] for key in harness.observed_keys(solved)}))
    return out


def world_seed(base, index):
    return random.Random(f'{base}:{index}').randrange(1 << 62)


# -- a process pool that keeps one catalog per worker ------------------------

_STATE = {}


def _init(tiebreak_seed, priors, views):
    harness = Harness()
    harness.set_tiebreak(tiebreak_seed)
    _STATE.update(simulator=Simulator(harness), priors=priors, views=views)


def _run(job):
    coach, world, budgets, arm, prior = job
    simulator = _STATE['simulator']
    views = _STATE['views'][world] if isinstance(world, str) else world
    return [simulator.lifetime(coach, views, _STATE['priors'][prior], budget, arm=arm)
            for budget in budgets]


def _run_traced(job):
    coach, world, budgets, arm, prior = job
    simulator = _STATE['simulator']
    views = _STATE['views'][world] if isinstance(world, str) else world
    out = []
    for budget in budgets:
        trace = []
        simulator.lifetime(coach, views, _STATE['priors'][prior], budget, arm=arm, trace=trace)
        out.append(trace)
    return out


class Pool:
    """Lifetimes evaluated in parallel. A job is (coach, world, arm, prior
    name), where a world is a key into the views the pool was built with or a
    view list shipped with the job; the result is one hit vector per budget."""

    def __init__(self, workers, tiebreak_seed, priors, views, budgets):
        import multiprocessing
        self.budgets = tuple(budgets)
        self.pool = multiprocessing.get_context('spawn').Pool(
            workers, initializer=_init, initargs=(tiebreak_seed, priors, views))

    def map(self, jobs, traced=False):
        """Jobs are (coach, world, arm, prior) or, to run other budgets than
        the pool's, (coach, world, arm, prior, budgets). A traced map returns
        each lifetime's per-task decisions instead of its hit vector."""
        return self.pool.map(_run_traced if traced else _run,
                             [(job[0], job[1], tuple(job[4]) if len(job) > 4
                               else self.budgets, job[2], job[3]) for job in jobs],
                             chunksize=1)

    def close(self):
        self.pool.close()
        self.pool.join()


# -- policy search on lifetimes ---------------------------------------------

def centred_ranks(values):
    ranks = np.empty(len(values))
    ranks[np.argsort(values, kind='stable')] = np.arange(len(values))
    return ranks / (len(values) - 1) - .5


def shaped(totals, kinds):
    """Centred ranks per budget and per kind of lifetime, averaged: each
    budget and each kind carries equal weight whatever its scale."""
    columns = [centred_ranks(totals[kind][:, b]) for kind in kinds
               for b in range(totals[kind].shape[1])]
    return np.mean(columns, axis=0)


class Trainer:
    """Evolution strategies over some of a coach's fields: antithetic
    Gaussian perturbations, every perturbation scored on the same lifetimes,
    centred-rank fitness shaping.

    `budget_sets` lists which budgets each coach is scored on; one set with
    every budget trains a single shared coach.
    """

    def __init__(self, budget_sets, searched, sigma, seed, pairs=8, learning_rate=1.,
                 arm='earned', start=CHAMPION):
        self.budget_sets = budget_sets
        self.index = [list(Coach.__dataclass_fields__).index(name) for name in searched]
        self.sigma = np.array([sigma[name] for name in searched])
        self.means = [start.vector() for _ in budget_sets]
        self.rng = np.random.default_rng(seed)
        self.pairs = pairs
        self.learning_rate = learning_rate
        self.arm = arm

    def coach(self, slot, noise=None):
        vector = self.means[slot].copy()
        if noise is not None:
            vector[self.index] += self.sigma * noise
        return Coach.from_vector(vector).clipped()

    def generation(self, pool, lifetimes):
        """One update from `lifetimes`, a list of (views, prior name, kind)."""
        plans = []
        for slot, budgets in enumerate(self.budget_sets):
            noise = self.rng.standard_normal((self.pairs, len(self.index)))
            coaches = [self.coach(slot, sign * row) for row in noise for sign in (1, -1)]
            plans.append((slot, budgets, noise, coaches))
        jobs = [(coach, views, self.arm, prior, budgets)
                for _slot, budgets, _noise, coaches in plans
                for coach in coaches for views, prior, _kind in lifetimes]
        results = iter(pool.map(jobs))
        kinds = sorted({kind for _views, _prior, kind in lifetimes})
        for slot, budgets, noise, coaches in plans:
            totals = {kind: np.zeros((len(coaches), len(budgets))) for kind in kinds}
            for number in range(len(coaches)):
                for _views, _prior, kind in lifetimes:
                    totals[kind][number] += [hits.sum() for hits in next(results)]
            fitness = shaped(totals, kinds)
            gradient = ((fitness[0::2] - fitness[1::2])[:, None] * noise).mean(axis=0)
            self.means[slot][self.index] += self.learning_rate * self.sigma * gradient
            self.means[slot] = self.coach(slot).vector()
