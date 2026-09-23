"""Independent reconciliation of retention scores, decisions, lineage, and artifacts."""
import argparse
import json
import math
from pathlib import Path

from rsi.common import digest, verify_journal, write_json
from rsi.retention_run import file_hash
from rsi.neural import adapter_hash
from rsi.oracle import correct as oracle_correct


def strict_correct_text(text, examples):
    program = text.strip().splitlines()[0] if text and text.strip() else ""
    return oracle_correct(program, examples)


def check_score(tasks, samples, score):
    assert set(samples) == {r["id"] for r in tasks}
    assert [r["id"] for r in tasks] == [r["id"] for r in score["tasks"]]
    total = 0
    for task, row in zip(tasks, score["tasks"]):
        texts = samples[task["id"]]
        successes = sum(strict_correct_text(text, task["visible"] + task["hidden"]) for text in texts)
        assert row["correct"] == successes and row["n"] == len(texts)
        for key, measured in row["pass_at_k"].items():
            k = int(key)
            expected = 1 - (math.comb(len(texts) - successes, k) / math.comb(len(texts), k) if len(texts) - successes >= k else 0)
            assert math.isclose(expected, measured, abs_tol=1e-12)
        total += len(texts)
    for k, mean in score["pass_at_k"].items():
        assert math.isclose(mean, sum(r["pass_at_k"][k] for r in score["tasks"]) / len(tasks), abs_tol=1e-12)
    return total


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run")
    args = parser.parse_args()
    root = Path(args.run)
    read = lambda path: json.loads((root / path).read_text(encoding="utf-8"))
    artifacts = read("artifact_manifest.json")
    for name, metadata in artifacts.items():
        assert file_hash(root / name) == metadata["sha256"], name
        assert (root / name).stat().st_size == metadata["bytes"], name
    banks, meta = read("protected_banks.json"), read("bank_manifest.json")
    for name, rows in banks.items():
        assert digest(rows) == meta[name]["sha256"]
    manifest = read("manifest.json")
    assert digest(read("config.json")) == manifest["config_sha256"]
    for name, expected in manifest["source_sha256"].items():
        assert file_hash(root / "source" / name) == expected
    events = [json.loads(line) for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    event_count = verify_journal(root / "events.jsonl")
    assert events[-1]["kind"] == "completed"
    results = read("results.json")
    assert digest(results) == events[-1]["payload"]["results_sha256"]
    closed = next(r["seq"] for r in events if r["kind"] == "optimization_closed")
    assert all(r["seq"] < closed for r in events if r["kind"] == "change_resolved")
    checked, training_rows = 0, 0
    for name, score in results["scores"].items():
        if name.endswith("_selected"):
            assert score == results["scores"][results["selected"][name.removesuffix("_selected")]]
        else:
            checked += check_score(banks["final"], read("final_samples/" + name + ".json"), score)
    train = {r["id"]: r for r in banks["train"]}
    from safetensors.torch import load_file
    initial = adapter_hash(load_file(str(root / "adapters/initial/bootstrap/adapter_model.safetensors")))
    lineage = {"fresh": initial, "replay": initial, "replay_gated": initial}
    selected_names = {name: "initial" for name in lineage}
    adapters = {"fresh": "amplified", "replay": "selftrain", "replay_gated": "frozen"}
    for change in results["changes"]:
        name = change["change_id"]
        arm = name.rsplit("_round", 1)[0]
        validation = read("validation/" + name + ".json")
        assert digest(validation) == change["validation_sha256"]
        tasks = banks[change["validation_split"]]
        for side in ("parent", "candidate"):
            checked += check_score(tasks, validation[side + "_samples"], validation[side])
        parent, candidate = validation["parent"], validation["candidate"]
        old = {r["id"] for r in parent["tasks"] if r["correct"]}
        new = {r["id"] for r in candidate["tasks"] if r["correct"]}
        p, c = parent["pass_at_k"], candidate["pass_at_k"]
        eligible = old <= new and c["64"] >= p["64"] - 1e-12 and c["1"] >= p["1"] - 1e-12 and (c["64"] > p["64"] + 1e-12 or c["1"] > p["1"] + 1e-12)
        decision = change["decision"]
        assert decision["eligible"] == eligible
        assert decision["lost_task_ids"] == sorted(old - new) and decision["gained_task_ids"] == sorted(new - old)
        assert decision["accepted"] == (eligible if decision["gate_enforced"] else True)
        assert decision["parent_sha256"] == lineage[arm]
        for stage in ("candidate", "selected"):
            path = root / "adapters" / (name + "_" + stage) / adapters[arm] / "adapter_model.safetensors"
            assert adapter_hash(load_file(str(path))) == decision[stage + "_sha256"]
        expected = decision["candidate_sha256"] if decision["accepted"] else lineage[arm]
        assert decision["selected_sha256"] == expected
        lineage[arm] = expected
        if decision["accepted"]:
            selected_names[arm] = name
        assert change["selected_checkpoint"] == selected_names[arm]
        pool = read("training_pools/" + name + ".json")
        assert digest(pool) == change["pool_sha256"] == change["training"]["rows_sha256"]
        for row in pool:
            task = train[row["task_id"]]
            assert row["oracle_correct"] and oracle_correct(row["program"], task["visible"] + task["hidden"])
            training_rows += 1
        steps = [e["payload"] for e in events if e["kind"] == "optimizer_step" and e["payload"]["rows_sha256"] == digest(pool)
                 and e["payload"]["arm"] == change["training"]["arm"]]
        assert len(steps) == change["training"]["steps"]
        assert [s["step"] for s in steps] == list(range(1, len(steps) + 1))
        assert all(0 <= index < len(pool) for s in steps for index in s["row_indices"])
    assert selected_names == results["selected"]
    audit = {"status": "passed", "artifacts_hashed": len(artifacts), "journal_events": event_count,
             "raw_samples_regraded_with_published_interpreter": checked, "training_pool_rows_reverified": training_rows,
             "gate_decisions_and_checkpoint_lineage": "passed", "per_step_draw_reconciliation": "passed"}
    write_json(root / "audit.json", audit)
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
