"""Experimental pool retaining pieces empty on some visible examples."""
from .common import canonical
from .search import features
from dsl import Case, ConstStr, CPos, MatchPos, PosError, SubStr, eval_atom, render_atom, run
from parse import ParseError, parse


def atom_pool(serialized_visible: str, serialized_macros: str):
    import json
    visible = json.loads(serialized_visible)
    macros = json.loads(serialized_macros)
    positions = [CPos(i) for i in range(-8, 9)]
    positions += [MatchPos(token, n, side) for token in ("WORD", "DIGITS", "UPPER", "LOWER") for n in (1, 2) for side in ("start", "end")]
    constants = {" ", "-", "/", ".", ", ", ": "}
    # Constants may only be inferred from outputs visible to the worker.
    constants.update(character for _, output in visible for character in output if not character.isalnum())
    atoms = [ConstStr(value) for value in sorted(constants)]
    for start in positions:
        for end in positions:
            atom = SubStr(start, end)
            atoms.extend([atom, Case("upper", atom), Case("lower", atom), Case("cap", atom)])
    pool, primitive_executions = [], 0
    for atom in atoms:
        values = []
        for inp, target in visible:
            primitive_executions += 1
            try:
                out = eval_atom(atom, inp)
            except PosError:
                break
            # Empty on some examples is allowed; only substring membership prunes here.
            if out not in target:
                break
            values.append(out)
        if len(values) == len(visible) and any(values):
            pool.append({"atoms": [render_atom(atom)], "values": values, "features": features(atom), "macro": False})
    for text in macros[:32]:
        try:
            program = parse(text)
            values = []
            for inp, target in visible:
                primitive_executions += len(program.atoms)
                out = run(program, inp)
                if out not in target:
                    break
                values.append(out)
            if len(values) == len(visible) and any(values) and len(program.atoms) <= 3:
                counts = {key: 0 for key in features(ConstStr(""))}
                for atom in program.atoms:
                    for key, value in features(atom).items():
                        counts[key] += value
                pool.append({"atoms": [render_atom(atom) for atom in program.atoms], "values": values, "features": counts, "macro": True})
        except (ValueError, ParseError, PosError, RecursionError):
            continue
    pool.sort(key=lambda item: canonical(item["atoms"]))
    return pool, primitive_executions
