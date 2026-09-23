# V80: multi-generation lineage credit and protected retention

## Research question

Can cross-task support credit turn stable lineage retention into improvement, while preserving immutable parents and rejecting unsupported mutations?

## Protocol

Development used `macro_transition`; admission and final used `novel_operator_transition`. Three parent macros were mined from development visible examples. Across two generations, a mutated child entered the shared library only when supported by at least two independent development tasks. Parents were immutable and the library was bounded at 24 bodies. Controls were legacy ordinal, direct grammar, unmodified macro replay, and unprotected local mutation.

## Findings

| seed | arm | development | admission | final |
|---:|---|---:|---:|---:|
| 2026100101 | legacy | 3/24 | 6/24 | 12/24 |
| 2026100101 | direct grammar | 24/24 | 20/24 | 19/24 |
| 2026100101 | mined macro | 24/24 | 20/24 | 19/24 |
| 2026100101 | credit lineage | 24/24 | 20/24 | 19/24 |
| 2026100102 | legacy | 9/24 | 6/24 | 7/24 |
| 2026100102 | direct grammar | 24/24 | 12/24 | 14/24 |
| 2026100102 | mined macro | 24/24 | 12/24 | 14/24 |
| 2026100102 | credit lineage | 24/24 | 12/24 | 14/24 |

The credit lineage grew from 3 to 12 bodies in both runs. It matched protected replay and passed admission twice. Unprotected mutation scored 12/24 and 7/24 final, showing that the stability gain comes from parent protection and cross-task support rather than mutation alone.

## Interpretation

Cross-task credit prevents unsupported local edits from contaminating the shared representation. It converts V79’s simple accumulation into a more principled lineage policy, but it still does not produce an accuracy gain. The remaining bottleneck is proposal quality: the mutation neighborhood does not yet contain a child that improves the held-out mechanism.

## Limitations

Support thresholds, mutation grammar, library cap, family boundary, visible alignment, and admission gate remain researcher-authored. The lineage is symbolic and bounded; no neural/world-model self-modification is present. This is protected bounded RSI evidence, not open-ended self-improvement.

## Verification

Both independent audits passed, replaying 360 arm-task rows and checking 25 sealed artifacts per run. Archives: `runs/credit-lineage-v80-20261001` and `runs/credit-lineage-v80-20261002`.
