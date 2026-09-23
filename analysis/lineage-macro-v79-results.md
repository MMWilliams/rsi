# V79: immutable-parent lineage retention for macro mutation

## Research question

Can a mutable macro system retain useful learned structure by preserving parents, accumulating visible-consistent children, and freezing the resulting lineage for held-out replay?

## Protocol

Development tasks used `macro_transition`; admission and final tasks used the separate `novel_operator_transition` family. Starting from three mined parent macros, the lineage engine generated bounded typed children from development visible examples only. Parents were immutable and never deleted; the descendant library was capped at 24 bodies. Controls were legacy ordinal, direct grammar, unmodified macro replay, and unprotected local mutation.

## Findings

| seed | arm | development | admission | final |
|---:|---|---:|---:|---:|
| 2026092901 | legacy | 8/24 | 8/24 | 6/24 |
| 2026092901 | direct grammar | 24/24 | 14/24 | 13/24 |
| 2026092901 | mined macro | 24/24 | 14/24 | 13/24 |
| 2026092901 | lineage library | 24/24 | 14/24 | 13/24 |
| 2026092902 | legacy | 13/24 | 7/24 | 7/24 |
| 2026092902 | direct grammar | 24/24 | 15/24 | 16/24 |
| 2026092902 | mined macro | 24/24 | 15/24 | 16/24 |
| 2026092902 | lineage library | 24/24 | 15/24 | 16/24 |

The lineage grew from 3 to 15 bodies in both runs. It matched the protected parent baseline and avoided the V78 collapse of unprotected mutation, which scored 6/24 and 7/24 final on the same protocol.

## Interpretation

Parent protection and accumulation are necessary stability mechanisms for self-editing. The result does not yet show an accuracy gain, but it demonstrates that a learned executable representation can be expanded without destroying its transfer behavior. The next step is lineage-level counterexample credit: retain children based on cross-task benefit and admission-gated replacement, not merely visible consistency.

## Limitations

The mutation grammar, child budget, library cap, visible retention rule, family boundary, and admission gate remain researcher-authored. Descendants are generated from a bounded typed fragment language, and no neural/world-model self-modification occurs. This is bounded lineage RSI evidence, not open-ended self-improvement.

## Verification

Both independent audits passed, replaying 360 arm-task rows and checking 25 sealed artifacts per run. Archives: `runs/lineage-macro-v79-20260929` and `runs/lineage-macro-v79-20260930`.
