"""Second independent replication of the complexity-improver confirmation.

The reporting rule in `EXPERIMENT-complexity-improver-confirmation.md` requires
C1 and C2 to pass on two independent frozen replications with passing audits
before reliable improver growth is claimed. This reuses replication one's
generator, action set, router fitting, controls and gates without modification,
changing only the seeds.
"""
from __future__ import annotations

import sys

import complexity_improver_confirmation as conf
from rsi.common import ROOT


DEST = ROOT / 'runs/complexity-improver-confirmation-rep2-20260920'
PANELS = {'history_a': tuple(range(913100, 913112)),
          'history_b': tuple(range(913200, 913212)),
          'transfer': tuple(range(913300, 913312))}


def install():
    conf.DEST = DEST
    conf.PANELS = PANELS


if __name__ == '__main__':
    install()
    {'prepare': conf.prepare, 'score': conf.score,
     'improver': conf.improver}[sys.argv[1]]()
