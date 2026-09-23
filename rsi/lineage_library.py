"""Immutable-parent lineage retention for V79."""

from __future__ import annotations

from .common import canonical
from .internal_body_mutation import mine_successful_mutated_bodies


def evolve_lineage_library(tasks, initial_library, max_library=24,
                           max_children_per_task=4, max_variants=128):
    """Accumulate visible-consistent children while preserving every parent."""
    library = [dict(record) for record in initial_library]
    parent_ids = {record["macro_id"] for record in library}
    events = []
    for task in tasks:
        children = mine_successful_mutated_bodies(
            task["visible"], library, max_variants=max_variants,
            max_children=max_children_per_task)
        added = []
        for child in children:
            if len(library) >= max_library:
                break
            if any(canonical(child["body"]) == canonical(existing["body"]) for existing in library):
                continue
            child = {**child, "source_tasks": [task["id"]]}
            library.append(child)
            added.append(child["macro_id"])
        events.append({"task_id": task["id"], "parent_count": len(parent_ids),
                       "children_considered": len(children), "children_added": added,
                       "library_size": len(library)})
    return library, events
