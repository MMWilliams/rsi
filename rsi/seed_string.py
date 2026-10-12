"""A second task form for the seed: string transformation tasks over the
published trapdoor DSL (2606.07856), given the world structure the
mechanism areas have so that the seed's four operations apply unchanged.

Keys are the DSL's primitives, widened: 49 positions (C-12 to C12, and the
start or end of the first, second or third WORD, DIGITS, UPPER or LOWER
match), three case operations and six constants, 9,400 rows in all against
a window of 1,024. Rows are the atoms built from them: the
substring between two positions, with or without a case operation, or a
constant. A program concatenates up to three rows; a task is three visible
and three hidden input-output pairs of one hidden program. A world is 14
keys drawn from three key families (as a mechanism world is 14 keys from
three atom families); its 100 tasks are programs over those keys alone. The
seed's job in a world is what it is elsewhere: find each task's program
with the rows inside its scan window, the first `budget` rows of the
catalog in the order its evidence, prior and model give (as the mechanism
window is the first `budget` rows of that catalog), learning as it goes
which keys this world uses so that the window closes on them. The UPPER and LOWER match positions are
withheld from the starting language: worlds built on them are the unfamiliar
pool, reachable only by invention. Nothing here reads a family label or a
hidden program; the pools name where a world came from, for the ledger only.
"""
from __future__ import annotations

import itertools
import random
import re
from ast import literal_eval

import numpy as np

from .seed import Area, KEYS_PER_WORLD, STREAM

FLOOR = 1e-4
TOKENS = {'WORD': re.compile(r'[A-Za-z]+'), 'DIGITS': re.compile(r'[0-9]+'),
          'UPPER': re.compile(r'[A-Z]+'), 'LOWER': re.compile(r'[a-z]+')}
CASES = ('upper', 'lower', 'cap')
CONSTS = (' ', '-', '/', '.', ', ', ': ')
POSITION_FAMILIES = ('CPOS', 'WORD', 'DIGITS', 'UPPER', 'LOWER')
FAMILIES = POSITION_FAMILIES + ('CASE', 'CONST')
UNFAMILIAR_FAMILIES = ('UPPER', 'LOWER')
VISIBLE, HIDDEN = 3, 6
CONFIRM = 32            # scans past the first solution in which no second one may appear
FIRST = ('John', 'Mary', 'Ana', 'Lucas', 'Priya', 'Chen', 'Omar', 'Zoe')
LAST = ('Smith', 'Souza', 'Lee', 'Khan', 'Garcia', 'Novak', 'Ito', 'Adebayo')


# -- the DSL ----------------------------------------------------------------

class PosError(Exception):
    pass


def positions(n_max=2, k_max=8):
    out = [f'C{k}' for k in range(-k_max, k_max + 1)]
    out += [f'M({tok},{n},{side})' for tok in TOKENS for n in range(1, n_max + 1)
            for side in ('start', 'end')]
    return out


def family(key):
    if key.startswith('M('):
        return key[2:key.index(',')]
    if key[0] == 'C' and key[1] in '-0123456789':
        return 'CPOS'
    return 'CASE' if key in CASES else 'CONST'


GENERATOR_KEYS = positions(n_max=3, k_max=12) + list(CASES) + [repr(c) for c in CONSTS]     # 58
SEED_LANGUAGE = [(f'str:{k}', 'str', k) for k in GENERATOR_KEYS if family(k) not in UNFAMILIAR_FAMILIES]


def resolve(pos, s):
    if pos[0] == 'C':
        k = int(pos[1:])
        i = k if k >= 0 else len(s) + k
        if i < 0 or i > len(s):
            raise PosError(pos)
        return i
    tok, n, side = pos[2:-1].split(',')
    matches = list(TOKENS[tok].finditer(s))
    if int(n) > len(matches):
        raise PosError(pos)
    m = matches[int(n) - 1]
    return m.start() if side == 'start' else m.end()


def eval_row(row, s):
    if row[0] == 'const':
        return row[1]
    out = s[resolve(row[1], s):resolve(row[2], s)]
    op = row[3]
    if op is None:
        return out
    return out.upper() if op == 'upper' else out.lower() if op == 'lower' else out.capitalize()


def run_program(rows, s):
    try:
        return ''.join(eval_row(r, s) for r in rows)
    except PosError:
        return None


