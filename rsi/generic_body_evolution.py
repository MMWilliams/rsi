"""Generic typed expression evolution for V83.

This module deliberately contains no rotate, popcount, gcd, or bitmix
template.  It builds serialized stack bodies bottom-up from typed leaves and
binary operators, retaining one shortest representative for each visible
behavior signature.  The visible signature is only a search index; hidden
examples are never consulted while proposing or admitting a child.
"""

from __future__ import annotations

from collections import defaultdict

from .common import canonical, digest
from .stack_program import evaluate_stack


GENERIC_CONSTANTS = (0, 1, 2, 3, 4, 5, 7, 8, 15, 31, 63, 127, 255)
GENERIC_BINARY_OPS = ("add", "sub", "mul", "xor", "and", "or", "shl", "shr", "mod")


def _aligned(visible):
    target, observed = set(), set()
    for text, value in visible:
        observed.update(text)
        if text.startswith(value) or text.endswith(value):
            target.update(value)
    return target, observed - target, sorted(observed, key=ord)


def _compile(expr):
    kind = expr[0]
    if kind == "load":
        return [{"op": "load_ord"}]
    if kind == "const":
        return [{"op": "const", "value": expr[1]}]
    return _compile(expr[1]) + _compile(expr[2]) + [{"op": kind}]


def _expr_key(expr):
    return canonical(_compile(expr))


def _apply(op, left, right):
    if op == "add":
        return left + right
    if op == "sub":
        return left - right
    if op == "mul":
        return left * right
    if op == "xor":
        return left ^ right
    if op == "and":
        return left & right
    if op == "or":
        return left | right
    if op == "shl":
        return left << right
    if op == "shr":
        return left >> right
    return left % right


def _score(values, chars, target=None, other=None):
    """Visible-only heuristic that keeps behaviorally useful beam states."""
    if not target or not other:
        return (len(set(values)), max(values) - min(values) if values else 0)
    target_indices = [i for i, char in enumerate(chars) if char in target]
    other_indices = [i for i, char in enumerate(chars) if char in other]
    best = 0
    for modulus in range(2, 10):
        reduced = [value % modulus for value in values]
        for constant in range(10):
            for relation in ("eq", "lt", "ge"):
                correct = 0
                for index in target_indices:
                    value = reduced[index]
                    if (value == constant if relation == "eq" else value < constant if relation == "lt" else value >= constant):
                        correct += 1
                for index in other_indices:
                    value = reduced[index]
                    if not (value == constant if relation == "eq" else value < constant if relation == "lt" else value >= constant):
                        correct += 1
                best = max(best, correct)
    return (best, len(set(values)), max(values) - min(values) if values else 0)


def _archive_rows(rows, chars, target, other, max_states_per_size, preserve_signatures=False):
    if not preserve_signatures:
        return sorted(rows, key=lambda row: (
            _score(row["values"], chars, target, other), repr(row["expr"])),
            reverse=True)[:max_states_per_size]
    by_signature = {}
    for row in rows:
        signature = row.get("signature", ())
        incumbent = by_signature.get(signature)
        if incumbent is None or (_score(row["values"], chars, target, other), repr(row["expr"])) > (_score(incumbent["values"], chars, target, other), repr(incumbent["expr"])):
            by_signature[signature] = row
    elites = list(by_signature.values())
    elites.sort(key=lambda row: (_score(row["values"], chars, target, other), repr(row["expr"])), reverse=True)
    return elites[:max_states_per_size]


