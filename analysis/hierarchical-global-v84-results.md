# V84: hierarchical generic body composition with a global development bank

## Research question

Does factorizing generic typed search into a reusable development-only body bank improve deep operator transfer beyond a flat search with the same 11-node and 64-state limits?

## Protocol

The seed library contained only `load_ord`. A global body bank was built once from development-visible symbols, then frozen for lineage support and admission/final replay. Bodies used only generic integer leaves and binary operators; no rotate, bitmix, popcount, or gcd constructor was supplied. The hierarchical arm composed generic subexpressions into balanced bodies; the flat arm searched the same maximum body size and state cap without factorization. Both used immutable parents, two-task support credit, and the same fresh bank (`bank_seed=2026101301`).

## Findings

| arm | development | admission | final | retained bodies |
|---|---:|---:|---:|---:|
| legacy | 6/24 | 7/24 | 12/24 | — |
| direct grammar | 14/24 | 24/24 | 24/24 | — |
| generic hierarchical | 6/24 | 7/24 | 12/24 | 20 |
| generic flat | 6/24 | 7/24 | 12/24 | 17 |

Both generic arms solved all 12/12 final `bit_splice` tasks and zero non-`bit_splice` mechanisms. Hierarchical factorization increased retained-body count and reached 11-node bodies, but did not improve selective transfer or aggregate accuracy over flat search.

## Interpretation

The result strengthens the earlier selective-transfer finding: generic typed bodies can reproduce the held-out operator behavior without a named rotate template. It also rules out a simple explanation in which deeper factorization alone creates an overall improver. The retained bodies may be functional shortcuts induced by the shared code-point distribution rather than a semantically faithful rotate representation.

## Limitations

The instruction vocabulary, constant bounds, 11-node limit, archive policy, support threshold, development-visible global alphabet, synthetic family relation, and admission gate remain authored. Development and held-out families share a low-level code-point convention. No neural/world-model self-modification or open-ended resource growth is present.

## Verification

Both independent audits passed, each replaying 288 arm-task rows and checking 25 sealed artifacts. Archives: `runs/generic-body-evolution-v84-hierarchical-global-20261013` and `runs/generic-body-evolution-v84-flat-global-20261013`.

