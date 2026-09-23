"""Reconstruct v7 provenance, ranking and decisions without the library learner."""
from __future__ import annotations

import argparse
import copy
import json
import math
import random
from pathlib import Path

from audit_inheritance import check_evaluation, file_hash
from audit_results import published_correct
from rsi.banks import public_task, template
from rsi.common import digest, verify_journal, write_json
from rsi.evaluation import paired_bootstrap
from rsi.search import BASE_CONFIG
from dsl import Concat, PosError, render, run
from parse import parse


def rebuild_memory(memory, harvest):
    expected, additions = copy.deepcopy(memory), []
    for result in harvest["results"]:
        if not result["oracle_correct"]:
            continue
        atoms = parse(result["program"]).atoms
        texts = set()
        for start in range(len(atoms)):
            for length in (2, 3):
                if start + length <= len(atoms):
                    texts.add(render(Concat(tuple(atoms[start:start + length]))))
        certificate = {"label": harvest["label"], "request_sha256": harvest["request_sha256"],
                       "task_id": result["task_id"], "program_sha256": digest(result["program"])}
        for text in sorted(texts):
            entries = expected.setdefault(text, [])
            if certificate not in entries:
                entries.append(certificate)
                additions.append({"fragment": text, "certificate": certificate})
    return expected, additions


def rebuild_scramble(memory, seed):
    generator = random.Random(seed)
    output, trace = {}, []
    for length in (2, 3):
        texts = sorted(k for k in memory if len(parse(k).atoms) == length)
        pool = sum((list(parse(t).atoms) for t in texts), [])
        permutation = list(range(len(pool)))
        generator.shuffle(permutation)
        for index, old in enumerate(texts):
            selected = permutation[index * length:(index + 1) * length]
            new = render(Concat(tuple(pool[j] for j in selected)))
            output.setdefault(new, []).extend({**c, "scrambled_from": old} for c in memory[old])
            trace.append({"original": old, "scrambled": new, "atom_indices": selected})
    return output, {"seed": seed, "original_count": len(memory), "result_count": len(output),
                    "unchanged_entries": sum(x["original"] == x["scrambled"] for x in trace), "entries": trace}


def rebuild_rankings(memory, tasks, macros):
    ranking, work = [], 0
    for text in sorted(memory):
        if text in macros:
            continue
        program = parse(text)
        matches = []
        for task in tasks:
            good = True
            for x, y in task["visible"]:
                work += len(program.atoms)
                try:
                    value = run(program, x)
                    good = bool(value) and value in y
                except PosError:
                    good = False
                if not good:
                    break
            if good:
                matches.append(task["id"])
        ranking.append({"fragment": text, "compatible_tasks": matches,
                        "support": len({(c["request_sha256"], c["task_id"]) for c in memory[text]}),
                        "atoms": len(program.atoms), "evidence_sha256": digest(memory[text])})
    ranking = sorted(ranking, key=lambda r: (-len(r["compatible_tasks"]), -r["support"], -r["atoms"], r["fragment"]))
    return ranking, work


