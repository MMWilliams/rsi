"""Bounded semantic-operator invention for the V50 shifted domain."""

from __future__ import annotations

import heapq
import json
import math
import re
import unicodedata

from .atom_pool_partial import atom_pool
from .cegis_search import _constant_items, _cost
from .common import canonical, digest
from .search import BASE_CONFIG
from dsl import PosError, run
from parse import ParseError, parse
from .invented_space import _split_atoms


_SEMANTIC_RE = re.compile(r'^(?P<op>Before|After)\((?P<delimiter>"(?:[^"\\]|\\.)*"),(?P<ordinal>[12])\)$')
_SPAN_RE = re.compile(r'^Slice\((?P<left>"(?:[^"\\]|\\.)*"),(?P<right>"(?:[^"\\]|\\.)*")\)$')


def render_semantic(op: str, delimiter: str, ordinal: int = 1) -> str:
    if op not in ("Before", "After") or ordinal not in (1, 2) or not delimiter:
        raise ValueError("invalid semantic operator")
    return f"{op}({json.dumps(delimiter, ensure_ascii=True)},{ordinal})"


def parse_semantic(atom: str):
    match = _SEMANTIC_RE.fullmatch(atom)
    if not match:
        return None
    return match.group("op").lower(), json.loads(match.group("delimiter")), int(match.group("ordinal"))


def render_span(left: dict, right: dict) -> str:
    left_token = json.dumps(json.dumps(left, sort_keys=True, separators=(',', ':')))
    right_token = json.dumps(json.dumps(right, sort_keys=True, separators=(',', ':')))
    return f"Slice({left_token},{right_token})"


def parse_span(atom: str):
    match = _SPAN_RE.fullmatch(atom)
    if not match:
        return None
    return json.loads(json.loads(match.group("left"))), json.loads(json.loads(match.group("right")))


def _resolve_boundary(boundary: dict, text: str) -> int:
    if boundary == {"kind": "start"}:
        return 0
    if boundary == {"kind": "end"}:
        return len(text)
    if boundary.get("kind") != "delimiter":
        if boundary.get("kind") == "run":
            runs = []
            predicate = boundary["predicate"]
            index = 0
            while index < len(text):
                if not _char_predicate(text[index], predicate):
                    index += 1
                    continue
                start = index
                while index < len(text) and _char_predicate(text[index], predicate):
                    index += 1
                runs.append((start, index))
            if not 1 <= boundary["ordinal"] <= len(runs):
                raise PosError("span run absent")
            start, end = runs[boundary["ordinal"] - 1]
            return start if boundary["side"] == "start" else end
        if boundary.get("kind") != "transition":
            raise PosError("unknown span boundary")
        positions = []
        for index in range(1, len(text)):
            if _char_class(text[index - 1]) == boundary["from"] and _char_class(text[index]) == boundary["to"]:
                positions.append(index)
        if not 1 <= boundary["ordinal"] <= len(positions):
            raise PosError("span transition absent")
        return positions[boundary["ordinal"] - 1]
    delimiter, ordinal, side = boundary["value"], boundary["ordinal"], boundary["side"]
    positions = [i for i in range(len(text)) if text.startswith(delimiter, i)]
    if not 1 <= ordinal <= len(positions):
        raise PosError("span delimiter absent")
    index = positions[ordinal - 1]
    return index if side == "start" else index + len(delimiter)


def _char_class(char: str) -> str:
    if char.isalpha():
        return "letter"
    if char.isdigit():
        return "digit"
    if char.isspace():
        return "space"
    if not char.isalnum():
        return "punct"
    return "other"


def _char_signature(char: str) -> tuple:
    """Return an unlabeled structural signature used by V54 induction."""
    return (unicodedata.category(char), char.isupper(), char.islower(),
            char.isdigit(), char.isalpha(), char.isspace(), char.isalnum())


