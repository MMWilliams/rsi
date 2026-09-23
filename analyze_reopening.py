"""Paired source-only counterfactual for the corrected search kernel."""
import argparse
import json
import shutil
import time
from pathlib import Path

from audit_results import published_correct
from rsi.common import ROOT, Journal, canonical, digest, write_json
from rsi.oracle import correct
from rsi.retention_run import file_hash, seal_artifacts
from rsi.search_reopen import solve


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("output")
    args = parser.parse_args()
    source, output = Path(args.source), Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    journal = Journal(output / "events.jsonl")
    started = time.perf_counter()
    try:
        read = lambda name: json.loads((source / name).read_text(encoding="utf-8"))
        assert read("audit.json")["status"] == "passed"
        manifest = read("artifact_manifest.json")
        for name in ("events.jsonl", "trajectories.json", "protected_banks.json"):
            assert file_hash(source / name) == manifest[name]["sha256"]
        source_tasks = read("protected_banks.json")["source_development"]
        tasks = {t["id"]: t for t in source_tasks}
        additions = [(d["label"], a["index"]) for t in read("trajectories.json") if t["phase"] == "source"
                     for d in t["trajectory"]["decisions"] for a in d["attempts"] if a["proposal"]["kind"] == "add_fragment"]
        assert len(additions) == 44
        labels = {p + suffix for p, i in additions for suffix in ("/parent", f"/p{i}")}
        evaluations = {}
        for line in (source / "events.jsonl").read_text(encoding="utf-8").splitlines():
            event = json.loads(line)
            if event["kind"] == "evaluation" and event["payload"]["label"] in labels:
                evaluations[event["payload"]["label"]] = event["payload"]
        paths = [ROOT / p for p in ("analyze_reopening.py", "REOPENING-DIAGNOSTIC-v7.md", "rsi/search.py", "rsi/search_reopen.py", "rsi/common.py", "rsi/oracle.py", "audit_results.py", "vendor/trapdoor-loom/dsl.py", "vendor/trapdoor-loom/parse.py")]
        hashes = {p.relative_to(ROOT).as_posix(): file_hash(p) for p in paths}
        for path in paths:
            dest = output / "source" / path.relative_to(ROOT)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)
        write_json(output / "source_tasks.json", source_tasks)
        journal.append("started", {"source_run": str(source), "source_artifacts": {n: file_hash(source / n) for n in ("audit.json", "events.jsonl", "trajectories.json", "protected_banks.json")}, "source_hashes": hashes, "addition_count": len(additions)})
        cache, records, reopened = {}, [], 0
        for label in sorted(evaluations):
            evaluation = evaluations[label]
            request = evaluation["request"]
            request_hash = digest(request)
            assert request_hash == evaluation["request_sha256"]
            if request_hash not in cache:
                results = []
                for task in request["tasks"]:
                    protected = tasks[task["id"]]
                    assert task == {"id": protected["id"], "visible": protected["visible"]}
                    args_for_solve = (task, request["config"], request["budget"], request["max_atoms"], request["macros"], [])
                    result = solve(*args_for_solve)
                    assert canonical(result) == canonical(solve(*args_for_solve)), "Reopening replay mismatch"
                    examples = protected["visible"] + protected["hidden"]
                    grade = published_correct(result["program"], examples)
                    assert grade == correct(result["program"], examples), "Oracle disagreement"
                    assert all(0 <= result["cost"]["expansions"] <= request["budget"] for _ in [0])
                    results.append({**result, "oracle_correct": grade})
                    reopened += result["reopened_states"]
                cache[request_hash] = {"request": request, "request_sha256": request_hash, "results": results,
                                       "correct": sum(r["oracle_correct"] for r in results), "replay_verified": True}
                journal.append("evaluation", cache[request_hash])
            newer = cache[request_hash]
            records.append({"label": label, "request_sha256": request_hash, "old_correct": evaluation["correct"],
                            "new_correct": newer["correct"], "n": evaluation["n"],
                            "changed_programs": sum(a["program"] != b["program"] for a, b in zip(evaluation["results"], newer["results"]))})
        by_label = {r["label"]: r for r in records}
        paired = []
        for prefix, index in additions:
            parent, child = by_label[prefix + "/parent"], by_label[prefix + f"/p{index}"]
            paired.append({"label": prefix + f"/p{index}", "n": child["n"], "old_net_wins": child["old_correct"] - parent["old_correct"],
                           "new_net_wins": child["new_correct"] - parent["new_correct"], "new_candidate_minus_old": child["new_correct"] - child["old_correct"]})
        result = {"source_run": str(source), "scope": "Retrospective source-request comparison only, not a fresh trajectory or final-bank result",
                  "unique_requests": len(cache), "search_outputs": sum(len(v["results"]) for v in cache.values()),
                  "replay_search_outputs": sum(len(v["results"]) for v in cache.values()),
                  "reopened_states": reopened, "records": records, "paired_additions": paired,
                  "positive_additions_after_fix": sum(p["new_net_wins"] > 0 for p in paired),
                  "negative_additions_after_fix": sum(p["new_net_wins"] < 0 for p in paired),
                  "candidate_correctness_change_sum": sum(p["new_candidate_minus_old"] for p in paired),
                  "elapsed_seconds": time.perf_counter() - started}
        assert all(file_hash(ROOT / p) == h for p, h in hashes.items())
        write_json(output / "results.json", result)
        journal.append("completed", {"results_sha256": digest(result)})
        seal_artifacts(output)
        print(json.dumps({k: v for k, v in result.items() if k not in ("records", "paired_additions")}, indent=2))
    except Exception as exc:
        journal.append("failed", {"type": type(exc).__name__, "message": str(exc)})
        write_json(output / "FAILED.json", {"type": type(exc).__name__, "message": str(exc)})
        raise


if __name__ == "__main__":
    main()
