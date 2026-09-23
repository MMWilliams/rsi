"""Audit the saved source-only paired kernel diagnostic; no new search."""
import argparse
import json
from pathlib import Path

from audit_results import published_correct
from rsi.common import digest, verify_journal, write_json
from rsi.retention_run import file_hash


def audit(root):
    root = Path(root)
    read = lambda name: json.loads((root / name).read_text(encoding="utf-8"))
    manifest = read("artifact_manifest.json")
    for name, record in manifest.items():
        assert file_hash(root / name) == record["sha256"] and (root / name).stat().st_size == record["bytes"]
    count = verify_journal(root / "events.jsonl")
    events = [json.loads(line) for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    assert events[0]["kind"] == "started" and events[-1]["kind"] == "completed"
    started = events[0]["payload"]
    source = Path(started["source_run"])
    for name, value in started["source_artifacts"].items():
        assert file_hash(source / name) == value
    for name, value in started["source_hashes"].items():
        assert file_hash(root / "source" / name) == value
    source_read = lambda name: json.loads((source / name).read_text(encoding="utf-8"))
    assert source_read("audit.json")["status"] == "passed"
    original_manifest = source_read("artifact_manifest.json")
    for name in ("events.jsonl", "trajectories.json", "protected_banks.json"):
        assert file_hash(source / name) == original_manifest[name]["sha256"]
    source_tasks = source_read("protected_banks.json")["source_development"]
    assert read("source_tasks.json") == source_tasks
    tasks = {t["id"]: t for t in source_tasks}
    additions = [(d["label"], a["index"]) for t in source_read("trajectories.json") if t["phase"] == "source"
                 for d in t["trajectory"]["decisions"] for a in d["attempts"] if a["proposal"]["kind"] == "add_fragment"]
    assert len(additions) == started["addition_count"] == 44
    labels = {p + suffix for p, i in additions for suffix in ("/parent", f"/p{i}")}
    original = {}
    for line in (source / "events.jsonl").read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if event["kind"] == "evaluation" and event["payload"]["label"] in labels:
            original[event["payload"]["label"]] = event["payload"]
    allowed = {v["request_sha256"]: v["request"] for v in original.values()}
    evaluated, outputs, reopened = {}, 0, 0
    for event in events[1:-1]:
        assert event["kind"] == "evaluation"
        payload = event["payload"]
        key = payload["request_sha256"]
        assert key not in evaluated and key in allowed
        request = payload["request"]
        assert digest(request) == key and request == allowed[key], "Non-source or changed request"
        assert payload["replay_verified"] is True and len(payload["results"]) == len(request["tasks"])
        total = 0
        for public, result in zip(request["tasks"], payload["results"]):
            task = tasks[public["id"]]
            assert public == {"id": task["id"], "visible": task["visible"]}
            assert result["task_id"] == task["id"] and result["kernel"] == "cost_reopening_v1"
            assert digest({k: v for k, v in result.items() if k not in ("oracle_correct", "replay_sha256")}) == result["replay_sha256"]
            grade = published_correct(result["program"], task["visible"] + task["hidden"])
            assert result["oracle_correct"] is grade
            assert 0 <= result["cost"]["expansions"] <= request["budget"]
            assert isinstance(result["reopened_states"], int) and result["reopened_states"] >= 0
            total += int(grade)
            reopened += result["reopened_states"]
            outputs += 1
        assert payload["correct"] == total
        evaluated[key] = payload
    assert set(evaluated) == set(allowed)
    records = []
    for label in sorted(original):
        old = original[label]
        new = evaluated[old["request_sha256"]]
        records.append({"label": label, "request_sha256": old["request_sha256"], "old_correct": old["correct"],
                        "new_correct": new["correct"], "n": old["n"],
                        "changed_programs": sum(a["program"] != b["program"] for a, b in zip(old["results"], new["results"]))})
    by_label = {r["label"]: r for r in records}
    paired = []
    for prefix, index in additions:
        parent, child = by_label[prefix + "/parent"], by_label[prefix + f"/p{index}"]
        paired.append({"label": prefix + f"/p{index}", "n": child["n"], "old_net_wins": child["old_correct"] - parent["old_correct"],
                       "new_net_wins": child["new_correct"] - parent["new_correct"], "new_candidate_minus_old": child["new_correct"] - child["old_correct"]})
    result = read("results.json")
    expected = {"unique_requests": len(evaluated), "search_outputs": outputs, "replay_search_outputs": outputs,
                "reopened_states": reopened, "records": records, "paired_additions": paired,
                "positive_additions_after_fix": sum(p["new_net_wins"] > 0 for p in paired),
                "negative_additions_after_fix": sum(p["new_net_wins"] < 0 for p in paired),
                "candidate_correctness_change_sum": sum(p["new_candidate_minus_old"] for p in paired)}
    for key, value in expected.items():
        assert result[key] == value, "Paired result mismatch: " + key
    assert events[-1]["payload"] == {"results_sha256": digest(result)}
    report = {"status": "passed", "journal_events": count, "artifacts_hashed": len(manifest),
              "source_requests": len(evaluated), "outputs_regraded": outputs, "paired_additions": len(paired),
              "audit_script_sha256": file_hash(Path(__file__)),
              "limits": "Regrades saved outputs and reconstructs pairings; does not independently repeat search/replay or authenticate the host."}
    write_json(root / "audit.json", report)
    return report


if __name__ == "__main__":
    if not __debug__:
        raise RuntimeError("Assertions must remain enabled")
    parser = argparse.ArgumentParser()
    parser.add_argument("run")
    print(json.dumps(audit(parser.parse_args().run), indent=2))