def _eval_ord_expr(expr: dict, char: str):
    """Evaluate the small, typed ordinal expression language used by V64."""
    if isinstance(expr, (int, float)):
        return expr
    op = expr.get("op")
    if op == "ord":
        return ord(char)
    if op == "mod":
        return _eval_ord_expr(expr["arg"], char) % int(expr["modulus"])
    if op == "bit":
        return (_eval_ord_expr(expr["arg"], char) >> int(expr["position"])) & 1
    if op in ("add", "sub", "mul", "xor", "and", "or"):
        left = _eval_ord_expr(expr["left"], char)
        right = _eval_ord_expr(expr["right"], char)
        return {"add": left + right, "sub": left - right, "mul": left * right, "xor": left ^ right,
                "and": left & right, "or": left | right}[op]
    if op == "div":
        return _eval_ord_expr(expr["left"], char) // int(expr["divisor"])
    if op == "shr":
        return _eval_ord_expr(expr["arg"], char) >> int(expr["position"])
    if op == "mask":
        return _eval_ord_expr(expr["arg"], char) & int(expr["mask"])
    if op == "popcount":
        return int(_eval_ord_expr(expr["arg"], char)).bit_count()
    if op == "parity":
        return int(_eval_ord_expr(expr["arg"], char)).bit_count() % 2
    if op == "rotl":
        value = int(_eval_ord_expr(expr["arg"], char))
        width = int(expr["width"])
        shift = int(expr["shift"]) % width
        mask = (1 << width) - 1
        value &= mask
        return ((value << shift) | (value >> (width - shift))) & mask
    if op == "gcd":
        return math.gcd(int(_eval_ord_expr(expr["left"], char)), int(expr["right"]))
    if op in ("bool_or", "bool_and", "bool_xor"):
        left = bool(_eval_ord_expr(expr["left"], char))
        right = bool(_eval_ord_expr(expr["right"], char))
        return {"bool_or": left or right, "bool_and": left and right,
                "bool_xor": left != right}[op]
    if op in ("eq", "neq", "lt", "le", "gt", "ge"):
        left = _eval_ord_expr(expr["left"], char)
        right = _eval_ord_expr(expr["right"], char)
        return {"eq": left == right, "neq": left != right, "lt": left < right,
                "le": left <= right, "gt": left > right, "ge": left >= right}[op]
    if op == "not":
        return not _eval_ord_expr(expr["arg"], char)
    if op == "stack":
        from .stack_program import evaluate_stack
        return evaluate_stack(expr["instructions"], char)
    if op == "macro":
        from .stack_program import evaluate_stack
        value = evaluate_stack(expr["body"], char)
        modulus = expr.get("modulus")
        return value if modulus is None else value % int(modulus)
    raise ValueError("unknown ordinal expression")


def induce_signature_predicates(visible: list[list[str]]) -> list[dict]:
    """Discover character-run predicates from observed character structure.

    The returned predicates have no human semantic names.  They are frozen
    structural signatures, so a predicate learned on one bank can be replayed
    on another bank without reintroducing an alpha/digit vocabulary.
    """
    # The first Unicode-category symbol is a learned structural family (L, N,
    # P, Z, ...). It groups Lu/Ll together without naming the group alpha or
    # digit, while remaining frozen and replayable across domains.
    families = {unicodedata.category(char)[0] for text, _target in visible for char in text}
    return [{"kind": "category_family", "value": family}
            for family in sorted(families)]


def induce_ord_range_predicates(visible: list[list[str]]) -> list[dict]:
    """Induce raw code-point intervals separated by observed output cuts.

    This deliberately uses no Unicode categories or semantic names.  Output
    prefix/suffix alignment identifies boundary glyphs; the learner then forms
    maximal observed code-point intervals between those glyphs.
    """
    codes = {ord(char) for text, _target in visible for char in text}
    boundary_codes = set()
    for text, target in visible:
        if text.startswith(target) and len(text) > len(target):
            boundary_codes.add(ord(text[len(target)]))
        if text.endswith(target) and len(text) > len(target):
            boundary_codes.add(ord(text[len(text) - len(target) - 1]))
    if not boundary_codes:
        return []
    ordered = sorted(boundary_codes)
    edges = [ordered[0] - 1, *ordered, max(codes) + 1]
    predicates = []
    for left, right in zip(edges, edges[1:]):
        members = sorted(code for code in codes if left < code < right and code not in boundary_codes)
        if not members:
            continue
        blocks = [[members[0]]]
        for code in members[1:]:
            if code - blocks[-1][-1] > 4:
                blocks.append([code])
            else:
                blocks[-1].append(code)
        for start in range(len(blocks)):
            for end in range(start, len(blocks)):
                predicates.append({"kind": "ord_range", "lo": blocks[start][0], "hi": blocks[end][-1]})
    return predicates


