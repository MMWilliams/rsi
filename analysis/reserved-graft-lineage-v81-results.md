# V81: reserved-budget graft mutation

## Research question

Does reserving search budget for balanced low-level grafts let an immutable macro lineage discover useful new internal operators that ordinary constant/operator edits miss?

## Protocol

V81 reused the V80 cross-family protocol: development used `macro_transition`, while admission and final used `novel_operator_transition`. The mutation neighborhood was versioned so one-third of the bounded edit budget was reserved for raw-bit grafts. Parents remained immutable, and cross-task support credit required two development-task supporters.

## Findings

| arm | development | admission | final |
|---|---:|---:|---:|
| legacy | 9/24 | 6/24 | 7/24 |
| direct grammar | 24/24 | 13/24 | 12/24 |
| mined macro | 24/24 | 13/24 | 11/24 |
| credit lineage | 24/24 | 13/24 | 11/24 |
| internal mutation | 6/24 | 6/24 | 7/24 |

The credit lineage grew from 3 to 15 bodies, including one right-shift/or graft, but did not improve final accuracy. The reserved graft arm was not selected.

## Interpretation

Simply reserving capacity for a new edit type is insufficient. The current graft is one-sided (`shr` plus a combiner), while the held-out rotated mechanism needs a balanced left/right branch. This narrows the next intervention: introduce a typed two-branch mutation and test whether it can be retained without contaminating the parents.

## Limitations

This is one seed. The graft grammar, support threshold, family boundary, visible alignment, and admission gate remain researcher-authored; the V81 wrapper reuses the audited V80 runner with an explicit versioned flag. The result is bounded mutation evidence, not open-ended RSI.

## Verification

The independent audit passed, replaying 360 arm-task rows and checking 26 sealed artifacts. Archive: `runs/reserved-graft-lineage-v81-20261003`.
