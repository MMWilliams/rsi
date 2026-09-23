# V70 lower-level typed stack-program discovery

Status: audited two-seed result. V70 removes the named V69 constructors (`popcount`, `rotl`, and `gcd`) from the proposer. After a visible failure of the legacy ordinal grammar, the system searches a generic typed stack language containing loads, constants, shifts, bitwise operations, arithmetic, modulo, and a generic bit-fold map/reduce instruction. An evolutionary retention policy chooses between fold and bit-mix program families on development and must pass held-out admission.

The held-out bank contains fold-parity, fold-mod-3, and bit-splice mechanisms. The task generator does not expose the mechanism label to the proposer.

| Seed | Legacy development | Broad stack development | Evolved development | Legacy admission | Broad admission | Evolved admission | Legacy final | Broad final | Evolved final |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2026091961 | 6/24 | 24/24 | 24/24 | 5/24 | 24/24 | 24/24 | 13/24 | 24/24 | 24/24 |
| 2026091962 | 7/24 | 24/24 | 24/24 | 10/24 | 24/24 | 24/24 | 9/24 | 24/24 | 24/24 |

The evolved system selected only the generic `fold` family on both seeds. It passed admission and transferred perfectly to both fresh final banks. No named popcount node is present in the V70 proposer; the successful parity behavior is represented as a stack program that folds per-bit values with addition and applies modulo.

Both independent audits passed. Each replayed 216 evaluation rows and checked 19 sealed artifacts, for 432 rows and 38 artifacts across the two replications. The audited archives are `runs/stack-discovery-v70-20261007/` and `runs/stack-discovery-v70-20261008/`.

## Interpretation

V70 is the strongest current recursive-improvement result. V69 selected a named constructor; V70 reconstructs the useful representation from a lower-level executable instruction language and then compresses the retained family to `fold`. This is evidence of compositional substrate discovery rather than simple retrieval of a fixed operator name.

It remains bounded RSI evidence, not proof of open-ended RSI. The stack instruction set, generic fold primitive, mutation/evolution policy, visible target alignment, synthetic mechanism generator, and admission protocol remain researcher-authored. The generic fold instruction is itself a strong prior and is not equivalent to unconstrained invention from raw machine primitives.

## Next discriminating test

Remove the generic `fold_bits` instruction and evolve its behavior from raw shift, mask, and arithmetic instructions, using a typed program synthesizer or mutation-based stack search. Test on a new reduction family and retain the same independent audit and held-out gate.
