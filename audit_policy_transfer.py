"""Independently replay bank generation, candidates, labels and frozen policy decisions."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from rsi.common import ROOT, digest, verify_journal, write_json
from rsi.retention_run import file_hash
from rsi.semantic_invention import evaluate_program
from stitch_ten import source_candidates
from run_policy_transfer import ARMS, FROZEN, SETS, banks_for, evolve, score


def audit(output):
    output = Path(output)
    read = lambda name: json.loads((output / name).read_text(encoding="utf-8"))
    assert not (output / "FAILED.json").exists()
    sealed = read("artifact_manifest.json")
    present = {path.relative_to(output).as_posix() for path in output.rglob("*") if path.is_file()}
    assert present - {"artifact_manifest.json", "audit.json"} == set(sealed)
    for name, row in sealed.items():
        assert file_hash(output / name) == row["sha256"] and (output / name).stat().st_size == row["bytes"], name
    for name, sha in read("source_manifest.json").items():
        assert file_hash(output / "source" / name) == sha, name
    cfg = read("config.json")
    banks = banks_for(cfg)
    assert digest(banks) == digest(read("protected_banks.json"))
    events = [json.loads(line) for line in (output / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    assert verify_journal(output / "events.jsonl") == len(events)
    assert events[-1]["kind"] == "completed"
    assert next(i for i, e in enumerate(events) if e["kind"] == "policies_frozen") < next(
        i for i, e in enumerate(events) if e["kind"] == "transfer_scored")
    assert all(next(i for i, e in enumerate(events) if e["kind"] == "policies_frozen") < i
               for i, e in enumerate(events) if e["kind"] == "transfer_labels_opened")
    pools = read("candidate_pools.json")
    pretransfer = read("candidate_pools_pretransfer.json")
    checked = 0
    for split, tasks in banks.items():
        for task in tasks:
            public = {"id": task["id"], "visible": task["visible"]}
            expected = []
            for arm in ARMS:
                rows = source_candidates(public, arm, {}, cfg["candidate_cap_per_arm"])
                for row in rows:
                    row["oracle_correct"] = bool(evaluate_program(row["program"], task["visible"] + task["hidden"]))
                expected += rows
                checked += 1
            assert digest(pools[task["id"]]) == digest(expected), task["id"]
            if split.startswith("transfer_"):
                assert all("oracle_correct" not in row for row in pretransfer[task["id"]])
                assert digest(pretransfer[task["id"]]) == digest([
                    {key: value for key, value in row.items() if key != "oracle_correct"} for row in expected])
            else:
                assert digest(pretransfer[task["id"]]) == digest(expected)
    result = read("results.json")
    for index, (name, allowed) in enumerate(SETS.items()):
        policy = result["policies"][name]
        assert tuple(policy["arms"]) == allowed
        genome, trace = evolve(banks["development"], pools, allowed, cfg, cfg["meta_seed"] + index)
        assert digest(policy["evolved_weights"]) == digest(genome)
        assert digest(policy["trace"]) == digest(trace)
        for split in ("development", "admission"):
            for mode, weights in (("frozen", FROZEN), ("evolved", genome)):
                assert digest(policy[split][mode]) == digest(score(banks[split], pools, allowed, weights))
        admitted = policy["admission"]["evolved"]["correct"] >= policy["admission"]["frozen"]["correct"]
        assert policy["admitted"] == admitted
        selected = genome if admitted else FROZEN
        assert digest(policy["selected_weights"]) == digest(selected)
        for split in banks:
            if not split.startswith("transfer_"):
                continue
            for mode, weights in (("frozen", FROZEN), ("evolved", genome), ("selected", selected)):
                assert digest(result["transfer"][split][name][mode]) == digest(score(banks[split], pools, allowed, weights))
    assert events[-1]["payload"]["sha256"] == digest(result)
    report = {"status": "passed", "artifacts_hashed": len(sealed), "journal_events": len(events),
              "task_count": sum(map(len, banks.values())), "candidate_generations_replayed": checked,
              "policy_modes_recomputed": len(SETS) * (4 + 3 * len(cfg["transfer_seeds"])),
              "scope": "semantic transfer lane only; V86 not pooled"}
    write_json(output / "audit.json", report)
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    args = ap.parse_args()
    print(json.dumps(audit(ROOT / args.run), indent=2))
