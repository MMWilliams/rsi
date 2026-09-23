# Pairwise evaluator feedback and query allocation

Status: **pairwise incremental growth gate failed.** The independent full replay passed in `runs/pairwise-query-transfer-20260918/audit.json`.

## Why this test

The preceding focused-feedback study established that blindly retraining or upweighting false output calls did not improve the eight-call evaluator. This study tested whether a decision-level loss helps: within each verified 48-task bank, rank tasks where one exact output would help above tasks where it would not. The same fixed pool, replay AST ranker, public-block route and top-20 output sensor were used for all policies. The external oracle scored final programs and could not be edited by the evaluator.

## Development dissection on opened banks

These analyses are **not fresh confirmation**:

- A public candidate-posterior proxy for query value scored below the trained E0 allocator on every opened panel. It overallocated calls to AST. See `analysis/posterior-query-value-development-20260918.json`.
- Reserving one or two AST calls produced mixed results: two reserved calls gained five tasks on one 576-task opened panel, but lost three on another six-bank panel. No stable quota was identified. See `analysis/family-quota-development-20260918.json`.
- At E0's 96 fixed call locations on an opened 576-task bank, top-20 entropy scored 345; the other public one-probe rules scored 336–343. An oracle choosing the best of eight probes at those same locations would score 355. An oracle jointly choosing probe and eight call locations per bank would score 402. Most measured headroom is in **where to call**, not which fixed probe to use. These oracle bounds use hidden outcomes and are not deployable. See `analysis/probe-counterfactual-development-20260918.json`.
- The selected all-pairs logistic ranker with weight decay .001 scored 346 versus E0's 342 on one opened transfer panel after six feedback banks. With 18 feedback banks it scored 348 versus E0's 345 on a second opened panel. A same-rule checkpoint replay showed P0=345, P3=343, P6=346 on the first; P0=P3=P6=343 and P18=348 on the second. The learning curve was not monotonic. See `analysis/pairwise-query-ranking-development-20260918.json` and `analysis/pairwise-checkpoint-development-20260918.json`.

## Fresh prospective test

Protocol: `EXPERIMENT-pairwise-query-transfer.md`. Models and protocol were frozen before seeds 902498–902509 were generated. Twelve new 48-task banks supplied 576 tasks. Each policy had eight true output calls per bank, 96 in total. All candidate pools, predicted outputs and policy allocations were saved before opening final labels.

| Policy | Correct / 576 | Role |
| --- | ---: | --- |
| E0 ridge on 576 source tasks | 338 | Retained early reference |
| P0 pairwise on 576 source tasks | 335 | Same-rule starting checkpoint |
| P6 pairwise after six feedback banks | 331 | Intermediate checkpoint |
| P18 pairwise after 18 feedback banks | 339 | Primary later checkpoint |
| Scrambled P18 | 331 | Feedback-inheritance control |
| Ridge-10 on the same 1,440 rows | 340 | Matched-data loss control |
| Ridge-100 on the same 1,440 rows | **343** | Strongest matched-data evaluator |
| Fixed transform + mutation calls | 332 | Fixed budget control |
| Deterministic random calls | 324 | Random budget control |

P18 beat P0 by **four tasks**. Six banks improved, two lost, and the paired exact bank-bootstrap interval was **[-3,+11]**. It exceeded E0 by one task, interval [-5,+7], and trailed the matched-data ridge-100 by four, interval for ridge minus P18 [0,+8]. The preregistered incremental promotion gate failed. P6 regressed to 331, so this is not a steady growth curve. Scrambling the added feedback lowered P18 by eight, showing the intact labels mattered for its behavior, but not enough to justify promoting it over the better matched-data model.

The no-query system scored 296. Querying every task scored 416 at 576 calls. Hindsight placement of eight calls per bank scored 391; reachable candidate coverage was 489 tasks. These are separate budgets or hidden-label bounds, not competing deployed policies.

P18 and P0 agreed on 70 of 96 calls. On the fresh tasks, P18's four extra gains came from transformation (+3) and novel-operator (+2), offset by AST (-1). Relative to P18, ridge-100 gained more from transformation and mutation but missed useful self-edit calls. Simple rank blending and family reservations failed to beat both models consistently across three opened panels; see `analysis/query-rank-fusion-development-20260918.json`.

An additional hindsight catalog analysis shows why choosing one entire evaluator policy per bank is a weak improver action. On the prior focused-feedback run, the best fixed policy scored 345 and an oracle choosing the best whole-bank policy from that catalog would score only 350; individual-call hindsight was 395. On this pairwise run, the best fixed policy scored 343, whole-bank catalog hindsight 351, and individual-call hindsight 391. Thus even a perfect whole-bank policy selector would add only 5 or 8 tasks on these catalogs, while most decision headroom lies in task-level allocation or genuinely new component edits. These are unavailable-label bounds, not deployed results. See `analysis/edit-catalog-headroom-20260918.json`.

The target run generated 100,514 base candidates plus 34,864 extra AST candidates, predicted 1,083,024 candidate/probe outputs and checked 135,378 candidate final labels for research scoring. Preparation wall time was 303.5 seconds; summed parallel generation CPU time was 1,487.5 seconds. Each deployed policy received 96 true output calls. The additional 864 feedback tasks used to train P18 required **201,884 candidate final labels and 1,615,072 predicted output cells**, on top of the original 576 source tasks. Those source costs matter when comparing evaluator growth to a static policy.

The independent auditor rebuilt all seven source models, regenerated all 576 tasks and candidate pools, checked 1,083,024 predicted output cells and 108 frozen bank-policy allocations, and replayed 135,378 candidate labels and all 108 bank-policy scores. It recomputed the forecast errors and gate. All checks passed.

## Decision

Keep E0 as the protected retained checkpoint. The matched-data ridge-100 model was the **best observed on this fresh set**, but its +5 over E0 had only five winning banks and a paired interval of [-1,+12]; it needs another protected replication before promotion. P18 is an unpromoted research candidate. A learner can change its choices with intact feedback and still fail to improve reliably or beat a simpler learner trained on the same evidence. The next improver experiment must choose among candidate evaluator/search/sensor edits from a common frozen base and then show that a later parent creates a better child improver on a second untouched bank. Forecast error, selected utility, harms and full acquisition cost should remain distinct endpoints. No synthetic result here establishes transfer to research, cybersecurity, social good or policy tasks.
