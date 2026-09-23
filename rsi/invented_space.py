"""Visible-only synthesis with bounded, data-invented positional operators.

V43 extends the fixed FlashFill substrate with a deliberately small invention
metalanguage.  The learner may discover run boundaries for punctuation, white
space, alphanumeric text, non-space text, or an observed literal separator.
The operator instances are generated from visible inputs only and are
verified by an independent evaluator; they are never copied from references.

This is an experiment in hypothesis-language expansion, not an unrestricted
Python/code execution path.  Every invented position has a finite regex,
ordinal, side, and resource cost.
"""

from __future__ import annotations

import ast
import heapq
import json
import re
from collections import Counter

from .atom_pool_partial import atom_pool
from .cegis_search import _constant_items, _cost
from .common import canonical
from .search import BASE_CONFIG
from dsl import PosError, run, render_atom
from parse import ParseError, parse


_FAMILY_PATTERNS = {
    "PUNCT_RUN": r"[^A-Za-z0-9\\s]+",
    "SPACE_RUN": r"\\s+",
    "ALNUM_RUN": r"[A-Za-z0-9]+",
    "NONSPACE_RUN": r"\\S+",
}
_FAMILY_ORDER = tuple(_FAMILY_PATTERNS)
_R_RE = re.compile(r'^R\((?P<family>"(?:[^"\\]|\\.)*"),(?P<ordinal>[12]),(?P<side>start|end)\)$')


def render_invented(family: str, ordinal: int, side: str) -> str:
    if family not in _FAMILY_PATTERNS and not family.startswith("CHAR:"):
        raise ValueError("unknown invented family")
    if ordinal not in (1, 2) or side not in ("start", "end"):
        raise ValueError("invalid invented position")
    return f"R({json.dumps(family, ensure_ascii=True)},{ordinal},{side})"


def parse_invented(atom: str) -> tuple[str, int, str] | None:
    match = _R_RE.fullmatch(atom)
    if not match:
        return None
    family = json.loads(match.group("family"))
    if family not in _FAMILY_PATTERNS and not family.startswith("CHAR:"):
        raise ValueError("unknown invented family")
    return family, int(match.group("ordinal")), match.group("side")


def _pattern(family: str) -> str:
    if family.startswith("CHAR:"):
        return re.escape(family[5:])
    return _FAMILY_PATTERNS[family]


def invented_value(atom: str, text: str) -> str:
    parsed = parse_invented(atom)
    if parsed is None:
        program = parse("Concat(" + atom + ")")
        return run(program, text)
    family, ordinal, side = parsed
    matches = list(re.finditer(_pattern(family), text))
    if not 1 <= ordinal <= len(matches):
        raise PosError("invented position absent")
    match = matches[ordinal - 1]
    index = match.start() if side == "start" else match.end()
    # A position is represented as a zero-width boundary.  Resolve the same
    # descriptor as both ends of a one-atom substring is not useful, so the
    # item constructor below supplies paired descriptors for extraction.
    return text[index:index]


def _resolve_position(family: str, ordinal: int, side: str, text: str) -> int:
    matches = list(re.finditer(_pattern(family), text))
    if not 1 <= ordinal <= len(matches):
        raise PosError("invented position absent")
    match = matches[ordinal - 1]
    return match.start() if side == "start" else match.end()


def _invented_atom_value(atom: str, text: str) -> str:
    """Interpret R(family,n,side) as the run ending at the discovered edge.

    The positional primitive is intentionally an atom-level extractor rather
    than a free-form regex program.  `start` extracts the run, and `end` is
    also useful as a run extractor; paired boundary operators are represented
    by the candidate generator and remain finite and auditable.
    """
    parsed = parse_invented(atom)
    if parsed is None:
        program = parse("Concat(" + atom + ")")
        return run(program, text)
    family, ordinal, _side = parsed
    matches = list(re.finditer(_pattern(family), text))
    if not 1 <= ordinal <= len(matches):
        raise PosError("invented run absent")
    return matches[ordinal - 1].group(0)


def evaluate_atoms(atoms: list[str] | tuple[str, ...], text: str) -> str:
    values = []
    for atom in atoms:
        try:
            values.append(_invented_atom_value(atom, text))
        except (ParseError, PosError, ValueError, TypeError, RecursionError):
            # Preserve the old atom semantics if it is not an invented atom.
            program = parse("Concat(" + atom + ")")
            values.append(run(program, text))
    return "".join(values)


