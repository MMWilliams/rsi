"""Regrade outcomes and reconstruct table updates without calling evolve/select.

Checks consistency against a trusted archive. Hashes do not authenticate its host.
Use ordinary Python (assertions must be enabled).
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import random
from pathlib import Path

from rsi.common import canonical, digest, verify_journal, write_json
from audit_results import published_correct
from rsi.banks import public_task, template
from rsi.operators import apply, empty_stats, initial_catalog
from rsi.search import BASE_CONFIG


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_selection(trace, catalog, table, rng, mode, excluded):
    """Reconstruct the selector arithmetic and random stream without importing select."""
    available = [op for op in catalog if op["name"] not in excluded] or catalog
    expected = {"policy": "operator_effect_v1", "mode": mode, "excluded": list(excluded),
                "available": [op["name"] for op in available], "table_sha256": digest(table),
                "rng_before_sha256": digest(rng.getstate()), "scores": []}
    if mode == "random":
        selected = rng.choice(available)["name"]
        reason = "uniform_choice_from_available_operators"
    else:
        for op in available:
            stats = table[op["name"]]
            alpha, beta = 1 + stats["beneficial"], 1 + stats["trials"] - stats["beneficial"]
            draw = rng.betavariate(alpha, beta)
            gain = stats["gain_sum"] / max(1, stats["trials"])
            descendant = stats["descendant_gain_sum"] / max(1, stats["descendant_trials"])
            expected["scores"].append({"name": op["name"], "alpha": alpha, "beta": beta,
                                       "productivity_draw": draw, "mean_gain": gain,
                                       "descendant_mean": descendant, "score": draw + gain + 0.25 * descendant})
        selected = max(expected["scores"], key=lambda row: (row["score"], row["name"]))["name"]
        reason = "maximum_sampled_productivity_plus_mean_gain_plus_quarter_descendant_mean; lexical_name_tiebreak"
    expected.update(selected=selected, rng_after_sha256=digest(rng.getstate()), reason=reason)
    assert trace == expected, "Selection explanation/random stream disagrees with reconstructed choice"
    return selected


def check_evaluation(payload, tasks, config, experiment, macros):
    expected = {"tasks": [public_task(t) for t in tasks], "config": config,
                "budget": experiment["search_budget"], "max_atoms": experiment["max_atoms"],
                "macros": macros, "proposals": {}}
    assert payload["request"] == expected, "Request differs from declared tasks/config"
    assert payload["request_sha256"] == digest(expected)
    rows = payload["results"]
    assert len(rows) == len(tasks) and payload["replay_verified"] is True
    correct_count = false_accepts = 0
    costs = {"worker_batches": 2, "replay_batches": 1, "incidents": 0,
             "search_expansions": 0, "primitive_executions": 0,
             "model_proposal_checks": 0, "oracle_string_executions": 0}
    for task, row in zip(tasks, rows):
        assert row["task_id"] == task["id"]
        worker_row = {k: v for k, v in row.items() if k not in ("oracle_correct", "replay_sha256")}
        assert digest(worker_row) == row["replay_sha256"]
        visible = published_correct(row["program"], task["visible"])
        correct = visible and published_correct(row["program"], task["hidden"])
        assert row["visible_fit"] is visible and row["oracle_correct"] is correct, "Published interpreter disagrees"
        if visible:
            assert row["visible_outputs"] == [out for _, out in task["visible"]]
        correct_count += int(correct)
        false_accepts += int(visible and not correct)
        assert 0 <= row["cost"]["expansions"] <= experiment["search_budget"]
        costs["search_expansions"] += 2 * row["cost"]["expansions"]
        costs["primitive_executions"] += 2 * row["cost"]["primitive_executions"]
        costs["model_proposal_checks"] += 2 * row["cost"]["model_checks"]
        costs["oracle_string_executions"] += len(task["visible"]) + len(task["hidden"])
    assert payload["correct"] == correct_count and payload["n"] == len(tasks)
    assert payload["accuracy"] == correct_count / len(tasks)
    assert payload["visible_false_accepts"] == false_accepts
    assert {k: v for k, v in payload["compute"].items() if k != "wall_seconds"} == costs
    assert math.isfinite(payload["compute"]["wall_seconds"]) and payload["compute"]["wall_seconds"] >= 0
    return len(rows)


def reconcile_trajectory(trajectory, label, initial, banks, experiment, macros, evaluations,
                         proposals, resolutions, generations, consumed):
    """Reconstruct fitness-derived statistics and choices from independently checked scores."""
    table = {op["name"]: copy.deepcopy(initial.get(op["name"], empty_stats())) for op in initial_catalog()}
    state, lineage = dict(BASE_CONFIG), []
    assert trajectory["snapshots"]["0"] == {"config": state, "table": table}
    seed = trajectory["seed"]
    selection_rng = random.Random(seed)
    catalog = {op["name"]: op for op in initial_catalog()}
    checked, computes = 0, []

    def evaluation(name, tasks, candidate):
        nonlocal checked
        row = evaluations[name]
        assert name not in consumed, "Duplicate evaluation use"
        consumed.add(name)
        checked += check_evaluation(row, tasks, candidate, experiment, macros)
        computes.append(row["compute"])
        return row

    assert len(trajectory["decisions"]) == 6
    for g, decision in enumerate(trajectory["decisions"], 1):
        prefix = f"{label}/{seed}/g{g}"
        dev_width, guard_width = len(banks["development"]) // 6, len(banks["admission"]) // 6
        dev = banks["development"][(g - 1) * dev_width:g * dev_width]
        guard = banks["admission"][(g - 1) * guard_width:g * guard_width]
        parent = evaluation(prefix + "/parent", dev, state)
        candidates = []
        attempts = decision["attempts"]
        assert len(attempts) == experiment["proposals_per_generation"]
        assert len({a["operator"]["name"] for a in attempts}) == len(attempts)
        selected_names = []
        for p, attempt in enumerate(attempts):
            name = attempt["operator"]["name"]
            if experiment.get("log_selection", False):
                assert check_selection(attempt["selection"], list(catalog.values()), table, selection_rng,
                                       trajectory["mode"], selected_names) == name
            selected_names.append(name)
            change_id = f"{prefix}/p{p}"
            assert attempt["change_id"] == change_id and attempt["operator"] == catalog[name]
            assert attempt["parent_config"] == state and attempt["parent_config_sha256"] == digest(state)
            assert attempt["stats_before"] == table[name]
            assert attempt["parent_evaluation_request_sha256"] == parent["request_sha256"]
            assert attempt["development_task_ids"] == [t["id"] for t in dev]
            proposed = proposals[change_id]
            assert all(attempt[k] == v for k, v in proposed.items())
            candidate = apply(catalog[name], state)
            assert attempt["valid"] is True and attempt["candidate_config"] == candidate
            assert attempt["candidate_config_sha256"] == digest(candidate)
            measured = evaluation(f"{prefix}/p{p}/{name}", dev, candidate)
            gain = measured["accuracy"] - parent["accuracy"]
            assert attempt["development_gain"] == gain
            assert attempt["candidate_evaluation_request_sha256"] == measured["request_sha256"]
            assert (attempt["parent_correct"], attempt["candidate_correct"], attempt["n"]) == (parent["correct"], measured["correct"], len(dev))
            table[name]["trials"] += 1
            table[name]["beneficial"] += int(gain > 0)
            table[name]["gain_sum"] += gain
            assert attempt["stats_after_trial"] == table[name]
            candidates.append((gain, name, candidate, change_id))
        best = max(candidates, key=lambda r: (r[0], r[1]))
        guard_parent = evaluation(prefix + "/guard_parent", guard, state)
        guard_child = evaluation(prefix + "/guard_candidate", guard, best[2])
        guard_gain = guard_child["accuracy"] - guard_parent["accuracy"]
        accepted = best[0] > 0 and guard_gain >= 0
        for ancestor in lineage:
            table[ancestor]["descendant_trials"] += 1
            table[ancestor]["descendant_gain_sum"] += guard_gain
        if accepted:
            table[best[1]]["accepted"] += 1
            lineage.append(best[1])
            state = best[2]
        for a in attempts:
            is_best = a["change_id"] == best[3]
            reason = ("not_selected_after_development_comparison" if not is_best else
                      "no_positive_development_gain" if best[0] <= 0 else
                      "admission_regression" if guard_gain < 0 else "development_gain_and_admission_nonregression")
            assert a["reason"] == reason and a["accepted"] is (is_best and accepted)
            assert a["admission_evaluated"] is is_best
            assert a["admission_gain"] == (guard_gain if is_best else None)
            assert a["stats_after"] == table[a["operator"]["name"]]
            assert a["selected_config_sha256"] == digest(state)
            if is_best:
                assert a["admission_parent_request_sha256"] == guard_parent["request_sha256"]
                assert a["admission_candidate_request_sha256"] == guard_child["request_sha256"]
            assert resolutions[a["change_id"]] == a
        assert decision["generation"] == g and decision["operator"] == best[1]
        assert decision["dev_gain"] == best[0] and decision["admission_gain"] == guard_gain
        assert decision["accepted"] is accepted and decision["config"] == state
        assert decision["table_sha256"] == digest(table)
        assert trajectory["snapshots"][str(g)] == {"config": state, "table": table}
        assert generations[(label, seed, g)] == {"label": label, "seed": seed, **decision}
    assert trajectory["table"] == table and trajectory["config"] == state
    return checked, {k: sum(c[k] for c in computes) for k in computes[0]}


def audit(root):
    if not __debug__:
        raise RuntimeError("Audit requires assertions enabled")
    root = Path(root)
    read = lambda name: json.loads((root / name).read_text(encoding="utf-8"))
    artifacts = read("artifact_manifest.json")
    for name, metadata in artifacts.items():
        assert file_hash(root / name) == metadata["sha256"] and (root / name).stat().st_size == metadata["bytes"], name
    config, banks, meta, manifest = (read(n) for n in ("config.json", "protected_banks.json", "bank_manifest.json", "manifest.json"))
    assert digest(config) == manifest["config_sha256"]
    for name, sha in manifest["source_sha256"].items():
        assert file_hash(root / "source" / name) == sha
    assert file_hash(root / "common_macros.json") == manifest["macro_source_sha256"]
    seen = set(read("prior_bank_exclusions.json")["templates"])
    for split, tasks in banks.items():
        assert len(tasks) == config["bank_counts"][split] == meta[split]["count"]
        assert digest(tasks) == meta[split]["sha256"]
        templates = {template(t["reference"]) for t in tasks}
        assert not seen & templates
        seen.update(templates)
        assert all(published_correct(t["reference"], t["visible"] + t["hidden"]) for t in tasks)
    events = [json.loads(line) for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    event_count = verify_journal(root / "events.jsonl")
    result = read("results.json")
    assert events[-1]["kind"] == "completed" and events[-1]["payload"]["results_sha256"] == digest(result)
    assert events[0]["kind"] == "preregistration" and events[0]["payload"]["config"] == config
    closed = [e for e in events if e["kind"] == "optimization_closed"]
    assert len(closed) == 1
    cutoff = closed[0]["seq"]
    assert all(e["seq"] < cutoff for e in events if e["kind"] in ("search_change_proposed", "search_change_resolved", "generation", "transfer_closed"))
    evaluation_events = [e for e in events if e["kind"] == "evaluation"]
    assert all((e["seq"] > cutoff) == e["payload"]["label"].startswith("final/") for e in evaluation_events)
    evaluations = {e["payload"]["label"]: e["payload"] for e in evaluation_events}
    assert len(evaluations) == len(evaluation_events)
    proposals = {e["payload"]["change_id"]: e["payload"] for e in events if e["kind"] == "search_change_proposed"}
    resolutions = {e["payload"]["change_id"]: e["payload"] for e in events if e["kind"] == "search_change_resolved"}
    assert proposals.keys() == resolutions.keys()
    generations = {(p["label"], p["seed"], p["generation"]): p for e in events if e["kind"] == "generation" for p in [e["payload"]]}
    sources, transfers, macros = (read(n) for n in ("source_trajectories.json", "transfer_trajectories.json", "common_macros.json"))
    assert [s["seed"] for s in sources] == config["seeds"]
    assert len(transfers) == len(config["seeds"]) * len(config["conditions"])
    assert {(t["source_seed"], t["condition"]) for t in transfers} == {(s, c) for s in config["seeds"] for c in config["conditions"]}
    checked, consumed = 0, set()
    def sliced(prefix, index):
        return {split: banks[prefix + "_" + split][index * (len(banks[prefix + "_" + split]) // len(sources)):(index + 1) * (len(banks[prefix + "_" + split]) // len(sources))]
                for split in ("development", "admission")}
    def same_compute(left, right):
        assert left.keys() == right.keys()
        assert all(math.isclose(left[k], right[k], rel_tol=1e-10, abs_tol=1e-9) for k in left)
    for index, source in enumerate(sources):
        seed = source["seed"]
        count, cost = reconcile_trajectory(source, "balanced_source", {}, sliced("source", index), config, macros, evaluations, proposals, resolutions, generations, consumed)
        checked += count
        acquisition = next(c for c in result["source_acquisition_compute"] if c["seed"] == seed)
        same_compute(cost, {k: v for k, v in acquisition.items() if k != "seed"})
        names = sorted(source["table"])
        records = [copy.deepcopy(source["table"][name]) for name in names]
        random.Random(seed + 77000).shuffle(records)
        tables = {"g0": source["snapshots"]["0"]["table"], "g3": source["snapshots"]["3"]["table"], "g6": source["table"], "scrambled_g6": dict(zip(names, records)), "random": {}}
        for item in [t for t in transfers if t["source_seed"] == seed]:
            condition = item["condition"]
            assert item["initial_table"] == tables[condition]
            assert item["trajectory"]["seed"] == seed + 10000
            assert item["trajectory"]["mode"] == ("random" if condition == "random" else "adaptive")
            count, cost = reconcile_trajectory(item["trajectory"], "transfer/" + condition, item["initial_table"], sliced("transfer", index),
                                              {**config, "proposals_per_generation": config["transfer_proposals"]}, macros, evaluations, proposals, resolutions, generations, consumed)
            checked += count
            same_compute(cost, item["compute"])
    ancestor = evaluations["final/ancestor"]
    checked += check_evaluation(ancestor, banks["final"], BASE_CONFIG, config, macros)
    consumed.add("final/ancestor")
    assert result["ancestor"] == ancestor
    assert len(result["measurements"]) == len(transfers)
    for item, measured in zip(transfers, result["measurements"]):
        assert (item["source_seed"], item["condition"]) == (measured["source_seed"], measured["condition"])
        name = f"final/{item['condition']}/{item['source_seed']}"
        score = evaluations[name]
        checked += check_evaluation(score, banks["final"], item["trajectory"]["config"], config, macros)
        consumed.add(name)
        assert measured["config"] == item["trajectory"]["config"]
        assert measured["task_scores"] == [int(r["oracle_correct"]) for r in score["results"]]
        for key in ("accuracy", "correct", "n", "request_sha256"):
            assert measured[key] == score[key]
        assert measured["gain_over_ancestor"] == score["accuracy"] - ancestor["accuracy"]
        assert measured["accepted_edits"] == sum(d["accepted"] for d in item["trajectory"]["decisions"])
    assert consumed == evaluations.keys(), "Unaccounted evaluation"
    same_compute(result["ledger"], {k: sum(e["compute"][k] for e in evaluations.values()) for k in result["ledger"]})
    for control in ("g0", "g3", "scrambled_g6", "random"):
        contrast = result["contrasts"]["g6_minus_" + control]
        means = []
        for seed, pair in zip(config["seeds"], contrast["paired_sources"]):
            rows = {m["condition"]: m for m in result["measurements"] if m["source_seed"] == seed}
            deltas = [a - b for a, b in zip(rows["g6"]["task_scores"], rows[control]["task_scores"])]
            rng = random.Random(20260916)
            boot = sorted(sum(rng.choice(deltas) for _ in deltas) / len(deltas) for _ in range(2000))
            mean = sum(deltas) / len(deltas)
            assert pair == {"source_seed": seed, "mean": mean, "ci95": [boot[50], boot[1950]], "unit": "paired task"}
            means.append(mean)
        assert contrast["mean"] == sum(means) / len(means)
    return {"status": "passed", "artifacts_hashed": len(artifacts), "journal_events": event_count,
            "search_outputs_regraded_with_published_interpreter": checked, "evaluation_batches": len(evaluations),
            "edit_attempts_reconciled": len(resolutions), "table_updates_and_admission_decisions": "passed",
            "selection_trace_reconciliation": "passed" if config.get("log_selection", False) else "not recorded in this protocol",
            "final_holdout_order_and_lineage": "passed", "compute_reconciliation": "passed",
            "limits": "Checks recorded outcomes and deterministic decision arithmetic; does not authenticate the host or independently repeat all searches."}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run")
    args = parser.parse_args()
    result = audit(args.run)
    write_json(Path(args.run) / "audit.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