def _char_predicate(char: str, predicate) -> bool:
    if isinstance(predicate, dict) and predicate.get("kind") == "ord_expr":
        try:
            return _eval_ord_expr(predicate["expr"], char) is True
        except (KeyError, TypeError, ValueError, OverflowError):
            return False
    if isinstance(predicate, dict) and predicate.get("kind") == "signature":
        return tuple(predicate.get("signature", ())) == _char_signature(char)
    if isinstance(predicate, dict) and predicate.get("kind") == "category_family":
        return unicodedata.category(char).startswith(predicate.get("value", "\0"))
    if isinstance(predicate, dict) and predicate.get("kind") == "category_exact":
        return unicodedata.category(char) == predicate.get("value")
    if isinstance(predicate, dict) and predicate.get("kind") == "ord_range":
        return predicate.get("lo", 1) <= ord(char) <= predicate.get("hi", 0)
    if isinstance(predicate, dict) and predicate.get("kind") == "method":
        try:
            result = getattr(char, predicate["name"])()
        except (AttributeError, TypeError, ValueError):
            return False
        return result is True
    if isinstance(predicate, dict) and predicate.get("kind") == "char_set":
        return char in set(predicate.get("values", ()))
    if isinstance(predicate, dict) and predicate.get("kind") == "ord_mod":
        value = ord(char) % predicate["modulus"] == predicate["residue"]
        return not value if predicate.get("invert", False) else value
    if isinstance(predicate, dict) and predicate.get("kind") == "ord_bit":
        value = ((ord(char) >> predicate["position"]) & 1) == 1
        return not value if predicate.get("invert", False) else value
    predicates = {"alpha": char.isalpha, "digit": char.isdigit, "space": char.isspace,
                  "punct": lambda: not char.isalnum() and not char.isspace(),
                  "upper": char.isupper, "lower": char.islower, "alnum": char.isalnum}
    return predicates.get(predicate, lambda: False)()


def span_value(atom: str, text: str) -> str:
    parsed = parse_span(atom)
    if parsed is None:
        raise ValueError("not a span")
    left, right = (_resolve_boundary(boundary, text) for boundary in parsed)
    if left > right:
        raise PosError("reversed span")
    return text[left:right]


def semantic_value(atom: str, text: str) -> str:
    if parse_span(atom) is not None:
        return span_value(atom, text)
    parsed = parse_semantic(atom)
    if parsed is None:
        return run(parse("Concat(" + atom + ")"), text)
    op, delimiter, ordinal = parsed
    starts = []
    cursor = 0
    while True:
        index = text.find(delimiter, cursor)
        if index < 0:
            break
        starts.append(index)
        cursor = index + len(delimiter)
    if ordinal > len(starts):
        raise PosError("semantic delimiter absent")
    index = starts[ordinal - 1]
    if op == "before":
        return text[:index]
    return text[index + len(delimiter):]


def evaluate_program(program: str, examples: list[list[str]]) -> bool:
    if not program.startswith("Concat(") or not program.endswith(")"):
        return False
    atoms = _split_atoms(program[7:-1])
    try:
        outputs = ["".join(semantic_value(atom, text) for atom in atoms) for text, _ in examples]
    except (ParseError, PosError, ValueError, TypeError, RecursionError):
        return False
    return bool(examples) and outputs == [target for _, target in examples]


def candidate_semantic_items(visible: list[list[str]], operators=("before", "after")) -> list[dict]:
    delimiters = sorted({char for text, _target in visible for char in text if not char.isalnum() and not char.isspace()})
    result = []
    for delimiter in delimiters:
        for op in operators:
            if op == "span":
                continue
            for ordinal in (1, 2):
                atom = render_semantic(op.title(), delimiter, ordinal)
                values = []
                valid = True
                for text, target in visible:
                    try:
                        value = semantic_value(atom, text)
                    except (PosError, ValueError):
                        valid = False
                        break
                    if not value or value not in target:
                        valid = False
                        break
                    values.append(value)
                if valid and len(values) == len(visible):
                    result.append({"atoms": [atom], "values": values, "features": {"semantic_cost": 1.0},
                                   "width": 1, "semantic": True, "operator": op, "delimiter": delimiter,
                                   "ordinal": ordinal})
    return result


