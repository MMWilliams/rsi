"""Dress rehearsal of the coach confirmation on a development seed.

The simulator bug of `COACH-RESULTS-2026-09-23.md` §9 biased every training run
before it; the procedure the confirmation will run has therefore never run.
This runs `mechanism_coach_confirmation.py` unchanged at full size, one
replication on development seed 627101, into development paths, followed by
its audit. The confirmation's seeds are not touched. Development evidence.
"""
from __future__ import annotations

import sys

import mechanism_coach_confirmation as confirmation
from rsi.common import ROOT

confirmation.OUT = ROOT / 'analysis/mechanism-coach-rehearsal-20260923.json'
confirmation.DEST = ROOT / 'runs/mechanism-coach-rehearsal-20260923'
confirmation.REPLICATIONS = (('dev', 627101),)

if __name__ == '__main__':
    confirmation.main()
    import audit_mechanism_coach_confirmation as audit
    audit.AUDIT = ROOT / 'analysis/audit-mechanism-coach-rehearsal-20260923.json'
    sys.exit(audit.main())
