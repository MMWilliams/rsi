# Supported seed on changed arithmetic mechanisms

Status: **the cheap query allocator did not transfer ahead of the prior allocator; candidate search and selection are the larger limits.** This is a 96-task changed-mechanism stress test, not another panel from the familiar six-mechanism generator. Full task/pool/prediction/decision/final-label replay passed after an audit-only JSON normalization of tuple-valued task metadata.

## Frozen setup

Twelve banks of eight tasks came from `shifted_ast_bank` with new seeds 903000-903011, one visible and 23 hidden examples each. Inputs occupy the familiar AST Unicode block, but the four arithmetic predicates differ from the training `ast_transition` rules. The existing V67/V73 AST arms generated base and widened candidate pools; the old AST replay ranker and frozen E0 top-20 reranker evaluated the same widened candidates. Neither generator nor evaluator was retrained. The first probe, all predictions and four-call choices were frozen before final labels opened. Protocol: `EXPERIMENT-shifted-ast-seed-transfer.md`.

The protected 24-feature E0 query model, the prior fixed allocator and a deterministic hash-four control each spent **48 exact-output calls** across 96 tasks. One query on every task was a separate **96-call** reference. The exact interpreter checked candidate correctness on the final 15 hidden examples.

## Outcome and bottleneck

| Quantity or policy | Correct or reachable / 96 | Output calls |
| --- | ---: | ---: |
| Correct candidate in full widened pool | 61 | — |
| Correct candidate in old top 20 | 40 | — |
| Old ranker, no query | 12 | 0 |
| E0 reranker, no query | 15 | 0 |
| E0 plus deterministic hash-four | 17 | 48 |
| E0 plus cheap learned four-call placement | 21 | 48 |
| E0 plus prior four-call allocator | **22** | 48 |
| E0 plus one query on every task | 23 | 96 |
| E0 plus unavailable hindsight four-call placement | 23 | 48 |

Cheap minus prior was **-1**, with zero positive and one losing bank, paired exact bank-bootstrap interval **[-3,0]**. Cheap beat hash-four by +4, but only five of twelve banks improved and the interval was [0,+8]. The declared allocator transfer gate failed. More importantly, no four-call allocator could exceed the prior one by four on this bank: hindsight placement reached 23, only **+1** beyond prior 22. This is the protocol's action-space-limit case, so this result does not justify more training of the same query-placement model.

The full pool covered 61 tasks, but the old top 20 covered only 40; **21 reachable tasks lay below the shortlist**. Even querying every task selected only 23, leaving **17 top-20 reachable tasks** unresolved and 38 full-pool reachable tasks unsolved by the present one-call system. E0 improved no-query ranking over old by only three. The next changed-mechanism edit should improve candidate coverage, shortlist formation or post-query ranking, then remeasure query value on identical pools. A familiar Unicode cue did not make the learned allocator superior under changed arithmetic rules.

An opened-task decomposition rechecked all 45,810 labels and separated those misses. Of the 96 tasks, 35 had no final-correct candidate; 15 were correct without a call; eight were corrected by one call, including two whose best correct candidate was below the old top 20; 19 remained wrong with correct candidates below the top 20; and 19 remained wrong despite a correct candidate in the old top 20 surviving the actual probe. **Every reachable task retained at least one final-correct candidate after that probe**, so probe elimination was not the cause of these misses. The top-20 recall and post-query ranking edits have distinct, measurable targets. See `analysis/shifted-ast-failure-dissection-v2-20260918.json`.

## Cost and audit

The run generated 13,186 base candidates and 32,624 extra AST candidates, rescored 1,920 top-20 entries, and predicted 366,480 candidate/probe outputs. Preparation took 94.2 seconds wall time, with 419.6 summed parallel candidate-generation seconds. The research oracle rechecked 45,810 final candidate labels. The cheap and prior policies each bought 48 logical exact outputs; the one-each reference bought 96.

The first audit attempt stopped before replay because `shifted_ast_bank` emits a tuple for rule parameters and JSON reloads it as a list. The audit-only wrapper normalized regenerated task metadata through JSON without changing the frozen experiment runner or its recorded hash. The completed audit regenerated all 96 tasks and candidate pools, checked 366,480 predicted output cells, 1,920 E0 rescores, 36 frozen allocations and 45,810 final candidate labels; it passed. See `audit_shifted_ast_seed_transfer.py` and `runs/shifted-ast-seed-transfer-20260918/audit.json`.

This result is limited to one shifted-AST task generator. It demonstrates that the current seed's fixed-budget gains on familiar mechanisms do not establish robust transfer or a growing improver. The next seed study should explicitly separate **search reachability**, **top-20 recall**, **zero-query ranking**, **sensor correction** and **allocation regret** under changed mechanisms before selecting an edit.
