"""Second confirmatory run: EXPERIMENT-mechanism-coach-confirmation-2.md.

Runs `mechanism_coach_confirmation.py` unchanged (its SHA-256 is frozen in both
protocols) with three constants replaced: output paths, the replication seeds,
and the number of validation worlds per kind, 32 → 256, sized from the first
confirmation's validation data. Then runs its audit.
"""
from __future__ import annotations

import sys

import mechanism_coach_confirmation as confirmation
from rsi.common import ROOT

confirmation.OUT = ROOT / 'analysis/mechanism-coach-confirmation2-20260923.json'
confirmation.DEST = ROOT / 'runs/mechanism-coach-confirmation2-20260923'
confirmation.REPLICATIONS = (('A', 961101), ('B', 962101))
confirmation.VALIDATION_WORLDS = 256

if __name__ == '__main__':
    confirmation.main()
    import audit_mechanism_coach_confirmation as audit
    audit.AUDIT = ROOT / 'analysis/audit-mechanism-coach-confirmation2-20260923.json'
    sys.exit(audit.main())
