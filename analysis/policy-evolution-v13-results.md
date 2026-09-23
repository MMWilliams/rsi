# V13 evolved-policy result

The search-policy evolution run selected a champion using a 24-task
development bank, then evaluated it once on a separate 24-task final bank.
The champion changed the search cost weights, case cost, progress weight and
widening while preserving the bounded DSL and search interface.

| Policy | Development selected correct | Final selected correct | Final coverage@64 |
| --- | ---: | ---: | ---: |
| Base | 13/24 | 12/24 | 15/24 |
| Evolved champion | 13/24 | 14/24 | 15/24 |

The initial final result is encouraging but provisional: pass@1 increased by
2 tasks, coverage@64 did not change, and the study used one development/final
pair.

The frozen replication across three new banks was then rerun with full
frontier retention and independently audited. It found:

| Policy | Replication selected correct | Replication coverage@64 |
| --- | ---: | ---: |
| Base | 39/72 | 42/72 |
| Evolved champion | 39/72 | 42/72 |

Thus the evolved policy is a promising hypothesis, not a demonstrated general
improver. The result shows why fresh-bank replication is essential: the first
positive result did not survive the corrected replication. The replication
archive passed its independent audit.