def invented_correct(program: str, examples: list[list[str]]) -> bool:
    """Independent semantic check for a rendered mixed program."""
    if not program.startswith("Concat(") or not program.endswith(")"):
        return False
    body = program[7:-1]
    # Candidate atoms contain no top-level commas except inside R's JSON
    # string, so use the same canonical atom list produced by the search and
    # only parse old atoms with the pinned parser.
    atoms = _split_atoms(body)
    try:
        return bool(examples) and [evaluate_atoms(atoms, inp) for inp, _ in examples] == [out for _, out in examples]
    except (ParseError, PosError, ValueError, TypeError, RecursionError, SyntaxError):
        return False


def _split_atoms(body: str) -> list[str]:
    atoms, start, depth, quote, escaped = [], 0, 0, None, False
    for index, char in enumerate(body):
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in ("'", '"'):
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif char == "," and depth == 0:
            atoms.append(body[start:index].strip())
            start = index + 1
    tail = body[start:].strip()
    if tail:
        atoms.append(tail)
    return atoms


def _observed_families(visible: list[list[str]]) -> list[str]:
    observed_chars = Counter()
    for text, _target in visible:
        for char in text:
            if not char.isalnum() and not char.isspace():
                observed_chars[char] += 1
    families = list(_FAMILY_ORDER)
    # Literal separators are learned only when they are actually observable;
    # this prevents inventing arbitrary constants from outside the task.
    families.extend("CHAR:" + char for char, _count in sorted(observed_chars.items()))
    return families


def invented_pool(visible: list[list[str]], families: list[str] | None = None,
                  ordinal_limit: int = 2) -> list[dict]:
    families = list(families or _observed_families(visible))
    targets = [target for _, target in visible]
    result = []
    seen = set()
    for family in families:
        for ordinal in range(1, ordinal_limit + 1):
            # A run itself is the new atom.  The side is retained in the
            # operator identity so the catalog can distinguish boundary use.
            for side in ("start", "end"):
                atom = render_invented(family, ordinal, side)
                if atom in seen:
                    continue
                values = []
                valid = True
                for text, target in visible:
                    matches = list(re.finditer(_pattern(family), text))
                    if ordinal > len(matches):
                        valid = False
                        break
                    value = matches[ordinal - 1].group(0)
                    if not value or value not in target:
                        valid = False
                        break
                    values.append(value)
                if valid and len(values) == len(visible):
                    result.append({"atoms": [atom], "values": values,
                                   "features": {"invented_cost": 1.0},
                                   "macro": False, "invented": True,
                                   "family": family, "ordinal": ordinal, "side": side})
                    seen.add(atom)
    return result


def enumerate_invented(task: dict, config: dict | None = None, search_width: int = 2,
                       families: list[str] | None = None, invented_cost: float = 1.0,
                       limit: int = 256, state_beam: int = 8, budget: int = 4096,
                       macros: list[str] | None = None, synthesize_constants: bool = False) -> list[dict]:
    """Enumerate old and invented transitions by visible-prefix dynamic search."""
    config = dict(config or BASE_CONFIG)
    visible = task["visible"]
    targets = tuple(value for _, value in visible)
    old_pool, _ = atom_pool(canonical(visible), canonical(macros or []))
    transitions = {}
    for item in old_pool:
        key = tuple(item["atoms"])
        transitions.setdefault(key, {**item, "width": len(key), "invented": False})
    if synthesize_constants:
        for item in _constant_items(visible):
            key = tuple(item["atoms"])
            transitions.setdefault(key, {**item, "width": len(key), "invented": False})
    for item in invented_pool(visible, families=families):
        key = tuple(item["atoms"])
        transitions.setdefault(key, {**item, "width": 1, "invented": True})
    scored = []
    for atoms, item in transitions.items():
        cost = _cost(item, config) if not item.get("invented") else invented_cost + config["length_cost"]
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
                     "atom_count": len(atoms), "search_width": search_width,
                     "invented_atoms": sum(parse_invented(atom) is not None for atom in atoms),
                     "atoms": list(atoms)})
    rows.sort(key=lambda row: (row["cost"], row["atom_count"], row["program"]))
    return rows[:limit]
