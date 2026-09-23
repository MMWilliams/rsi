# V73 self-editing executable grammar

Status: audited two-seed result after a contract repair. V73 evolves the set of enabled instructions in a safe executable sandbox. The initial grammar omits dormant operations; candidate predicates carry their required instruction set, and an evolutionary grammar editor selects an enabled subset on development with held-out admission.

The held-out family contains masked-complement, nibble-xor, and sub-fold mechanisms. The proposer receives no family label.

| Seed | Legacy development | Broad grammar development | Evolved grammar development | Legacy admission | Broad admission | Evolved admission | Legacy final | Broad final | Evolved final |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2026091991 | 3/24 | 10/24 | 10/24 | 7/24 | 17/24 | 17/24 | 12/24 | 18/24 | 18/24 |
| 2026091992 | 8/24 | 15/24 | 15/24 | 8/24 | 16/24 | 16/24 | 5/24 | 13/24 | 13/24 |

The evolved grammar converged to the same compact operation set on both seeds: `and`, `mod`, `not`, `shr`, and `xor`. It passed admission and matched the broad grammar on both fresh final banks.

The first exploratory V73 archives (`self-editing-grammar-v73-20261013` and `...20261014`) are excluded from this claim. A regression test found that their complement expression and hidden-domain implementation differed in masking order; the evaluator contract was repaired and both seeds were regenerated as `...20261015` and `...20261016` before auditing.

Both regenerated audits passed. Each replayed 216 evaluation rows and checked 20 sealed artifacts, for 432 rows and 40 artifacts across the two replications.

## Interpretation

V73 is evidence that the improver can change its executable hypothesis language: it retains a compact grammar that activates dormant primitives and transfers it to held-out mechanisms. This is a stronger form of recursive improvement than V72's fixed mutation vocabulary.

It remains bounded RSI evidence, not open-ended RSI. The sandbox instruction semantics, grammar mutation operators, visible alignment, synthetic task family, and admission protocol remain researcher-authored. The system edits which operations are available, but does not yet invent new instruction semantics.

## Next discriminating test

Let the grammar editor synthesize a new macro/instruction definition from existing primitives, validate it in a sandbox, and transfer it to a mechanism family absent from both the initial grammar and the mutation catalog. Retain strict contract tests like the V73 masking repair before promoting results.
