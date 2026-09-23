"""Attack a copied GPU fixture; checks must survive fresh hashes and journal chains."""
import json
import shutil

import pytest

from audit_frontier_distillation import audit
from rsi.common import ROOT, canonical, digest, write_json
from rsi.retention_run import seal_artifacts


FIXTURE = ROOT / "analysis/frontier-v9-verification-fixture-v2"


def rechain(root, events, results):
    events[-1]["payload"] = {"results_sha256": digest(results)}
    previous = "0" * 64
    for index, event in enumerate(events):
        event.pop("sha256")
        event.update(seq=index, previous=previous)
        event["sha256"] = digest(event)
        previous = event["sha256"]
    (root / "events.jsonl").write_text("\n".join(canonical(e) for e in events) + "\n", encoding="utf-8")
    write_json(root / "results.json", results)
    seal_artifacts(root)


def test_unmodified_gpu_fixture_passes_full_independent_audit(tmp_path):
    root = tmp_path / "unaltered"
    shutil.copytree(FIXTURE, root)
    result = audit(root)
    assert result["checkpoint_decisions_reconciled"] == 8
    assert result["optimizer_steps_reconciled"] == 8


@pytest.mark.parametrize("attack", ["fabricated_token_charge", "forged_promotion", "final_task_in_training"])
def test_neural_audit_rejects_resealed_semantic_forgery(tmp_path, attack):
    root = tmp_path / attack
    shutil.copytree(FIXTURE, root)
    read = lambda name: json.loads((root / name).read_text())
    result = read("results.json")
    events = [json.loads(line) for line in (root / "events.jsonl").read_text().splitlines()]
    change = result["changes"][0]
    name = change["change_id"]
    resolved = next(e for e in events if e["kind"] == "change_resolved" and e["payload"]["change_id"] == name)
    if attack == "fabricated_token_charge":
        step = next(e["payload"] for e in events if e["kind"] == "optimizer_step" and e["payload"]["change_id"] == name)
        step["supervised_tokens"] += 1
        change["training_cost"]["supervised_tokens"] += 1
        result["compute"]["supervised_tokens"] += 1
        expected_statement = 'event["supervised_tokens"]'
    elif attack == "forged_promotion":
        assert not change["decision"]["eligible"]
        change["decision"]["accepted"] = True
        change["decision"]["rollback_verified"] = False
        change["decision"]["selected_sha256"] = change["decision"]["candidate_sha256"]
        change["selected_checkpoint"] = name
        result["selected"][str(change["seed"])][change["arm"]][str(change["round"])] = name
        src = root / "adapters" / (name + "_candidate") / "amplified/adapter_model.safetensors"
        dst = root / "adapters" / (name + "_selected") / "amplified/adapter_model.safetensors"
        shutil.copy2(src, dst)
        expected_statement = 'decision["accepted"] is decision["eligible"]'
    else:
        pool_path = f"training_pools/{change['arm']}_round{change['round']}.json"
        pool = read(pool_path)
        final_task = read("protected_banks.json")["final"][0]
        index = next(i for i, row in enumerate(pool) if row["stratum"] == "harvest")
        pool[index] = {"task_id": final_task["id"], "program": final_task["reference"], "oracle_correct": True, "stratum": "harvest"}
        write_json(root / pool_path, pool)
        old_hash = change["pool_sha256"]
        new_hash = digest(pool)
        change["pool_sha256"] = new_hash
        change["training"]["rows_sha256"] = new_hash
        for event in events:
            p = event["payload"]
            if p.get("change_id") == name:
                for field in ("rows_sha256", "pool_sha256"):
                    if p.get(field) == old_hash:
                        p[field] = new_hash
        expected_statement = 'pool == read('
    resolved["payload"] = change
    write_json(root / "changes" / (name + ".json"), change)
    rechain(root, events, result)
    with pytest.raises(AssertionError) as failure:
        audit(root)
    # The intended semantic invariant must reject the forgery, not an earlier
    # stale hash or an incidental fixture-loading error.
    assert expected_statement in str(failure.traceback[-1].statement)