def row_name(row):
    if row[0] == 'const':
        return repr(row[1])
    inner = f'Sub({row[1]},{row[2]})'
    return inner if row[3] is None else f'{row[3]}({inner})'


def row_keys(row):
    if row[0] == 'const':
        return (repr(row[1]),)
    return (row[1], row[2]) + ((row[3],) if row[3] else ())


def rows_from(keys):
    """Every row the keys can build."""
    pos = [k for k in keys if family(k) in POSITION_FAMILIES]
    cases = [k for k in keys if family(k) == 'CASE']
    out = [('const', literal_eval(k)) for k in keys if family(k) == 'CONST']
    for a in pos:
        for b in pos:
            if a != b:
                out.append(('sub', a, b, None))
                out += [('sub', a, b, c) for c in cases]
    return out


# -- inputs and worlds --------------------------------------------------------

def _name(rng):
    return f'{rng.choice(FIRST)} {rng.choice(LAST)}'


def _name_mid(rng):
    return f'{rng.choice(FIRST)} {rng.choice(FIRST)} {rng.choice(LAST)}'


def _date_iso(rng):
    return f'{rng.randint(2000, 2030):04d}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}'


def _date_slash(rng):
    return f'{rng.randint(1, 28):02d}/{rng.randint(1, 12):02d}/{rng.randint(2000, 2030)}'


def _code(rng):
    head = ''.join(rng.choice('ABCDEFGH') for _ in range(3))
    return f'{head}-{rng.randint(1000, 9999)}'


def _email(rng):
    return f'{rng.choice(FIRST).lower()}.{rng.choice(LAST).lower()}@example.com'


SAMPLERS = (_name, _name_mid, _date_iso, _date_slash, _code, _email)


def sample_input(rng):
    return rng.choice(SAMPLERS)(rng)


class StringArea(Area):
    """Worlds of string tasks over a hidden set of 14 keys from three key
    families; pools as in the mechanism area."""
    pools = ('trained', 'untrained', 'unfamiliar')

    def __init__(self, seed, env_seed=7, untrained_share=.2, unfamiliar_share=.25):
        self.seed = seed
        self.name = f'str{env_seed}'
        self.spec = {'kind': 'string', 'env_seed': env_seed}
        rng = random.Random(seed * 7919 + env_seed)
        self.by_family = {f: [k for k in GENERATOR_KEYS if family(k) == f] for f in FAMILIES}
        triples = list(itertools.combinations(FAMILIES, 3))
        known = [t for t in triples if not set(t) & set(UNFAMILIAR_FAMILIES)]
        rng.shuffle(known)
        cut = max(1, round(untrained_share * len(known)))
        self.triples = {'untrained': known[:cut], 'trained': known[cut:],
                        'unfamiliar': [t for t in triples if set(t) & set(UNFAMILIAR_FAMILIES)]}
        self.unfamiliar_share = unfamiliar_share
        self.seed_language = list(SEED_LANGUAGE)

    def _keys(self, triple, rng):
        keys = [k for f in triple for k in self.by_family[f]]
        while True:
            chosen = rng.sample(keys, KEYS_PER_WORLD) if len(keys) > KEYS_PER_WORLD else list(keys)
            if sum(family(k) in POSITION_FAMILIES for k in chosen) >= 2:
                return chosen

    @staticmethod
    def _program(keys, rng):
        pos = [k for k in keys if family(k) in POSITION_FAMILIES]
        cases = [k for k in keys if family(k) == 'CASE']
        consts = [k for k in keys if family(k) == 'CONST']
        rows = []
        for _ in range(rng.randint(1, 3)):
            r = rng.random()
            if consts and r < .25:
                rows.append(('const', literal_eval(rng.choice(consts))))
            else:
                a, b = rng.sample(pos, 2)
                rows.append(('sub', a, b, rng.choice(cases) if cases and r >= .85 else None))
        return rows

    def _tasks(self, keys, rng, count=STREAM):
        out, tries = [], 0
        while len(out) < count:
            tries += 1
            if tries > count * 200:
                raise RuntimeError('cannot fill a world from %r' % (keys,))
            prog = self._program(keys, rng)
            seen = {}
            for _ in range(60):
                s = sample_input(rng)
                if s in seen:
                    continue
                o = run_program(prog, s)
                if not o or o == s:
                    continue
                seen[s] = o
                if len(seen) == VISIBLE + HIDDEN:
                    break
            if len(seen) < VISIBLE + HIDDEN:
                continue
            pairs = list(seen.items())
            out.append({'visible': pairs[:VISIBLE], 'hidden': pairs[VISIBLE:]})
        return out

    def draw(self, pool, count, rng):
        out = []
        for _ in range(count):
            keys = self._keys(rng.choice(self.triples[pool]), rng)
            out.append({'pool': pool, 'tasks': self._tasks(keys, rng)})
        return out

    def life_draw(self, count, rng):
        unfamiliar = round(count * self.unfamiliar_share)
        return self.draw('trained', count - unfamiliar, rng) + self.draw('unfamiliar', unfamiliar, rng)


