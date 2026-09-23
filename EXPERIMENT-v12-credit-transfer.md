# V12: prospective inherited-credit transfer comparison

Status: protocol and selector implementation prepared; fresh transfer run not
yet launched. This study follows the audited V10 source probe and tests whether
its measured credit fields help a bounded improver choose edits on new tasks.

## Hypothesis

An inherited estimate of an edit's effect on later improvement can select more
productive edits than immediate effect alone. The paired estimate is
`(edited_terminal - edited_start) - (baseline_terminal - baseline_start)` from
V10. It remains a source-derived estimate, not a proven causal predictor.

## Frozen source evidence

Use the sealed, independently audited V10 result at
`runs/paired-credit-20260916-v10/`. Aggregate all 72 paired rows by the twelve
existing numeric operator names before generating the new transfer bank. For
each operator, retain immediate effect, observational total-descendant effect,
and paired later-improvement effect as separate fields. No transfer outcome may
modify these source fields before the final evaluation.

All conditions receive the same V10 source evidence and its acquisition cost:

1. `immediate_only`: productivity plus immediate mean effect.
2. `observational_descendant`: productivity plus immediate effect plus 0.25 times
   the observed total-descendant mean.
3. `paired_credit`: productivity plus immediate effect plus 0.25 times the paired
   later-improvement mean.
4. `scrambled_paired`: the same paired records permuted across operator names.
5. `empty`: no inherited effect fields.
6. `random`: uniform operator selection through the same proposal and evaluation
   opportunities.

The selection draws, edit catalog, downstream task slices, six generations, two
proposals per generation, search budget, admission rule and final bank are fixed
across conditions. Each condition restarts from the same `BASE_CONFIG` and
initial catalog. Total downstream opportunities are matched; source acquisition
cost is charged once and reported for every condition rather than treated as
free.

## Fresh transfer bank and measurements

Generate six fresh source groups with seeds 347, 359, 373, 389, 401 and 419,
24 development tasks, 24 admission tasks and a common 256-task final bank. Each
task has three visible and thirteen hidden examples. Exclude every protected
template in prior runs, V10, V11 and implementation fixtures. Search sees only
visible examples; final tasks never enter selection or inherited-memory updates.

Primary outcome: paired final solve-rate difference for each credit condition
against `immediate_only`, with source-group and task-level contrasts reported.
Secondary outcomes: generation snapshots, accepted edits, immediate versus
later gains, full search/oracle/replay costs, and whether the paired selector's
choices differ from the immediate-only selector before final scoring.

No condition is promoted from a positive mean alone. A useful signal requires a
positive primary mean, positive contrasts in at least four of six source groups,
and no worse mean than immediate-only on the predeclared final screen. These are
engineering criteria, not significance tests. Six groups share the same final
bank and are not independent populations.

## Integrity and audit

Snapshot source evidence, protocol, configuration, selector, evaluator and
auditor before bank generation. Journal every selection draw, source-table hash,
request, exact replay, admission decision, checkpoint state and cost. The
independent auditor must regenerate banks, reexecute every unique request and
replay, recompute strict-oracle scores, reconstruct each selection and verify
that final evaluation begins after optimization closes. Preserve failures and
reject any resealed semantic forgery.

V12 does not test model weights, self-created edit types, mission-domain value or
full RSI. A positive result would justify reconnecting a validated credit policy
to the larger common-ancestor and amplify/verify/distill loop; it would not by
itself establish recursive self-improvement.