def candidate_span_items(visible: list[list[str]], include_transitions: bool = False,
                         include_runs: bool = False,
                         induced_predicates: list[dict] | None = None) -> list[dict]:
    delimiters = sorted({char for text, _target in visible for char in text if not char.isalnum() and not char.isspace()})
    boundaries = [{"kind": "start"}, {"kind": "end"}]
    for delimiter in delimiters:
        for ordinal in (1, 2):
            for side in ("start", "end"):
                boundaries.append({"kind": "delimiter", "value": delimiter, "ordinal": ordinal, "side": side})
    if include_transitions:
        observed = set()
        for text, _target in visible:
            for index in range(1, len(text)):
                pair = (_char_class(text[index - 1]), _char_class(text[index]))
                observed.add(pair)
        for left_class, right_class in sorted(observed):
            for ordinal in (1, 2):
                boundaries.append({"kind": "transition", "from": left_class, "to": right_class, "ordinal": ordinal})
    if include_runs:
        for predicate in ("alpha", "digit", "space", "punct", "upper", "lower", "alnum"):
            if any(any(_char_predicate(char, predicate) for char in text) for text, _target in visible):
                for ordinal in (1, 2):
                    for side in ("start", "end"):
                        boundaries.append({"kind": "run", "predicate": predicate, "ordinal": ordinal, "side": side})
    if induced_predicates is not None:
        for predicate in induced_predicates:
            for ordinal in (1, 2):
                for side in ("start", "end"):
                    boundaries.append({"kind": "run", "predicate": predicate, "ordinal": ordinal, "side": side})
    result = []
    for left in boundaries:
        for right in boundaries:
            atom = render_span(left, right)
            values = []
            valid = True
            for text, target in visible:
                try:
                    value = span_value(atom, text)
                except (PosError, ValueError):
                    valid = False
                    break
                if not value or value not in target:
                    valid = False
                    break
                values.append(value)
            if valid and len(values) == len(visible):
                result.append({"atoms": [atom], "values": values, "features": {"semantic_cost": 1.0},
                               "width": 1, "semantic": True, "operator": "span"})
    return result


def enumerate_semantic(task: dict, config: dict | None = None, search_width: int = 2,
                       operators=("before", "after"), semantic_cost: float = 1.0,
                       macros: list[str] | None = None, limit: int = 256,
                       state_beam: int = 8, budget: int = 4096,
                       include_transitions: bool = False, include_runs: bool = False,
                       induced_predicates: list[dict] | None = None) -> list[dict]:
    config = dict(config or BASE_CONFIG)
    visible = task["visible"]
    targets = tuple(target for _, target in visible)
    primitive, _ = atom_pool(canonical(visible), canonical(macros or []))
    transitions = {}
    for item in primitive:
        key = tuple(item["atoms"])
        transitions.setdefault(key, {**item, "width": len(key), "semantic": False})
    for item in _constant_items(visible):
        key = tuple(item["atoms"])
        transitions.setdefault(key, {**item, "width": len(key), "semantic": False})
    for item in candidate_semantic_items(visible, operators):
        transitions.setdefault(tuple(item["atoms"]), item)
    if "span" in operators:
        for item in candidate_span_items(visible, include_transitions=include_transitions, include_runs=include_runs,
                                         induced_predicates=induced_predicates):
            transitions.setdefault(tuple(item["atoms"]), item)
    scored = []
    for atoms, item in transitions.items():
        cost = semantic_cost + config["length_cost"] if item.get("semantic") else _cost(item, config)
        scored.append((cost, atoms, item))
    scored.sort(key=lambda row: (row[0], len(row[1]), canonical(row[1])))
    queue = [(0.0, 0, 0, (), tuple("" for _ in visible))]
    paths = {(0, tuple("" for _ in visible)): [(0.0, ())]}
    terminals = {}
    counter = expanded = 0
    while queue and expanded < budget:
        cost, _, used, atoms, outputs = heapq.heappop(queue)
        state = (used, outputs)
        known = {path: value for value, path in paths.get(state, [])}
        if known.get(atoms, float("inf")) < cost - 1e-12:
            continue
        if outputs == targets and used > 0:
            terminals[atoms] = min(cost, terminals.get(atoms, float("inf")))
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
    rows = []
    for atoms, cost in terminals.items():
        rows.append({"program": "Concat(" + ", ".join(atoms) + ")", "cost": cost,
                     "atom_count": len(atoms), "semantic_atoms": sum(parse_semantic(atom) is not None or parse_span(atom) is not None for atom in atoms),
                     "search_width": search_width})
    rows.sort(key=lambda row: (row["cost"], row["atom_count"], row["program"]))
    return rows[:limit]
