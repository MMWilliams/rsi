# Fixed-catalog seed-improver pilot

An admission gate over six frozen evaluator states did not outperform the
best fixed state on previously inspected banks. This is development evidence
and supplies no fresh improver-growth claim.

Twelve 32-task banks from the audited router and context-expert experiments
were each split into 16 admission and 16 final tasks. The catalog contained
E192, the public-context expert, its 50/50 blend, the pairwise ranker, the
E192/pairwise weight combination, and the learned router. The gate chose the
highest-scoring admission state only when it exceeded E192 by a declared
margin; otherwise it kept E192. All states used the same candidate pool.

| Strategy | Correct / 192 final tasks |
| --- | ---: |
| E192 fixed | 94 |
| Pure context expert fixed | **108** |
| Context blend fixed | **108** |
| Pairwise fixed | 94 |
| E192/pairwise combination fixed | 99 |
| Learned router fixed | 102 |
| Gate, margin 1 | 105 |
| Gate, margin 2 | 104 |
| Gate, margin 3 | 99 |
| Hindsight best state per episode | 115 |

At margin 1, the gate changed state in ten of twelve episodes yet lost three
tasks to the best fixed states. Increasing the margin retained E192 more
often and did worse. The hindsight ceiling exceeds the best fixed state by
only seven tasks across 12 episodes, while each gate decision relied on just
16 correlated admission tasks. More frequent switching is not evidence of a
better improver.

This pilot used opened data and did not preregister a fresh confirmation. It
does not invalidate the earlier confirmed E192 evaluator-growth result. It
shows that this closed catalog and small admission gate are not a supported
seed improver. A next edit must produce substantially different child
evaluators, and its selection rule must beat a fixed strong state under
matched verifier and training cost before a parent-to-child-improver test.

Machine results: `analysis/catalog-gate-development.json`. Source task banks
and candidate decisions came from `runs/evaluator-router-transfer-20260917/`
and `runs/context-expert-transfer-20260917/`, both independently audited.
