"""MDL-style byte-pair grammar induction over verified DSL programs."""

from __future__ import annotations

import json
from collections import Counter

from .grammar_library import atom_shape
from parse import parse


def _key(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def mine_bpe_templates(programs: list[str], max_merges: int = 64,
                       max_library: int = 32) -> dict:
    sequences = []
    definitions = {}
    for text in programs:
        atoms = tuple(parse(text).atoms)
        tokens = []
        for atom in atoms:
            shape = atom_shape(atom)
            token = "A:" + _key(shape)
            definitions[token] = [shape]
            tokens.append(token)
        if len(tokens) >= 2:
            sequences.append(tokens)
    merges = []
    for merge_index in range(max_merges):
        counts = Counter()
        for sequence in sequences:
            counts.update(zip(sequence, sequence[1:]))
        if not counts:
            break
        pair, frequency = max(counts.items(), key=lambda row: (row[1], tuple(row[0])))
        if frequency < 2:
            break
        token = f"M:{merge_index}"
        definitions[token] = definitions[pair[0]] + definitions[pair[1]]
        merges.append({"shape": definitions[token], "count": frequency,
                       "compression_gain": frequency * (len(definitions[token]) - 1)})
        updated = []
        for sequence in sequences:
            output = []
            index = 0
            while index < len(sequence):
                if index + 1 < len(sequence) and (sequence[index], sequence[index + 1]) == pair:
                    output.append(token)
                    index += 2
                else:
                    output.append(sequence[index])
                    index += 1
            updated.append(output)
        sequences = updated
    deduped = {}
    for row in merges:
        deduped[_key(row["shape"])] = row
    selected = sorted(deduped.values(), key=lambda row: (-row["compression_gain"], -row["count"], _key(row["shape"])))[:max_library]
    return {"templates": selected, "source_programs": len(programs), "merges": len(merges),
            "parameters": {"max_merges": max_merges, "max_library": max_library,
                           "selection": "MDL-byte-pair-v1"}}
