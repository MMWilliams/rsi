"""Build candidate feature caches for the two routing confirmation runs.

The routing confirmation (`complexity_improver_confirmation.py`) never needed
per-candidate feature matrices because its specialists were trained on separate
source panels. The reviewers' residual-over-default framing requires comparing
the routed system against a capacity-matched pooled model trained on the same
24 history banks, and that comparison needs the matrices. This reuses the
construction runner's `cache` stage pointed at the routing run directories. It
adds `*_cache.npz`, `*_cache.json` and `cache_manifest.json` beside the frozen
artifacts and modifies nothing that any audit hashes.
"""
from __future__ import annotations

import sys

import construction_improver_confirmation as conf
import complexity_improver_confirmation as routing
from rsi.common import ROOT


TARGETS = {
    'rep1': (routing.DEST, routing.PANELS, routing.PROTOCOL),
    'rep2': (ROOT / 'runs/complexity-improver-confirmation-rep2-20260920',
             {'history_a': tuple(range(913100, 913112)),
              'history_b': tuple(range(913200, 913212)),
              'transfer': tuple(range(913300, 913312))},
             routing.PROTOCOL),
}


def install(which):
    dest, panels, protocol = TARGETS[which]
    conf.DEST = dest
    conf.PANELS = panels
    conf.PROTOCOL = protocol


if __name__ == '__main__':
    install(sys.argv[1])
    conf.cache()
