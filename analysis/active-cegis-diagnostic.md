# Active CEGIS diagnostic

An interactive arm queried hidden target outputs as environment feedback to
filter the visible-equivalent candidate version space. This is deliberately
separate from the passive holdout results: hidden examples are oracle queries
in this arm and are not evidence of closed-loop generalization.

| Bank | Passive selected | Active, 1 query | Active, 2 queries | Active, 4 queries |
| --- | ---: | ---: | ---: | ---: |
| V19-A | 21/24 | 21/24 | 21/24 | 21/24 |
| V19-B | 19/24 | 19/24 | 20/24 | 20/24 |
| V20 | 17/24 | 18/24 | 18/24 | 18/24 |

The result shows that a small amount of external feedback can resolve some
visible ambiguity, but it does not repair missing candidate structure. It is
an interactive synthesis diagnostic, not RSI: the oracle is queried directly,
the candidate set is bounded, and no recursive improvement was demonstrated.
