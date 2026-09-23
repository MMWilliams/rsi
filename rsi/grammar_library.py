"""Anti-unifying reusable fragment shapes for passive program synthesis."""

from __future__ import annotations

import itertools
import json

from .common import ROOT, canonical  # noqa: F401 - installs the pinned vendor import path
from .atom_pool_partial import atom_pool
from dsl import Case, Concat, ConstStr, CPos, MatchPos, SubStr, render, render_atom
from parse import parse


def position_shape(position) -> str:
    if isinstance(position, CPos):
        return "C"
    if isinstance(position, MatchPos):
        return "M"
    return "?"


def atom_shape(atom) -> dict:
    if isinstance(atom, ConstStr):
        return {"kind": "const"}
    if isinstance(atom, SubStr):
        return {"kind": "substr", "start": position_shape(atom.start), "end": position_shape(atom.end)}
    if isinstance(atom, Case):
        return {"kind": "case", "op": atom.op, "inner": atom_shape(atom.atom)}
    return {"kind": "unknown"}


def fragment_shapes(programs: list[str], max_length: int = 3) -> dict[str, int]:
    counts: dict[str, int] = {}
    for text in programs:
        parsed = parse(text)
        atoms = tuple(parsed.atoms)
        seen: set[str] = set()
        for length in range(2, min(max_length, len(atoms)) + 1):
            for start in range(len(atoms) - length + 1):
                shape = json.dumps([atom_shape(atom) for atom in atoms[start:start + length]],
                                   sort_keys=True, separators=(",", ":"))
                seen.add(shape)
        for shape in seen:
            counts[shape] = counts.get(shape, 0) + 1
    return counts


def mine_templates(programs: list[str], max_library: int = 32, max_length: int = 3,
                   min_frequency: int = 2) -> dict:
    counts = fragment_shapes(programs, max_length)
    eligible = [(shape, count) for shape, count in counts.items() if count >= min_frequency]
    eligible.sort(key=lambda row: (-(row[1] * (len(json.loads(row[0])) - 1)), -row[1], row[0]))
    selected = eligible[:max_library]
    return {
        "templates": [{"shape": json.loads(shape), "count": count} for shape, count in selected],
        "candidate_shapes": len(counts), "eligible_shapes": len(eligible), "source_programs": len(programs),
        "parameters": {"max_library": max_library, "max_length": max_length, "min_frequency": min_frequency},
    }


def matches_shape(atom, shape: dict) -> bool:
    actual = atom_shape(atom)
    if actual.get("kind") != shape.get("kind"):
        return False
    if actual["kind"] == "substr":
        return actual["start"] == shape["start"] and actual["end"] == shape["end"]
    if actual["kind"] == "case":
        return actual["op"] == shape["op"] and matches_shape_from_dict(atom.atom, shape["inner"])
    return True


def matches_shape_from_dict(atom, shape: dict) -> bool:
    return matches_shape(atom, shape)


def instantiate_templates(library: dict, visible: list[list[str]], common_macros: list[str] | None = None,
                           max_proposals: int = 256, slot_limit: int = 16) -> list[str]:
    """Instantiate anti-unified shapes using only visible-compatible atoms."""
    pool, _ = atom_pool(canonical(visible), canonical(common_macros or []))
    options: list[tuple[str, object]] = []
    seen_atoms: set[str] = set()
    for item in pool:
        if len(item["atoms"]) != 1:
            continue
        text = item["atoms"][0]
        if text in seen_atoms:
            continue
        parsed = parse("Concat(" + text + ")")
        options.append((text, parsed.atoms[0]))
        seen_atoms.add(text)
    options.sort(key=lambda row: row[0])
    output: list[str] = []
    seen_programs: set[str] = set()
    for template in library.get("templates", []):
        shapes = template["shape"]
        slots = [[item for item in options if matches_shape(item[1], shape)][:slot_limit] for shape in shapes]
        if any(not candidates for candidates in slots):
            continue
        for choices in itertools.product(*slots):
            program = render(Concat(tuple(parse("Concat(" + text + ")").atoms[0] for text, _ in choices)))
            if program not in seen_programs:
                output.append(program)
                seen_programs.add(program)
            if len(output) >= max_proposals:
                return output
    return output