# -- the agent inside a worker ------------------------------------------------

_S = {}


def init_string(language, labels, prior_sets, tiebreak, budget):
    atoms = [a for a in language if a[1] == 'str']
    keys = [a[2] for a in atoms]
    names = [a[0] for a in atoms]
    index = {k: i for i, k in enumerate(keys)}
    by_name = {a[0]: index[a[2]] for a in atoms}
    rows = rows_from(keys)
    rk = [np.array([index[k] for k in row_keys(r)]) for r in rows]
    incidence = np.zeros((len(rows), len(keys)))
    for i, r in enumerate(rk):
        incidence[i, r] = 1.
    tie = [random.Random(f'{tiebreak}:{row_name(r)}').random() for r in rows]   # stable as the language changes
    prior = None
    if prior_sets:
        sets = [[by_name[n] for n in s if n in by_name] for s in prior_sets]
        sets = [s for s in sets if s]
        if sets:
            n = len(keys)
            count, cooc = np.zeros(n), np.zeros((n, n))
            for s in sets:
                count[s] += 1
                cooc[np.ix_(s, s)] += 1
            prior = {'appearance': np.log(FLOOR + count / len(sets)),
                     'log_cond': np.log(FLOOR + cooc / np.maximum(count, 1)[None, :])}
    groups = None
    if labels:
        groups = np.array([labels.get(nm, -1) for nm in names])
        if (groups >= 0).sum() < 3:
            groups = None
    _S.update(keys=keys, names=names, rows=rows, rk=rk, tie=np.array(tie), incidence=incidence,
              prior=prior, groups=groups, budget=budget)


def key_terms(s, evidence):
    """Per-key score: what this world has shown, what the prior says follows
    from it, and what the area model's groups say."""
    n = len(evidence)
    if not evidence.any():
        return s['prior']['appearance'] if s['prior'] is not None else np.zeros(n)
    terms = np.log(FLOOR + np.minimum(evidence, 1.))
    if s['prior'] is not None:
        terms = terms + s['prior']['log_cond'] @ (evidence / evidence.sum())
    if s['groups'] is not None:
        g = s['groups']
        mass = np.bincount(g[g >= 0], weights=evidence[g >= 0], minlength=int(g.max()) + 1)
        total = mass.sum()
        if total > 0:
            share = np.log(FLOOR + mass / total)
            model = np.full(n, float(share.mean()))
            model[g >= 0] = share[g[g >= 0]]
            terms = terms + model
    return terms


def programs(outs, targets, limit):
    """Programs of up to three rows in the given order that reproduce the
    visible outputs, each with the scan count at which it was found; the
    first row of a longer program must leave something to complete. `limit`
    is a one-element list the caller may lower."""
    n, scans = len(outs), 0
    for i in range(n):
        scans += 1
        if outs[i] == targets:
            yield (i,), scans
        if scans >= limit[0]:
            return
    pre = [i for i in range(n) if all(t.startswith(o) and len(o) < len(t) for o, t in zip(outs[i], targets))]
    rem = {i: [t[len(o):] for o, t in zip(outs[i], targets)] for i in pre}
    for i in pre:
        r = rem[i]
        for j in range(n):
            scans += 1
            if outs[j] == r:
                yield (i, j), scans
            if scans >= limit[0]:
                return
    for i in pre:
        r = rem[i]
        for j in range(n):
            if not all(t.startswith(o) and len(o) < len(t) for o, t in zip(outs[j], r)):
                continue
            r2 = [t[len(o):] for o, t in zip(outs[j], r)]
            for k in range(n):
                scans += 1
                if outs[k] == r2:
                    yield (i, j, k), scans
                if scans >= limit[0]:
                    return


