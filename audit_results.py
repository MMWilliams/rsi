"""Reconcile saved scores against raw generations and the published interpreter."""
import argparse
import json
import math
from pathlib import Path

from rsi.common import digest, verify_journal, write_json
from dsl import PosError, run
from parse import ParseError, parse


def published_correct(text, examples):
    program_text = text.strip().splitlines()[0] if text.strip() else ""
    try:
        program = parse(program_text)
        return all(run(program, inp) == output for inp, output in examples)
    except (ParseError, PosError, ValueError, TypeError, RecursionError, AttributeError):
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run")
    args = parser.parse_args()
    root = Path(args.run)
    results = json.loads((root / "results.json").read_text(encoding="utf-8"))
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    banks = json.loads((root / "protected_banks.json").read_text(encoding="utf-8"))
    bank_meta = json.loads((root / "bank_manifest.json").read_text(encoding="utf-8"))
    for split, rows in banks.items():
        assert digest(rows) == bank_meta[split]["sha256"], f"Changed bank: {split}"
    for name, expected in manifest["source_sha256"].items():
        source = root / "source" / Path(name)
        assert digest(source.read_text(encoding="utf-8")) == expected, f"Changed archived source: {name}"
    final_tasks = {task["id"]: task for task in banks["final"]}
    train_tasks = {task["id"]: task for task in banks["train"]}
    checked_samples = 0
    for checkpoint, score in results["neural"]["scores"].items():
        samples = json.loads((root / "neural_samples" / (checkpoint + ".json")).read_text(encoding="utf-8"))
        for row in score["tasks"]:
            task = final_tasks[row["id"]]
            texts = samples[row["id"]]
            count = sum(published_correct(text, task["visible"] + task["hidden"]) for text in texts)
            assert count == row["correct"], f"Interpreter/score disagreement: {checkpoint}/{row['id']}"
            assert len(texts) == row["n"]
            for k, measured in row["pass_at_k"].items():
                k = int(k)
                expected = 1 - (math.comb(len(texts) - count, k) / math.comb(len(texts), k) if len(texts) - count >= k else 0)
                assert math.isclose(expected, measured, abs_tol=1e-12)
            checked_samples += len(texts)
        for k, mean in score["pass_at_k"].items():
            assert math.isclose(mean, sum(row["pass_at_k"][k] for row in score["tasks"]) / len(score["tasks"]), abs_tol=1e-12)
    trajectories = 0
    for path in (root / "verified_trajectories").glob("*.json"):
        for row in json.loads(path.read_text(encoding="utf-8")):
            task = train_tasks[row["task_id"]]
            assert row["oracle_correct"] is True and published_correct(row["program"], task["visible"] + task["hidden"]), path.name
            trajectories += 1
    audit = {"source_snapshot_hashes": "passed", "bank_hashes": "passed", "journal_events": verify_journal(root / "events.jsonl"),
             "raw_samples_regraded_with_published_interpreter": checked_samples,
             "verified_training_trajectories_rechecked": trajectories, "pass_at_k_reconciliation": "passed"}
    write_json(root / "audit.json", audit)
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
