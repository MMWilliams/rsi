"""All available source-memory additions at the original fixed search budget."""
import argparse
import json
import shutil
import time
from pathlib import Path

from audit_results import published_correct
from rsi.common import ROOT, Journal, canonical, digest, write_json
from rsi.library import rank_memory
from rsi.oracle import correct
from rsi.retention_run import file_hash, seal_artifacts
from rsi.search_reopen import solve

DEPENDENCIES = ["rsi/search.py", "rsi/search_reopen.py", "rsi/common.py", "rsi/oracle.py",
                "vendor/trapdoor-loom/dsl.py", "vendor/trapdoor-loom/parse.py"]


def read(root, name):
    return json.loads((Path(root) / name).read_text(encoding="utf-8"))


def checked_archive(root, names):
    root = Path(root)
    assert read(root, "audit.json")["status"] == "passed"
    manifest = read(root, "artifact_manifest.json")
    for name in names:
        assert file_hash(root / name) == manifest[name]["sha256"], "Source archive changed"
    return {name: file_hash(root / name) for name in [*names, "audit.json", "artifact_manifest.json"]}


def build_plan(source):
    parents = {}
    for line in (Path(source) / "events.jsonl").open(encoding="utf-8"):
        event = json.loads(line)
        if event["kind"] == "evaluation":
            payload = event["payload"]
            if payload["label"].startswith("source/") and payload["label"].endswith("/parent"):
                parents[payload["label"][:-7]] = payload["request"]
    plan = []
    for row in read(source, "trajectories.json"):
        if row["phase"] != "source":
            continue
        trajectory = row["trajectory"]
        for decision in trajectory["decisions"]:
            generation, label = str(decision["generation"]), decision["label"]
            request = parents[label]
            assert request["budget"] == 128 and request["max_atoms"] == 4
            memory = trajectory["snapshots"][generation]["memory"]
            ranking, charge = rank_memory(memory, request["tasks"], request["macros"])
            selected = {a["proposal"]["name"] for a in decision["attempts"] if a["proposal"]["kind"] == "add_fragment"}
            candidates = [{**r, "originally_selected": r["fragment"] in selected} for r in ranking if r["compatible_tasks"]]
            plan.append({"label": label, "source_seed": row["seed"], "request": request,
                         "memory_sha256": digest(memory), "rankings": ranking, "candidates": candidates,
                         "ranking_primitive_upper_bound": charge})
    return plan