def enumerate_typed_bodies(chars, max_nodes=11, max_states_per_size=256,
                           target=None, other=None, preserve_signatures=False):
    """Enumerate generic stack expressions, returning body records.

    Expressions are typed by the stack machine's single integer value.  A
    behavior-signature quotient keeps this search finite while preserving a
    shortest representative for every behavior observed on the current task.
    """
    states = defaultdict(list)
    leaves = {}
    load = ("load",)
    leaves[tuple(ord(char) for char in chars)] = load
    for value in GENERIC_CONSTANTS:
        expr = ("const", value)
        leaves.setdefault(tuple(value for _ in chars), expr)
    states[1] = [{"expr": expr, "values": values, "signature": ()}
                  for values, expr in leaves.items()]

    for size in range(3, max_nodes + 1, 2):
        current = {}
        for left_size in range(1, size - 1, 2):
            right_size = size - 1 - left_size
            for left in states[left_size]:
                for right in states[right_size]:
                    left_values, right_values = left["values"], right["values"]
                    for op in GENERIC_BINARY_OPS:
                        # Shift and modulus require a nonzero/nonnegative
                        # right value.  Filtering by the visible trace keeps
                        # the generic search safe without naming a task rule.
                        if op in ("shl", "shr") and any(value < 0 or value > 8 for value in right_values):
                            continue
                        if op == "mod" and any(value == 0 for value in right_values):
                            continue
                        try:
                            values = tuple(_apply(op, a, b) for a, b in zip(left_values, right_values))
                        except (ValueError, ZeroDivisionError, OverflowError):
                            continue
                        expr = (op, left["expr"], right["expr"])
                        signature = tuple(sorted(left["signature"] + right["signature"] + (op,)))
                        # MAP-Elites-style archive: preserve both visible
                        # behavior and the complete operator niche.  A
                        # simple modulo shortcut therefore cannot evict a
                        # structurally different multi-branch body.
                        current.setdefault((values, signature),
                                           {"expr": expr, "values": values,
                                            "signature": signature})
        states[size] = _archive_rows(list(current.values()), chars, target, other,
                                     max_states_per_size, preserve_signatures)

    result = []
    for size in sorted(states):
        for row in states[size]:
            expr, values = row["expr"], row["values"]
            result.append({"body": _compile(expr), "nodes": size,
                           "visible_values": list(values), "expression_key": _expr_key(expr)})
    return sorted(result, key=lambda row: (row["nodes"], row["expression_key"]))


def _body_signature(body):
    return tuple(sorted(item["op"] for item in body
                        if item["op"] not in ("load_ord", "const")))


def enumerate_hierarchical_bodies(chars, max_nodes=11, max_states_per_size=64,
                                  target=None, other=None):
    """Compose generic subexpressions into deeper balanced bodies."""
    if max_nodes < 7:
        return enumerate_typed_bodies(chars, max_nodes=max_nodes,
                                      max_states_per_size=max_states_per_size,
                                      target=target, other=other)
    sublibrary = enumerate_typed_bodies(
        chars, max_nodes=min(5, max_nodes),
        max_states_per_size=max_states_per_size, target=target, other=other,
        preserve_signatures=True)
    records = list(sublibrary)
    by_size = defaultdict(list)
    for row in sublibrary:
        by_size[row["nodes"]].append(row)
    for left_size, right_size in ((3, 3), (3, 5), (5, 3), (5, 5)):
        size = left_size + right_size + 1
        if size > max_nodes or not by_size[left_size] or not by_size[right_size]:
            continue
        current = {}
        for left in by_size[left_size]:
            for right in by_size[right_size]:
                left_values, right_values = left["visible_values"], right["visible_values"]
                for op in GENERIC_BINARY_OPS:
                    if op in ("shl", "shr") and any(value < 0 or value > 8 for value in right_values):
                        continue
                    if op == "mod" and any(value == 0 for value in right_values):
                        continue
                    try:
                        values = tuple(_apply(op, a, b) for a, b in zip(left_values, right_values))
                    except (ValueError, ZeroDivisionError, OverflowError):
                        continue
                    body = left["body"] + right["body"] + [{"op": op}]
                    signature = _body_signature(body)
                    current.setdefault((values, signature), {
                        "body": body, "nodes": size, "visible_values": list(values),
                        "expression_key": canonical(body)})
        composed_rows = [{"expr": tuple(row["body"]), "values": tuple(row["visible_values"]),
                          "signature": _body_signature(row["body"]), **row}
                         for row in current.values()]
        composed = _archive_rows(composed_rows, chars, target, other,
                                 max_states_per_size, preserve_signatures=True)
        composed = [{key: row[key] for key in ("body", "nodes", "visible_values", "expression_key")}
                    for row in composed]
        records.extend(composed)
    return sorted(records, key=lambda row: (row["nodes"], row["expression_key"]))


