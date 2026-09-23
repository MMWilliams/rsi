"""Relational anti-unification over DSL programs.

Unlike the earlier shape library, this representation preserves arithmetic
relations between character positions inside a fragment.  For example, two
substring atoms using C0 and C-4 remain linked by a -4 offset when the schema
is instantiated.
"""

from __future__ import annotations

import itertools
import json
import math

from .atom_pool_partial import atom_pool
from .common import canonical
from dsl import Case, Concat, ConstStr, CPos, MatchPos, SubStr, render
from parse import parse


def _anchor(atoms) -> int | None:
    positions = []
    for atom in atoms:
        stack = [atom]
        while stack:
            item = stack.pop()
            if isinstance(item, SubStr):
                stack.extend([item.start, item.end])
            elif isinstance(item, Case):
                stack.append(item.atom)
            elif isinstance(item, CPos):
                positions.append(item.k)
    return min(positions) if positions else None


def _position_shape(position, anchor: int | None) -> dict:
    if isinstance(position, CPos):
        return {"kind": "C", "delta": position.k - (anchor or 0)}
    if isinstance(position, MatchPos):
        return {"kind": "M", "token": position.tok, "n": position.n, "side": position.side}
    return {"kind": "unknown"}


def atom_relational_shape(atom, anchor: int | None) -> dict:
    if isinstance(atom, ConstStr):
        return {"kind": "const"}
    if isinstance(atom, SubStr):
        return {"kind": "substr", "start": _position_shape(atom.start, anchor),
                "end": _position_shape(atom.end, anchor)}
    if isinstance(atom, Case):
        return {"kind": "case", "op": atom.op,
                "inner": atom_relational_shape(atom.atom, anchor)}
    return {"kind": "unknown"}


def fragment_shape(atoms) -> list[dict]:
    anchor = _anchor(atoms)
    return [atom_relational_shape(atom, anchor) for atom in atoms]


def _json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def mine_relational_templates(programs: list[str], max_library: int = 32,
                              max_length: int = 3, min_frequency: int = 2) -> dict:
    counts: dict[str, int] = {}
    for text in programs:
        parsed = parse(text)
        atoms = tuple(parsed.atoms)
        seen: set[str] = set()
        for length in range(2, min(max_length, len(atoms)) + 1):
            for start in range(len(atoms) - length + 1):
                seen.add(_json(fragment_shape(atoms[start:start + length])))
        for shape in seen:
            counts[shape] = counts.get(shape, 0) + 1
    eligible = [(shape, count) for shape, count in counts.items() if count >= min_frequency]
    eligible.sort(key=lambda row: (-(row[1] * (len(json.loads(row[0])) - 1)), -row[1], row[0]))
    selected = eligible[:max_library]
    return {"templates": [{"shape": json.loads(shape), "count": count} for shape, count in selected],
            "candidate_shapes": len(counts), "eligible_shapes": len(eligible), "source_programs": len(programs),
            "parameters": {"max_library": max_library, "max_length": max_length,
                           "min_frequency": min_frequency, "representation": "relative-C-offsets-v1"}}


def _local_position(shape: dict) -> dict:
    if shape.get("kind") == "C":
        return {"kind": "C"}
    return {key: value for key, value in shape.items() if key != "delta"}


def local_shape(shape: dict) -> dict:
    result = {key: value for key, value in shape.items() if key not in {"start", "end", "inner"}}
    if shape.get("kind") == "substr":
        result.update({"start": _local_position(shape["start"]), "end": _local_position(shape["end"])})
    elif shape.get("kind") == "case":
        result["inner"] = local_shape(shape["inner"])
    return result


def instantiate_relational_templates(library: dict, visible: list[list[str]],
                                     common_macros: list[str] | None = None,
                                     max_proposals: int = 256, slot_limit: int = 16) -> list[str]:
    pool, _ = atom_pool(canonical(visible), canonical(common_macros or []))
    options = []
    seen = set()
    for item in pool:
        if len(item["atoms"]) != 1 or item["atoms"][0] in seen:
            continue
        text = item["atoms"][0]
        parsed = parse("Concat(" + text + ")")
        options.append((text, parsed.atoms[0]))
        seen.add(text)
    options.sort(key=lambda row: row[0])
    output, seen_programs = [], set()
    for template in library.get("templates", []):
        shapes = template["shape"]
        slots = []
        for shape in shapes:
            candidates = [(text, atom) for text, atom in options
                          if local_shape(atom_relational_shape(atom, _anchor([atom]))) == local_shape(shape)]
            slots.append(candidates[:slot_limit])
        if any(not candidates for candidates in slots):
            continue
        for choices in itertools.product(*slots):
            atoms = tuple(atom for _, atom in choices)
            if fragment_shape(atoms) != shapes:
                continue
            program = render(Concat(atoms))
            if program in seen_programs:
                continue
            seen_programs.add(program)
            output.append(program)
            if len(output) >= max_proposals:
                return output
    return output


def program_relational_bonus(program: str, library: dict) -> float:
    try:
        atoms = tuple(parse(program).atoms)
    except Exception:
        return 0.0
    counts = {_json(item["shape"]): item["count"] for item in library.get("templates", [])}
    best = 0.0
    for length in range(2, min(3, len(atoms)) + 1):
        for start in range(len(atoms) - length + 1):
            shape = _json(fragment_shape(atoms[start:start + length]))
            if shape in counts:
                best = max(best, math.log1p(counts[shape]))
    return best
