"""V82: discover a balanced rotate body, then transfer it cross-family."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from run_credit_lineage_v80 import run as run_credit_lineage


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--bank-seed", type=int, default=2026100501)
    parser.add_argument("--generations", type=int, default=2)
    parser.add_argument("--training-tasks", type=int, default=48)
    parser.add_argument("--development-tasks", type=int, default=24)
    parser.add_argument("--admission-tasks", type=int, default=24)
    parser.add_argument("--final-tasks", type=int, default=24)
    parser.add_argument("--visible-examples", type=int, default=40)
    parser.add_argument("--hidden-examples", type=int, default=13)
    parser.add_argument("--max-macros", type=int, default=16)
    parser.add_argument("--max-library", type=int, default=24)
    parser.add_argument("--min-support", type=int, default=2)
    parser.add_argument("--max-children-per-task", type=int, default=4)
    parser.add_argument("--max-variants", type=int, default=64)
    args = parser.parse_args()
    args.seed_identity = True
    args.reserve_rotate = True
    args.families = {"train": "novel_operator_transition", "development": "novel_operator_transition",
                     "admission": "stack_transition", "final": "stack_transition"}
    args.bank_counts = {"train": args.training_tasks, "development": args.development_tasks,
                        "admission": args.admission_tasks, "final": args.final_tasks}
    print(json.dumps(run_credit_lineage(vars(args), Path(args.output)), indent=2))