def summarize(plan, evaluated):
    menus = []
    for entry in plan:
        request = entry["request"]
        parent_hash = digest(request)
        parent = evaluated[parent_hash]
        candidates = []
        for candidate in entry["candidates"]:
            child_request = {**request, "macros": sorted([*request["macros"], candidate["fragment"]])}
            child_hash = digest(child_request)
            child = evaluated[child_hash]
            wins, losses = [], []
            for a, b in zip(parent["results"], child["results"]):
                assert a["task_id"] == b["task_id"]
                if b["oracle_correct"] and not a["oracle_correct"]:
                    wins.append(a["task_id"])
                if a["oracle_correct"] and not b["oracle_correct"]:
                    losses.append(a["task_id"])
            candidates.append({"fragment": candidate["fragment"], "originally_selected": candidate["originally_selected"],
                               "request_sha256": child_hash, "correct": child["correct"], "wins": wins, "losses": losses,
                               "gain": (len(wins) - len(losses)) / len(request["tasks"]),
                               "changed_programs": sum(a["program"] != b["program"] for a, b in zip(parent["results"], child["results"]))})
        menus.append({"label": entry["label"], "source_seed": entry["source_seed"], "parent_request_sha256": parent_hash,
                      "parent_correct": parent["correct"], "n": len(request["tasks"]), "candidates": candidates,
                      "all_available_upper_bound": max([0.0, *[c["gain"] for c in candidates]]),
                      "original_top_two_upper_bound": max([0.0, *[c["gain"] for c in candidates if c["originally_selected"]]])})
    candidates = [c for m in menus for c in m["candidates"]]
    return {"menus": menus, "menu_count": len(menus), "candidate_count": len(candidates),
            "unselected_count": sum(not c["originally_selected"] for c in candidates),
            "positive_candidates": sum(c["gain"] > 0 for c in candidates),
            "negative_candidates": sum(c["gain"] < 0 for c in candidates),
            "positive_unselected": sum(c["gain"] > 0 and not c["originally_selected"] for c in candidates),
            "menus_with_opportunity": sum(m["all_available_upper_bound"] > 0 for m in menus),
            "mean_all_available_upper_bound": sum(m["all_available_upper_bound"] for m in menus) / len(menus),
            "mean_original_top_two_upper_bound": sum(m["original_top_two_upper_bound"] for m in menus) / len(menus),
            "changed_candidate_programs": sum(c["changed_programs"] for c in candidates)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--source", default="runs/library-inheritance-20260916-v7")
    parser.add_argument("--reuse", default="runs/reopening-diagnostic-20260916-v7")
    args = parser.parse_args()
    output, source, reuse = Path(args.output), Path(args.source), Path(args.reuse)
    output.mkdir(parents=True, exist_ok=False)
    journal = Journal(output / "events.jsonl")
    started = time.perf_counter()
    try:
        source_hashes = checked_archive(source, ["events.jsonl", "trajectories.json", "protected_banks.json"])
        reuse_hashes = checked_archive(reuse, ["events.jsonl", "results.json", "source_tasks.json"])
        for dependency in DEPENDENCIES:
            assert file_hash(ROOT / dependency) == file_hash(reuse / "source" / dependency), "Reuse kernel/dependency mismatch"
        source_tasks = read(source, "protected_banks.json")["source_development"]
        assert source_tasks == read(reuse, "source_tasks.json")
        tasks = {t["id"]: t for t in source_tasks}
        prior = {}
        for line in (reuse / "events.jsonl").open(encoding="utf-8"):
            event = json.loads(line)
            if event["kind"] == "evaluation":
                prior[event["payload"]["request_sha256"]] = event["payload"]
        plan = build_plan(source)
        assert len(plan) == 36 and sum(len(p["candidates"]) for p in plan) == 60
        paths = [ROOT / p for p in [*DEPENDENCIES, "rsi/library.py", "analyze_fragment_headroom.py", "audit_fragment_headroom.py", "audit_library.py", "audit_inheritance.py", "audit_results.py", "FRAGMENT-HEADROOM-v7.md"]]
        code_hashes = {p.relative_to(ROOT).as_posix(): file_hash(p) for p in paths}
        for path in paths:
            dest = output / "source" / path.relative_to(ROOT)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)
        write_json(output / "plan.json", plan)
        write_json(output / "source_tasks.json", source_tasks)
        journal.append("started", {"source": str(source), "reuse": str(reuse), "source_artifacts": source_hashes,
                                   "reuse_artifacts": reuse_hashes, "code_sha256": code_hashes, "plan_sha256": digest(plan)})
        evaluated, fresh, reused = {}, 0, 0
        for entry in plan:
            requests = [entry["request"], *[{**entry["request"], "macros": sorted([*entry["request"]["macros"], c["fragment"]])} for c in entry["candidates"]]]
            for request in requests:
                key = digest(request)
                assert key not in evaluated, "Unexpected duplicate menu request"
                if key in prior:
                    payload = prior[key]
                    assert payload["request"] == request
                    reused += len(payload["results"])
                    kind = "evaluation_reused"
                else:
                    results = []
                    for public in request["tasks"]:
                        task = tasks[public["id"]]
                        assert public == {"id": task["id"], "visible": task["visible"]}
                        call = (public, request["config"], request["budget"], request["max_atoms"], request["macros"], [])
                        result = solve(*call)
                        assert canonical(result) == canonical(solve(*call)), "Replay mismatch"
                        examples = task["visible"] + task["hidden"]
                        grade = published_correct(result["program"], examples)
                        assert grade == correct(result["program"], examples), "Oracle disagreement"
                        results.append({**result, "oracle_correct": grade})
                    payload = {"request": request, "request_sha256": key, "results": results,
                               "correct": sum(r["oracle_correct"] for r in results), "replay_verified": True}
                    fresh += len(results)
                    kind = "evaluation_fresh"
                evaluated[key] = payload
                journal.append(kind, payload)
            journal.append("menu_closed", {"label": entry["label"], "candidates": len(entry["candidates"])})
        result = summarize(plan, evaluated)
        charges = {name: 2 * sum(row["cost"][name] for evaluation in evaluated.values() for row in evaluation["results"])
                   for name in ("expansions", "primitive_executions", "generated_nodes")}
        result.update(fresh_outputs=fresh, reused_outputs=reused, fresh_replay_outputs=fresh,
                      logical_charges_including_replay=charges, elapsed_seconds=time.perf_counter() - started,
                      scope="Exhaustive available single-addition source diagnostic; oracle selection upper bound, not a new trajectory")
        assert all(file_hash(ROOT / name) == value for name, value in code_hashes.items()), "Code changed during diagnostic"
        write_json(output / "results.json", result)
        journal.append("completed", {"results_sha256": digest(result)})
        seal_artifacts(output)
        print(json.dumps({k: v for k, v in result.items() if k != "menus"}, indent=2))
    except Exception as exc:
        journal.append("failed", {"type": type(exc).__name__, "message": str(exc)})
        write_json(output / "FAILED.json", {"type": type(exc).__name__, "message": str(exc)})
        raise


if __name__ == "__main__":
    main()
