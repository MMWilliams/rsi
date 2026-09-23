# Learned AST query allocation at a fixed total budget

## Decision

**Do not promote the learned query allocator as an improved evaluator or improver.** With exactly **96 oracle output calls** across twelve fresh eight-task AST banks, it selected **31/96** correct programs, tying the simple rule of one query on every task at **31/96**. It beat neither that strongest fixed control nor its own promotion gate: learned-minus-one-each bank differences were 0,0,0,−1,+1,0,0,0,0,0,0,0, with an exact bank-resampling 95% interval of **−3 to +3**. Random two-on-four scored 29, high-entropy two-on-four 28, high-disagreement two-on-four 24, and a within-bank feature-scrambled learned policy 29. The 96-task reconstruction audit passed.

The learned policy is a useful negative test of the positive-feedback-loop hypothesis. It changed query placement—14 tasks got none, 68 got one and 14 got two—but did not improve final choices over the static schedule. An unqueried ranker scored 14/96 on the same pools. Candidate reachability was 55/96.

## Training and matched controls

The allocator was a 12-feature ridge model trained on the prior audited 96-task output-sensor bank. Its labels were the task-level correctness changes after the first and second top-20 entropy queries; its features came only from public examples, frozen rank scores and candidate-predicted probe outputs. Leave-one-bank-out development selected regularization 100, scoring 37/96 against 36/96 for one-per-task. The new test therefore examined a small development edge rather than assuming transfer.

Fresh mixed-stream seeds 902330–902335 each generated a full mixed bank before eight AST tasks were selected; AST-only seeds 902336–902341 each generated eight tasks. Every allocation saw the same V67/V73 cap-512 pool and replay AST ranker. An exact multiple-choice knapsack chose zero, one or two queries per task under **eight calls per bank**. Fixed two-on-four schedules, one-per-task and feature-scrambled learned allocations all spent the same eight calls. A top-20 entropy policy selected probe inputs within a queried task. All pools, candidate-predicted outputs, rank scores, first probes and allocations were frozen before true outputs or final labels were opened.

| Allocation, 96 calls each | Correct / 96 |
| --- | ---: |
| One query per task | **31** |
| Learned 0/1/2 allocation | **31** |
| Feature-scrambled learned state | 29 |
| Deterministic random, two on four | 29 |
| High entropy, two on four | 28 |
| High top disagreement, two on four | 24 |

The runner generated **47,346** candidate programs and **378,768** local candidate-output predictions; preparation took **64.0 seconds wall time** and **203.1 summed candidate-generation seconds** across workers. The audit regenerated all 96 tasks and pools, all 378,768 predicted outputs, all twelve eight-call allocations and all 47,346 final candidate labels, and passed. The scorer used sealed outputs to replay every policy's counterfactual path; 96 is the logical oracle-call budget per deployed policy, not the number of host reads made to score all arms offline. Training acquisition from the source bank is additional to this matched inference budget.

## Why the allocator did not improve

A post hoc oracle with complete knowledge of these tasks could allocate the same eight calls per bank for **40/96** correct. That number is diagnostic headroom, not a deployable control. The learned allocator spent **35 of 96** calls on tasks whose pools contained no correct program, compared with 41 for one-per-task. It saved some wasted calls but failed to turn them into more correct choices. Its predictions correlated weakly with realized marginal query value: **0.18** for the first query and **0.11** for the second. Across the 96 tasks, 18 first queries improved correctness, one hurt, and nine second queries improved correctness. The current public-feature value model does not reliably identify those cases. See `analysis/ast-query-allocation-diagnostic.json`.

The current best supported fixed-budget AST evaluator action is **one top-20 entropy output query per task** at one call per task, with the caveat that top-20's advantage over minimax failed its prior bank-level policy gate. The separate best zero-query whole-system control remains the prior fixed temperature map. No tested learned allocation, admission policy or later parent has yet produced a better child improver. The next meaningful improver test needs a more predictive edit-value or reachability model and a protected parent/child design that compares both parents on the same base, query budget and new child bank. More feedback labels alone have repeatedly failed to guarantee this.

Protocol: `EXPERIMENT-ast-query-allocation-transfer.md`. Source development: `analysis/ast-query-allocation-development.json`. Runner and audit: `ast_query_allocation_transfer.py`, `audit_ast_query_allocation_transfer.py`. Frozen data: `runs/ast-query-allocation-transfer-20260918/`.
