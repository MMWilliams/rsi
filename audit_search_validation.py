"""Recreate banks, replay search, independently combine and regrade all arms."""
import argparse
import json
import math
from pathlib import Path

from audit_results import published_correct
from rsi.banks import create_banks, template
from rsi.common import ROOT, canonical, digest, verify_journal, write_json
from rsi.retention_run import file_hash
from rsi.search import BASE_CONFIG
from rsi.search_diagnostic import solve


def audit(root):
    root = Path(root)
    read = lambda name: json.loads((root / name).read_text(encoding="utf-8"))
    manifest = read("artifact_manifest.json")
    actual_files = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and p.name not in ("artifact_manifest.json", "audit.json")}
    assert set(manifest) == actual_files
    for name, item in manifest.items():
        assert file_hash(root / name) == item["sha256"] and (root / name).stat().st_size == item["bytes"]
    event_count = verify_journal(root / "events.jsonl")
    events = [json.loads(line) for line in (root / "events.jsonl").read_text().splitlines()]
    assert events[0]["kind"] == "preregistration" and events[1]["kind"] == "bank_frozen" and events[-1]["kind"] == "completed"
    registration = events[0]["payload"]
    config = read("config.json")
    assert registration["config"] == config and registration["config_sha256"] == digest(config)
    assert registration["solver_config"] == BASE_CONFIG
    for name, value in registration["source_sha256"].items():
        assert file_hash(root / "source" / name) == value
        assert file_hash(ROOT / name) == value, "Audit requires archived source version"
    macros = read("common_macros.json")
    assert registration["macro_source_sha256"] == file_hash(ROOT / config["macro_source"])
    assert macros == json.loads((ROOT / config["macro_source"]).read_text())
    prior = read("prior_bank_exclusions.json")
    excluded = set()
    for name, value in prior["source_hashes"].items():
        assert file_hash(ROOT / name) == value
        old = json.loads((ROOT / name).read_text())
        excluded.update(template(t["reference"]) for rows in old.values() for t in rows)
    assert prior["templates"] == sorted(excluded) and registration["exclusions_sha256"] == digest(sorted(excluded))
    banks, meta = {}, {}
    for seed in config["seeds"]:
        bank, entry = create_banks({"bank_seed": seed, "bank_counts": {f"seed_{seed}": config["tasks_per_seed"]},
                                   "visible_examples": config["visible_examples"], "hidden_examples": config["hidden_examples"], "max_atoms": config["max_atoms"]}, excluded)
        banks.update(bank)
        meta.update(entry)
        excluded.update(template(t["reference"]) for rows in bank.values() for t in rows)
    assert banks == read("protected_banks.json") and meta == read("bank_manifest.json")
    assert events[1]["payload"] == {"sha256": digest(banks), "metadata": meta}
    raw = read("searches.json")
    expected = [(group, task, budget, mode) for group, tasks in banks.items() for index, task in enumerate(tasks)
                for budget in config["budgets"] for mode in (config["modes"] if index % 2 == 0 else config["modes"][::-1])]
    assert len(raw) == len(expected)
    assert [e["kind"] for e in events[2:2 + len(raw)]] == ["search"] * len(raw)
    assert [e["payload"] for e in events[2:2 + len(raw)]] == raw
    closure = events[2 + len(raw)]
    assert closure["kind"] == "search_closed" and closure["payload"] == {"records": len(raw), "sha256": digest(raw)}
    source_rows = {}
    for index, (row, (group, task, budget, mode)) in enumerate(zip(raw, expected)):
        request = {"task": {"id": task["id"], "visible": task["visible"]}, "config": BASE_CONFIG,
                   "budget": budget, "max_atoms": config["max_atoms"], "macros": macros, "mode": mode}
        assert row["request"] == request and row["request_sha256"] == digest(request)
        assert row["seed_group"] == group and row["task_id"] == task["id"] and row["arm"] == f"{mode}@{budget}"
        details = {}
        result = solve(request["task"], BASE_CONFIG, budget, config["max_atoms"], macros, [], diagnostics=details, pool_mode=mode)
        assert row["result"] == result and row["frontier"] == details["frontier"]
        assert not row["frontier"] or row["frontier"][0]["program"] == result["program"]
        assert row["distinct_candidates"] == details["distinct_candidates"]
        assert row["replay_result_sha256"] == digest(result)
        assert row["details_sha256"] == row["replay_details_sha256"] == digest(details)
        for key in ("cost", "replay_cost"):
            assert set(row[key]) == set(result["cost"]) | {"cpu_seconds", "wall_seconds"}
            assert {k: row[key][k] for k in result["cost"]} == result["cost"]
            assert all(isinstance(v, (int, float)) and math.isfinite(v) and v >= 0 for v in row[key].values())
        source_rows.setdefault(task["id"], {})[row["arm"]] = row
        if (index + 1) % 768 == 0:
            print(f"Audit reexecuted {index + 1} searches", flush=True)
    graded = read("graded.json")
    grade_events = events[3 + len(raw):-1]
    assert all(e["kind"] == "grade" for e in grade_events) and [e["payload"] for e in grade_events] == graded
    expected_grades, grade_count = [], 0
    for group, tasks in banks.items():
        for task in tasks:
            arms = source_rows[task["id"]]
            a, b = arms["baseline@64"], arms["partial_empty@64"]
            # Independent construction: sort the union, retain first per program.
            candidates = sorted(a["frontier"] + b["frontier"], key=lambda f: (f["cost"], len(f["program"]), f["program"]))
            merged, seen = [], set()
            for item in candidates:
                if item["program"] not in seen:
                    merged.append(item)
                    seen.add(item["program"])
            mixture = {"arm": "mixture@128", "frontier": merged[:64],
                       "cost": {k: a["cost"][k] + b["cost"][k] for k in a["cost"]},
                       "replay_cost": {k: a["replay_cost"][k] + b["replay_cost"][k] for k in a["replay_cost"]},
                       "origin_requests": [a["request_sha256"], b["request_sha256"]]}
            for row in list(arms.values()) + [mixture]:
                frontier = [{**f, "oracle_correct": published_correct(f["program"], task["visible"] + task["hidden"])} for f in row["frontier"]]
                assert all(published_correct(f["program"], task["visible"]) for f in frontier)
                grade_count += len(frontier)
                expected_grades.append({"task_id": task["id"], "seed_group": group, "arm": row["arm"], "frontier": frontier,
                    "selected_correct": bool(frontier and frontier[0]["oracle_correct"]), "cost": row["cost"], "replay_cost": row["replay_cost"],
                    "origin_requests": row.get("origin_requests", [row.get("request_sha256")])})
    assert graded == expected_grades, "Mixture or independent grades disagree"
    result = read("results.json")
    metrics = {}
    for arm in sorted({r["arm"] for r in graded}):
        rows = [r for r in graded if r["arm"] == arm]
        metrics[arm] = {"tasks": len(rows), "selected_correct": sum(r["selected_correct"] for r in rows),
            "visible_fit": sum(len(r["frontier"]) > 0 for r in rows),
            "coverage_at_k": {str(k): sum(sum(f["oracle_correct"] for f in r["frontier"][:k]) > 0 for r in rows) for k in (1, 4, 16, 64)},
            "verified_programs": sum(f["oracle_correct"] for r in rows for f in r["frontier"]),
            "cost": {k: sum(r["cost"][k] for r in rows) for k in rows[0]["cost"]},
            "replay_cost": {k: sum(r["replay_cost"][k] for r in rows) for k in rows[0]["replay_cost"]},
            "by_seed": {seed: {"selected_correct": sum(r["selected_correct"] for r in rows if r["seed_group"] == seed),
                               "coverage64": sum(any(f["oracle_correct"] for f in r["frontier"]) for r in rows if r["seed_group"] == seed)} for seed in sorted(banks)}}
    assert result["metrics"] == metrics
    pairs = [(f"partial_empty@{budget}", f"baseline@{budget}") for budget in config["budgets"]]
    pairs += [("mixture@128", f"{mode}@128") for mode in config["modes"]]
    assert set(result["contrasts"]) == {a + " minus " + b for a, b in pairs}
    for a, b in pairs:
        left = {r["task_id"]: r for r in graded if r["arm"] == a}
        right = {r["task_id"]: r for r in graded if r["arm"] == b}
        for metric in ("selected", "coverage64"):
            value = lambda r: r["selected_correct"] if metric == "selected" else any(f["oracle_correct"] for f in r["frontier"])
            wins = [t for t in left if value(left[t]) > value(right[t])]
            losses = [t for t in left if value(left[t]) < value(right[t])]
            assert result["contrasts"][a + " minus " + b][metric] == {"wins": wins, "losses": losses, "delta": (len(wins) - len(losses)) / len(left)}
    a, b = metrics["partial_empty@128"], metrics["baseline@128"]
    positive = sum(a["by_seed"][s]["selected_correct"] > b["by_seed"][s]["selected_correct"] and a["by_seed"][s]["coverage64"] > b["by_seed"][s]["coverage64"] for s in banks)
    assert result["screen"]["joint_positive_seed_groups"] == positive
    assert result["screen"]["passed"] is (a["selected_correct"] > b["selected_correct"] and a["coverage_at_k"]["64"] > b["coverage_at_k"]["64"] and positive >= 5)
    assert result["executed_searches"] == result["exact_replays"] == len(raw)
    assert result["grade_example_upper_bound"] == 2 * (config["visible_examples"] + config["hidden_examples"]) * grade_count
    assert result["execution_cost"] == {k: sum(r["cost"][k] + r["replay_cost"][k] for r in raw) for k in raw[0]["cost"]}
    assert events[-1]["payload"] == {"results_sha256": digest(result)}
    report = {"status": "passed", "artifacts_hashed": len(manifest), "journal_events": event_count,
              "fresh_tasks_regenerated": sum(len(t) for t in banks.values()), "searches_reexecuted": len(raw),
              "frontier_programs_regraded": grade_count, "mixtures_reconstructed": sum(len(t) for t in banks.values()),
              "limits": "Shared frozen search and generator; timings cannot be independently reproduced. Finite example verification, not all-input equivalence, host authentication or RSI."}
    write_json(root / "audit.json", report)
    return report


if __name__ == "__main__":
    if not __debug__:
        raise RuntimeError("Assertions must remain enabled")
    parser = argparse.ArgumentParser()
    parser.add_argument("run")
    print(json.dumps(audit(parser.parse_args().run), indent=2))