def compatible(rows, visible, inside=None):
    """Rows (within `inside`) whose output on every visible input is a
    non-empty part of the target: the free consistency test, as the mask test
    is elsewhere."""
    out = []
    for i in (range(len(rows)) if inside is None else inside):
        row = rows[i]
        outs = []
        for inp, tgt in visible:
            try:
                o = eval_row(row, inp)
            except PosError:
                break
            if not o or o not in tgt:
                break
            outs.append(o)
        else:
            out.append((i, outs))
    return out


def search(scored, targets, budget, keys_of):
    """The first program in the coach's order within the budget, and whether
    no program over other keys followed within CONFIRM scans."""
    limit = [budget]
    first = None
    for sol, scans in programs([o for _, o in scored], targets, limit):
        rows = tuple(scored[i][0] for i in sol)
        if first is None:
            first = rows
            limit[0] = min(budget, scans + CONFIRM)
        elif keys_of(rows) != keys_of(first):
            return first, False
    return first, True


def life_string(job):
    index, tasks, _rng_seed = job
    s = _S
    rows, rk, names = s['rows'], s['rk'], s['names']
    evidence = np.zeros(len(s['keys']))
    hits, picks, confident, unsolved = 0, {}, set(), []

    def keys_of(prog):
        return frozenset(k for i in prog for k in rk[i].tolist())

    window = terms = None
    for task in tasks:
        visible = task['visible']
        targets = [o for _, o in visible]
        fresh = key_terms(s, evidence)
        if terms is None or not np.array_equal(fresh, terms):
            terms = fresh
            score = s['incidence'] @ terms
            window = np.lexsort((s['tie'], -score))[:s['budget']]   # the rows the budget admits, in order
        comp = compatible(rows, visible, window)
        if not comp:
            unsolved.append(visible)
            continue
        found, sure = search(comp, targets, s['budget'], keys_of)
        if found is None:
            unsolved.append(visible)
            continue
        prog = [rows[i] for i in found]
        hits += all(run_program(prog, inp) == out for inp, out in task['hidden'])
        for k in keys_of(found):
            evidence[k] += 1.
            picks[names[k]] = picks.get(names[k], 0) + 1
            if sure:
                confident.add(names[k])
    return {'index': index, 'hits': int(hits), 'picks': picks, 'confident': sorted(confident),
            'unsolved': unsolved, 'stuck': len(unsolved)}


# -- invention ----------------------------------------------------------------

def candidates_string(language):
    """Keys the language lacks: the generator's positions and beyond them
    (fourth matches, offsets to 16), the case operations and the constants."""
    have = {a[2] for a in language if a[1] == 'str'}
    pool = positions(n_max=4, k_max=16) + list(CASES) + [repr(c) for c in CONSTS]
    return [k for k in pool if k not in have]


def _solves_with(rows, required, visible, budget):
    comp = compatible(rows, visible)
    if not comp:
        return False
    comp.sort(key=lambda c: c[0] not in required)      # the new rows first
    targets = [o for _, o in visible]
    for sol, _ in programs([o for _, o in comp], targets, [budget]):
        if any(comp[i][0] in required for i in sol):
            return True
    return False


def extend_string(seed, worlds, records, share=.3, cap=40, budget=256):
    """Candidate keys for the worlds with the most unsolved tasks: a key the
    language lacks that, with what the world earned, completes a program for
    at least two of the world's unsolved tasks on their visible examples."""
    language = seed.state['language']
    cands = candidates_string(language)
    stuck = np.array([r['stuck'] for r in records])
    cut = max(.15 * STREAM, float(np.quantile(stuck, 1 - share)))
    new, tests, provenance = {}, 0, []
    for w, r in zip(worlds, records):
        if r['stuck'] < cut:
            continue
        earned = [a[2] for a in language if a[1] == 'str' and a[0] in r['picks']]
        base = rows_from(earned)
        for c in cands:
            if c in new:
                continue
            rows = rows_from(earned + [c])
            required = {i for i, row in enumerate(rows) if c in row_keys(row)}
            if not required:
                continue
            explained = 0
            for visible in r['unsolved']:
                tests += 1
                explained += _solves_with(rows, required, visible, budget)
                if explained >= 2:
                    break
            if explained >= 2 and len(new) < cap:
                new[c] = (f'inv:str:{c}', 'str', c)
                provenance.append({'atom': f'inv:str:{c}', 'pool': w['pool'], 'stuck': int(r['stuck'])})
    seed.state['resource']['invention_tests'] += tests
    return list(new.values()), tests, provenance