def build_generic_body_bank(tasks, max_nodes=11, max_states_per_size=64,
                            hierarchical=False):
    """Build one reusable body bank from development-visible symbols only."""
    observed = sorted({char for task in tasks for text, _value in task["visible"]
                       for char in text}, key=ord)
    chars = observed[:96]
    enumerator = enumerate_hierarchical_bodies if hierarchical else enumerate_typed_bodies
    return enumerator(chars, max_nodes=max_nodes,
                      max_states_per_size=max_states_per_size)


def _search_alphabet(chars, target, other, limit=96):
    """Keep all visible target symbols plus a stable diagnostic sample."""
    target_chars = [char for char in chars if char in target]
    other_chars = [char for char in chars if char in other]
    return sorted(set(target_chars + other_chars[:max(0, limit - len(target_chars))]), key=ord)


def _matches(body, chars, target_mask, other_mask):
    try:
        raw = tuple(evaluate_stack(body, char) for char in chars)
    except (IndexError, ValueError, ZeroDivisionError, OverflowError):
        return False
    for modulus in range(2, 10):
        values = tuple(value % modulus for value in raw)
        for constant in range(10):
            for relation in ("eq", "lt", "ge"):
                mask = 0
                for index, value in enumerate(values):
                    result = value == constant if relation == "eq" else value < constant if relation == "lt" else value >= constant
                    if result:
                        mask |= 1 << index
                if mask in (target_mask, other_mask):
                    return {"modulus": modulus, "constant": constant, "relation": relation,
                            "complement": mask == other_mask}
    return False


def mine_generic_children(visible, library, max_nodes=11, max_states_per_size=12000,
                          max_children=8, hierarchical=False):
    """Find visible-consistent replacement bodies for immutable parents."""
    target, other, chars = _aligned(visible)
    if not target or not other:
        return []
    target_mask = sum(1 << index for index, char in enumerate(chars) if char in target)
    other_mask = sum(1 << index for index, char in enumerate(chars) if char in other)
    search_chars = _search_alphabet(chars, target, other)
    enumerator = enumerate_hierarchical_bodies if hierarchical else enumerate_typed_bodies
    bodies = enumerator(search_chars, max_nodes=max_nodes,
                        max_states_per_size=max_states_per_size,
                        target=target, other=other)
    if hierarchical:
        # The hierarchical archive is a novelty-search arm: expose deeper
        # surviving bodies to cross-task credit before short shortcuts.
        def novelty(row):
            ops = [item["op"] for item in row["body"]
                   if item["op"] not in ("load_ord", "const")]
            return (len(set(ops)), len(ops),
                    sum(item["op"] == "load_ord" for item in row["body"]))
        bodies = sorted(bodies, key=lambda row: (-row["nodes"],
                                                 tuple(-value for value in novelty(row)),
                                                 row["expression_key"]))
    found, seen = [], set()
    for record in bodies:
        body = record["body"]
        key = canonical(body)
        if any(canonical(parent["body"]) == key for parent in library):
            continue
        match = _matches(body, chars, target_mask, other_mask)
        if not match or key in seen:
            continue
        seen.add(key)
        found.append({"macro_id": "generic_child_" + digest(body)[:12], "body": body,
                      "uses": 1, "source_tasks": [], "body_instructions": len(body),
                      "inline_bytes": len(key), "call_bytes": 48,
                      "parent_macro_id": library[0]["macro_id"] if library else "none",
                      "mutation_edit": "generic_replace",
                      "generic_nodes": record["nodes"], "visible_match": match})
        if len(found) >= max_children:
            break
    return found


