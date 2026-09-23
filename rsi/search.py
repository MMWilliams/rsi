"""Visible-example-only, bounded graph search over the trapdoor DSL.

GATS-inspired progressive widening and syntactic transpositions. This is a
dedicated implementation, not the legacy GATS benchmark agent.
"""
from __future__ import annotations

import heapq
import math

from .common import canonical, digest
from dsl import Case, Concat, ConstStr, CPos, MatchPos, PosError, SubStr, eval_atom, render, render_atom, run
from parse import ParseError, parse

BOUNDS = {"absolute_cost": (0.1, 4.0), "match_cost": (0.1, 4.0), "constant_cost": (0.1, 4.0),
          "case_cost": (0.1, 4.0), "length_cost": (0.02, 1.5), "progress_weight": (0.1, 4.0),
          "widening": (0.25, 1.0), "macro_discount": (0.0, 0.8)}
BASE_CONFIG = {"absolute_cost": 1.0, "match_cost": 1.0, "constant_cost": 1.0, "case_cost": 1.0,
               "length_cost": 0.15, "progress_weight": 1.0, "widening": 0.5, "macro_discount": 0.25}


def validate_config(config: dict) -> dict:
    if set(config) != set(BOUNDS):
        raise ValueError("Unexpected or missing search fields")
    for key, value in config.items():
        if type(value) not in (int, float) or not math.isfinite(value) or not BOUNDS[key][0] <= value <= BOUNDS[key][1]:
            raise ValueError(f"Invalid field {key}")
    return dict(config)


def features(atom) -> dict:
    counts = {"absolute_cost": 0, "match_cost": 0, "constant_cost": 0, "case_cost": 0}
    if isinstance(atom, ConstStr):
        counts["constant_cost"] = 1 + len(atom.s) / 8
    elif isinstance(atom, SubStr):
        for position in (atom.start, atom.end):
            counts["absolute_cost" if isinstance(position, CPos) else "match_cost"] += 0.5
    elif isinstance(atom, Case):
        counts = features(atom.atom)
        counts["case_cost"] += 0.5
    return counts


def atom_pool(serialized_visible: str, serialized_macros: str):
    import json
    visible = json.loads(serialized_visible)
    macros = json.loads(serialized_macros)
    positions = [CPos(i) for i in range(-8, 9)]
    positions += [MatchPos(token, n, side) for token in ("WORD", "DIGITS", "UPPER", "LOWER") for n in (1, 2) for side in ("start", "end")]
    constants = {" ", "-", "/", ".", ", ", ": "}
    # Constants may only be inferred from outputs visible to the worker.
    constants.update(character for _, output in visible for character in output if not character.isalnum())
    atoms = [ConstStr(value) for value in sorted(constants)]
    for start in positions:
        for end in positions:
            atom = SubStr(start, end)
            atoms.extend([atom, Case("upper", atom), Case("lower", atom), Case("cap", atom)])
    pool, primitive_executions = [], 0
    for atom in atoms:
        values = []
        for inp, target in visible:
            primitive_executions += 1
            try:
                out = eval_atom(atom, inp)
            except PosError:
                break
            # Concat can only grow by appending; this pruning is exact.
            if not out or out not in target:
                break
            values.append(out)
        if len(values) == len(visible):
            pool.append({"atoms": [render_atom(atom)], "values": values, "features": features(atom), "macro": False})
    for text in macros[:32]:
        try:
            program = parse(text)
            values = []
            for inp, target in visible:
                primitive_executions += len(program.atoms)
                out = run(program, inp)
                if not out or out not in target:
                    break
                values.append(out)
            if len(values) == len(visible) and len(program.atoms) <= 3:
                counts = {key: 0 for key in features(ConstStr(""))}
                for atom in program.atoms:
                    for key, value in features(atom).items():
                        counts[key] += value
                pool.append({"atoms": [render_atom(atom) for atom in program.atoms], "values": values, "features": counts, "macro": True})
        except (ValueError, ParseError, PosError, RecursionError):
            continue
    pool.sort(key=lambda item: canonical(item["atoms"]))
    return pool, primitive_executions


def solve(task: dict, config: dict, budget: int, max_atoms: int = 4, macros: list | None = None, proposals: list | None = None) -> dict:
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
    seen = set()
    expansions = 0
    generated = 0
    # Reinsert parents to progressively widen their outgoing edges.
    consumed: dict[tuple, int] = {}
    while queue and expansions < budget:
        _, _, cost, atoms, outputs = heapq.heappop(queue)
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
            if next_atoms in seen:
                continue
            seen.add(next_atoms)
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
    payload["replay_sha256"] = digest(payload)
    return payload
