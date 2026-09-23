"""Bounded visible version-space enumeration for meta-selection experiments."""

from __future__ import annotations

import heapq
import math

from .atom_pool_partial import atom_pool
from .cegis_search import _constant_items, _cost, _proposal_items
from .common import canonical
from .search import BASE_CONFIG, features
from dsl import PosError, render_atom, run
from parse import ParseError, parse


def enumerate_candidates(task: dict, config: dict | None = None, max_atoms: int = 4,
                         macros: list[str] | None = None, proposals: list[str] | None = None,
                         synthesize_constants: bool = False, limit: int = 64,
                         state_beam: int = 8, budget: int = 4096,
                         epsilon_macros: list[str] | None = None) -> list[dict]:
    """Keep several paths per visible state, preserving semantic alternatives."""
    config = dict(config or BASE_CONFIG)
    visible = task["visible"]
    targets = tuple(value for _, value in visible)
    pool, _ = atom_pool(canonical(visible), canonical(macros or []))
    transitions: dict[tuple[str, ...], dict] = {tuple(item["atoms"]): item for item in pool}
    if synthesize_constants:
        for item in _constant_items(visible):
            transitions.setdefault(tuple(item["atoms"]), item)
    for item in _proposal_items(proposals or [], visible, max_atoms):
        transitions.setdefault(tuple(item["atoms"]), item)
    # Epsilon macros are learned from prior counterexample-guided episodes.
    # They are allowed to emit an empty string on every visible example; the
    # ordinary atom pool intentionally removes such transitions.
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
            if len(values) != len(visible) or any(values):
                continue
            counts = {key: 0.0 for key in features(program.atoms[0])}
            for atom in program.atoms:
                for key, amount in features(atom).items():
                    counts[key] += amount
            transitions.setdefault(atoms, {"atoms": list(atoms), "values": values,
                                             "features": counts, "macro": True, "epsilon": True})
        except (ValueError, ParseError, PosError, RecursionError):
            continue
    scored = sorted(((_cost(item, config), atoms, item) for atoms, item in transitions.items()),
                    key=lambda row: (row[0], len(row[1]), canonical(row[1])))

    start_outputs = tuple("" for _ in visible)
    queue = [(0.0, 0, 0, (), start_outputs)]
    paths: dict[tuple[int, tuple[str, ...]], list[tuple[float, tuple[str, ...]]]] = {(0, start_outputs): [(0.0, ())]}
    terminals: dict[tuple[str, ...], float] = {}
    counter = 0
    expanded = 0
    while queue and expanded < budget:
        cost, _, used, atoms, outputs = heapq.heappop(queue)
        state = (used, outputs)
        known = {path: value for value, path in paths.get(state, [])}
        if known.get(atoms, math.inf) < cost - 1e-12:
            continue
        if outputs == targets and used > 0:
            terminals[atoms] = min(cost, terminals.get(atoms, math.inf))
            expanded += 1
            continue
        if used >= max_atoms:
            expanded += 1
            continue
        for transition_cost, transition_atoms, item in scored:
            width = len(transition_atoms)
            if used + width > max_atoms:
                continue
            next_outputs = tuple(left + right for left, right in zip(outputs, item["values"]))
            if not all(target.startswith(prefix) for target, prefix in zip(targets, next_outputs)):
                continue
            next_used = used + width
            next_cost = cost + transition_cost
            next_state = (next_used, next_outputs)
            candidates = paths.setdefault(next_state, [])
            if any(existing_atoms == atoms + transition_atoms for _, existing_atoms in candidates):
                continue
            candidates.append((next_cost, atoms + transition_atoms))
            candidates.sort(key=lambda row: (row[0], canonical(row[1])))
            del candidates[state_beam:]
            if any(existing_atoms == atoms + transition_atoms for _, existing_atoms in candidates):
                counter += 1
                heapq.heappush(queue, (next_cost, counter, next_used, atoms + transition_atoms, next_outputs))
        expanded += 1

    rows = [{"program": "Concat(" + ", ".join(atoms) + ")", "cost": cost,
             "atom_count": len(atoms)} for atoms, cost in terminals.items()]
    rows.sort(key=lambda row: (row["cost"], row["atom_count"], row["program"]))
    return rows[:limit]
