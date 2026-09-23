"""Second replication of the frozen construction-improver confirmation.

Seeds 917xxx. No rule, threshold, window scheme or gate is changed.
"""
from __future__ import annotations

import sys

import construction_improver_confirmation as conf
from rsi.common import ROOT

DEST = ROOT / 'runs/construction-improver-confirmation-rep2-20260921'
PANELS = {'history_a': tuple(range(917100, 917112)),
          'history_b': tuple(range(917200, 917212)),
          'transfer': tuple(range(917300, 917312))}


def install():
    conf.DEST = DEST
    conf.PANELS = PANELS


if __name__ == '__main__':
    install()
    {'prepare': conf.prepare, 'cache': conf.cache,
     'improver': conf.improver}[sys.argv[1]]()
