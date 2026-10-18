"""Re-execute c21's losing branch b of the drawn7 patience test (ledger entry
37), whose meta-proof the v11 auditor could not replay from snapshots: b kept
nothing in either of its two lives, so its state entering its second life is
the loser snapshot's language and models with the experience shared up to
drawn7 life 1. Re-live that life on a scratch copy, score b on the meta set,
and write b's own experience to the given file. Usage: python
analysis/c21_meta1_reexecution.py <scratch dir> <tail.json>"""
import json
import pathlib
import sys

sys.path.insert(0, '.')
from rsi.seed import Seed, make_area


def main():
    src = json.load(open('seeds/c21/state.json'))
    e = src['ledger'][37]
    loser = json.load(open('seeds/c21/versions/' + e['loser_snapshot']))
    tmp = pathlib.Path(sys.argv[1])
    tmp.mkdir(parents=True, exist_ok=True)
    shared = e['experience_len'] - 96          # the winner's second life added 96 worlds
    st = dict(src, ledger=src['ledger'][:27], experience=src['experience'][:shared],
              language=loser['language'], inventions=loser['inventions'],
              areas={k: dict(v, held_out_score=None) for k, v in loser['areas'].items()})
    (tmp / 'state.json').write_text(json.dumps(st))
    seed = Seed(tmp)
    area = make_area(st['areas']['drawn7']['spec'], src['seed'])
    life, _, _ = seed.live(area, 96, e['budget'])
    print('b life', life, 'solved', seed.state['ledger'][-1]['total'], '(log 1569)')
    held = area.held_out(e['meta']['worlds'] // len(area.pools), salt=e['meta']['salt'])
    hb = [r['hits'] for r in seed.run(held, e['budget'], area.name)]
    print('b on the meta set', sum(hb), 'recorded', e['meta']['b'], 'every world equal', hb == e['meta']['hb'])
    pathlib.Path(sys.argv[2]).write_text(json.dumps({'experience_from': shared,
                                                     'experience_tail': seed.state['experience'][shared:]}))


if __name__ == '__main__':
    main()
