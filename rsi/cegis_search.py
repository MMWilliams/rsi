"""Visible-only counterexample-guided shortest-path synthesis.

The legacy search kernel progressively widens a heuristic queue and drops
atoms that are empty on one visible example.  This module treats the current
visible output prefixes as synthesis states instead.  A transition is a
verified atom or fragment; dynamic programming then finds the cheapest
program reaching the complete visible target within the atom budget.

Neural proposals may contribute typed DSL atoms/fragments, but they are
accepted only after the same visible-only execution and prefix checks.  Hidden
examples are never read here.
"""

from __future__ import annotations

from .common import canonical, digest
import heapq
import math

from dsl import ConstStr, PosError, render_atom, run
from parse import ParseError, parse

from .atom_pool_partial import atom_pool as partial_pool
from .search import BASE_CONFIG, features


def _cost(item: dict, config: dict) -> float:
    value = sum(config[key] * amount for key, amount in item["features"].items())
    value += config["length_cost"] * len(item["atoms"])
    if item.get("macro"):
        value *= 1 - config["macro_discount"]
    return value


def _visible_item(atoms: tuple, visible: list[list[str]], config: dict, macro: bool = False) -> dict | None:
    try:
        program = parse("Concat(" + ", ".join(atoms) + ")")
    except (ValueError, ParseError, PosError, RecursionError):
        return None
    values: list[str] = []
    for inp, target in visible:
        try:
            value = run(program, inp)
        except (ValueError, ParseError, PosError, RecursionError):
            return None
        if value not in target:
            return None
        values.append(value)
    if not any(values):
        return None
    counts = {key: 0.0 for key in features(program.atoms[0])}
    for atom in program.atoms:
        for key, amount in features(atom).items():
            counts[key] += amount
    return {"atoms": list(atoms), "values": values, "features": counts, "macro": macro}


def _proposal_items(proposals: list[str], visible: list[list[str]], max_atoms: int) -> list[dict]:
    found: dict[tuple[str, ...], dict] = {}
    for raw in (proposals or [])[:64]:
        text = raw.strip().splitlines()[0] if raw.strip() else ""
        try:
            program = parse(text)
            # Rendering through the canonical AST avoids trusting model text.
            atoms = tuple(render_atom(atom) for atom in program.atoms)
        except (ValueError, ParseError, PosError, RecursionError):
            continue
        for start in range(len(atoms)):
            for stop in range(start + 1, min(len(atoms), start + max_atoms) + 1):
                fragment = atoms[start:stop]
                item = _visible_item(fragment, visible, BASE_CONFIG, macro=len(fragment) > 1)
                if item is not None:
                    found.setdefault(fragment, item)
    return [found[key] for key in sorted(found)]


def _constant_items(visible: list[list[str]], max_length: int = 6) -> list[dict]:
    """Infer multi-character constants from the intersection of visible targets."""
    targets = [target for _, target in visible]
    if not targets:
        return []
    values = set()
    for start in range(len(targets[0])):
        for stop in range(start + 2, min(len(targets[0]), start + max_length) + 1):
            value = targets[0][start:stop]
            if all(value in target for target in targets[1:]):
                values.add(value)
    items = []
    for value in sorted(values):
        atom = render_atom(ConstStr(value))
        items.append({"atoms": [atom], "values": [value] * len(visible),
                      "features": features(ConstStr(value)), "macro": False})
    return items

