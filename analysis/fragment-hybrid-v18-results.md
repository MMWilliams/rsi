# V18 neural fragment-macro hybrid result

This experiment tested whether a neural proposal can contribute useful partial
structure without being accepted as a complete program. For each sampled DSL
proposal, contiguous atom fragments were extracted, checked only against the
task's visible examples, and injected as temporary symbolic macros. The fixed
symbolic search kernel then composed those fragments with its existing atoms
and macros.

| Condition | Final result |
| --- | ---: |
| Symbolic baseline selected correctness | 9/16 |
| Raw neural proposals, pre-update pass@16 | 4/16 |
| Fragment-hybrid proposals, pre-update pass@16 | 9/16 |
| Ranked fragment-hybrid, pre-update | 9/16 |
| Raw neural proposals, post-update pass@16 | 3/16 |
| Fragment-hybrid proposals, post-update pass@16 | 9/16 |
| Ranked fragment-hybrid, post-update | 9/16 |

The positive result is a reliability gain: visible-only fragments converted
the neural proposal stream into correct programs on the same 9/16 task subset
covered by the symbolic baseline. The negative result is equally important:
the method did not expand the final coverage ceiling, and verified fragment
self-training did not change it. It appears to be a search-routing and
completion mechanism, not a new capability generator under this DSL and
budget.

The run harvested 13 verified fragment rows from 24 training tasks. The sealed
archive audit passed: 25 journal events were checked, 560 selected/sample
programs were deterministically replayed and regraded, and all 13 verified
training rows were rechecked. The audit does not rerun neural optimization and
does not authenticate the host.

## Main limitation

The fragment contract is intentionally conservative: it admits only
contiguous, non-empty substrings that agree across all visible examples. This
prevents hidden-label leakage, but it also makes fragments primarily useful
when the existing kernel already contains the missing composition. Future work
should test learned non-contiguous composition, typed intermediate values, and
cross-task fragment reuse on fresh banks, with preregistered replication before
claiming a coverage gain.
