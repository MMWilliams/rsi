# V83: generic typed-body evolution without a named rotate mutation

## Research question

Can a generic bottom-up stack-expression search replace the researcher-authored rotate mutation, retain useful bodies through cross-task support credit, and transfer them to a held-out stack family?

## Protocol

The seed library contained only `load_ord`. Candidate bodies were assembled from generic integer leaves and binary operators (`add`, `sub`, `mul`, `xor`, `and`, `or`, `shl`, `shr`, `mod`) using visible examples only. Children required support from at least two development tasks; parents were immutable and the lineage was capped at 24 bodies. Development used `novel_operator_transition`; admission and final used `stack_transition`. No rotate, bitmix, popcount, or gcd constructor was supplied.

## Findings

| arm | development | admission | final |
|---|---:|---:|---:|
| legacy | 10/24 | 8/24 | 10/24 |
| direct grammar | 15/24 | 24/24 | 24/24 |
| generic body evolution | 10/24 | 8/24 | 10/24 |
| generic lineage | 10/24 | 8/24 | 10/24 |

The generic lineage grew to 24 bodies over two generations, but its retained representations did not improve aggregate accuracy beyond the legacy baseline. Direct grammar was selected.

The aggregate score hides a selective transfer signal. In the first fresh bank, generic lineage solved all 10/10 `bit_splice` tasks and 0 tasks from the other stack mechanisms. In the independent MAP-Elites bank, it solved all 7/7 `bit_splice` tasks and 0 non-`bit_splice` tasks. The direct grammar solved 24/24 overall in both banks.

## Interpretation

Removing the named rotate mutation exposed two distinct outcomes: generic typed composition produced a selective cross-family `bit_splice` signal, but support credit did not improve aggregate accuracy and selected structurally repetitive low-level bodies. This separates functional operator transfer from proof that the retained body is the intended rotate representation or that the overall improver is better.

## Limitations

The typed instruction set, constants, beam/archive search, support threshold, visible alignment, synthetic family relationship, and admission gate remain authored. The two banks share the same low-level code-point convention, and selective behavior does not prove representation identity. No neural/world-model self-modification is present.

## Verification

Both independent replay audits passed, each reconstructing 288 arm-task rows and checking 24 sealed artifacts. Archives: `runs/generic-body-evolution-v83-20261008` and `runs/generic-body-evolution-v83-mapelites-20261009`.
