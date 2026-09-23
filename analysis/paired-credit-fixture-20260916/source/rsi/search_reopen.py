"""Search variant that reopens a syntactic state when a cheaper route arrives.

Derived from the frozen v7 kernel; the default worker still uses rsi.search.
This corrects first-arrival cost suppression, not general search optimality.
"""
from __future__ import annotations

import heapq
import math

from .common import canonical, digest
from .search import atom_pool, features, validate_config
from dsl import PosError, render, run
from parse import ParseError, parse


def solve(task: dict, config: dict, budget: int, max_atoms: int = 4, macros: list | None = None, proposals: list | None = None, diagnostics: dict | None = None) -> dict:
    validate_config(config)
    if set(task) != {"id", "visible"}:
        raise ValueError("Worker task must contain only id and visible examples")
    if not 1 <= budget <= 10000 or not 1 <= max_atoms <= 6:
        raise ValueError("Search resource bounds")
    visible = task["visible"]
    targets = [value for _, value in visible]
    pool, primitive_cost = atom_pool(canonical(visible), canonical(macros or []))
    trace, candidates = [], []
    model_checks = 0
    # Neural proposals compete with symbolic results using the same visible-only cost.
    for raw in (proposals or [])[:64]:
        text = raw.strip().splitlines()[0] if raw.strip() else ""
        if len(text) > 2048:
            continue
        try:
            prog = parse(text)
            if not 1 <= len(prog.atoms) <= max_atoms:
                continue
            outputs = []
            for inp, _ in visible:
                model_checks += 1
                outputs.append(run(prog, inp))
            if outputs == targets:
                score = sum(sum(features(atom)[key] * config[key] for key in features(atom)) + config["length_cost"] for atom in prog.atoms)
                candidates.append((score, render(prog), outputs, "model"))
        except (ValueError, ParseError, PosError, RecursionError):
            continue
    scored = []
    for item in pool:
        cost = sum(config[key] * value for key, value in item["features"].items()) + config["length_cost"] * len(item["atoms"])
        if item["macro"]:
            cost *= 1 - config["macro_discount"]
        scored.append((cost, item))
    scored.sort(key=lambda pair: (pair[0], canonical(pair[1]["atoms"])))
    counter = 0
    queue = [(0.0, counter, 0.0, (), tuple("" for _ in visible))]
    best_cost = {(): 0.0}
    reopened = 0
    expansions = 0
    generated = 0
    # Reinsert parents to progressively widen their outgoing edges.
    consumed: dict[tuple, int] = {}
    while queue and expansions < budget:
        _, _, cost, atoms, outputs = heapq.heappop(queue)
        if cost > best_cost.get(atoms, math.inf) + 1e-12:
            continue
        key = atoms
        if list(outputs) == targets:
            text = "Concat(" + ", ".join(atoms) + ")"
            candidates.append((cost, text, list(outputs), "search"))
            trace.append(["solution", text, round(cost, 9)])
            expansions += 1
            continue
        if len(atoms) >= max_atoms:
            continue
        compatible = [(atom_cost, item) for atom_cost, item in scored
                      if len(atoms) + len(item["atoms"]) <= max_atoms
                      and all(target.startswith(prefix + suffix) for target, prefix, suffix in zip(targets, outputs, item["values"]))]
        start = consumed.get(key, 0)
        width = max(2, math.ceil((expansions + 1) ** config["widening"]))
        stop = min(len(compatible), start + width)
        for atom_cost, item in compatible[start:stop]:
            next_atoms = atoms + tuple(item["atoms"])
            next_cost = cost + atom_cost
            previous_cost = best_cost.get(next_atoms, math.inf)
            if next_cost >= previous_cost - 1e-12:
                continue
            if previous_cost < math.inf:
                reopened += 1
                consumed.pop(next_atoms, None)
            best_cost[next_atoms] = next_cost
            next_outputs = tuple(left + right for left, right in zip(outputs, item["values"]))
            next_cost = cost + atom_cost
            progress = sum(len(output) / max(1, len(target)) for output, target in zip(next_outputs, targets)) / len(targets)
            priority = next_cost - config["progress_weight"] * progress
            counter += 1
            heapq.heappush(queue, (priority, counter, next_cost, next_atoms, next_outputs))
            generated += 1
        consumed[key] = stop
        if stop < len(compatible):
            counter += 1
            # Fairness: eventually return to parents as expansion budget grows.
            heapq.heappush(queue, (cost + 0.05 * stop, counter, cost, atoms, outputs))
        trace.append(["expand", list(atoms), start, stop])
        expansions += 1
    candidates.sort(key=lambda row: (row[0], len(row[1]), row[1]))
    selected = candidates[0] if candidates else None
    payload = {"task_id": task["id"], "program": selected[1] if selected else "", "visible_outputs": selected[2] if selected else [None] * len(visible),
               "source": selected[3] if selected else "none", "visible_fit": bool(selected),
               "trace_sha256": digest(trace), "cost": {"expansions": expansions, "generated_nodes": generated,
               "primitive_executions": primitive_cost, "model_checks": model_checks, "candidate_count": len(candidates)}}
    payload["kernel"] = "cost_reopening_v1"
    payload["reopened_states"] = reopened
    payload["replay_sha256"] = digest(payload)
    if diagnostics is not None:
        diagnostics.clear()
        diagnostics.update(best_costs={"Concat(" + ", ".join(k) + ")": v for k, v in best_cost.items()},
                           reopened_states=reopened, selected_cost=selected[0] if selected else None)
    return payload
