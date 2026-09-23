"""Common visible-only candidate interface for the ten bounded components."""
from __future__ import annotations

import random
from rsi.common import digest
from rsi.evolving_domain import make_task
from rsi.invented_space import _split_atoms
from rsi.semantic_invention import evaluate_program, semantic_value
from rsi.ast_synthesis import synthesize_general_ast
from rsi.primitive_synthesis import invent_transform_expressions
from rsi.failure_invention import NOVEL_CONSTRUCTORS, synthesize_failure_driven_ast
from rsi.stack_program import synthesize_stack_programs
from rsi.meta_stack import STACK_FAMILIES
from rsi.mutation_synthesis import synthesize_mutated_stack_programs
from rsi.self_editing_grammar import SAFE_OPS, synthesize_self_edit_predicates
from rsi.macro_library import mine_macro_library, synthesize_macro_predicates
from rsi.typed_body_editor import synthesize_body_editor_predicates
from rsi.internal_body_mutation import synthesize_internal_mutation_predicates
from rsi.credit_lineage import evolve_credit_lineage
from run_ast_v66 import _direct_ast_candidates


SEMANTIC_ARMS = ("v65", "v67", "v69", "v70", "v72", "v73", "v75", "v77", "v80")
FAMILIES = ("transform_transition", "ast_transition", "novel_operator_transition",
            "stack_transition", "mutation_transition", "self_edit_transition")


def mixed_banks(config):
    rng = random.Random(config["bank_seed"])
    banks = {}
    for split, count in config["bank_counts"].items():
        rows = []
        for index in range(count):
            family = FAMILIES[index % len(FAMILIES)] if split != "train" else "macro_transition"
            row = make_task(rng, split, index, family, config["visible_examples"], config["hidden_examples"])
            row["family"] = family  # host-only analysis label; never passed to a proposer/router
            rows.append(row)
        banks[split] = rows
    return banks


def visible_outputs(program, examples):
    if not program.startswith("Concat(") or not program.endswith(")"):
        return None
    atoms = _split_atoms(program[7:-1])
    try:
        return ["".join(semantic_value(atom, text) for atom in atoms) for text, _ in examples]
    except (Exception):
        return None


def envelope(task, arm, candidate):
    program = candidate["program"]
    outputs = visible_outputs(program, task["visible"])
    targets = [target for _, target in task["visible"]]
    if outputs != targets:
        return None
    return {"program": program, "task_id": task["id"], "source": arm,
            "visible_signature": digest(outputs), "cost": candidate.get("cost", 1.0),
            "complexity": len(program), "required_operations": sorted(set(
                op for op in ("xor", "mod", "stack", "macro", "shr", "div", "mul") if op in program))}


def source_candidates(task, arm, libraries, cap):
    visible = task["visible"]
    if arm == "v65":
        predicates = invent_transform_expressions(visible)
    elif arm == "v67":
        predicates = synthesize_general_ast(visible)
    elif arm == "v69":
        predicates = synthesize_failure_driven_ast(visible, enabled=NOVEL_CONSTRUCTORS)
    elif arm == "v70":
        predicates = synthesize_stack_programs(visible, STACK_FAMILIES)
    elif arm == "v72":
        predicates, _ = synthesize_mutated_stack_programs(visible, seed=int(task["id"][:8], 16))
    elif arm == "v73":
        predicates = synthesize_self_edit_predicates(visible, SAFE_OPS)
    elif arm == "v75":
        predicates = synthesize_macro_predicates(visible, libraries["base"])
    elif arm == "v77":
        predicates = synthesize_body_editor_predicates(visible, libraries["base"], seed=int(task["id"][:8], 16))
    elif arm == "v80":
        predicates = synthesize_macro_predicates(visible, libraries["credit"])
        predicates += synthesize_internal_mutation_predicates(visible, libraries["base"], max_variants=16)
    else:
        raise ValueError(arm)
    candidates = _direct_ast_candidates({"id": task["id"], "visible": visible}, predicates)
    unique = {}
    for row in candidates:
        unique.setdefault(row["program"], row)
    ranked = sorted(unique.values(), key=lambda row: (row["cost"], len(row["program"]), row["program"]))
    return [item for row in ranked[:cap] if (item := envelope(task, arm, row)) is not None]


def libraries_from_train(train, config):
    base = mine_macro_library(train, max_macros=config["max_macros"])
    credit, trace = evolve_credit_lineage(train, base, generations=2, max_library=config["max_macros"] + 4,
                                          min_support=2, max_variants=16)
    return {"base": base, "credit": credit, "lineage_trace": trace}


def rank(candidates, allowed, priorities, cap):
    """Visible-only deterministic router; priorities come from development/admission."""
    best = {}
    for item in candidates:
        if item["source"] not in allowed:
            continue
        key = item["program"]  # signature alone would collapse every visible-perfect program
        old = best.get(key)
        if old is None or (item["cost"], item["complexity"], item["source"]) < (old["cost"], old["complexity"], old["source"]):
            best[key] = item
    return sorted(best.values(), key=lambda r: (priorities.index(r["source"]), r["cost"], r["complexity"], r["program"]))[:cap]


def selected_score(tasks, pools, allowed, priorities, cap):
    rows = []
    for task in tasks:
        candidates = rank(pools[task["id"]], allowed, priorities, cap)
        candidate = candidates[0] if candidates else None
        program = candidate["program"] if candidate else ""
        rows.append({"task_id": task["id"], "family": task["family"], "source": candidate["source"] if candidate else "none",
                     "program": program, "correct": evaluate_program(program, task["visible"] + task["hidden"])})
    return {"correct": sum(r["correct"] for r in rows), "n": len(rows), "rows": rows}
