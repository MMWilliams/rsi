# V34 evolutionary ranking-program synthesis

Status: audited null result. V34 evolved a candidate-ranking program with Gaussian mutation and tournament-style elitism over 32 individuals for 24 generations. The ranker used generator likelihood, candidate cost, atom structure, position types, and constant complexity as features; its weights were learned from independently oracle-graded development candidate pools.

| Arm | Development | Admission | Fresh final |
| --- | ---: | ---: | ---: |
| Generator control | 22/24 | 15/24 | 16/24 |
| Evolved ranking program | 22/24 | 15/24 | 16/24 |

The evolved program was accepted by the gate because it tied control on development and admission, but it produced no fresh-bank gain. This is a direct negative test of selector-level self-modification: evolving the ranking function without expanding the candidate hypothesis space did not improve transfer.

The archive passed independent replay: 144 evaluations and 21 sealed artifacts were checked. Limitations include oracle-labeled development evolution, a fixed candidate DSL and feature vocabulary, bounded evolutionary search, and small banks. This is not proof of RSI.

Artifact: `runs/genetic-ranker-v34-20260917/`.
