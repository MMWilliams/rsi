"""Version-space enumeration with learned macros counted as one transition."""

from __future__ import annotations

import heapq
import math

from .atom_pool_partial import atom_pool
from .cegis_search import _constant_items, _cost
from .common import canonical
from .search import BASE_CONFIG, features
from dsl import PosError, render_atom, run
from parse import ParseError, parse


def _macro_item(program: str, visible: list[list[str]]) -> dict | None:
    try:
        parsed = parse(program)
        if not 1 <= len(parsed.atoms):
            return None
        values = []
        for inp, target in visible:
            value = run(parsed, inp)
            if not value or value not in target:
                return None
            values.append(value)
        counts = {key: 0.0 for key in features(parsed.atoms[0])}
        for atom in parsed.atoms:
            for key, amount in features(atom).items():
                counts[key] += amount
        return {"atoms": [render_atom(atom) for atom in parsed.atoms], "values": values,
                "features": counts, "macro": True, "width": 1}
    except (ValueError, ParseError, PosError, RecursionError):
        return None


def enumerate_compressed(task: dict, config: dict | None = None, search_width: int = 2,
                         macros: list[str] | None = None, compressed_macros: list[str] | None = None,
                         synthesize_constants: bool = False, limit: int = 256,
                         state_beam: int = 8, budget: int = 4096) -> list[dict]:
    config = dict(config or BASE_CONFIG)
    visible = task["visible"]
    targets = tuple(value for _, value in visible)
    pool, _ = atom_pool(canonical(visible), canonical(macros or []))
    transitions = {}
    for item in pool:
        key = tuple(item["atoms"])
        transitions.setdefault(key, {**item, "width": len(key)})
    if synthesize_constants:
        for item in _constant_items(visible):
            key = tuple(item["atoms"])
            transitions.setdefault(key, {**item, "width": len(key)})
    for raw in (compressed_macros or [])[:512]:
        item = _macro_item(raw, visible)
        if item is not None:
            transitions.setdefault(tuple(item["atoms"]), item)
    scored = sorted(((_cost(item, config), atoms, item) for atoms, item in transitions.items()),
                    key=lambda row: (row[0], len(row[1]), canonical(row[1])))
    queue = [(0.0, 0, 0, (), tuple("" for _ in visible))]
    paths = {(0, tuple("" for _ in visible)): [(0.0, ())]}
    terminals = {}
    counter = expanded = 0
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
        if used >= search_width:
            expanded += 1
            continue
        for transition_cost, transition_atoms, item in scored:
            width = item["width"]
            if used + width > search_width:
                continue
            next_outputs = tuple(left + right for left, right in zip(outputs, item["values"]))
            if not all(target.startswith(prefix) for target, prefix in zip(targets, next_outputs)):
                continue
            next_used = used + width
            next_cost = cost + transition_cost
            next_atoms = atoms + transition_atoms
            next_state = (next_used, next_outputs)
            candidates = paths.setdefault(next_state, [])
            if any(existing_atoms == next_atoms for _, existing_atoms in candidates):
                continue
            candidates.append((next_cost, next_atoms))
            candidates.sort(key=lambda row: (row[0], canonical(row[1])))
            del candidates[state_beam:]
            if any(existing_atoms == next_atoms for _, existing_atoms in candidates):
                counter += 1
                heapq.heappush(queue, (next_cost, counter, next_used, next_atoms, next_outputs))
        expanded += 1
    rows = [{"program": "Concat(" + ", ".join(atoms) + ")", "cost": cost,
             "atom_count": len(atoms), "search_width": None} for atoms, cost in terminals.items()]
    # Recovering width from the path is unnecessary for selection; the expanded
    # program is the auditable semantic object and atom_count remains explicit.
    rows.sort(key=lambda row: (row["cost"], row["atom_count"], row["program"]))
    return rows[:limit]
