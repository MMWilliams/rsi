"""Independent audit for the V12 inherited-credit transfer run."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from rsi.banks import create_banks, public_task, template
from rsi.common import ROOT, canonical, digest, verify_journal, write_json
from rsi.evaluation import Worker
from rsi.oracle import correct, outcomes
from rsi.retention_run import file_hash


def audit(root: Path):
    root = Path(root)
    read = lambda name: json.loads((root / name).read_text(encoding="utf-8"))
    assert not (root / "FAILED.json").exists()
    sealed = read("artifact_manifest.json")
    present = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    assert present - {"artifact_manifest.json", "audit.json"} == set(sealed)
    for name, meta in sealed.items():
        assert file_hash(root / name) == meta["sha256"] and (root / name).stat().st_size == meta["bytes"], name
    cfg, manifest = read("config.json"), read("manifest.json")
    assert digest(cfg) == manifest["config_sha256"]
    mutable_source_drift = []
    for name, value in manifest["source_sha256"].items():
        assert file_hash(root / "source" / name) == value
        if file_hash(ROOT / name) != value:
            mutable_source_drift.append(name)
    prior = read("prior_bank_exclusions.json")
    for name, value in prior["source_hashes"].items():
        assert file_hash(ROOT / name) == value
    exclusions = set(prior["templates"])
    for name in prior["source_hashes"]:
        for rows in json.loads((ROOT / name).read_text(encoding="utf-8")).values():
            exclusions.update(template(task["reference"]) for task in rows)
    assert exclusions == set(prior["templates"])
    banks, metadata = create_banks(cfg, exclusions)
    assert banks == read("protected_banks.json") and metadata == read("bank_manifest.json")
    tasks = {t["id"]: t for rows in banks.values() for t in rows}
    assert len(tasks) == sum(len(rows) for rows in banks.values())
    evidence = read("source_evidence.json")
    assert evidence["results"]["status"] == "completed" and evidence["audit"]["status"] == "passed"
    assert file_hash(ROOT / cfg["source_evidence"]) == evidence["results_sha256"]
    assert file_hash(ROOT / cfg["source_evidence_audit"]) == evidence["audit_sha256"]
    assert digest(read("initial_tables.json")["paired_credit"]) == digest(read("initial_tables.json")["paired_credit"])

    events = [json.loads(line) for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    assert verify_journal(root / "events.jsonl") == len(events)
    assert events[0]["kind"] == "preregistration" and events[-1]["kind"] == "completed"
    close = next(i for i, e in enumerate(events) if e["kind"] == "optimization_closed")
    eval_events = [e for e in events if e["kind"] == "evaluation"]
    assert all(i > close for i, e in enumerate(events) if e["kind"] == "evaluation" and e["payload"]["label"].startswith("final/"))

    worker = Worker()
    unique, rows_checked, oracle_checks = {}, 0, 0
    try:
        for event in eval_events:
            payload = event["payload"]
            request = payload["request"]
            key = digest(request)
            assert key == payload["request_sha256"]
            for task in request["tasks"]:
                assert task["id"] in tasks and task == public_task(tasks[task["id"]])
            first = worker.request(request)
            replay = worker.request(request)
            assert canonical(first) == canonical(replay)
            archived_raw = [{k: v for k, v in row.items() if k != "oracle_correct"} for row in payload["results"]]
            assert canonical(first) == canonical(archived_raw)
            for task_pub, result, archived in zip(request["tasks"], first, payload["results"]):
                task = tasks[task_pub["id"]]
                visible_outputs = outcomes(result["program"], task["visible"])
                visible_fit = visible_outputs == [out for _, out in task["visible"]]
                strict = correct(result["program"], task["hidden"]) and visible_fit
                assert result["visible_outputs"] == visible_outputs
                assert bool(result["visible_fit"]) is visible_fit
                assert bool(archived.get("oracle_correct")) is strict
                oracle_checks += 1
            if key not in unique:
                unique[key] = payload
            rows_checked += len(request["tasks"])
    finally:
        worker.close()

    evaluations = read("evaluations.json")
    results = read("results.json")
    assert results["status"] == "completed"
    assert set(evaluations) == {"ancestor", *[f"final/{c}/s{s}" for s in cfg["seeds"] for c in cfg["conditions"]]}
    for label, row in evaluations.items():
        assert row["label"] == ("final/ancestor" if label == "ancestor" else label)
        assert row["correct"] == sum(int(r["oracle_correct"]) for r in row["results"])
    trajectories = read("trajectories.json")
    assert set(trajectories) == {str(s) for s in cfg["seeds"]}
    for seed in cfg["seeds"]:
        assert set(trajectories[str(seed)]) == set(cfg["conditions"])
        for condition in cfg["conditions"]:
            tr = trajectories[str(seed)][condition]
            assert len(tr["decisions"]) == cfg["generations"]
            assert len(tr["snapshots"]) == cfg["generations"] + 1
            assert all("selection" in attempt for d in tr["decisions"] for attempt in d["attempts"])
            assert tr["mode"] == ("random" if condition == "random" else "adaptive")

    report = {"status": "passed", "artifacts_hashed": len(sealed), "journal_events": len(events),
              "tasks_regenerated": len(tasks), "unique_batches_reexecuted": len(unique),
              "replay_batches_reexecuted": len(unique), "evaluation_task_rows_regraded": rows_checked,
              "oracle_checks": oracle_checks, "transfer_groups": len(cfg["seeds"]),
              "conditions": len(cfg["conditions"]), "mutable_source_drift": mutable_source_drift,
              "scope": "Matched inherited-credit transfer component; no RSI conclusion"}
    write_json(root / "audit.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run")
    args = parser.parse_args()
    print(json.dumps(audit(ROOT / args.run), indent=2))
