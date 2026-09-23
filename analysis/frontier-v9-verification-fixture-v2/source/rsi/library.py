"""Verified-solution fragment memory proposing bounded solver-library edits."""
from __future__ import annotations

import copy
import random

from .common import digest
from .search import BASE_CONFIG
from dsl import Concat, PosError, render, run
from parse import parse


def fragments(program):
    atoms = parse(program).atoms
    return sorted({render(Concat(tuple(atoms[i:i + width])))
                   for width in (2, 3) for i in range(len(atoms) - width + 1)})


def harvest_memory(memory, evaluation):
    memory = copy.deepcopy(memory)
    added = []
    for row in evaluation["results"]:
        if not row["oracle_correct"]:
            continue
        certificate = {"label": evaluation["label"], "request_sha256": evaluation["request_sha256"],
                       "task_id": row["task_id"], "program_sha256": digest(row["program"])}
        for fragment in fragments(row["program"]):
            evidence = memory.setdefault(fragment, [])
            if certificate not in evidence:
                evidence.append(certificate)
                added.append({"fragment": fragment, "certificate": certificate})
    return memory, added


def scramble_memory(memory, seed):
    rng = random.Random(seed)
    output, trace = {}, []
    for width in (2, 3):
        texts = sorted(t for t in memory if len(parse(t).atoms) == width)
        atoms = [atom for text in texts for atom in parse(text).atoms]
        indices = list(range(len(atoms)))
        rng.shuffle(indices)
        for i, original in enumerate(texts):
            positions = indices[i * width:(i + 1) * width]
            scrambled = render(Concat(tuple(atoms[j] for j in positions)))
            evidence = [{**entry, "scrambled_from": original} for entry in memory[original]]
            output.setdefault(scrambled, []).extend(evidence)
            trace.append({"original": original, "scrambled": scrambled, "atom_indices": positions})
    return output, {"seed": seed, "original_count": len(memory), "result_count": len(output),
                    "unchanged_entries": sum(r["original"] == r["scrambled"] for r in trace), "entries": trace}


def rank_memory(memory, tasks, macros):
    if any(set(task) != {"id", "visible"} for task in tasks):
        raise ValueError("Ranker accepts public examples only")
    rankings, charged = [], 0
    for fragment in sorted(memory):
        if fragment in macros:
            continue
        program = parse(fragment)
        compatible = []
        for task in tasks:
            fits = True
            for inp, target in task["visible"]:
                charged += len(program.atoms)
                try:
                    value = run(program, inp)
                    if not value or value not in target:
                        fits = False
                        break
                except PosError:
                    fits = False
                    break
            if fits:
                compatible.append(task["id"])
        support = len({(e["request_sha256"], e["task_id"]) for e in memory[fragment]})
        rankings.append({"fragment": fragment, "compatible_tasks": compatible, "support": support,
                         "atoms": len(program.atoms), "evidence_sha256": digest(memory[fragment])})
    rankings.sort(key=lambda r: (-len(r["compatible_tasks"]), -r["support"], -r["atoms"], r["fragment"]))
    return rankings, charged


def make_proposals(mode, config, macros, rankings):
    if mode == "numeric_pair":
        return [{"kind": "numeric", "name": name, "config": {**config, "absolute_cost": max(0.1, min(4.0, config["absolute_cost"] * factor))}, "macros": list(macros)}
                for name, factor in (("absolute_cost_down", 0.65), ("absolute_cost_up", 1.4))]
    proposals = []
    if mode == "library" and len(macros) < 32:
        for row in rankings:
            if row["compatible_tasks"]:
                proposals.append({"kind": "add_fragment", "name": row["fragment"], "config": dict(config),
                                  "macros": sorted([*macros, row["fragment"]])})
                if len(proposals) == 2:
                    break
    while len(proposals) < 2:
        proposals.append({"kind": "noop", "name": f"noop_{len(proposals)}", "config": dict(config), "macros": list(macros)})
    return proposals


def task_delta(parent, child):
    left = {r["task_id"]: r["oracle_correct"] for r in parent["results"]}
    right = {r["task_id"]: r["oracle_correct"] for r in child["results"]}
    assert left.keys() == right.keys()
    return {"wins": [t for t in left if right[t] and not left[t]],
            "losses": [t for t in left if left[t] and not right[t]]}


