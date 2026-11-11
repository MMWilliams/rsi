"""Does this machine draw the worlds the paper's runs drew? Prints one digest per
area for random seed 919127 and compares it with the reference platform's
(Windows 11 x86-64, CPython 3.12.9, NumPy 2.5.3). The two metric areas depend on
the last bits of numpy.fft.rfft and on how numpy.argsort orders equal distances,
and differ on Linux with the same versions; where a digest differs, a rerun is a
statistical replication of that area and not an exact one. About 15 seconds."""
import hashlib
import json
import sys

import numpy as np

from rsi.seed import KEYS_PER_WORLD, make_area

REFERENCE = {'metric777001': '72e10c5b15cf', 'metric555001': '64689d069d86', 'mech': '27d49b5f4fc6', 'drawn7': 'f0257768d10d',
             'drawn11': '807aedf53925', 'drawn13': 'fea4aa90bfa0', 'str7': 'd5b4a2708d08'}


def digest(value):
    return hashlib.sha256(json.dumps(value).encode()).hexdigest()[:12]


def main():
    differing = []
    for name, reference in REFERENCE.items():
        area = make_area(name, 919127)
        out = {}
        if name.startswith('metric'):   # each centre's nearest keys define the area's worlds
            distance = lambda c: (((area.latent - area.latent[c]) ** 2) * area.weights).sum(axis=1)
            out['centre_keys'] = [sorted(area.full.key_names[i] for i in np.argsort(distance(c))[:KEYS_PER_WORLD])
                                  for c in range(area.latent.shape[0])]
        out['fresh_worlds'] = [digest(w.get('masks') or w.get('tasks')) for w in area.held_out(24, salt=999)]
        mine = digest(out)
        print(f'{name:13s} {mine}  {"same" if mine == reference else "DIFFERS from " + reference}')
        differing += [name] * (mine != reference)
    return len(differing)


if __name__ == '__main__':
    sys.exit(main())