def audit(root):
    root = Path(root)
    read = lambda name: json.loads((root / name).read_text(encoding="utf-8"))
    artifact = read("artifact_manifest.json")
    for name, record in artifact.items():
        assert file_hash(root / name) == record["sha256"] and (root / name).stat().st_size == record["bytes"], "Artifact changed"
    config, manifest, banks = read("config.json"), read("manifest.json"), read("protected_banks.json")
    assert manifest["config_sha256"] == digest(config)
    for name, value in manifest["source_sha256"].items():
        assert file_hash(root / "source" / name) == value
    macros = read("common_macros.json")
    assert file_hash(root / "common_macros.json") == manifest["macro_source_sha256"]
    metadata = read("bank_manifest.json")
    seen_templates = set(read("prior_bank_exclusions.json")["templates"])
    task_ids = set()
    for split, tasks in banks.items():
        assert digest(tasks) == metadata[split]["sha256"] and len(tasks) == config["bank_counts"][split]
        templates = {template(t["reference"]) for t in tasks}
        assert not (templates & seen_templates), "Bank template leakage"
        seen_templates.update(templates)
        for task in tasks:
            assert task["id"] not in task_ids and published_correct(task["reference"], task["visible"] + task["hidden"])
            task_ids.add(task["id"])
    event_count = verify_journal(root / "events.jsonl")
    events = [json.loads(line) for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    assert events[0]["kind"] == "preregistration" and events[-1]["kind"] == "completed"
    assert events[0]["payload"] == {"config": config, "manifest": manifest, "bank_manifest": metadata}
    cutoffs = [e["seq"] for e in events if e["kind"] == "optimization_closed"]
    assert len(cutoffs) == 1
    cutoff = cutoffs[0]
    by_kind = {}
    for event in events:
        payload = event["payload"]
        if event["kind"] in ("evaluation", "fragment_memory_updated", "fragment_proposals", "fragment_change_resolved", "trajectory_closed"):
            label = payload["label"]
            key = event["kind"], label
            assert key not in by_kind, "Duplicate labeled event"
            by_kind[key] = event
            assert (event["seq"] > cutoff) == (event["kind"] == "evaluation" and label.startswith("final/")), "Final scoring before optimization closed"
    consumed, outputs = set(), 0
    ledger = {k: 0 for k in read("results.json")["ledger"]}

    def evaluation(label, tasks, state, library):
        nonlocal outputs
        key = "evaluation", label
        assert key not in consumed
        consumed.add(key)
        payload = by_kind[key]["payload"]
        outputs += check_evaluation(payload, tasks, state, config, library)
        for k, v in payload["compute"].items():
            ledger[k] += v
        return payload

    def get(kind, label):
        key = kind, label
        assert key not in consumed
        consumed.add(key)
        return by_kind[key]["payload"]

    trajectories = read("trajectories.json")
    assert len(trajectories) == len(config["seeds"]) * (1 + len(config["conditions"]))
    expected_order = [(phase, seed, condition) for seed in config["seeds"] for phase, condition in
                      [("source", "library"), *[("transfer", c) for c in config["conditions"]]]]
    assert [(e["phase"], e["seed"], e["condition"]) for e in trajectories] == expected_order
    sources, completed, ranking_total = {}, {}, 0
    scramble_rows = {r["seed"]: r for r in read("scrambled_memories.json")}
    expected_acquisition = []

    def delta(left, right):
        assert [r["task_id"] for r in left["results"]] == [r["task_id"] for r in right["results"]]
        return {"wins": [a["task_id"] for a, b in zip(left["results"], right["results"]) if b["oracle_correct"] and not a["oracle_correct"]],
                "losses": [a["task_id"] for a, b in zip(left["results"], right["results"]) if a["oracle_correct"] and not b["oracle_correct"]]}

    for entry in trajectories:
        phase, seed, condition = entry["phase"], entry["seed"], entry["condition"]
        trajectory = entry["trajectory"]
        label = f"{phase}/{condition}/{seed}"
        assert trajectory["label"] == label
        mode = condition if condition in ("numeric_pair", "frozen_library") else "library"
        assert trajectory["mode"] == mode
        state, library, memory = dict(BASE_CONFIG), list(macros), {}
        if phase == "transfer":
            source = sources[seed]
            if condition in ("g3", "g6"):
                memory = copy.deepcopy(source["snapshots"][condition[1:]]["memory"])
            elif condition == "scrambled_g6":
                memory, trace = rebuild_scramble(source["snapshots"]["6"]["memory"], seed + 77007)
                assert scramble_rows[seed] == {"seed": seed, "memory": memory, "trace": trace}, "Scrambled inheritance mismatch"
                matching = [e for e in events if e["kind"] == "memory_scrambled" and e["payload"]["seed"] == seed]
                assert len(matching) == 1 and matching[0]["seq"] < cutoff
                assert matching[0]["payload"] == {"seed": seed, "memory_sha256": digest(memory), "trace": trace}
        assert trajectory["snapshots"]["0"] == {"config": state, "macros": library, "memory": memory}, "Common ancestor/inherited memory mismatch"
        before = dict(ledger)
        seed_index = config["seeds"].index(seed)
        source_work = 0
        assert len(trajectory["decisions"]) == 6
        for generation in range(1, 7):
            prefix = f"{label}/g{generation}"
            slices = {}
            for split in ("harvest", "development", "admission"):
                all_tasks = banks[f"{phase}_{split}"]
                width = len(all_tasks) // (len(config["seeds"]) * 6)
                start = (seed_index * 6 + generation - 1) * width
                slices[split] = all_tasks[start:start + width]
            harvest = evaluation(prefix + "/harvest", slices["harvest"], state, library)
            old_hash = digest(memory)
            memory, added = rebuild_memory(memory, harvest)
            assert get("fragment_memory_updated", prefix) == {"label": prefix, "before_sha256": old_hash, "after_sha256": digest(memory),
                                                               "added": added, "harvest_request_sha256": harvest["request_sha256"]}, "Unverified fragment provenance"
            ranking, work = rebuild_rankings(memory, [public_task(t) for t in slices["development"]], library)
            source_work += work
            proposals = []
            if mode == "numeric_pair":
                for name, factor in (("absolute_cost_down", 0.65), ("absolute_cost_up", 1.4)):
                    candidate = {**state, "absolute_cost": min(4.0, max(0.1, state["absolute_cost"] * factor))}
                    proposals.append({"kind": "numeric", "name": name, "config": candidate, "macros": list(library)})
            elif mode == "library" and len(library) < 32:
                for rank in [r for r in ranking if r["compatible_tasks"]][:2]:
                    proposals.append({"kind": "add_fragment", "name": rank["fragment"], "config": dict(state), "macros": sorted([*library, rank["fragment"]])})
            while len(proposals) < 2:
                proposals.append({"kind": "noop", "name": f"noop_{len(proposals)}", "config": dict(state), "macros": list(library)})
            expected_selection = {"label": prefix, "mode": mode, "memory_sha256": digest(memory), "parent_config": state,
                                  "parent_macros": library, "rankings": ranking, "ranking_primitive_upper_bound": work,
                                  "proposals": proposals, "rule": "compatible task count, support, atom length descending; fragment text ascending"}
            assert get("fragment_proposals", prefix) == expected_selection, "Ranking/proposal mismatch"
            parent = evaluation(prefix + "/parent", slices["development"], state, library)
            children = [evaluation(prefix + f"/p{i}", slices["development"], p["config"], p["macros"]) for i, p in enumerate(proposals)]
            best = 0 if children[0]["correct"] >= children[1]["correct"] else 1
            guard_parent = evaluation(prefix + "/guard_parent", slices["admission"], state, library)
            guard_child = evaluation(prefix + "/guard_candidate", slices["admission"], proposals[best]["config"], proposals[best]["macros"])
            accepted = children[best]["correct"] > parent["correct"] and guard_child["correct"] >= guard_parent["correct"]
            attempts = []
            for i, proposal in enumerate(proposals):
                attempts.append({"index": i, "proposal": proposal, "parent_request_sha256": parent["request_sha256"],
                                 "candidate_request_sha256": children[i]["request_sha256"],
                                 "development_gain": children[i]["accuracy"] - parent["accuracy"], "development_delta": delta(parent, children[i]),
                                 "admission_evaluated": i == best, "accepted": accepted and i == best,
                                 "admission_gain": guard_child["accuracy"] - guard_parent["accuracy"] if i == best else None,
                                 "admission_delta": delta(guard_parent, guard_child) if i == best else None,
                                 "reason": "not_selected" if i != best else "no_development_gain" if children[i]["correct"] <= parent["correct"] else "admission_regression" if not accepted else "development_gain_and_admission_nonregression"})
            if accepted:
                state, library = copy.deepcopy(proposals[best]["config"]), list(proposals[best]["macros"])
            expected_decision = {"label": prefix, "generation": generation, "attempts": attempts, "best_index": best,
                                 "accepted": accepted, "config": state, "macros": library,
                                 "guard_parent_request_sha256": guard_parent["request_sha256"],
                                 "guard_candidate_request_sha256": guard_child["request_sha256"], "memory_sha256": digest(memory)}
            assert get("fragment_change_resolved", prefix) == expected_decision, "Admission/change outcome mismatch"
            assert trajectory["decisions"][generation - 1] == expected_decision
            assert trajectory["snapshots"][str(generation)] == {"config": state, "macros": library, "memory": memory}, "Snapshot memory/library mismatch"
            # Verify causal event order inside this generation, not just hashes.
            keys = [("evaluation", prefix + "/harvest"), ("fragment_memory_updated", prefix), ("fragment_proposals", prefix),
                    ("evaluation", prefix + "/parent"), ("evaluation", prefix + "/p0"), ("evaluation", prefix + "/p1"),
                    ("evaluation", prefix + "/guard_parent"), ("evaluation", prefix + "/guard_candidate"), ("fragment_change_resolved", prefix)]
            seqs = [by_kind[k]["seq"] for k in keys]
            assert seqs == sorted(seqs), "Selection used later evidence"
        assert get("trajectory_closed", label) == {"label": label, "snapshot_sha256": digest(trajectory["snapshots"]["6"])}
        assert trajectory["ranking_primitive_upper_bound"] == source_work
        ranking_total += source_work
        for k, value in entry["compute"].items():
            assert math.isclose(value, ledger[k] - before[k], abs_tol=1e-8), "Trajectory cost mismatch"
        if phase == "source":
            sources[seed] = trajectory
            expected_acquisition.append({"seed": seed, "compute": entry["compute"], "ranking_primitive_upper_bound": source_work})
        completed[label] = trajectory
    result = read("results.json")
    assert result["source_acquisition"] == expected_acquisition
    ancestor = evaluation("final/ancestor", banks["final"], BASE_CONFIG, macros)
    assert result["ancestor"] == ancestor
    assert len(result["measurements"]) == len(trajectories) * 2
    measured_keys = set()
    for measured in result["measurements"]:
        label = f"{measured['phase']}/{measured['condition']}/{measured['source_seed']}"
        generation = measured["generation"]
        assert generation in (3, 6) and (label, generation) not in measured_keys
        measured_keys.add((label, generation))
        snapshot = completed[label]["snapshots"][str(generation)]
        assert measured["label"] == f"final/{label}/g{generation}"
        score = evaluation(measured["label"], banks["final"], snapshot["config"], snapshot["macros"])
        for k in ("accuracy", "correct", "n", "request_sha256"):
            assert measured[k] == score[k]
        assert measured["task_scores"] == [int(r["oracle_correct"]) for r in score["results"]]
    final = {(m["source_seed"], m["condition"]): m for m in result["measurements"] if m["phase"] == "transfer" and m["generation"] == 6}
    contrasts = {}
    for condition in config["conditions"]:
        if condition == "g6":
            continue
        pairs = [{"source_seed": seed, **paired_bootstrap(final[seed, "g6"]["task_scores"], final[seed, condition]["task_scores"])} for seed in config["seeds"]]
        contrasts["g6_minus_" + condition] = {"mean": sum(p["mean"] for p in pairs) / len(pairs), "paired_sources": pairs}
    assert result["contrasts"] == contrasts
    wins = sum(final[s, "g6"]["correct"] > max(final[s, "g0"]["correct"], final[s, "scrambled_g6"]["correct"]) for s in config["seeds"])
    screen = {"all_mean_contrasts_positive": all(c["mean"] > 0 for c in contrasts.values()), "joint_source_wins": wins, "required_source_wins": len(config["seeds"]) // 2 + 1}
    screen["passed"] = screen["all_mean_contrasts_positive"] and wins >= screen["required_source_wins"]
    assert result["screen"] == screen and result["ranking_primitive_upper_bound"] == ranking_total
    for k, value in ledger.items():
        assert math.isclose(result["ledger"][k], value, abs_tol=1e-8), "Total cost mismatch"
    assert consumed == set(by_kind), "Unreconciled events"
    assert events[-1]["payload"] == {"results_sha256": digest(result), "screen": screen}
    report = {"status": "passed", "artifacts_hashed": len(artifact), "journal_events": event_count,
              "search_outputs_regraded": outputs, "evaluation_batches": sum(k[0] == "evaluation" for k in consumed),
              "trajectories": len(trajectories), "edit_attempts": len(trajectories) * 12,
              "checks": ["source certificates", "scrambled composition", "visible rankings", "common ancestors", "all admissions", "final cutoff", "costs"],
              "limits": "Published interpreter regrades saved programs; no independent rerun of every search or host authentication. Paired bootstrap helper shared."}
    write_json(root / "audit.json", report)
    return report


if __name__ == "__main__":
    if not __debug__:
        raise RuntimeError("Audit assertions must remain enabled")
    parser = argparse.ArgumentParser()
    parser.add_argument("run")
    print(json.dumps(audit(parser.parse_args().run), indent=2))
