# V76: compositional mutation of retained macros

## Research question

Can a retained executable macro library improve itself by composing learned macros with arithmetic/bitwise combinators and mutated outer moduli, producing behavior not present in the original library?

## Protocol

Development tasks used `macro_transition`; admission and final tasks used the separate `novel_operator_transition` family. Three controls were retained from V75: legacy ordinal, direct stack grammar, and replay of mined macros. A fourth arm formed ordered pairs of retained macros, applied six generic combinators (`add`, `sub`, `xor`, `and`, `or`, `mul`), and searched bounded moduli using visible examples only.

## Findings

| seed | arm | development | admission | final |
|---:|---|---:|---:|---:|
| 2026092301 | legacy | 8/24 | 10/24 | 8/24 |
| 2026092301 | direct grammar | 24/24 | 15/24 | 16/24 |
| 2026092301 | mined macro | 24/24 | 15/24 | 16/24 |
| 2026092301 | composed mutation | 24/24 | 15/24 | 16/24 |
| 2026092302 | legacy | 13/24 | 7/24 | 6/24 |
| 2026092302 | direct grammar | 24/24 | 13/24 | 11/24 |
| 2026092302 | mined macro | 24/24 | 13/24 | 11/24 |
| 2026092302 | composed mutation | 24/24 | 13/24 | 11/24 |

The composed arm produced 188 and 162 candidates across the two 72-task banks, but never exceeded replayed macros or direct grammar and was never selected. The result replicated the null across two seeds.

## Interpretation

Macro retention transfers a useful representation, but the current self-improvement language is too weak to expand that representation. Pairwise arithmetic/bitwise composition of existing macro outputs did not discover the rotated or gcd-like behavior in the held-out family. This is a useful negative finding: reuse and compositional novelty are separate capabilities.

## Limitations

The combinator set, modulus bounds, pair budget, visible alignment, family boundary, and admission gate are researcher-authored. Composition only combines existing macro outputs; it does not synthesize new stack instructions or edit internal macro bodies. The experiment is bounded RSI evidence, not open-ended self-improvement.

## Verification

Both independent audits passed, replaying 288 arm-task rows and checking 22 sealed artifacts per run. Archives: `runs/composed-macro-v76-20260923` and `runs/composed-macro-v76-20260924`.
