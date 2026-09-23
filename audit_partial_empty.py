"""Replay all profiles and independently check bounded visible reachability."""
import argparse
import json
from pathlib import Path

from audit_results import published_correct
from rsi.common import ROOT, canonical, digest, verify_journal, write_json
from rsi.retention_run import file_hash
from rsi.search import atom_pool
from rsi.atom_pool_partial import atom_pool as partial_pool
from rsi.search_diagnostic import solve


def independent_reachable(public, macros, mode):
    pool, _ = (atom_pool if mode == "baseline" else partial_pool)(canonical(public["visible"]), canonical(macros))
    # Keep every distinct (output vector, primitive length), rather than the
    # runner's shortest representative / cross-layer dominance algorithm.
    transitions = {(tuple(r["values"]), len(r["atoms"])) for r in pool}
    targets = tuple(out for _, out in public["visible"])
    reachable = [{tuple("" for _ in targets)}] + [set() for _ in range(4)]
    for used in range(5):
        if targets in reachable[used]:
            return True
        for prefix in reachable[used]:
            for values, length in transitions:
                if used + length > 4:
                    continue
                outputs = tuple(a + b for a, b in zip(prefix, values))
                if all(target.startswith(out) for target, out in zip(targets, outputs)):
                    reachable[used + length].add(outputs)
    return False


