"""How many distinct worlds the two metric areas hold, and how many of the
evaluation worlds the agent had already lived. A metric world is one centre atom
and its nearest atoms under a fixed weighting, so an area holds only as many
worlds as it has valid centres. World draws only, no scoring, except that the
growth on never-lived centres is read from the second draw's saved hits.
Writes analysis/review002-metric-coverage.json (about two minutes)."""
import json

from rsi.common import ROOT, write_json
from rsi.seed import STREAM, make_area
from rsi.seed_areas import MetricArea
from second_draw import HITS, PER_POOL, SALT
from summarize_arms import TAGS

AREAS = ('metric777001', 'metric555001')
LIFE_WORLDS = 96   # confirm_seed.sh


class Traced(MetricArea):
    """MetricArea whose worlds carry their centre and nothing else; it draws
    from the generator exactly as MetricArea._worlds does."""

    def _worlds(self, pool, count, rng):
        centres, out = self.centres[pool], []
        while len(out) < count:
            centre = centres[rng.randrange(len(centres))]
            members = self._members(centre)
            if members is None:
                continue
            members = list(members)
            rng.shuffle(members)
            out.append({'stream': members[:STREAM], 'centre': centre})
        return out

    def draw(self, pool, count, rng):
        return [{'pool': pool, 'centre': (pool, w['centre']), 'stream': w['stream']} for w in self._worlds(pool, count, rng)]


def main():
    hits = json.loads(HITS.read_text())['hits']
    out, never = {}, {'worlds': 0, 'start': 0, 'full': 0}
    lived_too = dict(never)
    for tag in TAGS:
        states = {arm: json.loads((ROOT / f'seeds/{arm}_{tag}/state.json').read_text()) for arm in ('full', 'matched')}
        seed = states['full']['seed']
        for name in AREAS:
            area = Traced(seed, weight_seed=int(name.removeprefix('metric')))
            plain, traced = make_area(name, seed).held_out(PER_POOL, salt=SALT), area.held_out(PER_POOL, salt=SALT)
            masks = area.full.catalog.masks
            assert all(p['masks'] == [masks[m] for m in t['stream']] for p, t in zip(plain, traced)), 'Traced drew other worlds'
            row = {'valid_centres': sum(area._members(c) is not None for cs in area.centres.values() for c in cs)}
            for arm, state in states.items():
                lives = sum(e['op'] == 'live' and e['area'] == name for e in state['ledger'])
                lived = {w['centre'] for life in range(lives) for w in area.life_worlds(life, LIFE_WORLDS)}
                was_lived = [w['centre'] in lived for w in traced]
                row[arm] = {'lives': lives, 'lived_centres': len(lived),
                            'first_draw_lived': sum(w['centre'] in lived for w in area.held_out(PER_POOL, salt=999)),
                            'second_draw_lived': sum(was_lived), 'evaluation_worlds': len(traced)}
                if arm == 'full':   # growth on worlds whose centre full never lived, against the rest
                    for known, start, carried in zip(was_lived, hits[f'start/{tag}/{name}'], hits[f'full/{tag}/{name}']):
                        group = lived_too if known else never
                        group['worlds'] += 1
                        group['start'] += start
                        group['full'] += carried
            out[f'{tag}/{name}'] = row
            print(tag, name, row, flush=True)
    result = {'salt': SALT, 'areas': out, 'full_on_never_lived_centres': never, 'full_on_lived_centres': lived_too}
    write_json(ROOT / 'analysis/review002-metric-coverage.json', result)
    print(never, lived_too)


if __name__ == '__main__':
    main()
