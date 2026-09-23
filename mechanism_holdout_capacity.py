"""Mechanism holdout at three evaluator capacities.

`mechanism_holdout_verifier.py` showed the 60-leaf pooled evaluator is worse
than E0 on every held-out family. This reruns the same leave-one-family-out
design at 15, 60 and 120 leaves to ask whether larger evaluators overfit
families more. If held-out regression grows with capacity, "a larger model is a
better evaluator" is itself family-bound.

Usage: python mechanism_holdout_capacity.py <leaves>
"""
from __future__ import annotations

import sys

import mechanism_holdout_verifier as base
from rsi.common import ROOT


if __name__ == '__main__':
    leaves = int(sys.argv[1])
    base.LEAVES = leaves
    base.OUT = ROOT / f'analysis/mechanism-holdout-verifier-leaves{leaves}-20260921.json'
    base.main()
