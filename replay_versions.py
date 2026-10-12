"""Score one area's fresh held-out set (24 worlds per pool, salt 999, the
set seed_check.py uses) with the state after each kept change, to see how
changes made anywhere moved that area. Usage: replay_versions.py <name>
<area> [v1,v2,...]; default: the start and every kept version."""
import json
import pathlib
import sys
import warnings

from rsi.seed import Seed, make_area

ROOT = pathlib.Path(__file__).resolve().parent


def main():
    warnings.filterwarnings('ignore')
    name, area_name = sys.argv[1], sys.argv[2]
    seed = Seed(ROOT / 'seeds' / name)
    area = make_area(area_name, seed.state['seed'])
    fresh = area.held_out(24, salt=999)
    changes = {k['version']: f"{k['area']} {k['change']}" for k in seed.state['kept']}
    versions = [int(v) for v in sys.argv[3].split(',')] if len(sys.argv) > 3 else [0] + sorted(changes)
    for v in versions:
        snap = json.loads((seed.path / 'versions' / f'{v}.json').read_text())
        st = seed.candidate()
        st['language'] = snap['language']
        st['areas'] = snap['areas']
        st['inventions'] = snap['inventions']
        st['experience'] = st['experience'][:snap['experience_len']]
        if v == 0:
            st['language'] = st['initial_language']
            st['areas'] = {area.name: {'model': None, 'prior': False, 'held_out_score': None}}
        out = seed.score(seed.run(fresh, 1024, area.name, state=st), fresh, 1024)
        print(v, out['total'], len(st['language']), changes.get(v, 'start'), flush=True)


if __name__ == '__main__':
    main()