def audit(root):
    root = Path(root)
    read = lambda base, name: json.loads((Path(base) / name).read_text(encoding="utf-8"))
    manifest = read(root, "artifact_manifest.json")
    for name, entry in manifest.items():
        assert file_hash(root / name) == entry["sha256"] and (root / name).stat().st_size == entry["bytes"]
    event_count = verify_journal(root / "events.jsonl")
    events = [json.loads(line) for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    assert events[0]["kind"] == "started" and events[-1]["kind"] == "completed"
    started = events[0]["payload"]
    source = Path(started["source"])
    assert read(source, "audit.json")["status"] == "passed"
    for name, value in started["source_sha256"].items():
        assert file_hash(source / name) == value
    for name, value in started["code_sha256"].items():
        assert file_hash(root / "source" / name) == value
        assert file_hash(ROOT / name) == value, "Audit needs the archived code version"
    tasks = read(source, "protected_banks.json")["source_development"]
    assert read(root, "source_tasks.json") == tasks
    tasks = {t["id"]: t for t in tasks}
    expected_parents = []
    for line in (source / "events.jsonl").open(encoding="utf-8"):
        event = json.loads(line)
        payload = event["payload"]
        if event["kind"] == "evaluation" and payload["label"].startswith("source/") and payload["label"].endswith("/parent"):
            expected_parents.append({"label": payload["label"], "request": payload["request"], "request_sha256": payload["request_sha256"]})
    assert read(root, "parent_requests.json") == expected_parents
    records = read(root, "records.json")
    assert [e["payload"] for e in events[1:-1]] == records
    assert all(e["kind"] == "task_profile" for e in events[1:-1])
    order = [(p, t, mode) for p in expected_parents for t in p["request"]["tasks"] for mode in ("baseline", "partial_empty")]
    assert len(order) == len(records) == 1152
    frontier_programs = 0
    for record, (parent, public, mode) in zip(records, order):
        request = parent["request"]
        protected = tasks[public["id"]]
        assert public == {"id": protected["id"], "visible": protected["visible"]}
        assert request["budget"] == 128 and request["max_atoms"] == 4 and request["proposals"] == {}
        assert record["task_id"] == public["id"] and record["mode"] == mode
        assert record["parent_label"] == parent["label"] and record["parent_request_sha256"] == parent["request_sha256"] == digest(request)
        assert record["replay_verified"] is True and record["baseline_identity_checked"] is (mode == "baseline")
        details = {}
        repeated = solve(public, request["config"], 128, 4, request["macros"], [], diagnostics=details, pool_mode=mode)
        assert repeated == record["search_result"], "Independent search reexecution mismatch"
        assert record["distinct_candidates"] == details["distinct_candidates"]
        assert len(record["frontier"]) == len(details["frontier"])
        for measured, actual in zip(record["frontier"], details["frontier"]):
            assert {k: v for k, v in measured.items() if k != "oracle_correct"} == actual
            grade = published_correct(measured["program"], protected["visible"] + protected["hidden"])
            assert measured["oracle_correct"] is grade
            assert published_correct(measured["program"], protected["visible"])
            frontier_programs += 1
        assert record["selected_correct"] == bool(record["frontier"] and record["frontier"][0]["oracle_correct"])
        assert record["example_count"] == len(protected["visible"]) + len(protected["hidden"])
        assert record["visible_count"] == len(protected["visible"])
        reach = record["reachability"]
        assert reach["reachable"] is independent_reachable(public, request["macros"], mode), "Reachability proof mismatch"
        if reach["reachable"]:
            assert published_correct(reach["witness"], protected["visible"])
        else:
            assert reach["witness"] is None
        assert not repeated["visible_fit"] or reach["reachable"]
    metrics = {}
    for mode in ("baseline", "partial_empty"):
        group = [r for r in records if r["mode"] == mode]
        metrics[mode] = {"tasks": len(group), "visible_reachable": sum(r["reachability"]["reachable"] for r in group),
                         "visible_fit": sum(r["search_result"]["visible_fit"] for r in group), "selected_correct": sum(r["selected_correct"] for r in group),
                         "budget_misses": sum(r["reachability"]["reachable"] and not r["search_result"]["visible_fit"] for r in group),
                         "visible_false_accepts": sum(r["search_result"]["visible_fit"] and not r["selected_correct"] for r in group),
                         "coverage_at_k": {str(k): sum(any(f["oracle_correct"] for f in r["frontier"][:k]) for r in group) for k in (1, 4, 16, 64)},
                         "verified_frontier_programs": sum(f["oracle_correct"] for r in group for f in r["frontier"]),
                         "additional_tasks_in_frontier": sum(not r["selected_correct"] and any(f["oracle_correct"] for f in r["frontier"]) for r in group),
                         "search_charges_including_replay": {key: sum(2 * r["search_result"]["cost"][key] for r in group) for key in ("expansions", "primitive_executions", "generated_nodes")},
                         "reachability_edge_checks": sum(r["reachability"]["edge_checks"] for r in group),
                         "reachability_pool_primitive_charge": sum(r["reachability"]["pool_primitive_charge"] for r in group),
                         "frontier_grade_example_upper_bound": sum(len(r["frontier"]) * r["example_count"] * 2 for r in group),
                         "witness_grade_example_upper_bound": sum(2 * r["visible_count"] for r in group if r["reachability"]["reachable"])}
    result = read(root, "results.json")
    assert result["metrics"] == metrics
    paired = list(zip(records[::2], records[1::2]))
    assert result["selected_task_wins"] == [a["task_id"] for a, b in paired if b["selected_correct"] and not a["selected_correct"]]
    assert result["selected_task_losses"] == [a["task_id"] for a, b in paired if a["selected_correct"] and not b["selected_correct"]]
    assert result["newly_visible_reachable"] == [a["task_id"] for a, b in paired if b["reachability"]["reachable"] and not a["reachability"]["reachable"]]
    assert result["lost_visible_reachability"] == [] and all(not a["reachability"]["reachable"] or b["reachability"]["reachable"] for a, b in paired)
    assert result["baseline_identity_validation_charges"] == {key: sum(a["search_result"]["cost"][key] for a, _ in paired) for key in ("expansions", "primitive_executions", "generated_nodes")}
    assert events[-1]["payload"] == {"results_sha256": digest(result)}
    report = {"status": "passed", "artifacts_hashed": len(manifest), "journal_events": event_count,
              "source_tasks": 576, "searches_reexecuted": 1152, "visible_reachability_checks": 1152,
              "frontier_programs_regraded": frontier_programs,
              "limits": "Reexecutes frozen search and independently checks bounded visible reachability using shared pool builders; not a fresh-task replication, host authentication or full-program semantic equivalence."}
    write_json(root / "audit.json", report)
    return report


if __name__ == "__main__":
    if not __debug__:
        raise RuntimeError("Assertions must remain enabled")
    parser = argparse.ArgumentParser()
    parser.add_argument("run")
    print(json.dumps(audit(parser.parse_args().run), indent=2))