def solve(task: dict, config: dict | None = None, budget: int = 128, max_atoms: int = 4,
          macros: list[str] | None = None, proposals: list[str] | None = None,
          diagnostics: dict | None = None, synthesize_constants: bool = False,
          epsilon_macros: list[str] | None = None) -> dict:
    config = dict(config or BASE_CONFIG)
    if set(task) != {"id", "visible"}:
        raise ValueError("Worker task must contain only id and visible examples")
    if not 1 <= budget <= 10000 or not 1 <= max_atoms <= 6:
        raise ValueError("Search resource bounds")
    visible = task["visible"]
    targets = tuple(value for _, value in visible)
    pool, primitive_cost = partial_pool(canonical(visible), canonical(macros or []))
    transitions: dict[tuple[str, ...], dict] = {}
    for item in pool:
        transitions.setdefault(tuple(item["atoms"]), item)
    if synthesize_constants:
        for item in _constant_items(visible):
            transitions.setdefault(tuple(item["atoms"]), item)
    for item in _proposal_items(proposals or [], visible, max_atoms):
        transitions.setdefault(tuple(item["atoms"]), item)
    epsilon_count = 0
    for raw in (epsilon_macros or [])[:256]:
        try:
            program = parse(raw)
            atoms = tuple(render_atom(atom) for atom in program.atoms)
            if not 1 <= len(atoms) <= max_atoms:
                continue
            values = []
            for inp, target in visible:
                value = run(program, inp)
                if value not in target:
                    break
                values.append(value)
            if len(values) != len(visible):
                continue
            counts = {key: 0.0 for key in features(program.atoms[0])}
            for atom in program.atoms:
                for key, amount in features(atom).items():
                    counts[key] += amount
            transitions.setdefault(atoms, {"atoms": list(atoms), "values": values,
                                             "features": counts, "macro": True, "epsilon": not any(values)})
            epsilon_count += 1
        except (ValueError, ParseError, PosError, RecursionError):
            continue
    scored = sorted(((_cost(item, config), atoms, item) for atoms, item in transitions.items()),
                    key=lambda row: (row[0], len(row[1]), canonical(row[1])))

    start_outputs = tuple("" for _ in visible)
    queue = [(0.0, 0, 0, (), start_outputs)]
    best = {(0, start_outputs): 0.0}
    candidates: list[tuple[float, tuple[str, ...], tuple[str, ...], str]] = []
    expanded = 0
    generated = 0
    while queue and expanded < budget:
        cost, _, used, atoms, outputs = heapq.heappop(queue)
        if cost > best.get((used, outputs), math.inf) + 1e-12:
            continue
        if outputs == targets and used > 0:
            candidates.append((cost, atoms, outputs, "cegis"))
            expanded += 1
            continue
        if used >= max_atoms:
            expanded += 1
            continue
        for atom_cost, item_atoms, item in scored:
            width = len(item_atoms)
            if used + width > max_atoms:
                continue
            item_values = tuple(item["values"])
            next_outputs = tuple(left + right for left, right in zip(outputs, item_values))
            if not all(target.startswith(prefix) for target, prefix in zip(targets, next_outputs)):
                continue
            next_used = used + width
            next_cost = cost + atom_cost
            key = (next_used, next_outputs)
            if next_cost >= best.get(key, math.inf) - 1e-12:
                continue
            best[key] = next_cost
            generated += 1
            heapq.heappush(queue, (next_cost, generated, next_used, atoms + item_atoms, next_outputs))
        expanded += 1

    candidates.sort(key=lambda row: (row[0], len(row[1]), canonical(row[1])))
    selected = candidates[0] if candidates else None
    program = "Concat(" + ", ".join(selected[1]) + ")" if selected else ""
    payload = {
        "task_id": task["id"],
        "program": program,
        "visible_outputs": list(selected[2]) if selected else [None] * len(visible),
        "source": selected[3] if selected else "none",
        "visible_fit": bool(selected),
        "trace_sha256": digest({"expanded": expanded, "generated": generated, "states": len(best)}),
        "cost": {"expansions": expanded, "generated_nodes": generated, "primitive_executions": primitive_cost,
                 "model_checks": 0, "candidate_count": len(candidates)},
        "kernel": "cegis_shortest_path_v1",
        "transition_count": len(scored),
        "neural_transition_count": max(0, len(scored) - len(pool)),
        "constant_transition_count": sum(1 for atoms in transitions if len(atoms) == 1 and atoms[0].startswith(("'", '"')) and
                                          any(item["atoms"] == list(atoms) for item in _constant_items(visible))),
        "epsilon_transition_count": epsilon_count,
    }
    payload["replay_sha256"] = digest(payload)
    if diagnostics is not None:
        diagnostics.clear()
        diagnostics.update({"states": len(best), "expanded": expanded, "generated": generated,
                            "transition_count": len(scored), "selected_cost": selected[0] if selected else None})
    return payload
