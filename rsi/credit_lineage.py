"""Cross-task credit and multi-generation lineage evolution for V80."""

from __future__ import annotations

from collections import defaultdict

from .common import canonical
from .internal_body_mutation import mine_successful_mutated_bodies


def evolve_credit_lineage(tasks, initial_library, generations=2, max_library=24,
                          min_support=2, max_children_per_task=4, max_variants=64,
                          reserve_grafts=False, reserve_rotate=False):
    """Accumulate children only when multiple development tasks support them."""
    library = [dict(record) for record in initial_library]
    events = []
    for generation in range(1, generations + 1):
        support = defaultdict(set)
        examples = {}
        for task in tasks:
            children = mine_successful_mutated_bodies(
                task["visible"], library, max_variants=max_variants,
                max_children=max_children_per_task, reserve_grafts=reserve_grafts,
                reserve_rotate=reserve_rotate)
            for child in children:
                key = canonical(child["body"])
                support[key].add(task["id"])
                examples[key] = child
        ranked = sorted((key for key, ids in support.items() if len(ids) >= min_support),
                        key=lambda key: (-len(support[key]), len(key), key))
        added = []
        for key in ranked:
            if len(library) >= max_library:
                break
            if any(canonical(record["body"]) == key for record in library):
                continue
            child = dict(examples[key])
            child["source_tasks"] = sorted(support[key])
            child["support_count"] = len(support[key])
            child["generation"] = generation
            library.append(child)
            added.append({"macro_id": child["macro_id"], "support_count": len(support[key]),
                          "source_tasks": sorted(support[key])})
        events.append({"generation": generation, "parent_library_size": len(library) - len(added),
                       "candidate_children": len(support), "eligible_children": len(ranked),
                       "children_added": added, "library_size": len(library),
                       "min_support": min_support})
        if not added:
            break
    return library, events
