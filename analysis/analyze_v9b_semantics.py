"""Characterize V9b's saved published-interpreter versus strict-oracle mismatch."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from audit_results import published_correct
from rsi.oracle import correct as oracle_correct, outcomes as oracle_outcomes
from rsi.common import digest
from dsl import PosError, run as published_run
from parse import ParseError, parse


def first_program(value):
    return value.strip().splitlines()[0] if value and value.strip() else ""


def published_outcomes(program, examples):
    try:
        parsed = parse(program)
    except (ParseError, ValueError, TypeError, RecursionError, AttributeError):
        return [None for _ in examples]
    values = []
    for text, _ in examples:
        try:
            values.append(published_run(parsed, text))
        except (PosError, ValueError, TypeError, OverflowError, RecursionError):
            values.append(None)
    return values


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run", type=Path)
    ap.add_argument("output", type=Path)
    args = ap.parse_args()
    files = sorted((args.run / "samples").glob("*.json"))
    bank_payload = json.loads((args.run / "protected_banks.json").read_text(encoding="utf-8"))
    task_bank = {}
    for rows in bank_payload.values():
        for task in rows:
            task_bank[task["id"]] = task
    total = 0
    correctness = Counter()
    behavior = Counter()
    patterns = Counter()
    examples = []
    by_split = Counter()
    by_label = Counter()
    for path in files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        request = payload["request"]
        tasks = {task["id"]: task_bank[task["id"]] for task in request["tasks"]}
        split = request.get("split", "unknown")
        label = path.stem
        for task_id, raw_outputs in payload["outputs"].items():
            task = tasks[task_id]
            full = task["visible"] + task["hidden"]
            for raw in raw_outputs:
                total += 1
                program = first_program(raw)
                pc = published_correct(program, full)
                oc = oracle_correct(program, full)
                key = (int(pc), int(oc))
                correctness[key] += 1
                by_split[(split, key)] += 1
                by_label[(label, key)] += 1
                po = published_outcomes(program, task["visible"])
                oo = oracle_outcomes(program, task["visible"])
                if po != oo:
                    behavior["vector_disagreement"] += 1
                    if digest(po) != digest(oo):
                        behavior["digest_disagreement"] += 1
                    if len(examples) < 20:
                        examples.append({"file": path.name, "task_id": task_id,
                                         "program": program, "published": po, "oracle": oo,
                                         "published_correct": pc, "oracle_correct": oc})
                    if "End" in program:
                        patterns["contains_upper_End"] += 1
                    else:
                        patterns["other"] += 1
    result = {
        "status": "characterization_only",
        "run": str(args.run),
        "sample_files": len(files),
        "raw_outputs": total,
        "correctness_contingency_published_oracle": {f"{p}/{o}": n for (p, o), n in sorted(correctness.items())},
        "visible_behavior_disagreements": dict(behavior),
        "disagreement_patterns": dict(patterns),
        "by_split": {f"{split}:{p}/{o}": n for (split, (p, o)), n in sorted(by_split.items())},
        "by_label": {f"{label}:{p}/{o}": n for (label, (p, o)), n in sorted(by_label.items())},
        "examples": examples,
        "interpretation": "This posthoc comparison does not alter V9b scores, admission decisions, or the benchmark contract.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("sample_files", "raw_outputs", "correctness_contingency_published_oracle", "visible_behavior_disagreements", "disagreement_patterns")}, indent=2))


if __name__ == "__main__":
    main()
