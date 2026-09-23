# V75: cross-family replay of retained executable macros

## Research question

Does a macro library mined from one mechanism family transfer to a different held-out mechanism family, rather than merely replaying within-family task variants?

## Protocol

For each replication, development tasks used `macro_transition`, while admission and final tasks used the separate `novel_operator_transition` family. The macro library was mined from development visible examples only. No admission or final examples were used during mining or candidate construction. The comparison was against the legacy ordinal grammar and direct V73 stack-grammar synthesis.

## Findings

| seed | arm | development | admission | final |
|---:|---|---:|---:|---:|
| 2026092101 | legacy | 10/24 | 5/24 | 7/24 |
| 2026092101 | direct grammar | 24/24 | 12/24 | 13/24 |
| 2026092101 | mined macro | 24/24 | 12/24 | 13/24 |
| 2026092102 | legacy | 9/24 | 11/24 | 11/24 |
| 2026092102 | direct grammar | 24/24 | 17/24 | 19/24 |
| 2026092102 | mined macro | 24/24 | 17/24 | 19/24 |

The mined-macro arm was selected in both replications. It retained three macros in each run and matched direct grammar on the cross-family admission and final splits. This is transfer across a family boundary, not just within-family memorization, but it does not yet show an accuracy advantage over direct synthesis.

## Interpretation

The result strengthens the V74 claim: a visible-only executable representation can persist and remain useful when the downstream task family changes. The improvement over the legacy grammar is replicated, but the equality between mined macros and direct grammar means the current contribution is reusable representation and transfer, not improved task accuracy.

## Limitations

The family boundary, safe instruction vocabulary, macro normalization, visible alignment, candidate budget, and admission gate remain researcher-authored. The cross-family relationship is deliberately chosen rather than discovered, and the final family still shares low-level code-point structure with the source family. This is bounded cross-family RSI evidence, not open-ended self-improvement.

## Verification

Both independent audits passed, each replaying 216 arm-task rows and checking 20 sealed artifacts. Archives: `runs/cross-family-macro-v75-20261021` and `runs/cross-family-macro-v75-20261022`.
