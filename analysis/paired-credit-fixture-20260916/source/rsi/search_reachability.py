"""Exact visible-prefix reachability inside a fixed filtered atom pool."""
from .common import canonical
from .search import atom_pool
from .atom_pool_partial import atom_pool as partial_pool


def reachable(task, macros, max_atoms=4, pool_mode="baseline"):
    if set(task) != {"id", "visible"} or pool_mode not in ("baseline", "partial_empty"):
        raise ValueError("Public task and known pool mode required")
    build = atom_pool if pool_mode == "baseline" else partial_pool
    pool, primitive_charge = build(canonical(task["visible"]), canonical(macros))
    choices = {}
    for item in pool:
        values, atoms = tuple(item["values"]), tuple(item["atoms"])
        if values not in choices or (len(atoms), atoms) < (len(choices[values]), choices[values]):
            choices[values] = atoms
    targets = [out for _, out in task["visible"]]
    goal = tuple(map(len, targets))
    start = (0,) * len(targets)
    layers = [{start: ()}] + [{} for _ in range(max_atoms)]
    best = {start: 0}
    states = edges = 0
    for used in range(max_atoms + 1):
        for position, prefix in sorted(layers[used].items()):
            states += 1
            if position == goal:
                return {"reachable": True, "witness": "Concat(" + ", ".join(prefix) + ")",
                        "states": states, "edge_checks": edges, "semantic_options": len(choices),
                        "pool_primitive_charge": primitive_charge}
            for values, atoms in sorted(choices.items()):
                if used + len(atoms) > max_atoms:
                    continue
                edges += 1
                if not all(target.startswith(value, pos) for target, value, pos in zip(targets, values, position)):
                    continue
                following = tuple(p + len(v) for p, v in zip(position, values))
                count = used + len(atoms)
                if count < best.get(following, max_atoms + 1):
                    best[following] = count
                    layers[count][following] = prefix + atoms
    return {"reachable": False, "witness": None, "states": states, "edge_checks": edges,
            "semantic_options": len(choices), "pool_primitive_charge": primitive_charge}
