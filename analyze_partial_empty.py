"""Source-only comparison of atom filtering, reachability and search frontiers."""
import argparse
import json
import shutil
import time
from pathlib import Path

from audit_results import published_correct
from rsi.common import ROOT, Journal, canonical, digest, write_json
from rsi.oracle import correct
from rsi.retention_run import file_hash, seal_artifacts
from rsi.search_diagnostic import solve
from rsi.search_reachability import reachable
from rsi.search_reopen import solve as baseline


def summarize(records):
    metrics = {}
    for mode in ("baseline", "partial_empty"):
        rows = [r for r in records if r["mode"] == mode]
        metrics[mode] = {"tasks": len(rows), "visible_reachable": sum(r["reachability"]["reachable"] for r in rows),
                         "visible_fit": sum(r["search_result"]["visible_fit"] for r in rows),
                         "selected_correct": sum(r["selected_correct"] for r in rows),
                         "budget_misses": sum(r["reachability"]["reachable"] and not r["search_result"]["visible_fit"] for r in rows),
                         "visible_false_accepts": sum(r["search_result"]["visible_fit"] and not r["selected_correct"] for r in rows),
                         "coverage_at_k": {str(k): sum(any(f["oracle_correct"] for f in r["frontier"][:k]) for r in rows) for k in (1, 4, 16, 64)},
                         "verified_frontier_programs": sum(f["oracle_correct"] for r in rows for f in r["frontier"]),
                         "additional_tasks_in_frontier": sum(not r["selected_correct"] and any(f["oracle_correct"] for f in r["frontier"]) for r in rows),
                         "search_charges_including_replay": {k: 2 * sum(r["search_result"]["cost"][k] for r in rows) for k in ("expansions", "primitive_executions", "generated_nodes")},
                         "reachability_edge_checks": sum(r["reachability"]["edge_checks"] for r in rows),
                         "reachability_pool_primitive_charge": sum(r["reachability"]["pool_primitive_charge"] for r in rows),
                         "frontier_grade_example_upper_bound": sum(len(r["frontier"]) * r["example_count"] * 2 for r in rows),
                         "witness_grade_example_upper_bound": sum(2 * r["visible_count"] for r in rows if r["reachability"]["reachable"])}
    by_task = {}
    for record in records:
        by_task.setdefault(record["task_id"], {})[record["mode"]] = record
    wins = [t for t, v in by_task.items() if v["partial_empty"]["selected_correct"] and not v["baseline"]["selected_correct"]]
    losses = [t for t, v in by_task.items() if v["baseline"]["selected_correct"] and not v["partial_empty"]["selected_correct"]]
    new_reachable = [t for t, v in by_task.items() if v["partial_empty"]["reachability"]["reachable"] and not v["baseline"]["reachability"]["reachable"]]
    lost_reachable = [t for t, v in by_task.items() if v["baseline"]["reachability"]["reachable"] and not v["partial_empty"]["reachability"]["reachable"]]
    return {"metrics": metrics, "selected_task_wins": wins, "selected_task_losses": losses,
            "newly_visible_reachable": new_reachable, "lost_visible_reachability": lost_reachable,
            "baseline_identity_validation_charges": {k: sum(r["search_result"]["cost"][k] for r in records if r["mode"] == "baseline") for k in ("expansions", "primitive_executions", "generated_nodes")}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--source", default="runs/library-inheritance-20260916-v7")
    args = parser.parse_args()
    source, output = Path(args.source), Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    journal = Journal(output / "events.jsonl")
    started = time.perf_counter()
    try:
        read = lambda name: json.loads((source / name).read_text(encoding="utf-8"))
        assert read("audit.json")["status"] == "passed"
        manifest = read("artifact_manifest.json")
        for name in ("events.jsonl", "protected_banks.json"):
            assert file_hash(source / name) == manifest[name]["sha256"]
        tasks = read("protected_banks.json")["source_development"]
        by_id = {t["id"]: t for t in tasks}
        parents = []
        for line in (source / "events.jsonl").open(encoding="utf-8"):
            event = json.loads(line)
            if event["kind"] == "evaluation" and event["payload"]["label"].startswith("source/") and event["payload"]["label"].endswith("/parent"):
                parents.append(event["payload"])
        assert len(parents) == 36 and sum(len(p["request"]["tasks"]) for p in parents) == 576
        names = ["analyze_partial_empty.py", "audit_partial_empty.py", "PARTIAL-EMPTY-DIAGNOSTIC.md", "audit_results.py",
                 "rsi/common.py", "rsi/oracle.py", "rsi/search.py", "rsi/search_reopen.py", "rsi/search_diagnostic.py",
                 "rsi/search_reachability.py", "rsi/atom_pool_partial.py", "vendor/trapdoor-loom/dsl.py", "vendor/trapdoor-loom/parse.py"]
        hashes = {name: file_hash(ROOT / name) for name in names}
        for name in names:
            destination = output / "source" / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, destination)
        write_json(output / "source_tasks.json", tasks)
        write_json(output / "parent_requests.json", [{"label": p["label"], "request": p["request"], "request_sha256": p["request_sha256"]} for p in parents])
        journal.append("started", {"source": str(source), "source_sha256": {name: file_hash(source / name) for name in ("audit.json", "events.jsonl", "protected_banks.json")}, "code_sha256": hashes, "tasks": 576})
        records = []
        for parent in parents:
            request = parent["request"]
            assert request["budget"] == 128 and request["max_atoms"] == 4 and request["proposals"] == {}
            for public in request["tasks"]:
                protected = by_id[public["id"]]
                assert public == {"id": protected["id"], "visible": protected["visible"]}
                for mode in ("baseline", "partial_empty"):
                    args_for_solve = (public, request["config"], 128, 4, request["macros"], [])
                    details, replay_details = {}, {}
                    result = solve(*args_for_solve, diagnostics=details, pool_mode=mode)
                    repeated = solve(*args_for_solve, diagnostics=replay_details, pool_mode=mode)
                    assert canonical(result) == canonical(repeated) and canonical(details) == canonical(replay_details)
                    if mode == "baseline":
                        assert result == baseline(*args_for_solve), "Diagnostic changed baseline output"
                    reach = reachable(public, request["macros"], 4, mode)
                    assert not result["visible_fit"] or reach["reachable"]
                    if reach["reachable"]:
                        assert published_correct(reach["witness"], public["visible"]) and correct(reach["witness"], public["visible"])
                    frontier = []
                    examples = protected["visible"] + protected["hidden"]
                    for candidate in details["frontier"]:
                        grade = published_correct(candidate["program"], examples)
                        assert grade == correct(candidate["program"], examples)
                        frontier.append({**candidate, "oracle_correct": grade})
                    assert not frontier or frontier[0]["program"] == result["program"]
                    record = {"parent_label": parent["label"], "parent_request_sha256": parent["request_sha256"], "task_id": public["id"], "mode": mode,
                              "search_result": result, "reachability": reach, "frontier": frontier,
                              "distinct_candidates": details["distinct_candidates"], "selected_correct": bool(frontier and frontier[0]["oracle_correct"]),
                              "example_count": len(examples), "visible_count": len(public["visible"]), "replay_verified": True, "baseline_identity_checked": mode == "baseline"}
                    records.append(record)
                    journal.append("task_profile", record)
            print(f"Profiled {parent['label']} ({len(records) // 2}/576 tasks)", flush=True)
        write_json(output / "records.json", records)
        result = summarize(records)
        result.update(elapsed_seconds=time.perf_counter() - started, scope="Retrospective source-only filter/coverage diagnostic; deterministic search coverage, not IID model pass@k")
        assert not result["lost_visible_reachability"]
        assert all(file_hash(ROOT / name) == value for name, value in hashes.items())
        write_json(output / "results.json", result)
        journal.append("completed", {"results_sha256": digest(result)})
        seal_artifacts(output)
        print(json.dumps({"metrics": result["metrics"], "wins": len(result["selected_task_wins"]), "losses": len(result["selected_task_losses"]), "newly_reachable": len(result["newly_visible_reachable"]), "elapsed_seconds": result["elapsed_seconds"]}, indent=2))
    except Exception as exc:
        journal.append("failed", {"type": type(exc).__name__, "message": str(exc)})
        write_json(output / "FAILED.json", {"type": type(exc).__name__, "message": str(exc)})
        raise


if __name__ == "__main__":
    main()
