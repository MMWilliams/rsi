"""The arms of the review's ablation and proof-cost comparisons: the seed with
one part removed or one rule changed. The frozen v11.1 code (rsi/seed.py,
seed_run.py) is imported and never edited, so its hashes keep holding.
"""
from __future__ import annotations

import numpy as np

from . import seed as seed_module
from . import seed_string
from .seed import STREAM, Seed

MINIMUM_EXPERIENCE = 48   # Seed.reflect's own minimum

_plain_init, _plain_string = seed_module._init, seed_string.init_string


def independent(appearance):
    """A pair table in which a row's score is only how often its atoms were
    earned: pairs are products, single atoms keep their own frequency."""
    pair = np.outer(appearance, appearance)
    np.fill_diagonal(pair, appearance)
    return pair


def init_frequency(*args):
    _plain_init(*args)
    state = seed_module._STATE
    if state['prior'] is not None:
        state['prior']._derive(state['h'], independent(state['prior'].appearance))


def init_string_frequency(*args):
    _plain_string(*args)
    prior = seed_string._S['prior']
    if prior is not None:   # the evidence shares sum to one, so a key scores its own frequency
        prior['log_cond'] = np.tile(prior['appearance'][:, None], (1, len(prior['appearance'])))


def use_arm(arm):
    """The frequency arm changes what the workers build, so this must be in
    force in every process that scores one of its states."""
    if arm == 'frequency':
        seed_module._init, seed_string.init_string = init_frequency, init_string_frequency


class NoGuidance(Seed):
    def reflect(self, area, **options):
        return None


class Frequency(Seed):
    def reflect(self, area, **options):
        lived = self.experience_count(area)
        if lived < MINIMUM_EXPERIENCE:
            return None
        # no groups are fitted: empty labels leave the workers on the plain simulator
        return {'labels': {}, 'groups': 0, 'per_world': 3, 'worlds': lived, 'r': {}}


class NoInvention(Seed):
    def extend(self, worlds, records, cands):
        return [], 0, []

    def prune(self, form, min_lives=2):
        return []


class Settling(Seed):
    def settle(self, area, held_out, salt, candidate, change, note, carried, new, kept):
        """Record a verdict and apply it, as the end of Seed.prove does; that
        method cannot be split without changing the frozen file's hash."""
        entry = {'life': self.lives(area.name) - 1, 'area': area.name, 'op': 'prove', 'change': change, 'salt': salt,
                 'carried': carried, 'candidate': new, 'kept': kept, 'experience_len': len(self.state['experience']),
                 'note': note}
        self.state['ledger'].append(entry)
        if kept:
            self._snapshot()
            for key in ('language', 'areas', 'inventions'):
                self.state[key] = candidate[key]
            self.state['version'] += 1
            entry['version_after'] = self.state['version']
            self._snapshot()
            new.update(version=self.state['version'], salt=salt, size=len(held_out),
                       experience=self.experience_count(area.name))
            self.area_state(area.name)['held_out_score'] = new
            self.state['kept'].append({'life': entry['life'], 'area': area.name, 'change': change,
                                       'gain': new['total'] - carried['total'], 'version': self.state['version']})
        self.save()
        return kept, carried, new, {}


class AcceptAll(Settling):
    def prove(self, area, held_out, salt, candidate, budget, change, note=None, shared=False):
        return self.settle(area, held_out, salt, candidate, change, note,
                           {'total': 0, 'by_pool': {}}, {'total': 0, 'by_pool': {}}, True)


class Point(Settling):
    def prove(self, area, held_out, salt, candidate, budget, change, note=None, shared=False):
        half = held_out[::2]
        carried = self._carried(area, half, salt, budget)
        records = self.run(half, budget, area.name, state=candidate)
        self.state['resource']['proof_scans'] += len(half) * STREAM * budget
        new = self.score(records, half, budget)
        new.update(hits=[r['hits'] for r in records], worlds=len(half))
        return self.settle(area, half, salt, candidate, change, note, carried, new, new['total'] > carried['total'])


ARMS = {'full': Seed, 'no-guidance': NoGuidance, 'frequency': Frequency, 'no-invention': NoInvention,
        'accept-all': AcceptAll, 'point': Point, 'matched': AcceptAll}   # matched differs only in its schedule