def mine_generic_children_from_records(visible, library, body_records,
                                       max_children=8, hierarchical=False):
    """Apply a frozen generic body bank to one task without new search."""
    target, other, chars = _aligned(visible)
    if not target or not other:
        return []
    target_mask = sum(1 << index for index, char in enumerate(chars) if char in target)
    other_mask = sum(1 << index for index, char in enumerate(chars) if char in other)
    records = list(body_records)
    if hierarchical:
        def novelty(row):
            ops = [item["op"] for item in row["body"]
                   if item["op"] not in ("load_ord", "const")]
            return (len(set(ops)), len(ops),
                    sum(item["op"] == "load_ord" for item in row["body"]))
        records = sorted(records, key=lambda row: (-row["nodes"],
                                                   tuple(-value for value in novelty(row)),
                                                   row["expression_key"]))
    found, seen = [], set()
    parent_keys = {canonical(parent["body"]) for parent in library}
    for record in records:
        body = record["body"]
        key = canonical(body)
        if key in parent_keys or key in seen:
            continue
        match = _matches(body, chars, target_mask, other_mask)
        if not match:
            continue
        seen.add(key)
        found.append({"macro_id": "generic_child_" + digest(body)[:12], "body": body,
                      "uses": 1, "source_tasks": [], "body_instructions": len(body),
                      "inline_bytes": len(key), "call_bytes": 48,
                      "parent_macro_id": library[0]["macro_id"] if library else "none",
                      "mutation_edit": "generic_replace", "generic_nodes": record["nodes"],
                      "visible_match": match})
        if len(found) >= max_children:
            break
    return found


def synthesize_generic_mutation_predicates(visible, library, max_nodes=11,
                                           max_states_per_size=12000, max_predicates=512,
                                           hierarchical=False):
    """Turn generic visible-consistent bodies into executable ordinal predicates."""
    target, other, chars = _aligned(visible)
    if not target or not other:
        return []
    target_mask = sum(1 << index for index, char in enumerate(chars) if char in target)
    other_mask = sum(1 << index for index, char in enumerate(chars) if char in other)
    parents = library or [{"macro_id": "none", "body": []}]
    predicates, seen = [], set()
    search_chars = _search_alphabet(chars, target, other)
    enumerator = enumerate_hierarchical_bodies if hierarchical else enumerate_typed_bodies
    for record in enumerator(search_chars, max_nodes=max_nodes,
                             max_states_per_size=max_states_per_size,
                             target=target, other=other):
        body, key = record["body"], canonical(record["body"])
        match = _matches(body, chars, target_mask, other_mask)
        if not match:
            continue
        relation = match["relation"]
        reduced = {"op": "mod", "arg": {"op": "stack", "instructions": body},
                   "modulus": match["modulus"]}
        atom = {"op": relation, "left": reduced, "right": match["constant"]}
        final = {"op": "not", "arg": atom} if match["complement"] else atom
        expr_key = canonical(final)
        if expr_key in seen:
            continue
        seen.add(expr_key)
        predicates.append({"kind": "ord_expr", "expr": final, "complexity": len(expr_key),
                           "macro_source": "generic_body_evolution",
                           "parent_macro_id": parents[0]["macro_id"],
                           "mutation_edit": "generic_replace", "mutation_body_digest": digest(body),
                           "generic_nodes": record["nodes"]})
        if len(predicates) >= max_predicates:
            break
    return sorted(predicates, key=lambda row: (row["complexity"], canonical(row["expr"])))


