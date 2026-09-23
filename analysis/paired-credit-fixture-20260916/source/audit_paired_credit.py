"""Rebuild paired branches, grades, costs and effects from a sealed archive."""
import argparse
import json
import math
import random
from pathlib import Path

from audit_results import published_correct
from paired_credit import bank_config, effects
from rsi.banks import create_banks, public_task, template
from rsi.common import ROOT, canonical, digest, verify_journal, write_json
from rsi.operators import apply, initial_catalog
from rsi.retention_run import file_hash
from rsi.search import BASE_CONFIG
from rsi.search_diagnostic import solve


def audit(root):
    if not __debug__:
        raise RuntimeError("Assertions required")
    root = Path(root)
    read = lambda name: json.loads((root / name).read_text(encoding="utf-8"))
    assert not (root / "FAILED.json").exists()
    sealed = read("artifact_manifest.json")
    present = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    assert present - {"artifact_manifest.json", "audit.json"} == set(sealed)
    for name, metadata in sealed.items():
        assert file_hash(root / name) == metadata["sha256"] and (root / name).stat().st_size == metadata["bytes"], name
    cfg, manifest = read("config.json"), read("manifest.json")
    assert cfg["pool_mode"] == "partial_empty" and cfg["rounds"] == 2
    assert digest(cfg) == manifest["config_sha256"]
    for name, value in manifest["source_sha256"].items():
        assert file_hash(root / "source" / name) == value
    macros = read("common_macros.json")
    assert file_hash(root / "common_macros.json") == manifest["macro_sha256"]
    prior = read("prior_bank_exclusions.json")
    for name, value in prior["source_hashes"].items():
        assert file_hash(ROOT / name) == value
    exclusion = set(prior["templates"])
    for name in prior["source_hashes"]:
        for tasks in json.loads((ROOT / name).read_text(encoding="utf-8")).values():
            exclusion.update(template(t["reference"]) for t in tasks)
    assert exclusion == set(prior["templates"])
    banks, metadata = create_banks(bank_config(cfg), exclusion)
    assert banks == read("protected_banks.json") and metadata == read("bank_manifest.json")
    tasks_by_id = {t["id"]: (split, t) for split, tasks in banks.items() for t in tasks}
    assert len(tasks_by_id) == sum(map(len, banks.values()))
    events = [json.loads(line) for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    count = verify_journal(root / "events.jsonl")
    assert count == len(events) and events[-1]["kind"] == "completed"
    assert events[0]["kind"] == "preregistration"
    assert events[0]["payload"]["config"] == cfg and events[0]["payload"]["manifest"] == manifest
    assert events[0]["payload"]["prior_templates_sha256"] == digest(prior["templates"])
    assert [e["kind"] for e in events].count("optimization_closed") == 1
    close_index = next(i for i, e in enumerate(events) if e["kind"] == "optimization_closed")
    for index, event in enumerate(events):
        if event["kind"] == "evaluation" and event["payload"]["split"].endswith("measurement"):
            assert index > close_index, "Measurement leaked before optimization closed"
    catalog = {op["name"]: op for op in initial_catalog()}
    records = read("search_records.json")
    checks, costs = 0, {"physical_searches": 0, "exact_replays": 0,
        "logical_search_requests": 0, "charged_expansions": 0,
        "charged_primitive_executions": 0, "oracle_program_checks": 0,
        "oracle_string_check_upper_bound": 0}
    for key, row in records.items():
        request = row["request"]
        assert key == digest(request)
        assert set(request["task"]) == {"id", "visible"}
        split, task = tasks_by_id[request["task"]["id"]]
        assert request["task"] == public_task(task)
        assert request["config"] and request["budget"] == cfg["search_budget"]
        assert request["max_atoms"] == cfg["max_atoms"] and request["macros"] == macros
        assert request["pool_mode"] == cfg["pool_mode"]
        args = (request["task"], request["config"], request["budget"], request["max_atoms"], macros, [])
        first = solve(*args, pool_mode=request["pool_mode"])
        replay = solve(*args, pool_mode=request["pool_mode"])
        assert canonical(first) == canonical(replay) == canonical(row["result"])
        assert row["exact_replay_sha256"] == digest(replay)
        correct = published_correct(first["program"], task["visible"] + task["hidden"])
        assert correct is row["oracle_correct"]
        costs["physical_searches"] += 1
        costs["exact_replays"] += 1
        costs["charged_expansions"] += 2 * first["cost"]["expansions"]
        costs["charged_primitive_executions"] += 2 * first["cost"]["primitive_executions"]
        costs["oracle_program_checks"] += 2
        costs["oracle_string_check_upper_bound"] += 2 * (len(task["visible"]) + len(task["hidden"]))
        assert math.isfinite(row["search_replay_wall_seconds"]) and row["search_replay_wall_seconds"] >= 0
    evaluations = read("evaluations.json")
    seen, sequence = set(), []
    for label, row in evaluations.items():
        assert label == row["id"] and row["split"] in banks
        assert row["n"] == len(row["task_ids"]) == len(row["rows"])
        assert row["task_ids"] == [r["task_id"] for r in row["rows"]]
        assert len(row["task_ids"]) == len(set(row["task_ids"]))
        assert all(tasks_by_id[tid][0] == row["split"] for tid in row["task_ids"])
        verified = 0
        for entry in row["rows"]:
            task = tasks_by_id[entry["task_id"]][1]
            request = {"task": public_task(task), "config": row["config"],
                "budget": cfg["search_budget"], "max_atoms": cfg["max_atoms"],
                "macros": macros, "pool_mode": cfg["pool_mode"]}
            key = digest(request)
            assert entry["request_sha256"] == key and key in records
            assert entry["reused"] is (key in seen)
            seen.add(key)
            assert entry["oracle_correct"] is records[key]["oracle_correct"]
            verified += int(entry["oracle_correct"])
            costs["logical_search_requests"] += 1
        assert verified == row["correct"]
        sequence.append(label)
        checks += len(row["rows"])
    assert seen == set(records)
    assert len([e for e in events if e["kind"] == "evaluation"]) == len(sequence)
    assert [(e["payload"]["id"], e["payload"]["sha256"], e["payload"]["correct"], e["payload"]["split"])
            for e in events if e["kind"] == "evaluation"] == [
                (label, digest(evaluations[label]), evaluations[label]["correct"], evaluations[label]["split"])
                for label in sequence]
    assert costs["physical_searches"] == len([e for e in events if e["kind"] == "search"])
    assert costs["logical_search_requests"] - costs["physical_searches"] == len([e for e in events if e["kind"] == "search_reused"])
    assert {e["payload"]["request_sha256"] for e in events if e["kind"] == "search"} == set(records)
    trajectories = read("trajectories.json")
    expected_eval_order = []
    for seed in cfg["source_seeds"]:
        rng = random.Random(seed + 126000)
        names = list(catalog)
        plan = [rng.sample(names, 2) for _ in range(cfg["rounds"])]
        group = trajectories[str(seed)]
        assert list(group) == ["no_edit", *names]
        for name, observed in group.items():
            label = f"s{seed}_{name}"
            state = apply(catalog[name], BASE_CONFIG) if name != "no_edit" else dict(BASE_CONFIG)
            assert observed["seed"] == seed and observed["label"] == label
            assert observed["initial_config"] == state and observed["schedule"] == plan
            assert len(observed["decisions"]) == cfg["rounds"]
            for index, decision in enumerate(observed["decisions"], 1):
                devsplit, guardsplit = f"s{seed}_development", f"s{seed}_admission"
                start = (index - 1) * cfg["development_per_round"]
                dev = banks[devsplit][start:start + cfg["development_per_round"]]
                start_guard = (index - 1) * cfg["admission_per_round"]
                guard = banks[guardsplit][start_guard:start_guard + cfg["admission_per_round"]]
                prefix = f"{label}/g{index}"
                def check_eval(ref, expected_tasks, expected_state, expected_split):
                    e = evaluations[ref]
                    assert e["split"] == expected_split and e["task_ids"] == [t["id"] for t in expected_tasks]
                    assert e["config"] == expected_state
                    expected_eval_order.append(ref)
                    return e["correct"]
                parent_ref = prefix + "/parent"
                assert decision["round"] == index and decision["parent_config"] == state
                assert decision["operator_names"] == plan[index - 1] and decision["parent_ref"] == parent_ref
                parent = check_eval(parent_ref, dev, state, devsplit)
                scores = []
                refs = []
                for op_name in plan[index - 1]:
                    candidate = apply(catalog[op_name], state)
                    ref = prefix + "/" + op_name
                    score = check_eval(ref, dev, candidate, devsplit)
                    scores.append((score - parent, op_name, candidate))
                    refs.append(ref)
                assert decision["candidate_refs"] == refs
                best = max(scores, key=lambda row: (row[0], row[1]))
                assert decision["chosen_operator"] == best[1] and decision["candidate_config"] == best[2]
                gp_ref, gc_ref = prefix + "/guard_parent", prefix + "/guard_candidate"
                assert decision["guard_parent_ref"] == gp_ref and decision["guard_candidate_ref"] == gc_ref
                gp = check_eval(gp_ref, guard, state, guardsplit)
                gc = check_eval(gc_ref, guard, best[2], guardsplit)
                accepted = best[0] > 0 and gc >= gp
                reason = "positive_development_and_admission_nonregression" if accepted else (
                    "no_positive_development_gain" if best[0] <= 0 else "admission_regression")
                assert decision["development_gain_count"] == best[0]
                assert decision["admission_gain_count"] == gc - gp and decision["accepted"] is accepted
                assert decision["reason"] == reason
                if accepted:
                    state = best[2]
                assert decision["selected_config"] == state
            assert observed["terminal_config"] == state
        assert next(e for e in events if e["kind"] == "schedule_frozen" and e["payload"]["seed"] == seed)["payload"]["operator_names"] == plan
    assert sequence[:len(expected_eval_order)] == expected_eval_order
    assert events[close_index]["payload"] == {"branches": len(cfg["source_seeds"]) * (1 + len(catalog)),
                                               "trajectories_sha256": digest(trajectories)}
    assert len([e for e in events if e["kind"] == "branch_closed"]) == len(cfg["source_seeds"]) * (1 + len(catalog))
    measurement_order = []
    expected_pairs = []
    for seed in cfg["source_seeds"]:
        split = f"s{seed}_measurement"
        group = trajectories[str(seed)]
        starts, ends = {}, {}
        for name, trajectory in group.items():
            label = f"s{seed}_{name}"
            start_ref, end_ref = label + "/start", label + "/end"
            starts[name], ends[name] = evaluations[start_ref], evaluations[end_ref]
            for ref, state in ((start_ref, trajectory["initial_config"]), (end_ref, trajectory["terminal_config"])):
                row = evaluations[ref]
                assert row["split"] == split and row["config"] == state
                assert row["task_ids"] == [t["id"] for t in banks[split]]
                measurement_order.append(ref)
        for name in catalog:
            vals = effects(starts["no_edit"]["correct"], ends["no_edit"]["correct"],
                           starts[name]["correct"], ends[name]["correct"])
            expected_pairs.append({"seed": seed, "edit": name, "measurement_n": len(banks[split]),
                "base_start_ref": starts["no_edit"]["id"], "base_end_ref": ends["no_edit"]["id"],
                "edited_start_ref": starts[name]["id"], "edited_end_ref": ends[name]["id"], **vals})
    assert sequence == expected_eval_order + measurement_order
    result = read("results.json")
    assert result["status"] == "completed" and result["pairs"] == expected_pairs
    assert result["headroom_observed"] is any(r["later_improvement"] != 0 for r in expected_pairs)
    assert result["cost"] == {**costs, "search_wall_seconds": result["cost"]["search_wall_seconds"]}
    assert math.isclose(result["cost"]["search_wall_seconds"], sum(r["search_replay_wall_seconds"] for r in records.values()), abs_tol=1e-6)
    assert events[-1]["payload"] == {"results_sha256": digest(result)}
    report = {"status": "passed", "artifacts_hashed": len(sealed), "journal_events": count,
        "tasks_regenerated": len(tasks_by_id), "unique_searches_reexecuted": len(records),
        "search_replays_reexecuted": len(records), "evaluation_task_rows_regraded": checks,
        "branches_reconstructed": len(cfg["source_seeds"]) * (1 + len(catalog)),
        "paired_effects_recomputed": len(expected_pairs),
        "scope": "Finite-example DSL source probe; no neural training, inherited selector test or RSI conclusion"}
    write_json(root / "audit.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run")
    print(json.dumps(audit(parser.parse_args().run), indent=2))
