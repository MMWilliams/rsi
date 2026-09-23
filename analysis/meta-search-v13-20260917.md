# V13 meta-search exploratory result

Run: `runs/meta-search-v13-20260917`.

This was a fresh 24-task bank using two visible-only search kernels at budget
128. Three selectors were compared after all searches closed: cheapest-cost
frontier, MAP-Elites-style syntax niches, and novelty-cost greedy selection.
Hidden examples were used only for final grading.

| Selector | Selected correct | Coverage@4 | Coverage@64 | Verified programs |
| --- | ---: | ---: | ---: | ---: |
| Cost frontier | 18/24 | 19/24 | 21/24 | 223 |
| MAP-Elites | 17/24 | 21/24 | 21/24 | 223 |
| Novelty-cost | 18/24 | 19/24 | 21/24 | 221 |

The result is a trade-off: MAP-Elites improved early coverage by two tasks but
lost one top-ranked task and produced no final coverage gain. It is therefore
not evidence of RSI. It does support a follow-up with a predeclared
multi-objective selector and independent bank replication.

Search cost was shared across selectors: 48 searches, 3,494 expansions,
13,512 generated nodes and 291,730 primitive executions. The run remains
exploratory because it has one bank and no standalone independent auditor.