def evolve_library(evaluator, banks, experiment, label, initial_memory, common_macros, mode="library"):
    state, macros, memory = dict(BASE_CONFIG), list(common_macros), copy.deepcopy(initial_memory)
    snapshots = {0: {"config": copy.deepcopy(state), "macros": list(macros), "memory": copy.deepcopy(memory)}}
    decisions, ranking_work = [], 0
    for generation in range(1, experiment["generations"] + 1):
        prefix = f"{label}/g{generation}"
        sliced = {name: tasks[(generation - 1) * (len(tasks) // experiment["generations"]):generation * (len(tasks) // experiment["generations"])] for name, tasks in banks.items()}
        harvest = evaluator.evaluate(sliced["harvest"], state, prefix + "/harvest", macros=macros)
        before = digest(memory)
        memory, added = harvest_memory(memory, harvest)
        evaluator.journal.append("fragment_memory_updated", {"label": prefix, "before_sha256": before,
                                 "after_sha256": digest(memory), "added": added, "harvest_request_sha256": harvest["request_sha256"]})
        public = [{"id": t["id"], "visible": t["visible"]} for t in sliced["development"]]
        rankings, charged = rank_memory(memory, public, macros)
        ranking_work += charged
        proposals = make_proposals(mode, state, macros, rankings)
        selection = {"label": prefix, "mode": mode, "memory_sha256": digest(memory),
                     "parent_config": state, "parent_macros": macros, "rankings": rankings,
                     "ranking_primitive_upper_bound": charged, "proposals": proposals,
                     "rule": "compatible task count, support, atom length descending; fragment text ascending"}
        evaluator.journal.append("fragment_proposals", selection)
        parent = evaluator.evaluate(sliced["development"], state, prefix + "/parent", macros=macros)
        scores = [evaluator.evaluate(sliced["development"], p["config"], prefix + f"/p{i}", macros=p["macros"]) for i, p in enumerate(proposals)]
        best = max(range(2), key=lambda i: (scores[i]["correct"], -i))
        winner = proposals[best]
        guard_parent = evaluator.evaluate(sliced["admission"], state, prefix + "/guard_parent", macros=macros)
        guard_child = evaluator.evaluate(sliced["admission"], winner["config"], prefix + "/guard_candidate", macros=winner["macros"])
        accepted = scores[best]["correct"] > parent["correct"] and guard_child["correct"] >= guard_parent["correct"]
        attempts = []
        for i, proposal in enumerate(proposals):
            attempts.append({"index": i, "proposal": proposal, "parent_request_sha256": parent["request_sha256"],
                             "candidate_request_sha256": scores[i]["request_sha256"],
                             "development_gain": scores[i]["accuracy"] - parent["accuracy"],
                             "development_delta": task_delta(parent, scores[i]),
                             "admission_evaluated": i == best, "accepted": i == best and accepted,
                             "admission_gain": guard_child["accuracy"] - guard_parent["accuracy"] if i == best else None,
                             "admission_delta": task_delta(guard_parent, guard_child) if i == best else None,
                             "reason": "not_selected" if i != best else "no_development_gain" if scores[i]["correct"] <= parent["correct"] else "admission_regression" if not accepted else "development_gain_and_admission_nonregression"})
        if accepted:
            state, macros = copy.deepcopy(winner["config"]), list(winner["macros"])
        decision = {"label": prefix, "generation": generation, "attempts": attempts,
                    "best_index": best, "accepted": accepted, "config": state, "macros": macros,
                    "guard_parent_request_sha256": guard_parent["request_sha256"],
                    "guard_candidate_request_sha256": guard_child["request_sha256"], "memory_sha256": digest(memory)}
        decisions.append(decision)
        evaluator.journal.append("fragment_change_resolved", decision)
        snapshots[generation] = {"config": copy.deepcopy(state), "macros": list(macros), "memory": copy.deepcopy(memory)}
    return {"label": label, "mode": mode, "snapshots": snapshots, "decisions": decisions,
            "ranking_primitive_upper_bound": ranking_work}