def synthesize_generic_predicates_from_records(visible, library, body_records,
                                               max_predicates=512, hierarchical=False):
    """Replay a frozen generic body bank against one visible task."""
    target, other, chars = _aligned(visible)
    if not target or not other:
        return []
    target_mask = sum(1 << index for index, char in enumerate(chars) if char in target)
    other_mask = sum(1 << index for index, char in enumerate(chars) if char in other)
    records = list(body_records)
    if hierarchical:
        records = sorted(records, key=lambda row: (-row["nodes"], row["expression_key"]))
    parents = library or [{"macro_id": "none", "body": []}]
    predicates, seen = [], set()
    for record in records:
        body = record["body"]
        match = _matches(body, chars, target_mask, other_mask)
        if not match:
            continue
        reduced = {"op": "mod", "arg": {"op": "stack", "instructions": body},
                   "modulus": match["modulus"]}
        atom = {"op": match["relation"], "left": reduced, "right": match["constant"]}
        final = {"op": "not", "arg": atom} if match["complement"] else atom
        key = canonical(final)
        if key in seen:
            continue
        seen.add(key)
        predicates.append({"kind": "ord_expr", "expr": final, "complexity": len(key),
                           "macro_source": "generic_body_evolution",
                           "parent_macro_id": parents[0]["macro_id"],
                           "mutation_edit": "generic_replace", "mutation_body_digest": digest(body),
                           "generic_nodes": record["nodes"]})
        if len(predicates) >= max_predicates:
            break
    return sorted(predicates, key=lambda row: (row["complexity"], canonical(row["expr"])))


def synthesize_library_body_predicates(visible, library, max_predicates=512,
                                       source="generic_lineage", encodings=("identity",)):
    """Replay only bodies that were actually retained by the lineage."""
    target, other, chars = _aligned(visible)
    if not target or not other:
        return []
    target_mask = sum(1 << index for index, char in enumerate(chars) if char in target)
    other_mask = sum(1 << index for index, char in enumerate(chars) if char in other)
    predicates, seen = [], set()
    for macro in library:
        for encoding in encodings:
            body = [{**item, "encoding": encoding} if item.get("op") == "load_ord" else dict(item)
                    for item in macro["body"]]
            if encoding == "identity":
                body = macro["body"]
            match = _matches(body, chars, target_mask, other_mask)
            if not match:
                continue
            reduced = {"op": "mod", "arg": {"op": "stack", "instructions": body},
                       "modulus": match["modulus"]}
            atom = {"op": match["relation"], "left": reduced, "right": match["constant"]}
            final = {"op": "not", "arg": atom} if match["complement"] else atom
            key = canonical(final)
            if key in seen:
                continue
            seen.add(key)
            predicates.append({"kind": "ord_expr", "expr": final, "complexity": len(key),
                               "macro_source": source, "macro_ids": [macro["macro_id"]],
                               "parent_macro_id": macro["macro_id"],
                               "mutation_edit": macro.get("mutation_edit", "retained_body"),
                               "mutation_body_digest": digest(body), "encoding": encoding})
            if len(predicates) >= max_predicates:
                break
        if len(predicates) >= max_predicates:
            break
    return sorted(predicates, key=lambda row: (row["complexity"], canonical(row["expr"])))


def synthesize_encoding_adaptive_library_predicates(visible, library, encodings,
                                                    max_predicates=512,
                                                    source="encoding_adaptive_lineage"):
    """Test retained bodies under a bounded representation hypothesis set."""
    return synthesize_library_body_predicates(
        visible, library, max_predicates=max_predicates, source=source,
        encodings=tuple(encodings))


def evolve_generic_lineage(tasks, initial_library, generations=2, max_library=24,
                           min_support=2, max_children_per_task=8, max_nodes=7,
                           max_states_per_size=16, hierarchical=False, body_records=None):
    """Grow an immutable body lineage using generic typed composition only."""
    library = [dict(record) for record in initial_library]
    events = []
    for generation in range(1, generations + 1):
        support = defaultdict(set)
        examples = {}
        for task in tasks:
            if body_records is None:
                children = mine_generic_children(
                    task["visible"], library, max_nodes=max_nodes,
                    max_states_per_size=max_states_per_size,
                    max_children=max_children_per_task, hierarchical=hierarchical)
            else:
                children = mine_generic_children_from_records(
                    task["visible"], library, body_records,
                    max_children=max_children_per_task, hierarchical=hierarchical)
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
                       "min_support": min_support, "max_nodes": max_nodes,
                       "max_states_per_size": max_states_per_size,
                       "hierarchical": hierarchical})
        if not added:
            break
    return library, events
