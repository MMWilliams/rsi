"""Bounded architecture mutations for recursive improver experiments."""

from __future__ import annotations

import copy

from .cegis_search import solve as cegis_solve
from .search import BASE_CONFIG
from .search_diagnostic import solve as diagnostic_solve


def architecture_id(architecture: dict) -> str:
    fields = [architecture["engine"], str(architecture["budget"]), str(architecture["max_atoms"]),
              str(architecture["synthesize_constants"]), str(architecture["progress_weight"]),
              str(architecture["widening"])]
    return "arch_" + "_".join(fields)


def base_architecture() -> dict:
    return {"engine": "baseline", "budget": 128, "max_atoms": 4,
            "synthesize_constants": False, "progress_weight": 1.0, "widening": 0.5}


def mutate(parent: dict) -> list[dict]:
    """Generate a finite, auditable neighborhood around one architecture."""
    result = []

    def add(**updates):
        candidate = copy.deepcopy(parent)
        candidate.update(updates)
        if candidate["engine"] != "cegis":
            candidate["synthesize_constants"] = False
        if candidate not in result:
            result.append(candidate)

    for engine in ("partial", "cegis"):
        add(engine=engine)
    add(engine="cegis", synthesize_constants=True)
    add(budget=256)
    add(max_atoms=5)
    add(progress_weight=0.75)
    add(progress_weight=1.25)
    add(widening=0.4)
    add(widening=0.7)
    if parent["engine"] == "cegis":
        add(engine="cegis", budget=256, max_atoms=5, synthesize_constants=True)
    for candidate in result:
        candidate["id"] = architecture_id(candidate)
    return result


def run_architecture(architecture: dict, task: dict, macros: list[str]) -> dict:
    config = dict(BASE_CONFIG)
    config["progress_weight"] = architecture["progress_weight"]
    config["widening"] = architecture["widening"]
    if architecture["engine"] == "baseline":
        return diagnostic_solve({"id": task["id"], "visible": task["visible"]}, config,
                                architecture["budget"], architecture["max_atoms"], macros, [], pool_mode="baseline")
    if architecture["engine"] == "partial":
        return diagnostic_solve({"id": task["id"], "visible": task["visible"]}, config,
                                architecture["budget"], architecture["max_atoms"], macros, [], pool_mode="partial_empty")
    if architecture["engine"] == "cegis":
        return cegis_solve({"id": task["id"], "visible": task["visible"]}, config,
                           architecture["budget"], architecture["max_atoms"], macros, [],
                           synthesize_constants=architecture["synthesize_constants"])
    raise ValueError(architecture["engine"])
